import flask
import telebot
from telebot import types
import conf
import content
import sqlite3

conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()


def db_table_val(user_id: int, user_name: str):
    cursor.execute('INSERT INTO users (user_id, user_name) VALUES (?, ?)', (user_id, user_name))
    conn.commit()


def db_table_insert_action_info(user_id: int, game_id: int, action_num: int, agent: str, action_type: str):
    sql_query = f"INSERT INTO games (user_id, game_id, action_num, agent, action_type) VALUES ({user_id}, {game_id}, {action_num}, '{agent}', '{action_type}')"
    cursor.execute(sql_query)
    conn.commit()

WEBHOOK_URL_BASE = "https://{}:{}".format(conf.WEBHOOK_HOST, conf.WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(conf.TOKEN)
bot = telebot.TeleBot(conf.TOKEN, threaded=False)
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH)
app = flask.Flask(__name__)

start_text = "Привет! Этот бот умеет играть в 'Слово-песня'. Чтобы узнать правила, нажми 'Правила'. Для начала игры нажми 'Играть'. Чтобы увидеть статистику своих игр, напиши 'статистика'."
rules_text = "Правила игры: Вы получите имя англоязычного певца (певицы), а также 3 пары слов, которые встречаются в какой-то его (ее) песне. Ваша задача - угадать название песни. Удачи!"
us_id = ''
action_num = 0
game_id = 0

@bot.message_handler(commands=["start", "help"])
def repeat_all_messages(message):
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton(text="Правила", callback_data="button1")
    button2 = types.InlineKeyboardButton(text="Играть", callback_data="button2")
    keyboard.add(button1)
    keyboard.add(button2)
    bot.send_message(message.chat.id, start_text, reply_markup=keyboard)

    global us_id
    us_id = message.from_user.id
    us_name = message.from_user.first_name

    a = """SELECT user_id FROM users WHERE user_id = """ + str(us_id)
    cursor.execute(a)
    b = cursor.fetchone()
    if not b:
        db_table_val(user_id=us_id, user_name=us_name)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        if call.data == "button1":
            bot.send_message(call.message.chat.id, rules_text)
            keyboard = types.InlineKeyboardMarkup()
            button2 = types.InlineKeyboardButton(text="Играть", callback_data="button2")
            keyboard.add(button2)
            bot.send_message(call.message.chat.id, "Поехали?", reply_markup=keyboard)
        if call.data == "button2":
            content.cur_to_ask = content.make_question(content.df)
            first_mes = f"Итак, я загадал песню {content.cur_to_ask['artist']}. В ней есть вот такие сочетания слов: 1. {content.cur_bigr[0][0]+', '+content.cur_bigr[0][1]}; 2. {content.cur_bigr[1][0]+', '+content.cur_bigr[1][1]}; 3. {content.cur_bigr[2][0]+', '+content.cur_bigr[2][1]}. Угадаешь? Если идей совсем нет, напиши 'подсказка'. Если хочешь закончить, напиши 'сдаюсь'."
            bot.send_message(call.message.chat.id, first_mes)
            artist = content.cur_to_ask['artist']
            print(artist)
            photo = open(f'./photos/{artist}.jpg', 'rb')
            bot.send_photo(call.message.chat.id, photo)
            global action_num
            global game_id
            action_num = 0
            g = "SELECT max(game_id) FROM games"
            cursor.execute(g)
            s = cursor.fetchone()
            game_id = s[0] + 1


@bot.message_handler(content_types=['text'])
def handle_text(message):
    global action_num
    action_num += 1
    if message.text.lower() == "подсказка":
        db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='user', action_type='подсказка')
        if len(content.cur_to_ask['bigrams']) < 3:
            bot.send_message(message.chat.id, (
                "Подсказки закончились :( Название песни, которую я загадал: {}. Чтобы увидеть статистику своих игр, напиши 'статистика'.".format(content.cur_to_ask['title'])))
            db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='bot',
                                        action_type='проигрыш')
        else:
            cur_bigr = content.three_bigrams(content.cur_to_ask)
            bot.send_message(message.chat.id,
                             f"В этой песне есть еще вот такие сочетания 1. {cur_bigr[0][0] + ', ' + cur_bigr[0][1]}; 2. {cur_bigr[1][0] + ', ' + cur_bigr[1][1]}; 3. {cur_bigr[2][0] + ', ' + cur_bigr[2][1]}.")
            db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='bot',
                                        action_type='подсказка')
    elif message.text.lower() == "сдаюсь":
        db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='user',
                                    action_type=message.text.lower())
        bot.send_message(message.chat.id, "Название песни, которую я загадал: " + content.cur_to_ask['title'] + ".\nЧтобы увидеть статистику своих игр, напиши 'статистика'.")
        db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='bot',
                                    action_type='проигрыш')
        content.cur_to_ask = {}
    elif message.text.lower() == 'статистика':
        query = f"SELECT count(DISTINCT game_id) as cnt_all" \
                ", sum(case when action_type='победа' then 1 else 0 end) as cnt_win" \
                ", sum(case when action_type='проигрыш' then 1 else 0 end) as cnt_fail FROM games WHERE user_id = """ + str(us_id)
        cursor.execute(query)
        st = cursor.fetchone()
        stat = message.from_user.first_name + f", твоя статистика:\nВсего игр: {st[0]} \nПобед: {st[1]} \nПоражений: {st[2]}"
        bot.send_message(message.chat.id, stat)
    else:
        if message.text.lower() == content.cur_to_ask['title'].lower():
            db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='user',
                                        action_type='вариант')
            bot.send_message(message.chat.id, "Молодец!")
            db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='bot',
                                        action_type='победа')
        else:
            db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='user',
                                        action_type='вариант')
            bot.send_message(message.chat.id, "Нет, я загадал не эту песню. Попробуй еще раз или напиши 'подсказка'")
            db_table_insert_action_info(user_id=us_id, game_id=game_id, action_num=action_num, agent='bot',
                                        action_type='мимо')

# пустая главная страничка для проверки
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'ok'

@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)


#if __name__ == '__main__':
#    bot.polling(none_stop=True)
