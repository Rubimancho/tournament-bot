import os
import csv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)

# === 🔐 Переменные окружения ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не установлена")

ADMIN_ID = os.getenv("ADMIN_ID")
if not ADMIN_ID:
    raise ValueError("❌ Переменная окружения ADMIN_ID не установлена")
ADMIN_ID = int(ADMIN_ID)

# === Этапы регистрации и редактирования ===
NICK, ROLE, RANK, OP_GG, DISCORD = range(5)

# === Хранение команд ===
teams = {'A': [], 'B': []}

# === Файлы ===
PARTICIPANTS_FILE = "participants.csv"
TOURNAMENTS_FILE = "tournaments.csv"

# === Главное меню ===
main_menu_keyboard = [
    ["📝 Зарегистрироваться"],
    ["🏆 Наши турниры", "👥 Список участников"],
    ["📅 Дата проведения", "⚔️ Команды"]
]
reply_menu = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

# === Меню турниров ===
tournaments_menu = [
    ["🏆 Битва регионов"],
    ["🎲 Голландский рандом"],
    ["💥 Грандиозная тусовка"],
    ["⬅️ Назад"]
]
tournaments_markup = ReplyKeyboardMarkup(tournaments_menu, resize_keyboard=True)

# === Создание файлов при старте ===
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

# === Старт ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🎮 Добро пожаловать!\n\nВыбери действие:", reply_markup=reply_menu)

# === Проверка, зарегистрирован ли пользователь ===
def is_registered(user_id):
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] == str(user_id):
                    return True
        return False
    except FileNotFoundError:
        return False

# === Редактирование профиля ===
async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Режим редактирования профиля\nВведите новый никнейм:")
    return NICK

# === Начать регистрацию или редактирование ===
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_registered(user_id):
        keyboard = [
            ["📝 Редактировать профиль"],
            ["❌ Отмена"]
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "✅ Вы уже зарегистрированы.\n\n"
            "Хотите обновить данные?",
            reply_markup=markup
        )
        return ROLE
    else:
        context.user_data['roles'] = []
        await update.message.reply_text("Введите ваш никнейм в игре:", reply_markup=None)
        return NICK

# === Обработка выбора после регистрации ===
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "📝 Редактировать профиль":
        return await edit_profile(update, context)
    else:
        await update.message.reply_text("Хорошо, оставляем как есть.", reply_markup=reply_menu)
        return ConversationHandler.END

# === Получение никнейма ===
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

# === Получение ролей — ✅ ИСПРАВЛЕНО НАВСЕГДА ===
async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # ✅ Полностью правильная строка
    if 'roles' not in context.user_
        context.user_data['roles'] = []

    if text == "✅ Готово":
        if not context.user_data['roles']:
            await update.message.reply_text("⚠️ Выбери хотя бы одну роль.")
            return ROLE

        # Ранги на английском
        rank_keyboard = [
            ["🥉 Bronze", "🥈 Silver"],
            ["🥇 Gold", "💎 Platinum"],
            ["🟩 Emerald", "🔷 Diamond"],
            ["⭐ Master", "👑 Grandmaster", "🏆 Challenger"]
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

# === Получение ранга ===
async def get_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    rank = raw_text.split(' ', 1)[-1]
    context.user_data['rank'] = rank
    await update.message.reply_text("Ссылка на ваш профиль Op.gg:")
    return OP_GG

# === Получение Op.gg ===
async def get_opgg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['opgg'] = update.message.text
    await update.message.reply_text("Ваш Discord (только ник, без #):")
    return DISCORD

# === Получение Discord и сохранение ===
async def get_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    discord_nick = update.message.text.strip().split('#')[0]
    context.user_data['discord'] = discord_nick

    nick = context.user_data['nick']
    roles = ", ".join(context.user_data['roles'])
    rank = context.user_data['rank']
    opgg = context.user_data['opgg']
    user_id = update.effective_user.id
    time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Обновление профиля
    rows = []
    user_found = False
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 0 and row[0] == str(user_id):
                    user_found = True
                else:
                    rows.append(row)
    except FileNotFoundError:
        pass

    rows.append([user_id, nick, roles, rank, opgg, discord_nick, time])

    with open(PARTICIPANTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])
        writer.writerows(rows)

    action = "обновлен" if user_found else "зарегистрирован"
    await update.message.reply_text(
        f"🎉 Отлично, {nick}! Ваш профиль {action}.\n"
        "Спасибо!",
        reply_markup=reply_menu
    )
    return ConversationHandler.END

