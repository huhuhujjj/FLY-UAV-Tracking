"""Local single-user offline test web server.

Serves the interactive frontend from web/frontend and exposes a small JSON API
that wraps the existing offline pipeline (model/src/pipeline.py). Bindings are
restricted to 127.0.0.1 (localhost only). No arbitrary server file path is ever
read back to the client; only well-known job artifacts are served.

Requirements enforced here mirror the offline runner and the SRS draft:
  - one image (JPEG/PNG) -> detection only (no track IDs);
  - one recorded constant-rate MP4 -> detection + within-video temporary IDs;
  - at most one non-terminal job at a time; a busy request returns 409;
  - WAITING/RUNNING are active; SUCCEEDED/FAILED/INTERRUPTED are terminal;
  - results are the real pipeline artifacts (annotated.jpg / annotated.mp4,
    frames.jsonl, detections.csv, tracks.json, run.json).

This is a local test interface, not a production service and not a completed
system acceptance. It adds no live feed, flight control, geolocation, real-world
speed, face/plate recognition, cross-video identity, filtering or evaluation.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import traceback
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

# Make model/src importable regardless of the working directory.
_PROJECT = Path(__file__).resolve().parents[2]
if str(_PROJECT / "model") not in sys.path:
    sys.path.insert(0, str(_PROJECT / "model"))

from src.pipeline import run  # noqa: E402

WEB_FRONTEND = _PROJECT / "web" / "frontend"
JOB_ROOT = Path(os.environ.get("UAV_JOB_ROOT", _PROJECT / "web" / "backend" / "jobs"))
DEFAULT_WEIGHTS = Path(os.environ.get("UAV_WEIGHTS", _PROJECT / "model" / "weights" / "yolo26l.pt"))
DEFAULT_CONFIG = {"device": "cpu", "imgsz": 640, "conf": 0.25, "iou": 0.7, "max_det": 1000}

# Accepted media types and an upper-bound guard applied to uploads. These are
# pilot/test convenience limits, not frozen production limits (SRS draft keeps
# input limits pending pilot validation).
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png"}
ALLOWED_VIDEO_EXT = {".mp4"}
MAX_UPLOAD_BYTES = 256 * 1024 * 1024

_TERMINAL = {"SUCCEEDED", "FAILED", "INTERRUPTED"}


class _JobStore:
    """Process-local job records; restarting the service clears this index."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs = {}  # job_id -> dict

    def active_nonterminal_exists(self) -> bool:
        with self._lock:
            for job in self._jobs.values():
                if job.get("status") not in _TERMINAL:
                    return True
                # A cancelled (INTERRUPTED) job may still have a running worker
                # holding the exclusive pipeline lock; block new work until it ends.
                if not job.get("_worker_done", True):
                    return True
            return False

    def create(self, job_id: str, record: dict) -> None:
        with self._lock:
            self._jobs[job_id] = record

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(fields)

    def get(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            # Return a shallow copy so callers can't mutate shared state.
            return dict(job) if job is not None else None

    def list_ids(self):
        with self._lock:
            return list(self._jobs.keys())

    def mark_cancel_requested(self, job_id: str) -> bool:
        """Flag a non-terminal job as cancel-requested. Returns True if flagged."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.get("status") in _TERMINAL:
                return False
            job["_cancel_requested"] = True
            return True

    def cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job.get("_cancel_requested"))

    def mark_worker_done(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["_worker_done"] = True


STORE = _JobStore()


def _job_status_payload(job: dict) -> dict:
    """Public status view. Only exposes artifact names, never server paths."""
    payload = {
        "job_id": job["job_id"],
        "status": job["status"],
        "media_type": job.get("media_type"),
        "input_name": job.get("input_name"),
        "created_at": job.get("created_at"),
        "error": job.get("error"),
        "artifacts": job.get("artifacts"),
        "run": job.get("run_summary"),
    }
    return payload


def _summarize_run(run_path: Path) -> dict | None:
    try:
        data = json.loads(run_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {
        "status": data.get("status"),
        "frame_count": data.get("frame_count"),
        "detection_count": data.get("detection_count"),
        "video": data.get("video"),
        "config": data.get("config"),
        "elapsed_seconds": data.get("elapsed_seconds"),
        "threshold_status": data.get("config", {}).get("threshold_status"),
    }


def _artifact_list(run_path: Path) -> list[dict]:
    artifacts_dir = run_path / "artifacts"
    if not artifacts_dir.is_dir():
        return []
    entries = []
    for f in sorted(artifacts_dir.iterdir()):
        if f.is_file():
            entries.append({"name": f.name, "bytes": f.stat().st_size})
    return entries


def _read_detections(run_path: Path, limit: int = 500) -> dict:
    """Parse the pipeline's detections.csv into a bounded, serialisable view."""
    csv_path = run_path / "artifacts" / "detections.csv"
    if not csv_path.is_file():
        return {"total": 0, "truncated": False, "rows": []}
    import csv as _csv
    rows = []
    total = 0
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                if total >= limit:
                    total += 1
                    continue
                rows.append({
                    "detection_id": row.get("detection_id", ""),
                    "frame_index": row.get("frame_index", ""),
                    "timestamp_ms": row.get("timestamp_ms", ""),
                    "class_name": row.get("class_name", ""),
                    "confidence": row.get("confidence", ""),
                    "track_id": row.get("track_id", ""),
                    "x1": row.get("x1", ""),
                    "y1": row.get("y1", ""),
                    "x2": row.get("x2", ""),
                    "y2": row.get("y2", ""),
                })
                total += 1
    except (OSError, _csv.Error):
        return {"total": 0, "truncated": False, "rows": []}
    return {"total": total, "truncated": total > limit, "rows": rows}


def _detect_media_type(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_IMAGE_EXT:
        return "image"
    if ext in ALLOWED_VIDEO_EXT:
        return "video"
    return None


def _run_job(job_id: str, source: Path, media_type: str, weights: Path,
             input_name: str, device: str, imgsz: int, conf: float, iou: float,
             max_det: int) -> None:
    job_dir = JOB_ROOT / job_id
    output = job_dir / "run"
    try:
        if STORE.cancel_requested(job_id):
            # Cancel was requested before the worker actually started.
            STORE.update(job_id, status="INTERRUPTED",
                         error="任务已被取消。", artifacts=[],
                         run_summary=None)
            return
        STORE.update(job_id, status="RUNNING")
        result = run(source, weights, output, device, imgsz, conf, iou, max_det)
        if STORE.cancel_requested(job_id):
            # Cancel requested mid-run: the pipeline still finished, but we do not
            # publish results as a success.
            STORE.update(job_id, status="INTERRUPTED",
                         error="任务已被取消。", artifacts=[], run_summary=None)
            return
        run_summary = _summarize_run(output / "run.json")
        STORE.update(
            job_id,
            status="SUCCEEDED",
            artifacts=_artifact_list(output),
            run_summary=run_summary,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 - report any pipeline failure as terminal
        error_text = f"{type(exc).__name__}: {exc}"
        # Read a more precise error from run.json if the pipeline wrote one.
        run_json = output / "run.json"
        status = "FAILED"
        if run_json.is_file():
            try:
                data = json.loads(run_json.read_text(encoding="utf-8"))
                if data.get("error"):
                    error_text = data["error"]
                if data.get("status") in ("FAILED", "INTERRUPTED"):
                    status = data["status"]
            except (OSError, ValueError):
                pass
        if STORE.cancel_requested(job_id):
            status = "INTERRUPTED"
            error_text = "任务已被取消。"
        STORE.update(job_id, status=status, error=error_text,
                     artifacts=_artifact_list(output), run_summary=None)
        # The pipeline already wrote error.log for FAILED runs; keep it local.
    finally:
        # Remove the uploaded source copy; the job's artifacts live under job_dir.
        try:
            source.unlink(missing_ok=True)
        except OSError:
            pass
        # Release the single-job slot: the worker is done and the exclusive
        # pipeline lock it held has been released.
        STORE.mark_worker_done(job_id)


def _start_job(source: Path, media_type: str, input_name: str, device: str,
               imgsz: int, conf: float, iou: float, max_det: int) -> tuple[int, dict]:
    # Check the web worker first; pipeline.run also takes an OS file lock
    # shared with offline CLI runs. Records are not restored from disk.
    if STORE.active_nonterminal_exists():
        return HTTPStatus.CONFLICT, {"error": "busy", "message": "已有任务在处理中，请等待完成后再提交。"}
    job_id = uuid.uuid4().hex[:12]
    job_dir = JOB_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    weights = DEFAULT_WEIGHTS
    record = {
        "job_id": job_id,
        "status": "WAITING",
        "media_type": media_type,
        "input_name": input_name,
        "created_at": _now_iso(),
        "artifacts": [],
        "run_summary": None,
        "error": None,
        "_source": source,
        "_weights": weights,
        "_worker_done": False,
    }
    STORE.create(job_id, record)
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, source, media_type, weights, input_name, device, imgsz, conf, iou, max_det),
        daemon=True,
    )
    thread.start()
    return HTTPStatus.ACCEPTED, _job_status_payload(STORE.get(job_id))


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Handler(BaseHTTPRequestHandler):
    server_version = "UAVLocalTest/0.1"

    # HTTP response helpers.
    def _send_json(self, code: int, obj: dict, headers: dict | None = None) -> None:
        body = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str, download_name: str | None = None) -> None:
        if not path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": "产物不存在。"})
            return
        length = path.stat().st_size
        range_header = self.headers.get("Range")
        # Inline video needs byte-range responses for seeking. Explicit
        # downloads take the full-file path with Content-Disposition instead.
        if range_header and download_name is None:
            # Support a single byte range for media seeking (e.g. video playback).
            try:
                unit, _, spec = range_header.partition("=")
                start_s, _, end_s = spec.partition("-")
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else length - 1
                end = min(end, length - 1)
                if start > end or start >= length:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{length}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                chunk_len = end - start + 1
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{length}")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(chunk_len))
                self.end_headers()
                with path.open("rb") as f:
                    f.seek(start)
                    remaining = chunk_len
                    while remaining > 0:
                        block = f.read(min(64 * 1024, remaining))
                        if not block:
                            break
                        self.wfile.write(block)
                        remaining -= len(block)
                return
            except (ValueError, OSError):
                pass  # fall through to a full 200 response
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        if content_type.startswith("video/") or content_type.startswith("audio/"):
            self.send_header("Accept-Ranges", "bytes")
        if download_name:
            from urllib.parse import quote
            self.send_header("Content-Disposition", f'attachment; filename="{quote(download_name)}"')
        self.end_headers()
        with path.open("rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def _log_message(self, fmt, *args):  # keep logs quiet; rely on backend/logs
        pass

    # API routes and static file requests.
    def do_HEAD(self) -> None:
        # Minimal HEAD support (used by video/audio element probing).
        self.do_GET()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"ok": True, "service": "uav-local-test",
                                            "active_nonterminal_job": STORE.active_nonterminal_exists()})
            return

        if path == "/api/jobs":
            jobs = [_job_status_payload(STORE.get(jid)) for jid in STORE.list_ids()
                    if STORE.get(jid) is not None]
            self._send_json(HTTPStatus.OK, {"jobs": jobs})
            return

        # /api/jobs/<id>/detections
        if path.startswith("/api/jobs/") and path.endswith("/detections"):
            job_id = path[len("/api/jobs/"):-len("/detections")]
            job = STORE.get(job_id)
            if job is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": "任务不存在。"})
                return
            if job.get("status") != "SUCCEEDED":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": "检测记录不可用。"})
                return
            run_path = JOB_ROOT / job_id / "run"
            data = _read_detections(run_path)
            self._send_json(HTTPStatus.OK, data)
            return

        # /api/jobs/<id>
        if path.startswith("/api/jobs/"):
            job_id = path[len("/api/jobs/"):]
            job = STORE.get(job_id)
            if job is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": "任务不存在。"})
                return
            self._send_json(HTTPStatus.OK, _job_status_payload(job))
            return

        # /api/artifacts/<job_id>/<artifact_name>
        if path.startswith("/api/artifacts/"):
            rest = path[len("/api/artifacts/"):]
            # Normalize an optional "artifacts/" infix for compatibility.
            if rest.startswith("artifacts/"):
                rest = rest[len("artifacts/"):]
            parts = rest.split("/")
            if len(parts) != 2 or not all(parts):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad_request"})
                return
            job_id, artifact_name = parts
            # Reject any traversal tokens in the artifact name.
            if artifact_name in ("", ".", "..") or "/" in artifact_name or "\\" in artifact_name:
                self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
            job = STORE.get(job_id)
            if job is None or job.get("status") != "SUCCEEDED":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": "产物不可用。"})
                return
            artifacts_root = (JOB_ROOT / job_id / "run" / "artifacts").resolve()
            artifact_path = (artifacts_root / artifact_name).resolve()
            # Ensure the resolved path stays inside the job artifacts directory.
            if not str(artifact_path).startswith(str(artifacts_root) + os.sep):
                self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
            if artifact_name == "annotated.jpg":
                self._send_file(artifact_path, "image/jpeg")
            elif artifact_name == "annotated.mp4":
                self._send_file(artifact_path, "video/mp4")
            elif artifact_name in ("frames.jsonl", "detections.csv", "tracks.json", "run.json"):
                self._send_file(artifact_path, "application/octet-stream", artifact_name)
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        # Serve static frontend files.
        if path == "/" or path == "/workspace.html":
            self._serve_static("workspace.html")
            return
        self._serve_static(path.lstrip("/"))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/jobs":
            self._handle_upload()
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # /api/jobs/<id> -> cancel a non-terminal job.
        if path.startswith("/api/jobs/"):
            job_id = path[len("/api/jobs/"):]
            if not job_id or "/" in job_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad_request"})
                return
            job = STORE.get(job_id)
            if job is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": "任务不存在。"})
                return
            if job.get("status") in _TERMINAL:
                self._send_json(HTTPStatus.CONFLICT,
                                {"error": "already_terminal",
                                 "message": "任务已结束，无需取消。"})
                return
            STORE.mark_cancel_requested(job_id)
            # Keep the status RUNNING/WAITING so the single-job lock stays held
            # until the worker actually finishes and releases the pipeline lock.
            # The worker observes the cancel flag and transitions to INTERRUPTED.
            current = STORE.get(job_id)
            self._send_json(HTTPStatus.OK, _job_status_payload(current))
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    # Upload parsing and pilot input limits.
    def _handle_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self._send_json(HTTPStatus.BAD_REQUEST,
                            {"error": "bad_request", "message": "需要 multipart/form-data 上传。"})
            return

        # Parse a minimal multipart body (single "file" field is expected).
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length > MAX_UPLOAD_BYTES + 1024 * 1024:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                            {"error": "too_large", "message": "文件超出上传大小限制。"})
            return

        body = self.rfile.read(length)
        field_name, filename, data = _parse_multipart_single_file(body, content_type)
        if field_name is None:
            self._send_json(HTTPStatus.BAD_REQUEST,
                            {"error": "bad_request", "message": "无法解析上传文件。"})
            return
        if not filename:
            self._send_json(HTTPStatus.BAD_REQUEST,
                            {"error": "bad_request", "message": "请选择要提交的图片或视频文件。"})
            return
        if len(data) > MAX_UPLOAD_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                            {"error": "too_large", "message": "文件超出上传大小限制。"})
            return

        media_type = _detect_media_type(filename)
        if media_type is None:
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                            {"error": "unsupported_type",
                             "message": "仅支持 JPEG/PNG 图片或 MP4 视频。"})
            return

        # Keep the client filename as display metadata only. The upload uses
        # a server-generated directory; the worker removes this copy in finally.
        job_id = uuid.uuid4().hex[:12]
        job_dir = JOB_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        suffix = Path(filename).suffix.lower()
        source = job_dir / f"input{suffix}"
        source.write_bytes(data)

        device = self._query_device()
        imgsz = self._query_int("imgsz", DEFAULT_CONFIG["imgsz"])
        conf = self._query_float("conf", DEFAULT_CONFIG["conf"])
        iou = self._query_float("iou", DEFAULT_CONFIG["iou"])
        max_det = self._query_int("max_det", DEFAULT_CONFIG["max_det"])

        code, payload = _start_job(source, media_type, filename, device, imgsz, conf, iou, max_det)
        self._send_json(code, payload)

    def _query_device(self) -> str:
        value = self._query("device", "")
        if value in ("cpu", "0"):
            return value
        if value == "gpu":
            return "0"
        return DEFAULT_CONFIG["device"]

    def _query_int(self, name: str, default: int) -> int:
        raw = self._query(name, "")
        try:
            return int(raw) if raw else default
        except ValueError:
            return default

    def _query_float(self, name: str, default: float) -> float:
        raw = self._query(name, "")
        try:
            return float(raw) if raw else default
        except ValueError:
            return default

    def _query(self, name: str, default: str) -> str:
        parsed = urlparse(self.path)
        from urllib.parse import parse_qs
        values = parse_qs(parsed.query)
        return values.get(name, [default])[0]

    # Frontend files are restricted to WEB_FRONTEND.
    def _serve_static(self, rel: str) -> None:
        # Only the bare root redirects to the workspace index page. index.html is
        # the video page, so it keeps its own route.
        if rel == "":
            rel = "workspace.html"
        # Reject path traversal.
        candidate = (WEB_FRONTEND / rel).resolve()
        if not str(candidate).startswith(str(WEB_FRONTEND.resolve()) + os.sep) \
                and candidate != WEB_FRONTEND.resolve():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
            return
        if not candidate.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        content_type = _content_type_for(candidate)
        self._send_file(candidate, content_type)


