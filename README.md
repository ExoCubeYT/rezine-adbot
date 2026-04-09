<div align="center">

<img src="https://i.pinimg.com/originals/2c/85/01/2c85015ad0b929bc0139f1e168533457.gif" width="200" />

# Rezine AdBot

If you need to push a single message to hundreds of Telegram groups simultaneously using multiple accounts, you've found the right tool. 

Built cleanly on Python, Telethon, and AIOSQLite, this bot automates the tedious process of forwarding and broadcasting marketing messages across your Telegram accounts. 

</div>

## What Problem Does This Solve?
Managing ad campaigns manually on Telegram is painful. You get flood limits, you have to click manually, and managing multiple accounts at once is practically impossible. 

**Rezine AdBot** fixes this by:
* Managing an unlimited amount of your Telegram accounts at once via a single, interactive bot interface.
* Reading every group each account is in and iteratively broadcasting a custom message to them.
* Catching and sleeping through Telegram's rate-limiting automatically (No more banned accounts from accidental spam).
* Keeping persistent sessions securely encrypted in a database so you never have to re-login if the script restarts.
* Pausing, resuming, and tracking the analytics of your broadcast runs directly from Telegram inline buttons.

---

## 🛠️ Installation & Setup

You will need a computer or server with **Python 3.10+**. 

**1. Clone the codebase**
```bash
git clone https://github.com/your-username/rezine-adbot.git
cd rezine-adbot
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure your keys**
Rename `.env.example` to `.env` and fill it out:
```bash
cp .env.example .env
```

You must fill out the `.env` file for the bot to run:
* `BOT_TOKEN` -> Get this by creating a new bot with [@BotFather](https://t.me/BotFather).
* `API_ID` & `API_HASH` -> Get these by logging into [my.telegram.org](https://my.telegram.org) and creating an API development app.
* `ADMIN_ID` -> Your personal Telegram numeric ID (get it from [@userinfobot](https://t.me/userinfobot)). Only you will be able to access the admin panel.
example:
   ```
   BOT_TOKEN=your-bot-token-here
   API_ID=your-api-id-here
   API_HASH=your-api-hash-here
   ADMIN_ID=your-numeric-admin-id
   DB_PATH=data/bot.db
   ```

**4. Start the engine**
```bash
python run.py
```
*(On your very first run, Rezine will generate a secure `ENCRYPTION_KEY` and append it to your `.env` file to encrypt all your session strings safely).*

---

## 🎮 Interacting with Rezine

Everything is controlled via inline buttons directly inside Telegram—no typing commands necessary.

Message your newly created bot to begin:
```
/start
```

* **My Accounts Menu**: Add your personal or runner Telegram accounts. Input the phone number, OTP, and 2FA password. The bot handles the MTProto authorization safely behind the scenes.
* **Campaigns Menu**: Select the sender account, upload your promotional material (Images, Videos, GIFs, or plain text), and fire off the broadcast.
* **The Admin Dashboard**: Type `/admin` to secretly peek at total stats across your database (who is using your bot, total campaigns, and global user broadcasts).

---

## 🧠 Under the Hood
* Built with [python-telegram-bot](https://python-telegram-bot.org/) for the sleek frontend and [Telethon](https://docs.telethon.dev/) for the heavy-lifting backend MTProto API interaction.
* Highly asynchronous. Relies fully on `asyncio` to ensure 5 campaigns can run alongside each other seamlessly without blocking the user interface. SQLite concurrency is handled via `aiosqlite`.
* **Zero plain-text sessions.** Your `telethon.StringSession` data is encrypted using Fernet cryptography before being written to disk.

---

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

*Please use this software responsibly and abide by Telegram's Terms of Service regarding mass-messaging and spam. The authors of Rezine AdBot take no responsibility for accounts restricted by excessive automation.*
