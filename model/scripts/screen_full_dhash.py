"""Vectorized cross-stage dHash candidate screen over every decoded media item.

Threshold four is a conservative triage threshold. Matches require visual or
source-lineage review; nonmatches do not prove independence.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import numpy as np
from audit_visdrone import DATA

SPLITS=('DET-train','DET-val','DET-test-dev','MOT-train','MOT-val','MOT-test-dev')
def stage(name):return 'train' if name.endswith('-train') else 'validation' if name.endswith('-val') else 'final_test'

def main():
    rows=[]
    for name in SPLITS:
        obj=json.loads((DATA/'manifests'/(name+'_media_audit.json')).read_text(encoding='utf-8'))
        if obj['status']!='COMPLETE':raise ValueError(name+' incomplete')
        rows.extend({'split':name,'stage':stage(name),'group':x['source_group'],
                     'prefix':x['source_group'].removeprefix('uav').split('_')[0],
                     'member':x['archive_member'],'dhash':int(x['dhash'],16)} for x in obj['media'])
    stages={s:[x for x in rows if x['stage']==s] for s in ('train','validation','final_test')}
    counts=Counter();examples=[];prefix_pairs=set()
    for left_stage,right_stage in (('train','validation'),('train','final_test'),('validation','final_test')):
        left=stages[left_stage];right=stages[right_stage]
        values=np.array([x['dhash'] for x in right],dtype=np.uint64)
        for start in range(0,len(left),128):
            chunk=left[start:start+128]
            queries=np.array([x['dhash'] for x in chunk],dtype=np.uint64)
            distances=np.bitwise_count(np.bitwise_xor(queries[:,None],values[None,:]))
            a_idx,b_idx=np.where(distances<=4)
            for ia,ib in zip(a_idx.tolist(),b_idx.tolist()):
                a=chunk[ia];b=right[ib];d=int(distances[ia,ib])
                counts['all_candidate_pairs']+=1
                if a['prefix']==b['prefix']:
                    counts['same_prefix_pairs']+=1;continue
                counts['different_prefix_pairs']+=1
                prefix_pairs.add((a['prefix'],b['prefix']))
                if len(examples)<5000:
                    examples.append({'a':a['split']+':'+a['group'],'a_member':a['member'],
                                     'b':b['split']+':'+b['group'],'b_member':b['member'],
                                     'dhash_distance':d})
            if start%2048==0:print(left_stage,right_stage,start,'/',len(left),flush=True)
    result={'version':'full-dhash-screen-1','status':'CANDIDATES_REQUIRE_VISUAL_REVIEW',
            'threshold_hamming_distance':4,'media_count':len(rows),'counts':dict(counts),
            'different_prefix_group_pairs':len(prefix_pairs),
            'different_prefix_examples':examples,
            'examples_truncated':counts['different_prefix_pairs']>len(examples),
            'limits':'dHash is a low-resolution perceptual signature; a candidate is not proof of duplicate source. Distance >4 cannot establish independence.',
            'final_test_frozen':False,'g1_passed':False}
    path=DATA/'manifests/full_dhash_screen.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'media_count':len(rows),**dict(counts),'different_prefix_group_pairs':len(prefix_pairs)},ensure_ascii=False))

if __name__=='__main__':main()
