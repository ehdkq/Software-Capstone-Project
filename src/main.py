from fastapi import FastAPI
from db import supabase
from datetime import datetime
import bcrypt
import uuid

app = FastAPI()

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
            if e == email and p == passw:
                return True
            
        return False
    
    except Exception as e:
        return False

# Create's a user account
# Pre: takes user email and password as parameters
# Post: returns True if the account was successfully created, False otherwise
@app.get("/create-account")
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
# Pre: takes a userID as a parameter
# Post: returns True if the account was deleted, false otherwise
@app.get("/account/delete-account")
def delete_account(userID):
    try:
        users = supabase.table("users").select("*").execute()

        for user in users.data:
            if user.get('user_id') == userID:
                supabase.table("users").delete().eq("user_id",userID).execute()
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
# Pre: takes the user ID, transaction amount, transaction type, merchant ID, merchant name, 
#      merchant code, a description, and a recurring T/F as parameters
# Post: returns true if the transaction was added, false otherwise
@app.get("/transactions/add-transaction")
def add_transaction(user_id, amount, t_type, m_id, m_name, m_code, desc, recurr):
    try:

        users = supabase.table("users").select("*").execute()
        for user in users.data:
            if user.get('user_id') == user_id:
                acc_id = user.get('account_id')
                
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
                return True
        
        return False
    except Exception as e:
        print(e)

        return False

# Deletes the specified transaction
# Pre: takes a transaction ID as a parameter
# Post:  returns true if the transaction was deleted, false otherwise
@app.get("/transactions/delete-transaction")
def delete_transaction(transaction_id):
    try:
        supabase.table("transactions").delete().eq("transaction_id", transaction_id).execute()
        return True
    
    except Exception as e:
        return False

'''


@app.get("/login/forgot-password")
def forgot_password(email):
    #forgot_password_email(email)
    try:
        
        
        return True
    except Exception as e:
        print(e)
        return False'''
    
# Updates the users password
# Pre: takes the user email and new desired password as parameters
# Post: returns true if the password was updated successfully, false otherwise
@app.get("/account/update-password")
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

'''
def forgot_password_email(email):
    #TODO'''

#print(verify_login('custosdfsdf@example.com', 'WyAH03DADiIJGThvBkyby2sMUMRgDd9Dg17yccD6JyE='))
#print(create_account('backendtest2@test.com', 'test1233'))
#print(delete_account('9a246eb6-ab5c-4350-b65a-149883eccee4'))
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