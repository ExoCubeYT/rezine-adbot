from __future__ import annotations
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.models import Account, Campaign


def _btn(text, data):
    return InlineKeyboardButton(text, callback_data=data)


def _back(target="m:main"):
    return [_btn("🔙 Back", target)]


def mask_phone(phone):
    if len(phone) <= 6:
        return phone
    return phone[:3] + "****" + phone[-4:]


def main_menu_kb():
    return InlineKeyboardMarkup([
        [_btn("📱 My Accounts", "m:acc"), _btn("📢 Campaigns", "m:camp")],
        [_btn("ℹ️ Help", "m:help")],
    ])


def accounts_menu_kb(accounts):
    rows = []
    for acc in accounts:
        label = mask_phone(acc.phone)
        if acc.display_name:
            label = f"{acc.display_name} ({mask_phone(acc.phone)})"
        rows.append([_btn(f"✅ {label}", f"a:{acc.id}")])
    rows.append([_btn("➕ Add Account", "a:add")])
    rows.append(_back())
    return InlineKeyboardMarkup(rows)


def account_detail_kb(account_id):
    return InlineKeyboardMarkup([
        [_btn("📋 View Groups", f"a:grp:{account_id}")],
        [_btn("🗑 Disconnect", f"a:del:{account_id}")],
        _back("m:acc"),
    ])


def account_confirm_delete_kb(account_id):
    return InlineKeyboardMarkup([
        [_btn("✅ Yes, disconnect", f"a:cdel:{account_id}"), _btn("❌ Cancel", "m:acc")],
    ])


def campaigns_menu_kb(campaigns):
    STATUS_ICON = {"draft": "📝", "running": "▶️", "paused": "⏸", "completed": "✅", "failed": "❌"}
    rows = []
    for c in campaigns[:10]:
        icon = STATUS_ICON.get(c.status, "❓")
        label = f"{icon} #{c.id} — {c.status.title()} ({c.sent_count}/{c.total_groups})"
        rows.append([_btn(label, f"c:{c.id}")])
    rows.append([_btn("📝 New Campaign", "c:new")])
    rows.append(_back())
    return InlineKeyboardMarkup(rows)


def campaign_select_account_kb(accounts):
    rows = []
    for acc in accounts:
        label = mask_phone(acc.phone)
        if acc.display_name:
            label = f"{acc.display_name} ({label})"
        rows.append([_btn(f"📱 {label}", f"cs:{acc.id}")])
    rows.append(_back("m:camp"))
    return InlineKeyboardMarkup(rows)


def campaign_confirm_kb():
    return InlineKeyboardMarkup([
        [_btn("✅ Start Campaign", "cc:yes"), _btn("✏️ Edit", "cc:edit")],
        [_btn("❌ Cancel", "cc:cancel")],
    ])


def campaign_detail_kb(campaign):
    rows = []
    if campaign.status in ("draft", "paused"):
        rows.append([_btn("▶️ Start / Resume", f"c:run:{campaign.id}")])
    if campaign.status == "running":
        rows.append([_btn("⏸ Pause", f"c:pause:{campaign.id}")])
    if campaign.status in ("draft", "paused", "running"):
        rows.append([_btn("❌ Cancel Campaign", f"c:stop:{campaign.id}")])
    if campaign.status in ("completed", "failed"):
        rows.append([_btn("🗑 Delete", f"c:del:{campaign.id}")])
    rows.append(_back("m:camp"))
    return InlineKeyboardMarkup(rows)


def admin_panel_kb():
    return InlineKeyboardMarkup([
        [_btn("👥 Users", "ad:users")],
        [_btn("📊 Statistics", "ad:stats"), _btn("📣 Broadcast", "ad:bc")],
        [_btn("🔙 Main Menu", "m:main")],
    ])


def admin_users_kb(users, page=0, page_size=8):
    rows = []
    for u in users:
        ban_icon = "🚫" if u.is_banned else ""
        name = u.username or str(u.telegram_id)
        rows.append([_btn(f"{ban_icon} {name}", f"ad:u:{u.telegram_id}")])
    nav = []
    if page > 0:
        nav.append(_btn("⬅️ Prev", f"ad:users:{page - 1}"))
    nav.append(_btn(f"Page {page + 1}", "ad:noop"))
    nav.append(_btn("➡️ Next", f"ad:users:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([_btn("🔙 Admin", "ad:panel")])
    return InlineKeyboardMarkup(rows)


def admin_user_detail_kb(user_id, is_banned):
    rows = []
    if is_banned:
        rows.append([_btn("✅ Unban", f"ad:uban:{user_id}")])
    else:
        rows.append([_btn("🚫 Ban", f"ad:ban:{user_id}")])
    rows.append([_btn("🔙 Users", "ad:users")])
    return InlineKeyboardMarkup(rows)
