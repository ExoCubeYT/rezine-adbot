import logging
from typing import List, Tuple

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
    FloodWaitError,
    PhoneNumberBannedError,
)
from telethon.tl.types import Channel, Chat

from bot.config import API_ID, API_HASH
from bot.encryption import encrypt_session, decrypt_session

logger = logging.getLogger(__name__)


class LoginError(Exception):
    pass


class TelethonManager:
    def __init__(self):
        self._clients = {}
        self._login_state = {}

    async def start_login(self, user_id, phone):
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()

        try:
            sent = await client.send_code_request(phone)
        except PhoneNumberInvalidError:
            await client.disconnect()
            raise LoginError("❌ Invalid phone number format. Use international format like +12345678901")
        except PhoneNumberBannedError:
            await client.disconnect()
            raise LoginError("❌ This phone number is banned by Telegram.")
        except FloodWaitError as e:
            await client.disconnect()
            raise LoginError(f"⏳ Too many attempts. Please wait {e.seconds} seconds.")
        except Exception as e:
            await client.disconnect()
            raise LoginError(f"❌ Error sending code: {e}")

        self._login_state[user_id] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent.phone_code_hash,
        }
        return "✅ OTP code sent! Check your Telegram app."

    async def submit_otp(self, user_id, code):
        state = self._login_state.get(user_id)
        if not state:
            raise LoginError("❌ No login in progress. Start again.")

        client = state["client"]
        try:
            await client.sign_in(
                phone=state["phone"],
                code=code,
                phone_code_hash=state["phone_code_hash"],
            )
        except PhoneCodeInvalidError:
            raise LoginError("❌ Invalid code. Please try again.")
        except PhoneCodeExpiredError:
            await client.disconnect()
            self._login_state.pop(user_id, None)
            raise LoginError("❌ Code expired. Please start over.")
        except SessionPasswordNeededError:
            return True, "🔐 This account has 2FA enabled. Please enter your password:"
        except FloodWaitError as e:
            raise LoginError(f"⏳ Too many attempts. Wait {e.seconds}s.")
        except Exception as e:
            raise LoginError(f"❌ Sign-in error: {e}")

        session_str = client.session.save()
        encrypted = encrypt_session(session_str)

        me = await client.get_me()
        display = me.first_name or ""
        if me.last_name:
            display += f" {me.last_name}"

        await client.disconnect()
        self._login_state.pop(user_id, None)
        return False, encrypted + "|||" + display

    async def submit_2fa(self, user_id, password):
        state = self._login_state.get(user_id)
        if not state:
            raise LoginError("❌ No login in progress.")

        client = state["client"]
        try:
            await client.sign_in(password=password)
        except PasswordHashInvalidError:
            raise LoginError("❌ Wrong password. Try again:")
        except FloodWaitError as e:
            raise LoginError(f"⏳ Too many attempts. Wait {e.seconds}s.")
        except Exception as e:
            raise LoginError(f"❌ 2FA error: {e}")

        session_str = client.session.save()
        encrypted = encrypt_session(session_str)

        me = await client.get_me()
        display = me.first_name or ""
        if me.last_name:
            display += f" {me.last_name}"

        await client.disconnect()
        self._login_state.pop(user_id, None)
        return encrypted + "|||" + display

    async def cancel_login(self, user_id):
        state = self._login_state.pop(user_id, None)
        if state and state.get("client"):
            try:
                await state["client"].disconnect()
            except Exception:
                pass

    async def get_client(self, account_id, session_encrypted):
        if account_id in self._clients:
            client = self._clients[account_id]
            if client.is_connected():
                return client

        session_str = decrypt_session(session_encrypted)
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            raise LoginError("❌ Session expired. Please re-link this account.")

        self._clients[account_id] = client
        return client

    async def disconnect_client(self, account_id):
        client = self._clients.pop(account_id, None)
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass

    async def get_groups(self, account_id, session_encrypted):
        client = await self.get_client(account_id, session_encrypted)
        groups = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, Channel) and entity.megagroup:
                groups.append((entity.id, dialog.title))
            elif isinstance(entity, Chat):
                groups.append((entity.id, dialog.title))
        return groups

    async def disconnect_all(self):
        for acc_id in list(self._clients.keys()):
            await self.disconnect_client(acc_id)


telethon_mgr = TelethonManager()