# === Правила турниров ===
async def rules_regions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏆 БИТВА РЕГИОНОВ\n\n"
        "1. <b>Основные принципы</b>\n"
        "• Формат: Best of Five (Bo5) — победа за первой командой, выигравшей 3 игры.\n"
        "• Команды: 2 по 5 человек.\n"
        "• Каждая игра — с чемпионами из одного региона.\n"
        "• Баны отсутствуют.\n"
        "• Один и тот же регион нельзя выбирать дважды.\n\n"
        
        "2. <b>Выбор чемпионов</b>\n"
        "• Только чемпионы из выбранного региона.\n"
        "• Пример: Демация → только демасийцы.\n\n"
        
        "3. <b>Порядок выбора региона</b>\n"
        "• Жеребьёвка определяет, кто выбирает первым.\n"
        "• Право выбора чередуется.\n\n"
        
        "4. <b>Спорные ситуации</b>\n"
        "• Решают организаторы.\n\n"
        
        "💡 Совет: Подготовьте чемпионов из разных регионов!",
        parse_mode="HTML",
        reply_markup=tournaments_markup
    )

async def rules_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 ГОЛЛАНДСКИЙ РАНДОМ\n\n"
        "1. <b>Общие принципы</b>\n"
        "• Формат: 5v5, Bo5 (до 3 побед).\n"
        "• Команды сбалансированы по MMR.\n"
        "• Цель: универсальность и веселье.\n\n"
        
        "2. <b>Система смещения ролей</b>\n"
        "• После каждой игры: Топ → Джангл → Мид → ADC → Саппорт → Топ...\n\n"
        
        "3. <b>Рандомизация чемпионов</b>\n"
        "• Random Draft — случайный выбор.\n"
        "• Баны отсутствуют.\n\n"
        
        "4. <b>Замены</b>\n"
        "• Только при форс-мажоре.\n\n"
        
        "5. <b>Споры</b>\n"
        "• Решают организаторы.\n\n"
        
        "💡 Этот турнир — про универсальность и веселье!",
        parse_mode="HTML",
        reply_markup=tournaments_markup
    )

async def rules_brawl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💥 ГРАНДИОЗНАЯ ПОБОИЩНАЯ ТУСОВКА\n\n"
        "1. <b>Формат</b>\n"
        "• Best of Five (Bo5), победа — в 3 играх.\n"
        "• Команды: 2 по 5 человек.\n\n"
        
        "2. <b>Драфт и баны</b>\n"
        "• Каждая команда банит по 5 чемпионов (всего 10).\n"
        "• Забаненные чемпионы нельзя использовать в будущем.\n\n"
        
        "3. <b>Формат матчей</b>\n"
        "• Карта: Summoner's Rift.\n"
        "• Сторона меняется после каждой игры.\n"
        "• Перерыв: 5 минут.\n\n"
        
        "4. <b>Споры</b>\n"
        "• Решают организаторы. Решение окончательно.\n\n"
        
        "🔥 Готовься к настоящей битве!",
        parse_mode="HTML",
        reply_markup=tournaments_markup
    )

# === Кнопка "Наши турниры" ===
async def show_tournaments_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 <b>Наши турниры</b>:\n\n"
        "Выбери, чтобы посмотреть правила и формат.",
        reply_markup=tournaments_markup,
        parse_mode="HTML"
    )

# === Список участников ===
async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        if len(rows) <= 1:
            await update.message.reply_text("Пока никто не зарегистрирован.", reply_markup=reply_menu)
            return
        message = f"📋 <b>Зарегистрировано: {len(rows) - 1}</b>:\n\n"
        for i, row in enumerate(rows[1:], start=1):
            if len(row) < 7: continue
            nick = row[1].strip('"')
            roles = row[2].strip('"')
            rank = row[3].strip('"')
            opgg = row[4].strip('"')
            discord = row[5].strip('"')
            url = opgg if opgg.startswith('http') else f"https://op.gg/summoners/ {opgg.replace(' ', '%20')}"
            message += (
                f"{i}. 🔹 <b>{nick}</b>\n"
                f"   • Роли: {roles}\n"
                f"   • Ранг: {rank}\n"
                f'   • <a href="{url}">🎮 Op.gg</a>\n'
                f"   • 💬 Discord: <code>{discord}</code>\n\n"
            )
        await update.message.reply_html(message, disable_web_page_preview=True, reply_markup=reply_menu)
    except FileNotFoundError:
        await update.message.reply_text("Файл участников не найден.", reply_markup=reply_menu)

