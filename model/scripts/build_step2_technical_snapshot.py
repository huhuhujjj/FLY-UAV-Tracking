"""Build an integrity-checked technical snapshot; never grant data permission."""
from pathlib import Path
import hashlib, json, zipfile, re, html
from collections import Counter
from functools import cache

ROOT = Path(__file__).resolve().parents[2]
M = ROOT/'model/data/manifests'
OUT = M/'step2_technical_v1'

@cache
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024), b''): h.update(block)
    return h.hexdigest()

def read(name): return json.loads((M/name).read_text(encoding='utf-8'))
def write(path, obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    OUT.mkdir(exist_ok=True)
    evidence=ROOT/'.qa/step2_anomalies'
    evidence.mkdir(exist_ok=True)
    plan=read('independent_split_candidates.json')
    audit=read('corpus_annotation_audit.json')
    issues=read('full_media_overlap_audit.json')['media_issues']
    clean={x['image'] for x in read('clean_det_candidates.json')['splits']['DET-train']['files']}
    buckets={}
    for bucket in ('train_candidate','validation_candidate','final_test_candidate','quarantine'):
        for item in plan[bucket]:
            assert item['source_prefix'] not in buckets
            buckets[item['source_prefix']]=(bucket,item.get('reasons',[]))
    policy={'version':'step2-technical-v1','status':'TECHNICAL_SNAPSHOT_PENDING_LICENCE',
        'authority':'Assistant selected guide recommended options under user delegation; not a student signature.',
        'quarantine':'Entire source-prefix component for existing source conflicts, malformed boxes and lineage risks; do not repair source truth.',
        'det_training':'Only candidate DET-train images without ignore, others or score-zero records.',
        'det_evaluation':'Project local union coverage >= 0.5 policy; not official VisDrone score equivalence.',
        'mot_evaluation':'Deferred to G2; not evaluation-ready.',
        'licence':'User reports inquiry sent; reply not available locally.',
        'limitations':['Different prefixes and no perceptual hash match do not prove source independence.',
        'Final-test integrity inspection does not authorize parameter selection.',
        'Technical hash snapshot is not final-test freeze or permission to train.'],
        'final_test_frozen':False,'g1_passed':False}
    write(OUT/'policy.json',policy)
    rows=[]; extracts=[]; archives={}
    for split, data in audit['splits'].items():
        manifest=read(split+'_full_archive.json')
        archive=ROOT/manifest['path']
        assert sha(archive)==manifest['sha256'], split+' archive hash mismatch'
        archives[split]={'path':str(archive.relative_to(ROOT)),'sha256':manifest['sha256']}
        with zipfile.ZipFile(archive) as z:
            for entry in z.infolist():
                if not entry.filename.lower().endswith(('.jpg','.jpeg','.png')): continue
                stem=Path(entry.filename).stem
                if split.startswith('DET'):
                    prefix=stem.split('_')[0]; annotation=stem+'.txt'
                else:
                    sequence=Path(entry.filename).parent.name
                    prefix=sequence.removeprefix('uav').split('_')[0]; annotation=sequence+'.txt'
                bucket,reasons=buckets[prefix]
                ann=ROOT/'model/data/raw'/split/'annotations'/annotation
                ann_sha=sha(ann)
                assert ann_sha==data['annotation_sha256'][annotation]
                eligible=bucket!='quarantine' and (split!='DET-train' or stem in clean)
                rows.append({'split':split,'archive_member':entry.filename,'source_prefix':prefix,
                    'bucket':bucket,'archive_sha256':manifest['sha256'],'member_crc32':f'{entry.CRC:08x}',
                    'member_bytes':entry.file_size,'annotation':str(ann.relative_to(ROOT)),
                    'annotation_sha256':ann_sha,'technical_candidate':eligible,
                    'exclusion_reasons':reasons if bucket=='quarantine' else ([] if eligible else ['TRAIN_IMAGE_HAS_IGNORE_RECORDS']),
                    'usage':'NO_TRAINING_OR_FINAL_EVALUATION_RELEASE'})
            for n,issue in enumerate(issues,1):
                if issue['split']!=split: continue
                target=evidence/(f'{n:02d}_'+Path(issue['archive_member']).name)
                raw=z.read(issue['archive_member']);target.write_bytes(raw)
                ann=ROOT/'model/data/raw'/split/'annotations'/issue['annotation']
                lines=ann.read_text(encoding='utf-8-sig').splitlines()
                extracts.append(dict(issue,number=n,image_path=str(target.relative_to(ROOT)),image_sha256=hashlib.sha256(raw).hexdigest(),source_annotation_line=lines[issue['line']-1]))
    assert len(rows)==42311 and len(extracts)==37
    assert len({(r['split'],r['archive_member']) for r in rows})==len(rows)
    jsonl=OUT/'media_inventory.jsonl'
    jsonl.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    write(evidence/'issues.json',extracts)
    cards=[]
    for item in sorted(extracts,key=lambda x:x['number']):
        x,y,w,h=item['bbox_xywh'];iw,ih=item['image_size']
        cards.append(f"<article><h2>{item['number']:02d} {html.escape(item['split'])}</h2><p>{html.escape(item['archive_member'])}</p><svg viewBox='0 0 {iw} {ih}'><image href='{html.escape(Path(item['image_path']).name)}' width='{iw}' height='{ih}'/><circle cx='{x}' cy='{y}' r='14' fill='none' stroke='red' stroke-width='3'/></svg><p>标注第 {item['line']} 行；xywh={item['bbox_xywh']}；原始行：{html.escape(item['source_annotation_line'])}</p></article>")
    (evidence/'index.html').write_text("<!doctype html><meta charset='utf-8'><title>37条源框异常证据</title><style>body{max-width:1100px;margin:30px auto;font-family:Arial}article{border-top:1px solid #aaa;padding:20px}svg{width:100%}p{overflow-wrap:anywhere}</style><h1>37条源框异常证据</h1><p>红圈标示异常框起点。零尺寸框无法正常绘成矩形；原图保留不变，所属来源继续隔离。这不是模型预测。</p>"+''.join(cards),encoding='utf-8')
    counts=Counter((r['split'],r['technical_candidate']) for r in rows)
    summary={'status':'TECHNICAL_SNAPSHOT_VERIFIED_PENDING_LICENCE','media_records':len(rows),
        'source_components':{k:len(plan[k]) for k in ('train_candidate','validation_candidate','final_test_candidate','quarantine')},
        'technical_eligible_media':{s:counts[s,True] for s in audit['splits']},
        'archives_verified_sha256':archives,'anomaly_records_exported':len(extracts),
        'member_integrity':'Archive SHA256 plus member CRC and size; CRC is not a standalone cryptographic member hash.',
        'inputs_sha256':{n:sha(M/n) for n in ('independent_split_candidates.json','corpus_annotation_audit.json','full_media_overlap_audit.json','clean_det_candidates.json')},
        'final_test_frozen':False,'g1_passed':False}
    write(OUT/'verification.json',summary)
    hashes={str(p.relative_to(ROOT)):sha(p) for p in (OUT/'policy.json',jsonl,OUT/'verification.json',evidence/'issues.json',evidence/'index.html')}
    write(OUT/'SHA256.json',hashes)
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__': main()
