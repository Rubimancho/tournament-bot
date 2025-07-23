import csv
import os
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, ContextTypes
)

# === 🔑 ВСТАВЬ СЮДА СВОЙ ТОКЕН И ADMIN ID ===
TOKEN = "ТВОЙ_ТОКЕН"
ADMIN_ID = 123456789  # Замени на свой Telegram ID

# === 📁 CSV-файл ===
CSV_FILE = "participants.csv"

# === 📋 Турниры: название, дата, правила ===
tournaments = {
    "regions": {
        "name": "Битва регионов",
        "date": "26 июля 2025, 18:00",
        "rules": "🏆 БИТВА РЕГИОНОВ\n1. Bo5. Команды: 5x5. Без банов."
    },
    "random": {
        "name": "Голландский рандом",
        "date": "27 июля 2025, 18:00",
        "rules": "🎲 ГОЛЛАНДСКИЙ РАНДОМ\n1. Bo5. Рандом по MMR. Позиции меняются."
    },
    "brawl": {
        "name": "Грандиозная тусовка",
        "date": "28 июля 2025, 18:00",
        "rules": "💥 ГРАНДИОЗНАЯ ТУСОВКА\n1. Bo5. 5 банов на команду. Rift."
    }
}

# === 📝 Регистрация ===
NICK, ROLE, RANK, OP_GG, DISCORD = range(5)

main_keyboard = ReplyKeyboardMarkup([
    ["📝 Зарегистрироваться"],
    ["📋 Список участников"],
    ["📅 Даты турниров", "📜 Правила турниров"]
], resize_keyboard=True)

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добро пожаловать! Выбери действие:", reply_markup=main_keyboard)

# === Регистрация ===
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Введите свой никнейм:")
    return NICK

async def get_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nick"] = update.message.text
    await update.message.reply_text("Выберите роль (топ, мид, саппорт и т.п.):")
    return ROLE

async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["role"] = update.message.text
    await update.message.reply_text("Ваш ранг:")
    return RANK

async def get_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rank"] = update.message.text
    await update.message.reply_text("Ссылка на профиль Op.gg:")
    return OP_GG

async def get_opgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["opgg"] = update.message.text
    await update.message.reply_text("Ваш Discord:")
    return DISCORD

