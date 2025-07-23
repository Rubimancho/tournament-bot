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
    CallbackQueryHandler,
)

# === 🔐 Переменные окружения ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не установлена")

ADMIN_ID = os.getenv("ADMIN_ID")
if not ADMIN_ID:
    raise ValueError("❌ Переменная окружения ADMIN_ID не установлена")
ADMIN_ID = int(ADMIN_ID)

# === Файлы ===
PARTICIPANTS_FILE = "participants.csv"
TOURNAMENTS_FILE = "tournaments.csv"

# === Этапы регистрации ===
NICK, ROLE, RANK, OPGG, DISCORD = range(5)

# === Админ-конверсации ===
EDIT_NAME, EDIT_DATE, EDIT_RULES = 100, 101, 102
ADD_KEY, ADD_NAME, ADD_DATE, ADD_RULES = 200, 201, 202, 203

# === Главное меню ===
main_menu_kb = [
    ["📝 Зарегистрироваться"],
    ["📃 Список участников", "📅 Даты турниров"],
    ["📜 Правила турниров", "⚙️ Админ-панель"]
]
MAIN_MENU = ReplyKeyboardMarkup(main_menu_kb, resize_keyboard=True)

# === Инициализация файлов ===
def init_files():
    # Участники
    if not os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "nick", "roles", "rank", "opgg", "discord", "time"])
        print("📁 participants.csv создан")

    # Турниры
    if not os.path.exists(TOURNAMENTS_FILE):
        with open(TOURNAMETS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["key", "name", "date", "rules"])
            writer.writerows([
                ["regions", "Битва регионов", "26 июля 2025, 18:00", "🏆 Bo5, команды 5×5, без банов"],
                ["random", "Голландский рандом", "27 июля 2025, 18:00", "🎲 Bo5, рандом по MMR, смена ролей"],
                ["brawl", "Грандиозная тусовка", "28 июля 2025, 18:00", "💥 Bo5, по 5 банов"]
            ])
        print("📁 tournaments.csv создан")

# === Чтение и запись CSV ===
def read_csv(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.reader(f))
    except FileNotFoundError:
        return []

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🎮 Добро пожаловать! Выберите действие:", reply_markup=MAIN_MENU)

# === Регистрация ===
async def reg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите ваш никнейм:", reply_markup=ReplyKeyboardRemove())
    return NICK

