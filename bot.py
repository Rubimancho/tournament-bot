import os
import csv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# === 🔑 ЗАМЕНИ НА СВОЙ ТОКЕН ===
TOKEN = "ВСТАВЬ_СЮДА_ТОКЕН"  # ←←← Вставь свой токен!
# =============================

# === 👤 ЗАМЕНИ НА СВОЙ ID ===
YOUR_USER_ID = 123456789  # ←←← Замени на свой ID
# ===========================

# === Этапы регистрации ===
NICK, ROLE, RANK, OP_GG, DISCORD = range(5)

# === Главное меню ===
main_menu_keyboard = [
    ["📝 Зарегистрироваться"],
    ["👥 Список участников"]
]
reply_menu = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

# === Создание файла ===
def init_file():
    if not os.path.exists("participants.csv"):
        with open("participants.csv", "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🎮 Добро пожаловать!", reply_markup=reply_menu)

# === Регистрация ===
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['roles'] = []
    await update.message.reply_text("Введите ваш никнейм:", reply_markup=None)
    return NICK

# === Никнейм → роли ===
async def get_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nick'] = update.message.text
    kb = [
        ["🛡️ Топ", "🌲 Джангл"],
        ["🌀 Мид", "🏹 ADC"],
        ["🧙 Саппорт"],
        ["✅ Готово"]
    ]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text("Выбери роли (можно несколько):", reply_markup=markup)
    return ROLE

# === Роли — ✅ ИСПРАВЛЕНО НАВСЕГДА ===
async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # ✅ Полностью правильная строка
    if 'roles' not in context.user_
        context.user_data['roles'] = []

    if text == "✅ Готово":
        if not context.user_data['roles']:
            await update.message.reply_text("⚠️ Выбери хотя бы одну роль.")
            return ROLE
        await update.message.reply_text("Ранг:")
        return RANK

    role = text.split(' ', 1)[-1]
    if role not in context.user_data['roles']:
        context.user_data['roles'].append(role)
        await update.message.reply_text(f"➕ {role}")
    return ROLE

# === Ранг ===
async def get_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rank'] = update.message.text
    await update.message.reply_text("Op.gg:")
    return OP_GG

# === Op.gg ===
async def get_opgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['opgg'] = update.message.text
    await update.message.reply_text("Discord (ник без #):")
    return DISCORD

# === Discord + Сохранение ===
async def get_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nick = context.user_data['nick']
    roles = ", ".join(context.user_data['roles'])
    rank = context.user_data['rank']
    opgg = context.user_data['opgg']
    discord = update.message.text.strip().split('#')[0]
    user_id = update.effective_user.id
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open('participants.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([user_id, nick, roles, rank, opgg, discord, time])

    await update.message.reply_text(f"✅ {nick}, вы зарегистрированы!", reply_markup=reply_menu)
    return ConversationHandler.END

# === Список участников ===
async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open('participants.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        if len(rows) <= 1:
            await update.message.reply_text("Пока никто не зарегистрирован.", reply_markup=reply_menu)
            return
        msg = f"📋 Участников: {len(rows) - 1}\n\n"
        for i, row in enumerate(rows[1:], start=1):
            if len(row) < 7: continue
            nick = row[1].strip('"')
            roles = row[2].strip('"')
            rank = row[3].strip('"')
            opgg = row[4].strip('"')
            discord = row[5].strip('"')
            url = opgg if opgg.startswith('http') else f"https://op.gg/summoners/{opgg.replace(' ', '%20')}"
            msg += (
                f"{i}. 🔹 {nick}\n"
                f"   • Роли: {roles}\n"
                f"   • Ранг: {rank}\n"
                f'   • <a href="{url}">Op.gg</a>\n'
                f"   • Discord: {discord}\n\n"
            )
        await update.message.reply_html(msg, disable_web_page_preview=True, reply_markup=reply_menu)
    except FileNotFoundError:
        await update.message.reply_text("Файл не найден.", reply_markup=reply_menu)

# === Запуск ===
def main():
    init_file()
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex('^📝'), register_start)],
        states={
            NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nick)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
            RANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rank)],
            OP_GG: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_opgg)],
            DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_discord)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^👥'), show_participants))

    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
