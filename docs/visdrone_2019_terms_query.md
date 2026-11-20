# VisDrone2019 数据用途条款核验草稿

状态：**学生于2026年11月18日报告已发送询问，待发布团队回复。** 本文件保存的是拟发送草稿，尚未取得实际发件记录或邮件原文，因此不把下文视作已发送内容的逐字副本，也不是授权证明。本地学术课程项目的数据审计继续保持原始压缩包与派生标签仅在本机使用，不公开或再分发。

## 已核对依据

- [VisDrone官方数据保护页](https://aiskyeye.com/data-protection/)写明学术用途及CC BY-NC-SA 3.0，但版权正文明确称VisDrone2021，不能直接当作2019 DET/MOT两类压缩包的完整版本证明。
- [官方下载页](https://aiskyeye.com/download/)说明新版DET数据与VisDrone2019相同；没有同样明确覆盖本地2019 MOT压缩包的许可句子。
- [官方DET工具箱说明](https://github.com/VisDrone/VisDrone2018-DET-toolkit)提供联系邮箱`tju.drone.vision@gmail.com`；它是工具箱说明中的联系渠道，不能代替数据授权条款。
- 本机六套VisDrone2019 DET/MOT完整ZIP的成员名中未发现LICENSE、LICENCE、COPYRIGHT或README文件。

## 询问邮件草稿（实际发件正文尚未核对）

**To:** tju.drone.vision@gmail.com
**Subject:** Clarification of permitted academic use for VisDrone2019 DET and MOT archives

Dear VisDrone team,

I am using the official VisDrone2019 DET and MOT train, validation, and test-dev archives for a local, non-commercial university course project on car, bus, and truck detection and within-video tracking. The raw archives and derived annotations remain on my computer and will not be redistributed.

Your data-protection page mentions academic use and CC BY-NC-SA 3.0, but its copyright section names VisDrone2021. Could you please confirm whether those terms also apply to the VisDrone2019 DET and MOT archives, including locally derived labels, evaluation tables, and a model trained on the permitted training split? If different terms apply, please point me to the version-specific terms. Could you also confirm the appropriate attribution for a course report and whether representative dataset screenshots may be included in a non-commercial submitted report?

My project needs both still-image detection annotations and video multi-object-tracking IDs. If there is a newer complete official DET and MOT release with version-specific terms, could you point me to its download links and explain whether its DET images or MOT sequences differ from VisDrone2019? I would prefer to audit and use the newer release if it covers both tasks.

Thank you for your guidance.

Best regards,
ZHANG XIAOHUI

## 收到回复后的记录步骤

1. 保留邮件原文、日期、发件人及明确涉及的数据版本；不要只摘一句许可名称。
2. 在`model/data/sources/licence_review.md`记录条款、归属与允许的输出物范围，报告引用发布团队回复；邮件中若有私人信息，公开文档只存必要摘要。
3. 若发布团队未回复，继续标为“版本适用性未确认”，不把2021页面或第三方镜像条款推断为2019授权。
