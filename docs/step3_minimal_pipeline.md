# 第三部分 离线最小技术链路

日期：2026年11月19日。项目版本：0.2.0-alpha.2。按开发计划草稿第三步，已实现并运行图片检测、连续短视频检测与临时ID跟踪，以及可手算核对的评价计算；并新增本机离线测试界面（web/backend/server.py 与 web/frontend/workspace.html），可从浏览器提交媒体并查看真实结果。模型微调属于第四步，尚未开始。19项系统验收未执行。

第二部分技术准备完成。许可版本适用性继续待跟进，不再作为整个毕业项目停工条件；没有据此补造授权或将G1改为已通过。旧的带日期G1记录是历史快照，入口决定见model/data/manifests/step3_entry_decision.json。最终测试候选未用于模型运行或选优。

## 已实现的离线功能

- 一张JPEG/PNG：仅检测car、bus、truck，输出标注图片和结构化记录，track_id始终为空。
- 一个恒定帧率MP4：处理全部解码帧，输出检测、ByteTrack临时ID、连续观测的图像轨迹和H264标注视频。
- JSONL保留空帧和未关联检测；CSV与JSON坐标一致。tracks.json只包含真实观测，不插值补点。
- 每次视频运行新建跟踪器；操作系统锁限制本项目同一运行环境中的离线作业。Windows和Docker依次运行，不同时启动两套运行环境。
- 损坏文件记FAILED，失败产物留在.staging且outputs为空；完成媒体与记录核对后才发布artifacts并记SUCCEEDED。新作业取得锁后，将本项目残留RUNNING记录恢复为INTERRUPTED。重试使用新输出目录。

## 样本和模型

预训练权重来自Ultralytics官方YOLO26l发布，SHA-256为9fe3c544f2b19bebad7ea41e76d7ad3d88b7c2f10d11d24430c5311f6b32db26。这是COCO预训练链路先导，未在VisDrone微调。按模型自带类别名检查COCO编号2/5/7，再映射为本地car/bus/truck编号0/1/2；VisDrone van标签没有合并。

从第二部分未隔离的验证候选中提取一张DET图片，以及MOT-val的uav0000117_02622_v源帧1至48。开发清单记录源ZIP、成员CRC、标注和提取图哈希，见model/data/manifests/step3_development_media.json。所有这些样本只用于开发，不构成独立最终评价。

短片为2720×1530，编码48帧，选定播放速率25 FPS，时长1.92秒。**25 FPS不是已核实的原始采集FPS。** 解码frame_index为0至47，与源帧1至48逐项对应；观测timestamp_ms为0至1880，来自解码PTS减首帧PTS。未推算真实速度、真实时间间隔或地理坐标。

## 本轮运行记录

模型输入imgsz=640、conf=0.25、IoU=0.7、max_det=1000；均是未冻结先导配置。ByteTrack参数见model/configs/offline_pilot.json及每次run.json。此轮未提交低于0.25的检测，所以没有完整试验低分匹配阶段的收益。

| 环境和运行 | 帧数 | 检测记录数 | 作业耗时 秒 | 平均推理 毫秒/帧 | PyTorch峰值已分配 MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Windows image_cpu | 1 | 12 | 4.099 | 3842.110 | 不适用 |
| Windows image_gpu | 1 | 12 | 1.020 | 689.238 | 184.9 |
| Windows video_gpu | 48 | 592 | 6.354 | 16.524 | 281.6 |
| Windows video_gpu_reset | 48 | 592 | 6.157 | 21.970 | 217.2 |
| Windows video_cpu | 48 | 592 | 11.212 | 124.822 | 不适用 |
| Docker image_cpu | 1 | 12 | 6.090 | 5299.363 | 不适用 |
| Docker image_gpu | 1 | 12 | 18.491 | 7453.834 | 184.9 |
| Docker video_cpu | 48 | 592 | 66.761 | 549.949 | 不适用 |
| Docker video_gpu | 48 | 592 | 14.518 | 59.918 | 184.9 |

耗时来自实际run.json，包含该次作业中的模型装载、首次推理、跟踪与媒体导出，排除Python进程启动和最初包导入；会受到预热、后台程序和缓存影响。这不是受控性能比较。峰值为PyTorch allocator数值，不含驱动上下文和其他程序显存。记录数是逐帧检测数量，不是唯一车辆数。

Windows使用Python3.12.14、PyTorch2.10.0+cu128；Docker使用其基础镜像的PyTorch2.13.0+cu130。两者都锁定Ultralytics8.4.215、TrackEval1.3.0。精确依赖分别见model/requirements-inference-windows-lock.txt及model/requirements-inference-docker-lock.txt，Docker基础镜像和构建定义在Dockerfile.offline。跨平台仅核查运行与输出一致性规则，没有宣称逐位相同或性能等价。

## 评价核查

