// --- Global Variables ---
const API_BASE_URL = "https://software-capstone-project.onrender.com";
let currentUserId = null;
let currentSortCol = 'date';
let currentSortAsc = false; // false = descending (newest first), true = ascending

// 1. Your two data nests!
let allTransactions = []; // The vault containing EVERYTHING
let activeTransactions = []; // The filtered list currently on screen

let goals = [];
let spendingChart = null; // Holds the Chart.js instance
let editingTransactionId = null;

// --- Physics Variables ---
let physicsEngine = null;
let physicsRender = null;
let currentGoalCategory = null;


// --- 1. Security & Profile Initialization ---
async function secureDashboard() {
    const isLoggedIn = localStorage.getItem("isLoggedIn");
    currentUserId = localStorage.getItem("userId");

    const savedTimeframe = localStorage.getItem('prefTimeframe');
    const filterDropdown = document.getElementById('timeframe-filter');
    
    if (savedTimeframe && filterDropdown) {
        filterDropdown.value = savedTimeframe;
        
        // If you have a function that updates your charts when the dropdown changes, 
        // you would call it right here! For example:
        // updateChartsForTimeframe(savedTimeframe); 
    }
    if (isLoggedIn !== "true" || !currentUserId) {
        window.location.replace("login.html");
        return; 
    }

    const profileCircle = document.getElementById("profile-circle");
    if (profileCircle) profileCircle.style.display = "flex";

    document.getElementById("existing-dashboard").style.display = "block";

    try {
        const profileRes = await fetch(`${API_BASE_URL}/account/get-profile?user_id=${currentUserId}`);
        const profileData = await profileRes.json();
        
        if (profileData.success) {
            const fName = profileData.first_name;
            const lName = profileData.last_name;
            
            // 1. UPDATE THE PROFILE CIRCLE INITIAL
            // If they have a first name, use it. Otherwise, fallback to email letter!
            const displayName = fName || profileData.email || "U";
            const firstLetter = displayName.charAt(0).toUpperCase();
            
            const initialEl = document.getElementById("profile-initial");
            if (initialEl) initialEl.textContent = firstLetter;
            
            // 2. UPDATE THE DASHBOARD GREETING
            const greetingEl = document.getElementById("dynamic-greeting");
            if (greetingEl) {
                const hour = new Date().getHours();
                let timeGreeting = "Good evening"; 
                
                if (hour < 12) {
                    timeGreeting = "Good morning"; 
                } else if (hour < 18) {
                    timeGreeting = "Good afternoon"; 
                }
                
                // Uses their First Name, or "User" if they left it blank
                greetingEl.textContent = `${timeGreeting}, ${fName || 'User'}!`;
            }
            
            // Save to local storage so Settings.html can use it too
            if (fName) localStorage.setItem("firstName", fName);
            if (lName) localStorage.setItem("lastName", lName);
        }
    } catch (e) {
        console.error("Could not load profile data", e);
    }

    await loadUserData();
    await loadGoals();

    setTimeout(startTour, 500);
}

// --- 2. Data Loading & Filtering ---
async function loadUserData() {
    try {
        // 1. Show the skeletons before we fetch from Render
        const skeletons = document.getElementById('loading-skeletons');
        const transactionList = document.getElementById('transaction-list');
        if (skeletons && transactionList) {
            skeletons.style.display = 'block';
            transactionList.style.display = 'none';
        }

        const response = await fetch(`${API_BASE_URL}/transactions/get-transactions?user_id=${currentUserId}`);
        const data = await response.json();
        
        if (data && data.data) {
            allTransactions = data.data; 
        } else {
            allTransactions = [];
        }
        
        applyTimeFilter();

        // 2. Hide the skeletons and show the real data now that it's loaded!
        if (skeletons && transactionList) {
            skeletons.style.display = 'none';
            transactionList.style.display = 'block'; // Or 'ul' depending on your CSS, but block usually works best!
        }

    } catch (error) {
        console.error('Error fetching transactions:', error);
        
        // If the server crashes, hide the skeletons so it doesn't spin forever
        const skeletons = document.getElementById('loading-skeletons');
        if (skeletons) skeletons.style.display = 'none';
    }
}

