"""Fetch official source snapshots and a bounded pilot using HTTP ZIP ranges.

Only the selected ZIP members are fetched. CRC verification is provided by zipfile.
No archive paths are extracted verbatim. Existing identical files are retained.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
import urllib.parse
import urllib.request
import zipfile
import zlib
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'model/data'
SOURCES = {
    'dataset_readme': 'https://raw.githubusercontent.com/VisDrone/VisDrone-Dataset/master/README.md',
    'det_toolkit_readme': 'https://raw.githubusercontent.com/VisDrone/VisDrone2018-DET-toolkit/master/README.md',
    'mot_toolkit_readme': 'https://raw.githubusercontent.com/VisDrone/VisDrone2018-MOT-toolkit/master/README.md',
    'download_page': 'https://aiskyeye.com/download/',
}
ARCHIVES = {
    'DET-val': 'https://github.com/ultralytics/assets/releases/download/v0.0.0/VisDrone2019-DET-val.zip',
    'MOT-val': 'https://drive.usercontent.google.com/download?id=1rqnKe9IgU_crMaxRoel9_nuUsMEBBVQu&export=download&confirm=t',
}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


class Form(HTMLParser):
    def __init__(self):
        super().__init__(); self.action = None; self.fields = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'form': self.action = a.get('action')
        if tag == 'input' and a.get('name'): self.fields[a['name']] = a.get('value', '')


class RemoteZip(io.RawIOBase):
    """Seekable, bounded HTTP reader; refuse servers that ignore byte ranges."""
    def __init__(self, url, budget=128*1024**2):
        self.url=url; self.pos=0; self.fetched=0; self.budget=budget; self.cache={}
        with self.request('bytes=0-0') as r:
            if 'text/html' in r.headers.get('Content-Type', ''):
                form=Form(); form.feed(r.read(100000).decode())
                if not form.action or urllib.parse.urlparse(form.action).hostname != 'drive.usercontent.google.com':
                    raise ValueError('Not a supported public Google Drive confirmation form')
                self.url=form.action+'?'+urllib.parse.urlencode(form.fields)
        with self.request('bytes=0-0') as r:
            cr=r.headers.get('Content-Range','')
            if r.status != 206 or not re.fullmatch(r'bytes 0-0/\d+',cr):
                raise ValueError(f'HTTP range unavailable: {r.status}, {cr}')
            self.size=int(cr.split('/')[-1]); r.read(1)

    def request(self, byte_range):
        return urllib.request.urlopen(urllib.request.Request(self.url, headers={
            'Range':byte_range, 'User-Agent':'FPY-VisDrone-Pilot-Audit/1.0'}),timeout=45)

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        if self.pos < 0: raise ValueError('Negative seek')
        return self.pos

    def read(self, n=-1):
        n=min(self.size-self.pos, n if n>=0 else self.size)
        if n<=0:return b''
        if self.fetched+n>self.budget:raise ValueError('Pilot network budget exceeded')
        pieces=[];end=self.pos+n;block=256*1024
        while self.pos<end:
            start=self.pos//block*block;stop=min(start+block,self.size)
            if start not in self.cache:
                for attempt in range(5):
                    try:
                        with self.request(f'bytes={start}-{stop-1}') as r:
                            cr=r.headers.get('Content-Range','')
                            if r.status!=206 or cr!=f'bytes {start}-{stop-1}/{self.size}':
                                raise ValueError(f'Range mismatch: {r.status}, {cr}, type={r.headers.get("Content-Type")}, at={start}-{stop-1}')
                            blob=r.read(stop-start+1)
                        if len(blob)!=stop-start:raise ValueError('Truncated range')
                        if self.fetched+len(blob)>self.budget:raise ValueError('Pilot network budget exceeded')
                        self.cache[start]=blob;self.fetched+=len(blob);break
                    except Exception:
                        if attempt==4:raise
                        time.sleep(attempt+1)
            take=min(end,stop)-self.pos
            pieces.append(self.cache[start][self.pos-start:self.pos-start+take]);self.pos+=take
        return b''.join(pieces)


def save(path, blob):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=blob:raise ValueError(f'Refuse overwrite: {path}')
    path.write_bytes(blob)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inspect-only',action='store_true');args=ap.parse_args()
    out=DATA/'manifests';out.mkdir(parents=True,exist_ok=True)
    record={'retrieved_at':datetime.now(timezone.utc).isoformat(),'purpose':'PILOT_ONLY_NOT_FINAL_TEST',
            'selection':'DET: first image of first 12 filename-prefix groups plus first 3 bus-bearing images; all DET-val annotation files. MOT: 6 spread frames of every sequence plus ID/class-anomaly evidence frames 878,879,950,951 in uav0000268_05773_v.',
            'sources':[],'archives':[],'failures':[]}
    for name,url in SOURCES.items():
        try:
            p=DATA/'sources'/(name+('.html' if name=='download_page' else '.md'))
            reused=p.exists()
            if reused:blob=p.read_bytes()
            else:
                with urllib.request.urlopen(url,timeout=45) as r:blob=r.read(4*1024**2)
                save(p,blob)
            record['sources'].append({'name':name,'url':url,'path':str(p.relative_to(ROOT)),
                                     'sha256':sha(blob),'existing_snapshot_reused':reused})
        except Exception as e:record['failures'].append({'source':name,'error':str(e)})
    for name,url in ARCHIVES.items():
        a={'name':name,'url':url,'members':[]}
        try:
            remote=RemoteZip(url)
            with zipfile.ZipFile(remote) as z:
                names=z.namelist();a['size_bytes']=remote.size
                listing=[{'name':i.filename,'size':i.file_size,'crc32':f'{i.CRC:08x}'} for i in z.infolist()]
                (out/(name+'_archive_index.json')).write_text(json.dumps(listing,indent=2)+'\n',encoding='utf-8')
                print(name, remote.size, len(names),names[:8],flush=True)
                if args.inspect_only:
                    a['status']='INDEX_ONLY';record['archives'].append(a);continue
                selected=[]
                if name=='DET-val':
                    groups={}
                    for n in sorted(names):
                        if '/images/' in n and n.lower().endswith('.jpg'):
                            groups.setdefault(Path(n).stem.split('_')[0],n)
                    for n in list(groups.values())[:12]:
                        selected.extend([n,n.replace('/images/','/annotations/').rsplit('.',1)[0]+'.txt'])
                    annotations=sorted(n for n in names if '/annotations/' in n and n.endswith('.txt'))
                    selected.extend(annotations)
                    bus_images=[]
                    for n in annotations:
                        info=z.getinfo(n);p=DATA/'raw'/name/'annotations'/Path(n).name
                        if p.exists() and len(p.read_bytes())==info.file_size and zlib.crc32(p.read_bytes())==info.CRC:blob=p.read_bytes()
                        else:blob=z.read(n);save(p,blob)
                        rows=[line.split(',') for line in blob.decode('utf-8-sig').splitlines() if line.strip()]
                        if any(len(row)>=6 and row[4]=='1' and row[5]=='9' for row in rows):
                            bus_images.append(n.replace('/annotations/','/images/').rsplit('.',1)[0]+'.jpg')
                    selected.extend(bus_images[:3])
                else:
                    sequences={}
                    for n in sorted(names):
                        if '/sequences/' in n and n.lower().endswith('.jpg'):
                            sequences.setdefault(n.split('/sequences/')[1].split('/')[0],[]).append(n)
                    for seq,frames in sequences.items():
                        inds=sorted({0,1,len(frames)//2,len(frames)//2+1,len(frames)-2,len(frames)-1})
                        selected.extend(frames[i] for i in inds if 0<=i<len(frames))
                        selected.extend(n for n in names if '/annotations/' in n and Path(n).stem==seq)
                    a['sequences']={s:len(v) for s,v in sequences.items()}
                    for seq,frames in sequences.items():
                        if seq=='uav0000268_05773_v':
                            selected.extend(n for n in frames if int(Path(n).stem) in (878,879,950,951))
                selected.extend(n for n in names if re.search(r'(readme|license|copying)',n,re.I) and not n.endswith('/'))
                for n in sorted(set(selected)):
                    info=z.getinfo(n)
                    if info.file_size>25*1024**2:raise ValueError('Unexpected large member')
                    # Remove only the known top-level archive directory.
                    relative=Path(*n.split('/')[1:])
                    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe member')
                    p=DATA/'raw'/name/relative
                    if p.exists():
                        blob=p.read_bytes()
                        if len(blob)!=info.file_size or zlib.crc32(blob)!=info.CRC:raise ValueError(f'Existing member corrupt: {p}')
                    else:blob=z.read(n);save(p,blob)
                    a['members'].append({'archive_member':n,'path':str(p.relative_to(ROOT)),
                                         'size_bytes':len(blob),'sha256':sha(blob),'crc32':f'{info.CRC:08x}'})
                    print('saved',name,relative,flush=True)
            a['network_bytes']=remote.fetched;a['status']='FETCHED'
        except Exception as e:
            a['status']='FAILED';a['error']=str(e);print(name,'FAILED',e,flush=True)
        record['archives'].append(a)
        (out/'pilot_acquisition.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/('archive_inspection.json' if args.inspect_only else 'pilot_acquisition.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if any(a.get('status')=='FAILED' for a in record['archives']):raise SystemExit(1)


if __name__=='__main__':main()
