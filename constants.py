# intended for common values, constants, setup...

# hmtml file name
page_name = "map.html"

# data names
sidewalks_path = 'data/sidewalks.geojson'
crossings_path = 'data/crossings.geojson'
kerbs_path = 'data/kerbs.geojson'

# # the ten block sample
bounding_box_sample = (-25.46340831586,-49.26485433156466,-25.45836407828201,-49.257818266840495)

# # entire city
bounding_box = (-25.6450101000000004,-49.3891399999999976,-25.3467008999999983,-49.1843181999999999)



# max radius to cut off unconnected crossings and kerbs
max_radius_cutoff = 50

# default note for features without values (in order to be different from zero)
default_score = 0.5




fields_values_properties = {
    'sidewalks':{
        'surface': {
            # colorscheme from colorbrewer, avaliiable at:
            # https://colorbrewer2.org/?type=qualitative&scheme=Set3&n=12

            'asphalt':{
                'score_default' : 100,
                'color' : '#fb8072', #
            },
            'concrete':{
                'score_default' : 100,
                'color' : '#80b1d3', 
            },
            'concrete:plates':{
                'score_default' : 70,
                'color' : '#fccde5', #
            },
            'paving_stones':{
                'score_default' : 90,
                'color' : '#bebada', #
            },
            'sett':{
                'score_default' : 60,
                'color' : '#ffed6f', #
            },

            'cobblestone':{
                'score_default' : 60,
                'color' : '#ffed6f', #
            },
            
            'unhewn_cobblestone':{
                'score_default' : 50,
                'color' : '#ffffb3', #black
            },

            'ground':{
                'score_default' : 30,
                'color' : '#fdb462' }, #
            'dirt':{
                'score_default' : 30,
                'color' : '#fdb462' }, #
            'earth':{
                'score_default' : 30,
                'color' : '#fdb462', #
            },
            'sand':{
                'score_default' : 30,
                'color' : '#fdb462', #
            },
            'grass':{
                'score_default' : 30,
                'color' : '#b3de69', #
            },
            # 'grass_paver':{
            #     'score_default' : 3,
            #     'color' : '#000000', #black
            # },

            'paved':{
                'score_default' : 60, # equals to worst paved: sett
                'color' : '#ffffff', # white
            },
            'unpaved':{
                'score_default' : 30,
                'color' : '#d9d9d9', #
            },

            # a sample for uncommon values:

            'gravel':{
                'score_default' : 30,
                'color' : '#bc80bd', #
            },

            'compacted':{
                'score_default' : 30,
                'color' : '#bc80bd', #
            },


            'ceramic:tiles':{
                'score_default' : 70,
                'color' : '#bc80bd', #
            },

            'wood':{
                'score_default' : 50,
                'color' : '#bc80bd', #
            },

            # 'Petit_Pavê':{
            #     'score_default' : 65,
            #     'color' : '#bc80bd', #
            # },

            # for the filled ones:
            '?':{
                'score_default' : 10,
                'color' : '#434343', #
            },




        },
        'smoothness' : {
            # for absence:
            '?':{
                'score_default' : 40, # equivalent to "very horrible"
                'color' : '#434343', #
            },


            # valid:
            'excellent':{
                'score_default' : 10, 
                'color' : '#006d2c', #
            },
            'good':{
                'score_default' : 90, 
                'color' : '#31a354', #
            },
            'intermediate':{
                'score_default' : 70, 
                'color' : '#74c476', #
            },
            'bad':{
                'score_default' : 50, 
                'color' : '#a1d99b', #
            },
            'very_bad':{
                'score_default' : 40, 
                'color' : '#a1d99b', #
            },
            'horrible':{
                'score_default' : 20, 
                'color' : '#c7e9c0', #
            },
            'very_horrible':{
                'score_default' : 10, 
                'color' : '#c7e9c0', #
            },
            'impassable':{
                'score_default' : 0, 
                'color' : '#edf8e9', #
            },


        # invalid values must be handled individually
                                                                                                 

        },
        'width':{
            '?':{
                'score_default' : 10,
                'color' : '#434343', #
            },
            # in a future...
        },
        'incline':{
            '?':{
                'score_default' : 10,
                'color' : '#434343', #
            },
            # in a future...
        },
        'tactile_paving':{
            #CHECK KERBS
        },
        'incline:across':{
            '?':{
                'score_default' : 10,
                'color' : '#434343', #
            },
            # in a future...
        }
    },

    'kerbs':{
        'kerb':{
            'raised':{
                'score_default' : 30,
                'color' : '#000000', #black
            },
            'rolled':{
                'score_default' : 50,
                'color' : '#808080', #50% gray
            },
            'no':{
                'score_default' : 70,
                'color' : '#bebebe', #75% hray
            },
            'lowered':{
                'score_default' : 90,
                'color' : '#ffffff', #white
            },
            'flush':{
                'score_default' : 100,
                'color' : '#ffffff', #white
            },

            '?':{
                'score_default' : 30, # equivalent to "raised"
                'color' : '#d9d9d9', #
            },

        },
        'tactile_paving':{
            'yes':{
                'score_default' : 100,
                'color' : '#000000', #black
            },
            'contrasted':{
                'score_default' : 100,
                'color' : '#000000', #black
            },
            'no':{
                'score_default' : 50,
                'color' : 'rgba(0, 0, 0, 0)', # transparent
            },

            '?':{
                'score_default' : 50, # equivalent to "no"
                'color' : '#d9d9d9', #
            },

        }
        },
    'crossings':{
        # default scores should be what was named "bonus"
        'crossing':{
            'no':{
                # 'score_default' : 0,
                # 'bonus' : -100,
                'score_default' : -100,

                'color' : '#ff0000', # RED
            },
            'unmarked':{
                # 'score_default' : 70,
                # 'bonus' : 0,
                'score_default' : 0,

                'color' : '#000000', #black
            },
            'marked':{
                # 'score_default' : 90,
                # 'bonus' : 20,

                'score_default' : 20,

                'color' : '#000000', #black
            },
            'traffic_signals':{
                # 'score_default' : 100,
                # 'bonus' : 30,

                'score_default' : 30,

                'color' : '#ffffff', #white
            },

            '?':{
                # 'score_default' : 10,
                # 'bonus' : 0,

                'score_default' : 0,

                'color' : '#d9d9d9', #
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
                # 'score_default' : 100,
                'score_default' : 20,

                # 'bonus' : 20,
                'color' : '#ffffff',
            },

            '?':{
                'score_default' : 0,
                'color' : '#d9d9d9', #
            },

        }
}
}

# values to be copied:
fields_values_properties['sidewalks']['tactile_paving'] = fields_values_properties['kerbs']['tactile_paving']

fields_values_properties['crossings']['surface'] = fields_values_properties['sidewalks']['surface']

fields_values_properties['crossings']['smoothness'] = fields_values_properties['sidewalks']['smoothness']


# required_fields:
req_fields = {
    'sidewalks':['surface','smoothness','width','incline','tactile_paving','incline:across'],
    'kerbs':['kerb','tactile_paving'],
    'crossings':['crossing','surface','smoothness','traffic_calming'],
}

# a case of "smoothness=concrete:pĺates" demanded this
wrong_misspelled_values ={
    'sidewalks':{
        'smoothness':{'concrete:plates':'?'},
        'surface':{'betão':'?','Petit_Pavê':'sett','porcelain tiles':'ceramic:tiles'}
    },
    'kerbs':{

    },
    'crossings':{

    },
}