async def get_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["discord"] = update.message.text
    user = context.user_data
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(CSV_FILE, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([update.effective_user.id, user["nick"], user["role"], user["rank"], user["opgg"], user["discord"], time])

    await update.message.reply_text("✅ Вы зарегистрированы!", reply_markup=main_keyboard)
    return ConversationHandler.END

# === Отмена регистрации ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Регистрация отменена.", reply_markup=main_keyboard)
    return ConversationHandler.END

# === Просмотр участников ===
async def participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(CSV_FILE):
        await update.message.reply_text("Нет зарегистрированных участников.")
        return

    with open(CSV_FILE, "r", encoding='utf-8') as f:
        reader = list(csv.reader(f))

    if len(reader) <= 0:
        await update.message.reply_text("Список пуст.")
        return

    msg = f"📋 Участников: {len(reader)}\n\n"
    for i, row in enumerate(reader, 1):
        msg += f"{i}. {row[1]} ({row[2]}) | {row[3]}\n"

    await update.message.reply_text(msg)

# === Правила ===
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = ""
    for key, t in tournaments.items():
        msg += f"<b>{t['name']}</b>\n{t['rules']}\n\n"
    await update.message.reply_html(msg)

# === Даты турниров ===
async def dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📅 <b>Даты турниров</b>:\n\n"
    for t in tournaments.values():
        msg += f"🔹 <b>{t['name']}</b>: {t['date']}\n"
    await update.message.reply_html(msg)

# === Админ-панель ===
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ только для администратора.")
        return

    buttons = [
        [InlineKeyboardButton(t["name"], callback_data=f"edit:{key}")]
        for key, t in tournaments.items()
    ] + [[InlineKeyboardButton("➕ Добавить турнир", callback_data="add")]]
    await update.message.reply_text("🔧 Админ-панель", reply_markup=InlineKeyboardMarkup(buttons))

# === Обработка inline-кнопок из админ-панели ===
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("edit:"):
        key = data.split(":")[1]
        context.user_data["edit_tournament"] = key
        await query.message.reply_text("Введите новое название турнира:")
        return 100

    elif data == "add":
        await query.message.reply_text("Введите ключ нового турнира:")
        return 200

    return ConversationHandler.END

# === Обработка нового названия турнира ===
async def update_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_tournament"]
    tournaments[key]["name"] = update.message.text
    await update.message.reply_text(f"✅ Название турнира обновлено: {update.message.text}")
    await update.message.reply_text("Теперь введите новую дату:")
    return 101

async def update_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_tournament"]
    tournaments[key]["date"] = update.message.text
    await update.message.reply_text(f"✅ Дата обновлена: {update.message.text}")
    await update.message.reply_text("Теперь введите новые правила:")
    return 102

async def update_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["edit_tournament"]
    tournaments[key]["rules"] = update.message.text
    await update.message.reply_text("✅ Правила обновлены.")
    return ConversationHandler.END

# === Добавление нового турнира ===
async def add_tournament_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    if key in tournaments:
        await update.message.reply_text("⚠️ Такой ключ уже есть.")
        return ConversationHandler.END
    context.user_data["new_tournament"] = key
    await update.message.reply_text("Введите название турнира:")
    return 201

async def add_tournament_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_name"] = update.message.text
    await update.message.reply_text("Введите дату турнира:")
    return 202

async def add_tournament_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_date"] = update.message.text
    await update.message.reply_text("Введите правила:")
    return 203

async def add_tournament_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["new_tournament"]
    tournaments[key] = {
        "name": context.user_data["new_name"],
        "date": context.user_data["new_date"],
        "rules": update.message.text
    }
    await update.message.reply_text(f"✅ Турнир «{context.user_data['new_name']}» добавлен.")
    return ConversationHandler.END

# === Удаление участника по команде /delete 123456789 ===
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только админ.")
        return

    if not context.args:
        await update.message.reply_text("Формат: /delete user_id")
        return

    target_id = context.args[0]
    updated = []
    removed = False

    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] != target_id:
                    updated.append(row)
                else:
                    removed = True

        with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(updated)

    await update.message.reply_text("✅ Участник удалён." if removed else "Не найден.")

# === Запуск бота ===
def main():
    app = Application.builder().token(TOKEN).build()

    # Регистрация
    reg_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Зарегистрироваться$"), register_start)],
        states={
            NICK: [MessageHandler(filters.TEXT, get_nick)],
            ROLE: [MessageHandler(filters.TEXT, get_role)],
            RANK: [MessageHandler(filters.TEXT, get_rank)],
            OP_GG: [MessageHandler(filters.TEXT, get_opgg)],
            DISCORD: [MessageHandler(filters.TEXT, get_discord)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Админ панель
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback)],
        states={
            100: [MessageHandler(filters.TEXT, update_name)],
            101: [MessageHandler(filters.TEXT, update_date)],
            102: [MessageHandler(filters.TEXT, update_rules)],
            200: [MessageHandler(filters.TEXT, add_tournament_key)],
            201: [MessageHandler(filters.TEXT, add_tournament_name)],
            202: [MessageHandler(filters.TEXT, add_tournament_date)],
            203: [MessageHandler(filters.TEXT, add_tournament_rules)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(reg_handler)
    app.add_handler(MessageHandler(filters.Regex("^📋 Список участников$"), participants))
    app.add_handler(MessageHandler(filters.Regex("^📜 Правила турниров$"), rules))
    app.add_handler(MessageHandler(filters.Regex("^📅 Даты турниров$"), dates))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(CommandHandler("delete", delete_user))

    # Файл участников
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
            pass

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == '__main__':
    main()
