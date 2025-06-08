import streamlit as st
import toml
from menu import menu, set_role
import requests
from params import FASTAPI_URL

menu()

if "role" not in st.session_state:
    st.session_state.role = False

st.session_state._role = st.session_state.role

if st.session_state.role == False:
    with st.form("signin", border=False):
        st.title("Привет! Добро пожаловать!")
        st.title("Авторизуйся, чтобы продолжить:")

        email = st.text_input("Почта")
        password = st.text_input("Пароль", type="password")

        if st.form_submit_button("Отправить"):
            data = {"username": email, "password": password}
            response = requests.post(f"{FASTAPI_URL}/user/signin", data=data)
            if response.status_code == 200:
                st.session_state._role = True
                set_role()

                user = requests.get(
                    f"{FASTAPI_URL}/user/email/{email}",
                    params={"email": email},
                    timeout=600,
                )
                st.markdown(user.json())
                st.session_state.user_id = user.json()["id"]
                st.session_state.user_name = user.json()["first_name"]
                st.write(response.json())
                st.rerun()

            elif response.status_code == 401 or response.status_code == 404:
                st.write(response.json())
            else:
                st.error("some error")


elif st.session_state.role == True:
    st.title("Авторизовано!")
    st.title(f"Добро пожаловать, {st.session_state.user_name}!")

else:
    st.title("Сервис недоступен")
