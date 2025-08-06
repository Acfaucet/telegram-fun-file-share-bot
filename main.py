
from keep_alive import keep_alive
keep_alive()

import logging
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# Get values from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
PRIVATE_GROUP_CHAT_ID = os.environ.get('PRIVATE_GROUP_CHAT_ID')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Convert to int if provided
if PRIVATE_GROUP_CHAT_ID:
    PRIVATE_GROUP_CHAT_ID = int(PRIVATE_GROUP_CHAT_ID)
if ADMIN_CHAT_ID:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# In-memory storage
pending_uploads = {}  # {user_id: {"step": ..., "file_id": ...}}
files_data = {}       # {file_id: title}
file_id_mapping = {}  # {short_id: file_id} for callback data
next_file_id = 1
FILES_PER_PAGE = 20

# Create persistent menu keyboard
def get_main_menu():
    keyboard = [
        [KeyboardButton("📤 Upload File"), KeyboardButton("📁 Browse Files")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Fun File Share Bot!\n\n"
        "Share cool (and safe!) stuff with others.\n\n"
        "Use the menu below or commands:\n"
        "📤 Upload File - Share a file\n"
        "📁 Browse Files - See shared files",
        reply_markup=get_main_menu()
    )


# Upload flow
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pending_uploads[user_id] = {"step": "awaiting_file"}
    await update.message.reply_text(
        "📢 Hey there! Before you upload, just a quick heads-up:\n"
        "This is a fun space for everyone. Please don't share any private, illegal, or inappropriate stuff.\n\n"
        "✅ Ready to share something cool? Send me the file now!",
        reply_markup=get_main_menu()
    )


# Handle file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in pending_uploads and pending_uploads[user_id]["step"] == "awaiting_file":
        # Determine file type and get file_id
        if update.message.document:
            file_id = update.message.document.file_id
            file_type = "document"
        elif update.message.video:
            file_id = update.message.video.file_id
            file_type = "video"
        elif update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_type = "photo"
        else:
            await update.message.reply_text("🤔 Please send a valid file type.")
            return

        pending_uploads[user_id]["file_id"] = file_id
        pending_uploads[user_id]["file_type"] = file_type
        pending_uploads[user_id]["step"] = "awaiting_title"

        await update.message.reply_text("🎉 Awesome! Now, give your file a catchy title.", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("🤔 Please use /upload before sending a file.", reply_markup=get_main_menu())


# Handle title input
async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_file_id
    user_id = update.message.from_user.id
    
    # Check for menu button presses
    if update.message.text == "📤 Upload File":
        await upload(update, context)
        return
    elif update.message.text == "📁 Browse Files":
        await need_file(update, context)
        return
    
    if user_id in pending_uploads and pending_uploads[user_id]["step"] == "awaiting_title":
        title = update.message.text
        file_id = pending_uploads[user_id]["file_id"]
        file_type = pending_uploads[user_id]["file_type"]

        # Create short ID for callback data
        short_id = str(next_file_id)
        next_file_id += 1
        
        files_data[file_id] = {"title": title, "type": file_type}
        file_id_mapping[short_id] = file_id

        # Try to forward to private group, but continue if it fails
        if PRIVATE_GROUP_CHAT_ID:
            try:
                await context.bot.send_message(chat_id=PRIVATE_GROUP_CHAT_ID, text=f"Stored: {title}")
                await context.bot.copy_message(
                    chat_id=PRIVATE_GROUP_CHAT_ID,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id - 1
                )
            except Exception as e:
                print(f"Warning: Could not send to private group: {e}")

        await update.message.reply_text(f"✅ Got it! Your file, '{title}', is now ready to share with everyone!", reply_markup=get_main_menu())
        del pending_uploads[user_id]
    else:
        await update.message.reply_text("🤔 I'm not expecting a title right now. Use the menu below or /upload.", reply_markup=get_main_menu())


# Pagination keyboard builder
def get_file_page(offset=0):
    file_items = list(files_data.items())
    page_items = file_items[offset:offset + FILES_PER_PAGE]

    keyboard = []
    for file_id, file_info in page_items:
        # Find the short_id for this file_id
        short_id = None
        for sid, fid in file_id_mapping.items():
            if fid == file_id:
                short_id = sid
                break
        
        if short_id:
            # Truncate title if too long to keep callback data under 64 bytes
            title = file_info["title"] if isinstance(file_info, dict) else file_info
            display_title = title[:30] + "..." if len(title) > 30 else title
            keyboard.append([InlineKeyboardButton(display_title, callback_data=f"f|{short_id}")])

    if offset + FILES_PER_PAGE < len(file_items):
        keyboard.append(
            [InlineKeyboardButton("📁 More files", callback_data=f"m|{offset + FILES_PER_PAGE}")]
        )

    return InlineKeyboardMarkup(keyboard)


# Handle /need_file
async def need_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not files_data:
        await update.message.reply_text("📭 Oops! It looks like there aren't any files yet. Be the first to share one with /upload!", reply_markup=get_main_menu())
        return

    markup = get_file_page(0)
    await update.message.reply_text("📂 Let's see what's out there! Pick a file from the list below:", reply_markup=markup)


# Callback queries
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("f|"):
        short_id = query.data.split("|")[1]
        file_id = file_id_mapping.get(short_id)
        
        if not file_id:
            await query.edit_message_text("❌ File not found.")
            return
            
        file_info = files_data.get(file_id)
        
        # Handle both old format (string) and new format (dict)
        if isinstance(file_info, dict):
            file_type = file_info["type"]
            title = file_info["title"]
        else:
            file_type = "document"  # Default for old entries
            title = file_info

        caption = "📁 Here's your file! This will disappear in 5 minutes, so grab it while you can!"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚩 Report", callback_data=f"r|{short_id}|{query.from_user.id}")]
        ])

        # Send file using appropriate method based on type
        try:
            if file_type == "photo":
                message = await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=file_id,
                    caption=caption,
                    reply_markup=reply_markup
                )
            elif file_type == "video":
                message = await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=file_id,
                    caption=caption,
                    reply_markup=reply_markup
                )
            else:  # document
                message = await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=file_id,
                    caption=caption,
                    reply_markup=reply_markup
                )
        except Exception as e:
            await query.edit_message_text("❌ Error sending file. It may no longer be available.")
            return

        # Delete after 5 minutes
        await asyncio.sleep(300)
        try:
            await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
        except:
            pass

    elif query.data.startswith("m|"):
        offset = int(query.data.split("|")[1])
        markup = get_file_page(offset)
        await query.edit_message_reply_markup(reply_markup=markup)

    elif query.data.startswith("r|"):
        parts = query.data.split("|")
        short_id = parts[1]
        user_id = parts[2]
        file_id = file_id_mapping.get(short_id)
        file_info = files_data.get(file_id, "Unknown Title")
        
        # Handle both old format (string) and new format (dict)
        if isinstance(file_info, dict):
            title = file_info["title"]
        else:
            title = file_info

        if ADMIN_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"🚨 File Reported:\nTitle: {title}\nReported by User ID: {user_id}"
                )
            except Exception as e:
                print(f"Warning: Could not send to admin chat: {e}")
            
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="🙌 Thanks for looking out for the community! We've received your report and will check it out."
        )


# Run
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("need_file", need_file))

    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title))

    app.add_handler(CallbackQueryHandler(handle_callback))

    # Run with better error handling and longer polling timeout
    app.run_polling(
        poll_interval=2.0,  # Check for updates every 2 seconds instead of default 1
        timeout=30         # Longer timeout for getUpdates requests
    )


if __name__ == '__main__':
    main()
