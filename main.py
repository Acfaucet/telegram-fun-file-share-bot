import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove, BotCommand, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
import asyncio

BOT_TOKEN = "8201973948:AAG6YvqFh3jGYRoaLO0jvUBEDQdD7NxmYRI"
PRIVATE_GROUP_CHAT_ID = -2533147454
ADMIN_CHAT_ID = -2856639895

logging.basicConfig(level=logging.INFO)

UPLOAD, TITLE = range(2)
file_data = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("/upload"), KeyboardButton("/need_file")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Welcome to the Fun File Share Bot!\n\n"
        "Use /upload to share something cool or /need_file to explore awesome files from others!",
        reply_markup=reply_markup
    )

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 Hey there! Before you upload, just a quick heads-up:\n"
        "This is a fun space for everyone. Please don't share any private, illegal, or inappropriate stuff. Let's keep things awesome for the whole community!"
    )
    await update.message.reply_text("Ready to share something cool? Send me the file now!")
    return UPLOAD

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.video or update.message.photo[-1] if update.message.photo else None
    if not file:
        await update.message.reply_text("❌ Unsupported file type. Please try again.")
        return UPLOAD

    context.user_data['file'] = file
    await update.message.reply_text("Awesome! Now, give your file a catchy title.")
    return TITLE

async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    file = context.user_data.get('file')
    file_id = file.file_id
    file_data.append({'title': title, 'file_id': file_id})

    # Forward to private group for storage
    await context.bot.forward_message(chat_id=PRIVATE_GROUP_CHAT_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id - 1)
    await update.message.reply_text(f"✅ Got it! Your file, '{title}', is now ready to share with everyone!")
    return ConversationHandler.END

async def need_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not file_data:
        await update.message.reply_text("Oops! It looks like there aren't any files yet. Be the first to share one!")
        return

    context.user_data["file_page"] = 0
    await send_file_buttons(update, context, 0)

async def send_file_buttons(update, context, page):
    start = page * 20
    end = start + 20
    files = file_data[start:end]

    if not files:
        await update.message.reply_text("No more files to show.")
        return

    keyboard = [
        [InlineKeyboardButton(f["title"], callback_data=f"file_{start + i}")]
        for i, f in enumerate(files)
    ]
    if end &lt; len(file_data):
        keyboard.append([InlineKeyboardButton("🔄 Show more", callback_data="more_files")])
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Let's see what's out there! Pick a file from the list below:", reply_markup=markup)

async def file_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "more_files":
        context.user_data["file_page"] += 1
        await send_file_buttons(query, context, context.user_data["file_page"])
        return

    index = int(query.data.split("_")[1])
    if index &gt;= len(file_data):
        await query.edit_message_text("⚠️ File no longer exists.")
        return

    file = file_data[index]
    msg = await query.message.reply_document(
        document=file["file_id"],
        caption="Here's your file! This will disappear in 5 minutes, so grab it while you can!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚩 Report inappropriate file", callback_data=f"report_{index}")]
        ])
    )
    await asyncio.sleep(300)
    try:
        await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
    except:
        pass

async def report_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    index = int(query.data.split("_")[1])
    file = file_data[index]
    reporter_id = query.from_user.id

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🚨 File reported: '{file['title']}'\nReporter ID: {reporter_id}"
    )
    await query.message.reply_text("Thanks for looking out for the community! We've received your report and will check it out.")

# Broadcast command for admin
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return

    text = update.message.text.replace("/broadcast", "").strip()
    if not text:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    for file_entry in file_data:
        try:
            await context.bot.send_message(chat_id=PRIVATE_GROUP_CHAT_ID, text=f"📢 Broadcast: {text}")
            break
        except Exception as e:
            logging.warning(f"Broadcast failed: {e}")

    await update.message.reply_text("✅ Broadcast sent!")

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Upload cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('upload', upload)],
        states={
            UPLOAD: [MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.PHOTO, handle_file)],
            TITLE: [MessageHandler(filters.TEXT &amp; ~filters.COMMAND, handle_title)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("need_file", need_file))
    app.add_handler(CallbackQueryHandler(file_button, pattern="^file_"))
    app.add_handler(CallbackQueryHandler(report_file, pattern="^report_"))
    app.add_handler(CallbackQueryHandler(file_button, pattern="^more_files$"))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Start polling
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
