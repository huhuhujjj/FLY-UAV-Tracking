"""Decode every image/frame in one full archive and check source boxes.

This uses archive data directly and saves compact per-image fingerprints. It
does not extract or publish media and does not evaluate a model.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image
from audit_visdrone import DATA,ROOT,dhash

def annotation_rows(path,kind):
    rows=defaultdict(list)
    for line_no,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip():continue
        fields=line.rstrip(',').split(',')
        try:v=[int(x) for x in fields]
        except ValueError:continue # Already reported by annotation audit.
        frame=v[0] if kind=='MOT' else None
        rows[frame].append((line_no,v[-8:-4],v[-4],v[-3]))
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',required=True,choices=('DET-train','DET-val','DET-test-dev','MOT-train','MOT-val','MOT-test-dev'));args=ap.parse_args()
    name=args.archive;kind=name.split('-')[0]
    archive=DATA/'raw/archives'/(name+'.zip')
    if not archive.is_file():raise FileNotFoundError(archive)
    full=json.loads((DATA/'manifests'/(name+'_full_archive.json')).read_text(encoding='utf-8'))
    digest=hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):digest.update(chunk)
    if full['status']!='FULL_ARCHIVE_CRC_VERIFIED' or digest.hexdigest()!=full['sha256']:
        raise ValueError('Full archive is not verified')
    output=DATA/'manifests'/(name+'_media_audit.json')
    previous=json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    seen={x['archive_member']:x for x in previous.get('media',[])}
    issues=previous.get('issues',[]);counts=Counter(previous.get('counts',{}))
    annotation_cache={}
    with zipfile.ZipFile(archive) as z:
        targets=[i for i in z.infolist() if i.filename.lower().endswith(('.jpg','.jpeg','.png')) and
                 (('/images/' in i.filename or i.filename.startswith('images/')) if kind=='DET' else
                  ('/sequences/' in i.filename or i.filename.startswith('sequences/')))]
        for idx,info in enumerate(targets,1):
            if info.filename in seen:continue
            blob=z.read(info)
            try:
                with Image.open(io.BytesIO(blob)) as im:im.load();image=im.convert('RGB')
            except Exception as e:
                issues.append({'archive_member':info.filename,'error':'decode_failed','detail':str(e)});continue
            if kind=='DET':
                source_group=Path(info.filename).stem.split('_')[0]
                ann=DATA/'raw'/name/'annotations'/(Path(info.filename).stem+'.txt')
                frame=None
            else:
                sub=info.filename.split('/sequences/')[-1].split('/')
                source_group=sub[0];frame=int(Path(sub[1]).stem)
                ann=DATA/'raw'/name/'annotations'/(source_group+'.txt')
            if not ann.exists():issues.append({'archive_member':info.filename,'error':'missing_annotation'});continue
            if ann not in annotation_cache:
                annotation_cache.clear();annotation_cache[ann]=annotation_rows(ann,kind)
            rows=annotation_cache[ann][frame]
            bad=0;valid=0;selected=0
            for line_no,(x,y,w,h),score,category in rows:
                if w<=0 or h<=0 or x<0 or y<0 or x+w>image.width or y+h>image.height:
                    bad+=1
                    if len(issues)<5000:
                        issues.append({'archive_member':info.filename,'annotation':ann.name,'line':line_no,
                                       'bbox_xywh':[x,y,w,h],'image_size':[image.width,image.height],
                                       'category':category,'score':score,'error':'source_box_out_of_bounds_or_nonpositive'})
                else:
                    valid+=1
                    if score==1 and category in (4,9,6):selected+=1
            counts['decoded_images']+=1;counts['source_rows_on_decoded_media']+=len(rows)
            counts['bad_boxes']+=bad;counts['selected_in_bounds_boxes']+=selected
            seen[info.filename]={'archive_member':info.filename,'source_group':source_group,
                'frame_index':frame,'width':image.width,'height':image.height,
                'image_sha256':hashlib.sha256(blob).hexdigest(),
                'pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
                'dhash':f'{dhash(image):016x}','source_rows':len(rows),'bad_boxes':bad,
                'selected_in_bounds_boxes':selected}
            if idx%250==0 or idx==len(targets):
                output.write_text(json.dumps({'archive':name,'status':'IN_PROGRESS','expected_images':len(targets),
                    'counts':dict(counts),'issues':issues,'media':list(seen.values())},ensure_ascii=False)+'\n',encoding='utf-8')
                print(name,idx,'/',len(targets),'bad boxes',counts['bad_boxes'],flush=True)
    status='COMPLETE' if len(seen)==len(targets) else 'INCOMPLETE'
    output.write_text(json.dumps({'archive':name,'status':status,'expected_images':len(targets),
        'counts':dict(counts),'issues':issues,'media':list(seen.values())},ensure_ascii=False)+'\n',encoding='utf-8')
    print(name,status,len(seen),len(targets),flush=True)

if __name__=='__main__':main()
