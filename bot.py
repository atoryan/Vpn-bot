#!/usr/bin/env python3
"""
Telegram бот для мониторинга VPN подписок через 3x-ui
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config
from xui_api import XUIClient

xui = XUIClient()

def is_allowed(update: Update) -> bool:
    return update.effective_user.id in config.ALLOWED_USERS

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Статистика", callback_data="list")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="getlink_menu")],
        [InlineKeyboardButton("🖥 Открыть панель", url=config.XUI_URL)],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "👋 Привет! Выбери действие:",
        reply_markup=main_keyboard()
    )

async def list_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text("⏳ Загружаю статистику...")
    clients = xui.get_clients()

    if not clients:
        await update.message.reply_text("📋 Подписок пока нет")
        return

    message = "📋 Подписки:\n\n"
    for client in clients:
        used_gb = client['allTime'] / (1024 ** 3)
        total_gb = client['total'] / (1024 ** 3) if client['total'] > 0 else 0
        traffic = f"{used_gb:.2f} ГБ" if total_gb == 0 else f"{used_gb:.2f}/{total_gb:.2f} ГБ"
        inbounds_str = ", ".join(client.get('inbounds', [])) or "—"

        message += (
            f"👤 {client['subId']}\n"
            f"📊 {traffic}\n"
            f"🌐 {inbounds_str}\n"
            f"{'✅' if client['enable'] else '❌'} {'Активна' if client['enable'] else 'Отключена'}\n\n"
        )

    await update.message.reply_text(message)

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    if not context.args:
        await update.message.reply_text("❌ Укажи имя: /getlink Vasya")
        return

    name = context.args[0]
    link = xui.get_client_link(name)
    if link:
        await update.message.reply_text(
            f"🔗 Subscription ссылка для *{name}*:\n\n`{link}`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Не удалось получить ссылку!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    query = update.callback_query
    await query.answer()

    if query.data == "list":
        clients = xui.get_clients()

        if not clients:
            await query.edit_message_text("📋 Подписок пока нет", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]]))
            return

        message = "📋 Подписки:\n\n"
        for client in clients:
            used_gb = client['allTime'] / (1024 ** 3)
            total_gb = client['total'] / (1024 ** 3) if client['total'] > 0 else 0
            traffic = f"{used_gb:.2f} ГБ" if total_gb == 0 else f"{used_gb:.2f}/{total_gb:.2f} ГБ"
            inbounds_str = ", ".join(client.get('inbounds', [])) or "—"

            message += (
                f"👤 {client['subId']}\n"
                f"📊 {traffic}\n"
                f"🌐 {inbounds_str}\n"
                f"{'✅' if client['enable'] else '❌'} {'Активна' if client['enable'] else 'Отключена'}\n\n"
            )

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "getlink_menu":
        clients = xui.get_clients()

        if not clients:
            await query.edit_message_text("📋 Подписок пока нет", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]]))
            return

        keyboard = []
        for client in clients:
            keyboard.append([InlineKeyboardButton(
                f"🔗 {client['subId']}",
                callback_data=f"getlink_{client['subId']}"
            )])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back")])

        await query.edit_message_text("Выбери подписку:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("getlink_"):
        sub_id = query.data.replace("getlink_", "")
        link = xui.get_client_link(sub_id)

        if link:
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="getlink_menu")]]
            await query.edit_message_text(
                f"🔗 Subscription ссылка для *{sub_id}*:\n\n`{link}`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ Не удалось получить ссылку!")

    elif query.data == "back":
        await query.edit_message_text("👋 Выбери действие:", reply_markup=main_keyboard())

def main():
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_subscriptions))
    app.add_handler(CommandHandler("getlink", get_link))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
