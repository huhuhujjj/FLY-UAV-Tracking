"""Run each browser test against its own server and temporary job directory."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
TESTS = ["e2e_test.js", "e2e_dragdrop_test.js", "e2e_reliability_test.js",
         "e2e_cancel_test.js", "e2e_i18n_test.js", "e2e_nav_test.js"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node", help="Node.js executable")
    parser.add_argument("--output", type=Path, default=PROJECT / ".qa" / "e2e")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for script in TESTS:
        # A fresh process prevents browser refresh tests from inheriting another
        # test's in-memory task list. User jobs and the normal service stay intact.
        with tempfile.TemporaryDirectory(prefix="uav_e2e_") as job_root:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            base = f"http://127.0.0.1:{port}"
            env = {**os.environ, "UAV_PORT": str(port), "UAV_JOB_ROOT": job_root,
                   "UAV_BASE": base, "PYTHONIOENCODING": "utf-8"}
            with (args.output / f"{script}.server.log").open("w", encoding="utf-8") as server_log:
                server = subprocess.Popen([sys.executable, str(HERE / "run.py")], cwd=PROJECT,
                                          env=env, stdout=server_log, stderr=subprocess.STDOUT)
                try:
                    deadline = time.monotonic() + 30
                    while True:
                        if server.poll() is not None:
                            raise RuntimeError(f"Server exited before {script}; see server log")
                        try:
                            with urlopen(base + "/api/health", timeout=1) as response:
                                if response.status == 200:
                                    break
                        except OSError:
                            if time.monotonic() >= deadline:
                                raise TimeoutError("Test server did not become ready")
                            time.sleep(0.2)
                    result = subprocess.run([args.node, str(HERE / script)], cwd=HERE, env=env,
                                            capture_output=True, encoding="utf-8", errors="replace", timeout=600)
                    (args.output / f"{script}.log").write_text(
                        result.stdout + result.stderr + f"\nexit_code={result.returncode}\n", encoding="utf-8")
                    results.append({"script": script, "exit_code": result.returncode})
                    print(f"{script}: {'PASS' if result.returncode == 0 else 'FAIL'}", flush=True)
                finally:
                    server.terminate()
                    try:
                        server.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait()
    summary = {"run_at_utc": datetime.now(timezone.utc).isoformat(), "tests": results,
               "scope": "Development checks on pilot media; not accuracy or system acceptance."}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return int(any(r["exit_code"] != 0 for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
