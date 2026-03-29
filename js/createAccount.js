// TODO: Plan to push ONLY relevant information to teams github page
// 1) login and creatAccount javascript files 
// 2) Mention changes in the main.py of full integration between html, javascript, python to get to the backend 

const createAccountBtn = document.getElementById('account-submit');

// Created the event listener for user clicking on submit button in creating an account
createAccountBtn.addEventListener("click", (event) => {
    event.preventDefault();

    // TODO
    // const firstName = document.getElementById('first-name').value;
    // const lastName = document.getElementById('last-name').value;

    const emailAddress = document.getElementById('email-address').value;
    const newPassword = document.getElementById('password-input').value;
    const reEnterPassword = document.getElementById('reenter-password').value;

    const url = new URL("http://127.0.0.1:8000/create-account");
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