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
... (код остался неизменным, пропустил ради экономии места)

# === КОМАНДА ДЛЯ ОТДЕЛЬНЫХ ОПЕРАЦИЙ ===
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ закрыт.")
        return
    
    # Меню администратора
    admin_menu_buttons = [
        [InlineKeyboardButton("Просмотр участников", callback_data="view_participants")],
        [InlineKeyboardButton("Удалить пользователя", callback_data="delete_user")],
        [InlineKeyboardButton("Массовое удаление", callback_data="delete_all_users")],
        [InlineKeyboardButton("Закрыть", callback_data="close_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(admin_menu_buttons)

    await update.message.reply_text("Административная панель:", reply_markup=reply_markup)

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "view_participants":
        await show_participants(query, context)
    elif query.data == "delete_user":
        await delete_user(query, context)
    elif query.data == "delete_all_users":
        await delete_all_users(query, context)
    elif query.data == "close_admin":
        await query.edit_message_text("Административная панель закрыта.")

# === ПОМОЩНИКИ ДЛЯ АДДМИНИСТРАТОРА ===
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

async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите User ID пользователя, которого хотите удалить:")
    return "WAITING_DELETE_USER"

async def wait_and_perform_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user_id = update.message.text.strip()
    participants = load_participants()

    found = False
    for i, participant in enumerate(participants):
        if participant.user_id == target_user_id:
            found = True
            del participants[i]
            break
    
    if found:
        save_participants(participants)
        await update.message.reply_text(f"Участник с User ID {target_user_id} успешно удалён.")
    else:
        await update.message.reply_text(f"Участника с указанным User ID не найдено.")
    
    return ConversationHandler.END

async def delete_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Перезапись файла участников
    with open(PARTICIPANTS_FILE, 'w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])

    await update.message.reply_text("Все участники успешно удалены.")

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

def format_opgg_link(opgg):
    if opgg.startswith('http'):
        return opgg
    else:
        return f"https://op.gg/summoners/{opgg.replace(' ', '%20')}"

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

    # Административная панель
    conv_admin_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={"ADMIN_MENU": [CallbackQueryHandler(handle_admin_actions)]},
        fallbacks=[]  # Оставляем пустой список fallbacks, так как в нашем сценарии не нужны дополнительные команды выхода
    )

    # Удаление отдельного пользователя
    conv_delete_user_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(delete_user)],
        states={"WAITING_DELETE_USER": [MessageHandler(filters.TEXT & ~filters.COMMAND, wait_and_perform_delete_user)]},
        fallbacks=[]  # Оставляем пустой список fallbacks, так как в нашем сценарии не нужны дополнительные команды выхода
    )

    application.add_handler(conv_register_handler)
    application.add_handler(conv_edit_handler)
    application.add_handler(conv_admin_handler)
    application.add_handler(conv_delete_user_handler)
    application.add_handler(MessageHandler(filters.Text("👥 Список участников"), show_participants))
    application.add_handler(MessageHandler(filters.Text("📅 Дата проведения"), show_dates))
    application.add_handler(MessageHandler(filters.Text("📜 Правила турниров"), show_rules))
    application.add_handler(CommandHandler("start", start))

    # Создание и запуск бота с методом run_polling()
    init_files()
    application.run_polling()

if __name__ == "__main__":
    main()
