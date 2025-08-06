# 🚀 Telegram Fun File Share Bot

A bot for Telegram that allows users to upload fun files and get random files in return. All content is public, reported items are flagged for moderation.

## 🔧 Features

- Upload files with a title and disclaimer
- Retrieve files via inline buttons with pagination
- Auto-delete shared files after 5 minutes
- Report system
- Admin broadcast command
- Menu buttons below text bar

## 🚀 Deploy on Railway

1. Click the button below  
   [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

2. Set the following environment variables:

| Name | Value |
|------|-------|
| BOT_TOKEN | Your Telegram Bot Token |
| PRIVATE_GROUP_CHAT_ID | Your private group chat ID (with - prefix) |
| ADMIN_CHAT_ID | Your admin group chat ID (with - prefix) |

---

## 💬 Bot Commands

- /start – Start the bot
- /upload – Upload a file
- /need_file – Get random files
- /broadcast – Admin-only message blast
