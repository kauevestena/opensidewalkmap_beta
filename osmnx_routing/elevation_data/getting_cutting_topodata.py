# import subprocess

# cwb_img_link = '/vsizip//vsicurl/http://www.dsr.inpe.br/topodata/data/geotiff/25S495ZN.zip'

# # getting GDALINFO
# subprocess.run(f'gdalinfo {cwb_img_link}',shell=True)

# # using gdwalarp directly on web image:
# outpah = 'osmnx_routing/elevation_data/cwb_dtm.tif'

# # ,,

# runstring = f'gdalwarp -s_srs EPSG:4674 -t_srs EPSG:4326 -te -49.459076 -25.649573 -49.047775 -25.277608 -te_srs EPSG:4326 -overwrite {cwb_img_link} {outpah}'

# subprocess.run(runstring,shell=True)

'''

    done manually =P
    TODO

'''