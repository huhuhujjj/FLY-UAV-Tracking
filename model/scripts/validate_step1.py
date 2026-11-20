"""Validate definition artifacts only; never mark model/application tests passed."""
from pathlib import Path
import csv, json, re

P=Path(__file__).resolve().parents[2]
def read(name):return json.loads((P/name).read_text(encoding='utf-8'))
def validate():
 c=read('model/configs/project_scope.json');cl=read('model/configs/classes.json');targets=read('model/configs/acceptance_targets.json')
 assert c['implementation_status'] in ('STATIC_UI_ONLY','OFFLINE_MINIMUM_PIPELINE_VERIFIED_UI_STATIC')
 if c['implementation_status']=='OFFLINE_MINIMUM_PIPELINE_VERIFIED_UI_STATIC':
  proof=read('.qa/step3_verification.json')
  assert proof['checks'] and all(x.startswith('PASS') for x in proof['checks'].values())
  assert all(proof['runs'][key]['status']=='SUCCEEDED' for key in ('image_cpu','image_gpu','video_cpu','video_gpu'))
  assert c['offline_pilot']['system_acceptance']=='NOT_EXECUTED'
 assert c['operation']['max_input_files']==c['operation']['max_nonterminal_jobs']==1
 assert [(x['local_id'],x['name']) for x in cl['classes']]==[(0,'car'),(1,'bus'),(2,'truck')]
 assert cl['source_validation'] in ('NOT_EXECUTED','OFFICIAL_SCHEMA_AND_PILOT_VERIFIED')
 if cl['source_validation']=='OFFICIAL_SCHEMA_AND_PILOT_VERIFIED':
  assert [(x['local_id'],x['visdrone_source_id']) for x in cl['classes']]==[(0,4),(1,9),(2,6)]
  assert cl['full_data_audit_status'] in ('NOT_COMPLETE','FULL_MEDIA_AND_SOURCE_ANNOTATIONS_AUDITED_WITH_QUARANTINES')
  if cl['full_data_audit_status']=='FULL_MEDIA_AND_SOURCE_ANNOTATIONS_AUDITED_WITH_QUARANTINES':
   audit=read('model/data/manifests/full_media_overlap_audit.json')
   assert audit['status']=='FULL_MEDIA_DECODE_AND_EXACT_SCREEN_COMPLETE'
   assert audit['total_decoded_media']==42311
 states=c['states'];assert not set(states['terminal'])&set(states['nonterminal'])
 assert set(states['transitions'])==set(states['terminal']+states['nonterminal'])
 for s,following in states['transitions'].items():
  assert all(x in states['transitions'] for x in following)
  if s in states['terminal']:assert following==[]
 with (P/c['acceptance']['matrix']).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==19 and len({r['test_id'] for r in rows})==19
 assert all(r['status']=='NOT_EXECUTED' and not r['actual_result'] and not r['evidence_path'] for r in rows)
 covered={x for r in rows for x in r['requirements'].split()}
 expected={f'FR{i:02}' for i in range(1,20)}|{f'NFR{i:02}' for i in range(1,13)}|{f'DR{i:02}' for i in range(1,8)}|{f'IR{i:02}' for i in range(1,7)}
 assert expected<=covered, sorted(expected-covered)
 assert set(targets['targets'])==set(c['acceptance']['metrics'])
 assert all(x['threshold'] is None for x in targets['targets'].values())
 assert c['acceptance']['block_final_acceptance_if_unset']
 assert c['model_selection']['selected_weights'] is None and c['tracking']['selected_tracker'] is None
 result={'definition_check':'PASS','meaning':'File consistency only; this validator does not run inference, audit datasets or test the application.','acceptance_rows':len(rows),'requirement_ids_covered':len(expected),'system_acceptance':'NOT_EXECUTED','final_acceptance_blocked':True,'blockers':['pilot thresholds unset','full dataset independence audit incomplete','formal model validation and official evaluator parity incomplete']}
 (P/'logs/step1_definition_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':validate()
