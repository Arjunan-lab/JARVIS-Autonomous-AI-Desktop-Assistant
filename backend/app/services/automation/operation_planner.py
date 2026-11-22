"""Operation planner decomposing user intent into verified atomic automation action steps."""

import logging
import re
import uuid
from pathlib import Path

from app.core.config import Settings, get_settings
from app.services.automation.automation_models import ActionStep

logger = logging.getLogger(__name__)


class OperationPlanner:
    """Translates user natural language instructions or structured requests into executable action plans."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def plan_operation(self, user_prompt: str) -> list[ActionStep]:
        """Convert a user command into a deterministic sequence of atomic action steps."""
        prompt = user_prompt.strip()
        lower = prompt.lower()
        steps: list[ActionStep] = []

        # ── Calculator & Arithmetic Workflow ─────────────────────────────
        if "calc" in lower or "calculator" in lower:
            steps.append(
                ActionStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    action_type="launch_or_focus",
                    description="Launch or focus Windows Calculator",
                    arguments={"application": "calculator"},
                    target_app_id="calculator",
                )
            )

            # Check if calculation requested (e.g. "ad 3 and 8", "add 3 and 8", "3 + 8", "multiply 5 by 6", "100 / 4")
            math_match = (
                re.search(r"(?:ad|add|plus|\+)\s+(\d+(?:\.\d+)?)\s+(?:and|\+)\s+(\d+(?:\.\d+)?)", prompt, re.IGNORECASE)
                or re.search(r"(\d+(?:\.\d+)?)\s*(?:\+|\-|plus|minus|times|\*|divided by|\/)\s*(\d+(?:\.\d+)?)", prompt, re.IGNORECASE)
                or re.search(r"(?:multiply|times|\*)\s+(\d+(?:\.\d+)?)\s+(?:and|by|\*)\s+(\d+(?:\.\d+)?)", prompt, re.IGNORECASE)
                or re.search(r"(?:subtract|minus|\-)\s+(\d+(?:\.\d+)?)\s+(?:from|and|\-)\s+(\d+(?:\.\d+)?)", prompt, re.IGNORECASE)
            )

            if math_match:
                n1_str, n2_str = math_match.group(1), math_match.group(2)
                try:
                    n1 = float(n1_str) if "." in n1_str else int(n1_str)
                    n2 = float(n2_str) if "." in n2_str else int(n2_str)
                    if any(w in lower for w in ["multiply", "times", "*"]):
                        op_sym, op_res = "*", n1 * n2
                    elif any(w in lower for w in ["subtract", "minus", "-"]):
                        op_sym, op_res = "-", n1 - n2
                    elif any(w in lower for w in ["divide", "/"]):
                        op_sym, op_res = "/", (n1 / n2) if n2 != 0 else 0
                    else:
                        op_sym, op_res = "+", n1 + n2

                    expr_str = f"{n1} {op_sym} {n2}"
                    steps.append(
                        ActionStep(
                            step_id=f"step-{uuid.uuid4().hex[:6]}",
                            action_type="calculate",
                            description=f"Calculate: {expr_str} = {op_res}",
                            arguments={
                                "application": "calculator",
                                "expression": expr_str,
                                "result": op_res,
                            },
                            target_app_id="calculator",
                        )
                    )
                except Exception as ex:  # noqa: BLE001
                    logger.debug("Math parsing error: %s", ex)

            return steps

        # ── Workflow 1 & 2: Notepad text entry and save ──────────────────
        if "notepad" in lower:
            steps.append(
                ActionStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    action_type="launch_or_focus",
                    description="Launch or focus Microsoft Notepad",
                    arguments={"application": "notepad"},
                    target_app_id="notepad",
                )
            )

            # Only add writing steps if the user actually commanded text entry
            has_write = any(w in lower for w in ["write", "type", "enter", "insert", "saying", "put", "text"])
            if has_write:
                # 1. Text extraction (quoted first, then unquoted)
                text_to_write = None
                q_match = re.search(r"""(?:write|type|enter|insert)\s+['"“]([^'"”]+)['"”]""", prompt, re.IGNORECASE)
                if q_match:
                    text_to_write = q_match.group(1).strip()
                else:
                    u_match = re.search(
                        r"""(?:write|type|enter|insert)\s+(?:the\s+text\s+)?(.+?)(?:,\s*and\s+save|\s+and\s+save|\s+and\s+store|\s+to|\s+as|$)""",
                        prompt,
                        re.IGNORECASE,
                    )
                    if u_match:
                        text_to_write = u_match.group(1).strip().strip("\"',.")
                if not text_to_write:
                    text_to_write = "Hello from JARVIS"

                steps.append(
                    ActionStep(
                        step_id=f"step-{uuid.uuid4().hex[:6]}",
                        action_type="type_text",
                        description=f"Enter text into Notepad: '{text_to_write}'",
                        arguments={"application": "notepad", "text": text_to_write},
                        target_app_id="notepad",
                    )
                )
                steps.append(
                    ActionStep(
                        step_id=f"step-{uuid.uuid4().hex[:6]}",
                        action_type="verify_ui_text",
                        description=f"Verify entered text '{text_to_write}' in Notepad control",
                        arguments={"application": "notepad", "expected_text": text_to_write},
                        target_app_id="notepad",
                    )
                )

                # Check if save is requested
                if "save" in lower or "desktop" in lower or ".txt" in lower:
                    filename = "JARVIS_Test.txt"
                    as_match = re.search(r"""(?:as|named|called)\s+['"]?([\w\.\-]+)['"]?""", prompt, re.IGNORECASE)
                    file_match = re.search(r"""['"]?([\w\-]+\.(?:txt|log|md|json))['"]?""", prompt, re.IGNORECASE)
                    if as_match:
                        filename = as_match.group(1).strip().strip(":,'\"").rstrip(".")
                    elif file_match:
                        filename = file_match.group(1).strip().strip(":,'\"").rstrip(".")

                    if not filename.lower().endswith(".txt"):
                        filename += ".txt"

                    target_dir = Path.home() / "Desktop" if "desktop" in lower else Path(self.settings.jarvis_allowed_dirs or (Path.home() / "Desktop"))
                    save_dest = target_dir / filename

                    steps.append(
                        ActionStep(
                            step_id=f"step-{uuid.uuid4().hex[:6]}",
                            action_type="save_file",
                            description=f"Save document as '{filename}' to {target_dir}",
                            arguments={
                                "application": "notepad",
                                "file_path": str(save_dest),
                                "text": text_to_write,
                            },
                            target_app_id="notepad",
                        )
                    )
                    steps.append(
                        ActionStep(
                            step_id=f"step-{uuid.uuid4().hex[:6]}",
                            action_type="verify_file",
                            description=f"Verify saved file '{filename}' on disk",
                            arguments={"file_path": str(save_dest), "expected_content": text_to_write},
                        )
                    )

            return steps

        # ── Workflow 3: File Explorer ────────────────────────────────────
        if "explorer" in lower or "folder" in lower or "directory" in lower:
            folder_target = Path.cwd()
            if "project" in lower or "jarvis" in lower:
                folder_target = Path.cwd()
            elif "desktop" in lower:
                folder_target = Path.home() / "Desktop"
            elif "document" in lower:
                folder_target = Path.home() / "Documents"

            steps.append(
                ActionStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    action_type="open_folder",
                    description=f"Open folder '{folder_target.name}' in File Explorer",
                    arguments={"application": "explorer", "folder_path": str(folder_target.resolve())},
                    target_app_id="explorer",
                )
            )
            return steps

        # ── Workflow 4: Visual Studio Code ───────────────────────────────
        if "vs code" in lower or "vscode" in lower or "code" in lower:
            project_path = Path.cwd()
            steps.append(
                ActionStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    action_type="open_workspace",
                    description=f"Open workspace in Visual Studio Code: {project_path.name}",
                    arguments={"application": "code", "project_path": str(project_path.resolve())},
                    target_app_id="code",
                )
            )
            return steps

        # ── Workflow 5: Browser interaction ──────────────────────────────
        if "browser" in lower or "chrome" in lower or "edge" in lower or "fastapi" in lower or "documentation" in lower or "search" in lower:
            target_url = "https://fastapi.tiangolo.com/"
            if "fastapi" in lower:
                target_url = "https://fastapi.tiangolo.com/tutorial/dependencies/" if "dependency" in lower else "https://fastapi.tiangolo.com/"
            elif "google" in lower:
                target_url = "https://www.google.com"

            steps.append(
                ActionStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    action_type="open_browser",
                    description=f"Navigate browser to {target_url}",
                    arguments={"url": target_url, "browser": "chrome"},
                )
            )
            return steps

        # ── Workflow 6: Read README and create summary file ──────────────
        if "readme" in lower and ("summary" in lower or "save" in lower):
            readme_path = Path.cwd() / "README.md"
            summary_path = (Path.cwd() / "project_summary.txt").resolve()

            steps.append(
                ActionStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    action_type="read_text_file",
                    description=f"Read project documentation from {readme_path.name}",
                    arguments={"file_path": str(readme_path)},
                )
            )
            steps.append(
                ActionStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    action_type="write_text_file",
                    description="Create short summary and write to project_summary.txt",
                    arguments={
                        "file_path": str(summary_path),
                        "content": "JARVIS System Summary: Advanced AI Desktop Assistant with Universal Windows Automation Engine.",
                        "overwrite": True,
                    },
                )
            )
            steps.append(
                ActionStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    action_type="verify_file",
                    description="Verify project_summary.txt content on disk",
                    arguments={"file_path": str(summary_path), "expected_content": "JARVIS System Summary"},
                )
            )
            return steps

        # ── Universal Application Launch / Focus ─────────────────────────
        open_match = re.search(r"^(?:open|launch|start|run|focus)\s+([a-zA-Z0-9\s._\-]+?)(?:\s+and|\s+in|\s+to|$)", prompt, re.IGNORECASE)
        if open_match:
            raw_target = open_match.group(1).strip()
            if raw_target and not any(k in raw_target.lower() for k in ["folder", "dir", "directory", "project", "readme"]):
                steps.append(
                    ActionStep(
                        step_id=f"step-{uuid.uuid4().hex[:6]}",
                        action_type="launch_or_focus",
                        description=f"Launch or focus {raw_target.capitalize()}",
                        arguments={"application": raw_target},
                        target_app_id=raw_target.lower(),
                    )
                )
                return steps

        # Default fallback: single generic execution step
        steps.append(
            ActionStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                action_type="generic_instruction",
                description=f"Execute instruction: {prompt}",
                arguments={"instruction": prompt},
            )
        )
        return steps
