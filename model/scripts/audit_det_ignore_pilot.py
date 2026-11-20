"""Apply the local ignore policy to DET validation candidates, without a model."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from audit_visdrone import DATA, ROOT, parse_line

sys.path.insert(0, str(ROOT / 'model/src'))
from visdrone_det_ignore import prepare_image


def main():
    plan_path = DATA/'manifests/independent_split_candidates.json'
    media_path = DATA/'manifests/DET-val_media_audit.json'
    policy_path = ROOT/'model/configs/det_ignore_policy.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    media = json.loads(media_path.read_text(encoding='utf-8'))
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    if media['status'] != 'COMPLETE' or plan['status'] != 'CANDIDATES_NOT_FROZEN':
        raise ValueError('Required audit input is incomplete')
    if policy['version'] != 'det-ignore-project-pilot-1':
        raise ValueError('Unexpected policy')
    allowed = {x['source_prefix'] for x in plan['validation_candidate']}
    totals = Counter()
    by_class = Counter()
    per_image = []
    for image in media['media']:
        stem = Path(image['archive_member']).stem
        if stem.split('_')[0] not in allowed:
            continue
        ann = DATA/'raw/DET-val/annotations'/(stem+'.txt')
        rows = [parse_line(line, 'DET', n) for n,line in enumerate(
                ann.read_text(encoding='utf-8-sig').splitlines(),1) if line.strip()]
        result = prepare_image(rows, [], image['width'], image['height'])
        totals.update(result['counts'])
        totals['images'] += 1
        totals['images_with_ignore_boxes'] += bool(result['counts']['ignore_boxes'])
        by_class.update(('car','bus','truck')[x['local_class']] for x in result['ground_truth'])
        per_image.append({'image':stem,'source_annotation_sha256':hashlib.sha256(ann.read_bytes()).hexdigest(),
                          'source_targets':result['counts']['source_target_boxes'],
                          'target_boxes_ignored':result['counts']['target_boxes_ignored'],
                          'retained_targets':len(result['ground_truth']),
                          'ignore_boxes':result['counts']['ignore_boxes']})
    output = {'version':'det-ignore-pilot-1','status':'LOCAL_POLICY_PILOT_NO_MODEL_EVALUATION',
              'split':'DET-val','candidate_plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),
              'policy_sha256':hashlib.sha256(policy_path.read_bytes()).hexdigest(),
              'counts':dict(totals),'retained_by_class':dict(by_class),'images':per_image,
              'official_score_equivalent':False,'training_policy_frozen':False,
              'final_test_frozen':False,'g1_passed':False}
    path = DATA/'manifests/DET-val_ignore_policy_pilot.json'
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'counts':output['counts'],'retained_by_class':output['retained_by_class']},ensure_ascii=False))


if __name__ == '__main__':main()
