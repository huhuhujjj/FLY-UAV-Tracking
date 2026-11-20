"""Compare representative images from source groups across proposed stages."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from audit_visdrone import DATA, ROOT

SPLITS=('DET-train','DET-val','DET-test-dev','MOT-train','MOT-val','MOT-test-dev')

def stage(name):return 'train' if name.endswith('-train') else 'validation' if name.endswith('-val') else 'final_test'

def main():
    all_samples=[]
    for name in SPLITS:
        p=DATA/'manifests'/(name+'_lineage_samples.json')
        obj=json.loads(p.read_text(encoding='utf-8'))
        if obj['status']!='FETCHED':raise ValueError(f'{name} sample acquisition unfinished')
        if len(obj['samples'])!=obj['expected_groups']:raise ValueError(f'{name} sample count mismatch')
        for row in obj['samples']:
            local=ROOT/row['path']
            if hashlib.sha256(local.read_bytes()).hexdigest()!=row['image_sha256']:
                raise ValueError(f'Image checksum mismatch: {local}')
            all_samples.append(dict(row,split=name,stage=stage(name),
                                    source_prefix=row['source_group'].removeprefix('uav').split('_')[0]))
    exact=[];near=[];same_prefix=[];compared=0
    for a,b in combinations(all_samples,2):
        if a['stage']==b['stage']:continue
        compared+=1
        pair={'a':a['split']+':'+a['source_group'],'b':b['split']+':'+b['source_group']}
        if a['source_prefix']==b['source_prefix']:same_prefix.append(pair)
        if a['image_sha256']==b['image_sha256'] or a['pixel_sha256']==b['pixel_sha256']:
            exact.append(pair)
        distance=(int(a['dhash'],16)^int(b['dhash'],16)).bit_count()
        if distance<=8:near.append(dict(pair,dhash_distance=distance,
                                        same_prefix=a['source_prefix']==b['source_prefix']))
    result={'version':'lineage-representative-screen-1','status':'SAMPLE_SCREEN_COMPLETE_FULL_PIXEL_AUDIT_PENDING',
        'sampled_groups':len(all_samples),'compared_cross_stage_pairs':compared,
        'exact':exact,'dhash_le_8_candidates':near,'same_prefix_pairs':same_prefix,
        'limits':'One representative image per source group. Negative matches cannot establish full-sequence independence. dHash candidates require visual review.',
        'final_test_frozen':False,'g1_passed':False}
    out=DATA/'manifests/lineage_sample_screen.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in result.items() if k in
        ('sampled_groups','compared_cross_stage_pairs','exact','dhash_le_8_candidates','same_prefix_pairs')},ensure_ascii=False))

if __name__=='__main__':main()
