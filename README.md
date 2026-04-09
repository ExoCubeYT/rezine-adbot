<div align="center">

<img src="https://i.pinimg.com/originals/2c/85/01/2c85015ad0b929bc0139f1e168533457.gif" width="200" />

# 📢 Rezine AdBot (Open Source Edition)

**Automated Multi-Account Ad Broadcasting for Telegram**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/Telethon-MTProto-0088cc?style=for-the-badge&logo=telegram&logoColor=white)](https://docs.telethon.dev/)
[![python-telegram-bot](https://img.shields.io/badge/Python_Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://github.com/python-telegram-bot/python-telegram-bot)

---

A robust, fully open-source Telegram bot that automatically forwards or sends messages containing text, photos, documents, and videos to **hundreds of groups** using your own Telegram accounts on full autopilot.

[Features](#-features) · [Prerequisites](#-prerequisites) · [Quick Start](#-quick-start) · [How to Use](#-how-to-use) · [Admin Guide](#-admin-guide)

</div>

---

## ✨ Features

- 🧑🤝🧑 **Multi-Account Support** Connect an unlimited number of accounts and launch simultaneous ad broadcasts.
- 🎯 **Full Media Support** Blast messages containing Text, Photos, Videos, Documents, and Animations.
- 📡 **Live Tracking & Bot UI** Beautiful inline keyboard UI for launching campaigns and viewing real-time progress.
- 🔄 **Crash Resilience** Automatically resumes interrupted campaigns after a bot restart.
- 🛡️ **FloodWait Safety Mechanism** Smart queue handles Telegram Rate Limiting (`FloodWaitError`) safely without getting accounts banned, pausing and resuming automatically.
- 🔐 **Encrypted Session Strings** Uses auto-generated Fernet encryption for `telethon` session strings in SQLite storage. No plain cookies stored.
- 🛠️ **Full Admin Control Panel** Manage connected users, observe analytics, and mass broadcast messages to users via the `/admin` dashboard.

---

## 🔐 Prerequisites

Before running the code, gather your API keys:

1. **Telegram API ID & API Hash**: 
   - Go to [my.telegram.org](https://my.telegram.org)
   - Log in with your phone number.
   - Click **API development tools** and create an application.
   - Note down the `api_id` and `api_hash`.
2. **Bot Token**:
   - Talk to [@BotFather](https://t.me/BotFather) on Telegram.
   - Send `/newbot`, choose a name and username.
   - Copy the HTTP API Bot Token.
3. **Your Admin Telegram ID**:
   - Talk to a user info bot like [@userinfobot](https://t.me/userinfobot) to grab your numeric `User ID`. 

---

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/rezine-adbot.git
   cd rezine-adbot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the Environment File:**
   Copy the example environment file and fill it out:
   ```bash
   cp .env.example .env
   ```
   Open `.env` in a text editor and fill in the values you copied in the Prerequisites step:
   ```env
   BOT_TOKEN=your-bot-token-here
   API_ID=your-api-id-here
   API_HASH=your-api-hash-here
   ADMIN_ID=your-numeric-admin-id
   DB_PATH=data/bot.db
   ```

4. **Run the bot:**
   ```bash
   python run.py
   ```
   *(Note: On the first run, the bot will auto-generate an `ENCRYPTION_KEY` safely into your `.env` string)*

---

## 📖 How to Use

#### 1. Link Your Accounts
- Talk to your bot using `/start`.
- Navigate to **📱 My Accounts** -> **➕ Add Account**.
- Give the bot your account's phone number exactly in international format `+1234567890`.
- Provide the OTP you received from Telegram (make sure to **add spaces between digits**, like `1 2 3 4 5`, to avoid Telegram's security blocks).
- Enter the Two-Step Verification Password if asked.

#### 2. Broadcast a Campaign
- In the Bot's menu, click **📢 Campaigns** -> **📝 New Campaign**.
- Choose the linked account.
- Send the message in any format you want (Video with Caption, Image, Text).
- Click **✅ Start Campaign**. 
- Sit back. The engine scans the account's available Groups and pushes the messages iteratively, reporting progression every 10 groups.

#### 3. Managing your active campaigns
- Hit **▶️ Start / Resume**, **⏸ Pause**, or **❌ Cancel/Delete** options on your specific campaigns. Operations occur securely queued in the background.

---

## 🛠️ Admin Guide

Use the hidden `/admin` command via the bot menu to access the special administrative panel.

What you can do directly from Telegram:
- **👥 Users:** Discover the `User ID` list holding all connected target customers. Ban/unban users.
- **📊 Statistics:** Look at live Analytics—Total Users registered, total accounts linked, and active campaigns.
- **📣 Broadcast:** Create a push-bullet/post to push to every single Bot User directly (For product announcements!).

---

<div align="center">

> If you enjoy this open-source project, please consider dropping a ⭐ on the repository!

</div>
