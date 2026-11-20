# 第二部分数据版本选型复核

日期：2026年11月18日。此页回应“为什么不用最近且完整的数据”。**VisDrone2019是当前已获取并审计的基线，不代表它最新，也不代表2019许可适用性已确认。** 本项目同时需要静态图片的car/bus/truck检测标注、带跨帧目标ID的视频跟踪标注，以及可审计的训练、验证、最终测试划分。

| 官方来源 | 已核对到的任务与数据 | 对本项目的影响 |
| --- | --- | --- |
| [VisDrone官方公开仓库](https://github.com/VisDrone/VisDrone-Dataset) | 提供DET图片和MOT视频各自的train、val、test-dev下载及工具箱；本机六套2019归档已完整获取并核验。 | 同时覆盖图片检测和视频内跟踪，便于追溯来源与标注。 |
| [VisDrone2021挑战页](https://aiskyeye.com/challenge_2021/)及[DET挑战论文](https://homes.esat.kuleuven.be/~konijn/publications/2021/Cao2.pdf) | 核心任务包含图片目标检测、多目标跟踪和人群计数；DET论文说明检测数据沿用前几届。 | 年份较新且含跟踪任务，但不能仅凭任务名称证明有适合本项目静态图片的完整可下载DET/MOT新版本。官方仓库的[2021下载链接询问](https://github.com/VisDrone/VisDrone-Dataset/issues/53)截至本次核验仍未得到发布方回复。 |
| [VisDrone2022挑战页](https://aiskyeye.com/challenge-2022/) | 核心任务为目标检测和人群计数，另列FusionPortable视觉SLAM；[计数任务页](https://aiskyeye.com/challenge-2022/crowd-counting/)说明使用成对可见光/热成像图像。 | 2022任务变化不等于发布了可替代现有MOT的视频ID标注；检测图片的逐文件变化仍须实际包核对。另一个`challenge_2022`旧网址正文误写2021，不作为2022任务依据。 |
| [VisDrone2023挑战页](https://aiskyeye.com/challenge-2023/)与[2024介绍](https://aiskyeye.com/home/) | 核心任务转为目标检测与零样本目标检测；2024页面未列多目标跟踪为核心任务。 | 单用新年份挑战数据不能直接替代已有MOT跨帧ID评价。 |
| [VisDrone2024下载页](https://aiskyeye.com/download/) | 明确写明目标检测数据与VisDrone2019相同。 | 把2019 DET改称2024不会自动带来更新的检测图像。 |
| [2025 DMTrack论文](https://arxiv.org/abs/2510.17860) | 提出应对UAV非线性运动、遮挡和身份切换的跟踪方法，实验继续使用VisDrone-MOT等既有基准。 | 属于方法进展，并非VisDrone2025新数据包。 |
| [2026 DynUAV论文](https://openaccess.thecvf.com/content/CVPR2026/papers/Ye_Breaking_Smooth-Motion_Assumptions_A_UAV_Benchmark_for_Multi-Object_Tracking_in_CVPR_2026_paper.pdf)与[作者仓库](https://github.com/kxzhang-lab/DynUAV) | 独立团队发布42段视频、37,893帧的动态无人机MOT基准和数据下载入口，重点是强相机运动、视角及尺度变化。 | 值得作为较新MOT候选；与2025 DMTrack不是同一项目的连续版本。尚未获取并审计实际归档、类别映射和数据许可，不替换当前基线。 |

**当前决定：**保留已验证的VisDrone2019 DET/MOT作为课程原型的基准候选，暂不把年份换成“2024”或把未核实来源的数据直接混入。依据是任务覆盖、可获取性与已完成的完整性审计，并非认为旧数据一定优于新数据。2019数据可能不反映最新场景和设备，这是外部有效性限制；后续若要验证新场景，应另选有明确许可、car/bus/truck类别和视频ID的较新数据，单列外部鲁棒性测试，不与正式基准样本混用。

**较新候选补充：**DynUAV已提供公开下载入口，因此“2025—2026没有新进展”不成立；它是另一套基准，不是VisDrone2019的年度升级。其仓库明确给出的是代码MIT许可，不能由此推断数据同样采用MIT。若纳入本项目，先核对数据条款、完整性、逐帧ID、类别映射及场景差异，再决定用于主要基准还是单列外部测试；当前不宣称已下载或验证。

**重新选型条件：**若发布团队给出2021或更新的、完整可下载的静态DET及MOT标注与版本条款，先做文件哈希、类别/ID、忽略区域、同源与许可审计，再决定是否迁移。迁移会使现有划分与部分先导统计失效，须同步proposal、SRS、项目指南、README和验收记录。当前G1仍未通过，最终测试集未冻结。
