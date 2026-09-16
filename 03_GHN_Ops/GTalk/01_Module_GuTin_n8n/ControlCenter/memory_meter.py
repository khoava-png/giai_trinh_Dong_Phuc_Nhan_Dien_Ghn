"""
Memory Meter Utility
-------------------
Utility cung cấp các hàm đo lường bộ nhớ (RSS, uptime,
pid, boot_id, app_commit) an toàn, trả về cấu trúc
JSON chuẩn cho GHN Control Center.
"""

from datetime import datetime, timezone
import os
import subprocess
import time
from typing import Any, Dict, Optional
import psutil


def _resolve_app_commit() -> Optional[str]:
    """Lấy Git commit SHA."""
    c_env = os.environ.get("RENDER_GIT_COMMIT")
    commit = c_env or os.environ.get("COMMIT_SHA")
    if commit:
        return commit.strip()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return None


_APP_COMMIT: Optional[str] = _resolve_app_commit()
_BOOT_ID: str = f"boot-{int(time.time())}"


def measure_memory_usage(
    job_id: str = "INIT", phase: str = "BOOT"
) -> Dict[str, Any]:
    """
    Đo lường bộ nhớ RSS.

    Args:
        job_id (str): Mã công việc.
        phase (str): Giai đoạn.

    Returns:
        Dict[str, Any]: Từ điển commit, boot_id,
        PID, uptime, RSS bytes/MiB,
        timestamp và status.
    """
    ts_utc = timezone.utc
    timestamp_str = datetime.now(
        ts_utc
    ).isoformat()

    result: Dict[str, Any] = {
        "app_commit": _APP_COMMIT,
        "boot_id": _BOOT_ID,
        "pid": None,
        "job_id": job_id,
        "phase": phase,
        "timestamp": timestamp_str,
        "uptime_sec": 0.0,
        "memory_rss_bytes": None,
        "memory_rss_mib": None,
        "status": "unavailable",
    }

    try:
        pid = os.getpid()
        result["pid"] = pid

        process = psutil.Process(pid)
        uptime_sec = time.time() - process.create_time()
        result["uptime_sec"] = round(float(uptime_sec), 2)

        mem_info = process.memory_info()
        rss_bytes = int(mem_info.rss)
        result["memory_rss_bytes"] = rss_bytes
        result["memory_rss_mib"] = round(
            rss_bytes / (1024 * 1024), 2
        )

        result["status"] = "success"
    except Exception as e:
        result["status"] = f"error: {str(e)}"

    return result