function applyTimeFilter() {
    const timeframeFilter = document.getElementById('timeframe-filter');
    const selectedDays = timeframeFilter ? timeframeFilter.value : "all";

    if (selectedDays === "all") {
        activeTransactions = [...allTransactions]; 
    } else {
        const daysToSubtract = parseInt(selectedDays, 10);
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - daysToSubtract);

        activeTransactions = allTransactions.filter(tx => {
            const txDate = new Date(tx.created_at);
            return txDate >= cutoffDate;
        });
    }

    refreshDashboardVisuals();
}

document.addEventListener('DOMContentLoaded', () => {
    const dropdown = document.getElementById('timeframe-filter');
    if (dropdown) {
        dropdown.addEventListener('change', applyTimeFilter);
    }
});

// Master function to update everything on the screen at once
function refreshDashboardVisuals() {
    fetchAndDisplayBalance();
    renderRecentTransactions();
    renderFullHistoryTable();
    updateChartData();
    renderGoals(); // Goals and gamification update too!
}


// --- 3. Dashboard Visuals (Balance & Chart) ---
async function fetchAndDisplayBalance() {
    try {
        const response = await fetch(`${API_BASE_URL}/account/get-balance?user_id=${currentUserId}`);
        const data = await response.json();
        
        const balanceDisplay = document.getElementById('display-balance');
        if (balanceDisplay && data.success) {
            const bal = parseFloat(data.balance || 0);
            balanceDisplay.innerText = `$${bal.toFixed(2)}`;
            balanceDisplay.style.color = bal < 0 ? '#ff4d4d' : 'var(--text-color)';
        }
    } catch (error) {
        console.error("Error fetching balance:", error);
    }
}

window.toggleAddFundsForm = function() {
    const form = document.getElementById('add-funds-form');
    if (form.style.display === 'none' || form.style.display === '') {
        form.style.display = 'block';
    } else {
        form.style.display = 'none';
    }
};

window.submitQuickDeposit = async function() {
    const amountInput = document.getElementById('quick-deposit-input');
    // Strip everything except numbers and decimals!
    const cleanAmount = amountInput.value.replace(/[^0-9.]/g, ''); 
    const amount = parseFloat(cleanAmount);
    if (!amount || amount <= 0) {
        showToast("Please enter a valid deposit amount.", "error");
        return;
    }

    try {
        const userEmail = localStorage.getItem("userEmail") || "user@example.com"; 
        const url = `${API_BASE_URL}/transactions/add-transaction?email=${encodeURIComponent(userEmail)}&amount=${amount}&t_type=Income&m_id=0&m_name=Quick Deposit&m_code=0&desc=Quick Deposit&recurr=false`;        
        const response = await fetch(url, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            await loadUserData(); 
            toggleAddFundsForm();
            amountInput.value = ''; 
        } else {
            showToast("Failed to process deposit. Check your server.", "error");
        }
    } catch (error) {
        console.error("Deposit error:", error);
    }
};

