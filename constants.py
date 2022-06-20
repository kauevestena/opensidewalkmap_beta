# intended for common values

# hmtml file name
page_name = "index.html"

# data names
sidewalks_path = 'data/sidewalks.geojson'
crossings_path = 'data/crossings.geojson' 
kerbs_path = 'data/kerbs.geojson'

# # the ten block sample
bounding_box_sample = (-25.46340831586,-49.26485433156466,-25.45836407828201,-49.257818266840495)

# # entire city
bounding_box = (-25.6450101000000004,-49.3891399999999976,-25.3467008999999983,-49.1843181999999999)

# required_fields:
req_fields = {
    'sidewalks':['surface','smoothness','width','incline','tactile_paving','incline:across'],
    'kerbs':['kerb','tactile_paving'],
    'crossings':['crossing','surface','smoothness','traffic_calming'],
}

# max radius to cut off unconnected crossings and kerbs
max_radius_cutoff = 50

# default note for features without values (in order to be different from zero)
default_score = 0.5




fields_values_properties = {
    'sidewalks':{
        'surface': {
            # OUTSIDE
        },
        'smoothness' : {
            # OUTSIDE
        },
        'width':{
            # in a future...
        },
        'incline':{
            # in a future...
        },
        'tactile_paving':{
            #CHECK KERBS
        },
        'incline:across':{
            # in a future...
        }
    },

    'kerbs':{
        'kerb':{
            'raised':{
                'score_default' : 3,
                'color' : '#000000', #black
            },
            'rolled':{
                'score_default' : 5,
                'color' : '#808080', #50% gray
            },
            'no':{
                'score_default' : 7,
                'color' : '#bebebe', #75% hray
            },
            'lowered':{
                'score_default' : 9,
                'color' : '#ffffff', #white
            },
            'flush':{
                'score_default' : 10,
                'color' : '#ffffff', #white
            },

        },
        'tactile_paving':{
            'yes':{
                'score_default' : 10,
                'color' : '#000000', #black
            },
            'contrasted':{
                'score_default' : 10,
                'color' : '#000000', #black
            },
            'no':{
                'score_default' : 5,
                'color' : 'rgba(0, 0, 0, 0)', # transparent
            },

        }
        },
    'crossings':{
        'crossing':{
            'no':{
                'score_default' : 0,
                'bonus' : -10,
                'color' : '#ff0000', # RED
            },
            'unmarked':{
                'score_default' : 7,
                'bonus' : 0,
                'color' : '#000000', #black
            },
            'marked':{
                'score_default' : 9,
                'bonus' : 2,
                'color' : '#000000', #black
            },
            'traffic_signals':{
                'score_default' : 10,
                'bonus' : 3,
                'color' : '#ffffff', #white
            },


        },
        'surface':{
            # CHECK SIDEWALKS

        },
        'smoothness':{
            # CHECK SIDEWALKS


        },
        'traffic_calming':{
            'table':{
                'score_default' : 10,
                'bonus' : 2,
                'color' : '',
            },            

        }
        },
}