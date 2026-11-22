"""Unit tests for Windows application discovery service."""

import struct
from pathlib import Path

import pytest

from app.services.app_discovery_service import (
    AppDiscoveryService,
    clean_app_name,
    generate_stable_app_id,
    infer_app_category,
    parse_lnk_target,
    validate_launch_target,
)


def create_mock_lnk(target_path: str) -> bytes:
    """Helper to synthesize a minimal valid MS-SHLLINK binary file structure."""
    header = bytearray(76)
    # HeaderSize: 0x0000004C (76)
    header[0:4] = struct.pack("<I", 76)
    # LinkCLSID
    header[4:20] = bytes.fromhex("0114020000000000c000000000000046")
    # LinkFlags: HasLinkInfo (bit 1 = 0x02)
    header[0x14:0x18] = struct.pack("<I", 0x02)

    # LinkInfo structure
    path_bytes = target_path.encode("mbcs") + b"\x00"
    header_size = 28
    local_base_path_offset = header_size
    link_info_size = header_size + len(path_bytes)

    link_info = bytearray(header_size)
    link_info[0:4] = struct.pack("<I", link_info_size)
    link_info[4:8] = struct.pack("<I", header_size)
    link_info[8:12] = struct.pack("<I", 0x01)  # VolumeIDAndLocalBasePath
    link_info[12:16] = struct.pack("<I", 0)  # VolumeIDOffset
    link_info[16:20] = struct.pack("<I", local_base_path_offset)
    link_info[20:24] = struct.pack("<I", 0)  # CommonNetworkRelativeLinkOffset
    link_info[24:28] = struct.pack("<I", local_base_path_offset)  # CommonPathSuffixOffset

    return bytes(header + link_info + path_bytes)


class TestAppDiscoveryTargetValidation:
    """Tests for validate_launch_target security enforcement."""

    def test_valid_executable_targets(self):
        is_valid, reason = validate_launch_target(r"C:\Program Files\Google\Chrome\chrome.exe", "executable")
        assert is_valid is True
        assert reason is None

        is_valid, reason = validate_launch_target(r"C:\Windows\System32\notepad.exe", "executable")
        assert is_valid is True

    def test_rejects_empty_target(self):
        is_valid, reason = validate_launch_target("", "executable")
        assert is_valid is False
        assert "empty" in reason.lower()

    def test_rejects_disallowed_extensions(self):
        for bad_ext in [".bat", ".cmd", ".ps1", ".vbs", ".msi", ".reg", ".scr"]:
            is_valid, reason = validate_launch_target(f"C:\\Tools\\script{bad_ext}", "executable")
            assert is_valid is False
            assert "forbidden" in reason.lower() or "must be a windows executable" in reason.lower()

    def test_rejects_relative_paths(self):
        is_valid, reason = validate_launch_target(r"notepad.exe", "executable")
        assert is_valid is False
        assert "absolute" in reason.lower()

    def test_rejects_command_injection_metacharacters(self):
        dangerous_targets = [
            r"C:\Tools\app.exe; calc.exe",
            r"C:\Tools\app.exe & whoami",
            r"C:\Tools\app.exe | echo pwned",
            r"C:\Tools\app.exe > out.txt",
            "C:\\Tools\\app.exe`calc`",
            "C:\\Tools\\app.exe\" --arg",
            "C:\\Tools\\app.exe' --arg",
        ]
        for dt in dangerous_targets:
            is_valid, reason = validate_launch_target(dt, "executable")
            assert is_valid is False
            assert "unsafe" in reason.lower() or "illegal" in reason.lower()

    def test_packaged_app_aumid_validation(self):
        assert validate_launch_target("Microsoft.WindowsCalculator_8wekyb3d8bbwe!App", "packaged_app")[0] is True
        assert validate_launch_target("Google.AntigravityIDE", "packaged_app")[0] is True

        # Invalid AUMID with illegal characters
        assert validate_launch_target("Calc; whoami", "packaged_app")[0] is False
        assert validate_launch_target("App & calc", "packaged_app")[0] is False