function updateChartData() {
    const ctx = document.getElementById('spending-chart');
    if (!ctx) return;

    const categoryTotals = {};
    
    // Rely exclusively on activeTransactions
    activeTransactions.forEach(t => {
        const type = t.type || t.transaction_type;
        if (type !== 'Income' && type !== 'Deposit') {
            const cat = type || 'Other';
            if (!categoryTotals[cat]) categoryTotals[cat] = 0;
            categoryTotals[cat] += parseFloat(t.amount);
        }
    });

    const labels = Object.keys(categoryTotals);
    const data = Object.values(categoryTotals);

    if (spendingChart) {
        spendingChart.destroy();
    }

    spendingChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.length > 0 ? labels : ['No Expenses'],
            datasets: [{
                data: data.length > 0 ? data : [1],
                backgroundColor: data.length > 0 ? ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'] : ['#e0e0e0']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

// --- 4. Rendering Tables & Lists ---
function renderRecentTransactions() {
    const list = document.getElementById('transaction-list');
    if (!list) return;
    
    list.innerHTML = '';
    
    const recentTx = [...activeTransactions]
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 5);

    recentTx.forEach(t => {
        const li = document.createElement('li');
        const desc = t.description || t.merchant_name || 'Item';
        const type = t.type || t.transaction_type;
        const sign = (type === 'Income' || type === 'Deposit') ? '+' : '-';
        
        li.innerHTML = `
            <span><strong>${desc}</strong> (${type}) - ${sign}$${parseFloat(t.amount).toFixed(2)}</span>
            <div>
                <button class="action-btn" style="padding: 4px 8px; font-size: 0.8rem; margin-right: 5px;" onclick="editTransaction('${t.transaction_id}', '${desc}', '${type}', '${t.amount}')">Edit</button>
                <button class="delete-btn" onclick="deleteTransactionFromBackend('${t.transaction_id}')">X</button>
            </div>
        `;
        list.appendChild(li);
    });
}

window.sortTable = function(column) {
    // If clicking the same column, flip the direction. Otherwise, switch columns.
    if (currentSortCol === column) {
        currentSortAsc = !currentSortAsc; 
    } else {
        currentSortCol = column;
        currentSortAsc = column === 'date' ? false : true; // Dates default to newest, text defaults to A-Z
    }
    
    // Update the directional arrow icons
    ['date', 'desc', 'cat', 'amount'].forEach(col => {
        const iconEl = document.getElementById(`sort-icon-${col}`);
        if (iconEl) {
            if (col === currentSortCol) {
                iconEl.textContent = currentSortAsc ? '▲' : '▼';
            } else {
                iconEl.textContent = ''; // Hide arrows on inactive columns
            }
        }
    });

    // Redraw the table!
    renderFullHistoryTable();
};

function renderFullHistoryTable() {
    const tableBody = document.getElementById('full-history-body');
    if (!tableBody) return;

    if (activeTransactions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px;">No transactions found for this time period.</td></tr>';
        return;
    }

    // --- THE NEW SORTING ENGINE ---
    let sortedTx = [...activeTransactions];
    
    sortedTx.sort((a, b) => {
        let valA, valB;
        
        // Grab the right data based on what column is active
        if (currentSortCol === 'date') {
            valA = new Date(a.created_at).getTime();
            valB = new Date(b.created_at).getTime();
        } else if (currentSortCol === 'amount') {
            valA = parseFloat(a.amount);
            valB = parseFloat(b.amount);
        } else if (currentSortCol === 'desc') {
            valA = (a.description || a.merchant_name || '').toLowerCase();
            valB = (b.description || b.merchant_name || '').toLowerCase();
        } else if (currentSortCol === 'cat') {
            valA = (a.type || a.transaction_type || '').toLowerCase();
            valB = (b.type || b.transaction_type || '').toLowerCase();
        }

        // Compare the values and return the proper direction
        if (valA < valB) return currentSortAsc ? -1 : 1;
        if (valA > valB) return currentSortAsc ? 1 : -1;
        return 0;
    });

    tableBody.innerHTML = ''; 

    // Draw the newly sorted rows
    sortedTx.forEach(t => {
        const dateObj = new Date(t.created_at);
        const niceDate = dateObj.toLocaleDateString();

        const type = t.type || t.transaction_type;
        const isIncome = (type === 'Income' || type === 'Deposit');
        const amountClass = isIncome ? 'amt-income' : 'amt-expense';
        const sign = isIncome ? '+' : '-';

        const desc = t.description || t.merchant_name || 'Transaction';
        const cat = type || 'Uncategorized';
        let flagHtml = "";
        const showLargeTxFlag = localStorage.getItem('prefLargeTx') === 'true';
        if (showLargeTxFlag && !isIncome && parseFloat(t.amount) >= 100) {
            flagHtml = `<span title="Large Transaction" style="background: #ff4d4d; color: white; padding: 2px 5px; border-radius: 4px; font-size: 0.7rem; margin-left: 8px;">🚩 HIGH</span>`;
        }
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${niceDate}</td>
            <td><strong>${desc}</strong></td>
            <td>${cat}</td>
            <td class="${amountClass}">${sign}$${parseFloat(t.amount).toFixed(2)}</td>
        `;
        tableBody.appendChild(row);
    });
}

// --- 5. Transaction Form Logic (Add & Edit) ---
const transactionForm = document.getElementById('transaction-form');
if (transactionForm) {
    transactionForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const desc = document.getElementById('t-desc').value;
        const type = document.getElementById('t-type').value;
        const rawAmount = document.getElementById('t-amount').value;
        const amount = rawAmount.replace(/[^0-9.]/g, ''); // Strip symbols!
        const tSubmitBtn = document.getElementById('t-submit-btn');

        if (editingTransactionId !== null) {
            tSubmitBtn.textContent = 'Updating...';
            tSubmitBtn.disabled = true;

            const success = await updateTransactionInBackend(editingTransactionId, desc, type, amount);

            if (success) {
                await loadUserData(); 
                editingTransactionId = null; 
                tSubmitBtn.textContent = 'Add'; 
                transactionForm.reset();
                showToast("Transaction updated!", "success");
            } else {
                showToast("Error updating transaction.", "error");
            }
            tSubmitBtn.disabled = false;
            
        } else {
            tSubmitBtn.textContent = 'Adding...';
            tSubmitBtn.disabled = true;

            try {
                const userEmail = localStorage.getItem("userEmail") || "user@example.com"; 
                const url = `${API_BASE_URL}/transactions/add-transaction?email=${encodeURIComponent(userEmail)}&amount=${amount}&t_type=${encodeURIComponent(type)}&m_id=0&m_name=${encodeURIComponent(desc)}&m_code=0&desc=${encodeURIComponent(desc)}&recurr=false`;
                
                const response = await fetch(url, { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    await loadUserData(); 
                    transactionForm.reset();
                    showToast("Transaction added!", "success");
                } else {
                    showToast("Error: Could not save transaction.", "error");
                }
            } catch (err) {
                console.error("Error adding transaction:", err);
            }
            tSubmitBtn.textContent = 'Add';
            tSubmitBtn.disabled = false;
        }
    });
}

window.editTransaction = function(id, desc, type, amount) {
    document.getElementById('t-desc').value = desc;
    document.getElementById('t-type').value = type;
    document.getElementById('t-amount').value = amount;
    
    editingTransactionId = id;
    document.getElementById('t-submit-btn').textContent = 'Update';
};

async function updateTransactionInBackend(id, desc, type, amount) {
    try {
        const response = await fetch(
            `${API_BASE_URL}/transactions/update-transaction?` +
            `transaction_id=${encodeURIComponent(id)}` +
            `&amount=${amount}` +
            `&t_type=${encodeURIComponent(type)}` +
            `&desc=${encodeURIComponent(desc)}`,
            { method: 'POST' }
        );
        const data = await response.json();
        return data.success === true;
    } catch (error) {
        console.error('Error updating transaction:', error);
        return false;
    }
}

window.deleteTransactionFromBackend = async function(id) {
    const isConfirmed = await budgieConfirm("Delete Transaction?", "Are you absolutely sure you want to delete this transaction? This cannot be undone.");
if (!isConfirmed) return;
    try {
        const response = await fetch(`${API_BASE_URL}/transactions/delete-transaction?transaction_id=${encodeURIComponent(id)}`, { method: 'POST' });
        const isDeleted = await response.json();
        if (isDeleted) {
            await loadUserData(); 
            showToast("Transaction deleted.", "success");
        } else {
            showToast("Failed to delete transaction.", "error");
        }
    } catch (error) {
        console.error('Error deleting:', error);
    }
};

// --- 6. Goals Logic ---
async function loadGoals() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/get-goals?user_id=${currentUserId}`);
        const data = await response.json();
        goals = data.data || [];
        renderGoals();
    } catch (error) {
        console.error('Error fetching goals:', error);
    }
}

function renderGoals() {
    const selectBox = document.getElementById('goal-visualizer-select');
    if (!selectBox) return;
    
    const currentSelection = selectBox.value; 
    selectBox.innerHTML = '<option value="">Select a Goal to view...</option>';
    
    goals.forEach(goal => {
        const option = document.createElement('option');
        option.value = goal.category;
        option.textContent = `${goal.category} (Target: $${parseFloat(goal.target_amount).toFixed(2)})`;
        selectBox.appendChild(option);
    });
    
    if (currentSelection) selectBox.value = currentSelection;

    selectBox.removeEventListener('change', drawGamificationArena); 
    selectBox.addEventListener('change', drawGamificationArena);
    
    drawGamificationArena();
}

function initPhysicsEngine() {
    if (physicsEngine) return; 

    const jarContainer = document.getElementById('the-jar');
    const Engine = Matter.Engine,
          Render = Matter.Render,
          Runner = Matter.Runner,
          Bodies = Matter.Bodies,
          Composite = Matter.Composite;

    physicsEngine = Engine.create();

    physicsRender = Render.create({
        element: jarContainer,
        engine: physicsEngine,
        options: {
            width: 150,
            height: 180,
            background: 'transparent',
            wireframes: false 
        }
    });

    const wallOptions = { isStatic: true, render: { visible: false } };
    
    const leftWall = Bodies.rectangle(37, 90, 10, 180, wallOptions); 
    const rightWall = Bodies.rectangle(115, 90, 10, 180, wallOptions); 
    const floor = Bodies.rectangle(80, 160, 150, 20, wallOptions); 

    Composite.add(physicsEngine.world, [leftWall, rightWall, floor]);
    Render.run(physicsRender);
    Runner.run(Runner.create(), physicsEngine);
}

function drawGamificationArena() {
    const selectBox = document.getElementById('goal-visualizer-select');
    const arena = document.getElementById('gamification-arena');
    const category = selectBox.value;

    if (!category) {
        arena.style.display = 'none';
        return;
    }

    const activeGoal = goals.find(g => g.category === category);
    if (!activeGoal) return;

    arena.style.display = 'block';

    initPhysicsEngine();

    const target = parseFloat(activeGoal.target_amount);
    
    // Use activeTransactions here so the seeds only show for the selected date range!
    const categoryTx = activeTransactions.filter(t => (t.type || t.transaction_type) === category);
    
    let currentSpent = 0;
    categoryTx.forEach(t => currentSpent += parseFloat(t.amount));

    const isOverBudget = currentSpent > target;
    const wantsDangerAlerts = localStorage.getItem('prefGoalDanger') === 'true';
    const percentSpent = currentSpent / target;
    
    // If they are between 90% and 99.9% spent, fire a warning toast!
    if (wantsDangerAlerts && percentSpent >= 0.90 && percentSpent < 1.0) {
        showToast(`Careful! You have spent ${Math.round(percentSpent * 100)}% of your ${category} budget.`, "warning");
    }
    const mascot = document.getElementById('budgie-mascot');
    const statusText = document.getElementById('budgie-status-text');
    const jar = document.getElementById('the-jar');
    const readout = document.getElementById('goal-math-readout');

    jar.classList.remove('over-budget-shake');
    readout.innerHTML = `Spent: <strong style="color: ${isOverBudget ? '#ff4d4d' : 'var(--text-color)'}">$${currentSpent.toFixed(2)}</strong> / Target: $${target.toFixed(2)}`;

    if (currentGoalCategory !== category) {
        Matter.World.clear(physicsEngine.world, true); 
        currentGoalCategory = category;
    }

    if (isOverBudget) {
        mascot.src = './images/sad-budgie.png';
        statusText.textContent = "Oh no! Seeds lost!";
        statusText.style.color = '#ff4d4d';
        
        Matter.World.clear(physicsEngine.world, true);
        setTimeout(() => jar.classList.add('over-budget-shake'), 10); 
        
    } else {
        mascot.src = './images/budgie-happy.png';
        statusText.textContent = "Looking good!";
        statusText.style.color = '#28a745';
        
        const targetSeeds = categoryTx.length;
        const currentSeeds = physicsEngine.world.bodies.filter(b => !b.isStatic).length;

        if (targetSeeds > currentSeeds) {
            let seedsToAdd = targetSeeds - currentSeeds;
            
            let dropInterval = setInterval(() => {
                if (seedsToAdd <= 0) {
                    clearInterval(dropInterval);
                    return;
                }
                
                const dropX = 75 + (Math.random() * 30 - 15); 
                
                const seed = Matter.Bodies.polygon(dropX, -10, 8, 7, { 
                    restitution: 0.5, 
                    friction: 0.1,
                    render: { fillStyle: '#f5c542' }
                });
                
                Matter.Composite.add(physicsEngine.world, seed);
                seedsToAdd--;
            }, 300); 
            
        } else if (targetSeeds < currentSeeds) {
             Matter.World.clear(physicsEngine.world, true);
             setTimeout(drawGamificationArena, 50); 
        }
    }
}

const goalForm = document.getElementById('goal-form');
if (goalForm) {
    goalForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const category = document.getElementById('g-category').value;
        const rawAmount = document.getElementById('g-amount').value;
        const amount = rawAmount.replace(/[^0-9.]/g, ''); // Strip symbols!
        try {
            const response = await fetch(`${API_BASE_URL}/dashboard/add-goal?user_id=${currentUserId}&category=${encodeURIComponent(category)}&target_amount=${amount}`, { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                await loadGoals();
                goalForm.reset();
                showToast("Goal saved successfully!", "success");
            } else {
                showToast("Error adding goal.", "error");
            }
        } catch (err) {
            console.error('Goal Error:', err);
        }
    });
}

window.deleteGoal = async function(goalId) {
    const isConfirmed = await budgieConfirm("Delete Goal?", "Are you sure you want to remove this savings goal permanently?");
    if (!isConfirmed) return;
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/delete-goal?goal_id=${goalId}`, { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            await loadGoals();
        }
    } catch (err) {
        console.error('Goal delete error:', err);
    }
};

// --- 7. Global Logout Logic ---
const logoutBtns = [document.getElementById('logout-btn-existing'), document.getElementById('logout-btn-new')];
logoutBtns.forEach(btn => {
    if (btn) {
        btn.addEventListener('click', function() {
            localStorage.removeItem("isLoggedIn");
            localStorage.removeItem("userId");
            localStorage.removeItem("userEmail");
            window.location.replace("index.html");
        });
    }
});

// --- 8. AI Statement Auto-Importer ---
const importBtn = document.getElementById('import-statement-btn');
if (importBtn) {
    importBtn.addEventListener('click', async function() {
        const fileInput = document.getElementById('statement-upload');
        const statusArea = document.getElementById('import-status-area');
        const statusText = document.getElementById('import-status-text');
        const progressBar = document.getElementById('import-progress-bar');
        const file = fileInput.files[0];

        if (!file) {
            showToast("Please select a PDF statement first.", "error");
            return;
        }

        importBtn.disabled = true;
        importBtn.textContent = "Reading...";
        statusArea.style.display = "block";
        statusText.style.color = "var(--text-color)";
        statusText.textContent = "Budgie AI is extracting your transactions...";
        progressBar.style.width = "5%"; 

        let progress = 5;
        const loadingInterval = setInterval(() => {
            progress += (90 - progress) * 0.1; 
            progressBar.style.width = `${progress}%`;
        }, 300);

        const formData = new FormData();
        formData.append("user_id", currentUserId); 
        formData.append("file", file);

        try {
            const response = await fetch(`https://software-capstone-project.onrender.com/api/import-statement`, {
                method: "POST",
                body: formData
            });
            const data = await response.json();

            clearInterval(loadingInterval);

            if (data.success) {
                progressBar.style.width = "100%";
                statusText.style.color = "#28a745";
                statusText.textContent = `Success! Imported ${data.count} transactions.`;
                
                if (typeof loadUserData === "function") await loadUserData();
                fileInput.value = "";
            } else {
                progressBar.style.width = "0%";
                statusText.style.color = "#ff4d4d";
                statusText.textContent = data.error || "Failed to import.";
            }
        } catch (err) {
            clearInterval(loadingInterval);
            progressBar.style.width = "0%";
            console.error("Import Error:", err);
            statusText.style.color = "#ff4d4d";
            statusText.textContent = "Server error. Check Python terminal!";
        }

        importBtn.disabled = false;
        importBtn.textContent = "Import via AI";
    });
}