async def reg_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nick"] = update.message.text.strip()
    kb = [
        ["🛡️ Топ", "🌲 Джангл"],
        ["🌀 Мид", "🏹 ADC"],
        ["🧙 Саппорт"],
        ["✅ Готово"]
    ]
    await update.message.reply_text(
        "Выберите роли (можно несколько), затем нажмите «✅ Готово»:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    context.user_data["roles"] = []
    return ROLE

async def reg_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "✅ Готово":
        if not context.user_data["roles"]:
            await update.message.reply_text("⚠️ Выберите хотя бы одну роль.")
            return ROLE
        kb = [
            ["🥉 Bronze", "🥈 Silver"],
            ["🥇 Gold", "💎 Platinum"],
            ["🟩 Emerald", "🔷 Diamond"],
            ["⭐ Master", "👑 Grandmaster", "🏆 Challenger"]
        ]
        await update.message.reply_text("Выберите свой ранг:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True))
        return RANK
    role = text.split(" ", 1)[-1]
    if role not in context.user_data["roles"]:
        context.user_data["roles"].append(role)
        await update.message.reply_text(f"➕ Роль «{role}» добавлена.")
    else:
        await update.message.reply_text(f"✔️ Роль «{role}» уже есть.")
    return ROLE

async def reg_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text.strip()
    context.user_data["rank"] = raw_text.split(" ", 1)[-1]
    await update.message.reply_text("Введите ссылку на Op.gg:", reply_markup=ReplyKeyboardRemove())
    return OPGG

async def reg_opgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["opgg"] = update.message.text.strip()
    await update.message.reply_text("Введите ваш Discord (ник без #):")
    return DISCORD

async def reg_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    discord = update.message.text.strip().split("#", 1)[0]
    data = context.user_data
    data["discord"] = discord
    user_id = str(update.effective_user.id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Читаем и обновляем
    rows = read_csv(PARTICIPANTS_FILE)
    rows = [r for r in rows if r and r[0] != user_id]
    rows.append([user_id, data["nick"], ",".join(data["roles"]), data["rank"], data["opgg"], discord, now])
    write_csv(PARTICIPANTS_FILE, rows)

    await update.message.reply_text("✅ Вы успешно зарегистрированы!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Регистрация отменена.", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# === Список участников ===
async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(PARTICIPANTS_FILE)
    if len(rows) <= 1:
        await update.message.reply_text("Пока никто не зарегистрирован.", reply_markup=MAIN_MENU)
        return
    msg = "📋 <b>Участники:</b>\n\n"
    for i, r in enumerate(rows[1:], start=1):
        if len(r) < 7: continue
        nick = r[1]
        roles = r[2].replace(",", ", ")
        rank = r[3]
        opgg = r[4]
        url = opgg if opgg.startswith("http") else f"https://op.gg/summoners/{opgg.replace(' ', '%20')}"
        msg += f"{i}. <b>{nick}</b> | {roles} | {rank}\n"
        msg += f'   • <a href="{url}">🎮 Op.gg</a>\n\n'
    await update.message.reply_html(msg, disable_web_page_preview=True, reply_markup=MAIN_MENU)

# === Даты турниров ===
async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(TOURNAMENTS_FILE)
    if len(rows) <= 1:
        await update.message.reply_text("📅 Пока нет турниров.", reply_markup=MAIN_MENU)
        return
    msg = "<b>📅 Даты турниров:</b>\n\n"
    for row in rows[1:]:
        if len(row) >= 3:
            msg += f"🔸 <b>{row[1]}</b>: {row[2]}\n"
    await update.message.reply_html(msg, reply_markup=MAIN_MENU)

# === Правила турниров ===
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(TOURNAMENTS_FILE)
    if len(rows) <= 1:
        await update.message.reply_text("📌 Пока нет правил.", reply_markup=MAIN_MENU)
        return
    msg = "<b>📜 Правила турниров:</b>\n\n"
    for row in rows[1:]:
        if len(row) >= 4:
            msg += f"🏷️ <b>{row[1]}</b>:\n{row[3]}\n\n"
    await update.message.reply_html(msg, reply_markup=MAIN_MENU)

# === /setdate — обновить дату турнира (по ключу) ===
async def setdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только администратор.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("UsageId: /setdate [ключ] [дата]\nПример: /setdate regions 30.07.2025 20:00")
        return
    key = context.args[0]
    date = " ".join(context.args[1:])
    rows = read_csv(TOURNAMENTS_FILE)
    updated = False
    for row in rows:
        if len(row) > 0 and row[0] == key:
            row[2] = date
            updated = True
    if updated:
        write_csv(TOURNAMENTS_FILE, rows)
        await update.message.reply_text(f"✅ Дата турнира '{key}' обновлена: {date}", reply_markup=MAIN_MENU)
    else:
        await update.message.reply_text("❌ Турнир с таким ключом не найден.", reply_markup=MAIN_MENU)

# === Админ-панель ===
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ только администратору.")
        return
    rows = read_csv(TOURNAMENTS_FILE)
    if len(rows) <= 1:
        await update.message.reply_text("⚠️ Нет турниров.", reply_markup=MAIN_MENU)
        return
    buttons = []
    for row in rows[1:]:
        if len(row) >= 2:
            key, name = row[0], row[1]
            buttons.append([
                InlineKeyboardButton(f"✏️ {name}", callback_data=f"edit:{key}"),
                InlineKeyboardButton("🗑️", callback_data=f"del:{key}")
            ])
    buttons.append([InlineKeyboardButton("➕ Добавить турнир", callback_data="add")])
    await update.message.reply_text("🔧 Админ-панель:", reply_markup=InlineKeyboardMarkup(buttons))

# === Обработка админ-действий ===
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("edit:"):
        key = data.split(":", 1)[1]
        context.user_data["edit_key"] = key
        await query.message.reply_text("Введите новое название:")
        return EDIT_NAME

    elif data.startswith("del:"):
        key = data.split(":", 1)[1]
        rows = read_csv(TOURNAMENTS_FILE)
        rows = [r for r in rows if not (r and r[0] == key)]
        write_csv(TOURNAMENTS_FILE, rows)
        await query.message.reply_text("🗑 Турнир удалён.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    elif data == "add":
        await query.message.reply_text("Введите ключ нового турнира (латиницей):")
        return ADD_KEY

# === Редактирование турнира ===
async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_key"]
    new = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0] == key:
            r[1] = new
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Название обновлено. Введите новую дату:")
    return EDIT_DATE

async def edit_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_key"]
    new = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0] == key:
            r[2] = new
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Дата обновлена. Введите новые правила:")
    return EDIT_RULES

async def edit_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_key"]
    new = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0] == key:
            r[3] = new
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Правила обновлены.", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# === Добавление турнира ===
async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_key"] = update.message.text.strip()
    await update.message.reply_text("Введите название турнира:")
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_name"] = update.message.text.strip()
    await update.message.reply_text("Введите дату турнира:")
    return ADD_DATE

async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_date"] = update.message.text.strip()
    await update.message.reply_text("Введите правила турнира:")
    return ADD_RULES

async def add_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["new_key"]
    name = context.user_data["new_name"]
    date = context.user_data["new_date"]
    rules = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    rows.append([key, name, date, rules])
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Турнир добавлен.", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# === Удаление участника ===
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только администратор.")
        return
    if not context.args:
        await update.message.reply_text("UsageId: /delete [user_id]")
        return
    uid = context.args[0]
    rows = read_csv(PARTICIPANTS_FILE)
    rows = [r for r in rows if r and r[0] != uid]
    write_csv(PARTICIPANTS_FILE, rows)
    await update.message.reply_text(f"✅ Участник {uid} удалён.", reply_markup=MAIN_MENU)

# === Запуск бота ===
def main():
    init_files()
    app = Application.builder().token(TOKEN).build()

    # Конверсация регистрации
    reg_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Зарегистрироваться$"), reg_start)],
        states={
            NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_nick)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_role)],
            RANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_rank)],
            OPGG: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_opgg)],
            DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_discord)],
        },
        fallbacks=[MessageHandler(filters.Regex("^(❌ Отмена|Отмена)$"), reg_cancel)],
        per_user=True
    )

    # Конверсация админки
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback)],
        states={
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_date)],
            EDIT_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_rules)],
            ADD_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_key)],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_date)],
            ADD_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rules)],
        },
        fallbacks=[],
        per_user=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(reg_conv)
    app.add_handler(MessageHandler(filters.Regex("^📃 Список участников$"), show_participants))
    app.add_handler(MessageHandler(filters.Regex("^📅 Даты турниров$"), show_dates))
    app.add_handler(MessageHandler(filters.Regex("^📜 Правила турниров$"), show_rules))
    app.add_handler(MessageHandler(filters.Regex("^⚙️ Админ-панель$"), admin_panel))
    app.add_handler(admin_conv)
    app.add_handler(CommandHandler("setdate", setdate))
    app.add_handler(CommandHandler("delete", delete_user))

    print("✅ Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
