import os
import csv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# === 🔑 ЗАМЕНИ НА СВОЙ ТОКЕН ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не установлена")

# === 👤 ЗАМЕНИ НА СВОЙ ID ===
ADMIN_ID = os.getenv("ADMIN_ID")
if not ADMIN_ID:
    raise ValueError("❌ Переменная окружения ADMIN_ID не установлена")
ADMIN_ID = int(ADMIN_ID)

# === 📁 ФАЙЛЫ ===
PARTICIPANTS_FILE = "participants.csv"
TOURNAMENTS_FILE = "tournaments.csv"

# === 🎯 ЭТАПЫ РЕГИСТРАЦИИ ===
NICK, ROLE, RANK, OP_GG, DISCORD = range(5)

# === 🎯 МЕНЮ ===
main_menu_kb = [
    ["📝 Зарегистрироваться"],
    ["👥 Список участников", "📅 Дата проведения"],
    ["📜 Правила турниров"]
]
reply_menu = ReplyKeyboardMarkup(main_menu_kb, resize_keyboard=True)

# === СОЗДАНИЕ ФАЙЛОВ ===
def init_files():
    if not os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])
        print("📁 Файл participants.csv создан")

    if not os.path.exists(TOURNAMENTS_FILE):
        with open(TOURNAMENTS_FILE, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Название", "Дата"])
        print("📁 Файл tournaments.csv создан")

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🎮 Добро пожаловать на турнир!\n\nВыбери действие:",
        reply_markup=reply_menu
    )

# === ОБРАБОТКА РЕГИСТРАЦИИ ===
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Проверяем, зарегистрирован ли уже пользователь
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 0 and str(user_id) == row[0]:
                    await update.message.reply_text("Вы уже зарегистрированы!")
                    return ConversationHandler.END
    except FileNotFoundError:
        pass
    
    await update.message.reply_text("Введите ваш никнейм в игре:", reply_markup=None)
    return NICK

async def get_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nick'] = update.message.text

    role_kb = [
        ["🛡️ Топ", "🌲 Джангл"],
        ["🌀 Мид", "🏹 ADC"],
        ["🧙 Саппорт"],
        ["✅ Готово"]
    ]
    markup = ReplyKeyboardMarkup(role_kb, resize_keyboard=True)
    await update.message.reply_text(
        "Выбери роли (можно несколько). Когда закончишь — нажми «✅ Готово»:",
        reply_markup=markup
    )
    context.user_data['roles'] = []
    return ROLE

