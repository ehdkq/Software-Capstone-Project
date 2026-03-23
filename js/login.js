const loginBtn = document.getElementById('login-button');

// Event listener for when user enters email and password then clicks on submit button
loginBtn.addEventListener("click", (event) => {
    event.preventDefault();

    const emailLogin = document.getElementById('email-login').value;
    const passwordLogin = document.getElementById('password-login').value;

    const url = new URL('http://127.0.0.1:8000/login'); // Likely will change this for when hosting on server (Netlify)
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
    
    // Complete Promise, likely change for when dashboard is added
    .then(response => response.json())
    .then(data => {
        console.log("Success", data);
        // TODOl: Redirect to the profile dashboard page
        alert("Successful Login");
    })
    .catch((error) => {
        console.error('Error', error);
        alert('Unsuccessful Login');
    });
});