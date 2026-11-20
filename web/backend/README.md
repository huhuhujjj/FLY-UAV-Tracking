# Backend 工作区

本目录提供本机单用户离线测试的本地 API 与后台处理。服务调用 [`../../model/src/pipeline.py`](../../model/src/pipeline.py) 完成图片检测与视频检测+跟踪，不在此复制模型训练代码或权重。

## 启动

在 `UAV_Video_Tracking` 目录运行：

```powershell
& model/.venv/Scripts/python.exe web/backend/run.py
```

- 服务绑定 `127.0.0.1:8765`，仅本机可访问；可用环境变量 `UAV_PORT` 改端口。
- 运行任务产物写入 `web/backend/jobs/<job_id>/run/`，上传的原始媒体不保留（处理完成后删除）。
- 停止：在终端按 Ctrl+C。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 服务健康与是否有非终态任务 |
| GET | `/api/jobs` | 列出所有任务状态 |
| GET | `/api/jobs/<id>` | 查询单个任务状态 |
| GET | `/api/jobs/<id>/detections` | 读取该任务的检测记录（来自 detections.csv，最多 500 条） |
| POST | `/api/jobs` | 上传媒体（multipart `file`），创建任务 |
| DELETE | `/api/jobs/<id>` | 请求取消非终态任务 |
| GET | `/api/artifacts/<id>/<name>` | 下载任务产物（仅成功任务） |

任务状态：`WAITING`、`RUNNING`、`SUCCEEDED`、`FAILED`、`INTERRUPTED`。同时最多一个非终态任务，重复提交返回 HTTP 409（`{"error":"busy"}`）。结果只发布真实流水线产物（`annotated.jpg` / `annotated.mp4` / `frames.jsonl` / `detections.csv` / `tracks.json` / `run.json`），不提供任意服务器路径读取。

取消说明：`DELETE /api/jobs/<id>` 请求取消后，任务状态保持非终态，待后台 worker 释放离线流水线的独占文件锁后才转为 `INTERRUPTED`；在收尾期间仍占用单任务槽（新提交返回 409），避免并发锁冲突。

输入限制（试运行范围，非冻结）：仅 JPEG/PNG 图片或 MP4 视频；图片只做检测，视频做检测与视频内临时跟踪。上传大小上限为 256 MiB（测试用保护值，非正式上限）。参数沿用 `model/configs/offline_pilot.json` 试运行值。

## 测试

后端/API 测试覆盖图片、视频、损坏文件、状态、并发单任务限制、下载、失败、路径穿越防护、未知任务、检测记录接口与取消：

```powershell
& model/.venv/Scripts/python.exe -m unittest web.backend.test_api -v
```

浏览器测试使用 Playwright，并由执行器自动创建隔离服务及临时任务目录。首次安装依赖（在 `web/backend` 下）：

```powershell
npm ci
npx playwright install chromium
```

从项目根目录运行全部六个脚本：

```powershell
model/.venv/Scripts/python.exe web/backend/run_e2e.py
```

结果保存在 `.qa/e2e/`，包含每个脚本的输出、退出码与汇总 JSON。可用 `--node` 指定 Node.js 可执行文件。手动运行单个 `node e2e_*.js` 时需自行启动服务；`UAV_BASE` 可覆盖服务地址。图片/视频功能测试访问各自的功能页，工作台只承担入口导航。

## 实现状态

本服务是本地离线测试界面，覆盖上传、单任务准入、任务状态、图片检测、视频检测+跟踪、结果下载的最小闭环；未实现筛选、摘要、训练或评估，也不是正式系统验收。19 项系统验收未执行，参数为试运行值。

运行日志预留在 [`logs/`](logs/README.md)；项目开发和验收记录保存在 [`../../logs/`](../../logs/README.md)。
