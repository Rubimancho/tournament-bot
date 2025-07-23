import os
import csv
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# === Настройки из окружения ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Нет BOT_TOKEN в окружении")
ADMIN_ID = os.getenv("ADMIN_ID")
if not ADMIN_ID:
    raise RuntimeError("❌ Нет ADMIN_ID в окружении")
ADMIN_ID = int(ADMIN_ID)

# === Файлы хранения ===
PARTICIPANTS_FILE = "participants.csv"
TOURNAMENTS_FILE = "tournaments.csv"

# === Шаги регистрации ===
NICK, ROLE, RANK, OPGG, DISCORD = range(5)

# === Главное меню ===
main_menu_kb = [
    ["📝 Зарегистрироваться"],
    ["📃 Список участников", "📜 Правила турниров"],
    ["📅 Даты турниров", "⚙️ Админ-панель"]
]
MAIN_MENU = ReplyKeyboardMarkup(main_menu_kb, resize_keyboard=True)

# === Инициализация файлов ===
def init_files():
    if not os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["user_id", "nick", "roles", "rank", "opgg", "discord", "time"]
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

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 Добро пожаловать! Выберите действие:", reply_markup=MAIN_MENU
    )

# === Регистрация-конверсация ===
async def reg_start(update, context):
    await update.message.reply_text(
        "Введите ваш никнейм:", reply_markup=ReplyKeyboardRemove()
    )
    return NICK

