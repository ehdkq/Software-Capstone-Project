from fastapi import FastAPI
from db import supabase
from datetime import datetime
import bcrypt
import uuid
import io
import os
import json
import re
import pdfplumber
from fastapi import File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from budgie_bot import get_ai_reply
from google import genai
from google.genai import types
from dotenv import load_dotenv
import smtplib
import secrets
from email.message import EmailMessage
from fastapi.responses import RedirectResponse

# --- SETUP & AI INIT ---
load_dotenv() # Loads the hidden keys from your .env file

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    # Replace the "*" with your actual Netlify URL and local testing URLs
    allow_origins=[
        "https://budgiebudgeting.netlify.app",
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
# Initialize Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None



# pull from db: response = supabase.table("TABLE_NAME").select("* (ALL)").execute()
# write to db: response = supabase.table("TABLE_NAME").insert(data - typically a dict).execute()
# update db: response = supabase.table("TABLE_NAME").update({"column name": "column value"}).eq("value", what_value_equals).execute()
# delete from db: response = supabase.table("TABLE_NAME").delete().eq("value", what value equals).execute()
# return response


# Create's a user account
# Pre: takes user email and password as parameters
# Post: returns True if the account was successfully created, False otherwise
# Create's a user account along with customer and account rows
@app.post("/create-account")
def create_account(email, passw, firstN, lastN):
    byte_pwd = passw.encode('utf-8')
    salt_bytes = bcrypt.gensalt()
    pw_hash_bytes = bcrypt.hashpw(byte_pwd, salt_bytes)
    now_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    
    # Generate a random 32-character token
    verification_token = secrets.token_urlsafe(32)

    user_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())

    user_data = {
        'user_id': user_id,
        'email': email,
        'password_hash': pw_hash_bytes.decode('utf-8'),
        'password_salt': salt_bytes.decode('utf-8'),
        'role': 'customer',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        'account_id': account_id,
        'is_verified': False, # New users start unverified
        'verification_token': verification_token # Save the token
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
        
        # Send the email!
        send_verification_email(email, verification_token)

        return {"success": True, "message": "Account created! Please check your email to verify."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/verify-email")
def verify_email(token: str):
    try:
        # Find the user with this token
        res = supabase.table("users").select("*").eq("verification_token", token).execute()
        
        if res.data:
            user_id = res.data[0].get("user_id")
            # Set them to verified and wipe the token so it can't be used again
            supabase.table("users").update({
                "is_verified": True, 
                "verification_token": None
            }).eq("user_id", user_id).execute()
            
            return RedirectResponse(url="https://budgiebudgeting.netlify.app//login.html")
        else:
            return "Invalid or expired verification link."
    except Exception as e:
        return f"Error verifying email: {e}"


@app.get("/login")
def verify_login(email, passw):
    try: 
        users = supabase.table("users").select("*").eq("email", email).execute()

        if users.data:
            user = users.data[0]
            
            # --- NEW SECURITY CHECK ---
            if not user.get('is_verified'):
                return {"success": False, "error": "Please check your email and verify your account first."}
            # --------------------------

            byte_pwd = passw.encode('utf-8')
            salt_bytes = user.get('password_salt').encode('utf-8')
            pw_hash_bytes = bcrypt.hashpw(byte_pwd, salt_bytes)
            
            if pw_hash_bytes.decode('utf-8') == user.get('password_hash'):
                return {"success": True, "user_id": user.get('user_id')}
            
        return {"success": False, "error": "Invalid credentials"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_reset_email(user_email, token):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    msg = EmailMessage()
    msg['Subject'] = 'Budgie Password Reset'
    msg['From'] = sender_email
    msg['To'] = user_email
    
    # We will create this page in Step 3!
    reset_link = f"https://budgiebudgeting.netlify.app/reset-password.html?token={token}"
    msg.set_content(f"We received a request to reset your Budgie password.\n\nClick the link below to set a new password:\n{reset_link}\n\nIf you did not request this, you can safely ignore this email.")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Failed to send reset email: {e}")

@app.post("/api/request-reset")
def request_password_reset(email: str = Form(...)):
    try:
        # 1. Verify the email exists in the database
        res = supabase.table("users").select("user_id").eq("email", email).execute()
        
        if res.data:
            user_id = res.data[0].get("user_id")
            # 2. Generate a secure token
            reset_token = secrets.token_urlsafe(32)
            
            # 3. Save the token to the database (reusing the verification_token column)
            supabase.table("users").update({"verification_token": reset_token}).eq("user_id", user_id).execute()
            
            # 4. Send the email
            send_reset_email(email, reset_token)
            
        # We always return success even if the email isn't found to prevent "Email Enumeration" hacker attacks
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/execute-reset")
def execute_password_reset(token: str = Form(...), new_password: str = Form(...)):
    try:
        # 1. Find the user with this token
        res = supabase.table("users").select("user_id").eq("verification_token", token).execute()
        
        if not res.data:
            return {"success": False, "error": "Invalid or expired reset link."}
            
        user_id = res.data[0].get("user_id")
        
        # 2. Hash the new password using your existing bcrypt logic
        byte_pwd = new_password.encode('utf-8')
        salt_bytes = bcrypt.gensalt()
        pw_hash_bytes = bcrypt.hashpw(byte_pwd, salt_bytes)
        
        # 3. Update the database and wipe the token so it can't be reused
        supabase.table("users").update({
            "password_hash": pw_hash_bytes.decode('utf-8'),
            "password_salt": salt_bytes.decode('utf-8'),
            "verification_token": None,
            "password_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }).eq("user_id", user_id).execute()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
# Deletes the users account
# Pre: takes an email as a parameter
# Post: returns True if the account was deleted, false otherwise
@app.post("/account/delete-account")
def delete_account(email: str = Form(...)):
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


@app.post("/account/wipe-data")
def wipe_account_data(user_id: str = Form(...)):
    try:
        # 1. Find the user's account_id
        user_res = supabase.table("users").select("account_id").eq("user_id", user_id).execute()
        if not user_res.data:
            return {"success": False, "error": "User not found"}

        acc_id = user_res.data[0].get("account_id")

        # 2. Delete all transactions tied to this account
        supabase.table("transactions").delete().eq("account_id", acc_id).execute()

        # 3. Delete all goals tied to this account
        supabase.table("goals").delete().eq("account_id", acc_id).execute()

        # 4. Reset the account balance to exactly $0.00
        supabase.table("accounts").update({"balance": 0.0}).eq("account_id", acc_id).execute()

        return {"success": True}
    except Exception as e:
        print("Error wiping account data:", e)
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

# Added tx_date=None to the end!
@app.post("/transactions/add-transaction")
@app.post("/transactions/add-transaction")
def add_transaction(email, amount, t_type, m_id, m_name, m_code, desc, recurr, tx_date=None):
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

                # --- SMART TIMESTAMP BUILDER ---
                if tx_date:
                    # If the AI gave us a short 'YYYY-MM-DD', attach a noon timestamp so Supabase accepts it
                    if len(tx_date) <= 10:
                        final_date = f"{tx_date} 12:00:00.000000"
                    else:
                        final_date = tx_date
                else:
                    # Fallback to right now if no date was found at all
                    final_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
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
                    'created_at': final_date  # <--- Custom AI Date
                }
                 
                supabase.table("transactions").insert(data).execute()
                return {"success": True}
        
        return {"success": False, "error": "User not found"}
        
    except Exception as e:
        # This is the "catch" block it was looking for!
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

@app.post("/api/import-statement")
async def import_statement(file: UploadFile = File(...), user_id: str = Form(None)):
    try:
        # 1. Match the user_id to an email (since add_transaction uses email)
        user_res = supabase.table("users").select("email").eq("user_id", user_id).execute()
        if not user_res.data:
            return {"success": False, "error": "Could not verify user account."}
        user_email = user_res.data[0].get("email")

        # 2. Extract the raw text from the uploaded PDF
        contents = await file.read()
        extracted_text = ""
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                # Removed layout=True. This stops pdfplumber from adding massive 
                # blank spaces that confuse the AI when reading tables.
                extracted_text += page.extract_text() + "\n"

        # WIRETAP: Print the raw text to Render so we can verify the PDF reader worked
        print("\n--- RAW PDF TEXT ---")
        print(extracted_text)
        print("--------------------\n")

        # 3. Use AI to structure the messy bank statement
        prompt = f"""
        Extract EVERY SINGLE transaction from the text below. Do not summarize or stop early.
        
        Return a JSON array of objects with exactly these keys:
        "tx_date": (string, YYYY-MM-DD format)
        "desc": (string, merchant name)
        "amount": (float, absolute value, no symbols)
        "t_type": (string, 'Groceries', 'Dining', 'Utilities', 'Entertainment', 'Income', or 'Other')

        TEXT:
        {extracted_text}
        """

        # 4. Call the Live Model with Strict JSON Mode
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0, # Zero creativity
                response_mime_type="application/json", # Forces native JSON output without markdown!
            )
        )
        
        # WIRETAP: Print what the AI decided to output
        print(f"AI OUTPUT: {response.text}")

        # 5. Parse the JSON (No string cleaning needed anymore!)
        transactions = json.loads(response.text)
        
        # Add every extracted transaction to Supabase using your existing function
        imported_count = 0
        for tx in transactions:
            add_transaction(
                email=user_email,
                amount=tx["amount"],
                t_type=tx["t_type"],
                m_id="0",
                m_name=tx["desc"],
                m_code="0",
                desc=tx["desc"],
                recurr="false",
                tx_date=tx.get("tx_date")
            )
            imported_count += 1

        return {"success": True, "count": imported_count}

    except Exception as e:
        print(f"Import Error: {e}")
        return {"success": False, "error": "Failed to parse PDF. The AI couldn't read the format."}
@app.post("/api/chat")
async def chat_with_budgie(message: str = Form(""), user_id: Optional[str] = Form(None), file: UploadFile = File(None)):
    try:
        extracted_text = ""
        # 1. Handle File Uploads (Existing logic)
        if file:
            contents = await file.read()
            if file.content_type == "application/pdf":
                with pdfplumber.open(io.BytesIO(contents)) as pdf:
                    for page in pdf.pages:
                        extracted_text += page.extract_text(layout=True) + "\n"
            elif file.content_type.startswith("image/"):
                extracted_text = f"[User attached an image: {file.filename}]"

        # 2. FETCH REAL DATA: No more generic answers
        user_context = "The user is currently browsing as a guest."
        if user_id and user_id != "null":
            # Get the account_id first
            user_res = supabase.table("users").select("account_id").eq("user_id", user_id).execute()
            if user_res.data:
                acc_id = user_res.data[0].get("account_id")
                # Grab the latest 10 transactions and all goals
                tx_res = supabase.table("transactions").select("*").eq("account_id", acc_id).limit(10).execute()
                goal_res = supabase.table("goals").select("*").eq("account_id", acc_id).execute()
                
                user_context = f"REAL USER DATA:\nTransactions: {tx_res.data}\nGoals: {goal_res.data}"

        # 3. SET THE PERSONALITY
        budgie_instructions = (
            "You are Budgie, the smart, clever, and supportive bird mascot for this app. "
            "Use the REAL USER DATA provided to give specific advice. If they are a guest, "
            "give general financial tips. Use bird-themed metaphors (nest egg, flying high, "
            "perching) and keep it conversational!"
        )

        # 4. CALL THE LIVE MODEL
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash', # Updated to the standard 2.0 stable version
            contents=f"{user_context}\n\nUser Question: {message}\n\n{extracted_text}",
            config=types.GenerateContentConfig(
                system_instruction=budgie_instructions,
                temperature=0.7,
            )
        )
        
        return {"success": True, "reply": response.text}

    except Exception as e:
        print(f"Detailed API Error: {e}") # This will show in your Render logs!
        return {"success": False, "reply": "My bird brain is having a connection hiccup! Double-check the Render Environment Variables."}
def send_verification_email(user_email, token):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    msg = EmailMessage()
    msg['Subject'] = 'Verify your Budgie Account'
    msg['From'] = sender_email
    msg['To'] = user_email
    
    # Point this to your Render API!
    verify_link = f"https://software-capstone-project.onrender.com/verify?token={token}"
    msg.set_content(f"Welcome to Budgie! Please verify your email by clicking here:\n\n{verify_link}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
            print("Live email successfully sent!")
    except Exception as e:
        print(f"Failed to send real email: {e}")