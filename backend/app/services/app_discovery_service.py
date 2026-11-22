"""Windows application discovery service.

Discovers installed applications from:
- Per-user and system-wide Start Menu shortcuts (.lnk)
- Registered application entries (App Paths in Registry)
- Packaged-app launch mechanisms (UWP/AUMID via Get-StartApps)

Never scans entire drives indiscriminately.
Deduplicates entries, infers categories, validates executable targets,
and flags invalid or unavailable entries.
"""

import glob
import hashlib
import json
import logging
import os
import re
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("jarvis.app_discovery")

# Disallowed extensions that must never be treated as valid application executables
DISALLOWED_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".js",
    ".wsf",
    ".msi",
    ".reg",
    ".scr",
    ".com",
    ".pif",
}

# Regex for detecting command injection metacharacters
UNSAFE_CHARS_RE = re.compile(r"[\x00-\x1f\x7f\"'|&;><`$]")

# AUMID format validation regex
AUMID_RE = re.compile(r"^[A-Za-z0-9_\-\.]+(?:![A-Za-z0-9_\-\.]+)?$")

# Common uninstaller/updater keywords to exclude from user apps
UNINSTALL_KEYWORDS = {"uninstall", "unins000", "modify", "repair", "readme", "documentation", "help"}


@dataclass
class DiscoveredApp:
    """Represents an application discovered on the Windows system."""

    id: str
    name: str
    target_path: str
    target_type: str  # "executable" | "packaged_app"
    category: str
    icon_path: str | None = None
    is_available: bool = True
    is_valid: bool = True
    rejection_reason: str | None = None


def generate_stable_app_id(target_type: str, canonical_target: str) -> str:
    """Generate a deterministic 16-character hex ID based on target type and canonical target."""
    payload = f"{target_type.strip().lower()}:{canonical_target.strip().lower()}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def parse_lnk_target(lnk_path: str | Path) -> str | None:
    """Parse a Windows .lnk binary file to extract the target path without external dependencies.

    Implements the MS-SHLLINK specification for LinkFlags and LinkInfo structures.
    """
    try:
        with open(lnk_path, "rb") as f:
            data = f.read()

        # Header check: must be >= 76 bytes and begin with 0x0000004C
        if len(data) < 76 or data[:4] != b"\x4c\x00\x00\x00":
            return None

        flags = struct.unpack("<I", data[0x14:0x18])[0]
        offset = 76

        # HasLinkTargetIDList (bit 0)
        if flags & 0x01:
            if len(data) < offset + 2:
                return None
            id_list_len = struct.unpack("<H", data[offset : offset + 2])[0]
            offset += 2 + id_list_len

        # HasLinkInfo (bit 1)
        if flags & 0x02:
            if len(data) < offset + 28:
                return None
            info_start = offset
            header_size = struct.unpack("<I", data[info_start + 4 : info_start + 8])[0]

            # Unicode LocalBasePathOffset (header size >= 36, offset 28)
            if header_size >= 36 and len(data) >= info_start + 32:
                u_offset = struct.unpack("<I", data[info_start + 28 : info_start + 32])[0]
                if u_offset > 0 and len(data) > info_start + u_offset:
                    u_start = info_start + u_offset
                    u_end = data.find(b"\x00\x00", u_start)
                    if u_end != -1 and (u_end - u_start) % 2 == 0:
                        path_candidate = data[u_start:u_end].decode("utf-16le", errors="ignore")
                        if path_candidate:
                            return path_candidate

            # ANSI LocalBasePathOffset (offset 16)
            local_offset = struct.unpack("<I", data[info_start + 16 : info_start + 20])[0]
            if local_offset > 0 and len(data) > info_start + local_offset:
                l_start = info_start + local_offset
                l_end = data.find(b"\x00", l_start)
                if l_end != -1:
                    path_candidate = data[l_start:l_end].decode("mbcs", errors="ignore")
                    if path_candidate:
                        return path_candidate

        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed parsing .lnk file %s: %s", lnk_path, exc)
        return None


