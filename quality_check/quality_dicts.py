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
        'kerb':'sidewalks are drawn at path axis, kerb acess points should be literally at the kerb ("meio-fio", pt-br)',
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
        'button_operated': "it may be referring to the crossing, may be OK",
        'traffic_signals:sound':"it may be referring to the crossing, may be OK",
        "traffic_signals:vibration": "it may be referring to the crossing, may be OK",
        "crossing:island" : "if in the middle of a crossing It's fine!! "

        }
        ,
}

replaceable_values = {
    'sidewalks': {},
    'crossings': {'crossing':{'marked':'uncontrolled','zebra':'uncontrolled','island':"should use the TAG 'crossing:island=yes' "}},
    'kerbs':     {},
}

invalid_characters = {
    '=' : "The '=' character is used ONLY in textual representation of tags to separate the key from the value",
}




categories_dict_keys = {
    "improper_keys": {
        'about':"Keys that (almost certainly) shouldn't be used at that feature type",
        'dict' : improper_keys,
        'type':'keys',

        'occurrences': {
                            'sidewalks': [],
                            'crossings': [],
                            'kerbs':     [],
                        },


        'occ_count': {
                    'sidewalks': 0,
                    'crossings': 0,
                    'kerbs':     0,
                },


    },

    "uncanny_keys": {
        'about':"Keys that may be OK in some specific situations, but may be a mistake",
        'dict' : uncanny_keys,
        'type':'keys',

        'occurrences': {
                            'sidewalks': [],
                            'crossings': [],
                            'kerbs':     [],
                        },
        
        'occ_count': {
                    'sidewalks': 0,
                    'crossings': 0,
                    'kerbs':     0,
                },

    },


        "keys_without_wiki": {
        'about':"Keys that may be wrong, because there's no wiki article for it",
        'dict' : 'quality_check/keys_without_wiki.json',
        'type':'keys',

        'occurrences': {
                            'sidewalks': [],
                            'crossings': [],
                            'kerbs':     [],
                        },
        
        'occ_count': {
                    'sidewalks': 0,
                    'crossings': 0,
                    'kerbs':     0,
                },

        },

    "replaceable_values": {
        'about':"values that are not wrong, but there's a better  option that is in the commentary",
        'dict' : replaceable_values,
        'type':'values',

        'occurrences': {
                            'sidewalks': [],
                            'crossings': [],
                            'kerbs':     [],
                        },


        'occ_count': {
                    'sidewalks': 0,
                    'crossings': 0,
                    'kerbs':     0,
                },

    },

    "wrong_mispelled_or_unlisted_values": {
        'about':"Values that are probably wrong, but they may be mispelled or just unlisted",
        'dict' : 'quality_check/valid_tag_values.json',
        'type':'values',

        'occurrences': {
                            'sidewalks': [],
                            'crossings': [],
                            'kerbs':     [],
                        },


        'occ_count': {
                    'sidewalks': 0,
                    'crossings': 0,
                    'kerbs':     0,
                },

    },


    "invalid_characters": {
        'about':"characters that should not be in the value or in the key",
        'dict' : invalid_characters,
        'type':'tags',

        'occurrences': {
                            'sidewalks': [],
                            'crossings': [],
                            'kerbs':     [],
                        },


        'occ_count': {
                    'sidewalks': 0,
                    'crossings': 0,
                    'kerbs':     0,
                },

    },

    "missing_value": {
        'about':"tags with only a key, no value",
        'dict' : None,
        'type':'tags',

        'occurrences': {
                            'sidewalks': [],
                            'crossings': [],
                            'kerbs':     [],
                        },



        'occ_count': {
                    'sidewalks': 0,
                    'crossings': 0,
                    'kerbs':     0,
                },

    },



}


occurrence_per_feature = {
    'sidewalks': {},
    'crossings': {},
    'kerbs':     {},
}



