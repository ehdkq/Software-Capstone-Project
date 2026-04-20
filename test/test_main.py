#from SOFTWARE-CAPSTONE-PROJECT.src.main.py import * 

import sys
import os
import random
import string

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend import main as m

# Test case 1.1
def test_valid_login():
    response = m.verify_login('backendtest2@test.com', 'test1234')
    assert response != {"success": False}

# Test case 1.2
def test_invalid_login():
    response = m.verify_login('backendtest2@test.com', 'incorrectpassword')
    assert response == {"success": False}

# Test case 2.1
def test_create_account():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    response = m.create_account(test_email, 'testpassword', 'Test', 'User')
    m.delete_account(test_email)  # Clean up after test
    assert response["success"] == True

# Test case 3.1
def test_delete_existing_account():
    m.create_account('tobedeleted@test.com', 'deleteme', 'Temp', 'User')
    response = m.delete_account('tobedeleted@test.com')
    assert response == {"success": True}

def test_delete_nonexistent_account():
    response = m.delete_account('unknownemail@test.com')
    assert response["success"] == False

# Test case 4.1
def test_add_transaction():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    m.create_account(test_email, 'testpassword', 'Test', 'User')
    response = m.add_transaction(test_email, 10.00, 'Withdrawal', '001', 'Test', '999', 'Test', False)
    m.delete_account(test_email)  # Clean up after test
    assert response == {"success": True}

def test_get_transactions():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    m.add_transaction(test_email, 20.00, 'Deposit', '002', 'Test', '999', 'Test', False)
    response = m.get_transactions(user_id)
    m.delete_account(test_email)  # Clean up after test
    assert response != False

# Test case 4.2
def test_delete_existing_transaction():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    m.add_transaction(test_email, 20.00, 'Withdrawal', '002', 'Test', '999', 'Test', False)
    transactions = m.get_transactions(user_id).data
    transaction_id = transactions[0]['transaction_id']
    response = m.delete_transaction(transaction_id)
    m.delete_account(test_email)  # Clean up after test
    assert response != False

def test_delete_nonexistent_transaction():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    response = m.delete_transaction("invalid_id")
    m.delete_account(test_email)  # Clean up after test
    assert response == False

# Test case 4.3
def test_update_transaction():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    m.add_transaction(test_email, 10.00, 'Withdrawal', '001', 'Test', '999', 'Test', False)
    transactions = m.get_transactions(user_id).data
    transaction_id = transactions[0]['transaction_id']
    response = m.update_transaction(transaction_id, 15.00, 'Withdrawal', 'Test')
    m.delete_account(test_email)  # Clean up after test
    assert response == {"success": True}

def test_update_nonexistent_transaction():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    m.create_account(test_email, 'testpassword', 'Test', 'User')
    response = m.update_transaction("invalid_id", 15.00, 'Withdrawal', 'Test')
    m.delete_account(test_email)  # Clean up after test
    assert response['success'] == False


def test_update_password():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    m.create_account(test_email, 'testpassword', 'Test', 'User')
    response = m.update_password(test_email, 'newpassword')
    m.delete_account(test_email)  # Clean up after test
    assert response == True

def test_get_balance():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    response = m.get_balance(user_id).data
    m.delete_account(test_email)  # Clean up after test
    assert response[0] == {'balance': 0.0}
    
# Test case 5.1
def test_update_balance():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    response = m.update_balance(user_id, 100.00)
    m.delete_account(test_email)  # Clean up after test
    assert response == {"success": True}

def test_get_profile():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    response = m.get_profile(user_id)
    m.delete_account(test_email)  # Clean up after test
    assert response['success'] == True

def test_get_goals():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    response = m.get_goals(user_id).data
    m.delete_account(test_email)  # Clean up after test
    assert response == []


# Test case 6.1
def test_add_goal():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    response = m.add_goal(user_id, 'Test Goal', 100.00)
    m.delete_account(test_email)  # Clean up after test
    assert response['success'] == True

# Test case 6.2
def test_delete_goal():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    user_info = m.create_account(test_email, 'testpassword', 'Test', 'User')
    user_id = user_info['user_id']
    m.add_goal(user_id, 'Test Goal', 100.00)
    goals = m.get_goals(user_id).data
    assert goals != []
    response = m.delete_goal(goals[0]['goal_id'])
    m.delete_account(test_email)  # Clean up after test
    assert response['success'] == True

# Test case 6.3
def test_chat_with_budgie():
    req = m.ChatRequest(message="Test")
    response = m.chat_with_budgie(req)
    assert response["reply"] != ""
