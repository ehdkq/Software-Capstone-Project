#from SOFTWARE-CAPSTONE-PROJECT.src.main.py import * 

import sys
import os
import random
import string

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from main import *

def test_valid_login():
    response = verify_login('backendtest2@test.com', 'test1234')
    assert response == True

def test_invalid_login():
    response = verify_login('backendtest2@test.com', 'incorrectpassword')
    assert response == False

def test_create_account():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    response = create_account(test_email, 'testpassword')
    assert response == True

def test_delete_existing_account():
    create_account('tobedeleted@test.com', 'deleteme')
    response = delete_account('tobedeleted@test.com')
    assert response == True


def test_delete_nonexistent_account():
    response = delete_account('unknownemail@test.com')
    assert response == False


# TODO
def test_add_transaction():
    test_email = (''.join(random.choices(string.ascii_letters + string.digits, k=8))) + '@test.com'
    create_account(test_email, 'testpassword')
    response = add_transaction(test_email, 10.00, 'Withdrawl', '001', 'Test', '999', 'Test', False)
    assert response == True

'''
def test_get_transactions():


def test_delete_existing_transaction():


def test_delete_nonexistent_transaction():


def test_update_password():

'''
