import asyncio
import logging
import os

from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    ChannelPrivateError,
    UserBannedInChannelError,
    SlowModeWaitError,
    ChatAdminRequiredError,
    PeerIdInvalidError,
)

from bot import database as db
from bot.config import FLOOD_WAIT_BUFFER
from bot.services.telethon_manager import telethon_mgr
from bot.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

SKIP_ERRORS = (
    ChatWriteForbiddenError,
    ChannelPrivateError,
    UserBannedInChannelError,
    ChatAdminRequiredError,
    PeerIdInvalidError,
    ValueError,
)


class CampaignEngine:
    def __init__(self):
        self._tasks = {}
        self._app = None

    def set_app(self, app):
        self._app = app

    async def start_campaign(self, campaign_id):
        if campaign_id in self._tasks and not self._tasks[campaign_id].done():
            return

        campaign = await db.get_campaign(campaign_id)
        if not campaign:
            return

        if campaign.status == "draft":
            account = await db.get_account(campaign.account_id)
            if not account:
                await db.update_campaign(campaign_id, status="failed")
                return

            try:
                groups = await telethon_mgr.get_groups(account.id, account.session_string)
            except Exception as e:
                logger.error("Failed to fetch groups for campaign %d: %s", campaign_id, e)
                await db.update_campaign(campaign_id, status="failed")
                await self._notify(campaign.owner_id, f"❌ Campaign #{campaign_id} failed: {e}")
                return

            if not groups:
                await db.update_campaign(campaign_id, status="failed")
                await self._notify(campaign.owner_id, f"❌ Campaign #{campaign_id}: No groups found for this account.")
                return

            await db.clear_campaign_log(campaign_id)
            await db.add_campaign_log_entries(campaign_id, groups)
            await db.update_campaign(campaign_id, total_groups=len(groups), status="running")
        else:
            await db.update_campaign(campaign_id, status="running")

        task = asyncio.create_task(self._run(campaign_id))
        self._tasks[campaign_id] = task
        task.add_done_callback(lambda t: self._tasks.pop(campaign_id, None))

    async def pause_campaign(self, campaign_id):
        task = self._tasks.get(campaign_id)
        if task and not task.done():
            task.cancel()
        await db.update_campaign(campaign_id, status="paused")
        campaign = await db.get_campaign(campaign_id)
        if campaign:
            await self._notify(campaign.owner_id, f"⏸ Campaign #{campaign_id} paused.")

    async def stop_campaign(self, campaign_id):
        task = self._tasks.get(campaign_id)
        if task and not task.done():
            task.cancel()
        await db.update_campaign(campaign_id, status="failed")
        campaign = await db.get_campaign(campaign_id)
        if campaign:
            await self._notify(campaign.owner_id, f"❌ Campaign #{campaign_id} cancelled.")

    async def resume_all(self):
        campaigns = await db.get_resumable_campaigns()
        for c in campaigns:
            logger.info("Resuming campaign %d (was %s)", c.id, c.status)
            await db.update_campaign(c.id, status="running")
            task = asyncio.create_task(self._run(c.id))
            self._tasks[c.id] = task
            task.add_done_callback(lambda t, cid=c.id: self._tasks.pop(cid, None))

    def is_running(self, campaign_id):
        task = self._tasks.get(campaign_id)
        return task is not None and not task.done()

    async def _run(self, campaign_id):
        campaign = await db.get_campaign(campaign_id)
        if not campaign:
            return

        account = await db.get_account(campaign.account_id)
        if not account:
            await db.update_campaign(campaign_id, status="failed")
            await self._notify(campaign.owner_id, f"❌ Campaign #{campaign_id}: Account not found.")
            return

        try:
            client = await telethon_mgr.get_client(account.id, account.session_string)
        except Exception as e:
            await db.update_campaign(campaign_id, status="failed")
            await self._notify(campaign.owner_id, f"❌ Campaign #{campaign_id}: {e}")
            return

        sent = campaign.sent_count
        failed = campaign.failed_count

        try:
            while True:
                pending = await db.get_pending_log_entries(campaign_id)
                if not pending:
                    break

                for entry in pending:
                    fresh = await db.get_campaign(campaign_id)
                    if not fresh or fresh.status != "running":
                        return

                    try:
                        if campaign.message_media_path and os.path.exists(campaign.message_media_path):
                            await client.send_file(
                                entry.group_id,
                                campaign.message_media_path,
                                caption=campaign.message_text,
                            )
                        else:
                            await client.send_message(entry.group_id, campaign.message_text)

                        await db.update_log_entry(entry.id, "sent")
                        sent += 1
                        rate_limiter.reset_flood(account.id)

                    except FloodWaitError as e:
                        rate_limiter.record_flood(account.id)
                        wait_time = e.seconds + FLOOD_WAIT_BUFFER
                        logger.warning("FloodWait %ds on campaign %d", e.seconds, campaign_id)
                        await db.update_campaign(campaign_id, status="paused", sent_count=sent, failed_count=failed)
                        await self._notify(
                            campaign.owner_id,
                            f"⏸ Campaign #{campaign_id} auto-paused (flood wait {e.seconds}s). Resuming in {wait_time}s…",
                        )
                        await asyncio.sleep(wait_time)
                        await db.update_campaign(campaign_id, status="running")
                        await self._notify(campaign.owner_id, f"▶️ Campaign #{campaign_id} resumed.")
                        continue

                    except SlowModeWaitError as e:
                        await db.update_log_entry(entry.id, "skipped", f"Slow mode: {e.seconds}s")
                        failed += 1

                    except SKIP_ERRORS as e:
                        await db.update_log_entry(entry.id, "skipped", str(e)[:200])
                        failed += 1

                    except Exception as e:
                        logger.error("Send error campaign %d group %d: %s", campaign_id, entry.group_id, e)
                        await db.update_log_entry(entry.id, "failed", str(e)[:200])
                        failed += 1

                    await db.update_campaign(campaign_id, sent_count=sent, failed_count=failed)

                    if (sent + failed) % 10 == 0:
                        total = campaign.total_groups
                        pct = int((sent + failed) / total * 100) if total else 0
                        await self._notify(
                            campaign.owner_id,
                            f"📢 Campaign #{campaign_id}: {sent + failed}/{total} ({pct}%) — ✅ {sent} sent, ❌ {failed} failed",
                        )

                    await rate_limiter.wait(account.id, campaign.delay_min, campaign.delay_max)

        except asyncio.CancelledError:
            await db.update_campaign(campaign_id, sent_count=sent, failed_count=failed)
            return
        except Exception as e:
            logger.error("Campaign %d crashed: %s", campaign_id, e)
            await db.update_campaign(campaign_id, status="failed", sent_count=sent, failed_count=failed)
            await self._notify(campaign.owner_id, f"❌ Campaign #{campaign_id} failed: {e}")
            return

        await db.update_campaign(campaign_id, status="completed", sent_count=sent, failed_count=failed)
        await telethon_mgr.disconnect_client(account.id)
        await self._notify(
            campaign.owner_id,
            f"✅ Campaign #{campaign_id} completed!\n📊 Results: ✅ {sent} sent, ❌ {failed} failed out of {campaign.total_groups} groups.",
        )

    async def _notify(self, user_id, text):
        if not self._app:
            return
        try:
            await self._app.bot.send_message(chat_id=user_id, text=text)
        except Exception:
            pass


campaign_engine = CampaignEngine()
