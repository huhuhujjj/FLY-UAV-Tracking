# 本地 Web 界面

当前版本 0.2.0-alpha.3。`frontend/` 为原生 HTML/CSS/JavaScript，`backend/` 为 Python 本地 HTTP 服务；前端通过同源 API 调用现有离线流水线。

从项目根目录执行 `model/.venv/Scripts/python.exe web/backend/run.py`，打开 http://127.0.0.1:8765/。功能页依赖后端，不能通过双击 HTML 完成处理。

| 页面 | 状态 |
| --- | --- |
| `workspace.html` | 图片/视频入口与服务状态 |
| `image-detection.html` | 单张图片检测、结果与下载 |
| `index.html` | 录制视频检测及视频内跟踪、播放与下载 |
| `task-history.html` | 占位页面，未接数据 |
| `evaluation.html` | 占位页面，未接评估结果 |

取消只在 worker 返回后停止发布结果，不立即中断推理。刷新可从仍在运行的服务恢复最近任务，服务重启后任务列表丢失。输入暂限 JPEG/PNG/MP4、256 MiB；参数未冻结，十九项正式系统验收尚未执行。

环境搭建见 [项目说明](../README.md)，接口与测试见 [后端说明](backend/README.md)。
