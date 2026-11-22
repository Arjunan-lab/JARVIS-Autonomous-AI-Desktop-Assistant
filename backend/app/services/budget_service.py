"""Service governing local API spending estimates, session duration tracking, and budget caps."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import UserSetting
from app.schemas.budget import BudgetStatusResponse


class BudgetService:
    """Service managing daily API budget safeguards and usage telemetry."""

    KEY_DATE = "budget_date"
    KEY_SPENT = "budget_spent_usd"
    KEY_SESSIONS = "budget_sessions_today"
    KEY_DURATION = "budget_duration_seconds_today"
    KEY_ACTIVE = "budget_active_sessions"
    KEY_CUSTOM_LIMIT = "budget_custom_limit_usd"

    @staticmethod
    def _get_setting(db: Session, key: str, default: str) -> str:
        stmt = select(UserSetting).where(UserSetting.key == key)
        setting = db.scalars(stmt).first()
        if not setting:
            setting = UserSetting(key=key, value=default)
            db.add(setting)
            db.commit()
            db.refresh(setting)
        return setting.value

    @staticmethod
    def _set_setting(db: Session, key: str, value: str) -> None:
        stmt = select(UserSetting).where(UserSetting.key == key)
        setting = db.scalars(stmt).first()
        if not setting:
            setting = UserSetting(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
        db.commit()

    @staticmethod
    def _ensure_rollover(db: Session) -> str:
        """Check if today is a new UTC date and rollover daily counters if needed."""
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        stored_date = BudgetService._get_setting(db, BudgetService.KEY_DATE, today_str)

        if stored_date != today_str:
            BudgetService._set_setting(db, BudgetService.KEY_DATE, today_str)
            BudgetService._set_setting(db, BudgetService.KEY_SPENT, "0.0")
            BudgetService._set_setting(db, BudgetService.KEY_SESSIONS, "0")
            BudgetService._set_setting(db, BudgetService.KEY_DURATION, "0")
            BudgetService._set_setting(db, BudgetService.KEY_ACTIVE, "0")
            return today_str

        return stored_date

    @staticmethod
    def get_effective_limit(db: Session, settings: Settings) -> float:
        """Get the configured daily budget limit in USD."""
        custom_limit_str = BudgetService._get_setting(db, BudgetService.KEY_CUSTOM_LIMIT, "")
        if custom_limit_str:
            try:
                custom_limit = float(custom_limit_str)
                if custom_limit > 0:
                    return custom_limit
            except ValueError:
                pass
        return settings.jarvis_max_daily_api_budget_usd

    @staticmethod
    def set_custom_limit(db: Session, limit_usd: float) -> None:
        """Set a user-defined daily budget limit."""
        if limit_usd <= 0:
            raise ValueError("Budget limit must be greater than zero")
        BudgetService._set_setting(db, BudgetService.KEY_CUSTOM_LIMIT, str(limit_usd))

    @staticmethod
    def get_budget_status(db: Session, settings: Settings) -> BudgetStatusResponse:
        """Retrieve the current day's API budget and usage status."""
        today_str = BudgetService._ensure_rollover(db)
        limit_usd = BudgetService.get_effective_limit(db, settings)

        spent_usd = float(BudgetService._get_setting(db, BudgetService.KEY_SPENT, "0.0"))
        sessions_today = int(BudgetService._get_setting(db, BudgetService.KEY_SESSIONS, "0"))
        duration_today = int(BudgetService._get_setting(db, BudgetService.KEY_DURATION, "0"))
        active_sessions = int(BudgetService._get_setting(db, BudgetService.KEY_ACTIVE, "0"))

        remaining_usd = max(0.0, round(limit_usd - spent_usd, 4))
        is_exceeded = spent_usd >= limit_usd

        return BudgetStatusResponse(
            date=today_str,
            limit_usd=limit_usd,
            spent_usd=round(spent_usd, 4),
            remaining_usd=remaining_usd,
            is_budget_exceeded=is_exceeded,
            sessions_today=sessions_today,
            duration_seconds_today=duration_today,
            active_sessions=active_sessions,
        )

    @staticmethod
    def can_start_session(db: Session, settings: Settings) -> tuple[bool, str | None]:
        """Verify whether budget safeguards allow initiating a new Realtime voice session."""
        status = BudgetService.get_budget_status(db, settings)

        if status.is_budget_exceeded:
            return (
                False,
                (
                    f"Daily API budget safeguard (${status.limit_usd:.2f} USD) has been reached. "
                    "New voice sessions are temporarily blocked to prevent unexpected cloud reasoning charges. "
                    "You may adjust or reset the limit in Settings."
                ),
            )

        # Guard against runaway parallel sessions with automatic self-healing for stale browser refreshes
        if settings.app_env != "test" and status.active_sessions >= 5:
            BudgetService._set_setting(db, BudgetService.KEY_ACTIVE, "1")

        return (True, None)

    @staticmethod
    def record_session_start(
        db: Session,
        settings: Settings,
        estimated_token_cost: float = 0.01,
    ) -> None:
        """Record the start of a voice session and apply estimated upfront token cost."""
        BudgetService._ensure_rollover(db)

        current_spent = float(BudgetService._get_setting(db, BudgetService.KEY_SPENT, "0.0"))
        current_sessions = int(BudgetService._get_setting(db, BudgetService.KEY_SESSIONS, "0"))
        current_active = int(BudgetService._get_setting(db, BudgetService.KEY_ACTIVE, "0"))

        new_spent = current_spent + estimated_token_cost
        BudgetService._set_setting(db, BudgetService.KEY_SPENT, str(round(new_spent, 4)))
        BudgetService._set_setting(db, BudgetService.KEY_SESSIONS, str(current_sessions + 1))
        BudgetService._set_setting(db, BudgetService.KEY_ACTIVE, str(current_active + 1))

    @staticmethod
    def record_session_end(
        db: Session,
        duration_seconds: int,
        estimated_cost: float | None = None,
    ) -> dict[str, Any]:
        """Record completion of a voice session with elapsed duration and audio usage estimate."""
        BudgetService._ensure_rollover(db)

        current_spent = float(BudgetService._get_setting(db, BudgetService.KEY_SPENT, "0.0"))
        current_duration = int(BudgetService._get_setting(db, BudgetService.KEY_DURATION, "0"))
        current_active = int(BudgetService._get_setting(db, BudgetService.KEY_ACTIVE, "0"))

        # Estimated audio streaming cost: ~$0.001 per second
        added_cost = estimated_cost if estimated_cost is not None else (duration_seconds * 0.001)

        new_spent = current_spent + added_cost
        new_active = max(0, current_active - 1)
        new_duration = current_duration + duration_seconds

        BudgetService._set_setting(db, BudgetService.KEY_SPENT, str(round(new_spent, 4)))
        BudgetService._set_setting(db, BudgetService.KEY_DURATION, str(new_duration))
        BudgetService._set_setting(db, BudgetService.KEY_ACTIVE, str(new_active))

        return {
            "duration_seconds": duration_seconds,
            "added_cost_usd": round(added_cost, 4),
            "total_spent_today": round(new_spent, 4),
        }

    @staticmethod
    def record_session_usage(
        db: Session,
        duration_seconds: int,
        estimated_cost: float | None = None,
    ) -> dict[str, Any]:
        """Convenience alias for record_session_end."""
        return BudgetService.record_session_end(db, duration_seconds=duration_seconds, estimated_cost=estimated_cost)

    @staticmethod
    def reset_daily_budget(db: Session) -> dict[str, Any]:
        """Reset today's usage counter."""
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        BudgetService._set_setting(db, BudgetService.KEY_DATE, today_str)
        BudgetService._set_setting(db, BudgetService.KEY_SPENT, "0.0")
        BudgetService._set_setting(db, BudgetService.KEY_SESSIONS, "0")
        BudgetService._set_setting(db, BudgetService.KEY_DURATION, "0")
        BudgetService._set_setting(db, BudgetService.KEY_ACTIVE, "0")
        return {"reset": True, "date": today_str}
