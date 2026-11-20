# 第二部分 DET 忽略区域规则先导验证

日期：2026年11月18日。**本页是car、bus、truck三类本地评价规则的先导试验，不是模型评价结果，也不能称为官方VisDrone分数。** 来源为独立划分候选中的DET-val图像；最终清单尚未冻结，G1未通过。

## 官方依据与本地规则

[VisDrone2019 DET工具箱说明](https://github.com/VisDrone/VisDrone2018-DET-toolkit)规定category 0为忽略区域、category 11为“others”，并称相关检测不参与评价。其[忽略区域MATLAB函数](https://github.com/VisDrone/VisDrone2018-DET-toolkit/blob/master/utils/dropObjectsInIgr.m)对category 0建立像素掩码，覆盖目标/检测框面积达到50%时排除；[匹配函数](https://github.com/VisDrone/VisDrone2018-DET-toolkit/blob/master/utils/evalRes.m)对普通真值优先匹配、对忽略真值采用检测框覆盖比例。公开代码中category 11没有与category 0相同的显式掩码步骤，说明文字与实现存在需要复核的差异。

本项目本地规则v1：[配置](../model/configs/det_ignore_policy.json)和[实现](../model/src/visdrone_det_ignore.py)把category 0、category 11及score=0源框视作忽略框；当它们的**并集**覆盖目标或预测框至少50%时，该框不参与三类评价。正常标注的van等其他类别不合并成car，也不自动当作忽略框。框采用图像范围内的半开像素坐标；越界框报错并由来源隔离处理。此规则是课程项目的明确选择，不能在未经MATLAB对照前宣称官方分数等价。

训练先导方案仍采用不含忽略记录的DET训练图像，以避免普通YOLO标签把未知区域误当背景；目前有3050张候选、其中bus框2271个。这只是规模检查，不是训练结果，也不是冻结的训练政策。验证候选可以保留有忽略框的图像并在评价前按本地规则过滤。

## 验证候选试跑

按来源隔离后，DET-val有407张候选图。以原始标注作为输入、不生成模型预测，规则过滤前后如下：

| 项目 | 数量 |
| --- | ---: |
| 含忽略框图像 | 260 |
| 忽略框 | 969 |
| 原始三类目标框 | 10,742 |
| 被忽略区域覆盖而排除的目标框 | 22 |
| 保留car框 | 10,027 |
| 保留bus框 | 126 |
| 保留truck框 | 567 |

整图排除方案只剩147张验证候选、13个bus框，因此本地规则在保留类别覆盖方面更合适。数值出自[试跑清单](../model/data/manifests/DET-val_ignore_policy_pilot.json)；单元测试总计12项，其中[新增5项](../model/tests/test_visdrone_det_ignore.py)覆盖并集、不重复计数、恰好50%、“others”与van区分、越界拒绝等情形。

## 下一步验证

1. 用实际模型输出验证预测框过滤和三类匹配，再与官方MATLAB工具箱的相同输入比较；MATLAB/Octave当前不可用，因此官方等价性未证明。
2. 固定训练图像排除或损失掩码政策，记录验证集bus框数量对指标稳定性的影响。
3. 在2019数据用途条款和来源清单核准后，冻结最终测试清单；正式测试不参与选优。
