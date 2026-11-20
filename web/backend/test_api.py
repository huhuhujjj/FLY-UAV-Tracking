"""Backend/API tests for the local offline test server.

These run against a live server in-process (threaded) and submit real pilot
media, exercising: image processing, video processing, invalid/corrupt files,
task status transitions, the single non-terminal job limit, result downloads,
and failure states. They do not test detector accuracy.

Run from the project root:

    model/.venv/Scripts/python.exe -m unittest web.backend.test_api -v

Requires the offline pipeline environment (model/.venv) and the step3 pilot
media under model/data/processed/step3_pilot/.
"""
from __future__ import annotations

import io
import json
import os
import sys
import threading
import time
import unittest
import uuid
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
if str(PROJECT / "web" / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT / "web" / "backend"))
if str(PROJECT / "model") not in sys.path:
    sys.path.insert(0, str(PROJECT / "model"))

# Isolate test jobs from real jobs before importing the server module.
import tempfile  # noqa: E402
_TEST_JOB_ROOT = Path(tempfile.mkdtemp(prefix="uav_test_jobs_"))
os.environ["UAV_JOB_ROOT"] = str(_TEST_JOB_ROOT)

import server  # noqa: E402
from server import Handler, STORE  # noqa: E402

PILOT = PROJECT / "model" / "data" / "processed" / "step3_pilot"
IMAGE = PILOT / "image.jpg"
VIDEO = PILOT / "clip.mp4"
CORRUPT_JPG = PILOT / "corrupt.jpg"
CORRUPT_MP4 = PILOT / "corrupt.mp4"

HOST = "127.0.0.1"


