import ast
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import telebot
from dotenv import load_dotenv
from html2image import Html2Image
from telebot import types
from telebot.types import CallbackQuery
from telebot_calendar import Calendar, CallbackData
from validate_email import validate_email

from database_operations import get_user_ids, add_user, set_user_email, is_user_active, get_user_email, get_users, \
    set_user_active
from language_for_calendar import UKRAINE_LANGUAGE
from privatbank_func import get_data_from_privatbank
from report_html import generate_report_html
from send_mail import send_mail

THIS_FOLDER = Path(__file__).parent.resolve()

load_dotenv(THIS_FOLDER)

ADMIN = int(os.getenv('ADMIN'))
bot = telebot.TeleBot(os.getenv('BOT_API_TOKEN'))

logger = telebot.logger
logging.basicConfig(filename='log.log', level=logging.INFO,
                    format=' %(asctime)s - %(levelname)s - %(message)s')
log_msg = logging.getLogger()

calendar = Calendar(language=UKRAINE_LANGUAGE)
calendar_1_callback = CallbackData("calendar_1", "action", "year", "month", "day")
calendar_3_callback = CallbackData("calendar_3", "action", "year", "month", "day")
calendar_4_callback = CallbackData("calendar_4", "action", "year", "month", "day", 'date_from')


@bot.message_handler(commands=['start'])
def start(message):
    log_msg.info(f"{message.from_user.first_name}[{message.from_user.id}] - {message.text}")
    user_ids = get_user_ids()
    welcome_message = f'Вітаю, {message.from_user.first_name} !'
    bot.send_message(message.chat.id, welcome_message, parse_mode="html")

    if message.from_user.id not in user_ids:
        registration_message = bot.send_message(message.chat.id,
                                                "Ви ще не зареєстровані.\n"
                                                "Будь-ласка, вкажіть свою пошту для отримання звітів на неї",
                                                parse_mode="html")
        add_user(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                 message.from_user.username)
        bot.register_next_step_handler(registration_message, email_create_request_data)
    elif is_user_active(message.from_user.id) == 0:
        bot.send_message(message.chat.id, "Адміністратор ще не підтвердив Вам доступ до боту",
                         parse_mode="html")
    elif is_user_active(message.from_user.id) == 0:
        draw_button(message.chat.id)


def email_create_request_data(message):
    if validate_email(message.text):
        set_user_email(message.from_user.id, message.text)
        bot.send_message(message.chat.id, "Дякую, після підтвердження Адміністратором Ви зможете користуватися"
                                          " даним ботом",
                         parse_mode="html")
        check_admin(message.from_user.id, message.from_user.first_name, message.text)
    else:
        invalid_email_message = bot.send_message(message.chat.id,
                                                 "Ви вказали не існуючу пошту, вкажіть корректно свою пошту",
                                                 parse_mode="html")
        bot.register_next_step_handler(invalid_email_message, email_create_request_data)


def check_admin(user_id, user_name, user_email):
    msg = bot.send_message(ADMIN, f"Зареєстрований новий користувач {user_name} {user_email} ", parse_mode="html")
    if msg.chat.id == ADMIN:
        keyboard_admin = types.InlineKeyboardMarkup(row_width=2)
        keyboard_yes = types.InlineKeyboardButton('Так', callback_data='new_user,activate_user', user_id=user_id)
        keyboard_no = types.InlineKeyboardButton('Ні', callback_data='new_user,deactivate_user')
        keyboard_admin.add(keyboard_yes, keyboard_no)
        bot.send_message(ADMIN, f'Активувати користувача?{user_id}', reply_markup=keyboard_admin)
    else:
        pass


@bot.message_handler(commands=['edit_mail'])
def edit_mail(message):
    def email_change(mess):
        validate_mail(mess)
        log_msg.info(f"{mess.from_user.first_name} - {mess.text}")

    received_email = get_user_email(message.from_user.id)
    bot.send_message(message.chat.id, f'Ваша поточна пошта: {received_email}',
                     parse_mode="html")
    new_mail = bot.send_message(message.chat.id, 'Вкажіть Вашу нову пошту',
                                parse_mode="html")
    bot.register_next_step_handler(new_mail, email_change)


@bot.message_handler(commands=['my_mail'])
def my_mail(message):
    log_msg.info(f"{message.from_user.first_name} - {message.text}")
    user_email = get_user_email(message.from_user.id)
    bot.send_message(message.chat.id, f'Ваша пошта: {user_email}', parse_mode="html")


@bot.message_handler(commands=['users'])
def users_command(message):
    if message.chat.type == 'private' and message.from_user.id == ADMIN:
        send_users_list(message.chat.id)
    else:
        bot.send_message(message.chat.id, 'Команда доступна лише адміністратору.')


# Функция для обработки нажатий на кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith("adminka"))
def button_callback(call):
    user_id = int(call.data.split("_")[-1])
    user_active_status = call.data.startswith("adminka_activate")

    set_user_active(user_id, user_active_status)

    message = "Користувач активований" if user_active_status else "Користувач деактивований"
    bot.answer_callback_query(call.id, text=message)


