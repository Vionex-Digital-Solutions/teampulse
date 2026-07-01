"""Aggregate all v1 route modules into a single router."""

from fastapi import APIRouter

from app.api.v1 import digest, kudos, pulse, standup, users

api_v1_router = APIRouter()

api_v1_router.include_router(pulse.router, prefix="/pulse", tags=["pulse"])
api_v1_router.include_router(standup.router, prefix="/standup", tags=["standup"])
api_v1_router.include_router(kudos.router, prefix="/kudos", tags=["kudos"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(digest.router, prefix="/digest", tags=["digest"])