def _content_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".json": "application/json; charset=utf-8",
    }.get(ext, "application/octet-stream")


def _parse_multipart_single_file(body: bytes, content_type: str):
    """Extract the first file part (field name, filename, data) from a raw body."""
    boundary = None
    for piece in content_type.split(";"):
        piece = piece.strip()
        if piece.startswith("boundary="):
            boundary = piece[len("boundary="):].strip('"')
    if not boundary:
        return None, None, b""
    marker = b"--" + boundary.encode("utf-8")
    parts = body.split(marker)
    for part in parts:
        if b"\r\n\r\n" not in part:
            continue
        header_blob, data = part.split(b"\r\n\r\n", 1)
        if b"filename=" not in header_blob:
            continue
        # data ends with \r\n
        if data.endswith(b"\r\n"):
            data = data[:-2]
        header_text = header_blob.decode("utf-8", errors="replace")
        field_name = None
        filename = None
        for line in header_text.split("\r\n"):
            if line.lower().startswith("content-disposition"):
                for token in line.split(";"):
                    token = token.strip()
                    if token.startswith("name="):
                        field_name = token[5:].strip('"')
                    elif token.startswith("filename="):
                        filename = token[9:].strip('"')
        if filename is not None:
            return field_name or "file", filename, data
    return None, None, b""


def main() -> None:
    host = "127.0.0.1"
    port = int(os.environ.get("UAV_PORT", "8765"))
    JOB_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving local UAV test interface at http://{host}:{port}/", flush=True)
    print("Stop with Ctrl+C. Only this machine can reach this service.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
