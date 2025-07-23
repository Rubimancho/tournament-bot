import os
import csv
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, ContextTypes
)

# === 🔐 Чтение секретов из окружения ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Не найден BOT_TOKEN в окружении")
ADMIN_ID = os.getenv("ADMIN_ID")
if not ADMIN_ID:
    raise RuntimeError("❌ Не найден ADMIN_ID в окружении")
ADMIN_ID = int(ADMIN_ID)

# === 📁 Файлы хранения ===
PARTICIPANTS_FILE = "participants.csv"
TOURNAMENTS_FILE = "tournaments.csv"

# === Шаги регистрации ===
NICK, ROLE, RANK, OP_GG, DISCORD = range(5)

# === Основное меню ===
main_menu = ReplyKeyboardMarkup([
    ["📝 Зарегистрироваться"],
    ["📃 Список участников", "📌 Правила турниров"],
    ["📅 Даты турниров"]
], resize_keyboard=True)

# === Инициализация CSV-файлов ===
def init_files():
    if not os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id","nick","roles","rank","opgg","discord","time"])
    if not os.path.exists(TOURNAMENTS_FILE):
        with open(TOURNAMENTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["key","name","date","rules"])
            writer.writerow(["regions","Битва регионов","26 июля 2025, 18:00","🏆 Bo5, команды 5×5, без банов"])
            writer.writerow(["random","Голландский рандом","27 июля 2025, 18:00","🎲 Bo5, рандом по MMR, смена ролей"])
            writer.writerow(["brawl","Грандиозная тусовка","28 июля 2025, 18:00","💥 Bo5, по 5 банов"])


# === Утилиты работы с CSV ===
def read_csv(fname):
    with open(fname, "r", encoding="utf-8") as f:
        return list(csv.reader(f))

def write_csv(fname, rows):
    with open(fname, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🎮 Добро пожаловать! Выберите действие:", reply_markup=main_menu)


# === Регистрация участников ===
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Введите ваш никнейм в игре:", reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True))
    return NICK

async def get_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nick"] = update.message.text.strip()
    context.user_data["roles"] = []
    kb = [["🛡️ Топ","🌲 Джангл"],["🌀 Мид","🏹 ADC"],["🧙 Саппорт"],["✅ Готово"]]
    await update.message.reply_text("Выберите ваши роли (можно несколько), затем нажмите Готово:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ROLE

async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "✅ Готово":
        if not context.user_data["roles"]:
            await update.message.reply_text("⚠️ Нужно выбрать хотя бы одну роль.")
            return ROLE
        kb = [["🥉 Bronze","🥈 Silver"],["🥇 Gold","💎 Platinum"],["🟩 Emerald","🔷 Diamond"],["⭐ Master","👑 Grandmaster","🏆 Challenger"]]
        await update.message.reply_text("Выберите ваш ранг:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True))
        return RANK
    role = text.split(" ",1)[-1]
    if role not in context.user_data["roles"]:
        context.user_data["roles"].append(role)
        await update.message.reply_text(f"➕ Роль «{role}» добавлена.")
    else:
        await update.message.reply_text(f"✔️ Роль «{role}» уже выбрана.")
    return ROLE

async def get_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rank"] = update.message.text.strip().split(" ",1)[-1]
    await update.message.reply_text("Введите ссылку на Op.gg профиль:", reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True))
    return OP_GG

async def get_opgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["opgg"] = update.message.text.strip()
    await update.message.reply_text("Введите ваш Discord (ник без #):")
    return DISCORD

async def get_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    discord = update.message.text.strip().split("#",1)[0]
    data["discord"] = discord
    user_id = update.effective_user.id
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Читаем старые
    rows = read_csv(PARTICIPANTS_FILE)
    # Убираем старую запись
    rows = [r for r in rows if r and r[0] != str(user_id)]
    # Добавляем новую
    rows.append([str(user_id), data["nick"], ",".join(data["roles"]), data["rank"], data["opgg"], discord, now])
    write_csv(PARTICIPANTS_FILE, rows)
    await update.message.reply_text("✅ Регистрация завершена!", reply_markup=main_menu)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.", reply_markup=main_menu)
    return ConversationHandler.END


# === Просмотр списка участников ===
async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(PARTICIPANTS_FILE)[1:]
    if not rows:
        await update.message.reply_text("Пока никто не зарегистрирован.", reply_markup=main_menu)
        return
    msg = f"📋 Участников: {len(rows)}\n\n"
    for i,r in enumerate(rows,1):
        msg += f"{i}. {r[1]} | {r[2]} | {r[3]}\n"
    await update.message.reply_text(msg, reply_markup=main_menu)


# === Правила и даты турниров ===
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(TOURNAMENTS_FILE)[1:]
    text = ""
    for key,name,date,rules in rows:
        text += f"🏷️ <b>{name}</b>\n{rules}\n\n"
    await update.message.reply_html(text, reply_markup=main_menu)

async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(TOURNAMENTS_FILE)[1:]
    text = "🗓 <b>Даты турниров:</b>\n\n"
    for key,name,date,rules in rows:
        text += f"🔸 <b>{name}</b>: {date}\n"
    await update.message.reply_html(text, reply_markup=main_menu)


# === Админ-панель: Inline-кнопки ===
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ только для администратора.")
        return
    rows = read_csv(TOURNAMENTS_FILE)[1:]
    buttons = [
        [InlineKeyboardButton(f"{name} (✏️)", callback_data=f"edit:{key}")]
        for key,name,date,rules in rows
    ]
    buttons.append([InlineKeyboardButton("➕ Добавить турнир", callback_data="add")])
    await update.message.reply_text("🔧 Админ‑панель:", reply_markup=InlineKeyboardMarkup(buttons))


# === Обработка нажатий в админ-панели ===
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Редактировать существующий
    if data.startswith("edit:"):
        key = data.split(":",1)[1]
        context.user_data["t_key"] = key
        await query.message.reply_text("Введите новое название:")
        return 100
    # Добавить новый
    if data == "add":
        await query.message.reply_text("Введите уникальный ключ нового турнира:")
        return 200

    return ConversationHandler.END

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["t_key"]
    new_name = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0] == key:
            r[1] = new_name
            break
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Название обновлено. Теперь введите новую дату:")
    return 101

async def edit_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["t_key"]
    new_date = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0] == key:
            r[2] = new_date
            break
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Дата обновлена. Теперь введите правила:")
    return 102

