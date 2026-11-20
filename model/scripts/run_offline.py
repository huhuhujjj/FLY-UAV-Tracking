"""Run from the project directory; see docs/step3_minimal_pipeline.md."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=.25)
    parser.add_argument("--iou", type=float, default=.7)
    parser.add_argument("--max-det", type=int, default=1000)
    args = parser.parse_args()
    result = run(args.source, args.weights, args.output, args.device, args.imgsz, args.conf, args.iou, args.max_det)
    print(f'{result["status"]}: {result["frame_count"]} frames, {result["detection_count"]} detections')
