import os
import csv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)

# === Настройки ===
TOKEN = "8073753782:AAFEz9paFiPit-CAu6kRNabhppGe9nSFF9o"  # ← Замени на свой токен
ADMIN_ID = 1613707243  # ← Замени на свой Telegram ID
PARTICIPANTS_FILE = "participants.csv"
TOURNAMENTS_FILE = "tournaments.csv"

# === Этапы регистрации ===
NICK, ROLE, RANK, OP_GG, DISCORD = range(5)

# === Хранение команд для драфта ===
teams = {'A': [], 'B': []}

# === Главное меню ===
main_menu_keyboard = [
    ["📝 Зарегистрироваться"],
    ["🏆 Битва регионов", "🎲 Голландский рандом"],
    ["💥 Грандиозная тусовка", "👥 Список участников"],
    ["📅 Дата проведения", "⚔️ Команды"]  # ← Кнопка "Команды" добавлена
]
reply_menu = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

# === Создание файлов, если их нет ===
def init_files():
    if not os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])

    if not os.path.exists(TOURNAMENTS_FILE):
        with open(TOURNAMENTS_FILE, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows([
                ["Битва регионов", "26 июля 2025, 18:00"],
                ["Голландский рандом", "27 июля 2025, 18:00"],
                ["Грандиозная тусовка", "28 июля 2025, 18:00"]
            ])

# === Правила турниров (твои) ===
RULES_REGIONS = """
🏆 БИТВА РЕГИОНОВ

1. Формат: Best of Five (Bo5) — победа за первой командой, выигравшей 3 игры.
2. Команды: 2 команды по 5 человек.
3. Выбор региона:
   - Перед каждой игрой команды выбирают регион (например, Демация, Ноксус).
   - Чемпионы должны быть из выбранного региона.
   - Один регион нельзя использовать дважды.
4. Баны: отсутствуют.
5. Жеребьёвка определяет, кто выбирает первым.
6. Спорные вопросы решают организаторы.

💡 Совет: Подготовьте чемпионов из разных регионов!
"""

RULES_RANDOM = """
🎲 ГОЛЛАНДСКИЙ РАНДОМ

1. Формат: 5v5, Bo5 (до 3 побед).
2. Команды формируются по MMR для баланса.
3. Система смещения ролей:
   - После каждой игры игроки переходят на следующую позицию:
     Топ → Джангл → Мид → ADC → Саппорт → Топ...
4. Выбор чемпиона — случайный (Random Draft).
5. Баны не используются.
6. Замены — только при форс-мажоре.
7. Все споры решают организаторы.

💡 Этот турнир — про универсальность и веселье!
"""

RULES_BRAWL = """
💥 ГРАНДИОЗНАЯ ПОБОИЩНАЯ ТУСОВКА

1. Формат: Best of Five (Bo5), победа — в 3 играх.
2. Команды: 2 по 5 человек.
3. Драфт:
   - Каждая команда банит по 5 чемпионов (всего 10).
   - Забаненных чемпионов нельзя выбирать в будущих матчах.
4. Карта: Summoner's Rift.
5. Сторона меняется после каждой игры.
6. Перерыв между играми: 5 минут.
7. Все споры решают организаторы.

🔥 Готовься к настоящей битве!
"""

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🎮 Добро пожаловать!\n\nВыбери действие:", reply_markup=reply_menu)

# === Регистрация ===
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['roles'] = []
    await update.message.reply_text("Введите ваш никнейм в игре:", reply_markup=None)
    return NICK

async def get_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nick'] = update.message.text

    role_keyboard = [
        ["🛡️ Топ", "🌲 Джангл"],
        ["🌀 Мид", "🏹 ADC"],
        ["🧙 Саппорт"],
        ["✅ Готово"]
    ]
    markup = ReplyKeyboardMarkup(role_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Выбери все роли, на которых ты играешь.\n"
        "Можно несколько. Когда закончишь — нажми «✅ Готово».",
        reply_markup=markup
    )
    return ROLE

async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "✅ Готово":
        if not context.user_data['roles']:
            await update.message.reply_text("⚠️ Выбери хотя бы одну роль.")
            return ROLE

        rank_keyboard = [
            ["⚫ Бронза", "⚪ Серебро"],
            ["🟡 Золото", "🔵 Платина"],
            ["🟣 Изумруд", "🔴 Диамант"],
            ["⚡ Мастер", "👑 Грандмастер", "🏆 Чемпион"]
        ]
        markup = ReplyKeyboardMarkup(rank_keyboard, resize_keyboard=True, one_time_keyboard=True)
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
    raw_text = update.message.text
    rank = raw_text.split(' ', 1)[-1]
    context.user_data['rank'] = rank
    await update.message.reply_text("Ссылка на ваш профиль Op.gg:")
    return OP_GG

async def get_opgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['opgg'] = update.message.text
    await update.message.reply_text("Ваш Discord (только ник, без #):")
    return DISCORD

async def get_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    discord_nick = update.message.text.strip().split('#')[0]
    context.user_data['discord'] = discord_nick

    nick = context.user_data['nick']
    roles = ", ".join(context.user_data['roles'])
    rank = context.user_data['rank']
    opgg = context.user_data['opgg']
    user_id = update.effective_user.id
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(PARTICIPANTS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([user_id, nick, roles, rank, opgg, discord_nick, time])

    await update.message.reply_text(
        f"🎉 Отлично, {nick}! Вы успешно зарегистрированы.\n"
        "Ждём вас на турнире!",
        reply_markup=reply_menu
    )
    return ConversationHandler.END

# === Правила турниров ===
async def rules_regions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_REGIONS, reply_markup=reply_menu)

async def rules_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_RANDOM, reply_markup=reply_menu)