def _free_port() -> int:
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class ServerContext:
    def __init__(self):
        self.port = _free_port()
        self.httpd = None
        self.thread = None

    def start(self):
        # Use a fresh, empty job root per test session to avoid collisions.
        self.httpd = server.ThreadingHTTPServer((HOST, self.port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    @property
    def base(self):
        return f"http://{HOST}:{self.port}"


CTX = ServerContext()


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not IMAGE.is_file() or not VIDEO.is_file():
            raise unittest.SkipTest("step3 pilot media missing; cannot run API tests")
        # Ensure a clean job store.
        STORE._jobs.clear()
        CTX.start()

    @classmethod
    def tearDownClass(cls):
        CTX.stop()
        import shutil
        shutil.rmtree(_TEST_JOB_ROOT, ignore_errors=True)

    def _post_file(self, path: Path, extra_query=""):
        import urllib.request
        import mimetypes
        boundary = "----wb" + uuid.uuid4().hex
        data = path.read_bytes()
        name = path.name
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
        url = f"{CTX.base}/api/jobs"
        if extra_query:
            url += "?" + extra_query
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            resp = urllib.request.urlopen(req)
            return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def _get(self, path):
        import urllib.request
        req = urllib.request.Request(f"{CTX.base}{path}")
        try:
            resp = urllib.request.urlopen(req)
            return resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    def _delete(self, path):
        import urllib.request
        req = urllib.request.Request(f"{CTX.base}{path}", method="DELETE")
        try:
            resp = urllib.request.urlopen(req)
            return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def _wait_terminal(self, job_id, timeout=300):
        deadline = time.time() + timeout
        while time.time() < deadline:
            status, body, _ = self._get(f"/api/jobs/{job_id}")
            if status == 200 and body and json.loads(body.decode("utf-8"))["status"] in ("SUCCEEDED", "FAILED", "INTERRUPTED"):
                return json.loads(body.decode("utf-8"))
            time.sleep(1.0)
        raise AssertionError(f"job {job_id} did not reach a terminal state in {timeout}s")

    def test_health(self):
        status, body, _ = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body.decode("utf-8"))["ok"])

    def test_image_detection_flow(self):
        code, job = self._post_file(IMAGE)
        self.assertIn(code, (202, 200))
        self.assertEqual(job["media_type"], "image")
        self.assertIn(job["status"], ("WAITING", "RUNNING"))
        final = self._wait_terminal(job["job_id"])
        self.assertEqual(final["status"], "SUCCEEDED")
        self.assertIsNone(final["error"])
        names = {a["name"] for a in final["artifacts"]}
        self.assertTrue(names >= {"annotated.jpg", "frames.jsonl", "detections.csv", "tracks.json"})
        # Image detection only: no track IDs, run.json confirms frame_count == 1.
        run = final["run"]
        self.assertEqual(run["frame_count"], 1)
        # Download the annotated image.
        status, content, headers = self._get(f"/api/artifacts/{job['job_id']}/annotated.jpg")
        self.assertEqual(status, 200)
        self.assertGreater(len(content), 0)
        self.assertEqual(headers["Content-Type"], "image/jpeg")

    def test_video_tracking_flow(self):
        code, job = self._post_file(VIDEO)
        self.assertIn(code, (202, 200))
        self.assertEqual(job["media_type"], "video")
        final = self._wait_terminal(job["job_id"])
        self.assertEqual(final["status"], "SUCCEEDED")
        names = {a["name"] for a in final["artifacts"]}
        self.assertTrue(names >= {"annotated.mp4", "frames.jsonl", "detections.csv", "tracks.json"})
        run = final["run"]
        self.assertEqual(run["frame_count"], 48)
        self.assertGreater(run["detection_count"], 0)
        status, content, headers = self._get(f"/api/artifacts/{job['job_id']}/annotated.mp4")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "video/mp4")

    def test_corrupt_image_fails(self):
        code, job = self._post_file(CORRUPT_JPG)
        self.assertIn(code, (202, 200))
        final = self._wait_terminal(job["job_id"])
        self.assertEqual(final["status"], "FAILED")
        self.assertIsNotNone(final["error"])
        # No success artifacts published.
        self.assertEqual(final["artifacts"], [])

    def test_corrupt_video_fails(self):
        code, job = self._post_file(CORRUPT_MP4)
        self.assertIn(code, (202, 200))
        final = self._wait_terminal(job["job_id"])
        self.assertEqual(final["status"], "FAILED")
        self.assertIsNotNone(final["error"])

    def test_unsupported_type_rejected(self):
        # A .txt file should be rejected with 415 before any job is created.
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / "not_media.txt"
        tmp.write_bytes(b"not media")
        try:
            code, body = self._post_file(tmp)
            self.assertEqual(code, 415)
            self.assertEqual(body["error"], "unsupported_type")
        finally:
            tmp.unlink(missing_ok=True)
            tmp.parent.rmdir()

    def test_single_nonterminal_job_limit(self):
        # Submit the (short) video first; it occupies the single-job slot.
        code, first = self._post_file(VIDEO)
        self.assertIn(code, (202, 200))
        # Immediately try a second submission; it must be rejected with 409.
        code2, body2 = self._post_file(IMAGE)
        self.assertEqual(code2, 409)
        self.assertEqual(body2["error"], "busy")
        # Wait for the first job to finish, then a new submission must be accepted.
        self._wait_terminal(first["job_id"])
        code3, third = self._post_file(IMAGE)
        self.assertIn(code3, (202, 200))
        self._wait_terminal(third["job_id"])

    def test_download_guard_blocks_path_traversal(self):
        # A traversal in the artifact name must not resolve outside the job dir.
        code, job = self._post_file(IMAGE)
        self._wait_terminal(job["job_id"])
        status, content, _ = self._get(f"/api/artifacts/{job['job_id']}/..%2f..%2f..%2fserver.py")
        self.assertNotEqual(status, 200)

    def test_unknown_job_404(self):
        status, _, _ = self._get("/api/jobs/doesnotexist")
        self.assertEqual(status, 404)

    def test_detections_endpoint(self):
        code, job = self._post_file(IMAGE)
        self.assertIn(code, (202, 200))
        self._wait_terminal(job["job_id"])
        status, body, _ = self._get(f"/api/jobs/{job['job_id']}/detections")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("total", data)
        self.assertIn("rows", data)
        self.assertGreater(data["total"], 0)
        # Rows are bounded and carry the expected fields.
        self.assertLessEqual(len(data["rows"]), 500)
        first = data["rows"][0]
        for key in ("class_name", "confidence", "x1", "y1"):
            self.assertIn(key, first)

    def test_cancel_nonterminal_job(self):
        code, job = self._post_file(VIDEO)
        self.assertIn(code, (202, 200))
        # Cancel while it is (likely) still running/queued.
        status, body = self._delete(f"/api/jobs/{job['job_id']}")
        self.assertIn(status, (200, 409))
        if status == 200:
            # Cancellation is requested but the worker is still winding down;
            # the status stays non-terminal until the worker releases the lock.
            self.assertIn(body["status"], ("WAITING", "RUNNING"))
        # Wait for the cancelled job to reach the terminal INTERRUPTED state.
        final = self._wait_terminal(job["job_id"], timeout=300)
        self.assertEqual(final["status"], "INTERRUPTED")
        self.assertEqual(final["artifacts"], [])
        # After the slot frees up, a new job is accepted and succeeds.
        code2, second = self._post_file(IMAGE)
        self.assertIn(code2, (202, 200))
        final2 = self._wait_terminal(second["job_id"])
        self.assertEqual(final2["status"], "SUCCEEDED")

    def test_cancel_terminal_job_conflict(self):
        code, job = self._post_file(IMAGE)
        self._wait_terminal(job["job_id"])
        status, body = self._delete(f"/api/jobs/{job['job_id']}")
        self.assertEqual(status, 409)
        self.assertEqual(body["error"], "already_terminal")


if __name__ == "__main__":
    unittest.main()
