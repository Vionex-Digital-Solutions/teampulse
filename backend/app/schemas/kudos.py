"""Kudos schemas."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class KudosCategory(str, Enum):
    """The reason a kudos is being given.

    Send the raw string value (e.g. ``"teamwork"``). Swagger renders these as a
    dropdown, so the frontend can populate a ``<select>`` directly from here.
    """

    TEAMWORK = "teamwork"
    INNOVATION = "innovation"
    MENTORSHIP = "mentorship"
    ABOVE_AND_BEYOND = "above_and_beyond"
    QUALITY = "quality"
    COMMUNICATION = "communication"


class KudosCreate(BaseModel):
    """Request body for sending a kudos.

    There is **no** ``sender_id`` here on purpose: the sender is always the
    authenticated user (taken from the JWT), never a client-supplied value.
    """

    receiver_id: uuid.UUID = Field(
        ...,
        description=(
            "ID of the teammate receiving the kudos. Must be an existing, active "
            "user, and cannot be your own ID (that returns 400)."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    category: KudosCategory = Field(
        ...,
        description="Why the kudos is being given. One of the fixed categories.",
        examples=["teamwork"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The recognition message, in English. 1–1000 characters.",
        examples=["Thanks for jumping in to unblock the deploy on Friday night!"],
    )
    message_ar: str | None = Field(
        default=None,
        max_length=1000,
        description=(
            "Optional Arabic translation of the message (max 1000 characters). "
            "Omit or send null if you only have the English version."
        ),
        examples=["شكراً لمساعدتك في حل مشكلة النشر يوم الجمعة!"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "receiver_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "category": "teamwork",
                    "message": (
                        "Thanks for jumping in to unblock the deploy on Friday "
                        "night!"
                    ),
                    "message_ar": "شكراً لمساعدتك في حل مشكلة النشر يوم الجمعة!",
                }
            ]
        }
    }


class KudosResponse(BaseModel):
    """A single kudos entry as returned by the API.

    Returned by ``POST /kudos`` (the entry you just created) and as list items
    by ``GET /kudos/feed``.
    """

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "b1e0c2a4-8f3d-4c1a-9b2e-1f4d6a7c8e90",
                    "sender_id": "9c8b7a6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
                    "receiver_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "category": "teamwork",
                    "message": (
                        "Thanks for jumping in to unblock the deploy on Friday "
                        "night!"
                    ),
                    "message_ar": "شكراً لمساعدتك في حل مشكلة النشر يوم الجمعة!",
                    "created_at": "2026-07-05T14:32:00Z",
                }
            ]
        },
    }

    id: uuid.UUID = Field(
        ...,
        description="Unique ID of this kudos entry.",
        examples=["b1e0c2a4-8f3d-4c1a-9b2e-1f4d6a7c8e90"],
    )
    sender_id: uuid.UUID = Field(
        ...,
        description="ID of the user who sent the kudos (the authenticated caller).",
        examples=["9c8b7a6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d"],
    )
    receiver_id: uuid.UUID = Field(
        ...,
        description="ID of the teammate who received the kudos.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    category: str = Field(
        ...,
        description="The category the kudos was filed under.",
        examples=["teamwork"],
    )
    message: str = Field(
        ...,
        description="The English recognition message.",
        examples=["Thanks for jumping in to unblock the deploy on Friday night!"],
    )
    message_ar: str | None = Field(
        default=None,
        description="Arabic translation, or null if none was provided.",
        examples=["شكراً لمساعدتك في حل مشكلة النشر يوم الجمعة!"],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp of when the kudos was created (ISO 8601).",
        examples=["2026-07-05T14:32:00Z"],
    )
