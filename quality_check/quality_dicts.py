"""

    FILE TO STORE THE CATEGORIES

"""

feature_categories = ['sidewalks','crossings','kerbs']

"""
template dict:

category = {
    'sidewalks': {},
    'crossings': {},
    'kerbs':     {},
}

"""

improper_keys = {
    'sidewalks': {
        'kerb':'sidewalks are drawn at path axis, kerb acess points should at the kerb ("meio-fio", pt-br)',
        'opening_hours':'if it has opening hours it may be a private pathway, not a sidewalk',
        'paving_stones':'paving stones is a value for "surface key"','crossing':"It's inappropriate for Sidewalks, probably mistakenly tagged",
        'barrier':"if there's a barrier it may be a node in the sidewalk, but not the sidewalk itself",
        
        },

    'crossings': {
        'kerb': 'kerbs are points, crossings are lines',
        'barrier':"a crossing with a barrier may not be an actual crossing..."

        },

    'kerbs': {
        'opening_hours':'a crossing may have opening hours (brigdes?), but not a kerb',
        'crossing':"It's inappropriate for Kerbs, it's for crossings",
        'crossing_ref' :"It's inappropriate for Kerbs, it's for crossings",
        'name':'most kerbs have no name',
        'traffinc_calming':'generally the trafic calming refers to the crossing'

    
    },
}

uncanny_keys = {
    'sidewalks': {
        'traffic_signals':'may be used for crossings',
        'name':'most sidewalks dont have an actual name'
        },
    'crossings': {'level':'according to wiki it may be used only for indoor or if bound to a floor...'},
    'kerbs':     {
        'button_operated': "it may be referring to the crossing, may be OK",'traffic_signals:sound':"it may be referring to the crossing, may be OK",
        "traffic_signals:vibration": "it may be referring to the crossing, may be OK",
        "crossing:island" : "if in the middle of a crossing It's fine!! "

        }
        ,
}


categories_dict = {
    "improper_keys": {
        'about':"Keys that (almost certainly) shouldn't be used at that feature type",
        'dict' : improper_keys,
    },

    "uncanny_keys": {
        'about':"Keys that may be OK in some specific situations, but may be a mistake",
        'dict' : uncanny_keys,
    },
}