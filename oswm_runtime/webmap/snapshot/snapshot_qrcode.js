/**
 * Minimal QR Code SVG generator for snapshot print sheets.
 *
 * Produces a QR code as an inline SVG string.  Supports byte-mode encoding
 * with error correction level M (15 % recovery).  Designed for short URLs
 * (≤ 100 characters) — the typical OSWM webmap URL with hash.
 *
 * No external dependencies.
 *
 * @module snapshot_qrcode
 */

/* ------------------------------------------------------------------ */
/*  Galois-field arithmetic over GF(256) with polynomial 0x11d        */
/* ------------------------------------------------------------------ */

const EXP = new Uint8Array(512);
const LOG = new Uint8Array(256);
{
    let x = 1;
    for (let i = 0; i < 255; i++) {
        EXP[i] = x;
        LOG[x] = i;
        x = (x << 1) ^ (x & 128 ? 0x11d : 0);
    }
    for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
}

function gfMul(a, b) {
    return a && b ? EXP[LOG[a] + LOG[b]] : 0;
}

/* ------------------------------------------------------------------ */
/*  Reed–Solomon error-correction codeword generation                 */
/* ------------------------------------------------------------------ */

function rsGenPoly(ecCount) {
    let poly = [1];
    for (let i = 0; i < ecCount; i++) {
        const next = new Array(poly.length + 1).fill(0);
        for (let j = 0; j < poly.length; j++) {
            next[j] ^= poly[j];
            next[j + 1] ^= gfMul(poly[j], EXP[i]);
        }
        poly = next;
    }
    return poly;
}

function rsEncode(data, ecCount) {
    const gen = rsGenPoly(ecCount);
    const result = new Array(ecCount).fill(0);
    for (const byte of data) {
        const lead = byte ^ result[0];
        for (let i = 0; i < ecCount - 1; i++) {
            result[i] = result[i + 1] ^ gfMul(gen[i + 1], lead);
        }
        result[ecCount - 1] = gfMul(gen[ecCount], lead);
    }
    return result;
}

/* ------------------------------------------------------------------ */
/*  QR version / capacity tables (versions 1-10, EC level M)          */
/* ------------------------------------------------------------------ */

// [totalCodewords, ecCodewordsPerBlock, numBlocks]
const VERSION_TABLE_M = [
    null, // v0 placeholder
    [26, 10, 1],    // v1
    [44, 16, 1],    // v2
    [70, 26, 1],    // v3
    [100, 18, 2],   // v4
    [134, 24, 2],   // v5
    [172, 16, 4],   // v6
    [196, 18, 4],   // v7 — was incorrectly listed as [196,18,2] in some refs
    [242, 22, 4],   // v8  — mixed block structure simplified
    [292, 22, 4],   // v9  — mixed block structure simplified
    [346, 26, 4],   // v10 — mixed block structure simplified
];

function selectVersion(dataBytes) {
    for (let v = 1; v <= 10; v++) {
        const [total, ecPerBlock, blocks] = VERSION_TABLE_M[v];
        const dataCapacity = total - ecPerBlock * blocks;
        if (dataCapacity >= dataBytes) return v;
    }
    throw new Error(`QR data too long (${dataBytes} bytes); max supported ≈ 190 bytes.`);
}

/* ------------------------------------------------------------------ */
/*  Data encoding (byte mode, EC level M)                             */
/* ------------------------------------------------------------------ */

