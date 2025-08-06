import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# BOT CONFIG
BOT_TOKEN = '8201973948:AAG6YvqFh3jGYRoaLO0jvUBEDQdI7NxmYRI'
PRIVATE_GROUP_CHAT_ID = -2533147454
ADMIN_CHAT_ID = -2856639895

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Memory storage
pending_uploads = {}
files_data = {}  # file_id: title
FILES_PER_PAGE = 20


def get_file_page(offset=0):
    file_items = list(files_data.items())
    page_items = file_items[offset:offset + FILES_PER_PAGE]

    keyboard = [
        [InlineKeyboardButton(title, callback_data=f"file|{file_id}")]
        for file_id, title in page_items
    ]

    if offset + FILES_PER_PAGE < len(file_items):
        keyboard.append(
            [InlineKeyboardButton("📁 Request more files", callback_data=f"more|{offset + FILES_PER_PAGE}")]
        )

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Fun File Share Bot!\n\n"
        "Share cool (and safe!) stuff with others.\n\n"
        "Use /upload to share a file.\n"
        "Use /need_file to browse shared files."
    )


async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pending_uploads[user_id] = {"step": "awaiting_file"}
    await update.message.reply_text(
        "📢 Hey there! Before you upload, just a quick heads-up:\n"
        "This is a fun space for everyone. Please don't share any private, illegal, or inappropriate stuff.\n\n"
        "✅ Ready to share something cool? Send me the file now!"
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in pending_uploads and pending_uploads[user_id]["step"] == "awaiting_file":
        document = update.message.document or update.message.video or update.message.photo[-1]
        file_id = document.file_id
        pending_uploads[user_id]["file_id"] = file_id
        pending_uploads[user_id]["step"] = "awaiting_title"
        await update.message.reply_text("🎉 Awesome! Now, give your file a catchy title.")
    else:
        await update.message.reply_text("🤔 Please use /upload before sending a file.")


async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in pending_uploads and pending_uploads[user_id]["step"] == "awaiting_title":
        title = update.message.text
        file_id = pending_uploads[user_id]["file_id"]
        files_data[file_id] = title

        await context.bot.send_message(chat_id=PRIVATE_GROUP_CHAT_ID, text=f"Stored: {title}")
        await context.bot.copy_message(
            chat_id=PRIVATE_GROUP_CHAT_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id - 1
        )

        await update.message.reply_text(f"✅ Got it! Your file, '{title}', is now ready to share with everyone!")
        del pending_uploads[user_id]
    else:
        await update.message.reply_text("🤔 I'm not expecting a title right now. Start with /upload.")


async def need_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not files_data:
        await update.message.reply_text("📭 Oops! It looks like there aren't any files yet. Be the first to share one with /upload!")
        return

    markup = get_file_page(0)
    await update.message.reply_text("📂 Let's see what's out there! Pick a file from the list below:", reply_markup=markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("file|"):
        file_id = query.data.split("|")[1]
        title = files_data.get(file_id)
message = await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=file_id,
            caption="📁 Here's your file! This will disappear in 5 minutes, so grab it while you can!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚩 Report inappropriate file", callback_data=f"report|{file_id}|{query.from_user.id}")]
            ])
        )

        await asyncio.sleep(300)
        try:
            await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
        except:
            pass

    elif query.data.startswith("more|"):
        offset = int(query.data.split("|")[1])
        markup = get_file_page(offset)
        await query.edit_message_reply_markup(reply_markup=markup)

    elif query.data.startswith("report|"):
        _, file_id, user_id = query.data.split("|")
        title = files_data.get(file_id, "Unknown Title")

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 File Reported:\nTitle: {title}\nReported by User ID: {user_id}"
        )
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="🙌 Thanks for looking out for the community! We've received your report and will check it out."
        )


# 🔊 Broadcast from admin group only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return

    if not context.args:
        await update.message.reply_text("❗ Usage: /broadcast Your message here")
        return

    msg = "📢 Broadcast:\n" + " ".join(context.args)
    for user_id in pending_uploads.keys():
        try:
            await context.bot.send_message(chat_id=user_id, text=msg)
        except:
            pass

    await update.message.reply_text("✅ Broadcast sent!")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("need_file", need_file))
    app.add_handler(CommandHandler("broadcast", broadcast))  # only for admin group

    app.add_handler(MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.PHOTO, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title))
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.run_polling()


if name == 'main':
    main()
