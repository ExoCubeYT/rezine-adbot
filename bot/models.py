from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    telegram_id: int
    username: Optional[str] = None
    is_banned: bool = False
    created_at: Optional[datetime] = None


@dataclass
class Account:
    id: int = 0
    owner_id: int = 0
    phone: str = ""
    session_string: str = ""
    display_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class Campaign:
    id: int = 0
    owner_id: int = 0
    account_id: int = 0
    message_text: str = ""
    message_media_type: Optional[str] = None
    message_media_path: Optional[str] = None
    status: str = "draft"
    total_groups: int = 0
    sent_count: int = 0
    failed_count: int = 0
    delay_min: float = 3.0
    delay_max: float = 8.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CampaignLog:
    id: int = 0
    campaign_id: int = 0
    group_id: int = 0
    group_title: str = ""
    status: str = "pending"
    error: Optional[str] = None
    sent_at: Optional[datetime] = None
