from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot import database as db
from bot.config import ADMIN_ID
from bot.keyboards import main_menu_kb

WELCOME = (
    "🚀 <b>Welcome to Rezine AdBot!</b>\n\n"
    "Broadcast your ads to hundreds of Telegram groups with one click.\n\n"
    "📱 <b>My Accounts</b> — Link your Telegram accounts\n"
    "📢 <b>Campaigns</b> — Create & manage ad broadcasts\n"
)

HELP_TEXT = (
    "ℹ️ <b>How It Works</b>\n\n"
    "1️⃣ <b>Link Account</b> — Go to 📱 My Accounts → Add Account.\n"
    "   Enter your phone, OTP, and 2FA (if enabled).\n\n"
    "2️⃣ <b>Create Campaign</b> — Go to 📢 Campaigns → New Campaign.\n"
    "   Pick an account, type your ad message, and launch!\n\n"
    "3️⃣ <b>Watch Progress</b> — The bot sends live updates as\n"
    "   your ad is delivered to each group.\n\n"
    "🛡 <b>Safety</b>: The bot automatically pauses on Telegram\n"
    "flood errors and resumes after the wait period.\n\n"
    "Need help? Contact the admin."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.get_or_create_user(user.id, user.username)

    db_user = await db.get_user(user.id)
    if db_user and db_user.is_banned:
        await update.message.reply_text("🚫 Your account has been suspended. Contact admin.")
        return

    await update.message.reply_text(WELCOME, parse_mode="HTML", reply_markup=main_menu_kb())


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    user = await db.get_or_create_user(query.from_user.id, query.from_user.username)
    if user.is_banned:
        await query.edit_message_text("🚫 Your account has been suspended.")
        return

    if data == "m:main":
        try:
            await query.edit_message_text(WELCOME, parse_mode="HTML", reply_markup=main_menu_kb())
        except BadRequest:
            pass

    elif data == "m:acc":
        from bot.handlers.accounts import show_accounts_menu
        await show_accounts_menu(query)

    elif data == "m:camp":
        from bot.handlers.campaigns import show_campaigns_menu
        await show_campaigns_menu(query)

    elif data == "m:help":
        try:
            await query.edit_message_text(HELP_TEXT, parse_mode="HTML", reply_markup=main_menu_kb())
        except BadRequest:
            pass
