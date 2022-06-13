# DEALING DIRECTLY WITH THE HTML FILE:
# from xml.etree.ElementPath import find
import bs4

page_name = 'index.html'
img_addr = 'assets/are_sidewalks_acessible_typog.png'

# thx: https://stackoverflow.com/a/35355433/4436950
# load  file
with open(page_name) as inf:
    txt = inf.read()
    soup = bs4.BeautifulSoup(txt,features='lxml')


image_refs = soup.find_all('img')

img_html_name = ''

for found_imref in image_refs:

    if found_imref['src'] == img_addr:
        img_html_name = found_imref['id']

style_refs = soup.find_all('style')

for style_ref in style_refs:
    as_txt = style_ref.get_text()
    if img_html_name in as_txt:
        new_text = as_txt.replace('bottom','top')
        print(as_txt)

        # style_ref.replaceWith(as_txt)

        print(style_ref)

        break


with open(page_name,'w+', encoding='utf-8') as writer:
    writer.write(str(soup).replace(as_txt,new_text))


