from __future__ import annotations
import os
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot import database as db
from bot.config import MEDIA_DIR, DEFAULT_DELAY_MIN, DEFAULT_DELAY_MAX
from bot.keyboards import (
    campaigns_menu_kb,
    campaign_select_account_kb,
    campaign_confirm_kb,
    campaign_detail_kb,
    main_menu_kb,
    mask_phone,
)
from bot.services.campaign_engine import campaign_engine

logger = logging.getLogger(__name__)

SELECT_ACCOUNT, COMPOSE_MSG, CONFIRM = range(3)


async def show_campaigns_menu(query):
    user_id = query.from_user.id

    campaigns = await db.get_campaigns(user_id)
    active = await db.count_active_campaigns(user_id)

    text = f"📢 <b>My Campaigns</b> ({active} active)\n\n"
    if not campaigns:
        text += "No campaigns yet. Tap 📝 to create one."
    else:
        text += "Tap a campaign to manage it."

    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=campaigns_menu_kb(campaigns))
    except BadRequest:
        pass


async def campaigns_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "c:list":
        await show_campaigns_menu(query)

    elif data.startswith("c:run:"):
        campaign_id = int(data.split(":")[2])
        campaign = await db.get_campaign(campaign_id)
        if not campaign or campaign.owner_id != user_id:
            return
        await query.edit_message_text(f"▶️ Starting campaign #{campaign_id}...")
        await campaign_engine.start_campaign(campaign_id)
        campaign = await db.get_campaign(campaign_id)
        await _show_campaign_detail(query, campaign)

    elif data.startswith("c:pause:"):
        campaign_id = int(data.split(":")[2])
        campaign = await db.get_campaign(campaign_id)
        if not campaign or campaign.owner_id != user_id:
            return
        await campaign_engine.pause_campaign(campaign_id)
        campaign = await db.get_campaign(campaign_id)
        await _show_campaign_detail(query, campaign)

    elif data.startswith("c:stop:"):
        campaign_id = int(data.split(":")[2])
        campaign = await db.get_campaign(campaign_id)
        if not campaign or campaign.owner_id != user_id:
            return
        await campaign_engine.stop_campaign(campaign_id)
        campaign = await db.get_campaign(campaign_id)
        await _show_campaign_detail(query, campaign)

    elif data.startswith("c:del:"):
        campaign_id = int(data.split(":")[2])
        campaign = await db.get_campaign(campaign_id)
        if not campaign or campaign.owner_id != user_id:
            return
        await db.delete_campaign(campaign_id)
        await query.edit_message_text("🗑 Campaign deleted.")
        await show_campaigns_menu(query)

    elif data.startswith("c:") and data[2:].isdigit():
        campaign_id = int(data[2:])
        campaign = await db.get_campaign(campaign_id)
        if not campaign or campaign.owner_id != user_id:
            await query.edit_message_text("❌ Campaign not found.", reply_markup=main_menu_kb())
            return
        await _show_campaign_detail(query, campaign)


async def _show_campaign_detail(query, campaign):
    STATUS_ICON = {"draft": "📝", "running": "▶️", "paused": "⏸", "completed": "✅", "failed": "❌"}
    icon = STATUS_ICON.get(campaign.status, "❓")

    account = await db.get_account(campaign.account_id)
    acc_label = mask_phone(account.phone) if account else "Unknown"

    text = (
        f"📢 <b>Campaign #{campaign.id}</b>\n\n"
        f"Status: {icon} {campaign.status.title()}\n"
        f"Account: {acc_label}\n"
        f"Progress: {campaign.sent_count + campaign.failed_count}/{campaign.total_groups}\n"
        f"  ✅ Sent: {campaign.sent_count}\n"
        f"  ❌ Failed: {campaign.failed_count}\n\n"
        f"📝 <b>Message preview:</b>\n"
        f"<i>{campaign.message_text[:200]}{'...' if len(campaign.message_text) > 200 else ''}</i>"
    )
    if campaign.message_media_type:
        text += f"\n📎 Media: {campaign.message_media_type}"

    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=campaign_detail_kb(campaign))
    except BadRequest:
        pass


async def new_campaign_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    accounts = await db.get_accounts(user_id)
    if not accounts:
        await query.edit_message_text(
            "❌ You need to link an account first.\nGo to 📱 My Accounts → Add Account.",
            reply_markup=main_menu_kb(),
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "📢 <b>New Campaign</b>\n\nSelect the account to send from:",
        parse_mode="HTML",
        reply_markup=campaign_select_account_kb(accounts),
    )
    return SELECT_ACCOUNT


