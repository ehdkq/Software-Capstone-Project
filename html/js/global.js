// --- GLOBAL UI FUNCTIONS ---
window.showToast = function(message, type = "error") {
    let container = document.getElementById('toast-container');
    
    // Auto-inject the container if it doesn't exist on this page yet!
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.classList.add('budgie-toast');
    
    if (type === "error") {
        toast.classList.add('toast-error');
    } else if (type === "success") {
        toast.classList.add('toast-success');
    }

    toast.innerText = message;
    container.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
};

// --- AUTH & HEADER LOGIC ---
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