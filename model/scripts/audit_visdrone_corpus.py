"""Audit all acquired annotation files and archive membership without using test data for tuning."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from audit_visdrone import DATA, ROOT, MAP, NAMES, parse_line

SPLITS=('DET-train','DET-val','DET-test-dev','MOT-train','MOT-val','MOT-test-dev')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def inventory(name):
    kind=name.split('-')[0];folder=DATA/'raw'/name/'annotations'
    files=sorted(folder.glob('*.txt'))
    if not files:raise FileNotFoundError(f'No annotations: {folder}')
    archive=json.loads((DATA/'manifests'/(name+'_archive_index.json')).read_text(encoding='utf-8'))
    ann_members=[x for x in archive if '/annotations/' in x['name'] or x['name'].startswith('annotations/')]
    img_members=[x for x in archive if '/images/' in x['name'] or x['name'].startswith('images/')]
    frame_members=[x for x in archive if '/sequences/' in x['name'] or x['name'].startswith('sequences/')]
    ann_members=[x for x in ann_members if x['name'].endswith('.txt')]
    img_members=[x for x in img_members if x['name'].lower().endswith(('.jpg','.jpeg','.png'))]
    frame_members=[x for x in frame_members if x['name'].lower().endswith(('.jpg','.jpeg','.png'))]
    if len(files)!=len(ann_members):raise ValueError(f'{name}: acquired {len(files)} annotation files, archive lists {len(ann_members)}')
    counts=Counter();by_class=defaultdict(Counter);groups={};errors=[];filename_hashes={}
    for p in files:
        local=Counter();ids=defaultdict(set);seen=set();class_by_id={};flagged=set();n=0
        for line_no,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
            if not line.strip():continue
            try:r=parse_line(line,kind,line_no)
            except ValueError as e:errors.append({'file':p.name,'line':line_no,'error':str(e)});continue
            n+=1;counts['rows']+=1;local['rows']+=1
            c=r['source_category'];counts[f'category_{c}']+=1
            if r['ignored']:counts['ignored']+=1;local['ignored']+=1
            if r['local_class'] is not None and not r['ignored']:
                label=NAMES[r['local_class']];counts[label]+=1;local[label]+=1
                area=r['bbox_xywh'][2]*r['bbox_xywh'][3]
                by_class[label]['small' if area<1024 else 'medium' if area<9216 else 'large']+=1
                by_class[label][f'occlusion_{r["occlusion"]}']+=1
                by_class[label][f'truncation_{r["truncation"]}']+=1
                if kind=='MOT':
                    key=(r['frame_index'],r['target_id'])
                    if key in seen:errors.append({'file':p.name,'line':line_no,'error':'duplicate selected frame/ID'})
                    seen.add(key);ids[label].add(r['target_id'])
                    prior=class_by_id.setdefault(r['target_id'],c)
                    if prior!=c and (r['target_id'],c) not in flagged:
                        flagged.add((r['target_id'],c))
                        errors.append({'file':p.name,'line':line_no,'frame_index':r['frame_index'],
                                       'source_id':r['target_id'],'error':'selected ID category changes',
                                       'first_category':prior,'current_category':c})
            if kind=='MOT':local['max_frame']=max(local['max_frame'],r['frame_index'])
        filename_hashes[p.name]=sha(p)
        group=p.stem if kind=='MOT' else p.stem.split('_')[0]
        item=groups.setdefault(group,{'annotation_files':0,'rows':0,'selected_boxes':Counter(),
                                      'source_names':[],'source_ids':set()})
        item['annotation_files']+=1;item['rows']+=n;item['selected_boxes'].update({c:local[c] for c in NAMES.values()})
        item['source_names'].append(p.stem)
        if kind=='MOT':
            item['source_ids'].update(class_by_id)
            item['max_frame']=local['max_frame']
    if kind=='MOT':
        archive_seq=defaultdict(set)
        for entry in frame_members:
            parts=entry['name'].split('/sequences/')[-1].split('/')
            if len(parts)==2:archive_seq[parts[0]].add(Path(parts[1]).stem)
        for g,item in groups.items():
            item['archive_frames']=len(archive_seq[g]);item['source_id_count']=len(item['source_ids'])
            if item['max_frame']>len(archive_seq[g]):errors.append({'file':g,'error':'annotation frame exceeds archive frame count'})
            del item['source_ids']
    else:
        for item in groups.values():del item['source_ids']
        archive_names={Path(x['name']).stem for x in img_members}
        missing=sorted(set(p.stem for p in files)-archive_names)
        extra=sorted(archive_names-set(p.stem for p in files))
        if missing:errors.append({'error':'annotation without image archive member','count':len(missing),'examples':missing[:8]})
        if extra:errors.append({'error':'image without annotation archive member','count':len(extra),'examples':extra[:8]})
    for item in groups.values():item['selected_boxes']=dict(item['selected_boxes'])
    return {'split':name,'annotation_files':len(files),'archive_images_or_frames':len(img_members or frame_members),
            'archive_uncompressed_member_bytes':sum(x['size'] for x in archive),'counts':dict(counts),
            'by_class':{c:dict(v) for c,v in by_class.items()},'groups':groups,'errors':errors,
            'annotation_sha256':filename_hashes,'audit_scope':'annotation rows and ZIP index; image pixels not fully acquired or verified'}

def main():
    results={}
    for name in SPLITS:
        results[name]=inventory(name)
        print(name,results[name]['annotation_files'],'files',results[name]['counts']['rows'],'rows',
              len(results[name]['errors']),'issues',flush=True)
    det_groups=defaultdict(set);mot_groups=defaultdict(set)
    for name,r in results.items():
        dest=det_groups if name.startswith('DET') else mot_groups
        for g in r['groups']:dest[g.removeprefix('uav').split('_')[0]].add(name+':'+g)
    same_prefix={g:sorted(det_groups[g]|mot_groups[g]) for g in det_groups.keys()&mot_groups.keys()}
    reused={g:sorted(v) for g,v in same_prefix.items() if len(v)>1}
    output={'version':'corpus-annotation-audit-1','status':'ANNOTATION_INVENTORY_COMPLETE_MEDIA_LINEAGE_PENDING',
            'splits':results,'cross_task_shared_numeric_prefix_candidates':reused,
            'cross_task_warning':'Prefix match is only a lineage candidate; nonmatching prefixes do not prove independence.',
            'final_test_frozen':False,'g1_passed':False,
            'train_val_test_policy':'Official splits are candidates only; hold final test from model/threshold selection. Preserve whole related sources.'}
    out=DATA/'manifests/corpus_annotation_audit.json'
    out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('saved',out,'cross-task prefix candidates',len(reused))

if __name__=='__main__':main()
