const MAGIC = 'OSWMGB02';
const SCHEMA_VERSION = 2;
const HEADER_BYTES = 192;
const UINT32_MAX = 0xffffffff;
const EARTH_RADIUS_M = 6371008.8;
const DEG_TO_RAD = Math.PI / 180;
const ISOCHRONE_CELL_SIZE_M = 20;
const ISOCHRONE_BUFFER_M = 50;
const ISOCHRONE_MAX_CELLS = 250000;

let graph = null;
let profileIndexes = new Map();
let heuristicScales = [];
let snapMarks = null;
let snapEpoch = 0;

self.addEventListener('message', async event => {
    const { id, type, ...payload } = event.data || {};
    try {
        let result;
        if (type === 'init') result = await initialize(payload);
        else if (type === 'snap') result = snapToNetwork(payload.coordinates);
        else if (type === 'route') result = routeRequest(payload);
        else if (type === 'isochrone') result = isochroneRequest(payload);
        else throw new Error(`Unknown routing worker request: ${type}`);
        self.postMessage({ id, ok: true, result });
    } catch (error) {
        self.postMessage({
            id,
            ok: false,
            error: error instanceof Error ? error.message : String(error)
        });
    }
});

async function initialize({ graphUrl, profileOrder, profileHeuristicScales }) {
    const response = await fetch(graphUrl);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText} loading routing graph`);
    }
    graph = parseGraph(await response.arrayBuffer());
    if (!Array.isArray(profileOrder) || profileOrder.length !== graph.profileCount) {
        throw new Error('Routing profiles do not match the binary graph.');
    }
    profileIndexes = new Map(profileOrder.map((profileId, index) => [profileId, index]));
    heuristicScales = profileOrder.map((_, index) => {
        const value = Number(profileHeuristicScales?.[index]);
        // Float32 edge weights can round a few ulps below their source value.
        // Keep the heuristic strictly conservative across those conversions.
        return Number.isFinite(value) && value >= 0
            ? Math.min(1, value) * 0.999999
            : 0;
    });
    snapMarks = new Uint32Array(graph.segmentCount);
    return {
        bounds: graph.bounds,
        nodeCount: graph.nodeCount,
        directedEdgeCount: graph.directedEdgeCount,
        segmentCount: graph.segmentCount,
        profileCount: graph.profileCount
    };
}

function parseGraph(buffer) {
    if (buffer.byteLength < HEADER_BYTES) {
        throw new Error('Routing graph is shorter than its header.');
    }
    const bytes = new Uint8Array(buffer, 0, 8);
    const magic = new TextDecoder().decode(bytes);
    const view = new DataView(buffer);
    if (magic !== MAGIC || view.getUint32(8, true) !== SCHEMA_VERSION) {
        throw new Error('Unsupported routing graph schema.');
    }
    if (view.getUint32(12, true) !== HEADER_BYTES) {
        throw new Error('Routing graph header size is invalid.');
    }

    const nodeCount = view.getUint32(16, true);
    const directedEdgeCount = view.getUint32(20, true);
    const profileCount = view.getUint32(24, true);
    const segmentCount = view.getUint32(28, true);
    const gridCols = view.getUint32(32, true);
    const gridRows = view.getUint32(36, true);
    const cellMembershipCount = view.getUint32(40, true);
    const offset = byteOffset => {
        const result = Number(view.getBigUint64(byteOffset, true));
        if (!Number.isSafeInteger(result) || result < HEADER_BYTES || result > buffer.byteLength) {
            throw new Error('Routing graph contains an invalid array offset.');
        }
        return result;
    };
    const offsets = [48, 56, 64, 72, 80, 88, 96, 104, 112].map(offset);
    const finalBytes = offsets[8] + cellMembershipCount * Uint32Array.BYTES_PER_ELEMENT;
    if (finalBytes > buffer.byteLength || offsets.some((value, index) => index && value < offsets[index - 1])) {
        throw new Error('Routing graph arrays are truncated or out of order.');
    }

    return {
        nodeCount,
        directedEdgeCount,
        profileCount,
        segmentCount,
        gridCols,
        gridRows,
        bounds: [
            view.getFloat64(136, true),
            view.getFloat64(144, true),
            view.getFloat64(152, true),
            view.getFloat64(160, true)
        ],
        tolerance: view.getFloat64(168, true),
        longitudes: new Float64Array(buffer, offsets[0], nodeCount),
        latitudes: new Float64Array(buffer, offsets[1], nodeCount),
        adjacencyOffsets: new Uint32Array(buffer, offsets[2], nodeCount + 1),
        targets: new Uint32Array(buffer, offsets[3], directedEdgeCount),
        weights: new Float32Array(buffer, offsets[4], profileCount * directedEdgeCount),
        segmentA: new Uint32Array(buffer, offsets[5], segmentCount),
        segmentB: new Uint32Array(buffer, offsets[6], segmentCount),
        cellOffsets: new Uint32Array(buffer, offsets[7], gridCols * gridRows + 1),
        cellSegments: new Uint32Array(buffer, offsets[8], cellMembershipCount)
    };
}

function requireGraph() {
    if (!graph) throw new Error('Routing graph has not finished loading.');
}

function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
}

function gridCoordinate(value, minimum, maximum, cells) {
    if (cells <= 1 || maximum <= minimum) return 0;
    return clamp(Math.floor((value - minimum) / (maximum - minimum) * cells), 0, cells - 1);
}

function projectedDistanceM(lon1, lat1, lon2, lat2, referenceLat) {
    const x = (lon2 - lon1) * DEG_TO_RAD * EARTH_RADIUS_M * Math.cos(referenceLat * DEG_TO_RAD);
    const y = (lat2 - lat1) * DEG_TO_RAD * EARTH_RADIUS_M;
    return Math.hypot(x, y);
}

function inspectSegment(segmentId, lon, lat, best) {
    if (snapMarks[segmentId] === snapEpoch) return best;
    snapMarks[segmentId] = snapEpoch;
    const a = graph.segmentA[segmentId];
    const b = graph.segmentB[segmentId];
    const scaleX = DEG_TO_RAD * EARTH_RADIUS_M * Math.cos(lat * DEG_TO_RAD);
    const scaleY = DEG_TO_RAD * EARTH_RADIUS_M;
    const ax = (graph.longitudes[a] - lon) * scaleX;
    const ay = (graph.latitudes[a] - lat) * scaleY;
    const bx = (graph.longitudes[b] - lon) * scaleX;
    const by = (graph.latitudes[b] - lat) * scaleY;
    const dx = bx - ax;
    const dy = by - ay;
    const denominator = dx * dx + dy * dy;
    const t = denominator > 0 ? clamp(-(ax * dx + ay * dy) / denominator, 0, 1) : 0;
    const distanceM = Math.hypot(ax + t * dx, ay + t * dy);
    if (distanceM >= best.distanceM) return best;
    return {
        segmentId,
        t,
        a,
        b,
        distanceM,
        coordinates: [
            graph.longitudes[a] + t * (graph.longitudes[b] - graph.longitudes[a]),
            graph.latitudes[a] + t * (graph.latitudes[b] - graph.latitudes[a])
        ]
    };
}

function snapToNetwork(coordinates) {
    requireGraph();
    const lon = Number(coordinates?.[0]);
    const lat = Number(coordinates?.[1]);
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
        throw new Error('Snap coordinates must be finite longitude and latitude values.');
    }

    snapEpoch = (snapEpoch + 1) >>> 0;
    if (snapEpoch === 0) {
        snapMarks.fill(0);
        snapEpoch = 1;
    }
    const [minLon, minLat, maxLon, maxLat] = graph.bounds;
    const centerCol = gridCoordinate(lon, minLon, maxLon, graph.gridCols);
    const centerRow = gridCoordinate(lat, minLat, maxLat, graph.gridRows);
    const maximumRadius = Math.max(graph.gridCols, graph.gridRows);
    let best = { distanceM: Infinity };

    for (let radius = 0; radius < maximumRadius; radius += 1) {
        const firstCol = Math.max(0, centerCol - radius);
        const lastCol = Math.min(graph.gridCols - 1, centerCol + radius);
        const firstRow = Math.max(0, centerRow - radius);
        const lastRow = Math.min(graph.gridRows - 1, centerRow + radius);
        for (let row = firstRow; row <= lastRow; row += 1) {
            for (let col = firstCol; col <= lastCol; col += 1) {
                if (
                    radius > 0
                    && row !== firstRow
                    && row !== lastRow
                    && col !== firstCol
                    && col !== lastCol
                ) continue;
                const cellId = row * graph.gridCols + col;
                for (
                    let index = graph.cellOffsets[cellId];
                    index < graph.cellOffsets[cellId + 1];
                    index += 1
                ) {
                    best = inspectSegment(graph.cellSegments[index], lon, lat, best);
                }
            }
        }

        const west = minLon + firstCol / graph.gridCols * (maxLon - minLon);
        const east = minLon + (lastCol + 1) / graph.gridCols * (maxLon - minLon);
        const south = minLat + firstRow / graph.gridRows * (maxLat - minLat);
        const north = minLat + (lastRow + 1) / graph.gridRows * (maxLat - minLat);
        const containsTarget = lon >= west && lon <= east && lat >= south && lat <= north;
        const outsideDistances = [];
        if (firstCol > 0) outsideDistances.push(projectedDistanceM(lon, lat, west, lat, lat));
        if (lastCol < graph.gridCols - 1) outsideDistances.push(projectedDistanceM(lon, lat, east, lat, lat));
        if (firstRow > 0) outsideDistances.push(projectedDistanceM(lon, lat, lon, south, lat));
        if (lastRow < graph.gridRows - 1) outsideDistances.push(projectedDistanceM(lon, lat, lon, north, lat));
        if (
            containsTarget
            && Number.isFinite(best.distanceM)
            && (outsideDistances.length === 0 || best.distanceM <= Math.min(...outsideDistances))
        ) break;
    }
    if (!Number.isFinite(best.distanceM)) throw new Error('Routing graph has no snappable segments.');
    return best;
}

function edgeWeight(profileIndex, edgeId) {
    if (edgeId === UINT32_MAX) return Infinity;
    return graph.weights[profileIndex * graph.directedEdgeCount + edgeId];
}

function directedEdge(source, target) {
    let low = graph.adjacencyOffsets[source];
    let high = graph.adjacencyOffsets[source + 1];
    while (low < high) {
        const middle = (low + high) >> 1;
        const candidate = graph.targets[middle];
        if (candidate < target) low = middle + 1;
        else high = middle;
    }
    return low < graph.adjacencyOffsets[source + 1] && graph.targets[low] === target
        ? low
        : UINT32_MAX;
}

function partialWeight(weight, fraction) {
    if (fraction <= 1e-12) return 0;
    return Number.isFinite(weight) ? weight * fraction : Infinity;
}

function distanceMeters(lon1, lat1, lon2, lat2) {
    const phi1 = lat1 * DEG_TO_RAD;
    const phi2 = lat2 * DEG_TO_RAD;
    const deltaLat = (lat2 - lat1) * DEG_TO_RAD;
    const deltaLon = (lon2 - lon1) * DEG_TO_RAD;
    const value = Math.sin(deltaLat / 2) ** 2
        + Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLon / 2) ** 2;
    return 2 * EARTH_RADIUS_M * Math.atan2(
        Math.sqrt(value),
        Math.sqrt(Math.max(0, 1 - value))
    );
}

function pathDistanceM(path) {
    let result = 0;
    for (let index = 1; index < path.length; index += 1) {
        result += distanceMeters(
            path[index - 1][0],
            path[index - 1][1],
            path[index][0],
            path[index][1]
        );
    }
    return result;
}

class MinHeap {
    constructor() {
        this.nodes = [];
        this.priorities = [];
        this.lastPriority = Infinity;
    }

    get size() {
        return this.nodes.length;
    }

    push(priority, node) {
        let index = this.nodes.length;
        this.nodes.push(node);
        this.priorities.push(priority);
        while (index > 0) {
            const parent = (index - 1) >> 1;
            if (this.priorities[parent] <= priority) break;
            this.nodes[index] = this.nodes[parent];
            this.priorities[index] = this.priorities[parent];
            index = parent;
        }
        this.nodes[index] = node;
        this.priorities[index] = priority;
    }

    pop() {
        const result = this.nodes[0];
        this.lastPriority = this.priorities[0];
        const tailNode = this.nodes.pop();
        const tailPriority = this.priorities.pop();
        if (this.nodes.length) {
            let index = 0;
            while (true) {
                const left = index * 2 + 1;
                if (left >= this.nodes.length) break;
                const right = left + 1;
                const child = right < this.nodes.length
                    && this.priorities[right] < this.priorities[left]
                    ? right : left;
                if (this.priorities[child] >= tailPriority) break;
                this.nodes[index] = this.nodes[child];
                this.priorities[index] = this.priorities[child];
                index = child;
            }
            this.nodes[index] = tailNode;
            this.priorities[index] = tailPriority;
        }
        return result;
    }
}

function sanitizeSnap(snap) {
    const segmentId = Number(snap?.segmentId);
    const t = Number(snap?.t);
    if (!Number.isInteger(segmentId) || segmentId < 0 || segmentId >= graph.segmentCount) {
        throw new Error('Route endpoint references an invalid graph segment.');
    }
    if (!Number.isFinite(t) || t < 0 || t > 1) {
        throw new Error('Route endpoint has an invalid segment position.');
    }
    const a = graph.segmentA[segmentId];
    const b = graph.segmentB[segmentId];
    return {
        segmentId,
        t,
        a,
        b,
        coordinates: [
            graph.longitudes[a] + t * (graph.longitudes[b] - graph.longitudes[a]),
            graph.latitudes[a] + t * (graph.latitudes[b] - graph.latitudes[a])
        ]
    };
}

function routeForProfile(rawStart, rawEnd, profileId) {
    const profileIndex = profileIndexes.get(profileId);
    if (profileIndex === undefined) throw new Error(`Unknown routing profile: ${profileId}`);
    const start = sanitizeSnap(rawStart);
    const end = sanitizeSnap(rawEnd);
    const startAb = edgeWeight(profileIndex, directedEdge(start.a, start.b));
    const startBa = edgeWeight(profileIndex, directedEdge(start.b, start.a));
    const endAb = edgeWeight(profileIndex, directedEdge(end.a, end.b));
    const endBa = edgeWeight(profileIndex, directedEdge(end.b, end.a));

    let bestWeight = Infinity;
    let bestGoal = -1;
    let direct = false;
    if (start.segmentId === end.segmentId) {
        const delta = end.t - start.t;
        const candidate = delta >= 0
            ? partialWeight(startAb, delta)
            : partialWeight(startBa, -delta);
        if (candidate < bestWeight) {
            bestWeight = candidate;
            direct = true;
        }
    }

    const distances = new Float64Array(graph.nodeCount);
    distances.fill(Infinity);
    const previous = new Int32Array(graph.nodeCount);
    previous.fill(-1);
    const queue = new MinHeap();
    const scale = heuristicScales[profileIndex] || 0;
    const heuristic = node => scale * distanceMeters(
        graph.longitudes[node],
        graph.latitudes[node],
        end.coordinates[0],
        end.coordinates[1]
    );
    const addStart = (node, weight) => {
        if (weight < distances[node]) {
            distances[node] = weight;
            previous[node] = -2;
            queue.push(weight + heuristic(node), node);
        }
    };
    addStart(start.a, partialWeight(startBa, start.t));
    addStart(start.b, partialWeight(startAb, 1 - start.t));

    let visitedNodes = 0;
    while (queue.size) {
        const node = queue.pop();
        const currentPriority = queue.lastPriority;
        const expectedPriority = distances[node] + heuristic(node);
        if (currentPriority > expectedPriority + 1e-7) continue;
        if (currentPriority >= bestWeight) break;
        visitedNodes += 1;

        let terminal = Infinity;
        if (node === end.a) terminal = partialWeight(endAb, end.t);
        if (node === end.b) terminal = Math.min(terminal, partialWeight(endBa, 1 - end.t));
        if (distances[node] + terminal < bestWeight) {
            bestWeight = distances[node] + terminal;
            bestGoal = node;
            direct = false;
        }

        for (
            let edgeId = graph.adjacencyOffsets[node];
            edgeId < graph.adjacencyOffsets[node + 1];
            edgeId += 1
        ) {
            const weight = edgeWeight(profileIndex, edgeId);
            if (!Number.isFinite(weight)) continue;
            const target = graph.targets[edgeId];
            const candidate = distances[node] + weight;
            if (candidate < distances[target]) {
                distances[target] = candidate;
                previous[target] = node;
                queue.push(candidate + heuristic(target), target);
            }
        }
    }

    if (!Number.isFinite(bestWeight)) return null;
    let path;
    if (direct) {
        path = [start.coordinates, end.coordinates];
    } else {
        const nodePath = [];
        for (let node = bestGoal; node >= 0; node = previous[node]) {
            nodePath.push(node);
            if (previous[node] === -2) break;
        }
        nodePath.reverse();
        path = [start.coordinates];
        for (const node of nodePath) {
            const coordinate = [graph.longitudes[node], graph.latitudes[node]];
            const last = path[path.length - 1];
            if (coordinate[0] !== last[0] || coordinate[1] !== last[1]) path.push(coordinate);
        }
        const last = path[path.length - 1];
        if (end.coordinates[0] !== last[0] || end.coordinates[1] !== last[1]) {
            path.push(end.coordinates);
        }
        if (path.length === 1) path.push(end.coordinates);
    }
    return { path, weight: bestWeight, distanceM: pathDistanceM(path), visitedNodes };
}

function routeRequest({
    start,
    end,
    profileId,
    comparisonProfileId,
    fallbackProfileId
}) {
    requireGraph();
    const primary = routeForProfile(start, end, profileId);
    let comparison = null;
    if (comparisonProfileId) {
        comparison = routeForProfile(start, end, comparisonProfileId);
    } else if (!primary && fallbackProfileId) {
        comparison = routeForProfile(start, end, fallbackProfileId);
    }
    return {
        primary,
        comparison
    };
}

function normalizeIsochroneCutoffs(cutoffsMinutes) {
    if (!Array.isArray(cutoffsMinutes) || cutoffsMinutes.length === 0) {
        throw new Error('Isochrone cutoffs must be a non-empty array of minutes.');
    }
    const cutoffs = [...new Set(cutoffsMinutes.map(Number))].sort((a, b) => a - b);
    if (
        cutoffs.some(value => !Number.isFinite(value) || value <= 0 || value > 120)
    ) {
        throw new Error('Isochrone cutoffs must be greater than 0 and no more than 120 minutes.');
    }
    return cutoffs;
}

function boundedDistancesFromOrigin(rawOrigin, profileIndex, maximumWeight) {
    const origin = sanitizeSnap(rawOrigin);
    const distances = new Float64Array(graph.nodeCount);
    distances.fill(Infinity);
    const queue = new MinHeap();
    const originAb = edgeWeight(profileIndex, directedEdge(origin.a, origin.b));
    const originBa = edgeWeight(profileIndex, directedEdge(origin.b, origin.a));
    const addOriginEndpoint = (node, weight) => {
        if (weight <= maximumWeight && weight < distances[node]) {
            distances[node] = weight;
            queue.push(weight, node);
        }
    };
    addOriginEndpoint(origin.a, partialWeight(originBa, origin.t));
    addOriginEndpoint(origin.b, partialWeight(originAb, 1 - origin.t));

    let visitedNodes = 0;
    while (queue.size) {
        const node = queue.pop();
        const currentDistance = queue.lastPriority;
        if (currentDistance > distances[node] + 1e-7) continue;
        if (currentDistance > maximumWeight) break;
        visitedNodes += 1;
        for (
            let edgeId = graph.adjacencyOffsets[node];
            edgeId < graph.adjacencyOffsets[node + 1];
            edgeId += 1
        ) {
            const weight = edgeWeight(profileIndex, edgeId);
            if (!Number.isFinite(weight)) continue;
            const target = graph.targets[edgeId];
            const candidate = currentDistance + weight;
            if (candidate <= maximumWeight && candidate < distances[target]) {
                distances[target] = candidate;
                queue.push(candidate, target);
            }
        }
    }
    return { origin, originAb, originBa, distances, visitedNodes };
}

function interpolateSegment(a, b, fraction) {
    return [
        graph.longitudes[a] + fraction * (graph.longitudes[b] - graph.longitudes[a]),
        graph.latitudes[a] + fraction * (graph.latitudes[b] - graph.latitudes[a])
    ];
}

function addReachablePart(parts, from, to) {
    const start = clamp(from, 0, 1);
    const end = clamp(to, 0, 1);
    if (end - start > 1e-10) parts.push([start, end]);
}

function mergedReachableParts(parts) {
    if (!parts.length) return [];
    parts.sort((left, right) => left[0] - right[0] || left[1] - right[1]);
    const merged = [parts[0].slice()];
    for (let index = 1; index < parts.length; index += 1) {
        const current = parts[index];
        const previous = merged[merged.length - 1];
        if (current[0] <= previous[1] + 1e-10) {
            previous[1] = Math.max(previous[1], current[1]);
        } else {
            merged.push(current.slice());
        }
    }
    return merged;
}

function reachableIntervals(search, profileIndex, budget) {
    const intervals = [];
    for (let segmentId = 0; segmentId < graph.segmentCount; segmentId += 1) {
        const a = graph.segmentA[segmentId];
        const b = graph.segmentB[segmentId];
        const weightAb = edgeWeight(profileIndex, directedEdge(a, b));
        const weightBa = edgeWeight(profileIndex, directedEdge(b, a));
        const parts = [];

        if (search.distances[a] < budget && Number.isFinite(weightAb) && weightAb > 0) {
            addReachablePart(parts, 0, (budget - search.distances[a]) / weightAb);
        }
        if (search.distances[b] < budget && Number.isFinite(weightBa) && weightBa > 0) {
            addReachablePart(parts, 1 - (budget - search.distances[b]) / weightBa, 1);
        }

        if (segmentId === search.origin.segmentId) {
            if (Number.isFinite(search.originAb) && search.originAb > 0) {
                addReachablePart(
                    parts,
                    search.origin.t,
                    search.origin.t + budget / search.originAb
                );
            }
            if (Number.isFinite(search.originBa) && search.originBa > 0) {
                addReachablePart(
                    parts,
                    search.origin.t - budget / search.originBa,
                    search.origin.t
                );
            }
        }

        for (const [from, to] of mergedReachableParts(parts)) {
            intervals.push([
                interpolateSegment(a, b, from),
                interpolateSegment(a, b, to)
            ]);
        }
    }
    return intervals;
}

function projectCoordinate(coordinates, reference) {
    return [
        (coordinates[0] - reference.longitude) * reference.scaleX,
        (coordinates[1] - reference.latitude) * reference.scaleY
    ];
}

function unprojectCoordinate(coordinates, reference) {
    return [
        reference.longitude + coordinates[0] / reference.scaleX,
        reference.latitude + coordinates[1] / reference.scaleY
    ];
}

function isochroneGrid(intervals, originCoordinates) {
    const reference = {
        longitude: originCoordinates[0],
        latitude: originCoordinates[1],
        scaleX: DEG_TO_RAD * EARTH_RADIUS_M
            * Math.max(1e-6, Math.cos(originCoordinates[1] * DEG_TO_RAD)),
        scaleY: DEG_TO_RAD * EARTH_RADIUS_M
    };
    let coordinateMinX = 0;
    let coordinateMinY = 0;
    let coordinateMaxX = 0;
    let coordinateMaxY = 0;
    for (const interval of intervals) {
        for (const coordinates of interval) {
            const [x, y] = projectCoordinate(coordinates, reference);
            coordinateMinX = Math.min(coordinateMinX, x);
            coordinateMinY = Math.min(coordinateMinY, y);
            coordinateMaxX = Math.max(coordinateMaxX, x);
            coordinateMaxY = Math.max(coordinateMaxY, y);
        }
    }

    let cellSizeM = ISOCHRONE_CELL_SIZE_M;
    for (let attempt = 0; attempt < 12; attempt += 1) {
        const marginM = ISOCHRONE_BUFFER_M + cellSizeM * 2;
        const minX = Math.floor((coordinateMinX - marginM) / cellSizeM) * cellSizeM;
        const minY = Math.floor((coordinateMinY - marginM) / cellSizeM) * cellSizeM;
        const maxX = Math.ceil((coordinateMaxX + marginM) / cellSizeM) * cellSizeM;
        const maxY = Math.ceil((coordinateMaxY + marginM) / cellSizeM) * cellSizeM;
        const columns = Math.max(1, Math.round((maxX - minX) / cellSizeM));
        const rows = Math.max(1, Math.round((maxY - minY) / cellSizeM));
        const cellCount = columns * rows;
        if (cellCount <= ISOCHRONE_MAX_CELLS) {
            return {
                reference,
                minX,
                minY,
                maxX,
                maxY,
                columns,
                rows,
                cellSizeM
            };
        }
        cellSizeM *= Math.sqrt(cellCount / ISOCHRONE_MAX_CELLS) * 1.02;
    }
    throw new Error('Unable to fit isochrone raster within the cell limit');
}

function gridIndex(grid, x, y) {
    const column = clamp(Math.floor((x - grid.minX) / grid.cellSizeM), 0, grid.columns - 1);
    const row = clamp(Math.floor((y - grid.minY) / grid.cellSizeM), 0, grid.rows - 1);
    return row * grid.columns + column;
}

function rasterizeIntervals(intervals, grid) {
    const lineMask = new Uint8Array(grid.columns * grid.rows);
    for (const interval of intervals) {
        const [start, end] = interval.map(
            coordinates => projectCoordinate(coordinates, grid.reference)
        );
        const length = Math.hypot(end[0] - start[0], end[1] - start[1]);
        const steps = Math.max(1, Math.ceil(length / (grid.cellSizeM * 0.45)));
        for (let step = 0; step <= steps; step += 1) {
            const fraction = step / steps;
            const x = start[0] + fraction * (end[0] - start[0]);
            const y = start[1] + fraction * (end[1] - start[1]);
            lineMask[gridIndex(grid, x, y)] = 1;
        }
    }

    const result = new Uint8Array(lineMask.length);
    const radius = Math.max(1, Math.ceil(ISOCHRONE_BUFFER_M / grid.cellSizeM));
    const radiusSquared = (ISOCHRONE_BUFFER_M + grid.cellSizeM * 0.5) ** 2;
    for (let row = 0; row < grid.rows; row += 1) {
        for (let column = 0; column < grid.columns; column += 1) {
            if (!lineMask[row * grid.columns + column]) continue;
            for (let dy = -radius; dy <= radius; dy += 1) {
                const targetRow = row + dy;
                if (targetRow < 0 || targetRow >= grid.rows) continue;
                for (let dx = -radius; dx <= radius; dx += 1) {
                    const targetColumn = column + dx;
                    if (targetColumn < 0 || targetColumn >= grid.columns) continue;
                    if ((dx * grid.cellSizeM) ** 2 + (dy * grid.cellSizeM) ** 2 > radiusSquared) {
                        continue;
                    }
                    result[targetRow * grid.columns + targetColumn] = 1;
                }
            }
        }
    }
    return result;
}

function edgeKey(point) {
    return `${point[0]},${point[1]}`;
}

function ringArea(ring) {
    let area = 0;
    for (let index = 0; index < ring.length - 1; index += 1) {
        area += ring[index][0] * ring[index + 1][1]
            - ring[index + 1][0] * ring[index][1];
    }
    return area / 2;
}

function simplifyOrthogonalRing(ring) {
    if (ring.length <= 4) return ring;
    const open = ring.slice(0, -1);
    const simplified = [];
    for (let index = 0; index < open.length; index += 1) {
        const previous = open[(index + open.length - 1) % open.length];
        const current = open[index];
        const next = open[(index + 1) % open.length];
        const firstX = current[0] - previous[0];
        const firstY = current[1] - previous[1];
        const secondX = next[0] - current[0];
        const secondY = next[1] - current[1];
        if (firstX * secondY !== firstY * secondX) simplified.push(current);
    }
    if (simplified.length < 3) return ring;
    simplified.push(simplified[0]);
    return simplified;
}

function splitRingAtRepeatedVertices(ring) {
    const pending = [ring];
    const result = [];
    while (pending.length) {
        const candidate = pending.pop();
        const firstIndexes = new Map();
        let split = false;
        for (let index = 0; index < candidate.length - 1; index += 1) {
            const key = edgeKey(candidate[index]);
            if (!firstIndexes.has(key)) {
                firstIndexes.set(key, index);
                continue;
            }
            const firstIndex = firstIndexes.get(key);
            const firstRing = candidate.slice(firstIndex, index + 1);
            const secondRing = candidate
                .slice(0, firstIndex + 1)
                .concat(candidate.slice(index + 1));
            for (const part of [firstRing, secondRing]) {
                if (part.length >= 4 && Math.abs(ringArea(part)) > 0) {
                    pending.push(simplifyOrthogonalRing(part));
                }
            }
            split = true;
            break;
        }
        if (!split) result.push(candidate);
    }
    return result;
}

function pointInRing(point, ring) {
    let inside = false;
    for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index++) {
        const currentPoint = ring[index];
        const previousPoint = ring[previous];
        const intersects = (
            (currentPoint[1] > point[1]) !== (previousPoint[1] > point[1])
            && point[0] < (previousPoint[0] - currentPoint[0])
                * (point[1] - currentPoint[1])
                / (previousPoint[1] - currentPoint[1]) + currentPoint[0]
        );
        if (intersects) inside = !inside;
    }
    return inside;
}

function traceMaskRings(mask, grid) {
    const edges = [];
    const outgoing = new Map();
    const addEdge = (start, end) => {
        const edgeId = edges.length;
        edges.push({ start, end });
        const key = edgeKey(start);
        if (!outgoing.has(key)) outgoing.set(key, []);
        outgoing.get(key).push(edgeId);
    };
    const occupied = (column, row) => (
        column >= 0 && column < grid.columns
        && row >= 0 && row < grid.rows
        && Boolean(mask[row * grid.columns + column])
    );
    for (let row = 0; row < grid.rows; row += 1) {
        for (let column = 0; column < grid.columns; column += 1) {
            if (!occupied(column, row)) continue;
            if (!occupied(column, row - 1)) addEdge([column, row], [column + 1, row]);
            if (!occupied(column + 1, row)) addEdge([column + 1, row], [column + 1, row + 1]);
            if (!occupied(column, row + 1)) addEdge([column + 1, row + 1], [column, row + 1]);
            if (!occupied(column - 1, row)) addEdge([column, row + 1], [column, row]);
        }
    }

    const used = new Uint8Array(edges.length);
    const rings = [];
    for (let firstEdgeId = 0; firstEdgeId < edges.length; firstEdgeId += 1) {
        if (used[firstEdgeId]) continue;
        let edgeId = firstEdgeId;
        const ring = [edges[edgeId].start];
        while (!used[edgeId]) {
            used[edgeId] = 1;
            const edge = edges[edgeId];
            ring.push(edge.end);
            if (edgeKey(edge.end) === edgeKey(ring[0])) break;
            const candidates = (outgoing.get(edgeKey(edge.end)) || []).filter(
                candidate => !used[candidate]
            );
            if (!candidates.length) break;
            const incomingX = edge.end[0] - edge.start[0];
            const incomingY = edge.end[1] - edge.start[1];
            edgeId = candidates.reduce((best, candidate) => {
                const candidateEdge = edges[candidate];
                const candidateX = candidateEdge.end[0] - candidateEdge.start[0];
                const candidateY = candidateEdge.end[1] - candidateEdge.start[1];
                const turn = Math.atan2(
                    incomingX * candidateY - incomingY * candidateX,
                    incomingX * candidateX + incomingY * candidateY
                );
                return turn > best.turn ? { edgeId: candidate, turn } : best;
            }, { edgeId: candidates[0], turn: -Infinity }).edgeId;
        }
        if (
            ring.length >= 4
            && edgeKey(ring[0]) === edgeKey(ring[ring.length - 1])
        ) {
            rings.push(...splitRingAtRepeatedVertices(simplifyOrthogonalRing(ring)));
        }
    }
    return rings;
}

function maskToGeometry(mask, grid) {
    const rings = traceMaskRings(mask, grid);
    const outers = rings
        .filter(ring => ringArea(ring) > 0)
        .map(ring => ({ ring, holes: [], area: ringArea(ring) }));
    const holes = rings.filter(ring => ringArea(ring) < 0);
    for (const hole of holes) {
        const start = hole[0];
        const end = hole[1];
        const dx = end[0] - start[0];
        const dy = end[1] - start[1];
        const length = Math.hypot(dx, dy);
        // Hole rings are clockwise. A small offset to the right of one edge is
        // guaranteed to lie in the empty cell, unlike a concave ring's centroid.
        const point = [
            (start[0] + end[0]) / 2 + dy / length * 0.25,
            (start[1] + end[1]) / 2 - dx / length * 0.25
        ];
        const container = outers
            .filter(outer => pointInRing(point, outer.ring))
            .sort((left, right) => left.area - right.area)[0];
        if (container) container.holes.push(hole);
    }
    const convertRing = ring => ring.map(([column, row]) => unprojectCoordinate([
        grid.minX + column * grid.cellSizeM,
        grid.minY + row * grid.cellSizeM
    ], grid.reference));
    const polygons = outers.map(outer => [
        convertRing(outer.ring),
        ...outer.holes.map(convertRing)
    ]);
    if (!polygons.length) return null;
    return polygons.length === 1
        ? { type: 'Polygon', coordinates: polygons[0] }
        : { type: 'MultiPolygon', coordinates: polygons };
}

function isochroneRequest({ origin: rawOrigin, profileId, speedKmh, cutoffsMinutes }) {
    requireGraph();
    const profileIndex = profileIndexes.get(profileId);
    if (profileIndex === undefined) throw new Error(`Unknown routing profile: ${profileId}`);
    const speed = Number(speedKmh);
    if (!Number.isFinite(speed) || speed <= 0) {
        throw new Error('Isochrone profile speed must be positive.');
    }
    const cutoffs = normalizeIsochroneCutoffs(cutoffsMinutes);
    const equivalentMetersPerMinute = speed * 1000 / 60;
    const maximumWeight = cutoffs[cutoffs.length - 1] * equivalentMetersPerMinute;
    const search = boundedDistancesFromOrigin(rawOrigin, profileIndex, maximumWeight);
    const intervalsByCutoff = cutoffs.map(minutes => reachableIntervals(
        search,
        profileIndex,
        minutes * equivalentMetersPerMinute
    ));
    const outerIntervals = intervalsByCutoff[intervalsByCutoff.length - 1];
    if (!outerIntervals.length) {
        return {
            type: 'FeatureCollection',
            features: [],
            metadata: {
                origin: search.origin.coordinates,
                profile_id: profileId,
                speed_kmh: speed,
                cutoffs_minutes: cutoffs,
                time_semantics: 'accessibility_adjusted',
                direction: 'outbound',
                visited_nodes: search.visitedNodes
            }
        };
    }

    const grid = isochroneGrid(outerIntervals, search.origin.coordinates);
    let previousMask = null;
    const features = [];
    for (let index = 0; index < cutoffs.length; index += 1) {
        const minutes = cutoffs[index];
        const mask = rasterizeIntervals(intervalsByCutoff[index], grid);
        if (previousMask) {
            for (let cell = 0; cell < mask.length; cell += 1) {
                if (previousMask[cell]) mask[cell] = 1;
            }
        }
        previousMask = mask;
        const geometry = maskToGeometry(mask, grid);
        if (!geometry) continue;
        features.push({
            type: 'Feature',
            properties: {
                minutes,
                profile_id: profileId,
                speed_kmh: speed,
                time_semantics: 'accessibility_adjusted',
                direction: 'outbound',
                budget_equivalent_m: Math.round(minutes * equivalentMetersPerMinute * 100) / 100,
                approximate: true
            },
            geometry
        });
    }
    return {
        type: 'FeatureCollection',
        features,
        metadata: {
            origin: search.origin.coordinates,
            profile_id: profileId,
            speed_kmh: speed,
            cutoffs_minutes: cutoffs,
            time_semantics: 'accessibility_adjusted',
            direction: 'outbound',
            visited_nodes: search.visitedNodes,
            polygonization: {
                method: 'rasterized_reachable_network_buffer',
                cell_size_m: Math.round(grid.cellSizeM * 100) / 100,
                buffer_m: ISOCHRONE_BUFFER_M
            }
        }
    };
}
