import streamlit as st
import pandas as pd
from menu import menu_with_redirect
import requests
from params import FASTAPI_URL

menu_with_redirect()

st.title(
    f"Посмотри, историю своих действий, {st.session_state.user_name}:"
)


if st.button("Посмотреть историю транзакций"):
    response = requests.get(
        f"{FASTAPI_URL}/transaction/history/{st.session_state.user_id}",
        timeout=600,
    )
    if response.status_code == 200 or response.status_code == 404:
        history = pd.DataFrame(response.json())
        history = history.reindex(
            columns=["transaction_id", "user_id", "date", "replenishment", "withdrawal"]
        )
        history = history.rename(
            columns={
                "transaction_id": "ID транзакции",
                "user_id": "ID пользователя",
                "date": "Дата",
                "replenishment": "Пополнение",
                "withdrawal": "Списание",
            }
        )
        st.table(history)
    else:
        st.markdown("Извини, но информации нет!")

if st.button("Посмотреть историю предсказаний путь к изображениям."):
    response = requests.get(
        f"{FASTAPI_URL}/rembg/history/dataimage/{st.session_state.user_id}",
        timeout=600,
    )
    if response.status_code == 200 or response.status_code == 404:
        history_di = pd.DataFrame(response.json())
        history_di = history_di.reindex(
            columns=["image_id", "user_id", "input_image_path", "output_image_path", "date"]
        )
        history_di = history_di.rename(
            columns={
                "image_id": "ID предсказания",
                "user_id": "ID пользователя",
                "input_image_path": "путь к входному изображению",
                "output_image_path": "путь к обработанному изображению",
                "date": "Дата",
            }
        )
        st.table(history_di)
    else:
        st.markdown("Извини, но информации нет!")