function encodeData(text) {
    const bytes = new TextEncoder().encode(text);
    const version = selectVersion(bytes.length + 3); // mode(4) + count(8/16) + terminator overhead
    const [totalCW, ecPerBlock, numBlocks] = VERSION_TABLE_M[version];
    const dataCW = totalCW - ecPerBlock * numBlocks;

    // Bit stream
    const bits = [];
    const push = (value, count) => {
        for (let i = count - 1; i >= 0; i--) bits.push((value >> i) & 1);
    };

    push(0b0100, 4); // byte-mode indicator
    push(bytes.length, version >= 10 ? 16 : 8); // character count
    for (const b of bytes) push(b, 8);
    push(0, Math.min(4, dataCW * 8 - bits.length)); // terminator
    while (bits.length % 8) bits.push(0); // byte-align

    // Pad codewords
    const codewords = [];
    for (let i = 0; i < bits.length; i += 8) {
        codewords.push(bits.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
    }
    const padBytes = [0xec, 0x11];
    let padIdx = 0;
    while (codewords.length < dataCW) {
        codewords.push(padBytes[padIdx]);
        padIdx ^= 1;
    }

    // Split into blocks and compute EC
    const blockSize = Math.floor(dataCW / numBlocks);
    const longBlocks = dataCW % numBlocks;
    const dataBlocks = [];
    const ecBlocks = [];
    let offset = 0;
    for (let b = 0; b < numBlocks; b++) {
        const size = blockSize + (b >= numBlocks - longBlocks ? 1 : 0);
        const block = codewords.slice(offset, offset + size);
        dataBlocks.push(block);
        ecBlocks.push(rsEncode(block, ecPerBlock));
        offset += size;
    }

    // Interleave
    const interleaved = [];
    const maxDataLen = blockSize + (longBlocks ? 1 : 0);
    for (let i = 0; i < maxDataLen; i++) {
        for (const block of dataBlocks) {
            if (i < block.length) interleaved.push(block[i]);
        }
    }
    for (let i = 0; i < ecPerBlock; i++) {
        for (const block of ecBlocks) interleaved.push(block[i]);
    }

    return { version, codewords: interleaved };
}

/* ------------------------------------------------------------------ */
/*  Module placement                                                  */
/* ------------------------------------------------------------------ */

function createMatrix(version) {
    const size = version * 4 + 17;
    // 0 = unset, 1 = dark, 2 = light, 3 = reserved-dark, 4 = reserved-light
    const matrix = Array.from({ length: size }, () => new Uint8Array(size));
    return matrix;
}

function setModule(matrix, row, col, dark, reserved = false) {
    if (row >= 0 && row < matrix.length && col >= 0 && col < matrix.length) {
        matrix[row][col] = reserved ? (dark ? 3 : 4) : (dark ? 1 : 2);
    }
}

function placeFinderPattern(matrix, row, col) {
    for (let r = -1; r <= 7; r++) {
        for (let c = -1; c <= 7; c++) {
            const inOuter = r >= 0 && r <= 6 && c >= 0 && c <= 6;
            const inInner = r >= 2 && r <= 4 && c >= 2 && c <= 4;
            const onBorder = r === 0 || r === 6 || c === 0 || c === 6;
            const dark = inInner || (inOuter && onBorder);
            setModule(matrix, row + r, col + c, dark, true);
        }
    }
}

function placeAlignmentPattern(matrix, row, col) {
    for (let r = -2; r <= 2; r++) {
        for (let c = -2; c <= 2; c++) {
            const dark = Math.max(Math.abs(r), Math.abs(c)) !== 1;
            if (matrix[row + r][col + c] === 0) {
                setModule(matrix, row + r, col + c, dark, true);
            }
        }
    }
}

const ALIGNMENT_POSITIONS = [
    null, [], [], [], [], [],
    [6, 34],    // v6
    [6, 22, 38], // v7
    [6, 24, 42], // v8
    [6, 26, 46], // v9
    [6, 28, 52], // v10
];

function placeTimingPatterns(matrix) {
    const size = matrix.length;
    for (let i = 8; i < size - 8; i++) {
        if (!matrix[6][i]) setModule(matrix, 6, i, i % 2 === 0, true);
        if (!matrix[i][6]) setModule(matrix, i, 6, i % 2 === 0, true);
    }
}

function reserveFormatBits(matrix) {
    const size = matrix.length;
    // Around top-left finder
    for (let i = 0; i <= 8; i++) {
        if (!matrix[8][i]) setModule(matrix, 8, i, false, true);
        if (!matrix[i][8]) setModule(matrix, i, 8, false, true);
    }
    // Around top-right finder
    for (let i = 0; i <= 7; i++) {
        if (!matrix[8][size - 1 - i]) setModule(matrix, 8, size - 1 - i, false, true);
    }
    // Around bottom-left finder
    for (let i = 0; i <= 7; i++) {
        if (!matrix[size - 1 - i][8]) setModule(matrix, size - 1 - i, 8, false, true);
    }
    // Dark module
    setModule(matrix, size - 8, 8, true, true);
}

function placeDataBits(matrix, codewords) {
    const size = matrix.length;
    const bits = [];
    for (const cw of codewords) {
        for (let i = 7; i >= 0; i--) bits.push((cw >> i) & 1);
    }
    let bitIdx = 0;
    let upward = true;
    for (let right = size - 1; right >= 1; right -= 2) {
        if (right === 6) right = 5; // skip timing column
        const rows = upward
            ? Array.from({ length: size }, (_, i) => size - 1 - i)
            : Array.from({ length: size }, (_, i) => i);
        for (const row of rows) {
            for (const col of [right, right - 1]) {
                if (matrix[row][col] === 0) {
                    const dark = bitIdx < bits.length ? bits[bitIdx] : 0;
                    matrix[row][col] = dark ? 1 : 2;
                    bitIdx++;
                }
            }
        }
        upward = !upward;
    }
}

/* ------------------------------------------------------------------ */
/*  Masking and format info                                           */
/* ------------------------------------------------------------------ */

const MASK_FUNCTIONS = [
    (r, c) => (r + c) % 2 === 0,
    (r, c) => r % 2 === 0,
    (r, c) => c % 3 === 0,
    (r, c) => (r + c) % 3 === 0,
    (r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
    (r, c) => ((r * c) % 2 + (r * c) % 3) === 0,
    (r, c) => ((r * c) % 2 + (r * c) % 3) % 2 === 0,
    (r, c) => ((r + c) % 2 + (r * c) % 3) % 2 === 0,
];

// Format info strings for EC level M (binary 00) with each mask pattern
// Pre-computed BCH(15,5) with mask 0x5412
const FORMAT_INFO = [
    0x5412 ^ 0b101010000010010, // mask 0
    0x5412 ^ 0b101000100100101,
    0x5412 ^ 0b101111001111100,
    0x5412 ^ 0b101101101001011,
    0x5412 ^ 0b100010011010110,
    0x5412 ^ 0b100000111100001,
    0x5412 ^ 0b100111010111000,
    0x5412 ^ 0b100101110001111,
];

// Actually pre-compute correctly:
function computeFormatInfo(ecLevel, mask) {
    // EC level M = 0, L = 1, H = 2, Q = 3
    // For level M, indicator is 00
    const data = (ecLevel << 3) | mask;
    let rem = data;
    for (let i = 0; i < 10; i++) {
        rem = (rem << 1) ^ ((rem >> 9) ? 0b10100110111 : 0);
    }
    return ((data << 10) | rem) ^ 0b101010000010010;
}

function applyMask(matrix, maskIdx) {
    const size = matrix.length;
    const masked = matrix.map((row) => new Uint8Array(row));
    const fn = MASK_FUNCTIONS[maskIdx];
    for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
            const val = masked[r][c];
            if (val === 1 || val === 2) { // only data modules
                if (fn(r, c)) {
                    masked[r][c] = val === 1 ? 2 : 1;
                }
            }
        }
    }
    // Write format info
    const info = computeFormatInfo(0, maskIdx); // EC level M = 0
    // Around top-left
    const formatPositions = [
        // horizontal (row 8, cols 0-7 skipping col 6)
        [8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8],
        // vertical (col 8, rows 7-0 skipping row 6)
        [7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8],
    ];
    for (let i = 0; i < 15; i++) {
        const dark = (info >> (14 - i)) & 1;
        if (i < formatPositions.length) {
            const [r, c] = formatPositions[i];
            masked[r][c] = dark ? 3 : 4;
        }
    }
    // Right of top-left (row 8, cols size-8 to size-1)
    for (let i = 0; i < 8; i++) {
        const dark = (info >> i) & 1;
        masked[8][size - 1 - i] = dark ? 3 : 4;
    }
    // Below top-left (col 8, rows size-7 to size-1)
    for (let i = 0; i < 7; i++) {
        const dark = (info >> (14 - 8 - i)) & 1;
        masked[size - 7 + i][8] = dark ? 3 : 4;
    }
    return masked;
}

