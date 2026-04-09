import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from bot.config import BOT_TOKEN
from bot.database import init_db
from bot.handlers.start import start_command, menu_callback
from bot.handlers.accounts import account_conv_handler, accounts_callback
from bot.handlers.campaigns import campaign_conv_handler, campaigns_callback
from bot.handlers.admin import (
    admin_command,
    admin_callback,
    admin_broadcast_conv_handler,
)
from bot.services.campaign_engine import campaign_engine

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("telethon").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def post_init(app):
    logger.info("Initializing database...")
    await init_db()

    logger.info("Setting up campaign engine...")
    campaign_engine.set_app(app)
    await campaign_engine.resume_all()

    logger.info("AdBot is ready!")


async def post_shutdown(app):
    from bot.services.telethon_manager import telethon_mgr
    await telethon_mgr.disconnect_all()
    logger.info("Bot shut down cleanly.")


def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN not set. Check your .env file.")
        sys.exit(1)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(account_conv_handler)
    app.add_handler(campaign_conv_handler)
    app.add_handler(admin_broadcast_conv_handler)

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))

    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^m:"))
    app.add_handler(CallbackQueryHandler(accounts_callback, pattern=r"^a:"))
    app.add_handler(CallbackQueryHandler(campaigns_callback, pattern=r"^c:"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^ad:"))

    logger.info("Starting AdBot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
