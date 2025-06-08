import streamlit as st
from menu import menu_with_redirect
from PIL import Image
import os
import io
import base64
from rembg import remove, new_session
import requests
from params import FASTAPI_URL


menu_with_redirect()

st.title("Удаление фона с фотографий")


def convert_image(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    return byte_im


def load_image(image_file):
    img = Image.open(image_file)
    return img


def remove_background(img):
    output = remove(img, session=new_session('u2netp'))  # .convert('RGB'))
    return output  # Image.fromarray(output)


user_id = st.session_state.user_id

check_balance = requests.get(
                f"{FASTAPI_URL}/user/balance/{user_id}",
                timeout=600,
)
balance = check_balance.text

if float(balance) < 60.0:
    st.markdown(f'У Вас на балансе {balance} единиц!')
    st.markdown('Обработка одной фотографии 60 единиц!')
    st.markdown('Пополните баланс и вовзращайтесь!')
else:
    col1, col2 = st.columns(2)

    with col1:
        st.header("Исходная фотография")
        image_file = st.file_uploader("Загрузите фотографию", type=["png", "jpg", "jpeg"])

        if image_file is not None:
            input_img = load_image(image_file)
            st.image(input_img, use_column_width=True)

            # save_path = os.path.join(os.getcwd(), 'output_images',
            #                          f'{os.path.splitext(image_file.name)[0]}_processed.png')
            # processed_img.save(save_path)
я
            # with open(save_path, "rb") as file:
            #     btn = st.download_button(
            #         label=f"Скачать обработанное изображение ({os.path.basename(save_path)})",
            #         data=file,
            #         file_name=os.path.basename(save_path),
            #         mime='image/png'
            #     )
я
    with col2:
        st.header("Обработанная фотография")
        if image_file is not None:
            try:
                processed_img = remove_background(input_img)

                st.write("Обработанная фотография:")
                st.image(processed_img, use_column_width=True)
                st.sidebar.markdown("\n")
                st.sidebar.subheader("- Click to download your image with the background removed.")
                st.sidebar.download_button("Download Image", convert_image(
                    processed_img), "fixed.png", "image/png", )
                requests.post(
                    f"{FASTAPI_URL}/transaction/withdrawal/{st.session_state.user_id}",
                    params={"amount_down": 60},
                    timeout=600,
                )
            except Exception as e:
                st.error(f"Произошла ошибка при обработке изображения: {e}")
