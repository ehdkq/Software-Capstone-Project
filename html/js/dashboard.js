
// ==========================================
// PART 1: SUPABASE AUTH & SECURITY LOGIC
// ==========================================
        
// 🛑 PASTE YOUR SUPABASE URL AND KEY HERE 🛑
const SUPABASE_URL = "https://izexxryxkqcgezdfjqlg.supabase.co";
const SUPABASE_KEY = "sb_publishable_4F8U5q77q5yDs2xYLVsUKA_cPuVOHCc";
const mySupabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

function secureDashboard() {
    // checks the custom login session when directed to the dashboard after successful login
    const isLoggedIn = localStorage.getItem("isLoggedIn");

    // if login session not in localStorage, stay on the login screen 
    if (isLoggedIn !== "true") {
        window.location.replace("login.html");
        return; 
    }

    // Un-hide the body because they are allowed to be here
    document.getElementById("body-wrapper").style.display = "block";

    // Welcome login page with buttons 
    document.getElementById("user-greeting-new").textContent = "Welcome to Budgie!";
    document.getElementById("new-user-welcome").style.display = "block";

    // Grab their first name from the database metadata
    //const user = session.user;
    //const firstName = user.user_metadata.first_name || "there"; 
            
    // Personalize the greetings
    //document.getElementById("user-greeting-new").textContent = `Welcome to Budgie, ${firstName}!`;
    //document.getElementById("dynamic-greeting").textContent = `Welcome back, ${firstName}!`;

    // For now, we will show the Blank Slate first since you wanted to test it!
    //document.getElementById("new-user-welcome").style.display = "block";
}

// Run security check on load
secureDashboard();

// UI Flow: Click to transition from Blank Slate to the main Dashboard
document.getElementById("start-budgeting-btn").addEventListener("click", function() {
    document.getElementById("new-user-welcome").style.display = "none";
    document.getElementById("existing-dashboard").style.display = "block";
});

// Logout Functions
async function handleLogout() {
    // remove login session from localStorage 
    localStorage.removeItem("isLoggedIn");

    // go back to login when clicking on logout on dashboard
    window.location.href = "login.html";
}

document.getElementById("logout-btn-new").addEventListener("click", handleLogout);
document.getElementById("logout-btn-existing").addEventListener("click", handleLogout);


// ==========================================
// PART 2: YOUR ORIGINAL DASHBOARD LOGIC (Made Blank!)
// ==========================================

// --- 1. Balance Logic ---
let currentBalance = 0.00; // Set default to 0!

function toggleBalanceEdit() {
    const form = document.getElementById('edit-balance-form');
    if (form.style.display === 'none' || form.style.display === '') {
        form.style.display = 'block';
        document.getElementById('new-balance-input').value = currentBalance.toFixed(2);
    } else {
        form.style.display = 'none';
    }
}

function saveBalance() {
    const newVal = parseFloat(document.getElementById('new-balance-input').value);
    if (!isNaN(newVal)) {
        currentBalance = newVal;
        document.getElementById('display-balance').innerText = '$' + currentBalance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        toggleBalanceEdit(); 
    }
}

// --- 2. Goals Management Logic ---
let goals = []; // Empty the default goals array!
        
const goalForm = document.getElementById('goal-form');
const goalsList = document.getElementById('goals-list');

goalForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const category = document.getElementById('g-category').value;
    const target = parseFloat(document.getElementById('g-amount').value);

    const existingIndex = goals.findIndex(g => g.category === category);
    if(existingIndex >= 0) {
        goals[existingIndex].target = target;
    } else {
        goals.push({ id: Date.now(), category, target });
    }
            
    goalForm.reset();
    renderGoals();
});

function deleteGoal(id) {
    goals = goals.filter(g => g.id !== id);
    renderGoals();
}