def infer_app_category(name: str, target: str) -> str:
    """Infer application category based on display name and target executable keywords."""
    combined = f"{name} {target}".lower()

    if any(k in combined for k in ["chrome", "edge", "brave", "firefox", "opera", "vivaldi", "browser"]):
        return "Browsers"
    if any(
        k in combined
        for k in [
            "code",
            "visual studio",
            "pycharm",
            "antigravity",
            "git",
            "python",
            "sublime",
            "terminal",
            "powershell",
            "cmd",
            "idea",
            "clion",
            "rider",
            "developer",
            "compiler",
        ]
    ):
        return "Development"
    if any(
        k in combined
        for k in [
            "word",
            "excel",
            "powerpoint",
            "powerpnt",
            "onenote",
            "outlook",
            "wps",
            "acrobat",
            "reader",
            "notion",
            "slack",
            "teams",
            "calc",
            "calculator",
            "notes",
            "office",
        ]
    ):
        return "Productivity"
    if any(
        k in combined
        for k in [
            "spotify",
            "vlc",
            "afterfx",
            "photoshop",
            "premiere",
            "illustrator",
            "audacity",
            "blender",
            "camera",
            "photos",
            "media",
            "music",
            "video",
        ]
    ):
        return "Media"
    if any(k in combined for k in ["steam", "epic games", "riot", "game", "xbox"]):
        return "Games"
    if any(
        k in combined
        for k in [
            "explorer",
            "taskmgr",
            "regedit",
            "settings",
            "paint",
            "notepad",
            "snipping",
            "utility",
            "tools",
        ]
    ):
        return "Utilities"

    return "General"


