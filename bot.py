import os
import csv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler
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
    ["📝 Зарегистрироваться", "📄 Редактировать профиль"],
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
    with open(PARTICIPANTS_FILE, 'a', newline='', encoding='utf-8') as f:
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

    keyboard = [[InlineKeyboardButton(text=v, callback_data=k)] for k, v in fields.items()]
    keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_edit")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выберите поле для редактирования:", reply_markup=reply_markup)
    return "EDITING_PROFILE"

async def process_field_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    field_name = query.data
    await query.answer()

    if field_name == "cancel_edit":
        await query.edit_message_text("Редактирование отменено.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    participant = find_participant_by_id(user_id)
    current_value = getattr(participant, field_name)

    await query.edit_message_text(f"Текущее значение: {current_value}\nВведите новое значение:")
    context.user_data["editing_field"] = field_name
    return "WAITING_FOR_VALUE"

async def save_edited_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new_value = update.message.text
    editing_field = context.user_data.pop("editing_field")

    # Загружаем всех участников
    participants = load_participants()
    index = next((i for i, p in enumerate(participants) if p.user_id == user_id), None)
    if index is None:
        await update.message.reply_text("Ошибка при поиске участника.")
        return ConversationHandler.END

    # Изменяем значения
    setattr(participants[index], editing_field, new_value)
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
    with open(PARTICIPANTS_FILE, 'w', newline='', encoding='utf-8') as f:
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

# === АДМИНИСТРАТОРСКАЯ ЧАСТЬ ===
admin_menu_kb = [
    ["📅 Добавить турнир", "🖊️ Удалить турнир"],
    ["👥 Удалить участника", "🗃️ Полная очистка"],
    ["📜 Вернуться назад"]
]
admin_reply_menu = ReplyKeyboardMarkup(admin_menu_kb, resize_keyboard=True)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    
    await update.message.reply_text("Панель администратора:", reply_markup=admin_reply_menu)

async def add_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    
    await update.message.reply_text("Введите название нового турнира:")
    return "ADD_TOURNAMENT_NAME"

async def process_add_tournament_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tournament_name = update.message.text
    context.user_data["new_tournament"] = {"name": tournament_name}
    await update.message.reply_text("Введите дату и время турнира (формат: ДД.ММ.ГГГГ чч:мм):")
    return "ADD_TOURNAMENT_DATE"

async def process_add_tournament_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tournament_date = update.message.text
    new_tournament = context.user_data.get("new_tournament", {})
    new_tournament["date"] = tournament_date

    # Сохраняем новую строку в файле турниров
    with open(TOURNAMENTS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([new_tournament["name"], new_tournament["date"]])

    del context.user_data["new_tournament"]
    await update.message.reply_text("Турнир успешно добавлен!", reply_markup=admin_reply_menu)
    return ConversationHandler.END

async def remove_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    
    try:
        with open(TOURNAMENTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Пропускаем заголовок
            tournaments = list(reader)
    except FileNotFoundError:
        await update.message.reply_text("Нет турниров для удаления.")
        return

    if not tournaments:
        await update.message.reply_text("Нет турниров для удаления.")
        return

    buttons = [[InlineKeyboardButton(name, callback_data=f"remove_{index}")] for index, (name, _) in enumerate(tournaments)]
    buttons.append([InlineKeyboardButton("Отмена", callback_data="cancel_remove")])
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text("Выберите турнир для удаления:", reply_markup=reply_markup)
    return "REMOVE_TOURNAMENT_SELECTION"

async def confirm_remove_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    await query.answer()

    if action == "cancel_remove":
        await query.edit_message_text("Удаление отменено.", reply_markup=admin_reply_menu)
        return ConversationHandler.END

    tournament_index = int(action.split("_")[1])
    removed_tournament = ""

    try:
        with open(TOURNAMENTS_FILE, 'r+', encoding='utf-8') as f:
            lines = f.readlines()
            header = lines[:1]
            body = lines[1:]
            removed_tournament = body[tournament_index].strip()
            del body[tournament_index]
            f.seek(0)
            f.write(''.join(header + body))
            f.truncate()
    except IndexError:
        await query.edit_message_text("Ошибка при удалении турнира.")
        return ConversationHandler.END

    await query.edit_message_text(f"🗑 Турнир '{removed_tournament}' удалён.", reply_markup=admin_reply_menu)
    return ConversationHandler.END

async def remove_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    
    await update.message.reply_text("Введите User ID участника для удаления:")
    return "REMOVE_PARTICIPANT_ID"

async def process_remove_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_to_delete = update.message.text
    participants = load_participants()
    found = False

    for p in participants:
        if p.user_id == user_id_to_delete:
            found = True
            participants.remove(p)
            break

    if found:
        save_participants(participants)
        await update.message.reply_text(f"Участник с ID {user_id_to_delete} удалён.", reply_markup=admin_reply_menu)
    else:
        await update.message.reply_text("Пользователь с указанным ID не найден.", reply_markup=admin_reply_menu)
    return ConversationHandler.END

async def full_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    
    with open(PARTICIPANTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])
    
    with open(TOURNAMENTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Название", "Дата"])
    
    await update.message.reply_text("Все данные очищены.", reply_markup=admin_reply_menu)
    return ConversationHandler.END

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
        entry_points=[CommandHandler("edit_profile", edit_profile), MessageHandler(filters.Text("📄 Редактировать профиль"), edit_profile)],
        states={
            "EDITING_PROFILE": [CallbackQueryHandler(process_field_selection)],
            "WAITING_FOR_VALUE": [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_field)]
        },
        fallbacks=[CallbackQueryHandler(lambda u,c: c.answer())],
        per_message=True
    )

    # Панель администратора
    conv_admin_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={
            "ADD_TOURNAMENT_NAME": [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_tournament_name)],
            "ADD_TOURNAMENT_DATE": [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_tournament_date)],
            "REMOVE_TOURNAMENT_SELECTION": [CallbackQueryHandler(confirm_remove_tournament)],
            "REMOVE_PARTICIPANT_ID": [MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_participant)]
        },
        fallbacks=[CallbackQueryHandler(lambda u,c: c.answer()), CommandHandler("admin", admin_panel)],
        per_message=True
    )

    application.add_handler(conv_register_handler)
    application.add_handler(conv_edit_handler)
    application.add_handler(conv_admin_handler)
    application.add_handler(MessageHandler(filters.Text("👥 Список участников"), show_participants))
    application.add_handler(MessageHandler(filters.Text("📅 Дата проведения"), show_dates))
    application.add_handler(MessageHandler(filters.Text("📜 Правила турниров"), show_rules))
    application.add_handler(CommandHandler("full_cleanup", full_cleanup))
    application.add_handler(CommandHandler("start", start))

    # Запуск бота
    init_files()
    application.run_polling()

if __name__ == "__main__":
    main()
