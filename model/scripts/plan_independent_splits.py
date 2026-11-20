"""Build conservative candidate split manifests from source-prefix components.

This is a leakage triage plan, not a frozen final evaluation set. Test media
must still pass pixel duplicate and human lineage review before release.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict,Counter
from pathlib import Path
from audit_visdrone import DATA

SOURCE=DATA/'manifests/corpus_annotation_audit.json'
OUTPUT=DATA/'manifests/independent_split_candidates.json'

def main():
    audit=json.loads(SOURCE.read_text(encoding='utf-8'))
    components=defaultdict(list)
    for split,details in audit['splits'].items():
        for group,g in details['groups'].items():
            key=group.removeprefix('uav').split('_')[0]
            components[key].append({'split':split,'group':group,'annotation_files':g['annotation_files'],
                                    'selected_boxes':g['selected_boxes'],
                                    'archive_frames':g.get('archive_frames')})
    pilot=json.loads((DATA/'manifests/pilot_split_plan.json').read_text(encoding='utf-8'))
    pilot_keys={s.split(':',1)[1].removeprefix('uav').split('_')[0] for s in pilot['excluded_from_final_test_source_groups']}
    annotation_error_keys=set()
    for split,details in audit['splits'].items():
        for err in details['errors']:
            name=err.get('file','')
            if name: annotation_error_keys.add(Path(name).stem.removeprefix('uav').split('_')[0])
    media_error_keys=set();exact_keys=set()
    media_report=DATA/'manifests/full_media_overlap_audit.json'
    if media_report.exists():
        full=json.loads(media_report.read_text(encoding='utf-8'))
        if full['status']!='FULL_MEDIA_DECODE_AND_EXACT_SCREEN_COMPLETE':
            raise RuntimeError('Full media audit exists but is incomplete')
        for issue in full['media_issues']:
            member=issue['archive_member']
            if '/sequences/' in member:
                parts=member.split('/sequences/')[1].split('/')
                key=parts[0].removeprefix('uav').split('_')[0]
            else:key=Path(member).stem.split('_')[0]
            media_error_keys.add(key)
        for group in full['exact_cross_stage_fingerprint_groups']:
            for row in group['rows']:
                exact_keys.add(row['group'].removeprefix('uav').split('_')[0])
    confirmed_related={'0000086'}
    triage_path=DATA/'manifests/full_dhash_visual_triage_2026-11-18.json'
    near_pending=set()
    if triage_path.exists():
        triage=json.loads(triage_path.read_text(encoding='utf-8'))
        near_pending=set(triage['quarantine_pending_prefixes'])
    train=[];validation=[];final=[];quarantine=[]
    for key,items in sorted(components.items()):
        splits={x['split'] for x in items}
        stages={'train' if s.endswith('train') else 'validation' if s.endswith('val') else 'final_test' for s in splits}
        record={'source_prefix':key,'members':items,'stages_present':sorted(stages),
                'pilot_reviewed':key in pilot_keys,'confidence':'FILENAME_PREFIX_ONLY'}
        reasons=[]
        if key in annotation_error_keys:reasons.append('annotation_schema_or_ID_class_conflict')
        if key in media_error_keys:reasons.append('media_boundary_issue')
        if key in exact_keys:reasons.append('exact_cross_stage_pixel_match')
        if key in confirmed_related:reasons.append('visually_related_cross_task_source')
        if key in near_pending:reasons.append('near_duplicate_lineage_pending_review')
        if len(stages)>1:reasons.append('source_prefix_spans_proposed_stages')
        if key in pilot_keys and 'final_test' in stages:reasons.append('pilot_touched_final_test_candidate')
        if reasons:
            record['reasons']=reasons;quarantine.append(record)
        elif stages=={'train'}:train.append(record)
        elif stages=={'validation'}:validation.append(record)
        elif stages=={'final_test'}:final.append(record)
        else:raise AssertionError(stages)
    def summary(group):
        boxes=Counter()
        for comp in group:
            for member in comp['members']:boxes.update(member['selected_boxes'])
        return {'components':len(group),'source_members':sum(len(c['members']) for c in group),
                'annotation_files':sum(m['annotation_files'] for c in group for m in c['members']),
                'selected_boxes':dict(boxes)}
    result={'version':'split-candidates-1','status':'CANDIDATES_NOT_FROZEN',
            'basis_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'group_rule':'conservative union by numeric source prefix across DET/MOT and official splits',
            'limitations':['Prefix equality is a leakage warning, not proof of shared pixels.',
                           'Different prefixes may still depict the same place or recording.',
            'Exact cross-stage pixel matches and media-boundary issues are quarantined when the full audit exists; perceptual near-duplicate candidates still require visual review.',
            'Known MOT source-ID class conflicts and malformed DET boxes are quarantined.',
                           'Official test-dev labels inspected for data integrity only; never tune with them.'],
            'train_candidate':train,'validation_candidate':validation,'final_test_candidate':final,
            'quarantine':quarantine,
            'summary':{k:summary(v) for k,v in [('train_candidate',train),('validation_candidate',validation),
                                                ('final_test_candidate',final),('quarantine',quarantine)]},
            'final_test_frozen':False,'g1_passed':False}
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['summary'],ensure_ascii=False))

if __name__=='__main__':main()
