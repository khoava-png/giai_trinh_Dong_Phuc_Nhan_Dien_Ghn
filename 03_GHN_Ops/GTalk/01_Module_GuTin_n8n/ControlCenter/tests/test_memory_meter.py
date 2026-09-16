"""
Unit Tests cho Memory Meter Utility.
"""

import os
import time
import unittest
from datetime import datetime
from typing import Any, Dict

import psutil

from memory_meter import (
    _APP_COMMIT,
    _BOOT_ID,
    _resolve_app_commit,
    measure_memory_usage,
)


class TestMemoryMeter(unittest.TestCase):
    """Unit tests toàn diện cho Memory Meter utility."""

    def test_all_metrics_and_types(self) -> None:
        """Kiểm tra đầy đủ tất cả các trường trong dictionary trả về."""
        res: Dict[str, Any] = measure_memory_usage(
            job_id="JOB_TEST_01", phase="TEST_RUN"
        )

        self.assertNotEqual(res["app_commit"], "local-workspace")
        self.assertEqual(res["app_commit"], _APP_COMMIT)
        self.assertEqual(res["boot_id"], _BOOT_ID)
        self.assertEqual(res["pid"], os.getpid())
        self.assertEqual(res["job_id"], "JOB_TEST_01")
        self.assertEqual(res["phase"], "TEST_RUN")

        self.assertIn("timestamp", res)
        dt = datetime.fromisoformat(res["timestamp"])
        self.assertIsNotNone(dt.tzinfo)

        self.assertIsNotNone(res["uptime_sec"])
        self.assertGreaterEqual(res["uptime_sec"], 0.0)

        self.assertIsNotNone(res["memory_rss_bytes"])
        self.assertGreater(res["memory_rss_bytes"], 0)

        self.assertIsNotNone(res["memory_rss_mib"])
        self.assertGreater(res["memory_rss_mib"], 0.0)

        self.assertEqual(res["status"], "success")

    def test_boot_id_persistence(self) -> None:
        """Kiểm tra boot_id giữ nguyên giữa nhiều lần gọi."""
        res1 = measure_memory_usage(job_id="J1", phase="P1")
        res2 = measure_memory_usage(job_id="J2", phase="P2")
        self.assertEqual(res1["boot_id"], res2["boot_id"])

    def test_resolve_app_commit_branches(self) -> None:
        """Kiểm tra các nhánh của _resolve_app_commit."""
        commit_val = _resolve_app_commit()
        self.assertTrue(commit_val is None or isinstance(commit_val, str))

        os.environ["RENDER_GIT_COMMIT"] = "abcdef123"
        try:
            self.assertEqual(_resolve_app_commit(), "abcdef123")
        finally:
            os.environ.pop("RENDER_GIT_COMMIT", None)

        import subprocess

        original_run = subprocess.run
        try:

            def mock_run_error(*args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("Git binary not found")

            subprocess.run = mock_run_error  # type: ignore

            os.environ.pop("RENDER_GIT_COMMIT", None)
            os.environ.pop("COMMIT_SHA", None)

            c = _resolve_app_commit()
            self.assertIsNone(c)
        finally:
            subprocess.run = original_run

    def test_psutil_process_error(self) -> None:
        """Kiểm tra nhánh lỗi khi psutil.Process() ném ngoại lệ."""
        original_process = psutil.Process
        try:

            def mock_process_error(*args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("Simulated psutil.Process error")

            psutil.Process = mock_process_error

            res = measure_memory_usage(job_id="J_ERR", phase="ERR_PHASE")
            self.assertTrue(res["status"].startswith("error"))
            self.assertIsNone(res["memory_rss_bytes"])
            self.assertIsNone(res["memory_rss_mib"])
        finally:
            psutil.Process = original_process

    def test_process_create_time_error(self) -> None:
        """Kiểm tra nhánh lỗi khi process.create_time() ném ngoại lệ."""
        original_process = psutil.Process

        class MockProcessCreateError:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def create_time(self) -> float:
                raise RuntimeError("Simulated create_time error")

            def memory_info(self) -> Any:
                class DummyMem:
                    rss = 1024

                return DummyMem()

        try:
            psutil.Process = MockProcessCreateError  # type: ignore
            res = measure_memory_usage(job_id="J_ERR_TIME", phase="ERR_TIME")
            self.assertTrue(res["status"].startswith("error"))
            self.assertIsNone(res["memory_rss_bytes"])
        finally:
            psutil.Process = original_process

    def test_process_memory_info_error(self) -> None:
        """Kiểm tra nhánh lỗi khi process.memory_info() ném ngoại lệ."""
        original_process = psutil.Process

        class MockProcessMemError:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def create_time(self) -> float:
                return time.time() - 10.0

            def memory_info(self) -> Any:
                raise RuntimeError("Simulated memory_info error")

        try:
            psutil.Process = MockProcessMemError  # type: ignore
            res = measure_memory_usage(job_id="J_ERR_MEM", phase="ERR_MEM")
            self.assertTrue(res["status"].startswith("error"))
            self.assertIsNone(res["memory_rss_bytes"])
        finally:
            psutil.Process = original_process


if __name__ == "__main__":
    unittest.main()
