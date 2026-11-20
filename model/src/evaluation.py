"""Class-separated TrackEval adapter for a local, explicit ignore policy."""
from __future__ import annotations
import importlib.metadata
import math
import numpy as np
from .visdrone_det_ignore import covered_fraction

NAMES = ("car", "bus", "truck")


def iou_matrix(gt, pred):
    matrix = np.zeros((len(gt), len(pred)), dtype=float)
    for i, a in enumerate(gt):
        ax, ay, ar, ab = a["bbox_xyxy"]
        for j, b in enumerate(pred):
            bx, by, br, bb = b["bbox_xyxy"]
            intersection = max(0, min(ar,br)-max(ax,bx)) * max(0, min(ab,bb)-max(ay,by))
            matrix[i,j] = intersection / ((ar-ax)*(ab-ay) + (br-bx)*(bb-by) - intersection)
    return matrix


def _validate(frames, require_ids):
    for expected, frame in enumerate(frames):
        if frame["frame_index"] != expected:
            raise ValueError("Frames must be consecutive, zero-based, including empty frames")
        width, height = frame["width"], frame["height"]
        if width <= 0 or height <= 0:
            raise ValueError("Invalid frame dimensions")
        seen = set()
        for row in frame["detections"]:
            box = row["bbox_xyxy"]
            if len(box) != 4 or not all(math.isfinite(x) for x in box):
                raise ValueError("Invalid box")
            x,y,r,b = box
            if not 0 <= x < r <= width or not 0 <= y < b <= height:
                raise ValueError("Box outside source image")
            if row["class_id"] not in range(3):
                raise ValueError("Invalid local class")
            tid = row["track_id"]
            if tid is None:
                if require_ids:
                    raise ValueError("Ground truth needs source track IDs")
                continue
            if not isinstance(tid, int) or tid < 0 or tid in seen:
                raise ValueError("Track IDs must be nonnegative and unique in a frame")
            seen.add(tid)


def evaluate_tracking(gt_frames, pred_frames):
    from trackeval.metrics import HOTA, CLEAR, Identity
    _validate(gt_frames, True)
    _validate(pred_frames, False)
    if not gt_frames or len(gt_frames) != len(pred_frames):
        raise ValueError("Reference and prediction must cover the same nonempty frame interval")
    gt_kept, pred_kept = [], []
    counts = {"gt_ignored": 0, "predictions_ignored": 0, "unassociated_detections": 0}
    for g, p in zip(gt_frames, pred_frames):
        if (g["width"],g["height"]) != (p["width"],p["height"]):
            raise ValueError("Reference and prediction dimensions differ")
        ignores = g.get("ignore_xywh", [])
        pair = []
        for key, frame in (("gt_ignored",g), ("predictions_ignored",p)):
            kept = []
            for row in frame["detections"]:
                x,y,r,b = row["bbox_xyxy"]
                if covered_fraction([x,y,r-x,b-y], ignores, g["width"], g["height"]) >= .5:
                    counts[key] += 1
                    continue
                if key == "predictions_ignored" and row["track_id"] is None:
                    counts["unassociated_detections"] += 1
                    continue
                kept.append(row)
            pair.append(kept)
        gt_kept.append(pair[0])
        pred_kept.append(pair[1])
    output = {}
    for category, name in enumerate(NAMES):
        gs = [[r for r in frame if r["class_id"] == category] for frame in gt_kept]
        ps = [[r for r in frame if r["class_id"] == category] for frame in pred_kept]
        # Class changes in a source identity are rejected rather than silently repaired.
        for frames in (gt_kept,):
            ids = {}
            for frame in frames:
                for row in frame:
                    tid = row["track_id"]
                    if tid in ids and ids[tid] != row["class_id"]:
                        raise ValueError("Source track ID changes class")
                    ids[tid] = row["class_id"]
        gm = {tid:i for i,tid in enumerate(sorted({r["track_id"] for f in gs for r in f}))}
        pm = {tid:i for i,tid in enumerate(sorted({r["track_id"] for f in ps for r in f}))}
        data = {"num_timesteps": len(gs), "num_gt_ids": len(gm), "num_tracker_ids": len(pm),
                "num_gt_dets": sum(map(len,gs)), "num_tracker_dets": sum(map(len,ps)),
                "gt_ids": [np.array([gm[r["track_id"]] for r in f], dtype=int) for f in gs],
                "tracker_ids": [np.array([pm[r["track_id"]] for r in f], dtype=int) for f in ps],
                "similarity_scores": [iou_matrix(g,p) for g,p in zip(gs,ps)]}
        h = HOTA().eval_sequence(data)
        c = CLEAR({"THRESHOLD": .5, "PRINT_CONFIG": False}).eval_sequence(data)
        ident = Identity({"THRESHOLD": .5, "PRINT_CONFIG": False}).eval_sequence(data)
        has_gt = data["num_gt_dets"] > 0
        output[name] = {"gt_detections": data["num_gt_dets"], "tracker_detections": data["num_tracker_dets"],
                        "TP": int(c["CLR_TP"]), "FP": int(c["CLR_FP"]), "FN": int(c["CLR_FN"]),
                        "IDSW": int(c["IDSW"]), "Frag": None, "TrackEval_Frag_unverified": int(c["Frag"]),
                        "MOTA": float(c["MOTA"]) if has_gt else None,
                        "IDF1": float(ident["IDF1"]) if has_gt else None,
                        "HOTA": float(np.mean(h["HOTA"])) if has_gt else None,
                        "HOTA_by_alpha": [float(x) for x in h["HOTA"]] if has_gt else None}
    return {"evaluator": "TrackEval", "evaluator_version": importlib.metadata.version("trackeval"),
            "adapter_version": "uav-trackeval-local-1", "scale": "ratios 0..1; MOTA may be negative",
            "matching": "class-separated; CLEAR/Identity IoU>=0.5; HOTA alpha=0.05:0.05:0.95",
            "ignore_policy": "local union coverage >=0.5 for category 0,11 and source score 0; NOT official VisDrone equivalence",
            "unassociated_policy": "retained in detection exports, excluded from submitted tracks; reported separately",
            "fragmentation_status": "NOT_VALIDATED: TrackEval 1.3.0 returns 0 for a full empty-prediction frame gap; raw value retained, not acceptance evidence",
            "frame_count": len(gt_frames), "preprocessing": counts, "per_class": output}



