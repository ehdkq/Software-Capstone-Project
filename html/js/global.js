// --- UNIVERSAL THEME LOADER ---
(function applySavedTheme() {
    const savedTheme = localStorage.getItem('budgieTheme');
    
    // Safety wipe
    document.body.classList.remove('dark-theme', 'high-contrast-theme');
    
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    } else if (savedTheme === 'high-contrast') {
        document.body.classList.add('high-contrast-theme');
    }
})();

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

// --- CUSTOM DANGER MODAL ---
window.budgieConfirm = function(title, message) {
    return new Promise((resolve) => {
        // Create the dark overlay
        const overlay = document.createElement('div');
        overlay.className = 'budgie-modal-overlay';
        
        // Build the modal HTML inside it (featuring a sad Budgie!)
        overlay.innerHTML = `
            <div class="budgie-modal">
                <img src="./images/worried-budgie.png" alt="Warning">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="budgie-modal-btns">
                    <button class="budgie-btn-cancel" id="budgie-cancel-btn">Cancel</button>
                    <button class="budgie-btn-confirm" id="budgie-confirm-btn">Yes, I'm sure</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        // Animate it onto the screen
        setTimeout(() => {
            overlay.style.opacity = '1';
            overlay.querySelector('.budgie-modal').classList.add('show');
        }, 10);

        // Handle the button clicks
        const close = (result) => {
            overlay.style.opacity = '0';
            overlay.querySelector('.budgie-modal').classList.remove('show');
            setTimeout(() => overlay.remove(), 200); // Wait for fade out to finish
            resolve(result); // Return true or false
        };

        document.getElementById('budgie-cancel-btn').onclick = () => close(false);
        document.getElementById('budgie-confirm-btn').onclick = () => close(true);
    });
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
            
            // 👇 NEW MOBILE MENU LOGIC GOES HERE 👇
            // (It must be inside this block so it runs AFTER the header is loaded!)
            const mobileBtn = document.getElementById('mobile-menu-btn');
            const navLinks = document.getElementById('nav-links-container');

            if (mobileBtn && navLinks) {
                mobileBtn.addEventListener('click', () => {
                    navLinks.classList.toggle('show');
                });
            }
            // 👆 END OF MOBILE MENU LOGIC 👆

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

// --- 3. BANK-GRADE INACTIVITY TIMEOUT ---
// (This goes completely outside and below the block above!)
if (localStorage.getItem("isLoggedIn") === "true") {
    let inactivityTimer;
    
    // Set for 5 minutes (300,000 milliseconds)
    const maxIdleTime = 300000; 

    function resetTimer() {
        clearTimeout(inactivityTimer);
        inactivityTimer = setTimeout(() => {
            // 1. Wipe the keys to the cage
            localStorage.removeItem("isLoggedIn");
            localStorage.removeItem("userId");
            localStorage.removeItem("userEmail");
            
            // 2. Warn the user and kick them out
            alert("For your security, Budgie has logged you out due to inactivity.");
            window.location.replace("login.html");
        }, maxIdleTime);
    }

    // Reset the clock if the user does literally anything
    window.onload = resetTimer;
    document.onmousemove = resetTimer;
    document.onkeypress = resetTimer;
    document.onclick = resetTimer;
    document.ontouchstart = resetTimer; 
}