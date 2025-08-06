import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputFile,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
)
import asyncio
import os

# Constants
BOT_TOKEN = "8201973948:AAG6YvqFh3jGYRoaLO0jvUBEDQdI7NxmYRI"
PRIVATE_GROUP_CHAT_ID = -2533147454
ADMIN_CHAT_ID = -2856639895
FILES_PER_PAGE = 20

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory file store
file_store = []  # List of dicts: {file_id, title}
user_upload_context = {}

# States
WAITING_FOR_FILE, WAITING_FOR_TITLE = range(2)

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("Upload File")], [KeyboardButton("Need File")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Welcome to the Fun File Share Bot!\n"
        "Use the buttons below or commands like /upload and /need_file to get started.",
        reply_markup=reply_markup,
    )

# Upload
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛑 Hey there! Before you upload, just a quick heads-up:\n"
        "This is a fun space for everyone. Please don't share any private, illegal, or inappropriate stuff.\n"
        "✅ Let’s keep it awesome for everyone!"
    )
    await update.message.reply_text("🎉 Ready to share something cool? Send me the file now!")
    return WAITING_FOR_FILE

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = update.message.document
    elif update.message.video:
        file = update.message.video
    elif update.message.photo:
        file = update.message.photo[-1]
    else:
        await update.message.reply_text("❌ Unsupported file type. Please try again.")
        return WAITING_FOR_FILE

    file_id = file.file_id
    user_upload_context[update.message.from_user.id] = file_id
    await update.message.reply_text("Nice! Now send me a catchy title for your file.")
    return WAITING_FOR_TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    title = update.message.text
    file_id = user_upload_context.get(user_id)

    if not file_id:
        await update.message.reply_text("Something went wrong. Please try /upload again.")
        return ConversationHandler.END

    file_store.append({"title": title, "file_id": file_id})
    await context.bot.forward_message(chat_id=PRIVATE_GROUP_CHAT_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
    await update.message.reply_text(f"✅ Got it! Your file, '{title}', is now ready to share with everyone!")
    return ConversationHandler.END

# Need File
async def need_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["file_offset"] = 0
    return await send_file_buttons(update, context)

async def send_file_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    offset = context.user_data.get("file_offset", 0)
    keyboard = []
    files = file_store[offset:offset + FILES_PER_PAGE]
    for i, item in enumerate(files):
        keyboard.append([InlineKeyboardButton(item["title"], callback_data=f"get_{offset + i}")])

    if offset + FILES_PER_PAGE < len(file_store):
        keyboard.append([InlineKeyboardButton("➡️ More Files", callback_data="more_files")])

    if not files:
        await update.message.reply_text("Oops! No files yet. Be the first to share one!")
        return ConversationHandler.END

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📁 Choose a file to download:", reply_markup=reply_markup)
    return ConversationHandler.END

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("get_"):
        index = int(query.data.split("_")[1])
        if index < len(file_store):
            file_id = file_store[index]["file_id"]
            title = file_store[index]["title"]
            msg = await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_id,
                caption=f"Here's your file: {title}\n⏳ This will disappear in 5 minutes!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚨 Report inappropriate file", callback_data=f"report_{index}")]
                ]),
            )
            await asyncio.sleep(300)
            await msg.delete()
    elif query.data == "more_files":
        context.user_data["file_offset"] += FILES_PER_PAGE
        await send_file_buttons(update, context)
    elif query.data.startswith("report_"):
        index = int(query.data.split("_")[1])
        title = file_store[index]["title"]
        reporter = update.effective_user.id
        await context.bot.send_message(
            ADMIN_CHAT_ID,
            f"⚠️ Report received!\nTitle: {title}\nReported by: {reporter}"
        )
        await query.edit_message_text("✅ Thanks for reporting! We'll look into it.")

# Broadcast
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    if not context.args:
        await update.message.reply_text("❗ Usage: /broadcast <message>")
        return

    message = "📢 Broadcast:\n" + " ".join(context.args)
    for user in set([u.message.from_user.id for u in context.application.chat_data.values() if u]):
        try:
            await context.bot.send_message(chat_id=user, text=message)
        except Exception as e:
            logger.warning(f"Failed to message user {user}: {e}")

# Fallback
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Upload File":
        return await upload_command(update, context)
    elif text == "Need File":
        return await need_file(update, context)

# Error handler
async def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")

# Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("need_file", need_file))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(handle_button))

    upload_conv = ConversationHandler(
        entry_points=[CommandHandler("upload", upload_command)],
        states={
            WAITING_FOR_FILE: [MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.PHOTO, receive_file)],
            WAITING_FOR_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
        },
        fallbacks=[],
    )

    app.add_handler(upload_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