@bot.message_handler(func=lambda message: is_user_active(message.from_user.id) == 0)
def some(message):
    bot.send_message(message.chat.id, 'Адміністратор ще не підтвердив Вам доступ до бота')


@bot.message_handler(func=lambda message: is_user_active(message.from_user.id) == 1)
def all_message(message):
    if message.text == 'Сформувати звіт':
        log_msg.info(f"{message.from_user.first_name} - {message.text}")
        choice_report(message)

    elif message.text == 'Список ФОП':
        log_msg.info(f"{message.from_user.first_name} - {message.text}")
        file_tokens = THIS_FOLDER / "data" / "tokens.txt"
        with open(file_tokens, 'r', encoding="utf-8") as f:
            for line in f:
                name, acc, id_number, token = line.strip().split(';')
                bot.send_message(message.chat.id, f'<b>{name}</b>' + '\n' + acc, parse_mode="html")

    elif message.text == 'Вчора':
        log_msg.info(f"{message.from_user.first_name} - {message.text}")
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%d-%m-%Y')
        inline_button_report(message, yesterday)

    elif message.text == 'Сьогодні':
        log_msg.info(f"{message.from_user.first_name} - {message.text}")
        today = datetime.now().strftime('%d-%m-%Y')
        inline_button_report(message, today)

    elif message.text == 'Довільний день':
        log_msg.info(f"{message.from_user.first_name} - {message.text}")
        bot.send_message(
            message.chat.id,
            "Виберіть дату",
            reply_markup=calendar.create_calendar(
                name=calendar_1_callback.prefix,
                year=datetime.now().year,
                month=datetime.now().month,
            ), )

    elif message.text == 'За період':
        log_msg.info(f"{message.from_user.first_name} - {message.text}")
        bot.send_message(
            message.chat.id,
            "Виберіть дату початку",
            reply_markup=calendar.create_calendar(
                name=calendar_3_callback.prefix,
                year=datetime.now().year,
                month=datetime.now().month,
            ), )

    elif message.text == 'Назад в основне меню':
        log_msg.info(f"{message.from_user.first_name} - {message.text}")
        draw_button(message.chat.id)
    else:
        log_msg.info(f"{message.from_user.first_name} - {message.text}")
        bot.send_message(message.chat.id, 'Ви ввели неправильну команду, я Вас не розумію.', parse_mode="html")


def inline_button_report(message, date, date_end=''):
    keyboard_type_report = types.InlineKeyboardMarkup(row_width=2)
    keyboard_mail = types.InlineKeyboardButton('📧 На пошту',
                                               callback_data="['report_to_mail', '" + date + "', '" + date_end + "']")
    keyboard_screen = types.InlineKeyboardButton('📱 На екран',
                                                 callback_data="['report_to_screen', '" + date + "', '" +
                                                               date_end + "']")
    keyboard_type_report.add(keyboard_mail, keyboard_screen)
    bot.send_message(message.from_user.id, f'Куди надіслати звіт?', reply_markup=keyboard_type_report)


