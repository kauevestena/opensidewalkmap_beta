import sys,csv
# import pandas as pd
import geopandas as gpd
from quality_dicts import *
sys.path.append('.')
from oswm_codebase.functions import *

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
                            if not row.id in curr['occurrences'][category]:
                                val_list = [row.id,osmkey,value,curr['dict'][category][osmkey]]

                                curr['occurrences'][category][row.id] = val_list


                                curr['occ_count'][category] += 1

                                add_to_occurrences(category,row.id)


                if isinstance(curr['dict'],str):
                    curr_ref_dict = read_json(curr['dict'])[category]

                    for osmkey in curr_ref_dict:

                        value = getattr(row,osmkey,None)

                        if value:
                            if not row.id in curr['occurrences'][category]:

                                val_list = [row.id,osmkey,value,'no wiki page for this key']

                                curr['occurrences'][category][row.id] = val_list


                                curr['occ_count'][category] += 1

                                add_to_occurrences(category,row.id)



                




            if curr['type'] == 'values':
                if isinstance(curr['dict'],dict):
                    for osmkey in curr['dict'][category]:
                        for osmvalue in curr['dict'][category][osmkey]:
                            if getattr(row,osmkey,None) == osmvalue:
                                if not row.id in curr['occurrences'][category]:
                                
                                
                                    val_list = [row.id,osmkey,osmvalue,curr['dict'][category][osmkey][osmvalue]]
                                    
                                    
                                    curr['occurrences'][category][row.id] = val_list

                                    curr['occ_count'][category] += 1


                                    add_to_occurrences(category,row.id)


                if isinstance(curr['dict'],str):
                    curr_ref_dict = read_json(curr['dict'])[category]

                    for osmkey in curr_ref_dict:
                        for osmvalue in curr_ref_dict[osmkey]:
                            value = getattr(row,osmkey,None)

                            if value :
                                if value not in curr_ref_dict[osmkey]:
                                     if not row.id in curr['occurrences'][category]:



                                        val_list = [row.id,osmkey,value,'unlisted at accepted/known values, probably wrong/misspelled']

                                        curr['occurrences'][category][row.id] = val_list


                                        curr['occ_count'][category] += 1


                                        add_to_occurrences(category,row.id)

            if curr['type'] == 'tags':

                for character in curr['dict']:
                    for field in row:
                        if isinstance(field,str):
                            if character in field:
                                val_list = [row.id,'ANY (check at feature link)',field,curr['dict'][character]]

                                curr['occurrences'][category][row.id] = val_list


                                curr['occ_count'][category] += 1


                                add_to_occurrences(category,row.id)

                                break




    



######### PART 2: files generation

print('generating subpages and files')

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


            for line_as_list in curr['occurrences'][category].values():
                # writer.write(','.join(list(map(str,linelist)))+'\n')


                writer.writerow(line_as_list)

        gen_quality_report_page(pagepath,list(curr['occurrences'][category].values()),type_dict[category],category,quality_category,curr['about'],curr['type'])

    number_occ_pagepath  = f'quality_check/pages/count_by_feature_{category}.html'


    # THX: https://stackoverflow.com/a/613218/4436950
    sorted_occ_dict = dict(sorted(occurrence_per_feature[category].items(), key=lambda item: item[1],reverse=True))
    
    

    gen_quality_report_page(number_occ_pagepath,list(map(list,sorted_occ_dict.items())),type_dict[category],category,'occurrence_per_feature','Features with more than one occurrence may be prioritized!!','count',True)



######### PART 3: Quality Check Main page

print('generating QC main page')

tablepart = """

    <tr>
    <th><b>Category</b></th>
    <th><b>Sidewalks</b></th>
    <th><b>Crossings</b></th>
    <th><b>Kerbs</b></th>

    
    </tr>

"""

about_part = """
<h3>

"""


for quality_category in categories_dict_keys:

    tablepart += "<tr>"

    tablepart += f"<td>{quality_category}</td>"


    for category in gdf_dict:

        tablepart += f'<td>  <a href="https://kauevestena.github.io/opensidewalkmap_beta/quality_check/pages/{quality_category}_{category}.html"> {categories_dict_keys[quality_category]["occ_count"][category]} </a> </td>'

    
    tablepart += "</tr>\n"

    about_part += f"{quality_category} : {categories_dict_keys[quality_category]['about']}<br>\n"

about_part += "</h3>"


        




qc_mainpage_path = 'quality_check/oswm_qc_main.html'

qcmainpage_txt = f"""

<!DOCTYPE html>

<!-- thx, w3schools, this page was made following their tutorial!! -->

<html lang="en">
<head>
    

{FONT_STYLE}

{TABLES_STYLE}

<style>

h3 {{
    font-size :  16px;
    text-align: left;
    text-align: left;


}}

h2 {{
    font-size :  25px;

}}

h1 {{
    text-align:center;
    font-size :  30px;
}}


</style>

<title>OpenSidewalkMap Data Quality Tool</title>

<link rel="icon" type="image/x-icon" href="../assets/homepage/favicon_homepage.png">

<body>

<h1>OpenSidewalkMap Data Quality Tool</h1>

<p>
This Section is dedicated to find errors in the Features of interest in the Context of OSWM project.<br>
In some cases it's a clear mistake, but it can be just a mispelling or an uncommon value<br><br>

currently, there are the categories presented at the table,<br> each one with the number of occurrences that are item-wise detailed at each link<br>
<a href="https://github.com/kauevestena/opensidewalkmap_beta/issues">you can post suggestions at repo "issues" section</a>

</p>

<table>

{tablepart}


</table>

<p>
The information here can be <b>outdated</b><br>
<a href="https://kauevestena.github.io/opensidewalkmap_beta/data/data_updating.html">here you can check the last update and read more about this</a>
<br>
</p>

<h2>About Each category: </h2>

{about_part}


<p>
in a future topological and geometric errors may be included!! 
</p>

</body>
</html> 

"""

with open(qc_mainpage_path,'w+') as writer:
    writer.write(qcmainpage_txt)


# AGING PART:

# generate the "report" of the updating info
record_datetime("Data Quality Tool")
sleep(.1)

gen_updating_infotable_page()
