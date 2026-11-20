"""Resume and verify full VisDrone archives with large HTTP ranges.

Archives stay local in model/data/raw/archives (Git ignored). An archive is
usable only after byte count, ZIP central directory and member CRC verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from fetch_visdrone_annotations import ARCHIVES
from fetch_visdrone_pilot import DATA

ARCHIVES.update({
 'DET-val':'https://github.com/ultralytics/assets/releases/download/v0.0.0/VisDrone2019-DET-val.zip',
 'MOT-val':'https://drive.usercontent.google.com/download?id=1rqnKe9IgU_crMaxRoel9_nuUsMEBBVQu&export=download&confirm=t'})
CHUNK=32*1024*1024

def expected_size(name):
    p=DATA/'manifests'/(name+'_annotations_acquisition.json')
    if p.exists():return json.loads(p.read_text(encoding='utf-8'))['archive_size_bytes']
    p=DATA/'manifests/pilot_acquisition.json'
    return next(x['size_bytes'] for x in json.loads(p.read_text(encoding='utf-8'))['archives'] if x['name']==name)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',required=True,choices=sorted(ARCHIVES));args=ap.parse_args()
    name=args.archive;size=expected_size(name);url=ARCHIVES[name]
    folder=DATA/'raw/archives';folder.mkdir(parents=True,exist_ok=True)
    archive=folder/(name+'.zip');partial=folder/(name+'.zip.part')
    manifest=DATA/'manifests'/(name+'_full_archive.json')
    if archive.exists():
        if archive.stat().st_size!=size:raise ValueError('Existing archive size mismatch')
    else:
        if partial.exists() and partial.stat().st_size>size:raise ValueError('Partial archive oversized')
        done=partial.stat().st_size if partial.exists() else 0
        if done%CHUNK!=0 and done!=size:raise ValueError('Partial archive is not aligned to chunk boundary')
        with partial.open('ab') as out:
            while done<size:
                end=min(done+CHUNK,size)-1
                request=urllib.request.Request(url,headers={'Range':f'bytes={done}-{end}',
                    'User-Agent':'FPY-VisDrone-Archive-Audit/1.0'})
                for attempt in range(5):
                    try:
                        start=time.monotonic()
                        with urllib.request.urlopen(request,timeout=90) as response:
                            expected=f'bytes {done}-{end}/{size}'
                            if response.status!=206 or response.headers.get('Content-Range')!=expected:
                                raise ValueError(f'Unexpected HTTP range {response.status} {response.headers.get("Content-Range")}')
                            blob=response.read(end-done+2)
                        if len(blob)!=end-done+1:raise ValueError('Short range read')
                        out.write(blob);out.flush();os.fsync(out.fileno())
                        done=end+1
                        print(name,done,'/',size,'seconds',round(time.monotonic()-start,1),flush=True)
                        break
                    except Exception as e:
                        if attempt==4:raise
                        print(name,'retry',attempt+1,str(e),flush=True)
                        time.sleep(attempt+1)
        partial.replace(archive)
    digest=hashlib.sha256()
    with archive.open('rb') as stream:
        for blob in iter(lambda:stream.read(8*1024*1024),b''):digest.update(blob)
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad:raise ValueError(f'ZIP member CRC failure: {bad}')
        count=len(z.infolist())
    record={'archive':name,'status':'FULL_ARCHIVE_CRC_VERIFIED','source_url':url,
        'verified_at':datetime.now(timezone.utc).isoformat(), 'path':str(archive.relative_to(DATA.parents[1])),
        'size_bytes':size,'sha256':digest.hexdigest(),'zip_members':count,'member_crc':'PASS',
        'scope':'Archive integrity only; annotation/media semantic audit is separate.'}
    manifest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(name,record['status'],'members',count,flush=True)

if __name__=='__main__':main()
