"""Create audit-only YOLO labels for every DET source image.

Preserves excluded/ignored annotations in separate JSONL. This derivative is
not automatically training-ready because ignored regions require a policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from audit_visdrone import DATA,ROOT,eligible,parse_line,yolo,decode_yolo

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--split',required=True,choices=('DET-train','DET-val','DET-test-dev'));args=ap.parse_args()
    name=args.split
    media=json.loads((DATA/'manifests'/(name+'_media_audit.json')).read_text(encoding='utf-8'))
    if media['status']!='COMPLETE':raise ValueError('Media audit incomplete')
    out=DATA/'processed/corpus_v1'/name;labels=out/'labels';labels.mkdir(parents=True,exist_ok=True)
    sidecar=out/'all_source_rows.jsonl';index=[];stats=Counter();max_error=0
    with sidecar.open('w',encoding='utf-8') as source:
        for image in media['media']:
            stem=Path(image['archive_member']).stem
            ann=DATA/'raw'/name/'annotations'/(stem+'.txt')
            rows=[]
            for line_no,line in enumerate(ann.read_text(encoding='utf-8-sig').splitlines(),1):
                if not line.strip():continue
                try:r=parse_line(line,'DET',line_no)
                except ValueError as e:
                    stats['invalid_source_rows']+=1
                    source.write(json.dumps({'image':stem,'line':line_no,'raw':line,'error':str(e)})+'\n')
                    continue
                r['image']=stem;rows.append(r);source.write(json.dumps(r,ensure_ascii=False)+'\n')
            selected=[r for r in rows if eligible(r,image['width'],image['height'])]
            lines=[yolo(r,image['width'],image['height']) for r in selected]
            for r,line in zip(selected,lines):
                c,box=decode_yolo(line,image['width'],image['height'])
                if c!=r['local_class']:raise AssertionError('Class roundtrip failed')
                max_error=max(max_error,max(abs(a-b) for a,b in zip(box,r['bbox_xywh'])))
            label=labels/(stem+'.txt');label.write_text('\n'.join(lines)+('\n' if lines else ''),encoding='utf-8')
            stats['images']+=1;stats['source_rows']+=len(rows);stats['selected_boxes']+=len(lines)
            stats['ignored_rows']+=sum(r['ignored'] for r in rows)
            stats['out_of_bounds_selected_rows']+=sum(not r['ignored'] and r['local_class'] is not None and
                not eligible(r,image['width'],image['height']) for r in rows)
            index.append({'image':stem,'source_annotation_sha256':hashlib.sha256(ann.read_bytes()).hexdigest(),
                          'label_sha256':hashlib.sha256(label.read_bytes()).hexdigest(),
                          'source_rows':len(rows),'selected_boxes':len(lines),
                          'contains_ignored_rows':any(r['ignored'] for r in rows)})
    result={'split':name,'status':'AUDIT_DERIVATIVE_NOT_TRAINING_READY',
            'source_media_audit_sha256':hashlib.sha256((DATA/'manifests'/(name+'_media_audit.json')).read_bytes()).hexdigest(),
            'stats':dict(stats),'max_coordinate_roundtrip_error_px':max_error,
            'retained_source_rows':str(sidecar.relative_to(ROOT)),
            'labels_dir':str(labels.relative_to(ROOT)),'index':index,
            'ignore_policy':'Source ignored rows retained in sidecar; no negative training/evaluation inference from their absence in YOLO labels.',
            'final_test_frozen':False}
    (DATA/'manifests'/(name+'_conversion.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(name,dict(stats),'max_error',max_error)

if __name__=='__main__':main()