class TestCategoryInference:
    """Tests for infer_app_category classification."""

    def test_infers_browser_category(self):
        assert infer_app_category("Google Chrome", "chrome.exe") == "Browsers"
        assert infer_app_category("Brave Browser", "brave.exe") == "Browsers"
        assert infer_app_category("Microsoft Edge", "msedge.exe") == "Browsers"

    def test_infers_development_category(self):
        assert infer_app_category("Visual Studio Code", "Code.exe") == "Development"
        assert infer_app_category("Antigravity IDE", "antigravity.exe") == "Development"
        assert infer_app_category("Windows Terminal", "wt.exe") == "Development"
        assert infer_app_category("Python 3.12", "python.exe") == "Development"

    def test_infers_productivity_category(self):
        assert infer_app_category("Microsoft Excel", "EXCEL.EXE") == "Productivity"
        assert infer_app_category("Word", "WINWORD.EXE") == "Productivity"
        assert infer_app_category("Calculator", "calc.exe") == "Productivity"

    def test_infers_media_and_utilities(self):
        assert infer_app_category("Spotify", "Spotify.exe") == "Media"
        assert infer_app_category("VLC Media Player", "vlc.exe") == "Media"
        assert infer_app_category("Task Manager", "taskmgr.exe") == "Utilities"
        assert infer_app_category("Registry Editor", "regedit.exe") == "Utilities"


class TestStableAppId:
    """Tests for generate_stable_app_id."""

    def test_deterministic_id(self):
        id1 = generate_stable_app_id("executable", r"C:\Program Files\App\app.exe")
        id2 = generate_stable_app_id("executable", r"c:\program files\app\app.exe")
        assert id1 == id2
        assert len(id1) == 16

    def test_distinguishes_different_targets(self):
        id_a = generate_stable_app_id("executable", r"C:\AppA\run.exe")
        id_b = generate_stable_app_id("executable", r"C:\AppB\run.exe")
        assert id_a != id_b


class TestLnkParsing:
    """Tests for parse_lnk_target."""

    def test_parses_valid_synthesized_lnk(self, tmp_path: Path):
        target = r"C:\Program Files\TestApp\app.exe"
        lnk_bytes = create_mock_lnk(target)
        lnk_file = tmp_path / "TestApp.lnk"
        lnk_file.write_bytes(lnk_bytes)

        parsed = parse_lnk_target(lnk_file)
        assert parsed is not None
        assert parsed.lower() == target.lower()

    def test_handles_corrupt_lnk_gracefully(self, tmp_path: Path):
        bad_file = tmp_path / "corrupt.lnk"
        bad_file.write_bytes(b"not a valid lnk file at all")
        assert parse_lnk_target(bad_file) is None

    def test_clean_app_name(self):
        assert clean_app_name("Google Chrome.lnk") == "Google Chrome"
        assert clean_app_name("visual_studio_code.exe") == "visual studio code"


class TestDiscoveryDeduplicationAndState:
    """Tests for AppDiscoveryService deduplication and availability marking."""

    def test_deduplicates_and_flags_missing_target(self, tmp_path: Path):
        # Create a mock Start Menu directory
        start_dir = tmp_path / "StartMenu"
        start_dir.mkdir()

        # Create real executable that exists
        app_exe = tmp_path / "real_app.exe"
        app_exe.write_text("binary content")

        # Create lnk 1 pointing to real_app.exe
        lnk1 = start_dir / "Real Application.lnk"
        lnk1.write_bytes(create_mock_lnk(str(app_exe.resolve())))

        # Create lnk 2 pointing to the same real_app.exe with slightly different name
        lnk2 = start_dir / "real_app.lnk"
        lnk2.write_bytes(create_mock_lnk(str(app_exe.resolve())))

        # Create lnk 3 pointing to non-existent executable
        ghost_exe = r"C:\NonExistent\GhostApp\ghost.exe"
        lnk3 = start_dir / "Ghost Application.lnk"
        lnk3.write_bytes(create_mock_lnk(ghost_exe))

        service = AppDiscoveryService(
            custom_user_start_menu=start_dir,
            enable_system_start_menu=False,
            enable_registry=False,
            enable_packaged_apps=False,
        )

        apps = service.discover_all()

        # Should deduplicate lnk1 and lnk2 into 1 entry
        assert len(apps) == 2

        # Check real app
        real_entry = next(a for a in apps if a.target_path.lower() == str(app_exe.resolve()).lower())
        assert real_entry.is_available is True
        assert real_entry.is_valid is True
        assert real_entry.name == "Real Application"  # Preferred more descriptive name

        # Check ghost app
        ghost_entry = next(a for a in apps if "ghost" in a.target_path.lower())
        assert ghost_entry.is_available is False
        assert ghost_entry.is_valid is False
        assert "not found" in ghost_entry.rejection_reason.lower()

    def test_live_windows_discovery_if_available(self):
        import sys

        if sys.platform != "win32":
            pytest.skip("Windows-only live discovery test")

        service = AppDiscoveryService(enable_packaged_apps=False)
        apps = service.discover_all()

        assert len(apps) > 0
        for app in apps:
            assert len(app.id) == 16
            assert app.name
            assert app.target_path
            assert app.category in {"Browsers", "Development", "Productivity", "Media", "Games", "Utilities", "General"}
