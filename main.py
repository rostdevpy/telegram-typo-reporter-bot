import telebot
from telebot import types
import datetime
import gspread
import os
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from telebot import apihelper

load_dotenv()

# Прокси
#apihelper.proxy = {
#    "http": "",
#    "https": ""
#}

# Токен бота и подключение
token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(token)

# Настройка гугл таблиц
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
# Открываем таблицу по названию
table = client.open('Опечатки MAXIMUM')
# Словарь для хранения ответов юзеров
user_states = {}

# Списки из задания
subjects = ["Русский язык", "Математика", "Информатика", "Физика", "История", "Обществознание", "Английский язык",
            "Биология", "Химия", "Digital Skills"]
classes = ["8 класс", "9 класс", "10 класс", "11 класс"]
digital_courses = ["Программирование", "Графический дизайн", "Маркетинг"]


# Команда старт
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.chat.id
    user_states[uid] = {}  # очищаем данные, если начали заново

    # Кнопки для выбора предмета
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for s in subjects:
        kb.add(types.KeyboardButton(s))

    bot.send_message(uid, "Привет! Выбери предмет, в котором нашел опечатку:", reply_markup=kb)
    print(f"Пользователь {uid} запустил бота")


# Получаем выбор предмета
@bot.message_handler(func=lambda m: m.chat.id in user_states and 'sub' not in user_states[m.chat.id])
def get_subject(message):
    uid = message.chat.id
    selected = message.text

    if selected not in subjects:
        bot.send_message(uid, "Выбери вариант с кнопки!")
        return

    user_states[uid]['sub'] = selected

    # Делаем кнопки для класса или курса
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    if selected == "Digital Skills":
        for d in digital_courses:
            kb.add(types.KeyboardButton(d))
        msg = "Выбери направление курса:"
    else:
        for c in classes:
            kb.add(types.KeyboardButton(c))
        msg = "Выбери класс:"

    bot.send_message(uid, msg, reply_markup=kb)
    print(f"Выбран предмет: {selected}")


# Выбор класса/курса
@bot.message_handler(func=lambda m: m.chat.id in user_states and 'course' not in user_states[m.chat.id])
def get_course(message):
    uid = message.chat.id
    selected = message.text

    if user_states[uid]['sub'] == "Digital Skills":
        if selected not in digital_courses:
            bot.send_message(uid, "Выбери направление с кнопки.")
            return
    else:
        if selected not in classes:
            bot.send_message(uid, "Выбери класс с кнопки.")
            return

    user_states[uid]['course'] = selected

    # Убираем клавиатуру и просим текст
    rem_kb = types.ReplyKeyboardRemove()
    bot.send_message(uid, "Отлично. Теперь напиши текст опечатки (или прикрепи описание):", reply_markup=rem_kb)
    print(f"Выбран курс/класс: {selected}")


# Финал: получаем текст опечатки и всё сохраняем
@bot.message_handler(func=lambda m: m.chat.id in user_states and 'course' in user_states[m.chat.id])
def get_typo_text(message):
    uid = message.chat.id
    typo = message.text

    # Собираем данные для записи
    date_now = datetime.date.today().strftime("%Y-%m-%d")
    username = message.from_user.username if message.from_user.username else f"ID_{uid}"
    sub = user_states[uid]['sub']
    course = user_states[uid]['course']

    # Пишем в текстовый файл typos.txt
    with open("typos.txt", "a", encoding="utf-8") as file:
        file.write(f"Дата: {date_now} | Юзер: {username} | Предмет: {sub} | Курс: {course} | Текст: {typo}\n")
    print("Данные записаны в txt файл")

    # Запись в Гугл Таблицу по вкладкам
    try:
        try:
            # Ищем нужную вкладку
            ws = table.worksheet(sub)
        except gspread.exceptions.WorksheetNotFound:
    # Если вкладки для этого предмета еще нет - создаем автоматически
            ws = table.add_worksheet(title=sub, rows="1000", cols="4")
            ws.append_row(["Дата", "Отправитель", "Курс/Класс", "Текст опечатки"])
            print(f"Создан новый лист: {sub}")

        # Добавляем строку с данными
        ws.append_row([date_now, username, course, typo])
        print("Данные успешно ушли в Google Sheets")
    except Exception as e:
        print(f"Ошибка в таблице: {e}")

    # Чистим данные сессии юзера
    del user_states[uid]

    bot.send_message(uid, "Спасибо! Опечатка сохранена и отправлена на проверку. Если найдешь еще - пиши /start.")

# Запуск
if __name__ == '__main__':
    print("Бот запущен вручную...")
    bot.infinity_polling()
