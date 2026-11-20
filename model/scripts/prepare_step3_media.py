"""Extract only audited development candidates; never final-test material."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT/"model"))
from src.pipeline import sha256, write_json


def main():
    out = PROJECT/"model/data/processed/step3_pilot"
    out.mkdir(parents=True, exist_ok=True)
    inventory = PROJECT/"model/data/manifests/step2_technical_v1/media_inventory.jsonl"
    records = [json.loads(line) for line in inventory.read_text(encoding="utf-8-sig").splitlines()]
    det = next(r for r in records if r["split"]=="DET-val" and r["bucket"]=="validation_candidate" and r["technical_candidate"])
    sequence = "uav0000117_02622_v"
    mot = sorted([r for r in records if r["split"]=="MOT-val" and r["bucket"]=="validation_candidate"
                  and r["technical_candidate"] and f"/{sequence}/" in r["archive_member"]],
                 key=lambda r:r["archive_member"])[:48]
    assert len(mot)==48
    selected = [det]+mot
    for split in ("DET-val","MOT-val"):
        rows = [r for r in selected if r["split"]==split]
        archive = PROJECT/f"model/data/raw/archives/{split}.zip"
        assert sha256(archive)==rows[0]["archive_sha256"]
        with zipfile.ZipFile(archive) as z:
            for row in rows:
                assert sha256(PROJECT/row["annotation"])==row["annotation_sha256"]
                member = z.getinfo(row["archive_member"])
                assert f"{member.CRC:08x}"==row["member_crc32"]
                data = z.read(member)
                relative = "image.jpg" if split=="DET-val" else "frames/"+Path(member.filename).name
                target = out/relative
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(data)
                row["extracted_path"] = str(target.relative_to(PROJECT))
                row["extracted_sha256"] = hashlib.sha256(data).hexdigest()
    import cv2
    first = cv2.imread(str(PROJECT/mot[0]["extracted_path"]))
    height,width = first.shape[:2]
    source_frame_ids = [int(Path(r["archive_member"]).stem) for r in mot]
    assert source_frame_ids == list(range(1,49))
    subprocess.run(["ffmpeg","-v","error","-y","-framerate","25","-start_number","1",
                    "-i",str(out/"frames/%07d.jpg"),"-frames:v","48","-c:v","libx264",
                    "-pix_fmt","yuv420p","-crf","18",str(out/"clip.mp4")],check=True)
    frames = [{"frame_index":i,"source_frame_index":source_frame_ids[i],"width":width,"height":height,
               "timestamp_ms":i*40, "detections":[], "ignore_xywh":[]} for i in range(48)]
    for line in (PROJECT/mot[0]["annotation"]).read_text(encoding="utf-8-sig").splitlines():
        values = list(map(int,line.strip().split(",")))
        frame,tid,x,y,w,h,score,category,truncation,occlusion = values
        if frame not in source_frame_ids:
            continue
        item=frames[source_frame_ids.index(frame)]
        if score==0 or category in (0,11):
            item["ignore_xywh"].append([x,y,w,h])
        elif category in (4,9,6):
            item["detections"].append({"track_id":tid,"class_id":{4:0,9:1,6:2}[category],
                                       "bbox_xyxy":[x,y,x+w,y+h]})
    write_json(out/"reference.json",frames)
    manifest = {"version":"step3-development-media-1", "purpose":"development smoke only; never final evaluation",
                "inventory_sha256":sha256(inventory), "records":selected, "source_sequence":sequence,
                "source_frame_mapping":"decoded index 0..47 -> original source index 1..48",
                "playback_fps":25, "fps_status":"chosen encoding rate; source acquisition FPS unverified",
                "clip_sha256":sha256(out/"clip.mp4"),"reference_sha256":sha256(out/"reference.json"),
                "limitations":"Compressed re-encoding and this short chosen interval are not representative evaluation."}
    write_json(PROJECT/"model/data/manifests/step3_development_media.json",manifest)
    print(out)


if __name__=="__main__":
    main()
