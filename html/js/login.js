const loginBtn = document.getElementById('login-button');
// --- PASSWORD TOGGLE LOGIC ---
const togglePassword = document.getElementById('toggle-password');
const passwordInput = document.getElementById('password-login');

if (togglePassword && passwordInput) {
    togglePassword.addEventListener('click', function () {
        // Check if it is currently hidden
        const isPassword = passwordInput.getAttribute('type') === 'password';
        
        // Swap the type
        passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
        
        // Swap the icon so they know it changed
        this.textContent = isPassword ? '🙈' : '👁️'; 
    });
}
// Event listener for when user enters email and password then clicks on submit button
loginBtn.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();

    const emailLogin = document.getElementById('email-login').value;
    const passwordLogin = document.getElementById('password-login').value;

    // Loading State 
    loginBtn.textContent = "Logging in...";
    loginBtn.style.pointerEvents = "none";

    const url = new URL('https://software-capstone-project.onrender.com/login'); // Likely will change this for when hosting on Netlify
    url.searchParams.append('email', emailLogin);
    url.searchParams.append('passw', passwordLogin)

    // send data to FastApi endpoint 
    fetch(url , {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    })
    
    // Complete Promise
    .then(response => response.json())
    .then(data => {
        // Check for the new response format: {success: true/false, user_id: "..."}
        if (data.success === true && data.user_id) {
            // Store login session and user information
            localStorage.setItem("isLoggedIn", "true");
            localStorage.setItem("userId", data.user_id);
            localStorage.setItem("userEmail", emailLogin);

            // UI flow for a successful login
            loginBtn.style.backgroundColor = "#4CAF50";
            loginBtn.style.color = "white";
            loginBtn.textContent = "√ Success!";

            // delay redirect
            setTimeout(() => {
                window.location.href = "dashboard.html";
            }, 1000);
        } else {
            // THE FIX: Show the EXACT error message from the Python backend
            showToast(data.error || "Unsuccessful Login.", "error");
            loginBtn.textContent = "Log In";
            loginBtn.style.pointerEvents = "auto";
        }
    })
    .catch((error) => {
        showToast("Cannot connect to server. Is Render awake?", "error");
        loginBtn.textContent = "Log In";
        loginBtn.style.pointerEvents = "auto";
    });
});

// --- FORGOT PASSWORD LOGIC ---
const showForgotLink = document.getElementById('show-forgot-password');
const forgotSection = document.getElementById('forgot-password-section');
const forgotForm = document.getElementById('forgot-password-form');
const resetSubmitBtn = document.getElementById('reset-submit-btn');

showForgotLink.addEventListener('click', (e) => {
    e.preventDefault();
    forgotSection.style.display = forgotSection.style.display === 'none' ? 'block' : 'none';
});

forgotForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('reset-email').value;
    
    resetSubmitBtn.textContent = "Sending...";
    resetSubmitBtn.disabled = true;

    try {
        const formData = new FormData();
        formData.append("email", email);

        const response = await fetch('https://software-capstone-project.onrender.com/api/request-reset', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast("Reset link sent! Check your email.", "success");
            forgotSection.style.display = 'none';
        } else {
            showToast(data.error || "Failed to send reset link.", "error");
        }
    } catch (error) {
        showToast("Server error. Please try again later.", "error");
    }
    
    resetSubmitBtn.textContent = "Send Reset Link";
    resetSubmitBtn.disabled = false;
});