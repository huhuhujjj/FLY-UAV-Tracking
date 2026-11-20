"""Refresh the local project snapshot after documentation or layout changes."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / ".qa" / "release_manifest.json"
manifest = json.loads(PATH.read_text(encoding="utf-8"))
legacy_web_layout = any(item["path"] == "web/workspace.html" for item in manifest["files"])
updated = []
for item in manifest["files"]:
    name = item["path"]
    if legacy_web_layout and name == "web/README.md":
        name = "web/frontend/README.md"
    elif legacy_web_layout and name.startswith("web/") and not name.startswith(("web/frontend/", "web/backend/")):
        name = "web/frontend/" + name[4:]
    if name.startswith("Final Report/"):
        name = "docs/reports/" + name[len("Final Report/"):]
    elif name.startswith("CAT405_Proposal_YOLO_UAV_Tracking"):
        name = "docs/proposals/" + name
    elif name == "docs/项目说明与开发流程.docx":
        name = "docs/guides/项目说明与开发流程.docx"
    elif name.startswith(("configs/", "data/", "scripts/", "tests/")):
        name = "model/" + name
    updated.append(name)
updated += [
    "docs/step2_ignore_policy_pilot.md",
    "docs/step2_dataset_version_review.md",
    "docs/visdrone_2019_terms_query.md",
    "model/configs/det_ignore_policy.json",
    "model/src/visdrone_det_ignore.py",
    "model/scripts/audit_det_ignore_pilot.py",
    "model/tests/test_visdrone_det_ignore.py",
    "model/data/manifests/DET-val_ignore_policy_pilot.json",
    "model/scripts/download_visdrone_archives.py",
    "model/scripts/audit_visdrone_media.py",
    "model/scripts/audit_media_overlap.py",
    "model/scripts/screen_full_dhash.py",
    "model/scripts/convert_det_corpus.py",
    "model/scripts/build_clean_det_candidates.py",
    "model/data/manifests/full_media_overlap_audit.json",
    "model/data/manifests/full_dhash_screen.json",
    "model/data/manifests/full_dhash_visual_triage_2026-11-18.json",
    "model/data/manifests/clean_det_candidates.json",
    "model/data/manifests/DET-train_conversion.json",
    "model/data/manifests/DET-val_conversion.json",
    "model/data/manifests/DET-test-dev_conversion.json",
    "model/data/manifests/DET-train_full_archive.json",
    "model/data/manifests/DET-val_full_archive.json",
    "model/data/manifests/DET-test-dev_full_archive.json",
    "model/data/manifests/MOT-train_full_archive.json",
    "model/data/manifests/MOT-val_full_archive.json",
    "model/data/manifests/MOT-test-dev_full_archive.json",
    "model/data/manifests/DET-train_media_audit.json",
    "model/data/manifests/DET-val_media_audit.json",
    "model/data/manifests/DET-test-dev_media_audit.json",
    "model/data/manifests/MOT-train_media_audit.json",
    "model/data/manifests/MOT-val_media_audit.json",
    "model/data/manifests/MOT-test-dev_media_audit.json",
    "docs/step2_data_audit.md",
    "docs/step2_corpus_annotation_review.md",
    "docs/step2_hands_on_review.md",
    "logs/2026-11-18_step2_corpus.md",
    "model/scripts/fetch_visdrone_annotations.py",
    "model/scripts/audit_visdrone_corpus.py",
    "model/scripts/plan_independent_splits.py",
    "model/scripts/fetch_lineage_samples.py",
    "model/scripts/screen_lineage_samples.py",
    "model/data/manifests/corpus_annotation_audit.json",
    "model/data/manifests/independent_split_candidates.json",
    "model/data/manifests/lineage_sample_screen.json",
    "model/data/manifests/user_visual_review_2026-11-18.json",
    "model/data/manifests/lineage_sample_visual_review_2026-11-18.json",
    "model/data/manifests/DET-train_annotations_acquisition.json",
    "model/data/manifests/DET-test-dev_annotations_acquisition.json",
    "model/data/manifests/MOT-train_annotations_acquisition.json",
    "model/data/manifests/MOT-test-dev_annotations_acquisition.json",
    "model/data/manifests/DET-train_archive_index.json",
    "model/data/manifests/DET-test-dev_archive_index.json",
    "model/data/manifests/MOT-train_archive_index.json",
    "model/data/manifests/MOT-test-dev_archive_index.json",
    "model/data/manifests/DET-train_lineage_samples.json",
    "model/data/manifests/DET-val_lineage_samples.json",
    "model/data/manifests/DET-test-dev_lineage_samples.json",
    "model/data/manifests/MOT-train_lineage_samples.json",
    "model/data/manifests/MOT-val_lineage_samples.json",
    "model/data/manifests/MOT-test-dev_lineage_samples.json",
    "logs/2026-11-17_step2.md",
    "logs/step2_data_audit.json",
    "logs/20261117_step2_experiment.json",
    "model/scripts/fetch_visdrone_pilot.py",
    "model/scripts/audit_visdrone.py",
    "model/tests/test_visdrone_audit.py",
    "model/configs/dataset_pilot.json",
    "model/requirements-data-audit.txt",
    "model/data/manifests/pilot_acquisition.json",
    "model/data/manifests/pilot_media_manifest.json",
    "model/data/manifests/pilot_split_plan.json",
    "model/data/manifests/pilot_issues.json",
    "model/data/manifests/DET-val_archive_index.json",
    "model/data/manifests/MOT-val_archive_index.json",
    "model/data/sources/dataset_readme.md",
    "model/data/sources/det_toolkit_readme.md",
    "model/data/sources/mot_toolkit_readme.md",
    "model/data/sources/licence_review.md",
    "web/README.md",
    "web/backend/README.md",
    "docs/文档总览.md",
    "docs/requirements_acceptance_overview.md",
    "docs/document_manifest.csv",
    "model/scripts/update_document_manifest.py",
    "model/scripts/update_release_manifest.py",
    "docs/drafts/目录结构草稿_2026-11-17.txt",
    "model/README.md",
    "model/src/.gitkeep",
    "model/scripts/.gitkeep",
    "model/configs/.gitkeep",
    "model/data/.gitkeep",
    "model/weights/.gitkeep",
    "model/experiments/.gitkeep",
    "model/experiments/README.md",
    "model/tests/.gitkeep",
    "logs/README.md",
    "logs/2026-11-17_model_directory_consolidation.md",
    "logs/2026-11-17_requirements_acceptance_overview.md",
    "web/backend/logs/README.md",
]
updated += ['docs/step3_minimal_pipeline.md', 'logs/2026-11-19_step3.md', 'model/src/__init__.py', 'model/src/pipeline.py', 'model/src/evaluation.py', 'model/scripts/run_offline.py', 'model/scripts/evaluate_offline.py', 'model/scripts/prepare_step3_media.py', 'model/scripts/verify_step3.py', 'model/scripts/download_step3_weights.py', 'model/tests/test_offline_evaluation.py', 'model/configs/offline_pilot.json', 'model/data/manifests/step3_entry_decision.json', 'model/data/manifests/step3_development_media.json', 'model/requirements-inference.txt', 'model/requirements-inference-windows-lock.txt', 'model/requirements-inference-docker-lock.txt', 'Dockerfile.offline', 'Dockerfile.offline.dockerignore', 'VERSION', 'docs/版本管理规范.md']
records = []
for name in sorted(set(updated), key=str.casefold):
    path = ROOT / name
    if not path.is_file():
        raise FileNotFoundError(path)
    records.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
manifest["files"] = records
manifest["design_report"] = "docs/reports/CAT405_System_Requirements_and_Design_ZHANG_XIAOHUI.docx"
manifest["active_pages"] = [
    "web/frontend/workspace.html",
    "web/frontend/image-detection.html",
    "web/frontend/index.html",
    "web/frontend/task-history.html",
    "web/frontend/evaluation.html",
]
manifest["implementation_status"] = (
    "Five-page static UI; no web processing backend. Offline image/video detection and within-video "
    "ByteTrack pilot exercised on Windows and Docker CPU/GPU. No training or system acceptance. "
    "Step 2 technical preparation complete with limitations; licence applicability follow-up remains. "
    "G1 not marked passed; final test not frozen. Local evaluation only; fragmentation withheld."
)
manifest["version"] = (ROOT/"VERSION").read_text(encoding="utf-8").strip()
manifest["offline_evidence"] = [".qa/step3_verification.json", ".qa/step3_docker_verification.json", ".qa/step3_unit_tests.log"]
now = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
manifest["snapshot_date"] = now.date().isoformat()
manifest["snapshot_at"] = now.isoformat(timespec="seconds")
PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Updated {len(records)} file hashes in {PATH}")
