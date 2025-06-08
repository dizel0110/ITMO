import streamlit as st
import requests
from menu import menu
from params import FASTAPI_URL

menu()


st.title("Введи свои данные в форму ниже:")

with (st.form("signup", border=False)):
    email = st.text_input("Почта")
    password = st.text_input("Пароль", type="password")
    first_name = st.text_input("Имя")
    partonymic = st.text_input("Отчество")
    last_name = st.text_input("Фамилия")
    phone = st.text_input("Номер телефона")
    login = email

    if st.form_submit_button("Отправить"):
        data = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "partonymic": partonymic,
            "last_name": last_name,
            "phone": phone,
            "login": login,
            "tg_id": -1,
            "credit_amount": 0,
            "admin_role": False,
        }
        response = requests.post(f"{FASTAPI_URL}/user/signup", json=data)
        if response.status_code == 200:
            st.markdown(response.json())
            st.markdown("А теперь войди на сайт")
        else:
            st.error("some error")
