#!/usr/bin/env python3
"""
Telegram бот для управления VPN подписками через 3x-ui
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import config
from xui_api import XUIClient

# Создаём клиент для работы с 3x-ui
xui = XUIClient()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие"""
    await update.message.reply_text(
        "👋 Привет! Я бот для управления VPN подписками.\n\n"
        "Используй /help чтобы увидеть список команд."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - список команд"""
    await update.message.reply_text(
        "📋 Доступные команды:\n\n"
        "/create <имя> - Создать новую подписку\n"
        "/list - Показать все подписки\n"
        "/getlink <email> - Получить ссылку подключения\n"
        "/delete <email> - Удалить подписку\n"
        "/help - Показать это сообщение\n\n"
        "Пример: /create Vasya"
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
        # Конвертируем байты в ГБ
        used_gb = client['allTime'] / (1024 ** 3)
        total_gb = client['total'] / (1024 ** 3) if client['total'] > 0 else 0

        traffic = f"{used_gb:.2f} ГБ" if total_gb == 0 else f"{used_gb:.2f}/{total_gb:.2f} ГБ"

        message += (
            f"👤 {client['subId']}\n"
            f"📧 {client['email']}\n"
            f"📊 Трафик: {traffic}\n"
            f"{'✅' if client['enable'] else '❌'} {'Активна' if client['enable'] else 'Отключена'}\n\n"
        )

    await update.message.reply_text(message)

async def delete_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /delete - удалить подписку"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи email клиента!\n"
            "Пример: /delete abc12345"
        )
        return

    email = context.args[0]
    await update.message.reply_text(f"⏳ Удаляю подписку {email}...")

    if xui.delete_client(email):
        await update.message.reply_text("✅ Подписка удалена!")
    else:
        await update.message.reply_text("❌ Ошибка удаления подписки!")

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /getlink - получить ссылку подключения"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи email клиента!\n"
            "Пример: /getlink abc12345"
        )
        return

    email = context.args[0]
    await update.message.reply_text(f"⏳ Получаю ссылку для {email}...")

    link = xui.get_client_link(email)
    if link:
        await update.message.reply_text(
            f"🔗 Ссылка для подключения:\n\n"
            f"`{link}`\n\n"
            f"Скопируй эту ссылку и добавь в v2ray клиент",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Не удалось получить ссылку!")

def main():
    """Запуск бота"""
    # Создаём приложение с прокси
    app = (Application.builder()
           .token(config.TELEGRAM_TOKEN)
           .get_updates_proxy("http://127.0.0.1:2080")
           .build())

    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("create", create_subscription))
    app.add_handler(CommandHandler("list", list_subscriptions))
    app.add_handler(CommandHandler("getlink", get_link))
    app.add_handler(CommandHandler("delete", delete_subscription))

    # Запускаем бота
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
