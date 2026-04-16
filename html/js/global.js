document.addEventListener("DOMContentLoaded", async () => {
    // 1. Find the placeholder and inject the header HTML
    const headerContainer = document.getElementById("header-container");
    
    if (headerContainer) {
        try {
            const response = await fetch("header.html");
            const headerHtml = await response.text();
            headerContainer.innerHTML = headerHtml;
        } catch (error) {
            console.error("Failed to load header:", error);
        }
    }

    // 2. Now that the header exists on the page, run the Auth Check!
    const isLoggedIn = localStorage.getItem("isLoggedIn") === "true";
    const loginBtn = document.getElementById("nav-login-btn"); 
    const dashboardBtn = document.getElementById("nav-dashboard-btn");

    if (isLoggedIn) {
        if (loginBtn) loginBtn.style.display = "none";
        if (dashboardBtn) dashboardBtn.style.display = "inline-block";
    } else {
        if (loginBtn) loginBtn.style.display = "inline-block";
        if (dashboardBtn) dashboardBtn.style.display = "none";
    }
});