async def reg_nick(update, context):
    context.user_data["nick"] = update.message.text.strip()
    # предложить выбор ролей
    kb = [
        ["🛡️ Топ", "🌲 Джангл"],
        ["🌀 Мид", "🏹 ADC"],
        ["🧙 Саппорт"],
        ["✅ Готово"]
    ]
    await update.message.reply_text(
        "Выберите роли (несколько), затем нажмите «Готово»:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )
    context.user_data["roles"] = []
    return ROLE

async def reg_role(update, context):
    text = update.message.text.strip()
    if text == "✅ Готово":
        if not context.user_data["roles"]:
            await update.message.reply_text("⚠️ Нужно выбрать хотя бы одну роль.")
            return ROLE
        # ранги
        kb = [
            ["🥉 Bronze", "🥈 Silver"],
            ["🥇 Gold", "💎 Platinum"],
            ["🟩 Emerald", "🔷 Diamond"],
            ["⭐ Master", "👑 Grandmaster", "🏆 Challenger"]
        ]
        await update.message.reply_text(
            "Выберите свой ранг:", 
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
        )
        return RANK
    # иначе добавляем роль
    role = text.split(" ",1)[-1]
    if role not in context.user_data["roles"]:
        context.user_data["roles"].append(role)
        await update.message.reply_text(f"➕ Роль «{role}» добавлена.")
    else:
        await update.message.reply_text(f"✔️ Роль «{role}» уже есть.")
    return ROLE

async def reg_rank(update, context):
    context.user_data["rank"] = update.message.text.strip().split(" ",1)[-1]
    await update.message.reply_text("Введите ссылку на Op.gg:", reply_markup=ReplyKeyboardRemove())
    return OPGG

async def reg_opgg(update, context):
    context.user_data["opgg"] = update.message.text.strip()
    await update.message.reply_text("Введите ваш Discord (ник без #):")
    return DISCORD

async def reg_discord(update, context):
    discord = update.message.text.strip().split("#",1)[0]
    data = context.user_data
    data["discord"] = discord
    # сохранить в CSV
    rows = read_csv(PARTICIPANTS_FILE)
    # удаляем старую строку если была
    rows = [r for r in rows if r and r[0] != str(update.effective_user.id)]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows.append([
        str(update.effective_user.id),
        data["nick"],
        ",".join(data["roles"]),
        data["rank"],
        data["opgg"],
        discord,
        now
    ])
    write_csv(PARTICIPANTS_FILE, rows)
    await update.message.reply_text("✅ Вы зарегистрированы!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def reg_cancel(update, context):
    await update.message.reply_text("❌ Регистрация отменена.", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# === Список участников ===
async def show_participants(update, context):
    rows = read_csv(PARTICIPANTS_FILE)[1:]
    if not rows:
        await update.message.reply_text("Пока нет участников.", reply_markup=MAIN_MENU)
        return
    msg = f"📋 Участников: {len(rows)}\n\n"
    for i,r in enumerate(rows,1):
        msg += f"{i}. {r[1]} | {r[2]} | {r[3]}\n"
    await update.message.reply_text(msg, reply_markup=MAIN_MENU)

# === Правила турниров ===
async def show_rules(update, context):
    rows = read_csv(TOURNAMENTS_FILE)[1:]
    text = "<b>📜 Правила турниров:</b>\n\n"
    for key,name,date,rules in rows:
        text += f"🏷️ <b>{name}</b>:\n{rules}\n\n"
    await update.message.reply_html(text, reply_markup=MAIN_MENU)

# === Даты турниров ===
async def show_dates(update, context):
    rows = read_csv(TOURNAMENTS_FILE)[1:]
    text = "<b>📅 Даты турниров:</b>\n\n"
    for key,name,date,rules in rows:
        text += f"🔸 <b>{name}</b>: {date}\n"
    await update.message.reply_html(text, reply_markup=MAIN_MENU)

# === Админ-панель ===
async def admin_panel(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ только администратору.")
        return
    rows = read_csv(TOURNAMENTS_FILE)[1:]
    buttons = []
    for key,name,date,rules in rows:
        buttons.append([
            InlineKeyboardButton(f"✏️ {name}", callback_data=f"edit:{key}"),
            InlineKeyboardButton("🗑️", callback_data=f"del:{key}")
        ])
    buttons.append([InlineKeyboardButton("➕ Добавить турнир", callback_data="add")])
    await update.message.reply_text("🔧 Админ‑панель:", reply_markup=InlineKeyboardMarkup(buttons))

# === Обработка inline ===
# состояния 100..199 — редактирование, 200..299 — добавление
async def admin_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("edit:"):
        key = data.split(":",1)[1]
        context.user_data["edit_key"] = key
        await query.message.reply_text("Введите новое название:")
        return 100
    if data.startswith("del:"):
        key = data.split(":",1)[1]
        rows = read_csv(TOURNAMENTS_FILE)
        rows = [r for r in rows if not (r and r[0]==key)]
        write_csv(TOURNAMENTS_FILE, rows)
        await query.message.reply_text("🗑 Турнир удалён.")
        return ConversationHandler.END
    if data=="add":
        await query.message.reply_text("Введите ключ нового турнира (латиницей):")
        return 200
    return ConversationHandler.END

async def edit_name(update, context):
    key = context.user_data["edit_key"]
    new = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0]==key:
            r[1]=new
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Название обновлено. Теперь введите новую дату:")
    return 101

async def edit_date(update, context):
    key = context.user_data["edit_key"]
    new = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0]==key:
            r[2]=new
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Дата обновлена. Теперь введите новые правила:")
    return 102

async def edit_rules(update, context):
    key = context.user_data["edit_key"]
    new = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    for r in rows:
        if r and r[0]==key:
            r[3]=new
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Правила обновлены.", reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def add_key(update, context):
    context.user_data["new_key"] = update.message.text.strip()
    await update.message.reply_text("Введите название турнира:")
    return 201

async def add_name(update, context):
    context.user_data["new_name"] = update.message.text.strip()
    await update.message.reply_text("Введите дату турнира:")
    return 202

async def add_date(update, context):
    context.user_data["new_date"] = update.message.text.strip()
    await update.message.reply_text("Введите правила турнира:")
    return 203

async def add_rules(update, context):
    key = context.user_data["new_key"]
    name = context.user_data["new_name"]
    date = context.user_data["new_date"]
    rules = update.message.text.strip()
    rows = read_csv(TOURNAMENTS_FILE)
    rows.append([key,name,date,rules])
    write_csv(TOURNAMENTS_FILE, rows)
    await update.message.reply_text("✅ Турнир добавлен.", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# === Удаление участника ===
async def del_user_cmd(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только админ.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /delete USER_ID")
        return
    uid = context.args[0]
    rows = read_csv(PARTICIPANTS_FILE)
    rows = [r for r in rows if r and r[0]!=uid]
    write_csv(PARTICIPANTS_FILE, rows)
    await update.message.reply_text("✅ Участник удалён.")

# === Сборка и запуск ===
def main():
    init_files()
    app = Application.builder().token(TOKEN).build()

    # Регистрация conv
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
    app.add_handler(MessageHandler(filters.Regex("^⚙️ Админ-панель$"), admin_panel))
    app.add_handler(admin_conv)
    app.add_handler(CommandHandler("delete", del_user_cmd))

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