# === Дата проведения ===
async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(TOURNAMENTS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if not lines or len(lines) < 2:
            await update.message.reply_text("📅 Пока нет запланированных турниров.", reply_markup=reply_menu)
            return
        message = "<b>🗓 Даты турниров:</b>\n\n"
        for line in lines[1:]:
            parts = line.strip().split(',', 1)
            if len(parts) == 2:
                name = parts[0].strip().strip('"')
                date = parts[1].strip().strip('"')
                message += f"🔸 <b>{name}</b>: {date}\n"
        await update.message.reply_html(message, reply_markup=reply_menu)
    except FileNotFoundError:
        await update.message.reply_text("❌ Файл tournaments.csv не найден.", reply_markup=reply_menu)

# === /setdate — добавить/обновить турнир ===
async def setdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет прав.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("UsageId: /setdate Название Дата\nПример: /setdate Final 30.07.2025_18:00")
        return
    title = context.args[0].replace("_", " ")
    date = " ".join(context.args[1:]).replace("_", " ")
    tournaments = []
    try:
        with open(TOURNAMENTS_FILE, 'r', encoding='utf-8') as f:
            tournaments = [row for row in csv.reader(f) if len(row) >= 2]
        if tournaments and tournaments[0] == ["Название", "Дата"]:
            tournaments = tournaments[1:]
    except FileNotFoundError:
        pass
    updated = False
    for row in tournaments:
        if row[0].lower() == title.lower():
            row[1] = date
            updated = True
    if not updated:
        tournaments.append([title, date])
    with open(TOURNAMENTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Название", "Дата"])
        writer.writerows(tournaments)
    await update.message.reply_text(f"✅ <b>{title}</b>: {date}", parse_mode="HTML", reply_markup=reply_menu)

# === /clear — очистить всех участников ===
async def clear_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только организатор.")
        return
    with open(PARTICIPANTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["User ID", "Никнейм", "Роли", "Ранг", "Op.gg", "Discord", "Время"])
    await update.message.reply_text("✅ Список участников очищен.", reply_markup=reply_menu)

# === /delete ID — удалить одного участника ===
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только организатор.")
        return
    if not context.args:
        await update.message.reply_text("UsageId: /delete 123456789")
        return
    target_id = context.args[0]
    rows = []
    deleted = False
    try:
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 0 and row[0] == target_id:
                    deleted = True
                else:
                    rows.append(row)
        if deleted:
            with open(PARTICIPANTS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            await update.message.reply_text(f"✅ Участник с ID {target_id} удалён.")
        else:
            await update.message.reply_text("❌ Участник не найден.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

# === Драфт команд ===
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
        await update.message.reply_text("❌ Только организатор.")
        return
    participants = await get_participants_list()
    if not participants:
        await update.message.reply_text("Пока нет участников.")
        return
    teams['A'].clear()
    teams['B'].clear()
    keyboard = [
        [InlineKeyboardButton("A", callback_data=f"team_a:{p['id']}:{p['nick']}"),
         InlineKeyboardButton("B", callback_data=f"team_b:{p['id']}:{p['nick']}")]
        for p in participants
    ]
    await update.message.reply_text(
        "📋 Выбери команду для каждого игрока:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":", 2)
    if len(data) != 3: return
    team_key, user_id, nick = data
    team_name = 'A' if 'a' in team_key else 'B'
    if nick in teams['A'] or nick in teams['B']:
        await query.edit_message_text(text=f"⚠️ {nick} уже в команде!")
        return
    teams[team_name].append(nick)
    await query.edit_message_text(text=f"✅ {nick} в Team {team_name}")

async def show_teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_a = "\n".join([f"• {p}" for p in teams['A']]) if teams['A'] else "Пусто"
    msg_b = "\n".join([f"• {p}" for p in teams['B']]) if teams['B'] else "Пусто"
    await update.message.reply_text(
        f"<b>📋 Состав команд:</b>\n\n<b>Team A</b>:\n{msg_a}\n\n<b>Team B</b>:\n{msg_b}",
        parse_mode="HTML"
    )

# === Запуск бота ===
def main():
    init_files()
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^(📝 Зарегистрироваться|📝 Редактировать профиль)$"), register_start)],
        states={
            NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nick)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice)],
            RANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rank)],
            OP_GG: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_opgg)],
            DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_discord)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🏆 Наши турниры$"), show_tournaments_menu))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🏆 Битва регионов$"), rules_regions))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🎲 Голландский рандом$"), rules_random))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💥 Грандиозная тусовка$"), rules_brawl))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^⬅️ Назад$"), start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^👥 Список участников$"), show_participants))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📅 Дата проведения$"), show_dates))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^⚔️ Команды$"), show_teams))
    app.add_handler(CommandHandler("setdate", setdate))
    app.add_handler(CommandHandler("clear", clear_participants))
    app.add_handler(CommandHandler("delete", delete_user))
    app.add_handler(CommandHandler("draft", draft_teams))
    app.add_handler(CommandHandler("teams", show_teams))
    app.add_handler(CallbackQueryHandler(button_click))

    print("✅ Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