async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if 'roles' not in context.user_data:
        context.user_data['roles'] = []

    if text == "✅ Готово":
        if not context.user_data['roles']:
            await update.message.reply_text("⚠️ Выбери хотя бы одну роль.")
            return ROLE

        rank_kb = [
            ["🥉 Bronze", "🥈 Silver"],
            ["🥇 Gold", "💎 Platinum"],
            ["🟩 Emerald", "🔷 Diamond"],
            ["⭐ Master", "👑 Grandmaster", "🏆 Challenger"]
        ]
        markup = ReplyKeyboardMarkup(rank_kb, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Выбери свой ранг:", reply_markup=markup)
        return RANK

    else:
        role = text.split(' ', 1)[-1]
        if role not in context.user_data['roles']:
            context.user_data['roles'].append(role)
            await update.message.reply_text(f"➕ Роль '{role}' добавлена.")
        else:
            await update.message.reply_text(f"✔️ Роль '{role}' уже есть.")
        return ROLE

async def get_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rank'] = update.message.text
    await update.message.reply_text("Ссылка на ваш профиль Op.gg:")
    return OP_GG

async def get_opgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['opgg'] = update.message.text
    await update.message.reply_text("Ваш Discord (например: player#1234):")
    return DISCORD

async def get_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nick = context.user_data['nick']
    roles = ", ".join(context.user_data['roles'])
    rank = context.user_data['rank']
    opgg = context.user_data['opgg']
    discord = update.message.text.split('#')[0]
    user_id = update.effective_user.id
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Сохраняем в CSV
    with open(PARTICIPANTS_FILE, 'a', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([user_id, nick, roles, rank, opgg, discord, time])

    await update.message.reply_text(
        f"🎉 Отлично, {nick}! Вы успешно зарегистрированы.\n"
        "Ждём вас на турнире!",
        reply_markup=reply_menu
    )
    return ConversationHandler.END

# === ОБРАБОТКА РЕДАКТИРОВАНИЯ ПРОФИЛЯ ===
async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    participant = find_participant_by_id(user_id)
    if not participant:
        await update.message.reply_text("Вы не зарегистрированы. Сначала зарегистрируйтесь.")
        return

    fields = {
        "nick": "Изменить никнейм",
        "roles": "Изменить роли",
        "rank": "Изменить ранг",
        "opgg": "Изменить профиль Op.gg",
        "discord": "Изменить Discord"
    }

    options = "\n".join([f"/edit_{k} — {v}" for k, v in fields.items()])
    await update.message.reply_text(f"Выполните одну из команд для редактирования профиля:\n{options}")

async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    field_name = update.message.text.lstrip('/').split('_')[1]
    participant = find_participant_by_id(user_id)
    if not participant:
        await update.message.reply_text("Вы не зарегистрированы. Сначала зарегистрируйтесь.")
        return

    await update.message.reply_text(f"Текущее значение: {getattr(participant, field_name)}\nВведите новое значение:")
    context.user_data["field_to_edit"] = field_name
    return "WAITING_FOR_NEW_VALUE"

async def save_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new_value = update.message.text
    field_name = context.user_data.pop("field_to_edit")

    # Загружаем всех участников
    participants = load_participants()
    index = next((i for i, p in enumerate(participants) if p.user_id == user_id), None)
    if index is None:
        await update.message.reply_text("Ошибка при поиске участника.")
        return ConversationHandler.END

    # Изменяем значения
    setattr(participants[index], field_name, new_value)
    save_participants(participants)

    await update.message.reply_text("Данные успешно обновлены.", reply_markup=reply_menu)
    return ConversationHandler.END

# === ПОЛЕЗНЫЕ КЛАССЫ И ФУНКЦИИ ===
class Participant:
    def __init__(self, data_row):
        self.user_id = data_row[0]
        self.nick = data_row[1]
        self.roles = data_row[2]
        self.rank = data_row[3]
        self.opgg = data_row[4]
        self.discord = data_row[5]
        self.time = data_row[6]

def load_participants():
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Пропускаем заголовок
            return [Participant(row) for row in reader if len(row) == 7]
    except FileNotFoundError:
        return []

def save_participants(participants):
    with open(PARTICIPANTS_FILE, 'w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])
        for p in participants:
            writer.writerow([p.user_id, p.nick, p.roles, p.rank, p.opgg, p.discord, p.time])

def find_participant_by_id(user_id):
    participants = load_participants()
    return next((p for p in participants if p.user_id == str(user_id)), None)

# === СПИСОК УЧАСТНИКОВ ===
async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    participants = load_participants()
    if not participants:
        await update.message.reply_text("Пока никто не зарегистрирован.", reply_markup=reply_menu)
        return

    message = f"📋 <b>Зарегистрировано: {len(participants)} участник(а)</b>:\n\n"
    for idx, p in enumerate(participants, start=1):
        message += (
            f"{idx}. 🔹 <b>{p.nick}</b>\n"
            f"   • Роли: {p.roles}\n"
            f"   • Ранг: {p.rank}\n"
            f'   • <a href="{format_opgg_link(p.opgg)}">🎮 Op.gg</a>\n'
            f"   • Discord: <code>{p.discord}</code>\n\n"
        )
    
    await update.message.reply_html(message, disable_web_page_preview=True, reply_markup=reply_menu)

def format_opgg_link(opgg):
    if opgg.startswith('http'):
        return opgg
    else:
        return f"https://op.gg/summoners/{opgg.replace(' ', '%20')}"

# === ДАТА ПРОВЕДЕНИЯ ===
async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(TOURNAMENTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Пропускаем заголовок
            tournaments = list(reader)
    except FileNotFoundError:
        await update.message.reply_text("Нет запланированных турниров.", reply_markup=reply_menu)
        return

    if not tournaments:
        await update.message.reply_text("Нет запланированных турниров.", reply_markup=reply_menu)
        return

    message = "<b>🗓️ Планируемые турниры:</b>\n\n"
    for idx, (name, date) in enumerate(tournaments, start=1):
        message += f"{idx}. ⬣️ <b>{name}:</b> {date}\n"

    await update.message.reply_html(message, reply_markup=reply_menu)

# === ПРАВИЛА ТУРНИРОВ ===
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = """
📜 <b>ПРАВИЛА ТУРНИРОВ</b>

<b>🏆 БИТВА РЕГИОНОВ</b>
1. Формат: Best of Five (Bo5)
2. Команды: 2 по 5 человек
3. Выбор региона: только один раз за матч
4. Баны отсутствуют
5. Спорные вопросы решают организаторы

<b>🎲 ГОЛЛАНДСКИЙ РАНДОМ</b>
1. Формат: 5v5, Bo5
2. Команды формируются по MMR
3. Система смещения ролей
4. Рандомный выбор чемпионов
5. Баны отсутствуют

<b>💥 ГРАНДИОЗНАЯ ПОБОИЩНАЯ ТУСОВКА</b>
1. Формат: Best of Five (Bo5)
2. Каждая команда банит по 5 чемпионов
3. Карта: Summoner's Rift
4. Перерыв: 5 минут
5. Все споры решают организаторы
"""
    await update.message.reply_html(rules_text, reply_markup=reply_menu)

# === КОМАНДА ДЛЯ УДАЛЕНИЯ ВСЕХ УЧАСТНИКОВ ===
async def clean_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ закрыт.")
        return
    
    # Перезапись файла участников
    with open(PARTICIPANTS_FILE, 'w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])

    await update.message.reply_text("Все участники успешно удалены.")

# === КОМАНДА ДЛЯ РЕДАКТИРОВАНИЯ ТУРНИРА ===
EDITOR_STATE_NAME, EDITOR_STATE_DATE = range(2)

async def edit_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ закрыт.")
        return
    
    await update.message.reply_text("Введите название турнира:")
    return EDITOR_STATE_NAME

async def edit_tournament_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tourney_name = update.message.text.strip()
    context.user_data['tourney_name'] = tourney_name
    await update.message.reply_text("Введите дату турнира (Формат: ДД.ММ.ГГГГ чч:мм):")
    return EDITOR_STATE_DATE

async def edit_tournament_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tourney_date = update.message.text.strip()
    tourney_name = context.user_data.pop('tourney_name')

    # Сохраняем турнир в файл
    with open(TOURNAMENTS_FILE, 'a', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([tourney_name, tourney_date])

    await update.message.reply_text(f"Турнир '{tourney_name}' успешно добавлен с датой {tourney_date}.")
    return ConversationHandler.END

# === КОМАНДА ДЛЯ УДАЛЕНИЯ ПРОШЕДШИХ ТУРНИРОВ ===
async def delete_past_tournaments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ закрыт.")
        return
    
    now = datetime.now()
    cleaned_tournaments = []

    try:
        with open(TOURNAMENTS_FILE, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Пропускаем первую строку-заголовок
            
            for row in reader:
                if len(row) >= 2:
                    name, date_str = row[0], row[1]
                    
                    # Парсим дату из строки
                    event_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                    
                    # Если дата будущего турнира, добавляем обратно в файл
                    if event_date > now:
                        cleaned_tournaments.append(row)
                
        # Перезаписываем файл с оставшимися будущими турнирами
        with open(TOURNAMENTS_FILE, 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Название", "Дата"])  # записываем заголовок
            writer.writerows(cleaned_tournaments)
    
    except Exception as e:
        await update.message.reply_text(f"Ошибка при удалении прошедших турниров: {e}")
        return

    await update.message.reply_text("Прошедшие турниры успешно удалены.")

# === ОСНОВНОЙ ХЭНДЛЕР ===
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Регистрация пользователя
    conv_register_handler = ConversationHandler(
        entry_points=[
            CommandHandler("register", register_start),
            MessageHandler(filters.Text("📝 Зарегистрироваться"), register_start)
        ],
        states={
            NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nick)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
            RANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rank)],
            OP_GG: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_opgg)],
            DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_discord)]
        },
        fallbacks=[]  # Оставляем пустой список fallbacks, так как в нашем сценарии не нужны дополнительные команды выхода
    )

    # Редактирование профиля
    conv_edit_handler = ConversationHandler(
        entry_points=[CommandHandler("edit_profile", edit_profile)],
        states={
            "WAITING_FOR_NEW_VALUE": [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_value)]
        },
        fallbacks=[CommandHandler("edit_profile", edit_profile)],  # Возвращаемся к началу редактирования профиля
        per_message=True
    )

    # Редактирование турнира
    conv_edit_tournament_handler = ConversationHandler(
        entry_points=[CommandHandler("edit_tournament", edit_tournament)],
        states={
            EDITOR_STATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_tournament_name)],
            EDITOR_STATE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_tournament_date)]
        },
        fallbacks=[]  # Оставляем пустой список fallbacks, так как в нашем сценарии не нужны дополнительные команды выхода
    )

    application.add_handler(conv_register_handler)
    application.add_handler(conv_edit_handler)
    application.add_handler(conv_edit_tournament_handler)
    application.add_handler(CommandHandler("clean_all_users", clean_all_users))  # Команда для массовых очисток
    application.add_handler(CommandHandler("delete_past_tournaments", delete_past_tournaments))  # Новая команда для удаления прошедших турниров
    application.add_handler(MessageHandler(filters.Text("👥 Список участников"), show_participants))
    application.add_handler(MessageHandler(filters.Text("📅 Дата проведения"), show_dates))
    application.add_handler(MessageHandler(filters.Text("📜 Правила турниров"), show_rules))
    application.add_handler(CommandHandler("start", start))

    # Создание и запуск бота с методом run_polling()
    init_files()
    application.run_polling()

if __name__ == "__main__":
    main()