async def edit_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["t_key"]
    new_rules = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0] == key:
            r[3] = new_rules
            break
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Правила обновлены.", reply_markup=main_menu)
    return ConversationHandler.END

async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    context.user_data["new_key"] = key
    await update.message.reply_text("Введите название турнира:")
    return 200

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_name"] = update.message.text.strip()
    await update.message.reply_text("Введите дату турнира:")
    return 201

async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_date"] = update.message.text.strip()
    await update.message.reply_text("Введите правила турнира:")
    return 202

async def add_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["new_key"]
    rows = read_csv(TOURNAMENTS_FILE)
    rows.append([ key,
                  context.user_data["new_name"],
                  context.user_data["new_date"],
                  update.message.text.strip() ])
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Новый турнир добавлен.", reply_markup=main_menu)
    return ConversationHandler.END


# === Удаление участника /delete USER_ID ===
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только админ.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /delete USER_ID")
        return
    uid = context.args[0]
    rows = read_csv(PARTICIPANTS_FILE)
    new = [r for r in rows if r and r[0]!=uid]
    write_csv(PARTICIPANTS_FILE, new)
    await update.message.reply_text("✅ Участник удалён.")


# === Запуск бота ===
def main():
    init_files()
    app = Application.builder().token(TOKEN).build()

    # Регистрация conversation
    reg_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Зарегистрироваться$"), register_start)],
        states={
            NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nick)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
            RANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rank)],
            OP_GG: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_opgg)],
            DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_discord)],
        },
        fallbacks=[MessageHandler(filters.Regex("^Отмена$"), cancel)]
    )

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback)],
        states={
            100: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            101: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_date)],
            102: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_rules)],
            200: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_key)],
            201: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            202: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_date)],
            203: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rules)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(reg_conv)
    app.add_handler(MessageHandler(filters.Regex("^📃 Список участников$"), show_participants))
    app.add_handler(MessageHandler(filters.Regex("^📜 Правила турниров$"), show_rules))
    app.add_handler(MessageHandler(filters.Regex("^📅 Даты турниров$"), show_dates))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(admin_conv)
    app.add_handler(CommandHandler("delete", delete_user))

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
