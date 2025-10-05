#!/usr/bin/env python3
"""
Read `.stuff/messages.md` and run rcdtool per line.

Each line format: `<link> ; <description>`
 - `<link>`: Telegram message link (e.g., https://t.me/c/123/456)
 - `<description>`: Used as the base output filename.

Usage examples:
  python scripts/rcdtool_from_messages.py \
      -f .stuff/messages.md -c config.ini --infer-extension

Notes:
 - Uses `-O <name>` to set the base filename.
 - If `rcdtool` CLI is not on PATH, falls back to `python -m rcdtool.main` with PYTHONPATH=src.
 - Sanitizes the description into a safe filename while preserving Unicode letters.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """Sanitize description into a safe base filename.

    - Keep Unicode letters/digits/underscore/space/.-()
    - Replace path separators and other symbols with underscore
    - Trim leading/trailing dots, spaces, and dashes
    """
    name = (name or "").strip()
    if not name:
        return "file"

    # Replace path separators and disallowed critical characters
    name = name.replace("/", "_").replace("\\", "_")
    name = name.replace(":", "_")

    # Keep letters/digits/underscore/space/.-() and Unicode word chars
    name = re.sub(r"[^\w\s().\-]+", "_", name, flags=re.UNICODE)
    # Collapse multiple underscores or spaces
    name = re.sub(r"[\s]+", " ", name, flags=re.UNICODE)
    name = re.sub(r"_{2,}", "_", name)

    # Trim problematic leading/trailing chars
    name = name.strip(" .-_")
    return name or "file"


def resolve_executor() -> list[str] | None:
    """Return the base command list to execute rcdtool.

    Prefer the `rcdtool` console script; if missing, use
    `python -m rcdtool.main` with PYTHONPATH=src (handled when running).
    """
    exe = shutil.which("rcdtool")
    if exe:
        return [exe]
    # Fallback to python -m rcdtool.main
    return [sys.executable, "-m", "rcdtool.main"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run rcdtool for each link in a file")
    parser.add_argument(
        "-f", "--file",
        default=".stuff/messages.md",
        help="Path to input file (default: .stuff/messages.md)",
    )
    parser.add_argument(
        "-c", "--config",
        default="config.ini",
        help="Path to rcdtool config.ini (default: config.ini)",
    )
    parser.add_argument(
        "--infer-extension",
        action="store_true",
        help="Pass --infer-extension to rcdtool",
    )
    parser.add_argument(
        "--detailed-name",
        action="store_true",
        help="Pass --detailed-name to rcdtool (adds channel/message to name)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands without executing",
    )
    args = parser.parse_args()

    in_path = Path(args.file)
    if not in_path.exists():
        print(f"Input file not found: {in_path}", file=sys.stderr)
        return 2

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Warning: config not found: {config_path}", file=sys.stderr)

    base_cmd = resolve_executor()
    if base_cmd is None:
        print("Unable to resolve rcdtool executor", file=sys.stderr)
        return 2

    # Ensure PYTHONPATH includes src for the fallback case
    env = os.environ.copy()
    if base_cmd[:3] == [sys.executable, "-m", "rcdtool.main"]:
        src_path = str((Path.cwd() / "src").resolve())
        env["PYTHONPATH"] = f"{src_path}:{env.get('PYTHONPATH', '')}" if env.get("PYTHONPATH") else src_path

    # Process each non-empty, non-comment line
    with in_path.open("r", encoding="utf-8") as fh:
        for ln_num, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if ";" in line:
                link, desc = line.split(";", 1)
                link = link.strip()
                desc = desc.strip()
            else:
                link = line
                desc = ""

            if not link:
                print(f"Skip line {ln_num}: missing link", file=sys.stderr)
                continue

            out_base = sanitize_filename(desc) if desc else "file"

            # Detect /c/<channel>/<topic>/<message> or /c/<channel>/<message>
            # We must skip the middle "topic" id if present and use the last part as message id.
            cmd: list[str]
            chan_msg = None  # tuple[channel_id, message_id]
            try:
                if "/c/" in link:
                    after_c = link.split("/c/", 1)[1]
                    # Drop query/fragment if present
                    after_c = after_c.split("?", 1)[0].split("#", 1)[0]
                    parts = [p for p in after_c.split("/") if p]

                    def _is_numlike(s: str) -> bool:
                        s2 = s.lstrip("+-")
                        return s2.isdigit()

                    if len(parts) >= 2 and _is_numlike(parts[0]):
                        channel_id = parts[0]
                        # If triple or more segments, last segment is the message id; skip middle(s)
                        message_id = parts[-1] if _is_numlike(parts[-1]) else None
                        if len(parts) == 2:
                            # /c/<channel>/<message>
                            message_id = parts[1] if _is_numlike(parts[1]) else None
                        if message_id is not None:
                            chan_msg = (channel_id, message_id)
            except Exception:
                chan_msg = None

            if chan_msg:
                channel_id, message_id = chan_msg
                cmd = [*base_cmd, "-c", str(config_path), "-C", channel_id, "-M", message_id, "-O", out_base]
            else:
                cmd = [*base_cmd, "-c", str(config_path), "--link", link, "-O", out_base]
            if args.infer_extension:
                cmd.append("--infer-extension")
            if args.detailed_name:
                cmd.append("--detailed-name")

            if args.dry_run:
                print("DRY:", " ".join(repr(c) if " " in c else c for c in cmd))
                continue

            print(f"Line {ln_num}: {link} -> {out_base}")
            try:
                # Stream output directly to the console
                proc = subprocess.run(cmd, env=env, check=False)
                if proc.returncode != 0:
                    print(f"  Error (exit {proc.returncode}) on line {ln_num}", file=sys.stderr)
            except FileNotFoundError as e:
                print(f"  Executor not found: {e}", file=sys.stderr)
                return 127

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
