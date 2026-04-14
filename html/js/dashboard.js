// --- Global Variables ---
const API_BASE_URL = "http://127.0.0.1:8000";
let currentUserId = null;
let transactions = [];
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

    if (isLoggedIn !== "true" || !currentUserId) {
        window.location.replace("login.html");
        return; 
    }

    // Unhide the settings profile button
    const profileCircle = document.getElementById("profile-circle");
    if (profileCircle) profileCircle.style.display = "flex";

    // Show the existing dashboard wrapper
    document.getElementById("existing-dashboard").style.display = "block";

    // Fetch the user's name for the profile circle and settings page!
    try {
        const profileRes = await fetch(`${API_BASE_URL}/account/get-profile?user_id=${currentUserId}`);
        const profileData = await profileRes.json();
        
        if (profileData.success) {
            const fName = profileData.first_name;
            const lName = profileData.last_name;
            
            // Use first name for the circle. If blank, fallback to email
            const displayName = fName || profileData.email;
            if (displayName) {
                const firstLetter = displayName.charAt(0).toUpperCase();
                const initialEl = document.getElementById("profile-initial");
                if (initialEl) initialEl.textContent = firstLetter;
                
                // Update the greeting text!
                const greetingEl = document.getElementById("dynamic-greeting");
                if (greetingEl) greetingEl.textContent = `Welcome back, ${fName || 'User'}!`;
            }
            
            // Save BOTH names to localStorage for the settings page!
            if (fName) localStorage.setItem("firstName", fName);
            if (lName) localStorage.setItem("lastName", lName);
        }
    } catch (e) {
        console.error("Could not load profile data", e);
    }

    // Load their data from the database
    await loadUserData();
    await loadGoals();
}

// --- 2. Load Core Data ---
async function loadUserData() {
    try {
        const response = await fetch(`${API_BASE_URL}/transactions/get-transactions?user_id=${currentUserId}`);
        const data = await response.json();
        
        if (data && data.data) {
            transactions = data.data;
        } else {
            transactions = [];
        }
        
        // Trigger all the visual updates
        refreshDashboardVisuals();

    } catch (error) {
        console.error('Error fetching transactions:', error);
    }
}

// Master function to update everything on the screen at once
function refreshDashboardVisuals() {
    fetchAndDisplayBalance();
    renderRecentTransactions();
    renderFullHistoryTable();
    updateChartData();
    renderGoals();
}

// --- 3. Time Filter Logic ---
function getFilteredTransactions() {
    const filterDropdown = document.getElementById('dashboard-timefilter');
    const filterValue = filterDropdown ? filterDropdown.value : 'all';
    
    // If they want everything, give them the whole array
    if (filterValue === 'all') return transactions;

    // Otherwise, do date math
    const daysToLookBack = parseInt(filterValue);
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysToLookBack);

    // Return only the transactions that happened AFTER the cutoff date
    return transactions.filter(t => {
        const txDate = new Date(t.created_at);
        return txDate >= cutoffDate;
    });
}

// Listen for the dropdown to change, and update the whole dashboard instantly!
const timeFilterEl = document.getElementById('dashboard-timefilter');
if (timeFilterEl) {
    timeFilterEl.addEventListener('change', function() {
        refreshDashboardVisuals();
    });
}

// --- 4. Dashboard Visuals (Balance & Chart) ---


// Fetches the exact balance from the database
async function fetchAndDisplayBalance() {
    try {
        const response = await fetch(`${API_BASE_URL}/account/get-balance?user_id=${currentUserId}`);
        const data = await response.json();
        
        const balanceDisplay = document.getElementById('display-balance');
        if (balanceDisplay && data.success) {
            const bal = parseFloat(data.balance || 0);
            balanceDisplay.innerText = `$${bal.toFixed(2)}`;
            
            // Make it red if negative, otherwise use the theme text color
            balanceDisplay.style.color = bal < 0 ? '#ff4d4d' : 'var(--text-color)';
        }
    } catch (error) {
        console.error("Error fetching balance:", error);
    }
}

// Opens and closes the Add Funds form
window.toggleAddFundsForm = function() {
    const form = document.getElementById('add-funds-form');
    if (form.style.display === 'none' || form.style.display === '') {
        form.style.display = 'block';
    } else {
        form.style.display = 'none';
    }
};

// Submits a "Quick Deposit" transaction to add money to the balance safely
window.submitQuickDeposit = async function() {
    const amountInput = document.getElementById('quick-deposit-input');
    const amount = parseFloat(amountInput.value);
    
    if (!amount || amount <= 0) {
        alert("Please enter a valid deposit amount.");
        return;
    }

    try {
        // We use your existing add-transaction endpoint so it logs the paper trail AND updates the balance!
        const userEmail = localStorage.getItem("userEmail") || "user@example.com"; 
        
        // Hardcoding 'Deposit' as the type and 'Quick Deposit' as the description
        const url = `${API_BASE_URL}/transactions/add-transaction?email=${encodeURIComponent(userEmail)}&amount=${amount}&t_type=Deposit&m_id=0&m_name=Quick Deposit&m_code=0&desc=Quick Deposit&recurr=false`;
        
        const response = await fetch(url, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            // Refresh the display, transaction lists, and hide the form!
            await loadUserData(); 
            toggleAddFundsForm();
            amountInput.value = ''; 
        } else {
            alert("Failed to process deposit. Check your server.");
        }
    } catch (error) {
        console.error("Deposit error:", error);
    }
};

