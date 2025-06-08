import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from database.database import get_session
from sqlmodel import Session, create_engine
from models.user import TokenResponse
from fastapi import status
from fastapi.testclient import TestClient
from api import app
from services.crud import user as UserService


client = TestClient(app)


@pytest.fixture()
def user_json():
    return {
        'id': 123,
        'email': "test_user@mail.ru",
        'password': "hrtwik",
        'first_name': "test_first_name",
        'last_name': "test_last_name",
        'phone': "+3528798",
        'tg_id': -1,
        'credit_amount': 0.0,
        'admin_role': True,
    }


def test_signup(user_json):
    response = client.post("user/signup", json=user_json)
    assert response.status_code == 200
    assert response.json() == {'message': 'User created!'}


def test_signup_same_email(user_json):
    response = client.post("user/signup", json=user_json)
    assert response.json() == status.HTTP_400_BAD_REQUEST


def test_user_by_email(user_json):
    email = user_json['email']
    response = client.get(f"user/email/{email}")
    user_response = response.json()
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert user_response['phone'] == "+3528798"


def test_check_balance(user_json):
    email = user_json['email']
    response_email = client.get(f"user/email/{email}")
    user_id_response = response_email.json()['id']
    response_balance = client.get(f"user/balance/{user_id_response}")
    assert response_email.status_code == 200
    assert user_id_response == user_json['id']
    assert response_balance.status_code == 200
    assert response_balance.json() == user_json['credit_amount']


def test_replenishment(user_json):
    email = user_json['email']
    response = client.get(f"user/email/{email}")
    user_id_response = response.json()['id']
    balance_before_replenishment = client.get(f"user/balance/{user_id_response}").json()
    amount_up = 500.0
    response = client.post(f"/transaction/replenishment/{user_id_response}?amount_up={amount_up}")
    balance_after_replenishment = client.get(f"user/balance/{user_id_response}").json()
    check_amount_up = balance_after_replenishment - balance_before_replenishment
    assert response.status_code == 200
    assert response.json() == "Баланс пополнен"
    assert check_amount_up == amount_up


def test_withdrawal_no_balance(user_json):
    email = user_json['email']
    user_balance = user_json['credit_amount']
    response = client.get(f"user/email/{email}")
    user_id_response = response.json()['id']
    balance_before_withdrawal = client.get(f"user/balance/{user_id_response}").json()
    amount_down = 60.0
    response = client.post(f"/transaction/withdrawal/{user_id_response}?amount_down={amount_down}")
    assert balance_before_withdrawal == user_balance
    assert response.json() == (f'В настоящий момент списание не доступно. '
                               f'Статус ошибки: 400: Insufficient funds. Balance: {user_balance}')


def test_withdrawal(user_json):
    email = user_json['email']
    response = client.get(f"user/email/{email}")
    user_id_response = response.json()['id']
    balance_before_withdrawal = client.get(f"user/balance/{user_id_response}").json()
    amount_down = 60.0
    response = client.post(f"/transaction/withdrawal/{user_id_response}?amount_down={amount_down}")
    balance_after_withdrawal = client.get(f"user/balance/{user_id_response}").json()
    check_amount_down = balance_before_withdrawal - balance_after_withdrawal
    assert response.status_code == 200
    assert response.json() == "С баланса списано"
    assert check_amount_down == amount_down


def test_load_transaction_history(user_json):
    email = user_json['email']
    response_email = client.get(f"user/email/{email}")
    user_id_response = response_email.json()['id']
    response = client.get(f"/transaction/history/{user_id_response}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_delete_transaction_history(user_json):
    email = user_json['email']
    response_email = client.get(f"user/email/{email}")
    user_id_response = response_email.json()['id']
    response = client.delete(f"/transaction/history/{user_id_response}/delete")
    assert response.status_code == 200
    assert isinstance(response.json(), str)


def test_load_data_history(user_json):
    email = user_json['email']
    response_email = client.get(f"user/email/{email}")
    user_id_response = response_email.json()['id']
    response = client.get(f"rembg/history/dataimage/{user_id_response}")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_delete_data_history(user_json):
    email = user_json['email']
    response_email = client.get(f"user/email/{email}")
    user_id_response = response_email.json()['id']
    response = client.delete(f"rembg/history/dataimage/{user_id_response}/delete")
    assert response.status_code == 200
    assert isinstance(response.json(), str)
