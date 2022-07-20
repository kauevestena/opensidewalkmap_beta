import sys,csv
# import pandas as pd
import geopandas as gpd
from quality_dicts import *
sys.path.append('.')
from functions import *

def add_to_occurrences(category,id):
    if id in occurrence_per_feature[category]:
        occurrence_per_feature[category][id] += 1
    else:
        occurrence_per_feature[category][id] = 1

# gdfs:
sidewalks_gdf = gpd.read_file('data/sidewalks_raw.geojson')
crossings_gdf = gpd.read_file('data/crossings_raw.geojson')
kerbs_gdf = gpd.read_file('data/kerbs_raw.geojson')

# dict for iteration
gdf_dict = {'sidewalks':sidewalks_gdf,'crossings':crossings_gdf,'kerbs':kerbs_gdf}

type_dict = {'sidewalks':'way','crossings':'way','kerbs':'node'}

# reading 
existing_keys = read_json('quality_check/feature_keys.json')


# iterating through feature categories:
for category in gdf_dict:
    print('for: ',category)
    for i,row in enumerate(gdf_dict[category].itertuples()):

        if i % 50 == 0:
            print('    ',i, ' features')

        # iterating through quality categories:
        for quality_category in categories_dict_keys:

            # using an alias to create a shortcut:
            curr = categories_dict_keys[quality_category]
            
            if curr['type'] == 'keys':
                if isinstance(curr['dict'],dict):

                    for osmkey in curr['dict'][category]:
                        value = getattr(row,osmkey,None)

                        if value:
                            curr['occurrences'][category].append([row.id,osmkey,value,curr['dict'][category][osmkey]])


                            curr['occ_count'][category] += 1

                            add_to_occurrences(category,row.id)

                if isinstance(curr['dict'],str):
                    curr_ref_dict = read_json(curr['dict'])[category]

                    for osmkey in curr_ref_dict:

                        value = getattr(row,osmkey,None)

                        if value:
                            print(value)

                            curr['occurrences'][category].append([row.id,osmkey,value,'no wiki page for this key'])


                            curr['occ_count'][category] += 1

                            add_to_occurrences(category,row.id)



                




            if curr['type'] == 'values':
                if isinstance(curr['dict'],dict):
                    for osmkey in curr['dict'][category]:
                        for osmvalue in curr['dict'][category][osmkey]:
                            if getattr(row,osmkey,None) == osmvalue:
                                curr['occurrences'][category].append([row.id,osmkey,osmvalue,curr['dict'][category][osmkey][osmvalue]])

                                curr['occ_count'][category] += 1


                                add_to_occurrences(category,row.id)

                if isinstance(curr['dict'],str):
                    curr_ref_dict = read_json(curr['dict'])[category]

                    for osmkey in curr_ref_dict:
                        for osmvalue in curr_ref_dict[osmkey]:
                            value = getattr(row,osmkey,None)

                            if value :
                                if value not in curr_ref_dict[osmkey]:

                                    curr['occurrences'][category].append([row.id,osmkey,value,'unlisted at accepted/known values, probably wrong/misspelled'])


                                    curr['occ_count'][category] += 1


                                    add_to_occurrences(category,row.id)



######### PART 2: files generation



# iterating again to generate the files:
for category in gdf_dict:
    for quality_category in categories_dict_keys:
        csvpath = f'quality_check/tables/{quality_category}_{category}.csv'

        pagepath = f'quality_check/pages/{quality_category}_{category}.html'



        curr = categories_dict_keys[quality_category]

        # print(quality_category['occurrences'])



        with open(csvpath,'w+') as file:
            writer = csv.writer(file,delimiter=',',quotechar='"')

            # header
            writer.writerow(['osm_id','key','value','commentary'])


            for line_as_list in curr['occurrences'][category]:
                # writer.write(','.join(list(map(str,linelist)))+'\n')


                writer.writerow(line_as_list)

        gen_quality_report_page(pagepath,curr['occurrences'][category],type_dict[category],category,quality_category,curr['about'],curr['type'])

    number_occ_pagepath  = f'quality_check/pages/count_by_feature_{category}.html'


    # THX: https://stackoverflow.com/a/613218/4436950
    sorted_occ_dict = dict(sorted(occurrence_per_feature[category].items(), key=lambda item: item[1],reverse=True))
    
    

    gen_quality_report_page(number_occ_pagepath,list(map(list,sorted_occ_dict.items())),type_dict[category],category,'occurrence_per_feature','Features with more than one occurrence may be prioritized!!','count',True)



######### PART 3: Quality Check Main page



# AGING PART:

# generate the "report" of the updating info
record_datetime('Quality Check of Tags')
sleep(.1)

gen_updating_infotable_page()
