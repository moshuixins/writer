from __future__ import annotations

from app.schemas.common import ApiModel


class PreferencesResponse(ApiModel):
    signature_org: str = ""
    default_tone: str = "formal"
    default_recipients: str = ""
    avoid_phrases: str = ""