// --- 9. ONBOARDING TOUR LOGIC ---
const tourSteps = [
    {
        title: "Welcome to Budgie! 🐦",
        text: "I'll be your wingman for getting your finances on track. Let's take a quick look around.",
        targetId: null 
    },
    {
        title: "Your Total Balance 💰",
        text: "This is your command center. Your balance updates automatically whenever you add income or expenses.",
        targetId: "tour-balance-card",
        placement: "right" // 👇 NEW: Tells it to sit to the right side!
    },
    {
        title: "Log Your Transactions 💳",
        text: "Use this area to manually enter your expenses or income.",
        targetId: "tour-transaction-area",
        placement: "left" // 👇 NEW: Sits to the left!
    },
    {
        title: "The Goal Visualizer 🎯",
        text: "Select a category from this dropdown to watch the physics engine drop seeds into your goal jar!",
        targetId: "tour-goal-dropdown",
        placement: "right"
    },
    {
        title: "Ask Budgie AI 🤖",
        text: "Need financial advice or help reading a bank statement? Click here to chat with me anytime!",
        targetId: "tour-ai-button",
        placement: "left" // 👇 NEW: Keeps it from falling off the top!
    },
    {
        title: "Settings & Profile ⚙️",
        text: "Customize your theme, download your data, or update your password right here.",
        targetId: "profile-circle",
        placement: "left"
    }
];

