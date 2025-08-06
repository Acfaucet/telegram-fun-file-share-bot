import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import asyncio

# Bot credentials (your actual values)
BOT_TOKEN = "8201973948:AAFLCmxJ31YQBKPAMfN6fAYMYojV2ZpOLhc"
PRIVATE_GROUP_CHAT_ID = -2533147454
ADMIN_CHAT_ID = -2856639895

# File storage
file_storage = []
file_titles = []

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Welcome to the Fun File Share Bot!\n\n"
        "You can:\n"
        "📤 Upload a file with /upload\n"
        "📥 Get a shared file using /need_file",
        reply_markup=main_menu()
    )

# Main Menu Keyboard
def main_menu():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("/upload"), KeyboardButton("/need_file")]],
        resize_keyboard=True
    )

# Upload command
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ Hey there! Before you upload, just a quick heads-up:\n\n"
        "This is a fun space for everyone. Please don't share any private, illegal, or inappropriate stuff.\n"
        "Let's keep things awesome for the whole community!"
    )
    await update.message.reply_text("Ready to share something cool? Send me the file now!")

# Handle incoming files
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.photo[-1] or update.message.video

    if not file:
        await update.message.reply_text("❌ Unsupported file type. Try again.")
        return

    context.user_data["file_id"] = file.file_id
    await update.message.reply_text("Awesome! Now, give your file a catchy title.")

# Handle title
async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "file_id" not in context.user_data:
        return

    title = update.message.text
    file_id = context.user_data["file_id"]

    file_storage.append({
        "title": title,
        "file_id": file_id
    })

    await context.bot.forward_message(
        chat_id=PRIVATE_GROUP_CHAT_ID,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id - 1
    )

    await update.message.reply_text(f"✅ Got it! Your file, '{title}', is now ready to share with everyone!")
    context.user_data.clear()

# Need file command
async def need_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_file_list(update, context, offset=0)

# Send 20 files with offset
async def send_file_list(update, context, offset):
    if not file_storage:
        await update.message.reply_text("Oops! It looks like there aren't any files yet. Be the first to share one!")
        return

    buttons = []
    end = min(len(file_storage), offset + 20)
    for i in range(offset, end):
        buttons.append([
            InlineKeyboardButton(file_storage[i]["title"], callback_data=f"sendfile_{i}")
        ])

    if end < len(file_storage):
        buttons.append([
            InlineKeyboardButton("➡️ More Files", callback_data=f"morefiles_{end}")
        ])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Let's see what's out there! Pick a file from the list below:", reply_markup=reply_markup)

# Callback query
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("sendfile_"):
        index = int(query.data.split("_")[1])
        file_info = file_storage[index]

        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=file_info["file_id"]
        )
        msg = await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Here's your file! This will disappear in 5 minutes, so grab it while you can!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚩 Report inappropriate file", callback_data=f"report_{index}")]
            ])
        )
        await asyncio.sleep(300)
        try:
            await context.bot.delete_message(chat_id=query.from_user.id, message_id=msg.message_id)
        except:
            pass

    elif query.data.startswith("morefiles_"):
        offset = int(query.data.split("_")[1])
        await send_file_list(query, context, offset)

    elif query.data.startswith("report_"):
        index = int(query.data.split("_")[1])
        file_info = file_storage[index]
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 File reported:\nTitle: {file_info['title']}\nBy user: {query.from_user.id}"
        )
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Thanks for looking out for the community! We've received your report and will check it out."
        )

# Broadcast command (admin only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("You're not authorized to use this command.")
        return

    if context.args:
        message = " ".join(context.args)
        count = 0
        for user in set(u.message.chat_id for u in context.bot_data.get("users", [])):
            try:
                await context.bot.send_message(chat_id=user, text=f"📢 Broadcast:\n\n{message}")
                count += 1
            except:
                pass
        await update.message.reply_text(f"Broadcast sent to {count} users.")
    else:
        await update.message.reply_text("Please provide a message to broadcast.")

# Track all users
async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data.setdefault("users", []).append(update)

# Main function
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("need_file", need_file))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # File handlers
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO,
        handle_file
    ))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_title))
    app.add_handler(MessageHandler(filters.ALL, track_users))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
                               
