import bs4
from time import sleep, time
import pandas as pd
from datetime import datetime 
import json

"""

    TIME STUFF

"""

def formatted_datetime_now():
    now = datetime.now()
    return now.strftime("%d/%m/%Y %H:%M:%S")

def read_json(inputpath):
    with open(inputpath) as reader:
        data = reader.read()

    return json.loads(data)
    
def dump_json(inputdict,outputpath):
    with open(outputpath,'w+') as json_handle:
        json.dump(inputdict,json_handle)

def record_datetime(key,json_path='data/last_updated.json'):

    datadict = read_json(json_path)

    datadict[key] = formatted_datetime_now()

    dump_json(datadict,json_path)



"""

    HTML STUFF

"""

def gen_updatingg_infotable_page(outpath='data/data_updating.html',json_path='data/last_updated.json'):


    tablepart = ''

    records_dict = read_json(json_path)

    for key in records_dict:
        tablepart += f"<tr><th><b>{key}</b></th><th>{records_dict[key]}</th></tr>"

    page_as_txt = f'''
    <!DOCTYPE html>
<html>
<head>
<title>OSWM Updating Info</title>


<style>


h1 {{text-align: center;}}



table {{
  font-family: arial, sans-serif;
  border-collapse: collapse;
  width: 100%;
}}

td, th {{
  border: 1px solid #dddddd;
  text-align: left;
  padding: 8px;
}}

tr:nth-child(even) {{
  background-color: #dddddd;
}}
</style>
</head>
<body>

<h1>OSWM Updating Info</h1>

<table>

{tablepart}

</table>

</body>
</html>    
    '''

    with open(outpath,'w+') as writer:
        writer.write(page_as_txt)

def find_html_name(input_htmlpath,specific_ref,tag_ref='img',specific_tag='src',identifier='id'):

    with open(input_htmlpath) as inf:
        txt = inf.read()
        soup = bs4.BeautifulSoup(txt,features='lxml')

    image_refs = soup.find_all(tag_ref)

    for found_imref in image_refs:

        if found_imref[specific_tag] == specific_ref:
            return found_imref[identifier]
            

def style_changer(in_out_htmlpath,img_key,key='style',original='bottom',new='top',append=None):
    with open(in_out_htmlpath) as inf:
        txt = inf.read()
        soup = bs4.BeautifulSoup(txt,features='lxml')

    style_refs = soup.find_all(key)

    for style_ref in style_refs:
        as_txt = style_ref.get_text()
        if img_key in as_txt:

            if new:
                new_text = as_txt.replace(original,new)
            else:
                new_text = as_txt

            if append:
                new_text += append

            break


    with open(in_out_htmlpath,'w+', encoding='utf-8') as writer:
        writer.write(str(soup).replace(as_txt,new_text))

    sleep(0.2)

        
def add_to_page_after_first_tag(html_filepath,element_string,tag_or_txt='<head>',count=1):
    '''
    Quick and dirty way to insert some stuff directly on the webpage 

    Originally intended only for <head>

    beware of tags that repeat! the "count" argument is very important!
    '''


    with open(html_filepath) as reader:
        pag_txt = reader.read()

    replace_text = f'{tag_or_txt} \n{element_string}\n'

    
    with open(html_filepath,'w+') as writer:
        writer.write(pag_txt.replace(tag_or_txt,replace_text,count))

    sleep(.1)
    


# (geo)Pandas stuff:
def get_score_df(inputdict,category='sidewalks',osm_key='surface',input_field='score_default',output_field_base='score'):

    output_field_name = f'{category}_{osm_key}_{output_field_base}'
    dict = {osm_key:[],output_field_name:[]}

    for val_key in inputdict[category][osm_key]:
        dict[osm_key].append(val_key)
        dict[output_field_name].append(inputdict[category][osm_key][val_key][input_field])

    return  pd.DataFrame(dict), output_field_name


def get_attr_dict(inputdict,category='sidewalks',osm_tag='surface',attr='color'):
    color_dict = {}
    for tag_value in inputdict[category][osm_tag]:
        color_dict[tag_value] = inputdict[category][osm_tag][tag_value][attr]

    return color_dict

def return_weblink_way(string_id):
    return f"<a href=https://www.openstreetmap.org/way/{string_id}>{string_id}</a>"

def return_weblink_node(string_id):
    return f"<a href=https://www.openstreetmap.org/node/{string_id}>{string_id}</a>"