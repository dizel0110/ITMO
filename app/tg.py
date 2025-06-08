import os
import sys
import json
import time
import telebot
from telebot import types
from services.crud import user as UserService
from services.crud.balance_service import BalanceService
from fastapi import APIRouter, HTTPException, Depends, status
from database.database import engine, get_session
from models.user import User
from sqlmodel import Session
from common.userservice.balance import Balance

import services.crud.user as UsertgService
from services.crud.transaction import TransactionBusiness
from services.crud.ml_service import RembgBusiness
from models.data_image import Dataimage


from database.database import SessionLocal
from rmworker.send_message import send_message


from decouple import config

TG_TOKEN = config('TG_TOKEN')

bot = telebot.TeleBot(token=TG_TOKEN)


@bot.message_handler(commands=["start"])
def startBot(message):
    first_mess = "Здесь ты сможешь удалить фон с фотографии!\nВойди или зарегистрируйся:"
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    button_reg = types.InlineKeyboardButton(text="Регистрация", callback_data="reg")
    button_auth = types.InlineKeyboardButton(text="Авторизация", callback_data="auth")
    markup.add(button_reg, button_auth)
    bot.send_message(chat_id, first_mess, parse_mode="html", reply_markup=markup)
    bot.edit_message_reply_markup(
        chat_id=chat_id, message_id=message.message_id, reply_markup=None
    )


@bot.callback_query_handler(func=lambda call: call.data == "auth")
def auth_init(call_auth):
    message = call_auth.message
    chat_id = message.chat.id
    markup = types.ForceReply()
    bot.send_message(chat_id, "Твой email?", reply_markup=markup)
    bot.register_next_step_handler(message, email_auth)


def email_auth(message):
    chat_id = message.chat.id
    markup = types.ForceReply()
    email = message.text
    bot.send_message(chat_id, "Введи пароль?", reply_markup=markup)
    bot.register_next_step_handler(message, passw_auth, email)


def passw_auth(message, email):
    chat_id = message.chat.id
    user_password = message.text
    user = User(
        email=email,
        password=user_password,
    )
    with Session(engine) as session:
        result = UserService.get_user_autorization(
            email=user.email,
            password=user.password,
            session=session,
        )
        if not result:
            bot.send_message(chat_id, 'Не верно введены регистрационные данные.')
            startBot(message)
        else:
            user = UserService.get_user_by_email(email=email, session=session)
            if user:
                user_id = user.id
                result = f"Все верно. Доступ открыт для пользователя с user_id {user_id}"
                bot.send_message(chat_id, result)
                user_menu(message, user_id)
            else:
                result = 'Попробуйте ещё раз. Сервис не работает.'
                bot.send_message(chat_id, result)


def user_menu(message, user_id):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    button_hist_load = types.InlineKeyboardButton(
        text="Загрузить историю транзакций", callback_data=f"hist_load/{user_id}"
    )
    button_hist_del = types.InlineKeyboardButton(
        text="Удалить историю транзакций", callback_data=f"hist_del/{user_id}"
    )
    button_repl = types.InlineKeyboardButton(
        text="Пополнить баланс", callback_data=f"repl/{user_id}"
    )
    button_balance = types.InlineKeyboardButton(
        text="Проверить баланс", callback_data=f"balance/{user_id}"
    )
    button_pred = types.InlineKeyboardButton(
        text="Посмотреть результаты", callback_data=f"pred/{user_id}"
    )
    button_start = types.InlineKeyboardButton(
        text="Начать сначала", callback_data="start"
    )
    markup.add(button_hist_load, button_hist_del)
    markup.add(button_repl, button_balance)
    markup.add(button_pred)
    markup.add(button_start)
    bot.send_message(chat_id, "Что дальше?", reply_markup=markup)
    bot.edit_message_reply_markup(
        chat_id=chat_id, message_id=message.message_id, reply_markup=None
    )


@bot.callback_query_handler(func=lambda call: call.data == "start")
def start_over(call):
    message = call.message
    startBot(message)