async def select_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "m:camp":
        await show_campaigns_menu(query)
        return ConversationHandler.END

    account_id = int(data.replace("cs:", ""))
    account = await db.get_account(account_id)
    if not account or account.owner_id != query.from_user.id:
        await query.edit_message_text("❌ Account not found.", reply_markup=main_menu_kb())
        return ConversationHandler.END

    context.user_data["camp_account_id"] = account_id
    await query.edit_message_text(
        "📝 <b>Compose your ad message</b>\n\n"
        "Send your ad message now. You can include:\n"
        "• Text\n• Photo with caption\n• Video with caption\n• Document with caption\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    return COMPOSE_MSG


async def compose_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = update.effective_user.id

    media_type = None
    media_path = None
    text = ""

    if msg.photo:
        media_type = "photo"
        file = await msg.photo[-1].get_file()
        media_path = os.path.join(MEDIA_DIR, f"{user_id}_{msg.message_id}.jpg")
        os.makedirs(MEDIA_DIR, exist_ok=True)
        await file.download_to_drive(media_path)
        text = msg.caption or ""
    elif msg.video:
        media_type = "video"
        file = await msg.video.get_file()
        ext = msg.video.file_name.split(".")[-1] if msg.video.file_name else "mp4"
        media_path = os.path.join(MEDIA_DIR, f"{user_id}_{msg.message_id}.{ext}")
        os.makedirs(MEDIA_DIR, exist_ok=True)
        await file.download_to_drive(media_path)
        text = msg.caption or ""
    elif msg.document:
        media_type = "document"
        file = await msg.document.get_file()
        fname = msg.document.file_name or f"{user_id}_{msg.message_id}"
        media_path = os.path.join(MEDIA_DIR, fname)
        os.makedirs(MEDIA_DIR, exist_ok=True)
        await file.download_to_drive(media_path)
        text = msg.caption or ""
    elif msg.animation:
        media_type = "animation"
        file = await msg.animation.get_file()
        media_path = os.path.join(MEDIA_DIR, f"{user_id}_{msg.message_id}.gif")
        os.makedirs(MEDIA_DIR, exist_ok=True)
        await file.download_to_drive(media_path)
        text = msg.caption or ""
    elif msg.text:
        text = msg.text
    else:
        await msg.reply_text("❌ Unsupported message type. Send text, photo, video, or document.")
        return COMPOSE_MSG

    if not text and not media_path:
        await msg.reply_text("❌ Please send a message with some content.")
        return COMPOSE_MSG

    context.user_data["camp_text"] = text
    context.user_data["camp_media_type"] = media_type
    context.user_data["camp_media_path"] = media_path

    preview = f"📢 <b>Campaign Preview</b>\n\n"
    preview += f"📝 <b>Message:</b>\n<i>{text[:300]}{'...' if len(text) > 300 else ''}</i>\n"
    if media_type:
        preview += f"📎 <b>Media:</b> {media_type}\n"
    preview += "\nConfirm to start broadcasting to all groups."

    await msg.reply_text(preview, parse_mode="HTML", reply_markup=campaign_confirm_kb())
    return CONFIRM


async def confirm_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "cc:cancel":
        await query.edit_message_text("❌ Campaign cancelled.", reply_markup=main_menu_kb())
        return ConversationHandler.END

    if data == "cc:edit":
        await query.edit_message_text("📝 Send your updated ad message:")
        return COMPOSE_MSG

    if data == "cc:yes":
        account_id = context.user_data.get("camp_account_id")
        text = context.user_data.get("camp_text", "")
        media_type = context.user_data.get("camp_media_type")
        media_path = context.user_data.get("camp_media_path")

        campaign_id = await db.create_campaign(
            owner_id=user_id, account_id=account_id, message_text=text,
            media_type=media_type, media_path=media_path,
            delay_min=DEFAULT_DELAY_MIN, delay_max=DEFAULT_DELAY_MAX,
        )

        await query.edit_message_text(
            f"✅ Campaign #{campaign_id} created!\n\n⏳ Fetching groups and starting broadcast..."
        )
        await campaign_engine.start_campaign(campaign_id)
        return ConversationHandler.END

    return CONFIRM


async def cancel_campaign_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Campaign creation cancelled.", reply_markup=main_menu_kb())
    return ConversationHandler.END


campaign_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(new_campaign_entry, pattern=r"^c:new$")],
    states={
        SELECT_ACCOUNT: [CallbackQueryHandler(select_account, pattern=r"^(cs:\d+|m:camp)$")],
        COMPOSE_MSG: [
            MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.ANIMATION) & ~filters.COMMAND,
                compose_message,
            ),
        ],
        CONFIRM: [CallbackQueryHandler(confirm_campaign, pattern=r"^cc:")],
    },
    fallbacks=[MessageHandler(filters.Regex(r"^/cancel$"), cancel_campaign_creation)],
    per_chat=True,
    per_user=True,
    per_message=False,
)
