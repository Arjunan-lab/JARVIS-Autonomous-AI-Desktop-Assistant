"""Safe mouse input service scoped to validated UI controls."""

import logging
import sys

from app.core.config import Settings, get_settings
from app.services.automation.automation_errors import ControlInteractionError
from app.services.automation.automation_models import UIControlInfo, WindowInfo

logger = logging.getLogger(__name__)


class MouseInputService:
    """Performs pointer interactions scoped strictly to validated UI element boundaries."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._is_windows = sys.platform == "win32"

    def click_control(self, window: WindowInfo, control: UIControlInfo) -> bool:
        """Click in the center of an identifiable control's validated bounding box."""
        if self.settings.app_env in {"test", "staging"}:
            return True

        if not self._is_windows:
            raise ControlInteractionError("Mouse actions require Windows.")

        rect = control.rect
        center_x = (rect["left"] + rect["right"]) // 2
        center_y = (rect["top"] + rect["bottom"]) // 2

        # Verify center point is within window boundaries
        win_rect = window.rect
        if not (win_rect["left"] <= center_x <= win_rect["right"] and win_rect["top"] <= center_y <= win_rect["bottom"]):
            raise ControlInteractionError(
                f"Control '{control.name}' coordinate ({center_x}, {center_y}) is outside window bounds."
            )

        try:
            from pywinauto import mouse
            mouse.click(coords=(center_x, center_y))
            return True
        except Exception as e:
            raise ControlInteractionError(f"Failed to click control at ({center_x}, {center_y}): {e}") from e
