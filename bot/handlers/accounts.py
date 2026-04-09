from __future__ import annotations
import logging
import re
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot import database as db
from bot.keyboards import (
    accounts_menu_kb,
    account_detail_kb,
    account_confirm_delete_kb,
    mask_phone,
    main_menu_kb,
)
from bot.services.telethon_manager import telethon_mgr, LoginError

logger = logging.getLogger(__name__)

PHONE, OTP, TWO_FA = range(3)


async def show_accounts_menu(query):
    accounts = await db.get_accounts(query.from_user.id)

    text = f"📱 <b>My Accounts</b> ({len(accounts)})\n\n"
    if not accounts:
        text += "No accounts linked yet. Tap ➕ to add one."
    else:
        text += "Tap an account to manage it."

    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=accounts_menu_kb(accounts))
    except BadRequest:
        pass


async def accounts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "a:list" or data == "m:acc":
        await show_accounts_menu(query)

    elif data.startswith("a:grp:"):
        account_id = int(data.split(":")[2])
        account = await db.get_account(account_id)
        if not account or account.owner_id != user_id:
            await query.edit_message_text("❌ Account not found.", reply_markup=main_menu_kb())
            return

        await query.edit_message_text("⏳ Fetching groups... This may take a moment.")
        try:
            groups = await telethon_mgr.get_groups(account.id, account.session_string)
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}", reply_markup=account_detail_kb(account_id))
            return

        text = f"📋 <b>Groups for {mask_phone(account.phone)}</b>\n\n"
        text += f"Found <b>{len(groups)}</b> groups:\n\n"
        for i, (gid, title) in enumerate(groups[:30], 1):
            text += f"  {i}. {title}\n"
        if len(groups) > 30:
            text += f"\n  ... and {len(groups) - 30} more."

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=account_detail_kb(account_id))

    elif data.startswith("a:del:"):
        account_id = int(data.split(":")[2])
        account = await db.get_account(account_id)
        if not account or account.owner_id != user_id:
            return
        await query.edit_message_text(
            f"⚠️ Disconnect <b>{mask_phone(account.phone)}</b>?\n\n"
            "This will remove the account and cancel any active campaigns using it.",
            parse_mode="HTML",
            reply_markup=account_confirm_delete_kb(account_id),
        )

    elif data.startswith("a:cdel:"):
        account_id = int(data.split(":")[2])
        account = await db.get_account(account_id)
        if not account or account.owner_id != user_id:
            return
        await telethon_mgr.disconnect_client(account_id)
        await db.deactivate_account(account_id)
        await query.edit_message_text("✅ Account disconnected.")
        await show_accounts_menu(query)

    elif data.startswith("a:") and data[2:].isdigit():
        account_id = int(data[2:])
        account = await db.get_account(account_id)
        if not account or account.owner_id != user_id:
            await query.edit_message_text("❌ Account not found.", reply_markup=main_menu_kb())
            return

        text = (
            f"📱 <b>Account Details</b>\n\n"
            f"📞 Phone: <code>{mask_phone(account.phone)}</code>\n"
            f"👤 Name: {account.display_name or 'N/A'}\n"
            f"✅ Status: Active\n"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=account_detail_kb(account_id))


async def add_account_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📱 <b>Add Account</b>\n\n"
        "Enter the phone number in international format:\n"
        "Example: <code>+12345678901</code>\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    return PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    user_id = update.effective_user.id

    if not phone.startswith("+"):
        await update.message.reply_text("❌ Phone must start with + (e.g. +12345678901)")
        return PHONE

    await update.message.reply_text("⏳ Sending OTP code...")

    try:
        msg = await telethon_mgr.start_login(user_id, phone)
    except LoginError as e:
        await update.message.reply_text(str(e))
        return ConversationHandler.END

    context.user_data["login_phone"] = phone
    await update.message.reply_text(
        f"{msg}\n\n"
        "📩 Enter the code you received.\n\n"
        "⚠️ <b>IMPORTANT:</b> To avoid Telegram blocking the login,\n"
        "enter the code with <b>spaces between digits</b>:\n"
        "Example: <code>1 2 3 4 5</code>\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    return OTP


async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    code = re.sub(r"[^0-9]", "", raw)
    user_id = update.effective_user.id

    if not code:
        await update.message.reply_text(
            "❌ Please enter the numeric code with spaces: e.g. <code>1 2 3 4 5</code>",
            parse_mode="HTML",
        )
        return OTP

    try:
        needs_2fa, result = await telethon_mgr.submit_otp(user_id, code)
    except LoginError as e:
        await update.message.reply_text(str(e))
        if "expired" in str(e).lower() or "start over" in str(e).lower():
            return ConversationHandler.END
        return OTP

    if needs_2fa:
        await update.message.reply_text(result)
        return TWO_FA

    encrypted, display = result.split("|||", 1)
    phone = context.user_data.get("login_phone", "")
    await db.add_account(user_id, phone, encrypted, display)

    await update.message.reply_text(
        f"✅ Account <b>{display}</b> ({mask_phone(phone)}) linked successfully!",
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def receive_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    user_id = update.effective_user.id

    try:
        result = await telethon_mgr.submit_2fa(user_id, password)
    except LoginError as e:
        await update.message.reply_text(str(e))
        if "wrong" in str(e).lower():
            return TWO_FA
        return ConversationHandler.END

    encrypted, display = result.split("|||", 1)
    phone = context.user_data.get("login_phone", "")
    await db.add_account(user_id, phone, encrypted, display)

    await update.message.reply_text(
        f"✅ Account <b>{display}</b> ({mask_phone(phone)}) linked successfully!",
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await telethon_mgr.cancel_login(user_id)
    await update.message.reply_text("❌ Login cancelled.", reply_markup=main_menu_kb())
    return ConversationHandler.END


account_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_account_entry, pattern=r"^a:add$")],
    states={
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
        OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp)],
        TWO_FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_2fa)],
    },
    fallbacks=[MessageHandler(filters.Regex(r"^/cancel$"), cancel_login)],
    per_chat=True,
    per_user=True,
    per_message=False,
)