24项组件测试通过，包括ID0、完美匹配、ID切换、缺帧、错类、重复预测、忽略框并集、空分母、检测索引、空帧跟踪推进、视频重置、作业锁和中断恢复。手算核心例：同一源ID连续4帧，预测前2帧ID7、后2帧ID8且框完全重合，则IDSW=1、MOTA=0.75、IDF1=0.5、HOTA=√0.5；四帧始终ID7时三项比率均为1。

检测调用pycocotools COCOeval，跟踪按类别调用TrackEval的CLEAR、Identity、HOTA。CLEAR/Identity匹配IoU为0.5；HOTA按0.05至0.95共19个阈值取均值，输出比率0至1，MOTA可能为负。无真值类别的AP、HOTA、IDF1和MOTA置空，而误检数仍保留。未关联检测继续参与检测评价，跟踪评价另行披露其数量。

沿用项目本地规则：对category0、category11及score0忽略框的并集，覆盖目标框或预测框面积至少50%时排除。van等非目标有效类不自动变成忽略区域。本地预处理尚未与官方MATLAB评价逐项对照，**不得称为官方VisDrone分数**。

发现TrackEval1.3.0在整帧无预测的手算序列上返回断轨数0，与预期1不一致。Frag字段因此置空，TrackEval_Frag_unverified仅保存原值供排查，留待第五步核验，不作为验收结果。

已运行48帧真实预测评价，记录位于model/experiments/step3_20261119_final/development_metrics.json。该短片只有car真值，bus/truck没有正样本，不能据此评价它们的召回能力。真实预测有漏检、误检和ID切换，先导分数只证明适配器能处理实际输出。conf0.25还截断了低分预测，因此该AP不代替正式低阈值验证，未测得模型总体准确率。

## 在本机复现

在UAV_Video_Tracking目录运行；已建立model/.venv，无须激活环境。

```powershell
& model/.venv/Scripts/python.exe model/scripts/run_offline.py model/data/processed/step3_pilot/image.jpg --weights model/weights/yolo26l.pt --output model/experiments/my_image_001 --device 0
& model/.venv/Scripts/python.exe model/scripts/run_offline.py model/data/processed/step3_pilot/clip.mp4 --weights model/weights/yolo26l.pt --output model/experiments/my_video_001 --device 0
& model/.venv/Scripts/python.exe model/scripts/evaluate_offline.py --reference model/data/processed/step3_pilot/reference.json --predictions model/experiments/my_video_001/artifacts/frames.jsonl --output model/experiments/my_video_001/metrics.json
& model/.venv/Scripts/python.exe -m unittest discover -s model/tests -v
```

将--device 0改为--device cpu可运行CPU。输出目录必须不存在；同名目录不覆盖。输入只接受本地JPEG/PNG或CFR MP4；变帧率、非单调PTS及H264不支持的奇数尺寸明确报错，音轨在标注视频中省略。更广的文件格式、输入上限和网页浏览器兼容性仍留到部署先导验证。

重新建Windows环境时使用Python3.12：先python -m venv model/.venv，再在该环境执行pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128，最后pip install -r model/requirements-inference-windows-lock.txt。FFmpeg/ffprobe需在PATH；本机已使用已安装版本。Docker内安装了所需视频工具。

## Docker复现

```powershell
docker build -f Dockerfile.offline -t uav-offline:step3 .
docker run --rm --gpus all --mount "type=bind,source=$PWD/model/data/processed/step3_pilot,target=/input,readonly" --mount "type=bind,source=$PWD/model/weights,target=/weights,readonly" --mount "type=bind,source=$PWD/model/experiments,target=/workspace/model/experiments" uav-offline:step3 /input/clip.mp4 --weights /weights/yolo26l.pt --output /workspace/model/experiments/my_docker_video_001 --device 0
```

CPU运行去掉--gpus all，并使用--device cpu。Windows和容器顺序启动。实际容器命令、镜像ID、版本与结果在.qa/step3_docker_verification.json。容器无须联网处理媒体；下载依赖和权重发生在准备阶段。

## 查看输出

首先打开model/experiments/step3_20261119_final/image_gpu/artifacts/annotated.jpg和video_gpu/artifacts/annotated.mp4。对应frames.jsonl逐帧记录所有检测，detections.csv便于表格查看，tracks.json记录临时轨迹观测。视频首、中、末帧已目视抽查，输出可打开；这不表示每个框或ID均正确。

可自己核对：视频第0帧为0毫秒，第23帧为920毫秒，第47帧为1880毫秒；在JSONL查相同frame_index，比较框与ID。换视频后ID可以重新从1开始，不能用来确认真实身份。原始源标注未修复，数据及权重保持本地。

第三步最小离线链路已运行并留下证据；没有据此宣称G1正式通过、官方评价等价或19项系统验收完成。第四步再比较模型大小与分辨率、建立正式基线并微调；第五步比较跟踪器和处理断轨评价；第七步才接入网页。

实现参考：[Ultralytics YOLO26](https://docs.ultralytics.com/models/yolo26/)、[跟踪说明](https://docs.ultralytics.com/modes/track/)、[TrackEval](https://github.com/JonathonLuiten/TrackEval)。实际接口以固定版本源码和本轮测试为准。
