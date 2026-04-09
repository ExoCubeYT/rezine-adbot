from __future__ import annotations
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List

from bot.config import DB_PATH, ensure_dirs
from bot.models import User, Account, Campaign, CampaignLog

_db = None


async def get_db():
    global _db
    if _db is None:
        ensure_dirs()
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def init_db():
    db = await get_db()
    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id   INTEGER PRIMARY KEY,
            username      TEXT,
            is_banned     INTEGER DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id        INTEGER REFERENCES users(telegram_id),
            phone           TEXT NOT NULL,
            session_string  TEXT NOT NULL,
            display_name    TEXT,
            is_active       INTEGER DEFAULT 1,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS campaigns (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id        INTEGER REFERENCES users(telegram_id),
            account_id      INTEGER REFERENCES accounts(id),
            message_text    TEXT NOT NULL,
            message_media_type TEXT,
            message_media_path TEXT,
            status          TEXT DEFAULT 'draft',
            total_groups    INTEGER DEFAULT 0,
            sent_count      INTEGER DEFAULT 0,
            failed_count    INTEGER DEFAULT 0,
            delay_min       REAL DEFAULT 3.0,
            delay_max       REAL DEFAULT 8.0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS campaign_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id  INTEGER REFERENCES campaigns(id),
            group_id     INTEGER NOT NULL,
            group_title  TEXT,
            status       TEXT DEFAULT 'pending',
            error        TEXT,
            sent_at      TIMESTAMP
        );
        """
    )
    await db.commit()


async def get_or_create_user(telegram_id, username=None):
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
        if row:
            return _row_to_user(row)
    await db.execute("INSERT INTO users (telegram_id, username) VALUES (?, ?)", (telegram_id, username))
    await db.commit()
    return User(telegram_id=telegram_id, username=username)


async def get_user(telegram_id):
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
        row = await cur.fetchone()
        return _row_to_user(row) if row else None


async def set_user_ban(telegram_id, banned):
    db = await get_db()
    await db.execute("UPDATE users SET is_banned = ? WHERE telegram_id = ?", (int(banned), telegram_id))
    await db.commit()


async def get_all_users(limit=50, offset=0):
    db = await get_db()
    async with db.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)) as cur:
        return [_row_to_user(r) for r in await cur.fetchall()]


async def count_users():
    db = await get_db()
    async with db.execute("SELECT COUNT(*) FROM users") as cur:
        return (await cur.fetchone())[0]


def _row_to_user(row):
    return User(
        telegram_id=row["telegram_id"], username=row["username"],
        is_banned=bool(row["is_banned"]), created_at=row["created_at"],
    )


async def add_account(owner_id, phone, session_string, display_name=""):
    db = await get_db()
    cur = await db.execute(
        "INSERT INTO accounts (owner_id, phone, session_string, display_name) VALUES (?, ?, ?, ?)",
        (owner_id, phone, session_string, display_name),
    )
    await db.commit()
    return cur.lastrowid


async def get_accounts(owner_id):
    db = await get_db()
    async with db.execute("SELECT * FROM accounts WHERE owner_id = ? AND is_active = 1", (owner_id,)) as cur:
        return [_row_to_account(r) for r in await cur.fetchall()]


async def get_account(account_id):
    db = await get_db()
    async with db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)) as cur:
        row = await cur.fetchone()
        return _row_to_account(row) if row else None


async def deactivate_account(account_id):
    db = await get_db()
    await db.execute("UPDATE accounts SET is_active = 0 WHERE id = ?", (account_id,))
    await db.commit()


async def count_accounts(owner_id):
    db = await get_db()
    async with db.execute("SELECT COUNT(*) FROM accounts WHERE owner_id = ? AND is_active = 1", (owner_id,)) as cur:
        return (await cur.fetchone())[0]


async def count_all_accounts():
    db = await get_db()
    async with db.execute("SELECT COUNT(*) FROM accounts WHERE is_active = 1") as cur:
        return (await cur.fetchone())[0]


def _row_to_account(row):
    return Account(
        id=row["id"], owner_id=row["owner_id"], phone=row["phone"],
        session_string=row["session_string"], display_name=row["display_name"],
        is_active=bool(row["is_active"]), created_at=row["created_at"],
    )


async def create_campaign(owner_id, account_id, message_text,
                          media_type=None, media_path=None, delay_min=3.0, delay_max=8.0):
    db = await get_db()
    cur = await db.execute(
        "INSERT INTO campaigns (owner_id, account_id, message_text, message_media_type, message_media_path, delay_min, delay_max) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (owner_id, account_id, message_text, media_type, media_path, delay_min, delay_max),
    )
    await db.commit()
    return cur.lastrowid


async def get_campaign(campaign_id):
    db = await get_db()
    async with db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)) as cur:
        row = await cur.fetchone()
        return _row_to_campaign(row) if row else None


async def get_campaigns(owner_id):
    db = await get_db()
    async with db.execute("SELECT * FROM campaigns WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,)) as cur:
        return [_row_to_campaign(r) for r in await cur.fetchall()]


async def update_campaign(campaign_id, **kwargs):
    db = await get_db()
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [campaign_id]
    await db.execute(f"UPDATE campaigns SET {sets} WHERE id = ?", vals)
    await db.commit()


async def delete_campaign(campaign_id):
    db = await get_db()
    await db.execute("DELETE FROM campaign_log WHERE campaign_id = ?", (campaign_id,))
    await db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    await db.commit()


async def get_resumable_campaigns():
    db = await get_db()
    async with db.execute("SELECT * FROM campaigns WHERE status IN ('running', 'paused')") as cur:
        return [_row_to_campaign(r) for r in await cur.fetchall()]


async def count_active_campaigns(owner_id):
    db = await get_db()
    async with db.execute(
        "SELECT COUNT(*) FROM campaigns WHERE owner_id = ? AND status IN ('draft', 'running', 'paused')",
        (owner_id,),
    ) as cur:
        return (await cur.fetchone())[0]


async def count_all_campaigns():
    db = await get_db()
    async with db.execute("SELECT COUNT(*) FROM campaigns") as cur:
        return (await cur.fetchone())[0]


def _row_to_campaign(row):
    return Campaign(
        id=row["id"], owner_id=row["owner_id"], account_id=row["account_id"],
        message_text=row["message_text"], message_media_type=row["message_media_type"],
        message_media_path=row["message_media_path"], status=row["status"],
        total_groups=row["total_groups"], sent_count=row["sent_count"],
        failed_count=row["failed_count"], delay_min=row["delay_min"],
        delay_max=row["delay_max"], created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def add_campaign_log_entries(campaign_id, groups):
    db = await get_db()
    await db.executemany(
        "INSERT INTO campaign_log (campaign_id, group_id, group_title) VALUES (?, ?, ?)",
        [(campaign_id, gid, title) for gid, title in groups],
    )
    await db.commit()


async def get_pending_log_entries(campaign_id):
    db = await get_db()
    async with db.execute(
        "SELECT * FROM campaign_log WHERE campaign_id = ? AND status = 'pending' ORDER BY id",
        (campaign_id,),
    ) as cur:
        return [_row_to_log(r) for r in await cur.fetchall()]


async def update_log_entry(entry_id, status, error=None):
    db = await get_db()
    await db.execute(
        "UPDATE campaign_log SET status = ?, error = ?, sent_at = ? WHERE id = ?",
        (status, error, datetime.utcnow().isoformat() if status == "sent" else None, entry_id),
    )
    await db.commit()


async def count_log_entries(campaign_id, status=None):
    db = await get_db()
    if status:
        query = "SELECT COUNT(*) FROM campaign_log WHERE campaign_id = ? AND status = ?"
        params = (campaign_id, status)
    else:
        query = "SELECT COUNT(*) FROM campaign_log WHERE campaign_id = ?"
        params = (campaign_id,)
    async with db.execute(query, params) as cur:
        return (await cur.fetchone())[0]


async def clear_campaign_log(campaign_id):
    db = await get_db()
    await db.execute("DELETE FROM campaign_log WHERE campaign_id = ?", (campaign_id,))
    await db.commit()


def _row_to_log(row):
    return CampaignLog(
        id=row["id"], campaign_id=row["campaign_id"],
        group_id=row["group_id"], group_title=row["group_title"],
        status=row["status"], error=row["error"], sent_at=row["sent_at"],
    )
