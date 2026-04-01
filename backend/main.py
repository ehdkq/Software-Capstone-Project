from fastapi import FastAPI
from db import supabase
from datetime import datetime
import bcrypt
import uuid
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from budgie_bot import get_ai_reply

class ChatRequest(BaseModel):
    message: str

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
@app.post("/create-account")
def create_account(email, passw):
    byte_pwd = passw.encode('utf-8')
    salt_bytes = bcrypt.gensalt()
    pw_hash_bytes = bcrypt.hashpw(byte_pwd, salt_bytes)
    salt = salt_bytes.decode('utf-8')
    pw_hash = pw_hash_bytes.decode('utf-8')
    now_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    data = {
        'user_id': str(uuid.uuid4()), 
        'email': email, 
        'password_hash': pw_hash, 
        'password_salt': salt, 
        'role': 'customer', 
        'created_at': now_timestamp, 
        'password_updated_at': now_timestamp,
        'account_id': str(uuid.uuid4())
        }

    try:
        supabase.table("users").insert(data).execute()
        return True
    except Exception as e:
        print(e)
        return False

# Deletes the users account
# Pre: takes an email as a parameter
# Post: returns True if the account was deleted, false otherwise
@app.post("/account/delete-account")
def delete_account(email):
    try:
        users = supabase.table("users").select("*").execute()

        for user in users.data:
            if user.get('email') == email:
                supabase.table("users").delete().eq("email", email).execute()
                return True
        
        return False
    except Exception as e:

        return False

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

# Adds a transaction to the user's account
# Pre: takes the user email, transaction amount, transaction type, merchant ID, merchant name, 
#      merchant code, a description, and a recurring T/F as parameters
# Post: returns true if the transaction was added, false otherwise
@app.post("/transactions/add-transaction")
def add_transaction(email, amount, t_type, m_id, m_name, m_code, desc, recurr):
    print(f"Received add_transaction request - Email: {email}, Amount: {amount}, Type: {t_type}")
    try:
        users = supabase.table("users").select("*").execute()
        for user in users.data:
            if user.get('email') == email:
                acc_id = user.get('account_id')
                
                transaction_id = str(uuid.uuid4())  # Generate ID first
                
                data = {
                    'transaction_id': transaction_id,
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
                 
                result = supabase.table("transactions").insert(data).execute()
                print(f"Transaction added successfully: {result}")
                return {"success": True, "transaction_id": transaction_id}  # Return the ID
        
        print(f"User not found with email: {email}")
        return {"success": False, "error": "User not found"}
        
    except Exception as e:
        print("="*50)
        print("FULL ERROR MESSAGE:")
        print(str(e))
        print("="*50)
        return {"success": False, "error": str(e)}


# Deletes the specified transaction
# Pre: takes a transaction ID as a parameter
# Post:  returns true if the transaction was deleted, false otherwise
@app.post("/transactions/delete-transaction")
def delete_transaction(transaction_id):
    try:
        supabase.table("transactions").delete().eq("transaction_id", transaction_id).execute()
        return True
    
    except Exception as e:
        return False

# Edits a transaction on the user's account
# Pre: takes the transaction_id, amount, t_type, desc as parameters
# Post: returns true if the transaction was added, false otherwise
@app.post("/transactions/edit-transaction")
def edit_transaction(transaction_id, amount, t_type, desc):
    try:
        data = {
            'amount': float(amount),
            'transaction_type': t_type,
            'description': desc
        }
        
        supabase.table("transactions").update(data).eq("transaction_id", transaction_id).execute()
        return {"success": True}
    
    except Exception as e:
        print(f"Error editing transaction: {e}")
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


'''
def forgot_password_email(email):
    #TODO'''

# TEST QUERIES
#print(verify_login('custosdfsdf@example.com', 'WyAH03DADiIJGThvBkyby2sMUMRgDd9Dg17yccD6JyE='))
#print(create_account('test@test.com', 'test123'))
#print(delete_account('usertest2@test.com'))
#print(delete_account('usertest@test.com'))
#print(delete_account('usertest3@test.com'))
#print(forgot_password('dfd'))

#print(get_transactions('080691cf-dd78-428e-a4ba-98e442940d6c'))
'''d = {
    'amount': 1.00,
    'type': 'Withdrawal',
    'merchant_id': 'Test01',
    'merchant_name': 'Test Merchant',
    'merchant_category_code': 5310,
    'description': 'Test Transaction',
    'is_recurring': False,
}
print(add_transaction('080691cf-dd78-428e-a4ba-98e442940d6c', d))'''

#print(delete_transaction('fcd4123c-b2f5-4d38-8e66-9e3381242397'))

#print(update_password('backendtest1@test.com', 'TestABCD'))

#print(create_account('backendtest2@test.com', 'test1234'))
#print(verify_login('backendtest2@test.com', 'test1234'))

@app.post("/api/chat")
def chat_with_budgie(request: ChatRequest):
    # 1. Grab the text the user typed
    user_text = request.message
    
    # 2. Send it to your budgie_bot file to get the AI's answer
    ai_answer = get_ai_reply(user_text)
    
    # 3. Send the answer back to the HTML page
    return {"reply": ai_answer}