function renderGoals() {
    goalsList.innerHTML = '';
            
    // BLANK STATE CHECK: If no goals exist, show the message!
    if (goals.length === 0) {
        goalsList.innerHTML = '<p style="text-align: center; color: #888; font-style: italic; margin-top: 15px;">Let\'s make your first goal!</p>';
        return; // Stop the function here so it doesn't try to draw empty bars
    }

    let spentTotals = { 'Groceries': 0, 'Dining': 0, 'Utilities': 0, 'Entertainment': 0 };
    transactions.forEach(t => {
        if(spentTotals[t.type] !== undefined) {
            spentTotals[t.type] += t.amount;
        }
    });

    goals.forEach(g => {
        const spent = spentTotals[g.category] || 0;
        let percent = (spent / g.target) * 100;
        let barColor = '#97dbff'; 
                
        if (percent >= 100) {
            percent = 100; 
            barColor = '#ff4d4d'; 
        }

        const goalDiv = document.createElement('div');
        goalDiv.style.marginBottom = '15px';
        goalDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <span><strong>${g.category}</strong>: $${spent.toFixed(2)} / $${g.target.toFixed(2)}</span>
                <button onclick="deleteGoal(${g.id})" class="delete-btn" style="padding: 2px 6px; font-size: 0.75rem;">X</button>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${percent}%; background-color: ${barColor};"></div>
            </div>
        `;
        goalsList.appendChild(goalDiv);
    });
}

// --- 3. Transaction Management Logic ---
let transactions = []; // Ensure this starts empty
let editingTransactionId = null; 
        
const transactionForm = document.getElementById('transaction-form');
const transactionList = document.getElementById('transaction-list');
const tSubmitBtn = document.getElementById('t-submit-btn');

transactionForm.addEventListener('submit', function(e) {
    e.preventDefault(); 
    const desc = document.getElementById('t-desc').value;
    const type = document.getElementById('t-type').value;
    const amount = parseFloat(document.getElementById('t-amount').value);

    if (editingTransactionId !== null) {
        const index = transactions.findIndex(t => t.id === editingTransactionId);
        if (index !== -1) {
            transactions[index] = { id: editingTransactionId, desc, type, amount };
        }
        editingTransactionId = null; 
        tSubmitBtn.textContent = 'Add'; 
    } else {
        transactions.push({ id: Date.now(), desc, type, amount });
    }
            
    transactionForm.reset();
    renderTransactions();
});

function editTransaction(id) {
    const transactionToEdit = transactions.find(t => t.id === id);
            
    if (transactionToEdit) {
        document.getElementById('t-desc').value = transactionToEdit.desc;
        document.getElementById('t-type').value = transactionToEdit.type;
        document.getElementById('t-amount').value = transactionToEdit.amount;
                
        editingTransactionId = id;
        tSubmitBtn.textContent = 'Update';
    }
}

function deleteTransaction(id) {
    transactions = transactions.filter(t => t.id !== id);
            
    if (editingTransactionId === id) {
        transactionForm.reset();
        editingTransactionId = null;
        tSubmitBtn.textContent = 'Add';
    }
            
    renderTransactions();
}

function renderTransactions() {
    transactionList.innerHTML = '';

    // BLANK STATE CHECK: If no transactions exist, show the message!
    if (transactions.length === 0) {
        transactionList.innerHTML = '<p style="text-align: center; color: #888; font-style: italic; margin-top: 15px;">No transactions yet. Add your first one above!</p>';
    } else {
        transactions.forEach(t => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span><strong>${t.desc}</strong> (${t.type})</span>
                <span>$${t.amount.toFixed(2)} 
                    <button onclick="editTransaction(${t.id})" style="background-color: #f0ad4e; color: white; border: none; border-radius: 4px; padding: 4px 8px; cursor: pointer; margin-left: 10px;">Edit</button>
                    <button onclick="deleteTransaction(${t.id})" class="delete-btn">X</button>
                </span>
            `;
            transactionList.appendChild(li);
        });
    }
            
    updateChartData(); 
    renderGoals(); 
}

// --- 4. Pie Chart Logic ---
const ctx = document.getElementById('spending-chart').getContext('2d');
let spendingChart = new Chart(ctx, {
    type: 'pie',
    data: {
        labels: ['Groceries', 'Dining', 'Utilities', 'Entertainment'],
        datasets: [{
            data: [0, 0, 0, 0], 
            backgroundColor: ['#97dbff', '#ffb3ba', '#bae1ff', '#baffc9']
        }]
    },
    options: { responsive: true, maintainAspectRatio: false }
});

function updateChartData() {
    let totals = { 'Groceries': 0, 'Dining': 0, 'Utilities': 0, 'Entertainment': 0 };
    transactions.forEach(t => {
        if(totals[t.type] !== undefined) totals[t.type] += t.amount;
    });
    spendingChart.data.datasets[0].data = Object.values(totals);
    spendingChart.update();
}

// --- 5. Mock File Upload Simulation ---
document.getElementById('statement-upload').addEventListener('change', function(e) {
    if(e.target.files.length > 0) {
        alert("File selected! Loading mock data to demonstrate the chart and goals update.");
        transactions = [
            { id: 1, desc: "Schnucks", type: "Groceries", amount: 120.50 },
            { id: 2, desc: "Evergy", type: "Utilities", amount: 85.00 },
            { id: 3, desc: "AMC Theaters", type: "Entertainment", amount: 35.00 },
            { id: 4, desc: "Chipotle", type: "Dining", amount: 24.50 }
        ];
        renderTransactions();
    }
});

// Initialize UI on first load (Forces the balance text to say $0.00 immediately)
document.getElementById('display-balance').innerText = '$0.00';
renderTransactions();
