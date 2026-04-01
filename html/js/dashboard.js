// ==========================================
// API CONFIGURATION
// ==========================================
const API_BASE_URL = 'http://127.0.0.1:8000';

// ==========================================
// PART 1: SUPABASE AUTH & SECURITY LOGIC
// ==========================================

let currentUserId = null;

async function secureDashboard() {
    const isLoggedIn = localStorage.getItem("isLoggedIn");
    currentUserId = localStorage.getItem("userId");
    console.log('id: ', currentUserId)

    if (isLoggedIn !== "true" || !currentUserId) {
        window.location.replace("login.html");
        return; 
    }

    // Load user data from backend
    await loadUserData();

    // NOW check if we should show welcome screen (after data is loaded)
    if (goals.length == 0 && transactions.length == 0){
        document.getElementById("body-wrapper").style.display = "block";
        document.getElementById("user-greeting-new").textContent = "Welcome to Budgie!";
        document.getElementById("new-user-welcome").style.display = "block";
    } else {
        // Show the main dashboard if they have data
        document.getElementById("body-wrapper").style.display = "block";
        document.getElementById("existing-dashboard").style.display = "block";
    }
}

// Load all user data from backend
async function loadUserData() {
    await loadTransactions();
    await loadGoals();
}

secureDashboard();

document.getElementById("start-budgeting-btn").addEventListener("click", function() {
    document.getElementById("new-user-welcome").style.display = "none";
    document.getElementById("existing-dashboard").style.display = "block";
});

async function handleLogout() {
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("userId");
    window.location.href = "login.html";
}

document.getElementById("logout-btn-new").addEventListener("click", handleLogout);
document.getElementById("logout-btn-existing").addEventListener("click", handleLogout);

// ==========================================
// PART 2: DASHBOARD LOGIC WITH BACKEND
// ==========================================

// --- 2. Goals Management Logic with Backend ---
let goals = [];
const goalForm = document.getElementById('goal-form');
const goalsList = document.getElementById('goals-list');

// Load goals from backend
async function loadGoals() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/dashboard/get-goals?user_id=${currentUserId}&_=${Date.now()}`
        );

        const data = await response.json();
        
        goals = [];

        if (data && data.data) {
            goals = data.data.map(g => ({
                id: g.goal_id,
                category: g.category,
                target: parseFloat(g.target_amount || 0)
            }));
        }

        renderGoals();

    } catch (error) {
        console.error('Error loading goals:', error);
    }
}

// Add or update goal in backend
async function addGoalToBackend(category, targetAmount) {
    try {
        if (!currentUserId) {
            console.error('No user ID found');
            return false;
        }
        
        console.log('Adding/updating goal:', { category, targetAmount, userId: currentUserId });
        
        const response = await fetch(
            `${API_BASE_URL}/dashboard/add-goal?` +
            `user_id=${encodeURIComponent(currentUserId)}` +
            `&category=${encodeURIComponent(category)}` +
            `&target_amount=${targetAmount}`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        console.log('Backend response:', data);
        
        return data.success === true;
        
    } catch (error) {
        console.error('Error adding goal:', error);
        return false;
    }
}

// Delete goal from backend
async function deleteGoalFromBackend(goalId) {
    try {
        const response = await fetch(
            `${API_BASE_URL}/dashboard/delete-goal?goal_id=${goalId}`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        return data.success === true;
        
    } catch (error) {
        console.error('Error deleting goal:', error);
        return false;
    }
}

goalForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const category = document.getElementById('g-category').value;
    const target = parseFloat(document.getElementById('g-amount').value);

    // Show loading state
    const submitBtn = goalForm.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.textContent;
    submitBtn.textContent = 'Saving...';
    submitBtn.disabled = true;

    // Add/update goal in backend
    const success = await addGoalToBackend(category, target);
    
    if (success) {
        // Reload goals from backend to get the updated list
        await loadGoals();
        goalForm.reset();
    } else {
        alert('Error saving goal to database. Check console for details.');
    }

    // Reset button state
    submitBtn.textContent = originalBtnText;
    submitBtn.disabled = false;
});

async function deleteGoal(id) {
    
    const success = await deleteGoalFromBackend(id);
    
    if (success) {
        goals = goals.filter(g => g.id !== id);
        renderGoals();
    } else {
        alert('Error deleting goal from database');
    }
}

function renderGoals() {
    goalsList.innerHTML = '';
            
    if (goals.length === 0) {
        goalsList.innerHTML = '<p style="text-align: center; color: #888; font-style: italic; margin-top: 15px;">Let\'s make your first goal!</p>';
        return;
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
                <button onclick="deleteGoal('${g.id}')" class="delete-btn" style="padding: 2px 6px; font-size: 0.75rem;">X</button>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${percent}%; background-color: ${barColor};"></div>
            </div>
        `;
        goalsList.appendChild(goalDiv);
    });
}

