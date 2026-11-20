/* Local offline test workbench controller. Talks to the backend JSON API on the
   same origin. Only shows real pipeline artifacts; no mock values.

   APP_MODE (set on window before this script runs, or inferred from body):
   - "image": single-type page for image detection only.
   - "video": single-type page for video tracking only.
   - "hub" (default): multi-type workbench with a media type picker. */
(function () {
  "use strict";

  // Localised string helper (provided by i18n.js).
  function t(key, params) {
    return (window.I18N && window.I18N.t) ? window.I18N.t(key, params) : key;
  }

  var APP_MODE = window.APP_MODE || "hub";

  var API = {
    health: "/api/health",
    jobs: "/api/jobs",
  };

  var MAX_UPLOAD_BYTES = 256 * 1024 * 1024; // matches server-side guard

  var state = {
    mediaType: null, // "image" | "video"
    fileName: null,
    file: null,
    currentJob: null, // latest job status payload
    polling: null,
    pollTimer: null,
    submitting: false,
  };

  function $(sel) { return document.querySelector(sel); }
  function $all(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function fmtBytes(n) {
    if (n == null || isNaN(n)) return "";
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / 1024 / 1024).toFixed(1) + " MB";
  }

  function friendlyError(body) {
    var msg = (body && body.message) || (body && body.error) || t("error.unknown");
    var err = body && body.error;
    if (err === "too_large") return t("error.too_large");
    if (err === "unsupported_type") return t("error.unsupported_type");
    if (err === "busy") return t("error.busy");
    if (err === "bad_request") return t("error.bad_request");
    // Show a translated error instead of a backend traceback.
    if (/RuntimeError|ValueError|Exception|Error:|Traceback/.test(msg)) {
      return t("error.pipeline");
    }
    return msg;
  }

  function apiGet(path) {
    return fetch(path, { cache: "no-store" }).then(function (r) {
      return r.json().then(function (body) { return { status: r.status, body: body }; });
    });
  }

  function apiDelete(path) {
    return fetch(path, { method: "DELETE", cache: "no-store" }).then(function (r) {
      return r.json().then(function (body) { return { status: r.status, body: body }; });
    });
  }

  function apiPostJob(formData) {
    return fetch(API.jobs, { method: "POST", body: formData }).then(function (r) {
      return r.json().then(function (body) { return { status: r.status, body: body }; });
    });
  }

  function isTerminal(status) {
    return status === "SUCCEEDED" || status === "FAILED" || status === "INTERRUPTED";
  }

  // Functional pages share this controller; workspace.html provides navigation.

  function setServicePill(health) {
    var pill = $("#service-pill");
    if (!pill) return;
    if (!health || !health.ok) {
      pill.classList.add("is-off");
      pill.querySelector(".service-label").textContent = t("service.offline");
    } else if (health.active_nonterminal_job) {
      pill.classList.add("is-busy");
      pill.querySelector(".service-label").textContent = t("service.busy");
    } else {
      pill.querySelector(".service-label").textContent = t("service.ready");
    }
  }

  function renderMediaPicker() {
    var picker = $("#media-picker");
    if (!picker) return;

    // Single-type pages have no picker: the media type is fixed and the picker
    // is hidden entirely (or reduced to a single locked card).
    if (APP_MODE === "image" || APP_MODE === "video") {
      if (state.mediaType !== APP_MODE) state.mediaType = APP_MODE;
      picker.classList.add("is-single");
      var single = $(".picker-card[data-type=\"" + APP_MODE + "\"]", picker);
      $all(".picker-card", picker).forEach(function (card) {
        if (card.getAttribute("data-type") !== APP_MODE) card.style.display = "none";
      });
      if (single) single.classList.add("is-selected");
      return;
    }

    // Hub mode: interactive picker.
    picker.classList.remove("is-single");
    $all(".picker-card", picker).forEach(function (card) {
      card.style.display = "";
      var type = card.getAttribute("data-type");
      card.classList.toggle("is-selected", state.mediaType === type);
      card.onclick = function () {
        if (state.currentJob && !isTerminal(state.currentJob.status)) {
          // Don't allow switching mode mid-run.
          return;
        }
        state.mediaType = type;
        state.fileName = null;
        state.file = null;
        $("#file-input").value = "";
        $("#chosen-file").classList.add("hidden");
        renderMediaPicker();
        renderUploadArea();
      };
    });
  }

  function renderUploadArea() {
    var strip = $("#job-strip");
    if (!strip) return;
    var ready = !!state.mediaType && !!state.fileName;
    var submit = $("#submit-btn");
    var cancelBtn = $("#cancel-btn");
    var busy = state.currentJob && !isTerminal(state.currentJob.status);
    var terminal = state.currentJob && isTerminal(state.currentJob.status);

    submit.disabled = busy || !ready || state.submitting;
    submit.querySelector("small").textContent =
      busy ? t("upload.state.processing")
        : (state.submitting ? t("upload.state.submitting")
          : (ready ? t("upload.state.ready") : t("upload.state.notready")));

    // Cancel button only shows while a job is non-terminal.
    if (cancelBtn) {
      if (busy) {
        cancelBtn.classList.remove("hidden");
        cancelBtn.disabled = false;
      } else {
        cancelBtn.classList.add("hidden");
      }
    }

    // Lock the picker + file input while busy to prevent mid-run changes.
    var picker = $("#media-picker");
    if (picker) picker.classList.toggle("is-locked", busy);
    var fileLabel = $(".file-input-label");
    if (fileLabel) {
      if (busy) fileLabel.setAttribute("aria-disabled", "true");
      else fileLabel.removeAttribute("aria-disabled");
    }

    // Reset button visibility: show "清空" only after a terminal job exists.
    var resetBtn = $("#reset-btn");
    if (resetBtn) {
      if (terminal) resetBtn.classList.remove("hidden");
      else resetBtn.classList.add("hidden");
    }
  }

  function resetWorkbench() {
    // Clear the current selection and result, returning to the empty state.
    state.currentJob = null;
    state.mediaType = null;
    state.fileName = null;
    state.file = null;
    state.submitting = false;
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
    var input = $("#file-input");
    if (input) input.value = "";
    $("#chosen-file").classList.add("hidden");
    renderMediaPicker();
    renderUploadArea();
    showEmpty();
  }

  function showStatusBanner(kind, text) {
    var banner = $("#status-banner");
    if (!banner) return;
    banner.className = "status-banner status-banner--" + kind;
    banner.innerHTML = "";
    if (kind === "running" || kind === "waiting") {
      banner.appendChild(el("span", "spinner"));
    }
    banner.appendChild(el("span", "status-text", text));
    banner.classList.remove("hidden");
  }

  function hideStatusBanner() {
    var banner = $("#status-banner");
    if (banner) banner.classList.add("hidden");
  }

  function showEmpty() {
    hideStatusBanner();
    $("#results").classList.add("hidden");
    $("#interactive-empty").classList.remove("hidden");
  }

  function showResults() {
    $("#interactive-empty").classList.add("hidden");
    $("#results").classList.remove("hidden");
  }

  function pollJob(jobId) {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(function () {
      apiGet("/api/jobs/" + jobId).then(function (res) {
        if (res.status !== 200) return;
        var job = res.body;
        state.currentJob = job;
        renderJobState(job);
        if (isTerminal(job.status)) {
          clearInterval(state.pollTimer);
          state.pollTimer = null;
        }
      }).catch(function () {
        // Keep the interval alive after a network error. There is currently
        // no retry limit; reset or page teardown ends this polling loop.
      });
    }, 1200);
  }

  function renderJobState(job) {
    if (!job) return;
    var status = job.status;
    if (status === "WAITING") {
      showStatusBanner("waiting", t("status.waiting"));
      showResults(); // keep prior results hidden but show region
      renderResultsPending();
    } else if (status === "RUNNING") {
      showStatusBanner("running", t("status.running"));
      showResults();
      renderResultsPending();
    } else if (status === "SUCCEEDED") {
      showStatusBanner("success", t("status.success"));
      showResults();
      renderResults(job);
    } else if (status === "INTERRUPTED") {
      showStatusBanner("failed", t("status.interrupted"));
      showResults();
      renderResultsError(job);
    } else if (status === "FAILED") {
      showStatusBanner("failed", t("status.failed.prefix") + friendlyError({ message: job.error }));
      showResults();
      renderResultsError(job);
    }
    renderUploadArea();
  }

  function renderResultsPending() {
    var media = $("#result-media");
    var inspector = $("#result-inspector");
    if (media) { media.innerHTML = ""; media.appendChild(el("p", "", t("status.pending"))); }
    if (inspector) inspector.innerHTML = "";
  }

  function renderResultsError(job) {
    var media = $("#result-media");
    var inspector = $("#result-inspector");
    if (media) {
      media.innerHTML = "";
      media.appendChild(el("p", "result-error-note", t("result.error.none")));
    }
    if (inspector) {
      inspector.innerHTML = "";
      inspector.appendChild(el("p", "prototype-copy", t("result.error.noresults")));
    }
  }
  function fmtTs(ms) {
    var total = Math.round(ms);
    var h = Math.floor(total / 3600000);
    var m = Math.floor((total % 3600000) / 60000);
    var s = Math.floor((total % 60000) / 1000);
    var msPart = total % 1000;
    function pad(n, w) { return String(n).padStart(w, "0"); }
    return pad(h, 2) + ":" + pad(m, 2) + ":" + pad(s, 2) + "." + pad(msPart, 3);
  }

  function renderImageResults(job) {
    var media = $("#result-media");
    media.innerHTML = "";
    var img = el("img");
    img.src = "/api/artifacts/" + job.job_id + "/annotated.jpg";
    img.alt = t("result.image.alt");
    media.appendChild(img);
    setResultCaption(job, t("result.image.caption"));

    var inspector = $("#result-inspector");
    inspector.innerHTML = "";
    var run = job.run || {};
    var head = el("div", "inspector-heading");
    var headLeft = el("div");
    headLeft.appendChild(el("p", "eyebrow", t("result.image.eyebrow")));
    headLeft.appendChild(el("h2", "", t("result.image.heading")));
    head.appendChild(headLeft);
    head.appendChild(el("span", "count-badge", String(run.detection_count || 0)));
    inspector.appendChild(head);

    // Detection records (from detections.csv).
    renderDetectionTable(job);

    // Downloads.
    inspector.appendChild(buildDownloadList(job));
  }

  function renderVideoResults(job) {
    var media = $("#result-media");
    media.innerHTML = "";
    var video = el("video");
    video.controls = true;
    video.preload = "metadata";
    video.src = "/api/artifacts/" + job.job_id + "/annotated.mp4";
    video.setAttribute("playsinline", "true");
    media.appendChild(video);
    setResultCaption(job, t("result.video.caption"));

    var inspector = $("#result-inspector");
    inspector.innerHTML = "";

    var run = job.run || {};
    var videoMeta = run.video || {};

    var head = el("div", "inspector-heading");
    var headLeft = el("div");
    headLeft.appendChild(el("p", "eyebrow", t("result.video.eyebrow")));
    headLeft.appendChild(el("h2", "", t("result.video.heading")));
    head.appendChild(headLeft);
    head.appendChild(el("span", "count-badge", String(run.detection_count || 0)));
    inspector.appendChild(head);

    var meta = el("div", "frame-details");
    var titleRow = el("div", "section-title-row");
    titleRow.appendChild(el("h3", "", t("result.runinfo")));
    titleRow.appendChild(el("span", "", t("result.realrecord")));
    meta.appendChild(titleRow);
    var dl = el("dl");
    function row(dt, dd) {
      var d = el("div");
      d.appendChild(el("dt", "", dt));
      d.appendChild(el("dd", "", dd));
      return d;
    }
    if (videoMeta.width) {
      dl.appendChild(row(t("result.meta.resolution"), videoMeta.width + " × " + videoMeta.height));
    }
    if (videoMeta.fps) {
      dl.appendChild(row(t("result.meta.fps"), videoMeta.fps + t("result.meta.fps.note")));
    }
    if (run.frame_count != null) {
      dl.appendChild(row(t("result.meta.frames"), run.frame_count + t("result.meta.frames.unit")));
    }
    if (run.detection_count != null) {
      dl.appendChild(row(t("result.meta.detections"), run.detection_count + t("result.meta.detections.unit")));
    }
    meta.appendChild(dl);
    inspector.appendChild(meta);

    var note = el("div", "identity-note");
    note.appendChild(el("span", "note-mark", "!"));
    note.appendChild(el("p", "", t("result.identity.note")));
    inspector.appendChild(note);

    // Detection records (from detections.csv).
    renderDetectionTable(job);

    // Downloads.
    inspector.appendChild(buildDownloadList(job));
  }

  function setResultCaption(job, text) {
    var caption = $("#result-caption");
    if (caption) {
      caption.innerHTML = "";
      caption.appendChild(el("span", "", text));
      caption.appendChild(el("span", "", job.input_name || ""));
    }
  }

  function buildDownloadList(job) {
    var wrap = el("div", "download-list");
    var items = job.artifacts || [];
    if (items.length === 0) {
      var empty = el("span", "download-none", t("download.empty"));
      wrap.appendChild(empty);
      return wrap;
    }
    items.forEach(function (a) {
      var link = el("a", "download-item");
      var name = el("span", "download-name", a.name);
      var size = el("span", "download-size", fmtBytes(a.bytes));
      link.appendChild(name);
      link.appendChild(size);
      link.href = "/api/artifacts/" + job.job_id + "/" + a.name;
      link.setAttribute("download", a.name);
      link.title = t("download.title") + " " + a.name;
      wrap.appendChild(link);
    });
    return wrap;
  }

  function renderDetectionTable(job) {
    var inspector = $("#result-inspector");
    if (!inspector) return;
    var isVideo = job.media_type === "video";

    var section = el("div", "detection-section");
    var titleRow = el("div", "section-title-row");
    titleRow.appendChild(el("h3", "", t("detection.title")));
    var totalSpan = el("span", "", t("detection.source"));
    titleRow.appendChild(totalSpan);
    section.appendChild(titleRow);

    var tableWrap = el("div", "detection-table-wrap");
    var table = el("table", "detection-table");
    var thead = el("thead");
    var hr = el("tr");
    var cols = isVideo
      ? [t("detection.col.frame"), t("detection.col.ts"), t("detection.col.class"),
         t("detection.col.conf"), t("detection.col.track"), t("detection.col.coord")]
      : [t("detection.col.class"), t("detection.col.conf"), t("detection.col.coord")];
    cols.forEach(function (c) { hr.appendChild(el("th", "", c)); });
    thead.appendChild(hr);
    table.appendChild(thead);

    var tbody = el("tbody");
    var loading = el("tr");
    var loadingCell = el("td", "", t("detection.loading"));
    loadingCell.colSpan = cols.length;
    loading.appendChild(loadingCell);
    tbody.appendChild(loading);
    table.appendChild(tbody);
    tableWrap.appendChild(table);
    section.appendChild(tableWrap);
    inspector.appendChild(section);

    apiGet("/api/jobs/" + job.job_id + "/detections").then(function (res) {
      var data = res.body || {};
      var rows = data.rows || [];
      tbody.innerHTML = "";
      if (rows.length === 0) {
        var emptyRow = el("tr");
        var emptyCell = el("td", "track-id-none", t("detection.empty"));
        emptyCell.colSpan = cols.length;
        emptyRow.appendChild(emptyCell);
        tbody.appendChild(emptyRow);
      } else {
        rows.forEach(function (d) {
          var r = el("tr");
          var conf = d.confidence ? (parseFloat(d.confidence) * 100).toFixed(1) + "%" : t("detection.none");
          if (isVideo) {
            var tsMs = parseInt(d.timestamp_ms, 10);
            r.appendChild(el("td", "", d.frame_index));
            r.appendChild(el("td", "", isNaN(tsMs) ? t("detection.none") : fmtTs(tsMs)));
            r.appendChild(el("td", "", d.class_name));
            r.appendChild(el("td", "", conf));
            r.appendChild(el("td", d.track_id ? "" : "track-id-none", d.track_id || t("detection.none")));
            r.appendChild(el("td", "", "(" + d.x1 + "," + d.y1 + ")"));
          } else {
            r.appendChild(el("td", "", d.class_name));
            r.appendChild(el("td", "", conf));
            r.appendChild(el("td", "", "(" + d.x1 + "," + d.y1 + ")"));
          }
          tbody.appendChild(r);
        });
      }
      if (data.truncated) {
        totalSpan.textContent = t("detection.total.truncated", { total: data.total, shown: rows.length });
      } else {
        totalSpan.textContent = t("detection.total.full", { total: data.total });
      }
    }).catch(function () {
      tbody.innerHTML = "";
      var errRow = el("tr");
      var errCell = el("td", "track-id-none", t("detection.unavailable"));
      errCell.colSpan = cols.length;
      errRow.appendChild(errCell);
      tbody.appendChild(errRow);
    });
  }

  function renderResults(job) {
    if (job.media_type === "image") {
      renderImageResults(job);
    } else if (job.media_type === "video") {
      renderVideoResults(job);
    } else {
      renderResultsError(job);
    }
  }

  var ACCEPT_RE = /\.(jpe?g|png|mp4)$/i;

  function fileKind(file) {
    if (!file) return null;
    if (/\.(jpe?g|png)$/i.test(file.name)) return "image";
    if (/\.mp4$/i.test(file.name)) return "video";
    return null;
  }

  function acceptFile(file) {
    if (!file) return false;
    return ACCEPT_RE.test(file.name);
  }

  function setChosenFile(file) {
    if (!file) return;

    // Size guard (mirrors the server-side 256 MiB limit).
    if (file.size > MAX_UPLOAD_BYTES) {
      showStatusBanner("failed", t("error.too_large"));
      clearChosenFile();
      return;
    }

    var kind = fileKind(file);
    if (kind && state.mediaType && kind !== state.mediaType) {
      showStatusBanner("failed",
        t("error.type_mismatch", { mode: state.mediaType === "image" ? t("mode.image") : t("mode.video") }));
      clearChosenFile();
      return;
    }

    state.fileName = file.name;
    var input = $("#file-input");
    // Reflect the file into the native input so submission picks it up,
    // allowing programmatic drag-drop selection.
    try {
      var dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      state.file = null;
    } catch (e) {
      // DataTransfer unsupported: keep the file in state and submit directly.
      state.file = file;
    }
    $("#chosen-file").classList.remove("hidden");
    $("#chosen-file .file-name").textContent = file.name;
    // Show a subtle size hint next to the name.
    var sizeHint = $("#chosen-file .file-size");
    if (sizeHint) sizeHint.textContent = fmtBytes(file.size);
    renderUploadArea();
  }

  function clearChosenFile() {
    state.fileName = null;
    state.file = null;
    var input = $("#file-input");
    if (input) input.value = "";
    $("#chosen-file").classList.add("hidden");
    renderUploadArea();
  }

  function onFileChosen(input) {
    var file = input.files && input.files[0];
    if (!file) return;
    setChosenFile(file);
  }

  function bindDragDrop() {
    var strip = $("#job-strip");
    if (!strip) return;
    var dragDepth = 0;

    function hasFiles(ev) {
      return ev.dataTransfer && Array.prototype.some.call(ev.dataTransfer.types, function (t) {
        return t === "Files";
      });
    }

    strip.addEventListener("dragenter", function (ev) {
      ev.preventDefault();
      if (!hasFiles(ev)) return;
      dragDepth++;
      strip.classList.add("is-dragover");
    });

    strip.addEventListener("dragover", function (ev) {
      ev.preventDefault();
      if (hasFiles(ev)) {
        ev.dataTransfer.dropEffect = "copy";
        strip.classList.add("is-dragover");
      }
    });

    strip.addEventListener("dragleave", function (ev) {
      ev.preventDefault();
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) strip.classList.remove("is-dragover");
    });

    strip.addEventListener("drop", function (ev) {
      ev.preventDefault();
      dragDepth = 0;
      strip.classList.remove("is-dragover");
      var files = ev.dataTransfer && ev.dataTransfer.files;
      if (!files || files.length === 0) return;
      var file = files[0];
      if (!acceptFile(file)) {
        showStatusBanner("failed", t("error.drop_unsupported"));
        return;
      }
      setChosenFile(file);
    });
  }

  function onSubmit() {
    if (state.submitting) return; // debounce double-clicks
    var input = $("#file-input");
    var file = (input.files && input.files[0]) || state.file;
    if (!file || !state.mediaType) return;

    // Pre-submit guards.
    if (file.size > MAX_UPLOAD_BYTES) {
      showStatusBanner("failed", t("error.too_large"));
      clearChosenFile();
      return;
    }
    var kind = fileKind(file);
    if (kind !== state.mediaType) {
      showStatusBanner("failed", t("error.type_mismatch_short"));
      return;
    }

    state.submitting = true;
    renderUploadArea();
    var fd = new FormData();
    fd.append("file", file);
    showStatusBanner("waiting", t("status.submitting"));
    apiPostJob(fd).then(function (res) {
      state.submitting = false;
      if (res.status === 409) {
        showStatusBanner("failed", friendlyError(res.body));
        return;
      }
      if (res.status !== 202 && res.status !== 200) {
        showStatusBanner("failed", friendlyError(res.body));
        renderUploadArea();
        return;
      }
      state.currentJob = res.body;
      renderJobState(res.body);
      pollJob(res.body.job_id);
    }).catch(function (err) {
      state.submitting = false;
      renderUploadArea();
      showStatusBanner("failed", t("error.connect") + err.message);
    });
  }

  function cancelJob() {
    var job = state.currentJob;
    if (!job || isTerminal(job.status)) return;
    apiDelete("/api/jobs/" + job.job_id).then(function (res) {
      if (res.status === 200 || res.status === 409) {
        // Cancellation is requested; the worker still needs a moment to release
        // the pipeline lock. Show a note and keep polling until INTERRUPTED.
        showStatusBanner("waiting", t("status.canceling"));
        var cancelBtn = $("#cancel-btn");
        if (cancelBtn) cancelBtn.disabled = true;
        if (!state.pollTimer) pollJob(job.job_id);
      } else {
        showStatusBanner("failed", friendlyError(res.body));
      }
    }).catch(function (err) {
      showStatusBanner("failed", t("error.cancel") + err.message);
    });
  }

  function checkHealth() {
    apiGet(API.health).then(function (res) {
      var h = res.body || {};
      setServicePill(h);
      if (h.active_nonterminal_job) {
        // If there is an active job, discover it via the jobs list.
        apiGet(API.jobs).then(function (listRes) {
          var list = listRes.body || {};
          var jobs = list.jobs || [];
          var active = jobs.filter(function (j) { return !isTerminal(j.status); })[0];
          if (active) {
            state.currentJob = active;
            renderJobState(active);
            pollJob(active.job_id);
          }
        });
      }
    }).catch(function () {
      setServicePill({ ok: false });
    });
  }

  // Restore the most recent job on page load (survives a refresh).
  // Restore from the running backend, not browser storage. A backend restart
  // clears the task index even when artifact files remain on disk.
  function restoreLastJob() {
    apiGet(API.jobs).then(function (res) {
      var jobs = (res.body && res.body.jobs) || [];
      if (jobs.length === 0) return;
      // Single-type pages only restore jobs of their own media type.
      var candidates = jobs;
      if (APP_MODE === "image" || APP_MODE === "video") {
        candidates = jobs.filter(function (j) { return j.media_type === APP_MODE; });
      }
      if (candidates.length === 0) return;
      var active = candidates.filter(function (j) { return !isTerminal(j.status); });
      var target = active[0] || candidates[0];
      if (!target) return;
      state.currentJob = target;
      state.mediaType = target.media_type || null;
      renderMediaPicker();
      renderJobState(target);
      if (!isTerminal(target.status)) {
        pollJob(target.job_id);
      }
    }).catch(function () {
      // no-op; leave the empty state.
    });
  }

  function init() {
    // Initialise i18n before rendering any dynamic text.
    if (window.I18N) window.I18N.init();
    // Single-type pages pre-select their media type up front.
    if (APP_MODE === "image" || APP_MODE === "video") {
      state.mediaType = APP_MODE;
    }
    renderMediaPicker();
    renderUploadArea();
    showEmpty();
    bindDragDrop();
    var fileInput = $("#file-input");
    if (fileInput) fileInput.onchange = function () { onFileChosen(fileInput); };
    var submit = $("#submit-btn");
    if (submit) submit.onclick = onSubmit;
    var cancelBtn = $("#cancel-btn");
    if (cancelBtn) cancelBtn.onclick = cancelJob;
    var resetBtn = $("#reset-btn");
    if (resetBtn) resetBtn.onclick = resetWorkbench;
    var langToggle = $("#lang-toggle");
    if (langToggle) {
      langToggle.onclick = function () {
        var next = (window.I18N && window.I18N.getLang() === "zh") ? "en" : "zh";
        if (window.I18N) window.I18N.setLang(next);
        // Re-render dynamic state so already-visible text updates too.
        renderUploadArea();
        setServicePill({ ok: true });
        if (state.currentJob) renderJobState(state.currentJob);
      };
    }
    restoreLastJob();
    checkHealth();
    setInterval(checkHealth, 5000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