def clean_app_name(raw_name: str) -> str:
    """Clean shortcut or executable filename into a human-readable title."""
    clean = raw_name
    for ext in [".lnk", ".exe", ".url"]:
        if clean.lower().endswith(ext):
            clean = clean[: -len(ext)]
    clean = re.sub(r"[\-_]+", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def validate_launch_target(target: str, target_type: str) -> tuple[bool, str | None]:
    """Validate that target path or AUMID meets strict security standards.

    Returns (is_valid, rejection_reason).
    """
    if not target or not target.strip():
        return False, "Target is empty"

    target = target.strip()

    # Disallow control and injection metacharacters
    if UNSAFE_CHARS_RE.search(target):
        return False, "Target contains illegal or unsafe shell characters"

    if target_type == "packaged_app":
        if not AUMID_RE.match(target):
            return False, f"Invalid AUMID format: '{target}'"
        return True, None

    if target_type == "executable":
        # Must end with .exe
        path_lower = target.lower()
        ext = os.path.splitext(path_lower)[1]
        if ext in DISALLOWED_EXTENSIONS:
            return False, f"Target extension '{ext}' is forbidden for direct execution"
        if ext != ".exe":
            return False, f"Target must be a Windows executable (.exe), got '{ext}'"

        # Must be an absolute path
        try:
            p = Path(target)
            if not p.is_absolute():
                return False, f"Executable path must be absolute: '{target}'"
        except Exception as exc:  # noqa: BLE001
            return False, f"Invalid file path format: {exc}"

        return True, None

    return False, f"Unknown target_type: '{target_type}'"


class AppDiscoveryService:
    """Discovers installed Windows applications from Start Menus, Registry, and Packaged apps."""

    def __init__(
        self,
        custom_user_start_menu: Path | str | None = None,
        custom_system_start_menu: Path | str | None = None,
        enable_user_start_menu: bool = True,
        enable_system_start_menu: bool = True,
        enable_registry: bool = True,
        enable_packaged_apps: bool = True,
    ) -> None:
        self.custom_user_start_menu = (
            Path(custom_user_start_menu) if custom_user_start_menu else None
        )
        self.custom_system_start_menu = (
            Path(custom_system_start_menu) if custom_system_start_menu else None
        )
        self.enable_user_start_menu = enable_user_start_menu
        self.enable_system_start_menu = enable_system_start_menu
        self.enable_registry = enable_registry
        self.enable_packaged_apps = enable_packaged_apps

    def get_start_menu_dirs(self) -> list[Path]:
        """Return the user and system Start Menu directories to scan."""
        dirs: list[Path] = []

        if self.custom_user_start_menu:
            dirs.append(self.custom_user_start_menu)
        elif self.enable_user_start_menu and sys.platform == "win32":
            user_path = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
            if os.path.isdir(user_path):
                dirs.append(Path(user_path))

        if self.custom_system_start_menu:
            dirs.append(self.custom_system_start_menu)
        elif self.enable_system_start_menu and sys.platform == "win32":
            system_path = os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs")
            if os.path.isdir(system_path):
                dirs.append(Path(system_path))

        return dirs

    def discover_start_menu_apps(self) -> list[DiscoveredApp]:
        """Discover applications by parsing .lnk shortcuts in user and system Start Menus."""
        discovered: list[DiscoveredApp] = []
        start_dirs = self.get_start_menu_dirs()

        for base_dir in start_dirs:
            if not base_dir.exists():
                continue

            for lnk_file in glob.glob(str(base_dir / "**" / "*.lnk"), recursive=True):
                lnk_path = Path(lnk_file)
                stem_name = lnk_path.stem

                # Skip uninstaller shortcuts
                if any(kw in stem_name.lower() for kw in UNINSTALL_KEYWORDS):
                    continue

                target = parse_lnk_target(lnk_path)
                if not target:
                    continue

                # Expand environment variables (e.g. %SystemRoot%\System32\notepad.exe)
                target = os.path.expandvars(target)

                is_valid, reason = validate_launch_target(target, "executable")
                app_name = clean_app_name(stem_name)
                category = infer_app_category(app_name, target)
                app_id = generate_stable_app_id("executable", target)

                is_available = False
                if is_valid:
                    try:
                        is_available = Path(target).is_file()
                        if not is_available:
                            reason = "Target executable not found on disk"
                    except OSError:
                        is_available = False
                        reason = "Target path invalid or inaccessible"

                discovered.append(
                    DiscoveredApp(
                        id=app_id,
                        name=app_name,
                        target_path=target,
                        target_type="executable",
                        category=category,
                        is_available=is_available,
                        is_valid=is_valid and is_available,
                        rejection_reason=reason,
                    )
                )

        return discovered

    def discover_registry_app_paths(self) -> list[DiscoveredApp]:
        """Discover registered applications from HKLM and HKCU App Paths."""
        if not self.enable_registry or sys.platform != "win32":
            return []

        try:
            import winreg
        except ImportError:
            return []

        discovered: list[DiscoveredApp] = []
        hives = [
            (winreg.HKEY_CURRENT_USER, "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
        ]

        for hive, _ in hives:
            try:
                with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\App Paths") as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            sub_name = winreg.EnumKey(key, i)
                            if any(kw in sub_name.lower() for kw in UNINSTALL_KEYWORDS):
                                continue

                            with winreg.OpenKey(key, sub_name) as sub_key:
                                raw_val, _ = winreg.QueryValueEx(sub_key, "")
                                if not raw_val or not isinstance(raw_val, str):
                                    continue

                                # Strip surrounding quotes if present
                                target = raw_val.strip().strip('"')
                                target = os.path.expandvars(target)

                                is_valid, reason = validate_launch_target(target, "executable")
                                app_name = clean_app_name(sub_name)
                                category = infer_app_category(app_name, target)
                                app_id = generate_stable_app_id("executable", target)

                                is_available = False
                                if is_valid:
                                    try:
                                        is_available = Path(target).is_file()
                                        if not is_available:
                                            reason = "Target executable not found on disk"
                                    except OSError:
                                        is_available = False
                                        reason = "Target path invalid or inaccessible"

                                discovered.append(
                                    DiscoveredApp(
                                        id=app_id,
                                        name=app_name,
                                        target_path=target,
                                        target_type="executable",
                                        category=category,
                                        is_available=is_available,
                                        is_valid=is_valid and is_available,
                                        rejection_reason=reason,
                                    )
                                )
                        except OSError:
                            continue
            except OSError:
                continue

        return discovered

    def discover_packaged_apps(self) -> list[DiscoveredApp]:
        """Discover packaged Windows Store / UWP apps with valid AUMIDs via Get-StartApps."""
        if not self.enable_packaged_apps or sys.platform != "win32":
            return []

        discovered: list[DiscoveredApp] = []
        try:
            proc = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "Get-StartApps | ConvertTo-Json -Compress",
                ],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                return []

            data = json.loads(proc.stdout)
            if isinstance(data, dict):
                data = [data]

            for entry in data:
                raw_name = str(entry.get("Name", "")).strip()
                app_id_raw = str(entry.get("AppID", "")).strip()
                if not raw_name or not app_id_raw:
                    continue

                if any(kw in raw_name.lower() for kw in UNINSTALL_KEYWORDS):
                    continue

                # Check if AppID is a Win32 executable path
                if app_id_raw.lower().endswith(".exe"):
                    target = os.path.expandvars(app_id_raw)
                    is_valid, reason = validate_launch_target(target, "executable")
                    app_name = clean_app_name(raw_name)
                    category = infer_app_category(app_name, target)
                    app_id = generate_stable_app_id("executable", target)

                    is_available = False
                    if is_valid:
                        try:
                            is_available = Path(target).is_file()
                            if not is_available:
                                reason = "Target executable not found on disk"
                        except OSError:
                            is_available = False
                            reason = "Target path invalid or inaccessible"

                    discovered.append(
                        DiscoveredApp(
                            id=app_id,
                            name=app_name,
                            target_path=target,
                            target_type="executable",
                            category=category,
                            is_available=is_available,
                            is_valid=is_valid and is_available,
                            rejection_reason=reason,
                        )
                    )
                else:
                    # Treat as packaged app AUMID
                    is_valid, reason = validate_launch_target(app_id_raw, "packaged_app")
                    app_name = clean_app_name(raw_name)
                    category = infer_app_category(app_name, app_id_raw)
                    app_id = generate_stable_app_id("packaged_app", app_id_raw)

                    discovered.append(
                        DiscoveredApp(
                            id=app_id,
                            name=app_name,
                            target_path=app_id_raw,
                            target_type="packaged_app",
                            category=category,
                            is_available=is_valid,
                            is_valid=is_valid,
                            rejection_reason=reason,
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed discovering packaged apps via Get-StartApps: %s", exc)

        return discovered

    def discover_all(self) -> list[DiscoveredApp]:
        """Discover and deduplicate all applications across all authorized Windows locations.

        Deduplication rule:
        Keyed by (target_type, canonical_target).
        Prefers the entry with the cleanest, most descriptive human name and valid status.
        """
        all_apps: list[DiscoveredApp] = []

        # 1. Start Menu shortcuts
        all_apps.extend(self.discover_start_menu_apps())

        # 2. Registry App Paths
        all_apps.extend(self.discover_registry_app_paths())

        # 3. Packaged apps (UWP / AUMID)
        all_apps.extend(self.discover_packaged_apps())

        # Deduplicate
        deduped: dict[tuple[str, str], DiscoveredApp] = {}

        for app in all_apps:
            norm_target = app.target_path.strip().lower()
            key = (app.target_type, norm_target)

            if key not in deduped:
                deduped[key] = app
            else:
                existing = deduped[key]
                # If current candidate is valid/available while existing is not, replace it
                if app.is_valid and not existing.is_valid or len(app.name) > len(existing.name) and not existing.name.isupper():
                    deduped[key] = app

        # Sort alphabetically by name
        results = sorted(deduped.values(), key=lambda a: a.name.lower())
        logger.info("Application discovery completed: %d unique applications identified.", len(results))
        return results