// --- 3. Transaction Management with Backend ---
let transactions = [];
let editingTransactionId = null;
const transactionForm = document.getElementById('transaction-form');
const transactionList = document.getElementById('transaction-list');
const tSubmitBtn = document.getElementById('t-submit-btn');

// Load transactions from backend
async function loadTransactions() {
    try {
        const response = await fetch(`${API_BASE_URL}/transactions/get-transactions?user_id=${currentUserId}`);
        const data = await response.json();
        
        if (data && data.data) {
            transactions = data.data.map(t => ({
                id: t.transaction_id,
                desc: t.description,
                type: t.transaction_type,
                amount: parseFloat(t.amount)
            }));
            renderTransactions();
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

// Add transaction to backend
async function addTransactionToBackend(desc, type, amount) {
    try {
        const userEmail = localStorage.getItem("userEmail");
        
        if (!userEmail) {
            console.error('No user email found in localStorage');
            return false;
        }
        
        console.log('Adding transaction:', { desc, type, amount, email: userEmail });
        
        const response = await fetch(
            `${API_BASE_URL}/transactions/add-transaction?` +
            `email=${encodeURIComponent(userEmail)}` +
            `&amount=${amount}` +
            `&t_type=${encodeURIComponent(type)}` +
            `&m_id=${Date.now()}` +
            `&m_name=${encodeURIComponent(desc)}` +
            `&m_code=0000` +
            `&desc=${encodeURIComponent(desc)}` +
            `&recurr=false`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        console.log('Backend response:', data);
        
        return data.success === true;  // Check for success property
        
    } catch (error) {
        console.error('Error adding transaction:', error);
        return false;
    }
}

// Delete transaction from backend
async function deleteTransactionFromBackend(transactionId) {
    try {
        const response = await fetch(
            `${API_BASE_URL}/transactions/delete-transaction?transaction_id=${transactionId}`,
            { method: 'POST' }
        );
        return await response.json();
    } catch (error) {
        console.error('Error deleting transaction:', error);
        return false;
    }
}

transactionForm.addEventListener('submit', async function(e) {
    e.preventDefault(); 
    const desc = document.getElementById('t-desc').value;
    const type = document.getElementById('t-type').value;
    const amount = parseFloat(document.getElementById('t-amount').value);

    if (editingTransactionId !== null) {
        // Update existing transaction
        const index = transactions.findIndex(t => t.id === editingTransactionId);
        if (index !== -1) {
            transactions[index] = { id: editingTransactionId, desc, type, amount };
        }
        editingTransactionId = null; 
        tSubmitBtn.textContent = 'Add'; 
        transactionForm.reset();
        renderTransactions();
    } else {
        // Show loading state
        tSubmitBtn.textContent = 'Adding...';
        tSubmitBtn.disabled = true;
        
        // Add new transaction to backend
        const success = await addTransactionToBackend(desc, type, amount);
        
        if (success) {
            // Reload transactions from backend to get the new one
            await loadTransactions();
            transactionForm.reset();
        } else {
            alert('Error adding transaction to database. Check console for details.');
        }
        
        // Reset button state
        tSubmitBtn.textContent = 'Add';
        tSubmitBtn.disabled = false;
    }
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

async function deleteTransaction(id) {
    const success = await deleteTransactionFromBackend(id);
    
    if (success) {
        transactions = transactions.filter(t => t.id !== id);
            
        if (editingTransactionId === id) {
            transactionForm.reset();
            editingTransactionId = null;
            tSubmitBtn.textContent = 'Add';
        }
            
        renderTransactions();
    } else {
        alert('Error deleting transaction from database');
    }
}

function renderTransactions() {
    transactionList.innerHTML = '';

    if (transactions.length === 0) {
        transactionList.innerHTML = '<p style="text-align: center; color: #888; font-style: italic; margin-top: 15px;">No transactions yet. Add your first one above!</p>';
    } else {
        transactions.forEach(t => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span><strong>${t.desc}</strong> (${t.type})</span>
                <span>$${t.amount.toFixed(2)} 
                    <button onclick="editTransaction(${t.id})" style="background-color: #f0ad4e; color: white; border: none; border-radius: 4px; padding: 4px 8px; cursor: pointer; margin-left: 10px;">Edit</button>
                    <button onclick="deleteTransaction('${t.id}')" class="delete-btn">X</button>
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

// Initialize UI on first load
document.getElementById('display-balance').innerText = '$0.00';
renderTransactions();