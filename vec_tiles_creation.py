'''
    Creating vectorial tilesets to use github/pages as a tileserver

'''

from constants import *
import subprocess

# other max zoom to override:
max_zoom = 20


# once for each layer
for layername in fields_values_properties.keys():

    inputpath = paths_dict['data'][layername]

    outputpath = f'tiles/vector/{layername}'
    
    run_string = f'{OGR2OGR_PATH} -append -update -f "MVT" -dsco MINZOOM={min_zoom} -dsco MAXZOOM={max_zoom} {outputpath} {inputpath}'

    print(run_string)

    subprocess.run(run_string,shell=True)
