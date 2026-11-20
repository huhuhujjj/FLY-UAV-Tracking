import urllib.request,hashlib
from pathlib import Path
p=Path('model/weights/yolo26l.pt')
expected='9fe3c544f2b19bebad7ea41e76d7ad3d88b7c2f10d11d24430c5311f6b32db26'
if p.exists():
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,'Existing weights differ; preserve for inspection'
    print('Verified existing weights:',p)
    raise SystemExit(0)
tmp=p.with_suffix('.download')
url='https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26l.pt'
with urllib.request.urlopen(url, timeout=120) as source, tmp.open('wb') as target:
    while block:=source.read(1024*1024): target.write(block)
assert hashlib.sha256(tmp.read_bytes()).hexdigest()==expected,'Download hash mismatch'
tmp.replace(p)
print(p,p.stat().st_size)