@bot.callback_query_handler(func=lambda call: call.data == "reg")
def reg_init(call_reg):
    message = call_reg.message
    chat_id = message.chat.id
    markup = types.ForceReply()
    bot.send_message(
        chat_id,
        "Начинаем регистрацию.\nТвой email?",
        parse_mode="html",
        reply_markup=markup,
    )
    bot.register_next_step_handler(message, email_reg)


def email_reg(message):

    chat_id = message.chat.id
    markup = types.ForceReply()
    user_data = {}
    user_data["email"] = message.text
    bot.send_message(
        chat_id,
        "Хорошо!\nПридумай, запомни и введи пароль.",
        parse_mode="html",
        reply_markup=markup,
    )
    bot.register_next_step_handler(message, passw_reg, user_data)


def passw_reg(message, user_data):

    chat_id = message.chat.id
    markup = types.ForceReply()
    bot.send_message(
        chat_id,
        "Отлично!\nДавай познакомимся, твоё имя?",
        parse_mode="html",
        reply_markup=markup,
    )
    user_data["password"] = message.text
    bot.register_next_step_handler(message, name_reg, user_data)


def name_reg(message, user_data):
    chat_id = message.chat.id
    markup = types.ForceReply()
    bot.send_message(
        chat_id,
        f"{message.text}, молодец!\nВведи фамилию.",
        parse_mode="html",
        reply_markup=markup,
    )
    user_data["name"] = message.text
    bot.register_next_step_handler(message, surname_reg, user_data)


def surname_reg(message, user_data):
    chat_id = message.chat.id
    markup = types.ForceReply()
    bot.send_message(
        chat_id,
        f"Значит, ты {user_data['name']} {message.text}...\nТакже нужен твой номер телефона:",
        parse_mode="html",
        reply_markup=markup,
    )
    user_data["surname"] = message.text
    bot.register_next_step_handler(message, phone_reg, user_data)


