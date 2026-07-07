"""Aggregate all v1 route modules into a single router."""

from fastapi import APIRouter

from app.api.v1 import auth, digest, kudos, pulse, reports, standup, users

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(pulse.router, prefix="/pulse", tags=["pulse"])
api_v1_router.include_router(standup.router, prefix="/standup", tags=["standup"])
api_v1_router.include_router(kudos.router, prefix="/kudos", tags=["kudos"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(digest.router, prefix="/digest", tags=["digest"])
api_v1_router.include_router(reports.router, prefix="/reports", tags=["reports"])
