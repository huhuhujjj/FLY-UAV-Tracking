"""Single-input offline pilot. Outputs are published only after media verification."""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import traceback
from types import SimpleNamespace
from contextlib import contextmanager

PROJECT = Path(__file__).resolve().parents[2]
CLASSES = ("car", "bus", "truck")
# COCO model IDs mapped to the project order above; these are not VisDrone IDs.
COCO_IDS = {2: 0, 5: 1, 7: 2}
SCHEMA = "uav-offline-0.1"


def write_json(path, value):
    """Replace the JSON file after serialization so readers never see half a write."""
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@contextmanager
def exclusive_job(path):
    """OS file lock releases on crash; a stale filename is harmless."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as f:
        f.seek(0, 2)
        if f.tell() == 0:
            f.write(b"0")
            f.flush()
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            raise RuntimeError("Another offline job is active") from exc
        try:
            yield
        finally:
            f.seek(0)
            if os.name == "nt":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def recover_interrupted(root):
    """Repair offline run metadata after a crash; this does not restore web jobs."""
    # Called only after obtaining the process-wide project lock.
    for path in Path(root).rglob("run.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if record.get("schema_version") == SCHEMA and record.get("status") == "RUNNING":
            record.update(status="INTERRUPTED", outputs=None,
                          error="Recovered after previous process released its OS job lock without a terminal status")
            write_json(path, record)


def probe_video(path):
    """Use actual decoded PTS. The initial writer supports constant-rate MP4."""
    command = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_frames", "-show_streams", "-show_entries",
               "frame=best_effort_timestamp_time:stream=width,height,avg_frame_rate",
               "-of", "json", str(path)]
    data = json.loads(subprocess.check_output(command, stderr=subprocess.STDOUT))
    stream = data["streams"][0]
    raw_times = [float(f["best_effort_timestamp_time"]) for f in data["frames"]]
    if not raw_times or not all(math.isfinite(t) for t in raw_times):
        raise ValueError("Video has no valid frame timestamps")
    numerator, denominator = map(int, stream["avg_frame_rate"].split("/"))
    fps = numerator / denominator if denominator else 0
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Video FPS is unavailable")
    times = [1000 * (t - raw_times[0]) for t in raw_times]
    if any(t <= s for s, t in zip(times, times[1:])):
        raise ValueError("Non-monotonic video timestamps")
    if any(abs(t - i * 1000 / fps) > 1.0 for i, t in enumerate(times)):
        raise ValueError("Variable frame rate is not supported by this pilot; no silent retiming")
    return {"width": int(stream["width"]), "height": int(stream["height"]),
            "fps": fps, "timestamps_ms": times, "source_start_pts_seconds": raw_times[0]}


def observations(result, frame_index, timestamp_ms, tracks):
    """Retain every detection, including those not associated with a track."""
    rows = []
    boxes = result.boxes.cpu().numpy()
    by_index = {}
    if tracks is not None:
        for tracked in tracks.update(boxes, result.orig_img):
            by_index[int(tracked[-1])] = int(tracked[4])
    width, height = result.orig_shape[1], result.orig_shape[0]
    for i, (xyxy, score, category) in enumerate(zip(boxes.xyxy, boxes.conf, boxes.cls)):
        local = COCO_IDS[int(category)]
        x1, y1, x2, y2 = map(float, xyxy)
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("Detector returned invalid source-image coordinates")
        rows.append({"detection_id": f"{frame_index}:{i}", "frame_index": frame_index,
                     "timestamp_ms": round(timestamp_ms, 6),
                     "timestamp_seconds": round(timestamp_ms / 1000, 9),
                     "class_id": local, "class_name": CLASSES[local],
                     "confidence": float(score), "track_id": by_index.get(i),
                     "bbox_xyxy": [x1, y1, x2, y2],
                     "center_xy": [(x1+x2)/2, (y1+y2)/2]})
    # Lost tracks are never synthesized as current detections.
    return rows


def annotate(image, rows, paths):
    import cv2
    colors = [(80, 210, 110), (245, 170, 50), (80, 140, 245)]
    for row in rows:
        x1, y1, x2, y2 = (round(v) for v in row["bbox_xyxy"])
        color = colors[row["class_id"]]
        suffix = "" if row["track_id"] is None else f' ID {row["track_id"]}'
        label = f'{row["class_name"]} {row["confidence"]:.2f}{suffix}'
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(image, label, (x1, max(14, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1, cv2.LINE_AA)
        tid = row["track_id"]
        if tid is not None:
            previous = paths.get(tid)
            # Draw only contiguous observations of the same class.
            if previous and previous[-1]["frame_index"] == row["frame_index"] - 1 and previous[-1]["class_id"] == row["class_id"]:
                points = [row]
                for old in reversed(previous[-29:]):
                    if old["frame_index"] != points[0]["frame_index"] - 1 or old["class_id"] != row["class_id"]:
                        break
                    points.insert(0, old)
                import numpy as np
                cv2.polylines(image, [np.array([p["center_xy"] for p in points], dtype="int32")], False, color, 2)
            paths.setdefault(tid, []).append(row)
    return image


def run(source, weights, output, device="cpu", imgsz=640, conf=.25, iou=.7, max_det=1000):
    os.environ.setdefault("YOLO_CONFIG_DIR", str(PROJECT/"model/experiments/.ultralytics"))
    os.environ.setdefault("MPLCONFIGDIR", str(PROJECT/"model/experiments/.matplotlib"))
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
    import cv2
    import numpy as np
    import torch
    from ultralytics import YOLO
    from ultralytics.trackers.byte_tracker import BYTETracker

    source, weights, output = Path(source).resolve(), Path(weights).resolve(), Path(output).resolve()
    if not 0 <= conf <= 1 or not 0 <= iou <= 1 or imgsz <= 0 or max_det <= 0:
        raise ValueError("Invalid inference parameters")
    with exclusive_job(PROJECT / "model/experiments/.offline.lock"):
        recover_interrupted(PROJECT / "model/experiments")
        output.mkdir(parents=True, exist_ok=False)
        work = output / ".staging"
        work.mkdir()
        status = {"schema_version": SCHEMA, "status": "RUNNING",
                  "run_id": output.name,
                  "source": str(source), "weights": str(weights), "outputs": None,
                  "pipeline_sha256": sha256(Path(__file__))}
        write_json(output/"run.json", status)
        cap = writer = None
        started = time.perf_counter()
        try:
            if not source.is_file() or not weights.is_file():
                raise FileNotFoundError("Input media or local model weights missing")
            extension = source.suffix.lower()
            is_image = extension in {".jpg", ".jpeg", ".png"}
            if not is_image and extension != ".mp4":
                raise ValueError("Pilot accepts JPEG/PNG or constant-rate MP4")
            metadata = None if is_image else probe_video(source)
            if metadata and (metadata["width"] % 2 or metadata["height"] % 2):
                raise ValueError("H264 yuv420 pilot needs even dimensions; no silent resize")
            if device != "cpu" and not torch.cuda.is_available():
                raise RuntimeError("CUDA requested but unavailable; no implicit CPU fallback")
            if device != "cpu":
                torch.cuda.set_device(int(device))
                torch.cuda.reset_peak_memory_stats(int(device))
            model = YOLO(str(weights), task="detect")
            if any(model.names.get(key) != CLASSES[value] for key, value in COCO_IDS.items()):
                raise ValueError("This pilot requires the verified COCO car/bus/truck mapping")
            tracker_config = {"tracker_type": "bytetrack", "track_high_thresh": .25,
                              "track_low_thresh": .1, "new_track_thresh": .25,
                              "track_buffer": 30, "match_thresh": .8, "fuse_score": True}
            tracker = None if is_image else BYTETracker(SimpleNamespace(**tracker_config))
            # A new tracker and detector are constructed for every video.
            if tracker is not None:
                tracker.reset()
            if is_image:
                image = cv2.imdecode(np.fromfile(source, dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is None:
                    raise ValueError("Image cannot be decoded")
            else:
                cap = cv2.VideoCapture(str(source))
                if not cap.isOpened():
                    raise ValueError("Video cannot be opened")
                writer = cv2.VideoWriter(str(work/"intermediate.avi"), cv2.VideoWriter_fourcc(*"MJPG"),
                                         metadata["fps"], (metadata["width"], metadata["height"]))
                if not writer.isOpened():
                    raise RuntimeError("Video writer unavailable")
            paths, inference_ms, count, n_detections = {}, [], 0, 0
            columns = ["detection_id", "frame_index", "timestamp_ms", "timestamp_seconds", "class_id",
                       "class_name", "confidence", "track_id", "x1", "y1", "x2", "y2", "cx", "cy"]
            with (work/"frames.jsonl").open("w", encoding="utf-8") as jf, (work/"detections.csv").open("w", newline="", encoding="utf-8") as cf:
                csv_writer = csv.DictWriter(cf, fieldnames=columns)
                csv_writer.writeheader()
                while True:
                    if is_image:
                        frame, timestamp = image, 0.0
                    else:
                        ok, frame = cap.read()
                        if not ok:
                            break
                        if count >= len(metadata["timestamps_ms"]):
                            raise ValueError("Decoder returned unexpected extra frames")
                        timestamp = metadata["timestamps_ms"][count]
                        if frame.shape[:2] != (metadata["height"], metadata["width"]):
                            raise ValueError("Decoded dimensions changed")
                    if count == 0:
                        print("First frame decoded; starting inference", flush=True)
                    if device != "cpu":
                        torch.cuda.synchronize(int(device))
                    tick = time.perf_counter()
                    result = model.predict(frame, device=device, imgsz=imgsz, conf=conf, iou=iou,
                                           classes=list(COCO_IDS), max_det=max_det, verbose=False)[0]
                    if device != "cpu":
                        torch.cuda.synchronize(int(device))
                    inference_ms.append(1000*(time.perf_counter()-tick))
                    if count == 0:
                        print("First inference finished; associating detections", flush=True)
                    rows = observations(result, count, timestamp, tracker)
                    item = {"frame_index": count, "timestamp_ms": round(timestamp, 6),
                            "width": frame.shape[1], "height": frame.shape[0], "detections": rows}
                    jf.write(json.dumps(item, allow_nan=False)+"\n")
                    for row in rows:
                        flat = {k: row[k] for k in columns if k in row}
                        flat.update(dict(zip(("x1", "y1", "x2", "y2"), row["bbox_xyxy"])))
                        flat.update(cx=row["center_xy"][0], cy=row["center_xy"][1])
                        csv_writer.writerow(flat)
                    annotated = annotate(frame.copy(), rows, paths)
                    if is_image:
                        if not cv2.imwrite(str(work/"annotated.jpg"), annotated):
                            raise RuntimeError("Image export failed")
                    else:
                        writer.write(annotated)
                    count += 1
                    n_detections += len(rows)
                    if not is_image and count % 12 == 0:
                        status.update(frames_processed=count, elapsed_seconds=time.perf_counter()-started)
                        write_json(output/"run.json", status)
                        print(f"Processed {count}/{len(metadata['timestamps_ms'])} frames", flush=True)
                    if is_image:
                        break
            if not is_image:
                cap.release()
                writer.release()
                cap = writer = None
                if count != len(metadata["timestamps_ms"]):
                    raise ValueError("Video decode ended early; partial output is not success")
                subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(work/"intermediate.avi"),
                                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                                "-movflags", "+faststart", str(work/"annotated.mp4")], check=True)
                verified = probe_video(work/"annotated.mp4")
                if len(verified["timestamps_ms"]) != count or verified["width"] != metadata["width"] or verified["height"] != metadata["height"]:
                    raise RuntimeError("Exported video frame count/dimensions mismatch")
                if max(abs(a-b) for a,b in zip(verified["timestamps_ms"], metadata["timestamps_ms"])) > 1:
                    raise RuntimeError("Exported video timeline mismatch")
                (work/"intermediate.avi").unlink()
            else:
                if cv2.imread(str(work/"annotated.jpg")) is None:
                    raise RuntimeError("Exported image cannot be decoded")
            write_json(work/"tracks.json", {"identity": "temporary within this run only",
                        "trajectory": "source-image observed centers; gaps are not interpolated",
                        "tracks": {str(k): [{"frame_index": p["frame_index"], "timestamp_ms": p["timestamp_ms"],
                                            "class_id": p["class_id"], "center_xy": p["center_xy"]} for p in v] for k,v in paths.items()}})
            outputs = {}
            for f in work.iterdir():
                outputs[f.name] = {"sha256": sha256(f), "bytes": f.stat().st_size}
            # Publish staged files only after media and timeline checks succeed.
            # Coordinates remain in source-image pixels, without ground speed.
            (work).rename(output/"artifacts")
            status.update(status="SUCCEEDED", outputs=outputs, frame_count=count, detection_count=n_detections,
                          input_sha256=sha256(source), weights_sha256=sha256(weights),
                          config={"device": device, "imgsz": imgsz, "conf": conf, "iou": iou, "max_det": max_det,
                                  "tracker": tracker_config if not is_image else None,
                                  "class_mapping": COCO_IDS, "threshold_status": "PILOT_NOT_FROZEN"},
                          video=metadata, frame_index_base=0, timestamp_origin="first decoded PTS",
                          output_audio="omitted", elapsed_seconds=time.perf_counter()-started,
                          inference_ms={"first": inference_ms[0], "mean": sum(inference_ms)/count,
                                        "median": float(np.median(inference_ms))},
                          cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(int(device)) if device != "cpu" else None,
                          cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(int(device)) if device != "cpu" else None,
                          cuda_device=torch.cuda.get_device_name(int(device)) if device != "cpu" else None,
                          versions={p: importlib.metadata.version(p) for p in ["ultralytics", "torch", "torchvision", "opencv-python", "numpy"]})
            write_json(output/"run.json", status)
            return status
        except BaseException as exc:
            status.update(status="INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "FAILED",
                          error=f"{type(exc).__name__}: {exc}", outputs=None,
                          elapsed_seconds=time.perf_counter()-started)
            write_json(output/"run.json", status)
            (output/"error.log").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        finally:
            if cap is not None:
                cap.release()
            if writer is not None:
                writer.release()