async def rules_brawl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_BRAWL, reply_markup=reply_menu)

# === Список участников (полный и красивый) ===
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
            user_id = row[0].strip('"')
            nick = row[1].strip('"')
            roles = row[2].strip('"')
            rank = row[3].strip('"')
            opgg = row[4].strip('"')
            discord = row[5].strip('"')
            time = row[6].strip('"')

            opgg_url = opgg if opgg.startswith('http') else f"https://op.gg/summoners/ {opgg.replace(' ', '%20')}"
            tg_link = f"tg://user?id={user_id}"

            message += (
                f"{i}. 🔹 <b><a href='{tg_link}'>{nick}</a></b>\n"
                f"   • Роли: {roles}\n"
                f"   • Ранг: {rank}\n"
                f'   • <a href="{opgg_url}">🎮 Op.gg</a>\n'
                f"   • 💬 Discord: <code>{discord}</code>\n"
                f"   • ⏰ Зарегистрирован: {time}\n\n"
            )
        
        await update.message.reply_html(message, disable_web_page_preview=True, reply_markup=reply_menu)
    
    except FileNotFoundError:
        await update.message.reply_text("Файл участников не найден.", reply_markup=reply_menu)

# === Дата проведения ===
def read_tournaments():
    try:
        with open(TOURNAMENTS_FILE, "r", encoding="utf-8") as f:
            return [row for row in csv.reader(f) if len(row) >= 2]
    except FileNotFoundError:
        return []

async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tournaments = read_tournaments()
    if not tournaments:
        await update.message.reply_text("⏳ Даты пока не установлены.", reply_markup=reply_menu)
        return

    text = "<b>🗓 Даты турниров:</b>\n\n"
    for name, date in tournaments:
        text += f"🔸 <b>{name}</b>: {date}\n"
    await update.message.reply_html(text, reply_markup=reply_menu)

# === /setdate ===
async def setdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет прав.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Используй: /setdate Название_турнира Дата_и_время\n"
                                        "Пример: /setdate Финал 30.07.2025_18:00")
        return

    title = args[0].replace("_", " ")
    date = " ".join(args[1:]).replace("_", " ")

    tournaments = read_tournaments()
    updated = False
    for row in tournaments:
        if row[0].lower() == title.lower():
            row[1] = date
            updated = True
            break
    if not updated:
        tournaments.append([title, date])

    with open(TOURNAMENTS_FILE, "w", newline='', encoding="utf-8") as f:
        csv.writer(f).writerows(tournaments)
    await update.message.reply_text(f"✅ Обновлено:\n<b>{title}</b>: {date}", parse_mode="HTML")

