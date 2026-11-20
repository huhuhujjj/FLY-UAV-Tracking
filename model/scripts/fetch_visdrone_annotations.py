"""Fetch source archive indices and annotation members without bulk media.

This advances the data inventory. Media pixels are not audited by this command,
and downloaded test annotations are never used for model selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

from fetch_visdrone_pilot import DATA, ROOT, RemoteZip

DRIVE='https://drive.usercontent.google.com/download?id={}&export=download&confirm=t'
ARCHIVES={
    'DET-train':DRIVE.format('1a2oHjcEcwXP8oUF95qiwrqzACb2YlUhn'),
    'DET-test-dev':DRIVE.format('1PFdW_VFSCfZ_sTSZAGjQdifF_Xd5mf0V'),
    'MOT-train':DRIVE.format('1-qX2d-P1Xr64ke6nTdlm33om1VxCUTSh'),
    'MOT-test-dev':DRIVE.format('14z8Acxopj1d86-qhsF1NwS4Bv3KYa4Wu'),
}

def sha(blob):return hashlib.sha256(blob).hexdigest()

def acquire(name,url):
    dest=DATA/'manifests'/(name+'_annotations_acquisition.json')
    old=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else {}
    records={r['archive_member']:r for r in old.get('members',[])}
    record={'archive':name,'source_url':url,'downloaded_at':datetime.now(timezone.utc).isoformat(),
            'status':'IN_PROGRESS','scope':'source annotation members and ZIP index; no bulk images',
            'members':records,'errors':[]}
    remote=RemoteZip(url,budget=512*1024**2)
    record['archive_size_bytes']=remote.size
    with zipfile.ZipFile(remote) as z:
        listing=[{'name':i.filename,'size':i.file_size,'crc32':f'{i.CRC:08x}'} for i in z.infolist()]
        (DATA/'manifests'/(name+'_archive_index.json')).write_text(json.dumps(listing,indent=2)+'\n',encoding='utf-8')
        targets=[i for i in z.infolist() if not i.is_dir() and
                 ('/annotations/' in i.filename or i.filename.startswith('annotations/') or
                  re.search(r'(readme|licen[sc]e|copying)',i.filename,re.I))]
        record['archive_members']=len(listing);record['annotation_members_expected']=sum('annotations/' in i.filename for i in targets)
        for idx,info in enumerate(targets,1):
            parts=info.filename.split('/')
            relative=parts if parts[0] in ('annotations','images','sequences') else parts[1:]
            if not relative or any(x in ('','..') for x in relative) or info.file_size>25*1024**2:
                raise ValueError(f'Unsafe archive member: {info.filename}')
            p=DATA/'raw'/name/Path(*relative);p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():
                blob=p.read_bytes()
                if len(blob)!=info.file_size or zlib.crc32(blob)!=info.CRC:raise ValueError(f'Existing file differs: {p}')
            else:
                blob=z.read(info);p.write_bytes(blob)
            records[info.filename]={'archive_member':info.filename,'path':str(p.relative_to(ROOT)),
                'size_bytes':len(blob),'crc32':f'{info.CRC:08x}','sha256':sha(blob)}
            if idx%100==0 or idx==len(targets):
                record['members']=list(records.values());record['network_bytes_this_run']=remote.fetched
                dest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print(name,idx,'/',len(targets),'network',remote.fetched,flush=True)
    record['members']=list(records.values());record['status']='FETCHED';record['network_bytes_this_run']=remote.fetched
    dest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return record

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',choices=list(ARCHIVES),required=True);args=ap.parse_args()
    try:record=acquire(args.archive,ARCHIVES[args.archive])
    except Exception as e:
        p=DATA/'manifests'/(args.archive+'_fetch_error.json')
        p.write_text(json.dumps({'archive':args.archive,'error':str(e)},indent=2)+'\n',encoding='utf-8')
        raise
    print(record['archive'],record['status'],len(record['members']))

if __name__=='__main__':main()
