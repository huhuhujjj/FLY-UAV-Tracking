import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.evaluation import evaluate_tracking, evaluate_detection
from src.pipeline import write_json, sha256

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--predictions",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    gt=json.loads(args.reference.read_text(encoding="utf-8-sig"))
    pred=[json.loads(s) for s in args.predictions.read_text(encoding="utf-8").splitlines()]
    result=evaluate_tracking(gt,pred)
    result["detection"]=evaluate_detection(gt,pred)
    result.update(reference_sha256=sha256(args.reference),predictions_sha256=sha256(args.predictions),
                  purpose="development pilot; not final acceptance or official VisDrone score")
    write_json(args.output,result)
    print(json.dumps(result["per_class"],indent=2))
