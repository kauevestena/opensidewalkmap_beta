
insertions_dict = {
    "<head>" :
        """
        <head>

        <title>OpenSidewalkMap</title>

        <link rel="icon" type="image/x-icon" href="assets/homepage/favicon_homepage.png">


            <script>
            function hideElementOnClick(elementId) {
            // thx : https://www.w3schools.com/howto/howto_js_toggle_hide_show.asp
            var x = document.getElementById(elementId);
            if (x.style.display === "none") {
                x.style.display = "block";
            } else {
                x.style.display = "none";
            }
            }

            function toggleOneHideOthers(toToggleId,others)
            {
                hideElementOnClick(toToggleId);
                others.forEach(untoggle);    
            }


            function untoggle(elementId){
                var x = document.getElementById(elementId);
                x.style.display = "none";

            }
        </script>
            
        <style>

        /* using a styles from: https://www.tutorialrepublic.com/codelab.php?topic=faq&file=changing-image-on-hover-with-css */
        .leg_div {
            position: fixed;
            top: 30%;
            right: 0%;

        }

        /* sidewalk surface rules:  */
        .sw-leg-sur {
            position: fixed;
            top: 30%;
            right: 0%;
            z-index: 1;
        }

        .sw-leg-sur .hover_base_sur {
            display: none;
            z-index: 101;


        }

        .sw-leg-sur:hover .hover_base_sur {
            display: inline;
            height: 120;
            z-index: 101;
            transform: scale(1.1,1.1);
            background-color: white;



        }


        /* sidewalk smoothness rules:  */
        .sw-leg-smo {
            position: fixed;
            top: 42%;
            right: 0%;
            z-index: 2;
        }

        .sw-leg-smo .hover_base_smo {
            display: none;
            z-index: 102;

        }

        .sw-leg-smo:hover .hover_base_smo {
            display: inline;
            z-index: 102;
            transform: scale(1.1,1.1);
            background-color: white;



        }

        /* crossings rules:  */
            .crossings-leg {
            position: fixed;
            top: 54%;
            right: 0%;
            z-index: 3;
        }

        .crossings-leg .hover_base_cr {
            display: none;
            z-index: 103;

        }

        .crossings-leg:hover .hover_base_cr {
            display: inline;
            transform: scale(1.1,1.1);
            background-color: white;

            position: absolute;
            top: 0;
            left: 0;


        }

        /* kerbs rules:  */
            .kerbs-leg {
            position: fixed;
            top: 66%;
            right: 0%;
            z-index: 4;
        }

        .kerbs-leg .hover_base_kb {
            display: none;
            z-index: 104;

        }

        .kerbs-leg:hover .hover_base_kb {
            display: inline;
            z-index: 104;
            transform: scale(1.1,1.1);
            background-color: white;




        }

        .map-symbols-common {
            display: none;
            position: fixed;
            top: 20%;
            right: 0%;
            transform: scale(.8,.8);

        }

        .responsive {
        max-width: 100%;
        height: auto;
        }

        /* hiding rules 

        #sw-smo-div:hover ~ #kerbs-div {
            display: none;
        } 
        
        */

    </style>


        """ ,



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