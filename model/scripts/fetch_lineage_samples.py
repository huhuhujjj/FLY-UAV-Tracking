"""Fetch one media member per source prefix/sequence for leakage triage.

Sampling cannot establish complete pixel independence. Keep all sampled source
components in development review until final-test lineage is resolved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
import zlib
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from PIL import Image
from fetch_visdrone_annotations import ARCHIVES
from fetch_visdrone_pilot import DATA, ROOT, RemoteZip
from audit_visdrone import dhash

ARCHIVES.update({
 'DET-val':'https://github.com/ultralytics/assets/releases/download/v0.0.0/VisDrone2019-DET-val.zip',
 'MOT-val':'https://drive.usercontent.google.com/download?id=1rqnKe9IgU_crMaxRoel9_nuUsMEBBVQu&export=download&confirm=t'})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',choices=sorted(ARCHIVES),required=True);args=ap.parse_args()
    name=args.archive;kind=name.split('-')[0]
    listing=json.loads((DATA/'manifests'/(name+'_archive_index.json')).read_text(encoding='utf-8'))
    per_group={}
    for item in listing:
        path=item['name']
        if not path.lower().endswith(('.jpg','.jpeg','.png')):continue
        if kind=='DET':group=Path(path).stem.split('_')[0]
        else:
            pieces=path.split('/sequences/')[-1].split('/')
            if len(pieces)!=2:continue
            group=pieces[0]
        per_group.setdefault(group,path)
    output=DATA/'manifests'/(name+'_lineage_samples.json')
    previous=json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    records={x['source_group']:x for x in previous.get('samples',[])}
    remote=RemoteZip(ARCHIVES[name],budget=768*1024**2)
    with zipfile.ZipFile(remote) as z:
        for i,(group,member) in enumerate(sorted(per_group.items()),1):
            info=z.getinfo(member)
            parts=member.split('/');relative=parts if parts[0] in ('images','sequences') else parts[1:]
            if '..' in relative or info.file_size>25*1024**2:raise ValueError(f'Unsafe media member: {member}')
            path=DATA/'raw'/name/Path(*relative);path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                blob=path.read_bytes()
                if len(blob)!=info.file_size or zlib.crc32(blob)!=info.CRC:raise ValueError(f'Existing media differs: {path}')
            else:blob=z.read(info);path.write_bytes(blob)
            with Image.open(BytesIO(blob)) as im:im.load();image=im.convert('RGB')
            records[group]={'source_group':group,'archive_member':member,'path':str(path.relative_to(ROOT)),
                'image_sha256':hashlib.sha256(blob).hexdigest(),'pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
                'dhash':f'{dhash(image):016x}','width':image.width,'height':image.height,
                'role':'lineage_review_sample_not_final_test_result'}
            if i%25==0 or i==len(per_group):
                output.write_text(json.dumps({'archive':name,'status':'IN_PROGRESS','expected_groups':len(per_group),
                    'samples':list(records.values()),'network_bytes_this_run':remote.fetched},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print(name,i,'/',len(per_group),'network',remote.fetched,flush=True)
    output.write_text(json.dumps({'archive':name,'status':'FETCHED','expected_groups':len(per_group),
        'samples':list(records.values()),'network_bytes_this_run':remote.fetched},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
