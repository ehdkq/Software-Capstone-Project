const loginBtn = document.getElementById('login-button');

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