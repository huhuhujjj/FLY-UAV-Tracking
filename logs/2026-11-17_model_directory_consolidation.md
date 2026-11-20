# 2026-11-17 模型目录集中整理

- 目的：按用户确认的目录方案，消除项目根目录与 `model/` 下重复的 `configs/`、`data/`、`scripts/`、`tests/`。
- 变更：原四个根目录内容已迁入 `model/`；相关配置路径、脚本根目录定位、README、文档索引和报告正文路径已同步。编辑正式 DOCX 前已备份到 `backups/20261117_model_consolidation/`。
- 验证命令：`python model/scripts/validate_step1.py`、`python model/scripts/update_document_manifest.py`、`python model/scripts/update_release_manifest.py`。
- 实际结果：定义一致性检查 PASS，覆盖 19 项验收行和 44 个需求编号；系统验收仍为 `NOT_EXECUTED`。文档清单 15 项、发布快照 47 项重新生成。
- 限制：目录迁移不表示 YOLO 数据、权重、训练、推理、跟踪或网页后端已实现。旧开发日志保留当时执行路径，不作为当前运行命令。
