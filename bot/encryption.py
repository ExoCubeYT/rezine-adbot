import os
from cryptography.fernet import Fernet
from bot.config import ENCRYPTION_KEY

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet

    key = ENCRYPTION_KEY
    if not key:
        key = Fernet.generate_key().decode()
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"ENCRYPTION_KEY={key}\n")
        os.environ["ENCRYPTION_KEY"] = key

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_session(session_string):
    return _get_fernet().encrypt(session_string.encode()).decode()


def decrypt_session(encrypted):
    return _get_fernet().decrypt(encrypted.encode()).decode()
