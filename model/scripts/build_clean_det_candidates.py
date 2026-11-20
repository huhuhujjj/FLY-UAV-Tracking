"""Quantify a conservative no-ignore DET subset without freezing it."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from audit_visdrone import DATA

def main():
    plan=json.loads((DATA/'manifests/independent_split_candidates.json').read_text(encoding='utf-8'))
    stages=[('DET-train','train_candidate'),('DET-val','validation_candidate'),('DET-test-dev','final_test_candidate')]
    out={'version':'clean-det-candidates-1','status':'PILOT_OPTION_NOT_FROZEN',
         'policy':'Exclude any source image with ignored/others/score-0 rows and any quarantined source prefix. This loses substantial data and does not solve MOT ignore-aware evaluation.',
         'splits':{},'final_test_frozen':False,'g1_passed':False}
    for name,bucket in stages:
        allowed={x['source_prefix'] for x in plan[bucket]}
        conversion=json.loads((DATA/'manifests'/(name+'_conversion.json')).read_text(encoding='utf-8'))
        files=[];counts=Counter()
        for item in conversion['index']:
            prefix=item['image'].split('_')[0]
            if prefix not in allowed or item['contains_ignored_rows']:continue
            label=DATA/'processed/corpus_v1'/name/'labels'/(item['image']+'.txt')
            rows=label.read_text(encoding='utf-8').splitlines()
            counts['images']+=1;counts['empty_target_images']+=not rows
            for line in rows:counts[('car','bus','truck')[int(line.split()[0])]]+=1
            files.append({'image':item['image'],'source_prefix':prefix,'label':str(label.relative_to(DATA.parents[1])),
                          'label_sha256':item['label_sha256']})
        out['splits'][name]={'counts':dict(counts),'files':files}
    p=DATA/'manifests/clean_det_candidates.json'
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v['counts'] for k,v in out['splits'].items()},ensure_ascii=False))

if __name__=='__main__':main()
