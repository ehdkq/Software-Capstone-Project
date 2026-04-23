 const createAccountBtn = document.getElementById('account-submit');

// Created the event listener for user clicking on submit button in creating an account
createAccountBtn.addEventListener("click", (event) => {
    event.preventDefault();

    // TODO: need refactor  file to direct to the dashboard after creation of a new account
    // const firstName = document.getElementById('first-name').value;
    // const lastName = document.getElementById('last-name').value;

    const emailAddress = document.getElementById('email-address').value;
    const newPassword = document.getElementById('password-input').value;
    const fName = document.getElementById('first-name').value;
    const lName = document.getElementById('last-name').value;
    const reEnterPassword = document.getElementById('reenter-password').value;

    // Security check 1: Do the passwords match?
    if (newPassword !== reEnterPassword) {
        showToast("Whoops, passwords don't match. Please try again", "error");
        return; // Stop the entire function
    }

    // Security check 2: Is the password strong enough?
    // This Regex requires: 1 Uppercase, 1 Number, 1 Special Char, and at least 8 characters long
    const passwordRegex = /^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+={}\[\]|\\:;"'<>,.?/-]).{8,}$/;
    
    if (!passwordRegex.test(newPassword)) {
        showToast("Password must be at least 8 characters and include an uppercase letter, a number, and a special symbol.", "error");
        return; // Stop the entire function
    }

    if (fName == null){
        showToast("Please enter your first name.", "error");
        return; 
    }

    if (lName == null){
        showToast("Please enter your last name.", "error");
        return; 
    }

    if (emailAddress == null){
        showToast("Please enter a valid email.", "error");
        return; 
    }

    console.log("Email type: " + typeof emailAddress)

    console.log("Passwords match and are secure! Proceeding with account creation...");

    const url = new URL("https://software-capstone-project.onrender.com/create-account"); // Likely will change this for when hosting on Netlify
    url.searchParams.append('email',emailAddress);
    url.searchParams.append('passw',newPassword);
    url.searchParams.append('firstN',fName);
    url.searchParams.append('lastN',lName);

    
    // send data to FastApi endpoint 
    fetch(url , {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
    })
    .then(response => {
        if (!response.ok) throw new Error("Server error");
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log("Success:", data);
            
            // 1. Hide the signup form
            document.getElementById("signup-section").style.display = "none";
            
            // 2. Show the "Check your email" message
            document.getElementById("verify-section").style.display = "block";
            
            // 3. Display their email address on the screen
            document.getElementById("display-email").textContent = emailAddress;
            
            showToast("Activation link sent!", "success");
            
        } else {
            showToast("Creation failed: " + (data.error || "Unknown error"), "error");
            console.error("Backend Error Details:", data.error);
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        showToast('Could not connect to the server. Is Python running?', "error");
    });
});
