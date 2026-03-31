 const createAccountBtn = document.getElementById('account-submit');

// Created the event listener for user clicking on submit button in creating an account
createAccountBtn.addEventListener("click", (event) => {
    event.preventDefault();

    // TODO: need refactor  file to direct to the dashboard after creation of a new account
    // const firstName = document.getElementById('first-name').value;
    // const lastName = document.getElementById('last-name').value;

    const emailAddress = document.getElementById('email-address').value;
    const newPassword = document.getElementById('password-input').value;
    const reEnterPassword = document.getElementById('reenter-password').value;

    const url = new URL("http://127.0.0.1:8000/create-account"); // Likely will change this for when hosting on Netlify
    url.searchParams.append('email',emailAddress);
    url.searchParams.append('passw',newPassword);

    // Security check!
    if (newPassword !== reEnterPassword) {
        alert("Whoops, passwords don't match. Please try again");
        return // Stop the entire function
    }

    console.log("Passwords match! Proceeding with account creation...");

    // send data to FastApi endpoint 
    fetch(url , {
        method: 'GET',
        headers: {
            'Accept': 'application/json'
        }
    })

    // Complete Promise
    .then(response => {
        if (!response.ok) throw new Error("Server error");
        return response.json();
    })
    .then(data => {
        if (data === true) {
            console.log("Success:", data);
            alert("Account Created Successfully! You can now log in.");
            // TODO: Redirect to login page
        } else {
            alert("Account creation failed. The email might already be in use.");
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        alert('Could not connect to the server.');
    });
});