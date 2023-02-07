function hideElementOnClick(elementId) {
    // thx : https://www.w3schools.com/howto/howto_js_toggle_hide_show.asp
    var x = document.getElementById(elementId);
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
}

function toggleOneHideOthers(toToggleId, others) {
    hideElementOnClick(toToggleId);
    others.forEach(untoggle);
}


function untoggle(elementId) {
    var x = document.getElementById(elementId);
    x.style.display = "none";

}