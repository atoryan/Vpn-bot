#!/usr/bin/env python3
"""
Telegram бот для управления VPN подписками через 3x-ui
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config
from xui_api import XUIClient

# Создаём клиент для работы с 3x-ui
xui = XUIClient()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие"""
    keyboard = [
        [InlineKeyboardButton("📋 Список подписок", callback_data="list")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="getlink_menu")],
        [InlineKeyboardButton("🗑 Удалить подписку", callback_data="delete_menu")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Привет! Я бот для управления VPN подписками.\n\n"
        "Выбери действие:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - список команд"""
    await update.message.reply_text(
        "📋 Доступные команды:\n\n"
        "/create <имя> - Создать новую подписку\n"
        "/list - Показать все подписки\n"
        "/getlink <имя> - Получить ссылку подключения\n"
        "/delete <имя> - Удалить подписку\n"
        "/help - Показать это сообщение\n\n"
        "Пример: /create Vasya\n"
        "Пример: /delete Vasya"
    )

async def create_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /create - создать подписку"""
    # Проверяем что передано имя
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи имя клиента!\n"
            "Пример: /create Vasya"
        )
        return

    name = context.args[0]
    await update.message.reply_text(f"⏳ Создаю подписку для {name}...")

    # Создаём клиента через API
    result = xui.create_client(name)

    if result:
        traffic = 'Безлимит' if result['totalGB'] == 0 else f"{result['totalGB']} ГБ"
        expiry = 'Бессрочно' if result['expiryDays'] == 0 else f"{result['expiryDays']} дней"

        await update.message.reply_text(
            f"✅ Подписка создана!\n\n"
            f"👤 Имя: {result['subId']}\n"
            f"📧 Email: {result['email']}\n"
            f"📊 Трафик: {traffic}\n"
            f"⏰ Срок: {expiry}"
        )
    else:
        await update.message.reply_text("❌ Ошибка создания подписки!")

async def list_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /list - список подписок"""
    await update.message.reply_text("⏳ Загружаю список подписок...")

    clients = xui.get_clients()

    if not clients:
        await update.message.reply_text("📋 Подписок пока нет")
        return

    # Формируем красивый список
    message = "📋 Активные подписки:\n\n"
    for client in clients:
        used_gb = client['allTime'] / (1024 ** 3)
        total_gb = client['total'] / (1024 ** 3) if client['total'] > 0 else 0

        traffic = f"{used_gb:.2f} ГБ" if total_gb == 0 else f"{used_gb:.2f}/{total_gb:.2f} ГБ"
        inbounds_str = ", ".join(client.get('inbounds', [])) or "—"

        message += (
            f"👤 {client['subId']}\n"
            f"📊 Трафик: {traffic}\n"
            f"🌐 Inbound'ы: {inbounds_str}\n"
            f"{'✅' if client['enable'] else '❌'} {'Активна' if client['enable'] else 'Отключена'}\n\n"
        )

    await update.message.reply_text(message)

async def delete_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /delete - удалить подписку"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи имя клиента!\n"
            "Пример: /delete Vasya"
        )
        return

    name = context.args[0]
    await update.message.reply_text(f"⏳ Удаляю подписку {name}...")

    # Пробуем получить UUID по имени
    client_uuid = xui.get_client_uuid(name)
    if client_uuid and xui.delete_client(client_uuid):
        await update.message.reply_text("✅ Подписка удалена!")
        return

    # Пробуем по имени напрямую
    if xui.delete_client(name):
        await update.message.reply_text("✅ Подписка удалена!")
        return

    # Пробуем по email
    email = xui.get_email_by_name(name)
    if email and xui.delete_client(email):
        await update.message.reply_text("✅ Подписка удалена!")
    else:
        await update.message.reply_text("❌ Ошибка удаления подписки!")

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /getlink - получить ссылку подключения"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи имя клиента!\n"
            "Пример: /getlink Vasya"
        )
        return

    name = context.args[0]
    await update.message.reply_text(f"⏳ Получаю ссылку для {name}...")

    link = xui.get_client_link(name)
    if link:
        await update.message.reply_text(
            f"🔗 Ссылка для подключения:\n\n"
            f"`{link}`\n\n"
            f"Добавь эту ссылку как subscription в v2ray/sing-box клиент",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Не удалось получить ссылку!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    if query.data == "list":
        clients = xui.get_clients()

        if not clients:
            await query.edit_message_text("📋 Подписок пока нет")
            return

        message = "📋 Активные подписки:\n\n"
        for client in clients:
            used_gb = client['allTime'] / (1024 ** 3)
            total_gb = client['total'] / (1024 ** 3) if client['total'] > 0 else 0
            traffic = f"{used_gb:.2f} ГБ" if total_gb == 0 else f"{used_gb:.2f}/{total_gb:.2f} ГБ"
            inbounds_str = ", ".join(client.get('inbounds', [])) or "—"

            message += (
                f"👤 {client['subId']}\n"
                f"📊 Трафик: {traffic}\n"
                f"🌐 Inbound'ы: {inbounds_str}\n"
                f"{'✅' if client['enable'] else '❌'} {'Активна' if client['enable'] else 'Отключена'}\n\n"
            )

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "getlink_menu":
        clients = xui.get_clients()

        if not clients:
            await query.edit_message_text("📋 Подписок пока нет")
            return

        keyboard = []
        for client in clients:
            keyboard.append([InlineKeyboardButton(
                f"🔗 {client['subId']}",
                callback_data=f"getlink_{client['subId']}"
            )])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back")])

        await query.edit_message_text(
            "Выбери подписку для получения ссылки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("getlink_"):
        sub_id = query.data.replace("getlink_", "")
        link = xui.get_client_link(sub_id)

        if link:
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="getlink_menu")]]
            await query.edit_message_text(
                f"🔗 Ссылка для подключения:\n\n`{link}`\n\nДобавь как subscription в v2ray/sing-box клиент",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ Не удалось получить ссылку!")

    elif query.data == "delete_menu":
        clients = xui.get_clients()

        if not clients:
            await query.edit_message_text("📋 Подписок пока нет")
            return

        keyboard = []
        for client in clients:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {client['subId']}",
                callback_data=f"delete_{client['email']}"
            )])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back")])

        await query.edit_message_text(
            "Выбери подписку для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("delete_"):
        email = query.data.replace("delete_", "")

        # Находим имя по email для отображения
        clients = xui.get_clients()
        client_name = None
        for client in clients:
            if client['email'] == email:
                client_name = client['subId']
                break

        if xui.delete_client(email):
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back")]]
            await query.edit_message_text(
                f"✅ Подписка {client_name} удалена!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ Ошибка удаления подписки!")

    elif query.data == "help":
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back")]]
        await query.edit_message_text(
            "📋 Доступные команды:\n\n"
            "/create <имя> - Создать новую подписку\n"
            "/list - Показать все подписки\n"
            "/getlink <имя> - Получить ссылку подключения\n"
            "/delete <имя> - Удалить подписку\n"
            "/help - Показать это сообщение\n\n"
            "Пример: /create Vasya\n"
            "Пример: /delete Vasya",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("📋 Список подписок", callback_data="list")],
            [InlineKeyboardButton("🔗 Получить ссылку", callback_data="getlink_menu")],
            [InlineKeyboardButton("🗑 Удалить подписку", callback_data="delete_menu")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        await query.edit_message_text(
            "👋 Привет! Я бот для управления VPN подписками.\n\n"
            "Выбери действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def main():
    """Запуск бота"""
    # Создаём приложение
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("create", create_subscription))
    app.add_handler(CommandHandler("list", list_subscriptions))
    app.add_handler(CommandHandler("getlink", get_link))
    app.add_handler(CommandHandler("delete", delete_subscription))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Запускаем бота
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
