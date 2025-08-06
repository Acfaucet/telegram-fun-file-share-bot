import logging
import asyncio
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    BotCommand,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes, 
    filters
)

BOT_TOKEN = "8201973948:AAFLCmxJ31YQBKPAMfN6fAYMYojV2ZpOLhc"
PRIVATE_GROUP_CHAT_ID = -2533147454
ADMIN_CHAT_ID = -2856639895

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data store
files = []
user_ids = set()

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ids.add(update.effective_user.id)
    await update.message.reply_text(
        "👋 Welcome to the Fun File Share Bot!\n"
        "You can share fun files with others using /upload or get some using /need_file!",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📤 Upload File"), KeyboardButton("📥 Need File")]],
            resize_keyboard=True
        )
    )

# Command: /upload
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Disclaimer!*\n\n"
        "This is a fun space for everyone. Please don't share any private, illegal, or inappropriate content.",
        parse_mode="Markdown"
    )
    await update.message.reply_text("Ready to share something cool? Send me the file now!")
    context.user_data["uploading"] = True

# Handle file upload
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("uploading"):
        return

    file = update.message.document or update.message.video or update.message.photo[-1] if update.message.photo else None
    if file:
        context.user_data["file_id"] = file.file_id
        await update.message.reply_text("Awesome! Now, give your file a catchy title.")
        context.user_data["awaiting_title"] = True
        context.user_data["uploading"] = False

# Handle title
async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_title"):
        title = update.message.text
        file_id = context.user_data.get("file_id")
        files.append({"title": title, "file_id": file_id})
        await context.bot.forward_message(chat_id=PRIVATE_GROUP_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id - 1)
        await update.message.reply_text(f"Got it! Your file, '{title}', is now ready to share with everyone!")
        context.user_data.clear()

# Command: /need_file
async def need_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not files:
        await update.message.reply_text("Oops! Looks like there aren’t any files yet. Be the first to share one!")
        return
    context.user_data["page"] = 0
    await send_file_list(update, context)

async def send_file_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = context.user_data.get("page", 0)
    start = page * 20
    end = start + 20
    file_buttons = [
        [InlineKeyboardButton(f["title"], callback_data=f'send_{i}')]
        for i, f in enumerate(files[start:end], start)
    ]
    if end < len(files):
        file_buttons.append([InlineKeyboardButton("➡ Request more files", callback_data="more_files")])
    await update.message.reply_text(
        "🎁 Pick a file from the list below:",
        reply_markup=InlineKeyboardMarkup(file_buttons)
    )

# Handle inline buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("send_"):
        index = int(data.split("_")[1])
        file_data = files[index]
        msg = await query.message.reply_document(
            file_id=file_data["file_id"],
            caption="Here's your file! This will disappear in 5 minutes, so grab it while you can!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚩 Report inappropriate file", callback_data=f"report_{index}")]
            ])
        )
        await asyncio.sleep(300)
        await msg.delete()

    elif data == "more_files":
        context.user_data["page"] += 1
        await send_file_list(update, context)

    elif data.startswith("report_"):
        index = int(data.split("_")[1])
        file_data = files[index]
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"⚠️ *Report Received!*\n\nTitle: {file_data['title']}\nReported by: {update.effective_user.id}",
            parse_mode="Markdown"
        )
        await query.message.reply_text("Thanks for looking out for the community! We've received your report.")

# Command: /broadcast (admin only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = "📢 Broadcast:\n" + " ".join(context.args)
    success = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, msg)
            success += 1
        except:
            continue
    await update.message.reply_text(f"Broadcast sent to {success} users.")

# Handler for reply keyboard options
async def reply_keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "📤 Upload File":
        await upload(update, context)
    elif update.message.text == "📥 Need File":
        await need_file(update, context)

# Main
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("upload", "Upload a file"),
        BotCommand("need_file", "Get a shared file"),
        BotCommand("broadcast", "Broadcast message to all users (admin only)")
    ])
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("need_file", need_file))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Photo.ALL | filters.Video.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_keyboard_handler))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
                        