function updateChartData() {
    const ctx = document.getElementById('spending-chart');
    if (!ctx) return;

    // Get the filtered transactions based on the dropdown
    const activeTransactions = getFilteredTransactions();

    const categoryTotals = {};
    
    activeTransactions.forEach(t => {
        const type = t.type || t.transaction_type;
        // Only graph expenses, ignore income
        if (type !== 'Income' && type !== 'Deposit') {
            const cat = type || 'Other';
            if (!categoryTotals[cat]) categoryTotals[cat] = 0;
            categoryTotals[cat] += parseFloat(t.amount);
        }
    });

    const labels = Object.keys(categoryTotals);
    const data = Object.values(categoryTotals);

    // Destroy the old chart before drawing a new one
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

// --- 5. Rendering Tables & Lists ---

// Renders just the top 5 most recent items for the quick "Manage Transactions" card
function renderRecentTransactions() {
    const list = document.getElementById('transaction-list');
    if (!list) return;
    
    list.innerHTML = '';
    
    // Sort newest to oldest, grab top 5
    const recentTx = [...transactions]
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

// Renders the big, full-width history ledger at the bottom
function renderFullHistoryTable() {
    const tableBody = document.getElementById('full-history-body');
    if (!tableBody) return;

    const filteredTx = getFilteredTransactions();

    if (filteredTx.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px;">No transactions found for this time period.</td></tr>';
        return;
    }

    const sortedTx = [...filteredTx].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    tableBody.innerHTML = ''; 

    sortedTx.forEach(t => {
        const dateObj = new Date(t.created_at);
        const niceDate = dateObj.toLocaleDateString();

        const type = t.type || t.transaction_type;
        const isIncome = (type === 'Income' || type === 'Deposit');
        const amountClass = isIncome ? 'amt-income' : 'amt-expense';
        const sign = isIncome ? '+' : '-';

        const desc = t.description || t.merchant_name || 'Transaction';
        const cat = type || 'Uncategorized';

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

// --- 6. Transaction Form Logic (Add & Edit) ---
const transactionForm = document.getElementById('transaction-form');
if (transactionForm) {
    transactionForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const desc = document.getElementById('t-desc').value;
        const type = document.getElementById('t-type').value;
        const amount = document.getElementById('t-amount').value;
        const tSubmitBtn = document.getElementById('t-submit-btn');

        if (editingTransactionId !== null) {
            // --- EDIT MODE ---
            tSubmitBtn.textContent = 'Updating...';
            tSubmitBtn.disabled = true;

            const success = await updateTransactionInBackend(editingTransactionId, desc, type, amount);

            if (success) {
                await loadUserData(); // Refresh from DB
                editingTransactionId = null; 
                tSubmitBtn.textContent = 'Add'; 
                transactionForm.reset();
            } else {
                alert('Error updating transaction.');
            }
            tSubmitBtn.disabled = false;
            
        } else {
            // --- ADD MODE ---
            tSubmitBtn.textContent = 'Adding...';
            tSubmitBtn.disabled = true;

            try {
                // Fetch to your Python backend
                const userEmail = localStorage.getItem("userEmail") || "user@example.com"; 
                const url = `${API_BASE_URL}/transactions/add-transaction?email=${encodeURIComponent(userEmail)}&amount=${amount}&t_type=${encodeURIComponent(type)}&m_id=0&m_name=${encodeURIComponent(desc)}&m_code=0&desc=${encodeURIComponent(desc)}&recurr=false`;
                
                const response = await fetch(url, { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    await loadUserData(); // Refresh from DB
                    transactionForm.reset();
                } else {
                    alert('Error: Could not save transaction.');
                }
            } catch (err) {
                console.error("Error adding transaction:", err);
            }
            tSubmitBtn.textContent = 'Add';
            tSubmitBtn.disabled = false;
        }
    });
}

// Pre-fill form for editing
window.editTransaction = function(id, desc, type, amount) {
    document.getElementById('t-desc').value = desc;
    document.getElementById('t-type').value = type;
    document.getElementById('t-amount').value = amount;
    
    editingTransactionId = id;
    document.getElementById('t-submit-btn').textContent = 'Update';
};

// Python fetch to update transaction
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

// Python fetch to delete transaction
window.deleteTransactionFromBackend = async function(id) {
    if (!confirm("Are you sure you want to delete this transaction?")) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/transactions/delete-transaction?transaction_id=${encodeURIComponent(id)}`, { method: 'POST' });
        const isDeleted = await response.json();
        if (isDeleted) {
            await loadUserData(); // Refresh from DB
        } else {
            alert('Failed to delete transaction.');
        }
    } catch (error) {
        console.error('Error deleting:', error);
    }
};

// --- 7. Goals Logic ---
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
    
    // 1. Populate the dropdown with the user's goals
    // Save the current selection so it doesn't reset when we redraw
    const currentSelection = selectBox.value; 
    selectBox.innerHTML = '<option value="">Select a Goal to view...</option>';
    
    goals.forEach(goal => {
        const option = document.createElement('option');
        option.value = goal.category;
        option.textContent = `${goal.category} (Target: $${parseFloat(goal.target_amount).toFixed(2)})`;
        selectBox.appendChild(option);
    });
    
    // Restore selection if it existed
    if (currentSelection) selectBox.value = currentSelection;

    // 2. Add the event listener to draw the arena when they pick a goal
    selectBox.removeEventListener('change', drawGamificationArena); // Prevent duplicates
    selectBox.addEventListener('change', drawGamificationArena);
    
    // Draw it immediately if something is already selected
    drawGamificationArena();
}
// Creates the physics world inside the jar
// Creates the physics world inside the jar
function initPhysicsEngine() {
    if (physicsEngine) return; 

    const jarContainer = document.getElementById('the-jar');
    const Engine = Matter.Engine,
          Render = Matter.Render,
          Runner = Matter.Runner,
          Bodies = Matter.Bodies,
          Composite = Matter.Composite;

    physicsEngine = Engine.create();

    // 1. Stretch the canvas to match the new 150x180 image
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

    // --- X-RAY VISION: TEMPORARILY RED AND VISIBLE ---
    const wallOptions = { isStatic: true, render: { visible: false } };
    
    // Reminder: Bodies.rectangle( x-center, y-center, width, height )
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

    // 1. Boot up the physics engine if it hasn't started yet
    initPhysicsEngine();

    // 2. Do the math
    const target = parseFloat(activeGoal.target_amount);
    const categoryTx = transactions.filter(t => (t.type || t.transaction_type) === category);
    
    let currentSpent = 0;
    categoryTx.forEach(t => currentSpent += parseFloat(t.amount));

    const isOverBudget = currentSpent > target;

    const mascot = document.getElementById('budgie-mascot');
    const statusText = document.getElementById('budgie-status-text');
    const jar = document.getElementById('the-jar');
    const readout = document.getElementById('goal-math-readout');

    jar.classList.remove('over-budget-shake');
    readout.innerHTML = `Spent: <strong style="color: ${isOverBudget ? '#ff4d4d' : 'var(--text-color)'}">$${currentSpent.toFixed(2)}</strong> / Target: $${target.toFixed(2)}`;

    // 3. PHYSICS LOGIC
    // If we swapped to a different goal in the dropdown, empty the jar completely!
    if (currentGoalCategory !== category) {
        Matter.World.clear(physicsEngine.world, true); // The 'true' keeps our invisible walls!
        currentGoalCategory = category;
    }

    if (isOverBudget) {
        mascot.src = '/html/images/sad budgie.png';
        statusText.textContent = "Oh no! Seeds lost!";
        statusText.style.color = '#ff4d4d';
        
        // Vaporize all the seeds and shake the jar
        Matter.World.clear(physicsEngine.world, true);
        setTimeout(() => jar.classList.add('over-budget-shake'), 10); 
        
    } else {
        mascot.src = '/html/images/budgie happy.png';
        statusText.textContent = "Looking good!";
        statusText.style.color = '#28a745';
        
        const targetSeeds = categoryTx.length;
        // Count how many dynamic objects (seeds) are currently in the physics world
        const currentSeeds = physicsEngine.world.bodies.filter(b => !b.isStatic).length;

        // If we have fewer seeds than transactions, drop the missing ones!
        if (targetSeeds > currentSeeds) {
            let seedsToAdd = targetSeeds - currentSeeds;
            
            // Drop them on a timer so they fall sequentially and collide
            let dropInterval = setInterval(() => {
                if (seedsToAdd <= 0) {
                    clearInterval(dropInterval);
                    return;
                }
                
                // Drop from the top, randomize the X axis slightly so they stack organically
                const dropX = 75 + (Math.random() * 30 - 15); 
                
                // Create an 8-sided polygon to simulate a rounded seed
                const seed = Matter.Bodies.polygon(dropX, -10, 8, 7, { 
                    restitution: 0.5, // Bounciness!
                    friction: 0.1,
                    render: { fillStyle: '#f5c542' }
                });
                
                Matter.Composite.add(physicsEngine.world, seed);
                seedsToAdd--;
            }, 300); // 300ms between each drop
            
        } else if (targetSeeds < currentSeeds) {
            // If they deleted a transaction, the easiest fix is to empty the jar and let the function redraw it
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
        const amount = document.getElementById('g-amount').value;

        try {
            const response = await fetch(`${API_BASE_URL}/dashboard/add-goal?user_id=${currentUserId}&category=${encodeURIComponent(category)}&target_amount=${amount}`, { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                await loadGoals();
                goalForm.reset();
            } else {
                alert('Error adding goal.');
            }
        } catch (err) {
            console.error('Goal Error:', err);
        }
    });
}

window.deleteGoal = async function(goalId) {
    if (!confirm("Remove this goal?")) return;
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

// --- 8. Global Logout Logic ---
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

// Run security check as soon as the file loads
secureDashboard();