@bot.callback_query_handler(func=lambda call: call.data.startswith("new_user"))
def active_user(call: CallbackQuery):
    user_id = call.message.text.split("?")[1]
    if call.data.split(',')[-1] == 'activate_user':
        set_user_active(user_id, 1)
        bot.send_message(user_id, "Ваш акаунт розблоковано")
        draw_button(user_id)
        bot.send_message(call.from_user.id, "Акаунт розблоковано")
    else:
        set_user_active(user_id, 0)
        bot.send_message(user_id, "Адміністратор не підтвердив Вашу особистість і заборонив Вам користуватися ботом.")
        bot.send_message(call.from_user.id, "Заборону встановлено")


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1_callback.prefix))
def calendar_any_day(call: CallbackQuery):
    name, action, year, month, day = call.data.split(calendar_1_callback.sep)
    date = calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month, day=day)
    if action == "DAY":
        log_msg.info(f"{call.from_user.first_name} - {date.strftime('%d.%m.%Y')}")
        date = date.strftime('%d-%m-%Y')
        inline_button_report(call, date)
    elif action == "CANCEL":
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_3_callback.prefix))
def calendar_period_from(call: CallbackQuery):
    name, action, year, month, day = call.data.split(calendar_3_callback.sep)
    date_from = calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month, day=day
    )
    if action == "DAY":
        log_msg.info(f"{call.from_user.first_name} - {date_from.strftime('%d.%m.%Y')}")
        bot.send_message(
            chat_id=call.from_user.id,
            text=f"Дата початку {date_from.strftime('%d.%m.%Y')}...", )
        now = datetime.now()

        bot.send_message(
            chat_id=call.from_user.id,
            text="Виберіть дату закінчення",
            reply_markup=calendar.create_calendar(
                name=calendar_4_callback.prefix + '(' + str(date_from.strftime('%d-%m-%Y')) + ')',
                year=now.year,
                month=now.month
            ),
        )
    elif action == "CANCEL":
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_4_callback.prefix))
def calendar_period_to(call: CallbackQuery):
    date_from = call.data.split("(")[1].split(")")[0]
    name, action, year, month, day = call.data.split(calendar_4_callback.sep)
    date = calendar.calendar_query_handler(
        bot=bot, call=call, name=name, action=action, year=year, month=month, day=day
    )
    if action == "DAY":
        log_msg.info(f"{call.from_user.first_name} - {date.strftime('%d.%m.%Y')}")
        bot.send_message(
            chat_id=call.from_user.id,
            text=f"Дата закінчення {date.strftime('%d.%m.%Y')}...", )
        date_to = date.strftime('%d-%m-%Y')
        if datetime.strptime(date_from, '%d-%m-%Y') > datetime.now() or date > datetime.now():
            bot.send_message(
                chat_id=call.from_user.id,
                text=f"Одна з ваших дат більша за поточну. Формування звіту скасовано.", )
        else:
            inline_button_report(call, date_from, date_to)
    elif action == "CANCEL":
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith("['"))
def send_report(call):
    date_from = ast.literal_eval(call.data)[1]
    date_to = ast.literal_eval(call.data)[2] if ast.literal_eval(call.data)[2] != '' else None
    mail = get_user_email(call.from_user.id)
    if call.data.startswith("['report_to_mail'"):
        bot.send_message(call.from_user.id, f'Формую звіт', parse_mode="html")
        send_mail(get_data_from_privatbank(date_from, date_to), date_from, date_to, mail)
        bot.send_message(call.from_user.id, f'Звіт надіслано на пошту', parse_mode="html")
    if call.data.startswith("['report_to_screen'"):
        if date_to:
            bot.send_message(call.from_user.id, f'Формую звіт', parse_mode="html")
        else:
            bot.send_message(call.from_user.id, f'Формую звіт за {date_from}...', parse_mode="html")
        report_to_screen(call.from_user.id, date_from, date_to)


def validate_mail(message):
    if validate_email(message.text):
        set_user_email(message.from_user.id, message.text)
        bot.send_message(message.chat.id, "Ваша електронна пошта успішно змінена", parse_mode="html")
    else:
        text = bot.send_message(message.chat.id,
                                "Ви вказали неіснуючу пошту.\nБудь ласка, напишіть коректно свою пошту.",
                                parse_mode="html")
        bot.register_next_step_handler(text, validate_mail)


def draw_button(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    report = types.KeyboardButton(f'Сформувати звіт')
    list_of_fop = types.KeyboardButton('Список ФОП')
    markup.row(report, list_of_fop)
    bot.send_message(chat_id, 'Виберіть необхідну дію', reply_markup=markup)


def choice_report(message):
    keyboard_subcategory = types.ReplyKeyboardMarkup(resize_keyboard=True)

    variable_date = types.KeyboardButton('Довільний день')
    yesterday = types.KeyboardButton('Вчора')
    today = types.KeyboardButton('Сьогодні')
    period_date = types.KeyboardButton('За період')

    keyboard_subcategory.row(yesterday, today)
    keyboard_subcategory.row(variable_date)
    keyboard_subcategory.row(period_date)
    back = types.KeyboardButton('Назад в основне меню')
    keyboard_subcategory.row(back)

    bot.send_message(message.chat.id, 'Виберіть дату', reply_markup=keyboard_subcategory)


def report_to_screen(chat_id, date_from, date_to=None):
    folder = f'{THIS_FOLDER}//temp'
    filename = f'report_{chat_id}.jpg'
    html = generate_report_html(get_data_from_privatbank(date_from, date_to), date_from, date_to)
    hti = Html2Image(output_path=folder, custom_flags=['--no-sandbox'])
    css = "body {background: white;}"
    hti.screenshot(html_str=html, css_str=css, save_as=filename, size=(750, 900))
    photo = open(f'{folder}//{filename}', 'rb')
    bot.send_photo(chat_id, photo)


def send_users_list(chat_id):
    users = get_users()
    for user in users:
        name = user[1]
        mail = user[3]
        user_active_status = user[6]
        state = "Активовано" if user_active_status else "Деактивовано"
        keyboard_admin = types.InlineKeyboardMarkup(row_width=2)
        keyboard_yes = telebot.types.InlineKeyboardButton("Активувати", callback_data=f"adminka_activate_{user[0]}")
        keyboard_no = telebot.types.InlineKeyboardButton("Деактивувати",
                                                         callback_data=f"adminka_deactivate_{user[0]}")

        keyboard_admin.add(keyboard_yes, keyboard_no)
        message = f"{name}: {state},\nmail: {mail}"
        bot.send_message(chat_id, message, reply_markup=keyboard_admin)


bot.polling(none_stop=True)
