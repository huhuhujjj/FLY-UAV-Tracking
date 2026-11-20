"""Write a checksum inventory for the project's active documentation."""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "document_manifest.csv"
FILES = [
    ("README.md", "project_entry", "active"),
    ("CHANGELOG.md", "change_log", "active"),
    ("docs/proposals/CAT405_Proposal_YOLO_UAV_Tracking.docx", "proposal_english", "canonical"),
    ("docs/proposals/CAT405_Proposal_YOLO_UAV_Tracking_ZH.docx", "proposal_chinese", "companion"),
    ("docs/reports/CAT405_System_Requirements_and_Design_ZHANG_XIAOHUI.docx", "system_design", "canonical"),
    ("docs/reports/CAT405_System_Requirements_and_Design_ZHANG_XIAOHUI.md", "system_design_text", "older_draft"),
    ("docs/reports/CAT405_Final_Report_Feasibility_SRS_ZH.docx", "feasibility_srs", "active"),
    ("docs/reports/CAT405_Final_Report_Feasibility_SRS_ZH.md", "feasibility_srs_text", "verify_before_use"),
    ("docs/guides/项目说明与开发流程.docx", "project_guide", "active"),
    ("docs/step3_minimal_pipeline.md", "offline_minimum_chain", "development_verified_with_limitations"),
    ("docs/step2_remaining_work_2026-11-19.md", "technical_snapshot", "technical_preparation_complete_terms_followup"),
    ("docs/step1_scope_and_acceptance.md", "scope_acceptance", "active"),
    ("docs/step2_data_audit.md", "data_pilot_audit", "active_g1_incomplete"),
    ("docs/step2_corpus_annotation_review.md", "corpus_annotation_audit", "active_g1_incomplete"),
    ("docs/step2_ignore_policy_pilot.md", "det_ignore_policy_pilot", "active_g1_incomplete"),
    ("docs/step2_dataset_version_review.md", "dataset_version_selection", "active_g1_incomplete"),
    ("docs/visdrone_2019_terms_query.md", "licence_query_draft", "student_reports_sent_reply_pending"),
    ("docs/step2_hands_on_review.md", "student_review_guide", "active"),
    ("docs/requirements_acceptance_overview.md", "acceptance_overview", "active"),
    ("docs/acceptance_matrix.csv", "acceptance_matrix", "active"),
    ("docs/版本管理规范.md", "version_policy", "active"),
    ("docs/文档总览.md", "document_index", "active"),
    ("docs/drafts/开发计划草稿_2026-11-17.txt", "planning_draft", "draft"),
    ("docs/drafts/目录结构草稿_2026-11-17.txt", "layout_draft", "draft"),
]

timestamp = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).isoformat(timespec="seconds")
rows = []
for relative, role, status in FILES:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    blob = path.read_bytes()
    rows.append({
        "snapshot_at": timestamp,
        "path": relative,
        "role": role,
        "status": status,
        "size_bytes": len(blob),
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime, ZoneInfo("Asia/Kuala_Lumpur")).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(blob).hexdigest(),
    })
with OUTPUT.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} entries to {OUTPUT}")
