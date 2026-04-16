from fastapi import FastAPI
from db import supabase
from datetime import datetime
import bcrypt
import uuid
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from budgie_bot import get_ai_reply

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (use specific URLs in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# pull from db: response = supabase.table("TABLE_NAME").select("* (ALL)").execute()
# write to db: response = supabase.table("TABLE_NAME").insert(data - typically a dict).execute()
# update db: response = supabase.table("TABLE_NAME")\.update({"column name": "column value"})\.eq("value", what_value_equals)\.execute()
# delete from db: response = supabase.table("TABLE_NAME")\.delete()\.eq("value", what value equals)\.execute()
# return response

# Verify's the users credentials
# Pre: takes user email and password as parameters
# Post: returns True if the login is valid, False otherwise
@app.get("/login")
def verify_login(email, passw):
    try: 
        users = supabase.table("users").select("*").execute()

        for user in users.data:
            e = user.get('email')
            p = user.get('password_hash')
            if e == email:
                byte_pwd = passw.encode('utf-8')
                salt_bytes = user.get('password_salt').encode('utf-8')
                pw_hash_bytes = bcrypt.hashpw(byte_pwd, salt_bytes)
                pw_hash = pw_hash_bytes.decode('utf-8')

                if pw_hash == p:
                    return {"success": True, "user_id": user.get('user_id')}  # Return user_id
            
        return {"success": False}
    
    except Exception as e:
        print('error: ', e)
        return {"success": False}

# Create's a user account
# Pre: takes user email and password as parameters
# Post: returns True if the account was successfully created, False otherwise
# Create's a user account along with customer and account rows
@app.post("/create-account")
def create_account(email, passw, firstN, lastN):
    byte_pwd = passw.encode('utf-8')
    salt_bytes = bcrypt.gensalt()
    pw_hash_bytes = bcrypt.hashpw(byte_pwd, salt_bytes)
    salt = salt_bytes.decode('utf-8')
    pw_hash = pw_hash_bytes.decode('utf-8')
    now_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    user_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    user_data = {
        'user_id': user_id,
        'email': email,
        'password_hash': pw_hash,
        'password_salt': salt,
        'role': 'customer',
        'created_at': now_timestamp,
        'password_updated_at': now_timestamp,
        'account_id': account_id
    }

    customer_data = {
        'customer_id': customer_id,
        'user_id': user_id,
        'first_name': firstN,
        'last_name': lastN,
        'created_at': now_timestamp
    }

    account_data = {
        'account_id': account_id,
        'customer_id': customer_id,
        'account_type': 'checking',
        'balance': 0.0,
        'created_at': now_timestamp
    }

    try:
        # Insert user
        supabase.table("users").insert(user_data).execute()
        # Insert customer
        supabase.table("customers").insert(customer_data).execute()
        # Insert account
        supabase.table("accounts").insert(account_data).execute()

        return {"success": True, "user_id": user_id, "customer_id": customer_id, "account_id": account_id}
    except Exception as e:
        print("Error creating account:", e)
        return {"success": False, "error": str(e)}


# Deletes the users account
# Pre: takes an email as a parameter
# Post: returns True if the account was deleted, false otherwise
@app.post("/account/delete-account")
def delete_account(email):
    try:
        users_resp = supabase.table("users").select("*").eq("email", email).execute()
        if not users_resp.data or len(users_resp.data) == 0:
            return {"success": False, "error": "User not found"}

        user = users_resp.data[0]
        account_id = user.get("account_id")
        user_id = user.get("user_id")

        # Delete transactions tied to the account
        supabase.table("transactions").delete().eq("account_id", account_id).execute()

        # Delete goals tied to the account
        supabase.table("goals").delete().eq("account_id", account_id).execute()

        # Delete account row
        supabase.table("accounts").delete().eq("account_id", account_id).execute()

        # Delete customer row
        supabase.table("customers").delete().eq("user_id", user_id).execute()

        # Delete user row
        supabase.table("users").delete().eq("user_id", user_id).execute()

        return {"success": True}
    except Exception as e:
        print("Error deleting account:", e)
        return {"success": False, "error": str(e)}

# Gets all transactions tied to the specified user
# Pre: takes a user ID as a parameter
# Post: returns a list of dictionaries - each dictionary is a transaction
@app.get("/transactions/get-transactions")
def get_transactions(user_id):
    try:
        users = supabase.table("users").select("*").execute()
        for user in users.data:
            if user.get('user_id') == user_id:
                acc_id = user.get('account_id')
                return supabase.table("transactions").select("*").eq('account_id', acc_id).execute()
        
        return False
    except Exception as e:

        return False

# Adds a transaction to the user's account and updates balance
@app.post("/transactions/add-transaction")
def add_transaction(email, amount, t_type, m_id, m_name, m_code, desc, recurr):
    try:
        users = supabase.table("users").select("*").execute()
        for user in users.data:
            if user.get('email') == email:
                acc_id = user.get('account_id')
                
                # --- SAFETY NET ---
                acc_check = supabase.table("accounts").select("account_id").eq("account_id", acc_id).execute()
                if not acc_check.data:
                    supabase.table("accounts").insert({"account_id": acc_id, "account_type": "checking"}).execute()
                
                # --- AUTOMATIC BALANCE UPDATE ---
                acc_res = supabase.table("accounts").select("balance").eq("account_id", acc_id).execute()
                if acc_res.data:
                    current_balance = float(acc_res.data[0].get("balance") or 0)
                    tx_amt = float(amount)
                    if str(t_type).lower() in ['income', 'deposit']:
                        new_balance = current_balance + tx_amt
                    else:
                        new_balance = current_balance - tx_amt
                    supabase.table("accounts").update({"balance": new_balance}).eq("account_id", acc_id).execute()
                # --------------------------------

                data = {
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': acc_id,
                    'amount': amount,
                    'transaction_type': t_type,
                    'merchant_id': m_id,
                    'merchant_name': m_name,
                    'merchant_category_code': m_code,
                    'description': desc,
                    'is_recurring': recurr,
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                }
                 
                supabase.table("transactions").insert(data).execute()
                return {"success": True}
        
        return {"success": False, "error": "User not found"}
        
    except Exception as e:
        print(f"Error adding transaction: {e}")
        return {"success": False, "error": str(e)}


# Deletes the specified transaction and reverses the balance
@app.post("/transactions/delete-transaction")
def delete_transaction(transaction_id):
    try:
        # 1. Find the transaction to reverse the math
        tx_res = supabase.table("transactions").select("*").eq("transaction_id", transaction_id).execute()
        if tx_res.data:
            tx = tx_res.data[0]
            acc_id = tx.get("account_id")
            old_amt = float(tx.get("amount") or 0)
            old_type = tx.get("transaction_type", "")
            
            # 2. Update the balance
            acc_res = supabase.table("accounts").select("balance").eq("account_id", acc_id).execute()
            if acc_res.data:
                current_balance = float(acc_res.data[0].get("balance") or 0)
                # If they delete an income, subtract it. If they delete an expense, add it back!
                if str(old_type).lower() in ['income', 'deposit']:
                    current_balance -= old_amt
                else:
                    current_balance += old_amt
                supabase.table("accounts").update({"balance": current_balance}).eq("account_id", acc_id).execute()

        # 3. Actually delete the transaction
        supabase.table("transactions").delete().eq("transaction_id", transaction_id).execute()
        return True
    
    except Exception as e:
        print(f"Error deleting transaction: {e}")
        return False


# Updates an existing transaction and recalculates balance
@app.post("/transactions/update-transaction")
def update_transaction(transaction_id, amount, t_type, desc):
    try:
        # 1. Get the old transaction to reverse it
        old_tx_res = supabase.table("transactions").select("*").eq("transaction_id", transaction_id).execute()
        if not old_tx_res.data:
            return {"success": False, "error": "Transaction not found"}
        
        old_tx = old_tx_res.data[0]
        acc_id = old_tx.get("account_id")
        old_amt = float(old_tx.get("amount") or 0)
        old_type = old_tx.get("transaction_type", "")
        
        # 2. Get current balance
        acc_res = supabase.table("accounts").select("balance").eq("account_id", acc_id).execute()
        current_balance = float(acc_res.data[0].get("balance") or 0) if acc_res.data else 0
            
        # 3. Reverse the old transaction
        if str(old_type).lower() in ['income', 'deposit']:
            current_balance -= old_amt
        else:
            current_balance += old_amt
            
        # 4. Apply the new transaction
        new_amt = float(amount)
        if str(t_type).lower() in ['income', 'deposit']:
            current_balance += new_amt
        else:
            current_balance -= new_amt
            
        # 5. Save the new balance and updated transaction
        supabase.table("accounts").update({"balance": current_balance}).eq("account_id", acc_id).execute()
        
        data = {
            "amount": new_amt,
            "transaction_type": t_type,
            "description": desc
        }
        supabase.table("transactions").update(data).eq("transaction_id", transaction_id).execute()
        
        return {"success": True}
    except Exception as e:
        print(f"Error updating transaction: {e}")
        return {"success": False, "error": str(e)}
    
# Updates the users password
# Pre: takes the user email and new desired password as parameters
# Post: returns true if the password was updated successfully, false otherwise
@app.post("/account/update-password")
def update_password(email, newpass):
    try: 
        users = supabase.table("users").select("*").execute()

        for user in users.data:
            e = user.get('email')

            if e == email:
                byte_pwd = newpass.encode('utf-8')
                salt_bytes = bcrypt.gensalt()
                salt = salt_bytes.decode('utf-8')
                pw_hash_bytes = bcrypt.hashpw(byte_pwd, salt_bytes)
                pw_hash = pw_hash_bytes.decode('utf-8')
                now_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                supabase.table("users").update({"password_hash": pw_hash}).eq("email", email).execute()
                supabase.table("users").update({"password_updated_at": now_timestamp}).eq("email", email).execute()
                return True
            
        return False
    except Exception as e:
        return False


# Gets the user's exact balance from the accounts table
@app.get("/account/get-balance")
def get_balance(user_id):
    try:
        user_res = supabase.table("users").select("account_id").eq("user_id", user_id).execute()
        if user_res.data:
            acc_id = user_res.data[0].get("account_id")
            
            # Grab the balance
            acc_res = supabase.table("accounts").select("balance").eq("account_id", acc_id).execute()
            if acc_res.data:
                balance = acc_res.data[0].get("balance", 0)
                return {"success": True, "balance": balance}
                
        return {"success": False, "balance": 0}
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return {"success": False, "error": str(e)}

# Updates the user's balance in the accounts table
@app.post("/account/update-balance")
def update_balance(user_id, new_balance):
    try:
        user_res = supabase.table("users").select("account_id").eq("user_id", user_id).execute()
        if user_res.data:
            acc_id = user_res.data[0].get("account_id")
            
            # Save the new balance
            supabase.table("accounts").update({"balance": new_balance}).eq("account_id", acc_id).execute()
            return {"success": True}
            
        return {"success": False}
    except Exception as e:
        print(f"Error updating balance: {e}")
        return {"success": False, "error": str(e)}
    
# Gets the user's profile information
@app.get("/account/get-profile")
def get_profile(user_id):
    try:
        user_res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        if user_res.data:
            user = user_res.data[0]
            # Looks for a column named 'name' or 'first_name'. If it's blank, it falls back to the email.
            user_name = user.get('name') or user.get('first_name') or ""
            user_email = user.get('email') or ""
            
            return {"success": True, "name": user_name, "email": user_email}
            
        return {"success": False, "error": "User not found"}
        
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return {"success": False, "error": str(e)}

# Gets all transactions tied to the specified user
# Pre: takes a user ID as a parameter
# Post: returns a list of dictionaries - each dictionary is a transaction
@app.get("/dashboard/get-goals")
def get_goals(user_id):
    print('Starting get_goals')
    try:
        # Query for the specific user directly instead of fetching all users
        print(f'Querying for user_id: {user_id}')
        user_response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        print(f'Query completed. Found {len(user_response.data)} users')
        
        if user_response.data:
            acc_id = user_response.data[0].get('account_id')
            print(f'Found account_id: {acc_id}')
            goals = supabase.table("goals").select("*").eq('account_id', acc_id).execute()
            print('Goals retrieved')
            return goals
        
        print('User not found')
        return {"data": []}
        
    except Exception as e:
        print(f'Error: {e}')
        return False

# Add a goal for a user
# Pre: takes user_id, category, and target amount as parameters
# Post: returns True if goal was added/updated, False otherwise
@app.post("/dashboard/add-goal")
def add_goal(user_id, category, target_amount):
    print(f"Received add_goal request - user_id: {user_id}, category: {category}, amount: {target_amount}")
    try:
        # Get the user's account_id
        user_response = supabase.table("users").select("account_id").eq("user_id", user_id).execute()
        
        if not user_response.data or len(user_response.data) == 0:
            print(f"User not found with user_id: {user_id}")
            return {"success": False, "error": "User not found"}
        
        account_id = user_response.data[0].get('account_id')
        
        # --- THE SAFETY NET FIX ---
        acc_check = supabase.table("accounts").select("account_id").eq("account_id", account_id).execute()
        if not acc_check.data:
            print(f"Creating missing account row for account_id: {account_id}")
            # Added user_id to satisfy database rules
            supabase.table("accounts").insert({"account_id": account_id,
                                               "account_type": "checking"}).execute()
        # --------------------------

        # Check if goal already exists for this category
        existing_goal = supabase.table("goals").select("*").eq("account_id", account_id).eq("category", category).execute()
        
        if existing_goal.data and len(existing_goal.data) > 0:
            # Update existing goal
            goal_id = existing_goal.data[0].get('goal_id')
            supabase.table("goals").update({
                "target_amount": float(target_amount),
            }).eq("goal_id", goal_id).execute()
            print(f"Goal updated successfully")
            return {"success": True, "action": "updated", "goal_id": goal_id}
        else:
            # Create new goal
            goal_data = {
                'account_id': account_id,
                'category': category,
                'target_amount': float(target_amount),
            }
            
            result = supabase.table("goals").insert(goal_data).execute()

            # Extract the generated goal_id from Supabase response
            new_goal = result.data[0]
            goal_id = new_goal.get("goal_id")

            print(f"Goal added successfully: {goal_id}")

            return {
                "success": True,
                "action": "created",
                "goal_id": goal_id
            }
        
    except Exception as e:
        print(f"Error in add_goal: {e}")
        return {"success": False, "error": str(e)}


# Delete a goal
# Pre: takes goal_id as parameter
# Post: returns True if goal was deleted, False otherwise
@app.post("/dashboard/delete-goal")
def delete_goal(goal_id):
    try:
        supabase.table("goals").delete().eq("goal_id", goal_id).execute()
        print(f"Goal deleted successfully")
        return {"success": True}
    except Exception as e:
        print(f"Error in delete_goal: {e}")
        return {"success": False, "error": str(e)}


# Gets balance tied to the specified user
# Pre: takes a user ID as a parameter
# Post: returns a float
@app.get("/dashboard/get-balance")
def get_balance(user_id):
    try:
        print(f'Querying for user_id: {user_id}')
        user_response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        
        if user_response.data:
            acc_id = user_response.data[0].get('account_id')
            goals = supabase.table("accounts").select("balance").eq('account_id', acc_id).execute()
            return goals
        
        print('User not found')
        return {"data": []}
        
    except Exception as e:
        print(f'Error: {e}')
        return False



# Updates the specified user's balance
# Pre: takes a user ID and new balance as parameters
# Post: returns success or failure
@app.post("/dashboard/update-balance")
def update_balance(user_id, new_balance):
    try:
        user_response = supabase.table("users").select("account_id").eq("user_id", user_id).execute()
        
        if not user_response.data:
            return {"success": False, "error": "User not found"}
        
        acc_id = user_response.data[0].get("account_id")

        supabase.table("accounts").update({
            "balance": float(new_balance)
        }).eq("account_id", acc_id).execute()

        return {"success": True}
    
    except Exception as e:
        print(f"Error updating balance: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/chat")
def chat_with_budgie(request: ChatRequest):
    user_text = request.message
    user_id = request.user_id
    
    financial_context = ""

    # If the user is logged in, pull their data from Supabase!
    if user_id:
        try:
            # 1. Find their account ID
            user_res = supabase.table("users").select("account_id").eq("user_id", user_id).execute()
            
            if user_res.data:
                acc_id = user_res.data[0].get("account_id")

                # 2. Grab their Account info, Transactions, and Goals
                acc_res = supabase.table("accounts").select("*").eq("account_id", acc_id).execute()
                trans_res = supabase.table("transactions").select("*").eq("account_id", acc_id).execute()
                goals_res = supabase.table("goals").select("*").eq("account_id", acc_id).execute()
                
                transactions = trans_res.data or []
                goals = goals_res.data or []

                # 3. Pull the exact balance directly from the accounts table (No math required!)
                balance = 0
                if acc_res.data:
                    # ---> Change 'balance' below if your database column has a different name! <---
                    balance = acc_res.data[0].get('balance', 0)

                # 4. Build a clean text summary for the AI to read
                financial_context += f"--- USER'S LIVE BANK DATA ---\n"
                financial_context += f"TOTAL ACCOUNT BALANCE: ${float(balance):.2f}\n\n"
                
                if goals:
                    financial_context += "USER'S BUDGET GOALS:\n"
                    for g in goals:
                        financial_context += f"- Goal: {g.get('category')}, Target: ${g.get('target_amount')}\n"
                    financial_context += "\n"
                
                if transactions:
                    financial_context += "RECENT TRANSACTIONS:\n"
                    for t in transactions[-15:]:
                        financial_context += f"- {t.get('transaction_type')}: ${t.get('amount')} at {t.get('merchant_name')}\n"
                
                # --- SNEAK PEEK ---
                print("\n=== WHAT BUDGIE IS READING ===")
                print(financial_context)
                print("==============================\n")
        
        except Exception as e:
            print(f"Failed to pull context for AI: {e}")
            pass

    # Send the user's message AND their database context to the AI
    ai_answer = get_ai_reply(user_text, financial_context)
    
    return {"reply": ai_answer}