# 2026-11-17 首轮需求验收总览

- 目的：将已固定的六组首轮需求汇总为一张可阅读的验收表，并指向现有 19 项详细用例。
- 变更：新增 `docs/requirements_acceptance_overview.md`；补充 `logs/experiment_template.json` 的数据、模型、跟踪器、评价器及配置版本字段；更新文档入口与清单脚本。
- 依据：现有 SRS 1.2、`docs/step1_scope_and_acceptance.md`、`model/configs/classes.json`、`model/configs/project_scope.json` 和 `docs/acceptance_matrix.csv`。没有改变功能范围。
- 状态：全部功能验收 `NOT_EXECUTED`；模型阈值及性能目标 `PENDING_PILOT`。此项只完成文档定义与结构检查，不涉及下载数据或推理。
- 检查：运行 `python model/scripts/validate_step1.py` 返回定义一致性 PASS，覆盖 19 个验收行和 44 个需求编号；类别为 car/bus/truck，van 排除策略存在；全部目标阈值为 null。需求总览的本地链接无失效，发布清单 50 个文件哈希均匹配。
