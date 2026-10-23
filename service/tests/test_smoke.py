import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


SERVICE_DIR = Path(__file__).resolve().parents[1]


class ServiceSmokeTest(unittest.TestCase):
    def test_restart_keeps_database_and_health_hides_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]

            env = os.environ.copy()
            env.update(
                SONAR_DATA_DIR=str(Path(tmp) / "data"),
                SONAR_PORT=str(port),
                SONAR_TEST_SECRET="test-secret-sentinel",
                SONAR_PUMPPORTAL_ENABLED="0",
                SONAR_SHRINE_ENABLED="0",
                SONAR_RISK_ENABLED="0",
            )
            db_path = Path(env["SONAR_DATA_DIR"]) / "sonar.db"

            for attempt in range(2):
                process = subprocess.Popen(
                    [sys.executable, "-m", "sonar"],
                    cwd=SERVICE_DIR,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    for _ in range(50):
                        if process.poll() is not None:
                            self.fail(f"service exited early: {process.stderr.read()}")
                        try:
                            with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                                body = response.read().decode()
                            break
                        except URLError:
                            time.sleep(0.1)
                    else:
                        self.fail("health endpoint did not start")

                    self.assertEqual(json.loads(body), {"status": "ok"})
                    self.assertNotIn(env["SONAR_TEST_SECRET"], body)
                    with urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                        self.assertIn("<title>Sonar</title>", response.read().decode())
                    with sqlite3.connect(db_path) as db:
                        self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
                        if attempt == 0:
                            db.execute(
                                "INSERT INTO candidates (mint, first_seen_ms, last_seen_ms) VALUES (?, ?, ?)",
                                ("mint-1", 1000, 1000),
                            )
                            db.execute(
                                "INSERT INTO candidate_events (mint, kind, source, received_ms) VALUES (?, ?, ?, ?)",
                                ("mint-1", "launch", "pumpportal", 1000),
                            )
                        else:
                            self.assertEqual(
                                db.execute(
                                    "SELECT first_seen_ms FROM candidates WHERE mint = ?", ("mint-1",)
                                ).fetchone()[0],
                                1000,
                            )
                            self.assertEqual(
                                db.execute(
                                    "SELECT kind FROM candidate_events WHERE mint = ?", ("mint-1",)
                                ).fetchone()[0],
                                "launch",
                            )
                finally:
                    process.terminate()
                    _, logs = process.communicate(timeout=5)
                    self.assertNotIn(env["SONAR_TEST_SECRET"], logs)
                    for line in logs.splitlines():
                        self.assertIn("message", json.loads(line))


if __name__ == "__main__":
    unittest.main()