function penaltyScore(matrix) {
    const size = matrix.length;
    const isDark = (r, c) => {
        const v = matrix[r][c];
        return v === 1 || v === 3;
    };
    let penalty = 0;

    // Rule 1: runs of same color
    for (let r = 0; r < size; r++) {
        let run = 1;
        for (let c = 1; c < size; c++) {
            if (isDark(r, c) === isDark(r, c - 1)) {
                run++;
                if (run === 5) penalty += 3;
                else if (run > 5) penalty += 1;
            } else {
                run = 1;
            }
        }
    }
    for (let c = 0; c < size; c++) {
        let run = 1;
        for (let r = 1; r < size; r++) {
            if (isDark(r, c) === isDark(r - 1, c)) {
                run++;
                if (run === 5) penalty += 3;
                else if (run > 5) penalty += 1;
            } else {
                run = 1;
            }
        }
    }

    // Rule 2: 2×2 blocks
    for (let r = 0; r < size - 1; r++) {
        for (let c = 0; c < size - 1; c++) {
            const d = isDark(r, c);
            if (d === isDark(r, c + 1) && d === isDark(r + 1, c) && d === isDark(r + 1, c + 1)) {
                penalty += 3;
            }
        }
    }

    // Rule 4: proportion
    let darkCount = 0;
    for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
            if (isDark(r, c)) darkCount++;
        }
    }
    const pct = (darkCount * 100) / (size * size);
    const prev5 = Math.floor(pct / 5) * 5;
    const next5 = prev5 + 5;
    penalty += Math.min(Math.abs(prev5 - 50), Math.abs(next5 - 50)) * 2;

    return penalty;
}

