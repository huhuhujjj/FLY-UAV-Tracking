"""Execute sequential, real-media smoke checks and retain auditable evidence."""
from pathlib import Path
import csv
import json
import sys
import traceback

PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/"model"))
from src.pipeline import run,sha256,write_json,probe_video
from src.evaluation import evaluate_tracking,evaluate_detection

def verify(directory):
    status=json.loads((directory/"run.json").read_text(encoding="utf-8"))
    assert status["status"]=="SUCCEEDED"
    rows=[json.loads(x) for x in (directory/"artifacts/frames.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows)==status["frame_count"]
    for name,record in status["outputs"].items():
        assert sha256(directory/"artifacts"/name)==record["sha256"]
    for i,frame in enumerate(rows):
        assert frame["frame_index"]==i
        for detection in frame["detections"]:
            assert detection["frame_index"]==i and detection["timestamp_ms"]==frame["timestamp_ms"]
            assert abs(detection["timestamp_seconds"]-detection["timestamp_ms"]/1000)<1e-9
    with (directory/"artifacts/detections.csv").open(encoding="utf-8",newline="") as f:
        exported=list(csv.DictReader(f))
    assert len(exported)==sum(len(r["detections"]) for r in rows)
    for flat,row in zip(exported,(d for f in rows for d in f["detections"])):
        assert flat["detection_id"]==row["detection_id"]
        assert [float(flat[k]) for k in ("x1","y1","x2","y2")]==row["bbox_xyxy"]
    if status["video"]:
        meta=probe_video(directory/"artifacts/annotated.mp4")
        assert len(meta["timestamps_ms"])==len(rows)
    else:
        assert all(d["track_id"] is None for f in rows for d in f["detections"])
    return rows

def main():
    import cv2
    import numpy as np
    base=PROJECT/"model/experiments/step3_20261119_final"
    media=PROJECT/"model/data/processed/step3_pilot"
    weights=PROJECT/"model/weights/yolo26l.pt"
    base.mkdir(parents=True,exist_ok=True)
    results={"date":"2026-11-19","purpose":"minimal offline development chain; not final acceptance",
             "weights_sha256":sha256(weights),"checks":{},"runs":{}}
    for name,source,device in (("image_cpu","image.jpg","cpu"),("image_gpu","image.jpg","0"),
                                ("video_gpu","clip.mp4","0"),("video_gpu_reset","clip.mp4","0"),
                                ("video_cpu","clip.mp4","cpu")):
        target=base/name
        if target.exists():
            status=json.loads((target/"run.json").read_text(encoding="utf-8"))
            if status["status"]!="SUCCEEDED":
                raise RuntimeError(f"Prior failed run retained at {target}; use a new run name")
        else:
            status=run(media/source,weights,target,device)
        verify(target)
        results["runs"][name]={"path":str(target.relative_to(PROJECT)),"status":status["status"],
                               "frames":status["frame_count"],"detections":status["detection_count"],
                               "elapsed_seconds":status["elapsed_seconds"],"inference_ms":status["inference_ms"],
                               "cuda_peak_allocated_bytes":status["cuda_peak_allocated_bytes"]}
        write_json(PROJECT/".qa/step3_verification.json",results)
        print(name,status["status"],flush=True)
    first=verify(base/"video_gpu")
    second=verify(base/"video_gpu_reset")
    assert first==second,"Repeated same-device inference or reset differs"
    results["checks"]["same_process_video_reset"]="PASS_IDENTICAL_OBSERVATIONS"
    gt=json.loads((media/"reference.json").read_text(encoding="utf-8"))
    evaluation=evaluate_tracking(gt,first)
    evaluation["detection"]=evaluate_detection(gt,first)
    evaluation["purpose"]="48-frame chosen development interval; not representative or final results"
    write_json(base/"development_metrics.json",evaluation)
    results["checks"]["real_prediction_evaluation"]="PASS_EXECUTED_LOCAL_POLICY"
    # Reversible negative cases: corrupt media must have FAILED and outputs=null.
    for name,content in (("corrupt.jpg",b"not an image"),("corrupt.mp4",b"not an MP4")):
        path=media/name
        path.write_bytes(content)
        target=base/name.replace(".","_")
        if not target.exists():
            try:
                run(path,weights,target,"cpu")
            except Exception:
                pass
            else:
                raise AssertionError("Corrupt input accepted")
        status=json.loads((target/"run.json").read_text(encoding="utf-8"))
        assert status["status"]=="FAILED" and status["outputs"] is None and not (target/"artifacts").exists()
        results["checks"][name]="PASS_FAILED_WITHOUT_PUBLISHED_OUTPUTS"
    blank=media/"empty.png"
    cv2.imwrite(str(blank),np.zeros((240,320,3),dtype=np.uint8))
    if not (base/"empty_image").exists():
        run(blank,weights,base/"empty_image","cpu")
    empty=verify(base/"empty_image")
    assert empty[0]["detections"]==[]
    results["checks"]["empty_image"]="PASS_SUCCEEDED_ZERO_DETECTIONS"
    results["checks"]["exports"]="PASS_HASHES_CSV_JSON_FRAME_TIMESTAMPS_AND_MEDIA"
    write_json(PROJECT/".qa/step3_verification.json",results)
    print(json.dumps(results,indent=2))

if __name__=="__main__":
    main()
