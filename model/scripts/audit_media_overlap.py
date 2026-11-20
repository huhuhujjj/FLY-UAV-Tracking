"""Aggregate full-media decode/boundary checks and cross-stage fingerprints."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict,Counter
from itertools import combinations
from pathlib import Path
from audit_visdrone import DATA,ROOT

SPLITS=('DET-train','DET-val','DET-test-dev','MOT-train','MOT-val','MOT-test-dev')
def stage(name):return 'train' if name.endswith('-train') else 'validation' if name.endswith('-val') else 'final_test'

def main():
    all_rows=[];summaries={};media_issues=[]
    for name in SPLITS:
        path=DATA/'manifests'/(name+'_media_audit.json')
        obj=json.loads(path.read_text(encoding='utf-8'))
        if obj['status']!='COMPLETE' or len(obj['media'])!=obj['expected_images']:
            raise ValueError(f'{name} incomplete')
        summaries[name]={'images':len(obj['media']),'counts':obj['counts'],'issues':len(obj['issues'])}
        for issue in obj['issues']:media_issues.append(dict(issue,split=name))
        for row in obj['media']:
            all_rows.append({'split':name,'stage':stage(name),'archive_member':row['archive_member'],
                'source_group':row['source_group'],'source_prefix':row['source_group'].removeprefix('uav').split('_')[0],
                'image_sha256':row['image_sha256'],'pixel_sha256':row['pixel_sha256'],'dhash':row['dhash']})
    exact={};same_dhash={};all_exact=[];all_dhash=[]
    for key,field,out in [('exact','pixel_sha256',all_exact),('same_dhash','dhash',all_dhash)]:
        buckets=defaultdict(list)
        for row in all_rows:buckets[row[field]].append(row)
        for value,items in buckets.items():
            stages={x['stage'] for x in items}
            if len(stages)>1:
                out.append({'fingerprint':value,'rows':[
                    {'split':x['split'],'group':x['source_group'],'member':x['archive_member']} for x in items],
                    'stages':sorted(stages)})
    cross_prefix_exact=[];cross_prefix_dhash=[]
    for group in all_exact:
        prefixes={x['group'].removeprefix('uav').split('_')[0] for x in group['rows']}
        if len(prefixes)>1:cross_prefix_exact.append(group)
    for group in all_dhash:
        prefixes={x['group'].removeprefix('uav').split('_')[0] for x in group['rows']}
        if len(prefixes)>1:cross_prefix_dhash.append(group)
    output={'version':'full-media-overlap-1','status':'FULL_MEDIA_DECODE_AND_EXACT_SCREEN_COMPLETE',
        'total_decoded_media':len(all_rows),'splits':summaries,'media_issues':media_issues,
        'exact_cross_stage_fingerprint_groups':all_exact,
        'same_dhash_cross_stage_fingerprint_groups':all_dhash,
        'exact_cross_prefix_groups':cross_prefix_exact,
        'same_dhash_cross_prefix_groups':cross_prefix_dhash,
        'meaning':'Exact pixel hashes detect identical decoded pixels. Same dHash is only a visual candidate and needs review. Similarity with nonzero distance and common lineage beyond filename prefixes remain pending.',
        'final_test_frozen':False,'g1_passed':False}
    path=DATA/'manifests/full_media_overlap_audit.json'
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'total_media':len(all_rows),'media_issues':len(media_issues),
        'exact_cross_stage_groups':len(all_exact),'same_dhash_cross_stage_groups':len(all_dhash),
        'cross_prefix_same_dhash':len(cross_prefix_dhash)},ensure_ascii=False))

if __name__=='__main__':main()
