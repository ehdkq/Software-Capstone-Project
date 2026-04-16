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

# --- SETUP & AI INIT ---
load_dotenv() # Loads the hidden keys from your .env file

# Initialize Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://budgiebudgeting.netlify.app"],  # Allows all origins (use specific URLs in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# pull from db: response = supabase.table("TABLE_NAME").select("* (ALL)").execute()
# write to db: response = supabase.table("TABLE_NAME").insert(data - typically a dict).execute()
# update db: response = supabase.table("TABLE_NAME").update({"column name": "column value"}).eq("value", what_value_equals).execute()
# delete from db: response = supabase.table("TABLE_NAME").delete().eq("value", what value equals).execute()
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
    
    # ... (Keep your existing customer_data and account_data dictionaries here) ...

    try:
        supabase.table("users").insert(user_data).execute()
        # ... (Keep your existing customer/account inserts here) ...
        
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
            
            return "Email successfully verified! You can now log in to Budgie."
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

# Deletes the users account
# Pre: takes an email as a parameter
# Post: returns True if the account was deleted, false otherwise@app.post("/account/delete-account")
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
def get_balance(user_id: str):
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
def update_balance(user_id: str, new_balance: float):
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
def get_profile(user_id: str):
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
    print(f"Received delete_goal request - goal_id: {goal_id}")
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
async def chat_with_budgie(message: str = Form(""), file: UploadFile = File(None)):
    try:
        extracted_text = ""

        # 1. Handle the File Upload
        if file:
            contents = await file.read()
            
            if file.content_type == "application/pdf":
                # Extract text from the PDF
                with pdfplumber.open(io.BytesIO(contents)) as pdf:
                    for page in pdf.pages:
                        extracted_text += page.extract_text(layout=True) + "\n"
                        
            elif file.content_type.startswith("image/"):
                extracted_text = f"[User attached an image file: {file.filename}]"

        # 2. Build the final prompt for Gemini
        prompt = message
        if extracted_text:
            prompt += f"\n\n--- ATTACHED DOCUMENT DATA ---\n{extracted_text}\n-------------------"

        # 3. ---> CALL GEMINI HERE <---
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are Budgie, a helpful, friendly, and concise financial AI assistant. You help users analyze their spending, read bank statements, and hit their budget goals. Keep your answers brief and conversational.",
                    temperature=0.7,
                )
            )
            ai_response = response.text
            
        except Exception as api_error:
            print(f"Gemini API Error: {api_error}")
            ai_response = "My brain is having a little trouble connecting right now! Please make sure the Gemini API key is set up correctly in the .env file."

        return {"success": True, "reply": ai_response}

    except Exception as e:
        print(f"Chat Error: {e}")
        return {"success": False, "reply": "Oops! I had trouble reading that. Please try again."}
    
@app.post("/api/import-statement")
async def import_statement(user_id: str = Form(...), file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        if file.content_type != "application/pdf":
            return {"success": False, "error": "Please upload a PDF statement."}

        # 1. THE BULLETPROOF PROMPT
        prompt = """
        You are an elite financial data extraction tool. Read the attached bank statement PDF and extract EVERY SINGLE transaction. 
        Return a valid JSON array of objects.
        
        CRITICAL RULES:
        1. You MUST extract every single transaction. Do not stop early. Do not skip any rows.
        2. Output amounts as pure positive numbers. Strip out commas, dollar signs, and minus signs (e.g., "$1,842.65" or "-1,842.65" must become exactly 1842.65).
        
        Each object must have exactly these keys:
        - "date": The date the transaction occurred. Format strictly as "YYYY-MM-DD" (e.g., "04/14/2026" becomes "2026-04-14"). If a date has a typo like "010201202", infer the real date or default to the current year/month.
        - "amount": a positive float representing the transaction value.
        - "t_type": If money came IN (deposits, credits, Payroll), this must be exactly "Income". If money went OUT, assign a category like "Groceries", "Dining", "Utilities", "Entertainment", or "Other".
        - "desc": a clean, short name of the merchant.
        """

        # 2. FEED THE RAW PDF DIRECTLY TO GEMINI'S VISION MODEL!
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                prompt,
                types.Part.from_bytes(data=contents, mime_type='application/pdf')
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json" # This forces the AI to output flawless JSON!
            ) 
        )
        
        # Because we forced JSON output, we don't need regex scrubbing anymore!
        transactions = json.loads(response.text)

        user_res = supabase.table("users").select("email").eq("user_id", user_id).execute()
        if not user_res.data:
            return {"success": False, "error": "User not found."}
        email = user_res.data[0].get("email")

        imported_count = 0
        for tx in transactions:
            extracted_date = tx.get("date") or tx.get("Date")
            
            # The Python comma scrubber as a final safety net
            raw_amount_str = str(tx.get("amount", "0"))
            clean_amount_str = raw_amount_str.replace(",", "").replace("$", "").replace("-", "").strip()
            
            try:
                final_amount = float(clean_amount_str)
            except ValueError:
                final_amount = 0.0 

            add_transaction(
                email=email,
                amount=final_amount,
                t_type=tx.get("t_type", "Other"),
                m_id="0",
                m_name=tx.get("desc", "Unknown"),
                m_code="0",
                desc=tx.get("desc", "Unknown"),
                recurr="false",
                tx_date=extracted_date
            )
            imported_count += 1

        return {"success": True, "count": imported_count}

    except Exception as e:
        print(f"Import Error: {e}")
        return {"success": False, "error": str(e)}
    
def send_verification_email(user_email, token):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    msg = EmailMessage()
    msg['Subject'] = 'Verify your Budgie Account'
    msg['From'] = sender_email
    msg['To'] = user_email
    
    verify_link = f"http://127.0.0.1:5500/login.html?token={token}"
    msg.set_content(f"Welcome to Budgie! Please verify your email by clicking here:\n\n{verify_link}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
            print("Live email successfully sent!")
    except Exception as e:
        print(f"Failed to send real email: {e}")