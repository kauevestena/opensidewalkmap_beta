import bs4
from time import sleep
import pandas as pd

def find_html_name(input_htmlpath,specific_ref,tag_ref='img',specific_tag='src',identifier='id'):

    with open(input_htmlpath) as inf:
        txt = inf.read()
        soup = bs4.BeautifulSoup(txt,features='lxml')

    image_refs = soup.find_all(tag_ref)

    for found_imref in image_refs:

        if found_imref[specific_tag] == specific_ref:
            return found_imref[identifier]
            

def style_changer(in_out_htmlpath,img_key,key='style',original='bottom',new='top'):
    with open(in_out_htmlpath) as inf:
        txt = inf.read()
        soup = bs4.BeautifulSoup(txt,features='lxml')

    style_refs = soup.find_all(key)

    for style_ref in style_refs:
        as_txt = style_ref.get_text()
        if img_key in as_txt:
            new_text = as_txt.replace(original,new)

            break


    with open(in_out_htmlpath,'w+', encoding='utf-8') as writer:
        writer.write(str(soup).replace(as_txt,new_text))

    sleep(0.2)

        
        
def get_score_df(inputdict,category='sidewalks',osm_key='surface',input_field='score_default',output_field_base='score'):

    output_field_name = f'{category}_{osm_key}_{output_field_base}'
    dict = {osm_key:[],output_field_name:[]}

    for val_key in inputdict[category][osm_key]:
        dict[osm_key].append(val_key)
        dict[output_field_name].append(inputdict[category][osm_key][val_key][input_field])

    return  pd.DataFrame(dict), output_field_name