function bestMask(matrix) {
    let best = 0;
    let bestScore = Infinity;
    for (let m = 0; m < 8; m++) {
        const masked = applyMask(matrix, m);
        const score = penaltyScore(masked);
        if (score < bestScore) {
            bestScore = score;
            best = m;
        }
    }
    return best;
}

/* ------------------------------------------------------------------ */
/*  Public API                                                        */
/* ------------------------------------------------------------------ */

/**
 * Generate a QR code as an inline SVG string.
 *
 * @param {string} text  The text to encode (typically a URL).
 * @param {object} [options]
 * @param {number} [options.size=80]    Width/height of the SVG in CSS pixels.
 * @param {number} [options.margin=2]   Quiet-zone modules around the code.
 * @param {string} [options.dark="#111"]   Colour for dark modules.
 * @param {string} [options.light="#fff"]  Colour for light modules.
 * @returns {string} SVG markup string.
 */
export function qrcodeSvg(text, { size = 80, margin = 2, dark = "#111", light = "#fff" } = {}) {
    const { version, codewords } = encodeData(text);
    const matrix = createMatrix(version);
    const matrixSize = matrix.length;

    // Place function patterns
    placeFinderPattern(matrix, 0, 0);
    placeFinderPattern(matrix, 0, matrixSize - 7);
    placeFinderPattern(matrix, matrixSize - 7, 0);

    // Alignment patterns (version ≥ 2)
    const alignPos = ALIGNMENT_POSITIONS[version] || [];
    if (alignPos.length) {
        for (const r of alignPos) {
            for (const c of alignPos) {
                // Skip if overlapping finder patterns
                if (r <= 8 && c <= 8) continue;
                if (r <= 8 && c >= matrixSize - 8) continue;
                if (r >= matrixSize - 8 && c <= 8) continue;
                placeAlignmentPattern(matrix, r, c);
            }
        }
    }

    placeTimingPatterns(matrix);
    reserveFormatBits(matrix);
    placeDataBits(matrix, codewords);

    const maskIdx = bestMask(matrix);
    const finalMatrix = applyMask(matrix, maskIdx);

    // Render SVG
    const totalModules = matrixSize + margin * 2;
    const paths = [];
    for (let r = 0; r < matrixSize; r++) {
        for (let c = 0; c < matrixSize; c++) {
            const v = finalMatrix[r][c];
            if (v === 1 || v === 3) {
                paths.push(`M${c + margin},${r + margin}h1v1h-1z`);
            }
        }
    }

    return [
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${totalModules} ${totalModules}"`,
        ` width="${size}" height="${size}" shape-rendering="crispEdges">`,
        `<rect width="${totalModules}" height="${totalModules}" fill="${light}"/>`,
        `<path d="${paths.join("")}" fill="${dark}"/>`,
        `</svg>`,
    ].join("");
}
