'''
    File Just to host the replacements to be carried out!!

'''

def file_as_string(inputpath:str):
    # no problem recreating some functions, it can avoid circular imports
    with open(inputpath) as reader:
        return reader.read()


insertions_dict = {
    "<head>" :
        f"""
        <head>

        <title>OpenSidewalkMap</title>

        <link rel="icon" type="image/x-icon" href="assets/homepage/favicon_homepage.png">


        <script>
            {file_as_string("assets/webscripts/symbols_toggling.js")}
        </script>
            
        <style>
            {file_as_string('assets/styles/webmap_styles.css')}
        </style>


        """ , 

    # fixed stuff at the beggining of body
    "<body>" : """

    <body>
    <script>var lastHoveredFeatureId;</script>
    
    """,

    "</body>":
        """

                    <!-- the 4 side images: -->
            <div class="leg_div">

            <div class="kerbs-leg" id="kerbs-div">
                <img src="assets/kerbs_leg.png" alt="kerbs_leg" title="test_hover 02"  id="kerbs-leg-img"></img>

                    <img src="assets/kerbs_leg.png" alt="kerbs_leg" class="kerbs-leg hover_base_kb" title="Kerbs Map Symbols (click)" 
                    
                    onclick="toggleOneHideOthers('kerbs_symbols',['crossings_symbols','sw_surface_symbols','sw_smoothness_symbols'])"

                    ></img>




            </div>

            <div class="crossings-leg" id="crossings-div">
                <img src="assets/crossings_leg.png" alt="crossings_leg"></img>

                    <img src="assets/crossings_leg.png" alt="crossings_leg" class="crossings-leg hover_base_cr" title="Crossings Map Symbols (click)"
                    
                    onclick="toggleOneHideOthers('crossings_symbols',['sw_smoothness_symbols','kerbs_symbols','sw_surface_symbols'])"
                    
                    ></img>



            </div>

            <div class="sw-leg-smo" id="sw-smo-div">


                <img src="assets/sw_leg_smoothness.png" alt="sw_leg_smoothness"></img>

                    <img src="assets/sw_leg_smoothness.png" alt="sw_surface_leg_hover" class="sw-leg-smo hover_base_smo" title="Sidewalk Smoothness Map Symbols (click)" 
                    
                    onclick="toggleOneHideOthers('sw_smoothness_symbols',['kerbs_symbols','sw_surface_symbols','crossings_symbols'])"
                    
                    
                    ></img>

            </div>

            <div class="sw-leg-sur" id="sw-sur-div">

                <img src="assets/sw_leg_surface.png" alt="sw_surface_leg"></img>

                    <img src="assets/sw_leg_surface.png" alt="sw_surface_leg_hover" class="sw-leg-sur hover_base_sur" title="Sidewalk Surface Map Symbols (click)" 
                    
                    onclick="toggleOneHideOthers('sw_surface_symbols',['kerbs_symbols','sw_smoothness_symbols','crossings_symbols'])"
                    
                    ></img>



            </div>

            <!-- SIDEWALKS SURFACE -->
            <div> 
                <img src="assets/sw_leg_surface_content.png" alt="sw_leg_surface_content" class="map-symbols-common responsive" id="sw_surface_symbols"
                
                onclick="hideElementOnClick('sw_surface_symbols')"
                
                ></img>
            </div>

            <!-- SIDEWALKS SMOOTHNESS -->
            <div> 
                <img src="assets/sw_leg_smoothness_content.png" alt="sw_leg_smoothness_content" class="map-symbols-common responsive" id="sw_smoothness_symbols"

                onclick="hideElementOnClick('sw_smoothness_symbols')"
                
                
                ></img>
            </div>

            <!-- CROSSINGS -->
            <div> 
                <img src="assets/crossings_leg_content.png" alt="crossings_leg_content" class="map-symbols-common responsive" id="crossings_symbols" 


                onclick="hideElementOnClick('crossings_symbols')"

                
                ></img>
            </div>
            
            <!-- KERBS -->
            <div> 
                <img src="assets/kerbs_leg_content.png" alt="kerbs_leg_content" class="map-symbols-common responsive" id="kerbs_symbols" 

                onclick="hideElementOnClick('kerbs_symbols')"

                
                
                ></img>
            </div>


            </div>

    </body>
        """
}