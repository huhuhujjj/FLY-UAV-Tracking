"""Hand-checkable fixtures; they validate scoring, not detector accuracy."""
import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.evaluation import evaluate_tracking, evaluate_detection
from src.pipeline import exclusive_job, recover_interrupted, write_json, observations

def sequence(ids):
    return [{"frame_index":i,"width":100,"height":100,"detections":
             [] if tid is None else [{"track_id":tid,"class_id":0,"bbox_xyxy":[10,10,30,30]}]}
            for i,tid in enumerate(ids)]

class EvaluationTests(unittest.TestCase):
    def test_perfect_and_source_id_zero(self):
        result=evaluate_tracking(sequence([0]*4),sequence([7]*4))["per_class"]["car"]
        self.assertEqual((result["TP"],result["FP"],result["FN"],result["IDSW"]),(4,0,0,0))
        for key in ("HOTA","IDF1","MOTA"): self.assertAlmostEqual(result[key],1)

    def test_identity_switch(self):
        result=evaluate_tracking(sequence([0]*4),sequence([7,7,8,8]))["per_class"]["car"]
        self.assertEqual(result["IDSW"],1)
        self.assertAlmostEqual(result["MOTA"],.75)
        self.assertAlmostEqual(result["IDF1"],.5)
        self.assertAlmostEqual(result["HOTA"],math.sqrt(.5))

    def test_missing_frame_and_reappearance(self):
        result=evaluate_tracking(sequence([0]*4),sequence([7,None,7,7]))["per_class"]["car"]
        self.assertEqual((result["TP"],result["FN"]),(3,1))
        self.assertIsNone(result["Frag"])
        self.assertEqual(result["TrackEval_Frag_unverified"],0)
        self.assertAlmostEqual(result["HOTA"],.75)
        self.assertAlmostEqual(result["IDF1"],6/7)
        self.assertAlmostEqual(result["MOTA"],.75)

    def test_wrong_class_is_fp_and_fn(self):
        pred=sequence([7])
        pred[0]["detections"][0]["class_id"]=1
        result=evaluate_tracking(sequence([0]),pred)["per_class"]
        self.assertEqual(result["car"]["FN"],1)
        self.assertEqual(result["bus"]["FP"],1)
        self.assertIsNone(result["bus"]["HOTA"])

    def test_ignore_union_threshold(self):
        gt=sequence([0]); pred=sequence([7])
        gt[0]["ignore_xywh"]=[[10,10,5,20],[15,10,5,20]]
        result=evaluate_tracking(gt,pred)
        self.assertEqual(result["preprocessing"]["predictions_ignored"],1)
        self.assertEqual(result["per_class"]["car"]["gt_detections"],0)

    def test_unassociated_not_silently_lost(self):
        pred=sequence([7]);pred[0]["detections"][0]["track_id"]=None
        result=evaluate_tracking(sequence([0]),pred)
        self.assertEqual(result["preprocessing"]["unassociated_detections"],1)
        self.assertEqual(result["per_class"]["car"]["FN"],1)

    def test_empty_is_na(self):
        self.assertIsNone(evaluate_tracking(sequence([None]),sequence([None]))["per_class"]["car"]["IDF1"])

    def test_reject_offset_duplicate_and_class_conflict(self):
        bad=sequence([0]);bad[0]["frame_index"]=1
        with self.assertRaises(ValueError):evaluate_tracking(bad,sequence([7]))
        bad=sequence([0]);bad[0]["detections"]*=2
        with self.assertRaises(ValueError):evaluate_tracking(bad,sequence([7]))
        bad=sequence([0,0]);bad[1]["detections"][0]["class_id"]=1
        with self.assertRaises(ValueError):evaluate_tracking(bad,sequence([7,7]))

    def test_detection_metrics_and_duplicate_false_positive(self):
        gt=sequence([0]); pred=sequence([7])
        r=evaluate_detection(gt,pred)["per_class"]["car"]
        self.assertAlmostEqual(r["AP50_95"],1)
        extra=copy.deepcopy(pred[0]["detections"][0]);extra["track_id"]=8
        pred[0]["detections"].append(extra)
        r=evaluate_detection(gt,pred)["per_class"]["car"]
        self.assertEqual((r["TP"],r["FP"],r["FN"]),(1,1,0))
        self.assertAlmostEqual(r["Precision"],.5)

    def test_interrupted_run_recovery_preserves_success(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name,status in (("old","RUNNING"),("done","SUCCEEDED")):
                (root/name).mkdir()
                write_json(root/name/"run.json",{"schema_version":"uav-offline-0.1","status":status,"outputs":None})
            recover_interrupted(root)
            self.assertEqual(json.loads((root/"old/run.json").read_text())["status"],"INTERRUPTED")
            self.assertEqual(json.loads((root/"done/run.json").read_text())["status"],"SUCCEEDED")

    def test_bytetrack_indices_empty_frames_and_new_video_reset(self):
        import os
        os.environ.setdefault("YOLO_CONFIG_DIR",str(Path(__file__).resolve().parents[1]/"experiments/.ultralytics"))
        import numpy as np
        from types import SimpleNamespace
        from ultralytics.engine.results import Boxes
        from ultralytics.trackers.byte_tracker import BYTETracker
        args=SimpleNamespace(track_high_thresh=.25,track_low_thresh=.1,new_track_thresh=.25,
                             track_buffer=30,match_thresh=.8,fuse_score=True)
        def result(data):
            return SimpleNamespace(boxes=Boxes(np.array(data,dtype=np.float32).reshape(-1,6),(100,100)),
                                   orig_shape=(100,100),orig_img=np.zeros((100,100,3),dtype=np.uint8))
        tracker=BYTETracker(args)
        rows=observations(result([[60,60,70,70,.05,5],[10,10,30,30,.9,2]]),0,0,tracker)
        self.assertIsNone(rows[0]["track_id"])
        self.assertEqual(rows[1]["track_id"],1)
        self.assertEqual(observations(result([]),1,40,tracker),[])
        self.assertEqual(tracker.frame_id,2)
        fresh=BYTETracker(args)
        self.assertEqual(observations(result([[10,10,30,30,.9,2]]),0,0,fresh)[0]["track_id"],1)

    def test_process_lock(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"job.lock"
            with exclusive_job(path):
                with self.assertRaises(RuntimeError):
                    with exclusive_job(path): pass
            with exclusive_job(path): pass

if __name__=="__main__":unittest.main()
