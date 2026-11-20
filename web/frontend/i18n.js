/* Internationalisation dictionary + runtime for the local test workbench.
   Provides zh (Simplified Chinese) and en (English). Language is persisted in
   localStorage and defaults to the browser locale. */
(function (window) {
  "use strict";

  var I18N = {
    zh: {
      // Chrome / navigation
      "nav.workspace": "工作台",
      "nav.image": "图片检测",
      "nav.video": "视频跟踪",
      "nav.history": "任务历史",
      "nav.evaluation": "评估记录",
      "nav.section": "工作区",
      "nav.main": "主要页面",
      "nav.aria": "项目导航",
      "project.name": "无人机车辆分析",
      "project.local": "本地单用户项目",
      "project.state.title": "原型展示状态",
      "workspace.local": "本机工作区",
      "workspace.offline": "离线测试已接入",
      "breadcrumb.root": "无人机车辆分析",
      "breadcrumb.workspace": "工作台",
      "avatar.aria": "本机用户",
      "lang.zh": "中文",
      "lang.en": "English",
      "lang.switch.aria": "切换语言",

      // Service pill
      "service.offline": "本地服务未连接",
      "service.busy": "本地服务 · 处理中",
      "service.ready": "本地服务 · 就绪",

      // Page heading
      "heading.title": "影像分析工作台",
      "heading.lede": "选择影像类型，提交一张图片或一段录制视频，查看本机离线处理后的真实结果。",
      "heading.chip": "本地单用户 · 离线测试",

      // Notice
      "notice.strong": "本机离线测试界面。",
      "notice.body": "仅限 127.0.0.1 访问；图片只做检测，录制视频做检测与视频内临时跟踪。结果显示的是本次真实运行产物，不含示意值。",

      // Media picker
      "picker.aria": "选择媒体类型",
      "picker.image.title": "图片检测",
      "picker.image.desc": "单张 JPEG/PNG · 仅检测框 · 类别与置信度 · 不分配跟踪 ID",
      "picker.video.title": "视频跟踪",
      "picker.video.desc": "恒定帧率 MP4 · 逐帧检测 · 视频内临时 ID · 图像平面轨迹",

      // Upload strip
      "upload.aria": "选择并提交媒体",
      "upload.title": "拖拽或选择待处理媒体",
      "upload.desc": "将 JPEG/PNG 图片或 MP4 录制视频拖入此处，或点击右侧「选择文件」；单文件上限 256 MB，一次只处理一个非终态任务。",
      "upload.choose": "选择文件",
      "upload.submit": "运行处理",
      "upload.cancel": "取消",
      "upload.reset": "清空",
      "upload.state.processing": "处理中",
      "upload.state.submitting": "提交中",
      "upload.state.ready": "可运行",
      "upload.state.notready": "未就绪",

      // Empty state
      "empty.aria": "空状态",
      "empty.eyebrow": "处理结果",
      "empty.title": "这里暂时还没有任务",
      "empty.body": "选择媒体类型并提交文件后，本页会显示等待、处理中、成功或失败状态，并在完成后展示本次运行的真实标注媒体、检测记录与下载入口。",

      // Result region
      "result.aria": "处理结果",
      "result.inspector.aria": "检测结果详情",
      "note.aria": "结果说明",
      "note.strong": "结果说明：",
      "note.body": "跟踪 ID 仅在当前视频内临时有效，不表示真实身份；轨迹是图像平面观测。参数采用现有试运行配置（conf 0.25 等），属于未冻结先导值，不代表正式标准或系统性能承诺。",
      "footer.left": "CAT405 · 无人机视频目标检测与多目标跟踪",
      "footer.right": "本地单用户方案 · 离线测试阶段",

      // Status messages
      "status.waiting": "任务已排队，等待本地处理…",
      "status.running": "正在处理媒体，请稍候…",
      "status.success": "处理完成。以下为该次运行的真实产物。",
      "status.interrupted": "任务已取消。可重新选择媒体再次运行。",
      "status.failed.prefix": "处理失败：",
      "status.pending": "等待处理结果…",
      "status.canceling": "正在取消任务，后台收尾中…",
      "status.submitting": "正在提交媒体…",

      // Result contents
      "result.error.none": "本次运行未产生可用产物。失败详情见上方提示。",
      "result.error.noresults": "没有可显示的检测结果。",
      "result.image.alt": "该次运行生成的标注图片",
      "result.image.caption": "标注图片 · annotated.jpg",
      "result.image.eyebrow": "单张图片",
      "result.image.heading": "检测结果",
      "result.video.caption": "标注视频 · annotated.mp4（轨迹 ID 仅在本视频内临时有效）",
      "result.video.eyebrow": "录制视频",
      "result.video.heading": "逐帧检测与跟踪",
      "result.runinfo": "运行信息",
      "result.realrecord": "真实记录",
      "result.meta.resolution": "分辨率",
      "result.meta.fps": "播放速率",
      "result.meta.fps.note": " FPS（未核实采集 FPS）",
      "result.meta.frames": "帧数",
      "result.meta.frames.unit": " 帧",
      "result.meta.detections": "检测记录",
      "result.meta.detections.unit": " 条（逐帧检测数，非唯一车辆数）",
      "result.identity.note": "跟踪 ID 仅在当前视频内临时有效，不表示车辆真实身份；轨迹是图像平面观测，缺帧不插值。",

      // Detection table
      "detection.title": "检测记录",
      "detection.source": "从 detections.csv 读取",
      "detection.col.frame": "帧",
      "detection.col.ts": "时间戳",
      "detection.col.class": "类别",
      "detection.col.conf": "置信度",
      "detection.col.track": "临时ID",
      "detection.col.coord": "坐标(x1,y1)",
      "detection.loading": "正在读取检测记录…",
      "detection.empty": "无检测记录。",
      "detection.unavailable": "检测记录不可用。",
      "detection.total.full": "共 {total} 条",
      "detection.total.truncated": "共 {total} 条，仅显示前 {shown} 条",
      "detection.none": "—",

      // Downloads
      "download.title": "下载",
      "download.empty": "本次运行未产生可下载产物。",

      // Errors / validation
      "error.too_large": "文件超过 256 MB 上传上限，请更换文件。",
      "error.unsupported_type": "仅支持 JPEG/PNG 图片或 MP4 视频。",
      "error.busy": "已有任务在处理中，请等待完成后再提交。",
      "error.bad_request": "提交内容无效，请重新选择文件。",
      "error.unknown": "未知错误",
      "error.pipeline": "处理未成功。可能原因：文件损坏、格式异常，或无法解析的媒体。",
      "error.drop_unsupported": "不支持的文件类型。请拖入 JPEG/PNG 图片或 MP4 视频。",
      "error.type_mismatch": "所选文件与「{mode}」类型不符，请切换模式或更换文件。",
      "error.type_mismatch_short": "所选文件与当前模式不符，请切换模式或更换文件。",
      "error.connect": "无法连接本地服务：",
      "error.cancel": "无法取消任务：",
      "mode.image": "图片检测",
      "mode.video": "视频跟踪",

      // Hub / index page
      "hub.title": "影像分析工作台",
      "hub.lede": "选择一种影像处理方式，进入对应的功能页面进行本地离线检测或跟踪。",
      "hub.chip": "本地单用户 · 离线测试",
      "hub.image.title": "图片检测",
      "hub.image.desc": "提交单张 JPEG/PNG 影像，查看车辆候选框、类别与置信度。仅检测，不分配跟踪 ID。",
      "hub.image.cta": "进入图片检测",
      "hub.video.title": "视频跟踪",
      "hub.video.desc": "提交恒定帧率 MP4 录制视频，查看逐帧检测与视频内临时 ID 跟踪。",
      "hub.video.cta": "进入视频跟踪",
      "hub.note": "两个入口都调用同一套本地离线流水线；跟踪 ID 仅在当前视频内临时有效，轨迹为图像平面观测。"
    },

    en: {
      // Chrome / navigation
      "nav.workspace": "Workspace",
      "nav.image": "Image Detection",
      "nav.video": "Video Tracking",
      "nav.history": "Task History",
      "nav.evaluation": "Evaluation",
      "nav.section": "Workspace",
      "nav.main": "Main pages",
      "nav.aria": "Project navigation",
      "project.name": "UAV Vehicle Analysis",
      "project.local": "Local single-user project",
      "project.state.title": "Prototype display status",
      "workspace.local": "Local workspace",
      "workspace.offline": "Offline testing connected",
      "breadcrumb.root": "UAV Vehicle Analysis",
      "breadcrumb.workspace": "Workspace",
      "avatar.aria": "Local user",
      "lang.zh": "中文",
      "lang.en": "English",
      "lang.switch.aria": "Switch language",

      // Service pill
      "service.offline": "Local service disconnected",
      "service.busy": "Local service · Processing",
      "service.ready": "Local service · Ready",

      // Page heading
      "heading.title": "Media Analysis Workspace",
      "heading.lede": "Choose a media type, submit an image or a recorded video, and view the real results of the local offline processing.",
      "heading.chip": "Local single-user · Offline test",

      // Notice
      "notice.strong": "Local offline test interface.",
      "notice.body": "Accessible only from 127.0.0.1; images are detected only, recorded videos are detected with within-video temporary tracking. Results show the real artifacts of this run, without mock values.",

      // Media picker
      "picker.aria": "Choose media type",
      "picker.image.title": "Image Detection",
      "picker.image.desc": "Single JPEG/PNG · detection boxes only · class & confidence · no track ID assigned",
      "picker.video.title": "Video Tracking",
      "picker.video.desc": "Constant-rate MP4 · per-frame detection · within-video temporary ID · image-plane tracks",

      // Upload strip
      "upload.aria": "Choose and submit media",
      "upload.title": "Drag or choose media to process",
      "upload.desc": "Drop a JPEG/PNG image or MP4 recorded video here, or click \"Choose file\" on the right; 256 MB per file, one non-terminal task at a time.",
      "upload.choose": "Choose file",
      "upload.submit": "Run",
      "upload.cancel": "Cancel",
      "upload.reset": "Clear",
      "upload.state.processing": "Processing",
      "upload.state.submitting": "Submitting",
      "upload.state.ready": "Ready",
      "upload.state.notready": "Not ready",

      // Empty state
      "empty.aria": "Empty state",
      "empty.eyebrow": "Results",
      "empty.title": "No tasks yet",
      "empty.body": "After choosing a media type and submitting a file, this page shows waiting, processing, success or failure states, then displays the real annotated media, detection records and downloads of this run.",

      // Result region
      "result.aria": "Results",
      "result.inspector.aria": "Detection result details",
      "note.aria": "Result note",
      "note.strong": "Note:",
      "note.body": "Track IDs are only valid within the current video and do not represent real identity; trajectories are image-plane observations. Parameters use the current pilot configuration (conf 0.25 etc.), which are unfrozen pilot values and not a formal standard or a performance commitment.",
      "footer.left": "CAT405 · UAV Video Object Detection and Multi-Object Tracking",
      "footer.right": "Local single-user · Offline test phase",

      // Status messages
      "status.waiting": "Task queued, waiting for local processing…",
      "status.running": "Processing media, please wait…",
      "status.success": "Processing complete. Below are the real artifacts of this run.",
      "status.interrupted": "Task cancelled. You may choose media again and re-run.",
      "status.failed.prefix": "Processing failed: ",
      "status.pending": "Waiting for results…",
      "status.canceling": "Cancelling task, winding down in the background…",
      "status.submitting": "Submitting media…",

      // Result contents
      "result.error.none": "This run produced no usable artifacts. See the message above for details.",
      "result.error.noresults": "No detection results to display.",
      "result.image.alt": "Annotated image generated by this run",
      "result.image.caption": "Annotated image · annotated.jpg",
      "result.image.eyebrow": "Single image",
      "result.image.heading": "Detection Results",
      "result.video.caption": "Annotated video · annotated.mp4 (track IDs valid only within this video)",
      "result.video.eyebrow": "Recorded video",
      "result.video.heading": "Per-frame Detection & Tracking",
      "result.runinfo": "Run information",
      "result.realrecord": "Real record",
      "result.meta.resolution": "Resolution",
      "result.meta.fps": "Playback rate",
      "result.meta.fps.note": " FPS (capture FPS unverified)",
      "result.meta.frames": "Frames",
      "result.meta.frames.unit": " frames",
      "result.meta.detections": "Detections",
      "result.meta.detections.unit": " records (per-frame detections, not unique vehicles)",
      "result.identity.note": "Track IDs are only valid within the current video and do not represent vehicle identity; trajectories are image-plane observations, missing frames are not interpolated.",

      // Detection table
      "detection.title": "Detection Records",
      "detection.source": "from detections.csv",
      "detection.col.frame": "Frame",
      "detection.col.ts": "Timestamp",
      "detection.col.class": "Class",
      "detection.col.conf": "Confidence",
      "detection.col.track": "Temp ID",
      "detection.col.coord": "Coord (x1,y1)",
      "detection.loading": "Loading detection records…",
      "detection.empty": "No detection records.",
      "detection.unavailable": "Detection records unavailable.",
      "detection.total.full": "{total} records",
      "detection.total.truncated": "{total} records, showing first {shown}",
      "detection.none": "—",

      // Downloads
      "download.title": "Download",
      "download.empty": "This run produced no downloadable artifacts.",

      // Errors / validation
      "error.too_large": "File exceeds the 256 MB upload limit. Please choose another file.",
      "error.unsupported_type": "Only JPEG/PNG images or MP4 videos are supported.",
      "error.busy": "A task is already processing. Please wait for it to finish.",
      "error.bad_request": "Invalid submission. Please choose a file again.",
      "error.unknown": "Unknown error",
      "error.pipeline": "Processing did not succeed. Possible causes: corrupted file, malformed format, or unparseable media.",
      "error.drop_unsupported": "Unsupported file type. Drop a JPEG/PNG image or MP4 video.",
      "error.type_mismatch": "The selected file does not match the \"{mode}\" mode. Switch mode or choose another file.",
      "error.type_mismatch_short": "The selected file does not match the current mode. Switch mode or choose another file.",
      "error.connect": "Cannot connect to the local service: ",
      "error.cancel": "Cannot cancel the task: ",
      "mode.image": "Image Detection",
      "mode.video": "Video Tracking",

      // Hub / index page
      "hub.title": "Media Analysis Workspace",
      "hub.lede": "Choose a media processing mode to enter its dedicated page for local offline detection or tracking.",
      "hub.chip": "Local single-user · Offline test",
      "hub.image.title": "Image Detection",
      "hub.image.desc": "Submit a single JPEG/PNG image to view vehicle candidate boxes, class and confidence. Detection only; no track IDs assigned.",
      "hub.image.cta": "Open Image Detection",
      "hub.video.title": "Video Tracking",
      "hub.video.desc": "Submit a constant-rate MP4 recorded video to view per-frame detection and within-video temporary ID tracking.",
      "hub.video.cta": "Open Video Tracking",
      "hub.note": "Both entries call the same local offline pipeline; track IDs are valid only within the current video, and trajectories are image-plane observations."
    }
  };

  var STORAGE_KEY = "uav_workspace_lang";
  var current = "zh";

  function detectDefault() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "zh" || saved === "en") return saved;
    } catch (e) { /* ignore */ }
    var nav = (window.navigator.language || "zh").toLowerCase();
    return nav.indexOf("zh") === 0 ? "zh" : "en";
  }

  function t(key, params) {
    var dict = I18N[current] || I18N.zh;
    var str = dict[key] !== undefined ? dict[key] : (I18N.zh[key] || key);
    if (params) {
      Object.keys(params).forEach(function (k) {
        str = str.replace("{" + k + "}", params[k]);
      });
    }
    return str;
  }

  function setLang(lang) {
    if (lang !== "zh" && lang !== "en") lang = "zh";
    current = lang;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* ignore */ }
    document.documentElement.setAttribute("lang", lang === "zh" ? "zh-Hans" : "en");
    applyI18n();
  }

  function getLang() { return current; }

  // Apply data-i18n text / data-i18n-attr translations across the document.
  function applyI18n() {
    // data-i18n="key" -> textContent
    var nodes = document.querySelectorAll("[data-i18n]");
    Array.prototype.forEach.call(nodes, function (node) {
      var key = node.getAttribute("data-i18n");
      node.textContent = t(key);
    });
    // data-i18n-attr="key:attr" -> set attribute (e.g. title/aria-label)
    var attrNodes = document.querySelectorAll("[data-i18n-attr]");
    Array.prototype.forEach.call(attrNodes, function (node) {
      var spec = node.getAttribute("data-i18n-attr");
      var idx = spec.indexOf(":");
      var key = idx >= 0 ? spec.slice(0, idx) : spec;
      var attr = idx >= 0 ? spec.slice(idx + 1) : "title";
      node.setAttribute(attr, t(key));
    });
    // Update the language toggle label.
    updateLangToggle();
  }

  function updateLangToggle() {
    var toggle = document.getElementById("lang-toggle");
    if (toggle) {
      toggle.textContent = current === "zh" ? "English" : "中文";
      toggle.title = current === "zh" ? "Switch to English" : "切换为中文";
      toggle.setAttribute("aria-label",
        current === "zh" ? "Switch language to English" : "切换语言为中文");
    }
  }

  window.I18N = {
    t: t,
    setLang: setLang,
    getLang: getLang,
    apply: applyI18n,
    init: function () {
      current = detectDefault();
      document.documentElement.setAttribute("lang", current === "zh" ? "zh-Hans" : "en");
      applyI18n();
    }
  };
})(window);
