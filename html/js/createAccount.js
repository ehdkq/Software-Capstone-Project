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

    const url = new URL("https://software-capstone-project.onrender.com/create-account"); // Likely will change this for when hosting on Netlify
    url.searchParams.append('email',emailAddress);
    url.searchParams.append('passw',newPassword);
    url.searchParams.append('firstN',fName);
    url.searchParams.append('lastN',lName);

    // Security check!
    if (newPassword !== reEnterPassword) {
        alert("Whoops, passwords don't match. Please try again");
        return // Stop the entire function
    }

    console.log("Passwords match! Proceeding with account creation...");

    // send data to FastApi endpoint 
    fetch(url , {
        method: 'POST',
        headers: {
            'Accept': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) throw new Error("Server error");
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log("Success:", data);
            
            // Show the success message from Python (so they know to check their mock email!)
            alert(data.message || "Account created successfully!");
            
            // delay redirect
            setTimeout(() => {
                window.location.href = "login.html";
            }, 1000);
        } else {
            // THE FIX: Stop guessing, and print the EXACT error from the Python server!
            alert("Creation failed: " + (data.error || "Unknown error"));
            console.error("Backend Error Details:", data.error);
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        alert('Could not connect to the server. Is Python running?');
    });
})