def evaluate_detection(gt_frames, pred_frames):
    """COCO interpolation after project preprocessing; not official VisDrone AP."""
    from contextlib import redirect_stdout
    import io
    from scipy.optimize import linear_sum_assignment
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    _validate(gt_frames, True)
    _validate(pred_frames, False)
    if not gt_frames or len(gt_frames) != len(pred_frames):
        raise ValueError("Reference and prediction intervals differ")
    images, annotations, detections = [], [], []
    frame_pairs = []
    for g,p in zip(gt_frames,pred_frames):
        if (g["width"],g["height"]) != (p["width"],p["height"]):
            raise ValueError("Frame dimensions differ")
        ignores=g.get("ignore_xywh",[])
        pair=[]
        for frame in (g,p):
            kept=[]
            for r in frame["detections"]:
                x,y,right,bottom=r["bbox_xyxy"]
                if covered_fraction([x,y,right-x,bottom-y],ignores,g["width"],g["height"])<.5:
                    kept.append(r)
            pair.append(kept)
        frame_pairs.append(pair)
        image_id=g["frame_index"]+1
        images.append({"id":image_id,"width":g["width"],"height":g["height"]})
        for r in pair[0]:
            x,y,right,bottom=r["bbox_xyxy"]
            annotations.append({"id":len(annotations)+1,"image_id":image_id,"category_id":r["class_id"],
                                "bbox":[x,y,right-x,bottom-y],"area":(right-x)*(bottom-y),"iscrowd":0})
        for r in pair[1]:
            x,y,right,bottom=r["bbox_xyxy"]
            score=float(r.get("confidence",1.0))
            if not math.isfinite(score) or not 0<=score<=1:
                raise ValueError("Invalid confidence")
            detections.append({"image_id":image_id,"category_id":r["class_id"],
                               "bbox":[x,y,right-x,bottom-y],"score":score})
    with redirect_stdout(io.StringIO()):
        coco=COCO()
        coco.dataset={"images":images,"annotations":annotations,
                      "categories":[{"id":i,"name":n} for i,n in enumerate(NAMES)],"info":{}}
        coco.createIndex()
        if detections:
            prediction=coco.loadRes(detections)
        else:
            prediction=COCO()
            prediction.dataset={"images":images,"annotations":[],"categories":coco.dataset["categories"]}
            prediction.createIndex()
        evaluator=COCOeval(coco,prediction,"bbox")
        evaluator.params.maxDets=[1,10,1000]
        evaluator.evaluate()
        evaluator.accumulate()
    result={}
    for category,name in enumerate(NAMES):
        tp=fp=fn=0
        for gs,ps in frame_pairs:
            gs=[r for r in gs if r["class_id"]==category]
            ps=[r for r in ps if r["class_id"]==category]
            similarities=iou_matrix(gs,ps)
            scores=(similarities>=.5).astype(float)*1000+similarities
            ri,ci=linear_sum_assignment(-scores)
            matches=int(np.sum(similarities[ri,ci]>=.5))
            tp+=matches; fp+=len(ps)-matches;fn+=len(gs)-matches
        precision=evaluator.eval["precision"][:,:,category,0,-1]
        valid=precision[precision>=0]
        ap50=precision[0][precision[0]>=0]
        result[name]={"TP":tp,"FP":fp,"FN":fn,"Precision":tp/(tp+fp) if tp+fp else None,
                      "Recall":tp/(tp+fn) if tp+fn else None,
                      "AP50":float(np.mean(ap50)) if len(ap50) else None,
                      "AP50_95":float(np.mean(valid)) if len(valid) else None}
    return {"evaluator":"pycocotools", "evaluator_version":importlib.metadata.version("pycocotools"),
            "adapter_version":"uav-cocoeval-local-1","max_detections_per_frame":1000,
            "input_policy":"AP uses submitted confidence range; smoke conf=.25 is truncated, not full low-confidence validation",
            "precision_recall_policy":"one-to-one maximum-cardinality IoU>=.5 matching at submitted confidence cutoff",
            "ignore_policy":"project union coverage>=.5; not official VisDrone scores",
            "per_class":result}