let currentTourStep = 0;

function startTour() {
    // Check if they've already taken the tour
    if (localStorage.getItem("hasSeenBudgieTour") === "true") return;

    const overlay = document.getElementById('tour-overlay');
    if (!overlay) return;

    overlay.style.display = 'flex';
    renderTourStep();

    document.getElementById('tour-next').onclick = () => {
        currentTourStep++;
        if (currentTourStep >= tourSteps.length) {
            endTour();
        } else {
            renderTourStep();
        }
    };

    document.getElementById('tour-skip').onclick = endTour;
}

function renderTourStep() {
    const step = tourSteps[currentTourStep];
    
    document.getElementById('tour-title').textContent = step.title;
    document.getElementById('tour-text').textContent = step.text;
    document.getElementById('tour-progress').textContent = `${currentTourStep + 1} / ${tourSteps.length}`;
    
    const nextBtn = document.getElementById('tour-next');
    if (currentTourStep === tourSteps.length - 1) {
        nextBtn.textContent = "Finish ✓";
        nextBtn.style.backgroundColor = "#28a745"; 
    } else {
        nextBtn.textContent = "Next ➔";
        nextBtn.style.backgroundColor = ""; 
    }

    // Remove highlight from previous elements
    document.querySelectorAll('.tour-highlight').forEach(el => el.classList.remove('tour-highlight'));

    const tourBox = document.querySelector('.tour-box');

    if (step.targetId) {
        const targetEl = document.getElementById(step.targetId);
        if (targetEl) {
            targetEl.classList.add('tour-highlight');
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

            setTimeout(() => {
                const rect = targetEl.getBoundingClientRect();
                const boxRect = tourBox.getBoundingClientRect();
                let top, left;

                // 1. Read the placement preference (default to bottom)
                const placement = step.placement || "bottom";

                // 2. Calculate coordinates based on the requested side
                if (placement === "left") {
                    top = rect.top + (rect.height / 2) - (boxRect.height / 2);
                    left = rect.left - boxRect.width - 20;
                } else if (placement === "right") {
                    top = rect.top + (rect.height / 2) - (boxRect.height / 2);
                    left = rect.right + 20;
                } else if (placement === "top") {
                    top = rect.top - boxRect.height - 20;
                    left = rect.left + (rect.width / 2) - (boxRect.width / 2);
                } else { // bottom
                    top = rect.bottom + 20;
                    left = rect.left + (rect.width / 2) - (boxRect.width / 2);
                }

                // 3. THE SAFETY NET: Keep it strictly inside the screen bounds!
                // If it tries to go off the top, push it down to 10px
                if (top < 10) top = 10;
                // If it tries to go off the left, push it right to 10px
                if (left < 10) left = 10;
                // If it tries to fall off the bottom, snap it above the bottom edge
                if (top + boxRect.height > window.innerHeight) top = window.innerHeight - boxRect.height - 10;
                // If it tries to fall off the right side, snap it inside the right edge
                if (left + boxRect.width > window.innerWidth) left = window.innerWidth - boxRect.width - 10;

                // 4. Apply the final safe coordinates
                tourBox.style.top = `${top}px`;
                tourBox.style.left = `${left}px`;
                tourBox.style.transform = "none"; 
            }, 300); 
        }
    } else {
        // Welcome screen: Dead center
        tourBox.style.top = "50%";
        tourBox.style.left = "50%";
        tourBox.style.transform = "translate(-50%, -50%)";
    }
}

function endTour() {
    document.getElementById('tour-overlay').style.display = 'none';
    document.querySelectorAll('.tour-highlight').forEach(el => el.classList.remove('tour-highlight'));
    // Permanently save that they finished it so it never bothers them again
    localStorage.setItem("hasSeenBudgieTour", "true");
}
// Kick off the application!
secureDashboard();