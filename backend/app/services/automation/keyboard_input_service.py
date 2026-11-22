"""Safe keyboard input and validated shortcut service."""

import logging
import sys
import time

from app.core.config import Settings, get_settings
from app.services.automation.automation_errors import (
    ControlInteractionError,
    OperationPermissionDeniedError,
    WindowNotActiveError,
)
from app.services.automation.automation_models import WindowInfo

logger = logging.getLogger(__name__)

# Strictly allowlisted key combinations for productivity and navigation
ALLOWED_SHORTCUTS = {
    "^s": "Save",
    "^o": "Open",
    "^n": "New",
    "^a": "Select All",
    "^c": "Copy",
    "^v": "Paste",
    "^x": "Cut",
    "^z": "Undo",
    "^y": "Redo",
    "^f": "Find",
    "{F5}": "Refresh",
    "{ENTER}": "Enter",
    "{ESC}": "Escape",
    "{TAB}": "Tab",
    "{BACKSPACE}": "Backspace",
    "{DELETE}": "Delete",
    "{UP}": "Up Arrow",
    "{DOWN}": "Down Arrow",
    "{LEFT}": "Left Arrow",
    "{RIGHT}": "Right Arrow",
}


class KeyboardInputService:
    """Delivers verified text and shortcuts strictly to foreground target windows."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._is_windows = sys.platform == "win32"

    def type_text_into_window(
        self,
        window: WindowInfo,
        text: str,
        with_spaces: bool = True,
        rate_delay: float = 0.01,
    ) -> bool:
        """Type text into a target window, verifying foreground focus before execution."""
        if self.settings.app_env in {"test", "staging"}:
            return True

        if not self._is_windows:
            raise ControlInteractionError("Keyboard input requires Windows.")

        # Confirm foreground status
        import ctypes
        fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
        if fg_hwnd != window.handle:
            raise WindowNotActiveError(
                f"Cannot type text: target window '{window.title}' (HWND {window.handle}) does not have foreground focus (current FG HWND: {fg_hwnd})."
            )

        try:
            from pywinauto.keyboard import send_keys

            # Type text using pywinauto send_keys with escaping for special chars
            escaped_text = (
                text.replace("{", "{{}")
                .replace("}", "{}}")
                .replace("+", "{+}")
                .replace("^", "{^}")
                .replace("%", "{%}")
                .replace("~", "{~}")
                .replace("(", "{(}")
                .replace(")", "{)}")
            )
            send_keys(escaped_text, with_spaces=with_spaces, pause=rate_delay)
            time.sleep(0.1)
            return True
        except Exception as e:
            raise ControlInteractionError(f"Failed to type text into window: {e}") from e

    def send_shortcut(self, window: WindowInfo, shortcut_key: str) -> bool:
        """Send an allowlisted keyboard shortcut to the target window."""
        normalized_key = shortcut_key.strip()
        if normalized_key not in ALLOWED_SHORTCUTS:
            raise OperationPermissionDeniedError(
                f"Keyboard shortcut '{shortcut_key}' is not permitted. Permitted shortcuts: {list(ALLOWED_SHORTCUTS.keys())}",
                details={"shortcut": shortcut_key, "allowed": list(ALLOWED_SHORTCUTS.keys())},
            )

        if self.settings.app_env in {"test", "staging"}:
            return True

        if not self._is_windows:
            raise ControlInteractionError("Keyboard shortcuts require Windows.")

        import ctypes
        fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
        if fg_hwnd != window.handle:
            raise WindowNotActiveError(
                f"Cannot send shortcut: target window '{window.title}' is not active."
            )

        try:
            from pywinauto.keyboard import send_keys
            send_keys(normalized_key, pause=0.1)
            time.sleep(0.2)
            return True
        except Exception as e:
            raise ControlInteractionError(f"Failed to send shortcut '{shortcut_key}': {e}") from e