# === /deletedate ===
async def deletedate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет прав.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Используй: /deletedate Название_турнира\nПример: /deletedate Финал")
        return

    title = " ".join(args).replace("_", " ").strip().lower()
    tournaments = read_tournaments()
    new_list = [row for row in tournaments if row[0].lower() != title]

    if len(new_list) == len(tournaments):
        await update.message.reply_text("❌ Турнир не найден.")
        return

    with open(TOURNAMENTS_FILE, "w", newline='', encoding="utf-8") as f:
        csv.writer(f).writerows(new_list)
    await update.message.reply_text(f"🗑 Турнир <b>{title}</b> удалён.", parse_mode="HTML")

# === 🧩 ДРАФТ КОМАНД ===
async def get_participants_list():
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        return [{"id": row[0], "nick": row[1].strip('"')} for row in rows[1:] if len(row) > 1]
    except FileNotFoundError:
        return []

async def draft_teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только организатор может использовать драфт.")
        return

    participants = await get_participants_list()
    if not participants:
        await update.message.reply_text("Пока нет участников для драфта.")
        return

    teams['A'].clear()
    teams['B'].clear()

    keyboard = [
        [InlineKeyboardButton("A", callback_data=f"team_a:{p['id']}:{p['nick']}"),
         InlineKeyboardButton("B", callback_data=f"team_b:{p['id']}:{p['nick']}")]
        for p in participants
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "<b>📋 Режим драфта активирован!</b>\n\n"
        "Нажмите на кнопку A или B, чтобы добавить игрока в команду.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split(":", 2)
    if len(data) != 3:
        return

    team_key, user_id, nick = data
    team_name = 'A' if 'a' in team_key else 'B'

    if nick in teams['A'] or nick in teams['B']:
        await query.edit_message_text(text=f"⚠️ {nick} уже в команде!")
        return

    teams[team_name].append(nick)
    await query.edit_message_text(text=f"✅ {nick} добавлен в Team {team_name}")

    # ✅ Показываем обновлённый состав после каждого добавления
    msg_a = "\n".join([f"• {p}" for p in teams['A']]) if teams['A'] else "Пусто"
    msg_b = "\n".join([f"• {p}" for p in teams['B']]) if teams['B'] else "Пусто"

    await query.message.reply_text(
        "<b>📋 Текущий состав команд:</b>\n\n"
        "<b>Team A</b>:\n" + msg_a + "\n\n"
        "<b>Team B</b>:\n" + msg_b,
        parse_mode="HTML"
    )

# === ⚔️ Кнопка "Команды" ===
async def show_teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_a = "\n".join([f"• {p}" for p in teams['A']]) if teams['A'] else "Пока пусто"
    msg_b = "\n".join([f"• {p}" for p in teams['B']]) if teams['B'] else "Пока пусто"

    await update.message.reply_text(
        "<b>📋 Состав команд:</b>\n\n"
        "<b>🔥 Team A</b>:\n" + msg_a + "\n\n"
        "<b>🧊 Team B</b>:\n" + msg_b,
        parse_mode="HTML"
    )

# === Запуск бота ===
def main():
    init_files()
    app = Application.builder().token(TOKEN).build()

    # Диалог регистрации
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^📝 Зарегистрироваться$"), register_start)],
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
    app.add_handler(CommandHandler("setdate", setdate))
    app.add_handler(CommandHandler("deletedate", deletedate))
    app.add_handler(CommandHandler("draft", draft_teams))
    app.add_handler(CommandHandler("teams", show_teams))
    app.add_handler(CallbackQueryHandler(button_click))

    # Обычные сообщения
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📅 Дата проведения$"), show_dates))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🏆 Битва регионов$"), rules_regions))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🎲 Голландский рандом$"), rules_random))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💥 Грандиозная тусовка$"), rules_brawl))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^👥 Список участников$"), show_participants))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^⚔️ Команды$"), show_teams))

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()