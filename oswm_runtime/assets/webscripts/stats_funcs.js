function responsiveTopNav() {
    var x = document.getElementById("stTopnav");
    if (x.className === "topnav") {
      x.className += " responsive";
    } else {
      x.className = "topnav";
    }
} 

// Theme toggle logic
document.addEventListener("DOMContentLoaded", () => {
    const themeBtn = document.getElementById("themeToggleBtn");
    const themeIcon = document.getElementById("themeIcon");
    
    // Check local storage or system preference
    const currentTheme = localStorage.getItem("theme");
    
    if (currentTheme) {
        document.body.setAttribute("data-theme", currentTheme);
        updateIcon(currentTheme);
    } // default is light, no attribute needed if light
    
    if (themeBtn) {
        themeBtn.addEventListener("click", () => {
            let theme = document.body.getAttribute("data-theme");
            if (theme === "dark") {
                document.body.removeAttribute("data-theme");
                localStorage.setItem("theme", "light");
                updateIcon("light");
            } else {
                document.body.setAttribute("data-theme", "dark");
                localStorage.setItem("theme", "dark");
                updateIcon("dark");
            }
        });
    }

    function updateIcon(theme) {
        if (!themeIcon) return;
        if (theme === "dark") {
            themeIcon.className = "fa fa-sun-o";
        } else {
            themeIcon.className = "fa fa-moon-o";
        }
    }
});