import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, MessageHandler, filters,
    CommandHandler, CallbackQueryHandler, ContextTypes
)

BOT_TOKEN = "8201973948:AAFLCmxJ31YQBKPAMfN6fAYMYojV2ZpOLhc"
PRIVATE_GROUP_CHAT_ID = -2533147454
ADMIN_GROUP_CHAT_ID = -2856639895

uploaded_files = []  # Stores (file_id, file_name)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("Upload File", callback_data="upload")],
        [InlineKeyboardButton("Request File", callback_data="request")]
    ]
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(buttons))


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.photo[-1] or update.message.video
    file_name = update.message.document.file_name if update.message.document else "Photo/Video"
    file_id = file.file_id
    uploaded_files.append((file_id, file_name))
    await context.bot.send_message(PRIVATE_GROUP_CHAT_ID, f"New file uploaded:\n{file_name}")
    await update.message.reply_text("File received!")


async def show_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(context.user_data.get("page", 0))
    files_per_page = 20
    start = page * files_per_page
    end = start + files_per_page
    buttons = [
        [InlineKeyboardButton(f"{name}", callback_data=f"get_{file_id}")]
        for file_id, name in uploaded_files[start:end]
    ]
    if end < len(uploaded_files):
        buttons.append([InlineKeyboardButton("More Files", callback_data="more_files")])
    await query.edit_message_text("Choose a file:", reply_markup=InlineKeyboardMarkup(buttons))


async def send_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_id = query.data.split("_", 1)[1]
    await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id)


async def more_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["page"] = context.user_data.get("page", 0) + 1
    await show_files(update, context)


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_GROUP_CHAT_ID:
        return
    if context.args:
        msg = " ".join(context.args)
        await context.bot.send_message(PRIVATE_GROUP_CHAT_ID, f"📢 Broadcast:\n{msg}")
        await update.message.reply_text("Broadcast sent.")
    else:
        await update.message.reply_text("Usage: /broadcast <message>")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "upload":
        await query.answer("Send a file now!")
    elif query.data == "request":
        context.user_data["page"] = 0
        await show_files(update, context)
    elif query.data == "more_files":
        await more_files(update, context)
    elif query.data.startswith("get_"):
        await send_file(update, context)


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO, handle_file))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    await app.run_polling()


if __name__ == "__main__":
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
                                 
