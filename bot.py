```python
import os
import csv
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes
)

# === 🔐 Чтение токена и ID администратора из окружения ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Не задан BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
if not ADMIN_ID:
    raise RuntimeError("❌ Не задан ADMIN_ID")
ADMIN_ID = int(ADMIN_ID)

# === Пути к CSV-файлам ===
PARTICIPANTS_FILE = "participants.csv"
TOURNAMENTS_FILE  = "tournaments.csv"

# === Этапы регистрации ===
NICK, ROLE, RANK, OPGG, DISCORD = range(5)

# === Этапы админ‑панели ===
EDIT_NAME, EDIT_DATE = 100, 101
ADD_KEY, ADD_NAME, ADD_DATE, ADD_RULES = 200, 201, 202, 203

# === Клавиатуры ===
MAIN_KB = ReplyKeyboardMarkup([
    ["📝 Зарегистрироваться"],
    ["📃 Список участников", "📜 Правила турниров"],
    ["📅 Даты турниров", "⚙️ Админ-панель"]
], resize_keyboard=True)

ROLES_KB = ReplyKeyboardMarkup([
    ["🛡️ Топ","🌲 Джангл"],
    ["🌀 Мид","🏹 ADC"],
    ["🧙 Саппорт"],
    ["✅ Готово"]
], resize_keyboard=True)

RANK_KB = ReplyKeyboardMarkup([
    ["🥉 Bronze","🥈 Silver"],
    ["🥇 Gold","💎 Platinum"],
    ["🟩 Emerald","🔷 Diamond"],
    ["⭐ Master","👑 Grandmaster","🏆 Challenger"]
], resize_keyboard=True, one_time_keyboard=True)

TOURN_KB = ReplyKeyboardMarkup([
    ["🏆 Битва регионов"],
    ["🎲 Голландский рандом"],
    ["💥 Грандиозная тусовка"],
    ["⬅️ Назад"]
], resize_keyboard=True)

# === Инициализация файлов ===
def init_files():
    if not os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["user_id","nick","roles","rank","opgg","discord","time"]
            )
    if not os.path.exists(TOURNAMENTS_FILE):
        with open(TOURNAMENTS_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows([
                ["key","name","date","rules"],
                ["regions","Битва регионов","26 июля 2025, 18:00","🏆 Bo5, команды 5×5, без банов"],
                ["random","Голландский рандом","27 июля 2025, 18:00","🎲 Bo5, рандом по MMR, смена ролей"],
                ["brawl","Грандиозная тусовка","28 июля 2025, 18:00","💥 Bo5, по 5 банов"]
            ])

def read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.reader(f))

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

# === Проверка регистрации ===
def is_registered(user_id):
    try:
        for row in read_csv(PARTICIPANTS_FILE)[1:]:
            if row and row[0] == str(user_id):
                return True
    except FileNotFoundError:
        pass
    return False

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 Главное меню:", reply_markup=MAIN_KB)

# === Регистрация-конверсация ===
async def reg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_registered(uid):
        await update.message.reply_text("✅ Вы уже зарегистрированы.", reply_markup=MAIN_KB)
        return ConversationHandler.END
    await update.message.reply_text("Введите ваш никнейм:", reply_markup=ReplyKeyboardRemove())
    return NICK

async def reg_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nick"] = update.message.text.strip()
    context.user_data["roles"] = []
    await update.message.reply_text("Выберите роли:", reply_markup=ROLES_KB)
    return ROLE

async def reg_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Инициализация списка ролей
    if 'roles' not in context.user_data:
        context.user_data['roles'] = []
    if text == "✅ Готово":
        if not context.user_data["roles"]:
            await update.message.reply_text("⚠️ Нужно хотя бы одну роль.")
            return ROLE
        await update.message.reply_text("Выберите ваш ранг:", reply_markup=RANK_KB)
        return RANK
    role = text.split(" ",1)[-1]
    if role not in context.user_data["roles"]:
        context.user_data["roles"].append(role)
        await update.message.reply_text(f"➕ Роль «{role}» добавлена.")
    else:
        await update.message.reply_text("⚠️ Уже добавлено.")
    return ROLE

async def reg_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rank"] = update.message.text.split(" ",1)[-1]
    await update.message.reply_text("Введите ссылку на Op.gg:", reply_markup=ReplyKeyboardRemove())
    return OPGG

async def reg_opgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["opgg"] = update.message.text.strip()
    await update.message.reply_text("Ваш Discord (ник без #):")
    return DISCORD

async def reg_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.user_data
    discord = update.message.text.strip().split("#",1)[0]
    # читаем и обновляем CSV
    rows = read_csv(PARTICIPANTS_FILE)
    rows = [r for r in rows if r and r[0]!=str(user.id)]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows.append([
        str(user.id),
        data["nick"],
        ",".join(data["roles"]),
        data["rank"],
        data["opgg"],
        discord,
        now
    ])
    write_csv(PARTICIPANTS_FILE, rows)
    await update.message.reply_text("✅ Вы зарегистрированы!", reply_markup=MAIN_KB)
    return ConversationHandler.END

async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Регистрация отменена.", reply_markup=MAIN_KB)
    return ConversationHandler.END

# === Список участников ===
async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(PARTICIPANTS_FILE)[1:]
    if not rows:
        await update.message.reply_text("Пока нет участников.", reply_markup=MAIN_KB)
        return
    msg = "📋 Участники:\n\n"
    for i, r in enumerate(rows,1):
        msg += f"{i}. {r[1]} | {r[2]} | {r[3]}\n"
    await update.message.reply_text(msg, reply_markup=MAIN_KB)

# === Правила турниров ===
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(TOURNAMENTS_FILE)[1:]
    text = ""
    for _, name, _, rules in rows:
        text += f"🏷️ <b>{name}</b>:\n{rules}\n\n"
    await update.message.reply_html(text, reply_markup=MAIN_KB)

# === Даты турниров ===
async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = read_csv(TOURNAMENTS_FILE)[1:]
    text = "<b>📅 Даты турниров:</b>\n\n"
    for _, name, date, _ in rows:
        text += f"🔸 <b>{name}</b>: {date}\n"
    await update.message.reply_html(text, reply_markup=MAIN_KB)

# === Админ‑панель ===
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return
    buttons = [
        [InlineKeyboardButton("✏️ Редактировать турнир", callback_data="edit")],
        [InlineKeyboardButton("➕ Добавить турнир", callback_data="add")],
        [InlineKeyboardButton("🧹 Очистить участников", callback_data="clear")]
    ]
    await update.message.reply_text("🔧 Админ‑панель:", reply_markup=InlineKeyboardMarkup(buttons))

# === Обработка админ inline ===
async def admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "clear":
        write_csv(PARTICIPANTS_FILE, [["user_id","nick","roles","rank","opgg","discord","time"]])
        await query.message.reply_text("✅ Список участников очищен.")
        return
    rows = read_csv(TOURNAMENTS_FILE)
    if data == "edit":
        buttons = []
        for key, name, date, rules in rows[1:]:
            buttons.append([InlineKeyboardButton(name, callback_data=f"edit:{key}")])
        await query.message.reply_text("Выберите турнир:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("edit:"):
        key = data.split(":",1)[1]
        context.user_data["edit_key"] = key
        await query.message.reply_text("Введите новое название:")
        return EDIT_NAME
    elif data == "add":
        await query.message.reply_text("Введите уникальный ключ нового турнира:")
        return ADD_KEY

# === Редактирование турнира ===
async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_key"]
    new = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r[0] == key:
            r[1] = new
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Название обновлено. Введите новую дату:")
    return EDIT_DATE

async def edit_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_key"]
    new = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r[0] == key:
            r[2] = new
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Дата обновлена.", reply_markup=MAIN_KB)
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
    rows = read_csv(TOURNAMENTS_FILE)
    rows.append([
        context.user_data["new_key"],
        context.user_data["new_name"],
        context.user_data["new_date"],
        update.message.text.strip()
    ])
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Турнир добавлен.", reply_markup=MAIN_KB)
    return ConversationHandler.END

# === Сборка и запуск ===
def main():
    init_files()
    app = Application.builder().token(TOKEN).build()

    # Регистрация
    reg_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Зарегистрироваться$"), reg_start)],
        states={
            NICK:   [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_nick)],
            ROLE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_role)],
            RANK:   [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_rank)],
            OPGG:   [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_opgg)],
            DISCORD:[MessageHandler(filters.TEXT & ~filters.COMMAND, reg_discord)],
        },
        fallbacks=[MessageHandler(filters.Regex("^Отмена$"), reg_cancel)]
    )

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_cb)],
        states={
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
            EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_date)],
            ADD_KEY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_key)],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_date)],
            ADD_RULES:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_rules)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(reg_conv)
    app.add_handler(MessageHandler(filters.Regex("^📃 Список участников$"), show_participants))
    app.add_handler(MessageHandler(filters.Regex("^📜 Правила турниров$"), show_rules))
    app.add_handler(MessageHandler(filters.Regex("^📅 Даты турниров$"), show_dates))
    app.add_handler(MessageHandler(filters.Regex("^⚙️ Админ-панель$"), admin_panel))
    app.add_handler(admin_conv)

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
```