def phone_reg(message, user_data):
    chat_id = message.chat.id
    user_data["phone"] = message.text
    new_user = User(
        email=user_data["email"],
        phone=user_data["phone"],
        first_name=user_data["name"],
        last_name=user_data["surname"],
        password=user_data["password"],
        tg_id=message.from_user.id,
        credit_amount=100,
    )
    UserService.create_user(
        new_user=new_user,
        session=Depends(get_session),
    )
    user_data = UserService.get_user_by_email(user_data["email"], session=Depends(get_session))
        balance_user_exists = Balance(
            user_id=user_data.id,
            balance=user_data.credit_amount,
        )
        BalanceService.init_balance(
            balance_user_exists,
            session,
        )
    name = user_data["name"]
    markup = types.InlineKeyboardMarkup()
    button_auth = types.InlineKeyboardButton(text="Авторизация", callback_data="auth")
    markup.add(button_auth)
    bot.send_message(
        chat_id, f"Теперь, {name}, авторизуемся!", reply_markup=markup
    )
    bot.edit_message_text(
        text="Авторизуемся...", chat_id=chat_id, message_id=message.id
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("hist_load"))
def hist_load(call):
    message = call.message
    chat_id = message.chat.id
    data_parts = call.data.split("/")
    if len(data_parts) == 2 and data_parts[0] == "hist_load":
        user_id = data_parts[1]
        transaction = TransactionBusiness()
        with Session(engine) as session:
            hist = transaction.show_transaction(session=session, user_id=user_id)e
        if hist:
            hist = hist
            hist = transaction.transform_history(hist)
            for key in hist.keys():
                bot.send_message(chat_id, f"{key}: {hist[key]}")
            bot.send_message(chat_id, "Что-то есть.")
        else:
            bot.send_message(chat_id, "Нет истории - нет проблем.")
        user_menu(message, user_id)
    else:
        bot.send_message(chat_id, "Извини, но я прилег.\nПопробуй позже.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("hist_del"))
def hist_del(call):
    message = call.message
    chat_id = message.chat.id
    data_parts = call.data.split("/")
    if len(data_parts) == 2 and data_parts[0] == "hist_del":
        user_id = data_parts[1]
        transaction = TransactionBusiness()
        with Session(engine) as session:
            transaction.del_transaction(session=session, user_id=user_id)
            bot.send_message(chat_id, "История транзакций удалена.")
            user_menu(message, user_id)
    else:
        bot.send_message(chat_id, "Извини, но я прилег.\nПопробуй позже.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("repl"))
def repl_init(call):
    message = call.message
    chat_id = message.chat.id
    data_parts = call.data.split("/")
    if len(data_parts) == 2 and data_parts[0] == "repl":
        user_id = data_parts[1]
        markup = types.ForceReply()
        bot.send_message(
            chat_id, "Сколько денег ты хочешь потратить?", reply_markup=markup
        )
        bot.register_next_step_handler(message, repl, user_id)
    else:
        bot.send_message(chat_id, "Извини, но я прилег.\nПопробуй позже.")


def repl(message, user_id):
    chat_id = message.chat.id
    try:
        bot.send_message(chat_id, f"Идёт пополнение баланса...{user_id}")
        value = int(message.text)
        with Session(engine) as session:
            transaction = TransactionBusiness()
            transaction.replenishment(session=session, user_id=user_id, value=value)
        bot.send_message(chat_id, "Баланс пополнен.")
        user_menu(message, user_id)
    except ValueError:
        bot.send_message(chat_id, "Для пополнения баланса введи целое число.")
        bot.register_next_step_handler(message, repl, user_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("balance"))
def check_bal(call):
    message = call.message
    chat_id = message.chat.id
    data_parts = call.data.split("/")
    if len(data_parts) == 2 and data_parts[0] == "balance":
        user_id = data_parts[1]
        with Session(engine) as session:
            bot.send_message(chat_id, "Сейчас поищем тебя и твой баланс.")
            user = UserService.get_user_by_id(user_id, session)
            bot.send_message(chat_id, "Итак...")
            if not user:
                bot.send_message(chat_id, "Что-то есть. Но тебя нет.")
                user_menu(message, user_id)
            else:
                balance_checker = BalanceService()
                # user = User(user_id=user_id)
                # balance = user.check_balance(session=session)
                # balance = BalanceService.check_balance_sufficiency(user_id=user_id, session=session)
                balance = balance_checker.check_balance(user_id, session)
                bot.send_message(chat_id, f"Твой баланс: {balance}")
                user_menu(message, user_id)
    else:
        bot.send_message(chat_id, "Извини, но я прилег.\nПопробуй позже.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("pred"))
def pred_init(call):
    message = call.message
    chat_id = message.chat.id
    data_parts = call.data.split("/")
    if len(data_parts) == 2 and data_parts[0] == "pred":
        user_id = data_parts[1]
        user = User(user_id=user_id)
        if user.check_balance(session=session) < 100:
            bot.send_message(chat_id, "Кинь сотку на баланс.")
            user_menu(message, user_id)
        else:
            markup = types.ForceReply()
            bot.send_message(chat_id, "Загрузи фотку, а я сниму изображение.", reply_markup=markup)
            bot.register_next_step_handler(message, pred, user_id)
    else:
        bot.send_message(chat_id, "Нет связи, приходи позже.")


def pred(message, user_id):
    chat_id = message.chat.id
    to_send = input_path
    send_message(message=to_send)
    bot.send_message(chat_id, "Запрос отправлен в очередь. Скоро вернусь.")
    save_data(message, user_id, data)


def save_data(message, user_id, input_path):
    callback(message, user_id, data)


def callback(message, user_id, input_path):
    chat_id = message.chat.id
    if not data.check_output(session):
        time.sleep(5)
        callback(message, user_id, data)
    else:
        new_dataimage = Dataimage(
            user_id=user_id,
            input_image_path=input_path,
            output_image_path=output_path,
        )
        rembgbusiness.create_note(
            new_dataimage=new_dataimage,
            session=session,
        )
        transaction = TransactionBusiness()
        transaction.withdrawal(session=session, user_id=user_id, value=100)
        bot.send_message(chat_id, response)
        user_menu(message, user_id)


bot.infinity_polling()
