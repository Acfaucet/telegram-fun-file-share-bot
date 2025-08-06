import logging
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from collections import deque
import asyncio

BOT_TOKEN = "8201973948:AAG6YvqFh3jGYRoaLO0jvUBEDQdI7NxmYRI"
PRIVATE_GROUP_CHAT_ID = -2533147454
ADMIN_CHAT_ID = -2856639895

logging.basicConfig(level=logging.INFO)
user_states = {}
file_storage = deque(maxlen=1000)  # Holds (file_id, title)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Welcome to the Fun File Share Bot!\n\n"
        "Use /upload to share a file.\n"
        "Use /need_file to explore and grab files from the community.",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("/upload"), KeyboardButton("/need_file")]],
            resize_keyboard=True,
        )
    )

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id] = {"step": "waiting_file"}
    await update.message.reply_text(
        "Hey there! 🚀\nBefore you upload, just a quick heads-up: "
        "this is a fun space for everyone. Please don't share any private, illegal, or inappropriate stuff. "
        "Let's keep things awesome for the whole community!\n\n"
        "Ready to share something cool? Send me the file now!"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if not state or state.get("step") != "waiting_file":
        return

    file = update.message.document or update.message.video or update.message.photo[-1]
    file_id = file.file_id

    state["file_id"] = file_id
    state["step"] = "waiting_title"

    await update.message.reply_text("Awesome! 🎉 Now, give your file a catchy title.")

async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if not state or state.get("step") != "waiting_title":
        return

    title = update.message.text
    file_id = state["file_id"]
    file_storage.append((file_id, title))

    await context.bot.forward_message(chat_id=PRIVATE_GROUP_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id - 1)

    await update.message.reply_text(f"✅ Got it! Your file, '{title}', is now ready to share with everyone!")

    user_states.pop(user_id, None)

async def need_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not file_storage:
        await update.message.reply_text("Oops! 😅 There aren't any files yet. Be the first to share one!")
        return
    await send_file_list(update, context, 0)

async def send_file_list(update: Update, context: ContextTypes.DEFAULT_TYPE, offset: int):
    buttons = []
    for i, (file_id, title) in enumerate(list(file_storage)[offset:offset + 20]):
        buttons.append([InlineKeyboardButton(title, callback_data=f"get_{offset + i}")])

    if offset + 20 < len(file_storage):
        buttons.append([InlineKeyboardButton("🔁 Show More", callback_data=f"more_{offset + 20}")])

    await update.message.reply_text(
        "📁 Let's see what's out there! Pick a file from the list below:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("get_"):
        index = int(data.split("_")[1])
        file_id, title = list(file_storage)[index]

        sent_message = await query.message.reply_document(
            file_id,
            caption=f"Here's your file! ⏳ This will disappear in 5 minutes, so grab it while you can!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚩 Report inappropriate file", callback_data=f"report_{index}")]
            ])
        )

        await asyncio.sleep(300)
        try:
            await sent_message.delete()
        except:
            pass

    elif data.startswith("more_"):
        offset = int(data.split("_")[1])
        await send_file_list(update, context, offset)

    elif data.startswith("report_"):
        index = int(data.split("_")[1])
        file_id, title = list(file_storage)[index]
        user_id = query.from_user.id

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 Report Alert!\nFile Title: {title}\nReported by User ID: {user_id}"
        )
        await query.message.reply_text("Thanks for looking out for the community! We'll check it out. 🙏")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return await update.message.reply_text("🚫 You are not authorized to use this command.")
    message = update.message.text.split(" ", 1)
    if len(message) < 2:
        return await update.message.reply_text("⚠️ Usage: /broadcast Your message here")
    for user_id in user_states:
        try:
            await context.bot.send_message(chat_id=user_id, text=message[1])
        except Exception as e:
            logging.error(e)
    await update.message.reply_text("✅ Broadcast sent.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("need_file", need_file))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.PHOTO, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()

if __name__ == "__main__":
    main()
