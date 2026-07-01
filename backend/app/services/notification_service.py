"""Notification service stub for future push/email notifications."""


class NotificationService:
    """Service for sending notifications to team members."""

    async def notify_kudos_received(self, receiver_id: str, sender_name: str) -> None:
        """Notify a user that they received kudos."""
        raise NotImplementedError("Sprint 3: implement kudos notification")

    async def send_standup_reminder(self, user_ids: list[str]) -> None:
        """Send a reminder to users who haven't submitted their standup."""
        raise NotImplementedError("Sprint 3: implement standup reminders")

    async def send_weekly_digest_email(self, user_id: str, digest: dict) -> None:
        """Send the weekly digest via email."""
        raise NotImplementedError("Sprint 4: implement email digest delivery")
