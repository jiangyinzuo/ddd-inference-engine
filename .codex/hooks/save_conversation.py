#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_MAX_BYTES = 1 * 1024 * 1024


def safe_name(s: str, fallback: str = "session") -> str:
    s = s.strip() or fallback
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)


def find_project_root(event: dict) -> Path:
    """
    优先从 cwd 向上找 .codex 或 .git，避免在 repo 子目录启动时，
    日志落到 subdir/.codex/saved_conversation。
    """
    cwd = Path(event.get("cwd") or os.getcwd()).resolve()

    for p in [cwd, *cwd.parents]:
        if (p / ".codex").is_dir() or (p / ".git").is_dir():
            return p

    return cwd


def get_max_bytes() -> int:
    return DEFAULT_MAX_BYTES


def now_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def save_dir_for(event: dict) -> Path:
    root = find_project_root(event)
    d = root / ".codex" / "saved_conversation"
    d.mkdir(parents=True, exist_ok=True)
    return d


def current_marker_path(save_dir: Path, session_id: str) -> Path:
    return save_dir / f"{session_id}-current.md"


def new_log_file(save_dir: Path, session_id: str) -> Path:
    base = save_dir / f"{session_id}-{now_stamp()}.md"

    # 极端情况下，同一秒内连续 rollover，避免重名
    if not base.exists():
        return base

    for i in range(1, 1000):
        candidate = save_dir / f"{session_id}-{now_stamp()}-{i}.md"
        if not candidate.exists():
            return candidate

    raise RuntimeError("failed to create unique log file name")


def read_current_file(marker: Path) -> Path | None:
    try:
        raw = marker.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None

    if not raw:
        return None

    p = Path(raw)
    if p.exists():
        return p

    return None


def write_current_file(marker: Path, log_file: Path) -> None:
    marker.write_text(str(log_file), encoding="utf-8")


def pick_log_file(event: dict, incoming_bytes: int) -> Path:
    save_dir = save_dir_for(event)
    session_id = safe_name(str(event.get("session_id", "")))
    marker = current_marker_path(save_dir, session_id)

    max_bytes = get_max_bytes()
    cur = read_current_file(marker)

    if cur is None:
        cur = new_log_file(save_dir, session_id)
        write_current_file(marker, cur)
        return cur

    try:
        cur_size = cur.stat().st_size
    except FileNotFoundError:
        cur = new_log_file(save_dir, session_id)
        write_current_file(marker, cur)
        return cur

    if cur_size + incoming_bytes > max_bytes:
        cur = new_log_file(save_dir, session_id)
        write_current_file(marker, cur)

    return cur


def append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def main() -> int:
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}, ensure_ascii=False))
        return 0

    event_name = event.get("hook_event_name")
    text = ""

    if event_name == "UserPromptSubmit":
        prompt = event.get("prompt", "")
        if prompt:
            text = f"\n\n## User\n\n{prompt.rstrip()}\n"

    elif event_name == "Stop":
        msg = event.get("last_assistant_message", "")
        if msg:
            text = f"\n\n## Assistant\n\n{msg.rstrip()}\n"

    if text:
        incoming_bytes = len(text.encode("utf-8"))
        log_file = pick_log_file(event, incoming_bytes)
        append(log_file, text)

    print(json.dumps({"continue": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
