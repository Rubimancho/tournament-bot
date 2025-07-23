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
            writer.writerow(["Битва регионов", "26 июля 2025, 18:00"])
            writer.writerow(["Голландский рандом", "27 июля 2025, 18:00"])
            writer.writerow(["Грандиозная тусовка", "28 июля 2025, 18:00"])
        print("📁 Файл tournaments.csv создан")

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🎮 Добро пожаловать на турнир!\n\nВыбери действие:",
        reply_markup=reply_menu
    )

# === РЕГИСТРАЦИЯ ===
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# === СПИСОК УЧАСТНИКОВ ===
async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if len(rows) <= 1:
            await update.message.reply_text("Пока никто не зарегистрирован.", reply_markup=reply_menu)
            return
        
        message = f"📋 <b>Зарегистрировано: {len(rows) - 1} участник(а)</b>:\n\n"
        for i, row in enumerate(rows[1:], start=1):
            if len(row) < 7: continue
            user_id, nick, roles, rank, opgg, discord, time = row
            
            # Формируем ссылку Op.gg
            if opgg.startswith('http'):
                url = opgg
            else:
                url = f"https://op.gg/summoners/{opgg.replace(' ', '%20')}"
            
            message += (
                f"{i}. 🔹 <b>{nick}</b>\n"
                f"   • Роли: {roles}\n"
                f"   • Ранг: {rank}\n"
                f'   • <a href="{url}">🎮 Op.gg</a>\n'
                f"   • Discord: <code>{discord}</code>\n\n"
            )
        
        await update.message.reply_html(message, disable_web_page_preview=True, reply_markup=reply_menu)
    
    except FileNotFoundError:
        await update.message.reply_text("Файл участников не найден.", reply_markup=reply_menu)

# === ДАТА ПРОВЕДЕНИЯ ===
async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(TOURNAMENTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if len(rows) <= 1:
            await update.message.reply_text("📅 Пока даты не установлены.", reply_markup=reply_menu)
            return
        
        message = "<b>🗓 Даты турниров:</b>\n\n"
        for row in rows[1:]:
            if len(row) >= 2:
                name, date = row[0], row[1]
                message += f"🔸 <b>{name}</b>: {date}\n"
        
        await update.message.reply_html(message, reply_markup=reply_menu)
    
    except FileNotFoundError:
        await update.message.reply_text("Файл дат не найден.", reply_markup=reply_menu)

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

# === /setdate — УСТАНОВИТЬ ДАТУ ТУРНИРА ===
async def setdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /setdate Название_турнира Дата_и_время\n"
            "Пример: /setdate Битва_регионов 30.07.2025_18:00"
        )
        return
    
    title = context.args[0].replace('_', ' ')
    date = ' '.join(context.args[1:])
    
    # Читаем существующие турниры
    tournaments = []
    try:
        with open(TOURNAMENTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            tournaments = list(reader)
    except FileNotFoundError:
        await update.message.reply_text("❌ Файл турниров не найден.")
        return
    
    # Обновляем или добавляем
    updated = False
    for i, row in enumerate(tournaments):
        if len(row) >= 2 and row[0] == title:
            tournaments[i][1] = date
            updated = True
            break
    
    if not updated:
        tournaments.append([title, date])
    
    # Сохраняем
    with open(TOURNAMENTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(tournaments)
    
    await update.message.reply_text(f"✅ Дата обновлена:\n<b>{title}</b>: {date}", parse_mode="HTML")

# === /delete — УДАЛИТЬ УЧАСТНИКА ===
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    
    if not context.args:
        await update.message.reply_text("Укажите User ID участника для удаления.")
        return
    
    user_id_to_delete = context.args[0]
    
    # Читаем существующих участников
    participants = []
    deleted = False
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            participants = list(reader)
    except FileNotFoundError:
        await update.message.reply_text("❌ Файл участников не найден.")
        return
    
    # Удаляем
    new_participants = []
    for row in participants:
        if len(row) > 0 and str(row[0]) == user_id_to_delete:
            deleted = True
        else:
            new_participants.append(row)
    
    if not deleted:
        await update.message.reply_text("Участник с таким ID не найден.")
        return
    
    # Сохраняем изменения
    with open(PARTICIPANTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(new_participants)
    
    await update.message.reply_text(f"✅ Участник с ID {user_id_to_delete} удалён.")

# === ОСНОВНОЙ ХЭНДЛЕР ===
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
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

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text("👥 Список участников"), show_participants))
    application.add_handler(MessageHandler(filters.Text("📅 Дата проведения"), show_dates))
    application.add_handler(MessageHandler(filters.Text("📜 Правила турниров"), show_rules))
    application.add_handler(CommandHandler("setdate", setdate))
    application.add_handler(CommandHandler("delete", delete_user))

    # Запуск бота
    init_files()
    application.run_polling()

if __name__ == "__main__":
    main()
