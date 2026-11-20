"""Lossless annotation audit and three-class YOLO derivatives; no model execution.

Run after fetch_visdrone_pilot.py. All fetched/inspected media are development
pilot data. This script deliberately cannot approve an independent final test.
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT/'model/data'
MAP = {4:0, 9:1, 6:2}
NAMES = {0:'car',1:'bus',2:'truck'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_line(line, kind, line_number):
    """Keep source integers, ignore flags, IDs and attributes; reject bad schemas."""
    fields=line.strip().split(',')
    if fields[-1]=='':fields.pop()  # Some official rows have a terminal comma.
    if len(fields)!=(8 if kind=='DET' else 10):raise ValueError('wrong field count')
    try:v=[int(x) for x in fields]
    except ValueError:raise ValueError('annotation fields must be integers') from None
    frame,tid=(None,None) if kind=='DET' else v[:2]
    x,y,w,h,score,category,trunc,occ=v[-8:]
    if score not in (0,1) or category not in range(12):raise ValueError('unknown score/category')
    if trunc not in (0,1,2) or occ not in (0,1,2):raise ValueError('unknown attribute')
    if w<=0 or h<=0:raise ValueError('nonpositive box')
    if kind=='MOT' and (frame<1 or (score==1 and category in MAP and tid<0)):
        raise ValueError('invalid frame/target ID')
    return {'source_line':line_number,'frame_index':frame,'target_id':tid,
            'bbox_xywh':[x,y,w,h],'score':score,'source_category':category,
            'truncation':trunc,'occlusion':occ,'local_class':MAP.get(category),
            'ignored':score==0 or category in (0,11),'raw_fields':v}


def eligible(row,width,height):
    x,y,w,h=row['bbox_xywh']
    return (not row['ignored'] and row['local_class'] is not None and
            x>=0 and y>=0 and x+w<=width and y+h<=height)


def yolo(row,width,height):
    x,y,w,h=row['bbox_xywh']
    return f"{row['local_class']} {(x+w/2)/width:.8f} {(y+h/2)/height:.8f} {w/width:.8f} {h/height:.8f}"


def decode_yolo(line,width,height):
    c,cx,cy,w,h=map(float,line.split())
    return int(c),[(cx-w/2)*width,(cy-h/2)*height,w*width,h*height]


def dhash(image):
    vals=list(image.convert('L').resize((9,8)).tobytes())
    return sum((vals[y*9+x]>vals[y*9+x+1])<<(y*8+x) for y in range(8) for x in range(8))


def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def draw_overlay(image, rows, lines, title):
    """Both panels in source coordinates, then identically downscale for viewing."""
    left=image.copy();right=image.copy();dl=ImageDraw.Draw(left);dr=ImageDraw.Draw(right)
    colors={0:'#00d9ff',1:'#ffb000',2:'#f062d6'}
    for r in rows:
        x,y,w,h=r['bbox_xywh'];color=colors.get(r['local_class'],'#999999')
        if r['ignored']:color='#ff4444'
        dl.rectangle((x,y,x+w,y+h),outline=color,width=2)
        if r['local_class'] is not None and not r['ignored']:
            dl.text((x,max(0,y-12)),f"src{r['source_category']} id{r['target_id']}",fill=color,stroke_width=1,stroke_fill='black')
    for line in lines:
        c,(x,y,w,h)=decode_yolo(line,image.width,image.height)
        dr.rectangle((x,y,x+w,y+h),outline=colors[c],width=2)
        dr.text((x,max(0,y-12)),f'{c}:{NAMES[c]}',fill=colors[c],stroke_width=1,stroke_fill='black')
    width=min(1000,image.width);height=round(image.height*width/image.width)
    canvas=Image.new('RGB',(width*2,height+52),'#18202c');d=ImageDraw.Draw(canvas)
    d.text((12,6),title,fill='white');d.text((12,27),'SOURCE all categories / red = ignored',fill='white')
    d.text((width+12,27),'YOLO decoded car / bus / truck',fill='white')
    canvas.paste(left.resize((width,height)),(0,52));canvas.paste(right.resize((width,height)),(width,52))
    return canvas


def run(data=DATA):
    derived=data/'processed/pilot_v1';derived.mkdir(parents=True,exist_ok=True)
    qa=ROOT/'.qa/step2_data';qa.mkdir(parents=True,exist_ok=True)
    acquisition=json.loads((data/'manifests/pilot_acquisition.json').read_text(encoding='utf-8'))
    errors=[];warnings=[];all_rows=[];ann_stats={};mot_by_seq={};annotation_hashes={}
    for a in acquisition['archives']:
        if a.get('status')!='FETCHED':errors.append({'archive':a['name'],'error':'acquisition incomplete'})
        for member in a.get('members',[]):
            p=ROOT/member['path']
            if not p.is_file() or digest(p)!=member['sha256']:
                errors.append({'path':member['path'],'error':'acquisition checksum mismatch'})
    for kind in ('DET','MOT'):
        counts=Counter();class_stats=defaultdict(Counter);sequences={}
        for p in sorted((data/f'raw/{kind}-val/annotations').glob('*.txt')):
            rows=[];seen=set();id_class={}
            for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
                if not line.strip():continue
                try:r=parse_line(line,kind,i)
                except ValueError as e:errors.append({'path':str(p.relative_to(ROOT)),'line':i,'error':str(e)});continue
                r.update(kind=kind,annotation=str(p.relative_to(ROOT)),sequence=p.stem if kind=='MOT' else None)
                rows.append(r);all_rows.append(r);counts['source_rows']+=1
                counts[f"category_{r['source_category']}"]+=1
                if r['ignored']:counts['ignored_rows']+=1
                elif r['local_class'] is not None:
                    c=NAMES[r['local_class']];class_stats[c]['boxes']+=1
                    class_stats[c][f"occlusion_{r['occlusion']}"]+=1
                    class_stats[c][f"truncation_{r['truncation']}"]+=1
                    area=r['bbox_xywh'][2]*r['bbox_xywh'][3]
                    class_stats[c]['small_area_lt_1024' if area<1024 else 'medium_area_lt_9216' if area<9216 else 'large_area_ge_9216']+=1
                    if kind=='MOT':
                        key=(r['frame_index'],r['target_id'])
                        if key in seen:errors.append({'path':str(p.relative_to(ROOT)),'line':i,'error':'duplicate selected frame/ID'})
                        seen.add(key)
                        if r['target_id'] in id_class and id_class[r['target_id']]!=r['source_category']:
                            errors.append({'path':str(p.relative_to(ROOT)),'line':i,'error':'selected ID category changes',
                                           'target_id':r['target_id'],'frame':r['frame_index'],
                                           'previous_category':id_class[r['target_id']],'new_category':r['source_category']})
                        id_class[r['target_id']]=r['source_category']
            annotation_hashes[str(p.relative_to(ROOT))]=digest(p)
            if kind=='MOT':
                mot_by_seq[p.stem]=defaultdict(list)
                for r in rows:mot_by_seq[p.stem][r['frame_index']].append(r)
                sequences[p.stem]={'rows':len(rows),'annotated_frames':len(mot_by_seq[p.stem]),
                    'min_frame':min(mot_by_seq[p.stem],default=None),'max_frame':max(mot_by_seq[p.stem],default=None),
                    'selected_class_boxes':dict(Counter(NAMES[r['local_class']] for r in rows if not r['ignored'] and r['local_class'] is not None)),
                    'selected_source_ids':len(id_class)}
        ann_stats[kind]={'counts':dict(counts),'selected_classes':dict(class_stats),'sequences':sequences,
                         'scope':'fetched annotation files; MOT files cover full sequences, not just fetched frames'}
    with (derived/'source_annotations.jsonl').open('w',encoding='utf-8') as f:
        for r in all_rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    index=json.loads((data/'manifests/MOT-val_archive_index.json').read_text(encoding='utf-8'))
    frame_sets=defaultdict(set)
    for entry in index:
        if '/sequences/' in entry['name'] and entry['name'].endswith('.jpg'):
            seq,filename=entry['name'].split('/sequences/')[1].split('/')
            frame_sets[seq].add(int(Path(filename).stem))
    for seq,frames in mot_by_seq.items():
        unknown=sorted(set(frames)-frame_sets[seq])
        if unknown:errors.append({'sequence':seq,'error':'annotation references nonexistent archive frames','frames':unknown})
        ann_stats['MOT']['sequences'][seq]['archive_frames']=len(frame_sets[seq])
        ann_stats['MOT']['sequences'][seq]['unannotated_archive_frames']=len(frame_sets[seq]-set(frames))
    media=[];roundtrip_max=0;pilot_counts=defaultdict(Counter)
    for kind in ('DET','MOT'):
        folder=data/f'raw/{kind}-val'/('images' if kind=='DET' else 'sequences')
        for p in sorted(folder.rglob('*.jpg')):
            seq=p.parent.name if kind=='MOT' else p.stem.split('_')[0]
            frame=int(p.stem) if kind=='MOT' else None
            if kind=='DET':rows=[r for r in all_rows if r['kind']=='DET' and Path(r['annotation']).stem==p.stem]
            else:rows=mot_by_seq.get(seq,{}).get(frame,[])
            ann=data/f'raw/{kind}-val/annotations'/(p.stem+'.txt' if kind=='DET' else seq+'.txt')
            if not ann.exists():errors.append({'path':str(p.relative_to(ROOT)),'error':'missing annotations'});continue
            try:
                with Image.open(p) as im:im.load();image=im.convert('RGB')
            except Exception as e:errors.append({'path':str(p.relative_to(ROOT)),'error':'image decode '+str(e)});continue
            for r in rows:
                x,y,w,h=r['bbox_xywh']
                if x<0 or y<0 or x+w>image.width or y+h>image.height:
                    warnings.append({'path':str(p.relative_to(ROOT)),'line':r['source_line'],'issue':'out_of_bounds_preserved_not_clipped',
                                     'selected':not r['ignored'] and r['local_class'] is not None})
            selected=[r for r in rows if eligible(r,image.width,image.height)]
            lines=[yolo(r,image.width,image.height) for r in selected]
            for r,line in zip(selected,lines):
                c,box=decode_yolo(line,image.width,image.height)
                assert c==r['local_class']
                roundtrip_max=max(roundtrip_max,max(abs(a-b) for a,b in zip(box,r['bbox_xywh'])))
            key=f'{kind}_{seq}_{p.stem}'
            label=derived/'labels'/(key+'.txt');label.parent.mkdir(exist_ok=True)
            label.write_text('\n'.join(lines)+ ('\n' if lines else ''),encoding='utf-8')
            overlay=qa/(key+'.jpg');draw_overlay(image,rows,lines,key).save(overlay,quality=88)
            for r in selected:pilot_counts[kind][NAMES[r['local_class']]]+=1
            media.append({'key':key,'kind':kind,'official_split':'val','role':'development_pilot',
                'image':str(p.relative_to(ROOT)),'annotation':str(ann.relative_to(ROOT)),
                'source_group':seq,'source_group_status':'sequence_id' if kind=='MOT' else 'filename_prefix_candidate_not_verified',
                'frame_index':frame,'timestamp_ms':None,'fps_status':'NOT_VERIFIED',
                'width':image.width,'height':image.height,'image_sha256':digest(p),
                'pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest(),'dhash':f'{dhash(image):016x}',
                'annotation_sha256':digest(ann),'label':str(label.relative_to(ROOT)),'label_sha256':digest(label),
                'source_rows':len(rows),'selected_boxes':len(lines),'ignored_rows':sum(r['ignored'] for r in rows),
                'overlay':str(overlay.relative_to(ROOT))})
    exact=[];near=[];prefix=[]
    for i,a in enumerate(media):
        for b in media[i+1:]:
            if a['kind']==b['kind']:continue
            pair={'a':a['key'],'b':b['key']}
            if a['image_sha256']==b['image_sha256'] or a['pixel_sha256']==b['pixel_sha256']:exact.append(pair)
            distance=(int(a['dhash'],16)^int(b['dhash'],16)).bit_count()
            if distance<=8:near.append(dict(pair,dhash_distance=distance))
            if a['source_group'].lstrip('0')==b['source_group'].split('_')[0].removeprefix('uav').lstrip('0'):prefix.append(pair)
    coverage={a['name']:{'archive_members':len(a.get('members',[])),'status':a.get('status')} for a in acquisition['archives']}
    blockers=['Only validation pilot media acquired; train and final-test corpora not audited.',
        'Cross-task source lineage and full-corpus near-duplicate review are not complete.',
        'Explicit dataset licence/version and redistribution terms still require authoritative confirmation.',
        'Ignore-region training/evaluation adapter is not implemented; YOLO derivatives are audit artifacts.',
        'No independent final-test manifest is frozen; all inspected samples are excluded from future blind testing.']
    for kind in ('DET','MOT'):
        absent=[name for name in NAMES.values() if not pilot_counts[kind][name]]
        if absent:blockers.append(f'{kind} pilot media lack converted examples for: '+', '.join(absent))
    if errors:blockers.append('Annotation/decode errors require resolution.')
    if any(w['selected'] for w in warnings):blockers.append('Selected out-of-bounds boxes require a reviewed clipping/rejection policy.')
    report={'audit_version':'visdrone-pilot-1','date':'2026-11-17','status':'PILOT_AUDITED_G1_NOT_PASSED',
        'runtime':{'python':sys.version,'platform':platform.platform()},'acquisition':coverage,
        'mapping':{'4':'0 car','9':'1 bus','6':'2 truck','5':'excluded van'},
        'annotation_file_statistics':ann_stats,'pilot_media':len(media),'pilot_images_by_task':dict(Counter(m['kind'] for m in media)),
        'pilot_converted_boxes':dict(pilot_counts),'conversion_roundtrip_max_error_px':roundtrip_max,
        'conversion_roundtrip_check':'PASS' if roundtrip_max<=0.001 else 'FAIL',
        'annotation_errors':errors,'warnings':warnings,
        'overlap':{'scope':'downloaded DET/MOT pilot image pairs only','exact_matches':exact,
                   'dhash_candidates_le_8':near,'filename_candidates':prefix,
                   'meaning':'No hit does not establish source independence; hash similarity is triage, not lineage proof.'},
        'final_test_frozen':False,'g1_passed':False,'training_ready':False,'blockers':blockers,
        'application_acceptance':'NOT_EXECUTED','annotation_sha256':annotation_hashes}
    write_json(data/'manifests/pilot_media_manifest.json',media)
    write_json(data/'manifests/pilot_split_plan.json',{
        'version':'pilot-splits-1','status':'NOT_FROZEN','train':[],'validation':[], 'final_test':[],
        'development_pilot':[m['key'] for m in media], 'excluded_from_final_test_source_groups':sorted({m['kind']+':'+m['source_group'] for m in media}),
        'policy':'Keep whole source sequences together; audit full corpus and cross-task lineage before freeze; no final-test tuning.',
        'reason':'Pilot inspection consumes these samples for development; empty final_test is unavailable, never passed.'})
    write_json(ROOT/'logs/step2_data_audit.json',report)
    with (qa/'visual_review.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['key','overlay','review_status','notes']);w.writeheader()
        for m in media:w.writerow({'key':m['key'],'overlay':m['overlay'],'review_status':'PENDING','notes':''})
    print(json.dumps({k:report[k] for k in ['status','pilot_images_by_task','pilot_converted_boxes','conversion_roundtrip_max_error_px','conversion_roundtrip_check']},ensure_ascii=False))
    print('errors',len(errors),'warnings',len(warnings),'overlap',len(exact),len(near),'G1 NOT PASSED')
    return report


if __name__=='__main__':run()
