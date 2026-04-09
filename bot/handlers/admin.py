import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot import database as db
from bot.config import ADMIN_ID
from bot.keyboards import (
    admin_panel_kb,
    admin_users_kb,
    admin_user_detail_kb,
    main_menu_kb,
)

logger = logging.getLogger(__name__)

BROADCAST_MSG, BROADCAST_CONFIRM = range(2)


def is_admin(user_id):
    return user_id == ADMIN_ID


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Admin access only.")
        return
    await update.message.reply_text("⚙️ <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_panel_kb())


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("🚫 Admin only", show_alert=True)
        return
    await query.answer()
    data = query.data

    if data == "ad:panel":
        await query.edit_message_text("⚙️ <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_panel_kb())

    elif data.startswith("ad:users"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        page_size = 8
        users = await db.get_all_users(limit=page_size, offset=page * page_size)
        total = await db.count_users()
        text = f"👥 <b>Users</b> ({total} total)\n\n"
        if not users:
            text += "No users yet."
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=admin_users_kb(users, page, page_size))

    elif data.startswith("ad:u:"):
        user_id = int(data.split(":")[2])
        await _show_user_detail(query, user_id)

    elif data.startswith("ad:ban:"):
        user_id = int(data.split(":")[2])
        await db.set_user_ban(user_id, True)
        await query.answer(f"🚫 User {user_id} banned.", show_alert=True)
        await _show_user_detail(query, user_id)

    elif data.startswith("ad:uban:"):
        user_id = int(data.split(":")[2])
        await db.set_user_ban(user_id, False)
        await query.answer(f"✅ User {user_id} unbanned.", show_alert=True)
        await _show_user_detail(query, user_id)

    elif data == "ad:stats":
        total_users = await db.count_users()
        total_accounts = await db.count_all_accounts()
        total_campaigns = await db.count_all_campaigns()
        text = (
            f"📊 <b>Statistics</b>\n\n"
            f"👥 Total users: {total_users}\n"
            f"📱 Linked accounts: {total_accounts}\n"
            f"📢 Total campaigns: {total_campaigns}\n"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=admin_panel_kb())

    elif data == "ad:noop":
        pass


async def _show_user_detail(query, user_id):
    user = await db.get_user(user_id)
    if not user:
        await query.edit_message_text("User not found.", reply_markup=admin_panel_kb())
        return

    accounts = await db.count_accounts(user_id)
    campaigns = await db.count_active_campaigns(user_id)

    ban_status = "🚫 BANNED" if user.is_banned else "✅ Active"
    text = (
        f"👤 <b>User Detail</b>\n\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Accounts: {accounts}\n"
        f"Active campaigns: {campaigns}\n"
        f"Status: {ban_status}\n"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=admin_user_detail_kb(user_id, user.is_banned))


async def broadcast_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("🚫 Admin only", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    await query.edit_message_text(
        "📣 <b>Broadcast</b>\n\nSend the message to broadcast to all users:\n\nSend /cancel to abort.",
        parse_mode="HTML",
    )
    return BROADCAST_MSG


async def broadcast_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["broadcast_text"] = update.message.text
    await update.message.reply_text(
        f"📣 <b>Broadcast Preview:</b>\n\n{update.message.text}\n\n"
        "Send <b>CONFIRM</b> to send to all users, or /cancel to abort.",
        parse_mode="HTML",
    )
    return BROADCAST_CONFIRM


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip().upper() != "CONFIRM":
        await update.message.reply_text("Send CONFIRM to proceed or /cancel to abort.")
        return BROADCAST_CONFIRM

    text = context.user_data.get("broadcast_text", "")
    users = await db.get_all_users(limit=10000)
    sent = 0
    failed = 0
    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u.telegram_id,
                text=f"📣 <b>Announcement</b>\n\n{text}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast complete!\nSent: {sent} | Failed: {failed}",
        reply_markup=admin_panel_kb(),
    )
    return ConversationHandler.END


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.", reply_markup=admin_panel_kb())
    return ConversationHandler.END


admin_broadcast_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(broadcast_entry, pattern=r"^ad:bc$")],
    states={
        BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_msg)],
        BROADCAST_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_confirm)],
    },
    fallbacks=[MessageHandler(filters.Regex(r"^/cancel$"), cancel_admin)],
    per_chat=True,
    per_user=True,
    per_message=False,
)
