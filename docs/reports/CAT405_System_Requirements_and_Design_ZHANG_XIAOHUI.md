# UAV Video Object Detection and Multi Object Tracking Web Visualization System

CAT405 Intelligent Computing Major Project

System Requirements and Design Analysis Report

School of Computer Science, Universiti Sains Malaysia

Author: ZHANG XIAOHUI

Student ID: USM202309040

Supervisor: Dr.Danny Chen Sien Yau

Programme: Intelligent Computing

Report date: 17 November 2026

Requirements baseline: SRS 1.2. Design document version: SRD 1.0.

## 1 Abstract

### 1.1 English Abstract

Reviewing unmanned aerial vehicle (UAV) recordings requires more than displaying object boxes: users need to follow observations over time, inspect errors, and retrieve results with a clear connection to the original media. This project proposes a local web application for vehicle detection, within-video multi-object tracking, and bounded evidence-linked scene summaries. It accepts one image or recorded video at a time and initially targets car, bus, and truck. A supported YOLO26 detector will be adapted to aerial imagery using audited VisDrone annotations. Larger model candidates will be evaluated against a compact baseline under the available computer resources, rather than assuming that the largest model provides the best result. ByteTrack and BoT-SORT will be compared using consistent detection settings. A Python API and single background worker will process media, while SQLite and local files preserve jobs, configuration snapshots, observations, and outputs. The browser will provide synchronized playback, class and temporary-ID filtering, history, and annotated-media and structured-data export. Scene summaries will report visible counts, image-region distribution, and observed track intervals; they will not infer incidents, real-world speed, or identity. Independent detection, tracking, summary, and software acceptance tests are specified. At this analysis stage, the requirements package and static interface mockup exist, but dataset auditing, training, evaluation, and functional integration remain uncompleted. The design therefore defines feasibility gates and pilot-dependent targets without claiming measured accuracy or operational benefits.

Keywords: UAV video, object detection, multi-object tracking, YOLO, VisDrone, web visualization.

### 1.2 Abstrak Bahasa Melayu

Semakan rakaman kenderaan udara tanpa pemandu (UAV) memerlukan lebih daripada paparan kotak pengesanan. Pengguna perlu mengikuti pemerhatian merentas bingkai, meneliti ralat, dan mendapatkan hasil yang dapat dipadankan dengan media asal. Projek ini mencadangkan aplikasi web setempat untuk pengesanan kenderaan, penjejakan berbilang objek dalam satu video, serta ringkasan pemandangan terhad yang disokong bukti. Sistem menerima satu imej atau video rakaman pada satu masa dan pada peringkat awal menumpukan kelas kereta, bas, dan trak. Model pengesan YOLO26 akan disesuaikan menggunakan anotasi VisDrone yang telah diaudit. Calon model yang lebih besar akan dibandingkan dengan model asas yang ringkas berdasarkan ketepatan dan sumber komputer yang tersedia. ByteTrack dan BoT-SORT pula akan dibandingkan menggunakan tetapan pengesanan yang konsisten. API Python dan satu proses pekerja latar belakang akan memproses media, manakala SQLite serta fail setempat menyimpan tugas, konfigurasi, pemerhatian, dan hasil. Antara muka pelayar akan menyediakan main balik terselaras, penapisan mengikut kelas dan ID sementara, sejarah tugas, serta eksport media beranotasi dan data berstruktur. Ringkasan hanya merangkumi bilangan objek yang kelihatan, taburan kawasan imej, dan sela pemerhatian jejak; sistem tidak menentukan kejadian, kelajuan sebenar, atau identiti. Laporan ini menetapkan ujian berasingan bagi pengesanan, penjejakan, ringkasan, dan fungsi perisian. Pada peringkat analisis ini, dokumen keperluan dan prototaip antara muka statik telah tersedia, tetapi audit data, latihan model, penilaian, dan penyepaduan fungsi belum selesai. Oleh itu, sasaran kuantitatif akan ditetapkan selepas ujian rintis dan sebelum ujian akhir.

Kata kunci: video UAV, pengesanan objek, penjejakan berbilang objek, YOLO, VisDrone, visualisasi web.

## 2 Introduction

### 2.1 Project Background

An elevated camera can observe several vehicles in a single image, but target size, density, occlusion, and camera movement make aerial video analysis difficult. An object detector identifies categories and locations in individual frames; a tracker associates detections across time. Neither component alone supplies a complete application for uploading a recording, finding an observation, checking a trajectory gap, and exporting reproducible results. The proposed project connects these functions through a local browser application.

The application is a computer-science project rather than a drone construction project. Its inputs are existing images and recorded UAV videos; it does not operate an aircraft. The intended users are the student developer and a supervisor or reviewer using the same local workstation at different times. The core classes are car, bus, and truck. Their exact source mappings and their compatibility with the selected tracking evaluation subset remain subject to data auditing.

VisDrone provides human-annotated aerial detection and tracking tasks [1], [2]. These annotations provide a basis for supervised adaptation and independent evaluation, but the project must still verify downloaded files, task-specific class definitions, ignored regions, and possible overlap between detection and tracking data. Publicly available annotations do not automatically establish that a particular experiment is valid.

### 2.2 Problem Statements

P1: Aerial targets may be small or partially hidden, causing missed detections and confusion between vehicle categories. A high-confidence output can still be wrong, so confidence alone cannot measure recognition accuracy.

P2: Tracking IDs may change when targets overlap or disappear. Camera motion affects image-plane displacement, and an apparently continuous line may hide missing observations. Users require honest representation of track gaps and the limited meaning of temporary IDs.

P3: Standalone inference scripts lack a complete review workflow. Input errors, background processing, media synchronization, saved results, and export must be handled consistently by the software.

P4: A visually convincing demonstration may lack independent evaluation. Related video frames can leak across splits, annotation conversions can be incorrect, and data generated by the model can be mistaken for ground truth. The system needs traceable configurations and a reproducible evaluation protocol.

P5: Broad claims of scene understanding exceed the available annotations and project scope. A useful first version should summarize observable counts, image regions, and track intervals with evidence instead of inventing incidents or physical interpretations.

### 2.3 Motivation

The motivation is to make selected observations in aerial recordings easier to inspect and reproduce. A reviewer should be able to see a detection, select its temporary track, move to the relevant source time, and inspect the corresponding structured record. This is a concrete software and AI integration problem with a bounded evaluation route. Potential contexts include offline aerial traffic review and research demonstrations, but no improvement in professional productivity or public safety is claimed without a separate study.

### 2.4 System Objectives

| Objective | Planned outcome | Acceptance evidence |
| --- | --- | --- |
| O1 Data integrity | Prepare audited detection and tracking data with fixed class mappings and independent manifests. | Source inventory, conversion checks, overlap review, DR01-DR07 and AT11. |
| O2 Recognition | Establish a pretrained baseline and fine-tune a supported YOLO26 detector for the selected vehicle classes. | Per-class precision/recall, mAP50 and mAP50-95, controlled comparisons, AT12/AT17/AT18. |
| O3 Tracking | Associate observations within each video and expose identity errors and trajectory gaps. | Validated tracking adapter, HOTA/IDF1/MOTA, ID switches and fragmentation, AT06/AT12. |
| O4 Evidence summaries | Derive counts, image-region distribution, and observed video-track intervals without unsupported claims. | Hand-checkable logic cases and end-to-end reference comparisons, AT16a/AT16b. |
| O5 Software workflow | Support local upload, validation, processing, playback, filtering, history and export. | Functional, fault, persistence, privacy and reproduction evidence, AT01-AT15. |

Quantitative quality thresholds are not yet measured or approved. They must be justified with pilot results and frozen before final testing. Objective completion requires both the specified evidence and the applicable frozen criteria, not simply a model that runs.

### 2.5 Proposed Solution

The proposed solution uses YOLO26 for detection, ByteTrack as a tracking baseline, and BoT-SORT as a controlled comparison. It uses a deterministic rule-and-template layer for limited scene summaries. The frontend calls a Python API; one background worker performs decoding and inference; SQLite records job metadata and immutable configuration references; local directories hold source media and outputs. Images bypass tracking. Training and evaluation remain offline developer activities rather than browser features.

[[FIG:architecture|Figure 2.1 Proposed local system architecture]]

All blocks in Figure 2.1 are planned functional components. The current HTML/CSS mockup demonstrates navigation and layout only. Its illustrative imagery and fictional values must not be presented as model output.

[[FIG:intro_pipeline|Figure 2.2 Proposed model and algorithm pipeline]]

Figure 2.2 outlines the proposed intelligent processing method rather than the internal neural-network structure. YOLO26 produces selected-class detections for both input modes. Images proceed directly to a single-frame summary; recorded videos additionally use a configured tracker and observed track segments. Both paths produce source-linked results for the web workflow. The exact YOLO26 model scale, weights, input resolution and final tracker remain pending validation-set comparison. The diagram is a planned design, not evidence that inference or integration has been implemented.

### 2.6 Benefits and Uniqueness

The intended benefit is an inspectable workflow that joins aerial detection and tracking to source-linked results. Its contribution is applied engineering and evaluation: preserving configuration provenance, maintaining observation gaps, comparing detection and tracking choices fairly, and checking finite summaries against independent labels. It does not propose a new neural-network architecture. The design deliberately avoids treating temporary IDs as identity or deriving real-world movement from camera-relative pixel tracks.

### 2.7 Organisation of the Report

Chapter 3 reviews the technical context and limitations of available components. Chapter 4 specifies scope, project management, requirements, system models, modules, data, interfaces, deployment and acceptance. Chapter 5 concludes the analysis and identifies implementation gates. Chapter 6 gives IEEE-style references. Chapter 7 contains detailed use cases, pseudocode, requirements traceability, a parameter-freeze checklist and report-outline coverage.

## 3 Background and Related Work

### 3.1 Development Status and Reused Work

The UAV application is a new project direction supported by earlier environment and camera experiments. Those experiments do not establish UAV model performance. The current UAV project contains a five-page static HTML/CSS prototype: workspace, image detection, video tracking, task history and evaluation. Links between pages exist. Upload, inference, tracking, job persistence, synchronized playback, filtering and export are not implemented. A SRS 1.2 definition package, class table, configuration drafts, nineteen acceptance cases and experiment-log template have been created. Their definition checks cover forty-four requirement identifiers but do not execute application tests.

The following implementation work remains open: data download and audit, model adaptation, evaluator validation, processing services, storage lifecycle, functional frontend integration, and independent testing. The report describes a proposed design for that work and does not report invented measurements, interviews or completed user trials.

### 3.2 Relevant Concepts

Detection outputs category-labelled boxes for each image. Multi-object tracking associates observations into temporary trajectories. Track fragmentation occurs when one true trajectory is split; an ID switch occurs when an identity association changes according to the evaluator's protocol. Image-plane trajectories are sequences of observed box centres, not georeferenced paths. Ground truth means independent human annotations or reviewed reference values derived from them; model predictions are not independent ground truth.

The finite summary layer aggregates these observations. A current-frame count includes valid selected-class detections even when they have no track ID. A track count describes temporary segments and cannot be reported as a count of unique physical vehicles. Region labels refer to left, middle and right portions of the image rather than geographical directions.

### 3.3 Existing Algorithms and Resources

| Resource or method | Relevant strengths | Limitations and role in this project |
| --- | --- | --- |
| YOLO26 via Ultralytics [3], [4] | Supported pretrained detection weights, training and inference interfaces, and integration with trackers. | Generic pretraining is not aerial-domain validation. Larger models and higher resolution consume resources; final weights and parameters remain unselected. |
| VisDrone DET/MOT [1], [2] | Aerial imagery with human boxes and task-specific tracking identities. | Tasks and evaluated classes need auditing; ignored regions, sampling and DET/MOT overlap must be handled explicitly. |
| ByteTrack [5] | Uses a second association stage for lower-score detections to recover useful observations. Straightforward baseline. | A low-score box is not necessarily correct. Association still depends on detector quality and the selected configuration. |
| BoT-SORT [6] | Combines tracking association with camera-motion compensation; optional appearance components are available in relevant implementations. | Its published results are not UAV guarantees. This project does not train a ReID network; enabled options must be recorded. |
| TrackEval [7] and HOTA [8] | Separates detection and association aspects and supplies common tracking metrics. | A compatible VisDrone conversion/adapter and ignore protocol must be verified. A running metric script alone does not validate the evaluation. |
| Deterministic summary rules | Counts and descriptions are inspectable and traceable without a language-model training dataset. | Expressiveness is limited; upstream detection and tracking errors still affect end-to-end correctness. |

This comparison supports integrating existing components rather than claiming a complete off-the-shelf solution. The official Ultralytics tracking interface supports explicit tracker selection [4]; this project will pin a version and name the tracker in configuration instead of relying on a changing library default.

### 3.4 Critical Review and Design Implications

Model benchmark results from other papers or vendor documentation cannot be transferred directly to this project. The dataset split, classes, resolution, ignored regions, hardware and evaluation code may differ. Published claims are treated as motivation for controlled local experiments, not as acceptance scores.

The design separates three kinds of evidence. Detection labels evaluate boxes and categories. Tracking labels evaluate cross-frame association. Summary reference values are computed from independent annotations under explicit rules and reviewed on sample cases. This separation prevents a summary template from being declared accurate merely because it repeats incorrect detector output consistently.

An unrestricted visual-language system could produce richer prose, but it would introduce additional truthfulness, evaluation and dependency problems. The present system therefore uses finite summaries and evidence links. Expanding to event recognition or semantic road analysis would require a formal scope change and appropriate labels.

### 3.5 Proposed Work in Context

The proposed work will implement the review workflow, audit the data and evaluation route, adapt the detector, compare trackers and measure the complete result. Success is a reproducible software and evaluation package with honest failure reporting. It does not require a physical drone, live camera, simulation environment or a production cloud deployment.

## 4 System Requirements and Design

### 4.1 Project Scope and System Boundaries

The system is for local single-user operation. It accepts one JPEG/PNG image or one MP4 recorded video and permits at most one nonterminal job. The initial local classes are 0=car, 1=bus and 2=truck. Their semantic meanings are fixed for the pilot, while the downloaded source taxonomy and common evaluated MOT classes are still to be checked. The class van is not silently merged with car.

Images produce detection overlays and single-frame summaries, with null track IDs and no temporal statements. Videos produce detections, within-job temporary IDs, observed trajectories, per-frame summaries and observed intervals. Inputs outside the supported domain may be processed only within validated file limits; no claim of generalization to arbitrary photographs or recordings follows.

| In scope | Out of scope |
| --- | --- |
| Local upload, validation, one background job, history and deletion of terminal jobs. | Live streams, flight control, public multi-user service or cloud-based processing. |
| Three-class vehicle detection and within-video tracking, with explicit observation gaps. | Face/plate recognition, permanent identity, cross-video matching or ReID training. |
| Source-linked counts, image-region distribution and observed track intervals. | Congestion/violation/accident recognition, semantic segmentation or unrestricted video questions. |
| Annotated media, frame/detection records, CSV/JSON and independent offline evaluation. | Geolocation, real speed, physical driving direction, autonomous safety decisions or guaranteed real-time processing. |

| Candidate input constraint | Planned value | Status |
| --- | --- | --- |
| Image | JPEG/PNG; at most 15 MiB; width <=4096 and height <=2160 pixels. | Pending pilot validation. |
| Video | MP4; at most 200 MiB, 120 seconds, 1920x1080 and 30 FPS. | Pending pilot validation. |
| Encoding and time | Actual deployed decoder must support the codec and preserve a valid frame/time mapping. | Codec profiles and VFR support pending validation. |
| Admission | One file and one nonterminal job; excess submission rejected explicitly. | Fixed requirement; not yet implemented. |

MiB denotes 1,048,576 bytes. MP4 is a container and does not guarantee codec compatibility. Unsupported variable-frame-rate media must be rejected with a conversion suggestion if its timestamps cannot be preserved; the system must not silently trim, skip frames or relabel time.

### 4.2 Project Management

#### 4.2.1 Work Breakdown Structure

| WBS | Work package | Deliverable and dependency |
| --- | --- | --- |
| W1 | Requirements and configuration | SRS, scope/class tables, acceptance matrix and unresolved-parameter register; prerequisite for all stages. |
| W2 | Data acquisition and audit | Source/rights inventory, annotation checks, class mapping, cross-task overlap and split manifests; before full training. |
| W3 | Environment and minimal pipeline | CPU/GPU and container checks, one-image/short-video output and evaluator sanity cases; before experiments. |
| W4 | Detector adaptation | Controlled pretrained versus fine-tuned experiments and selected candidates; requires W2/W3. |
| W5 | Tracking and summaries | Fixed-detector tracker comparison, gap representation and reference-checked summaries; requires valid observations. |
| W6 | Application services | API, admission, worker, storage, recovery and deletion; minimal browser workflow begins early. |
| W7 | Interface integration | Real upload, playback mapping, filters, evidence navigation and exports; replaces illustrative UI content. |
| W8 | Verification and submission | Frozen independent evaluation, fault/stability tests, report, user guide and reproducible demonstration. |

#### 4.2.2 Relative Gantt Schedule and Milestones

The following schedule restates the existing twelve-week sequence. It is relative to project execution, not a calendar promise or a change to the university's official milestones. A filled cell indicates planned work, not completed work. Early minimal frontend integration is retained while model experiments continue offline.

[[GANTT]]

| Gate | Planned point | Evidence needed to proceed |
| --- | --- | --- |
| G1 | Week 1 | Accessible permitted sample, source and annotation inventory, rights record. |
| G2 | Week 2 | Correct label conversion, image/short-video processing and manually checkable evaluation adapter. |
| G3 | End of week 4 | Pilot-driven class/split/configuration and numerical-target freeze; minimal functional webpage. |
| G4 | End of week 8 | Detection adaptation, controlled comparisons, tracking/summary evidence and failure cases. |
| G5 | Weeks 11-12 | All mandatory acceptance evidence, limitations, reproducible configuration and final documentation. |

None of these gates is marked passed in this report. If a gate fails, record a repair plan or an explicit scope change. A reduced demonstration must not be presented as fulfilment of the unchanged original objectives.

#### 4.2.3 SWOT and Risk Responses

| Factor | Analysis | Response |
| --- | --- | --- |
| Strength | Existing annotated aerial data, mature open-source components, and a tightly bounded local workflow. | Preserve raw labels, pin dependencies and build a short technical loop first. |
| Weakness | Small aerial targets, limited development time and no completed functional pipeline. | Compare a limited number of configurations and deliver a minimal web workflow early. |
| Opportunity | Demonstrates AI evaluation and complete software engineering, with later links to robotic perception. | Provide traceable evidence and modular outputs rather than overstating deployment readiness. |
| Threat | Download/access issues, incompatible labels, leakage, resource limits, codec failures and identity switches. | Audit before training; use manifests, bounded processing, explicit errors and failure analysis. |

Data/rights ambiguity blocks affected acquisition or release. Unverified evaluator conversion blocks metric acceptance. GPU memory failure leads to a smaller batch, controlled resolution or documented candidate change, not a fabricated result. Browser codec failure blocks successful publication of that output until repaired.

### 4.3 Development Methodology

An iterative and incremental process is proposed. Each iteration specifies a small requirement group, implements its module, checks it on controlled inputs, and records configuration and evidence before integration. The first loop is data-to-output-to-evaluation on short samples. Subsequent loops add the API and minimal UI, improve the detector, compare tracking, and add source-linked summaries. This sequence exposes data and evaluation risks before extensive training or interface decoration.

Configuration is versioned separately from model weights and data manifests. A change affecting class order, preprocessing, tracker association, timestamp mapping or summary rules triggers the corresponding regression checks. Source data and weights remain outside ordinary source-code commits; their manifests and hashes are versioned. The project directory is currently untracked in its parent Git repository, so no committed release is claimed.

### 4.4 Requirements Elicitation and Stakeholders

Requirements were derived from project discussions, review of the proposed workflow, the existing SRS, static interface inspection and public technical resources. No questionnaire, formal interview sample, field deployment or measured user satisfaction is reported. A later supervised usability exercise is planned but remains unexecuted.

| Stakeholder | Need | Related requirements |
| --- | --- | --- |
| Local reviewer | Submit media, inspect time-linked observations, understand uncertainty, save results. | FR01-FR14, FR18-FR19. |
| Student developer | Prepare data, reproduce experiments, diagnose faults and manage versions. | FR15-FR17, DR01-DR07, NFR11-NFR12. |
| Supervisor or assessor | Check objective completion, experimental validity and honest status. | FR16, AT11-AT12, AT16a-AT18. |
| People represented in media | Controlled local handling and no identity or sensitive recognition claims. | NFR06-NFR08 and scope exclusions. |

### 4.5 Functional Requirements

All functional requirements below are mandatory planned capabilities. Their presence in this document does not imply implementation or a passed test.

| ID | Requirement | Acceptance condition |
| --- | --- | --- |
| FR01 | Accept one image or recorded video and create a job identifier. | Valid JPEG/PNG/MP4 follows its mode; no batch upload implied. |
| FR02 | Validate actual media content, limits and decoding. | Empty, corrupt, disguised and excessive inputs are rejected; no silent truncation. |
| FR03 | Permit only deployed classes and registered configurations. | Invalid options rejected; no arbitrary host path or uploaded weight accepted. |
| FR04 | Enforce at most one nonterminal job on the server. | Second submission in every active stage returns busy without overwriting the first. |
| FR05 | Display truthful stage and processing progress. | Refresh restores status; unknown frame totals do not yield invented percentages. |
| FR06 | Show image boxes, class and confidence. | No targets can be a valid success; images have no track IDs. |
| FR07 | Show video detections and temporary IDs where assigned. | IDs reset per job; unassociated detections may have null ID. |
| FR08 | Synchronize results with source frames/time. | Pause/seek and at least ten sampled points agree within one source frame. |
| FR09 | Filter class/ID and select a track. | Filtering changes presentation only; complete saved results remain intact. |
| FR10 | Draw observed pixel tracks and mark gaps. | Predicted positions are not reported as observed; missing observations remain visible. |
| FR11 | Download valid annotated image or browser-playable MP4. | Output integrity checked before success; audio need not be preserved. |
| FR12 | Export complete CSV/JSON and a data dictionary. | Frames with zero detections retained; IDs/nulls and coordinates agree across formats. |
| FR13 | Persist jobs and reopen terminal results. | Normal restart retains output; missing files produce an explicit inconsistency. |
| FR14 | Show processing metadata and correctly named aggregates. | Counts can be recomputed; track segments are not labelled unique vehicles. |
| FR15 | Bind each result to immutable source/model/configuration evidence. | SHA256 and software, class, input-size, threshold and tracker settings are retrievable. |
| FR16 | Supply reproducible offline evaluation. | Fixed manifests, valid metrics, per-class evidence and failure cases; no browser training required. |
| FR17 | Report failures and interrupted jobs truthfully. | Decode/inference/storage/encoding failures become FAILED; restart marks unfinished work INTERRUPTED. |
| FR18 | Delete a terminal job and registered associated files. | Active deletion rejected; partial cleanup is visible and retryable. |
| FR19 | Generate evidence-linked finite scene summaries. | Counts/regions and video observation intervals satisfy logic and end-to-end checks without unsupported claims. |

### 4.6 Nonfunctional and Data Requirements

| ID | Requirement and planned verification |
| --- | --- |
| NFR01 | Measure full-pipeline time and resource use; after warm-up record at least three runs and their median. Model-only latency is not application FPS. |
| NFR02 | Pilot targets: initial response within 3 seconds after upload, polling every 2 seconds, visible state updates within 5 seconds under normal conditions. Freeze measured conditions and targets before acceptance. |
| NFR03 | Use bounded frame buffers and one worker; training and application inference do not compete concurrently for the same GPU. |
| NFR04 | Publish success only after complete required media/results/index verification. No temporary or partial output through normal download routes. |
| NFR05 | Planned stability exercise: ten consecutive allowed image/video jobs without service crash or cross-job ID residue. This is not a production reliability claim. |
| NFR06 | Bind to loopback, validate Host/Origin, protect state changes with a same-origin token, and reject path traversal. No public unauthenticated exposure. |
| NFR07 | Core processing remains local; no implicit cloud/media upload. After dependency preparation, verify a short input offline. |
| NFR08 | Preserve traceability; detect incomplete jobs and missing assets on restart. Never automatically delete research ground truth. |
| NFR09 | Provide labels, keyboard focus and non-colour status cues; record actual non-developer operation when performed. |
| NFR10 | Validate a recorded Windows and Chromium-browser version, CPU path and optional GPU path; verify actual codec support. |
| NFR11 | Separate responsibilities, pin dependencies, and reproduce a permitted example from recorded commands in a clean setup. |
| NFR12 | Separate proposed targets, measured results, failures and untested cases. Never report a missing test as passed. |

| ID | Data requirement |
| --- | --- |
| DR01 | Record source version, access/rights, package hash, sequence/image ID and acquired sample counts. |
| DR02 | Preserve untouched raw annotations; create versioned conversion outputs and change logs. |
| DR03 | Verify source-to-local class mapping and common evaluated classes. Version class order with the weights. |
| DR04 | Retain ignore information and specify coordinate conversion; deleting ignored boxes does not implement official ignore scoring. |
| DR05 | Separate training, tuning and final test by source sequence; audit exact/near duplicates and cross-task overlap. |
| DR06 | Validate all converted records automatically and review a stratified sample. Current planning values are thirty DET images and ten frames per evaluated MOT sequence, pending pilot freeze. |
| DR07 | Derive summary references from independent human labels using fixed reviewed rules, not from model predictions. |

### 4.7 System Analysis Models

#### 4.7.1 Actors and Use Cases

The local reviewer is the application actor. The developer also runs offline data preparation and evaluation. These are roles for one local installation, not a multi-user authentication design. There is no aircraft actor because flight and live communication are excluded.

[[FIG:web_user|Figure 4.1a UML use cases for the web user]]

[[FIG:offline_developer|Figure 4.1b UML use cases for offline development]]

UC01 submits media and observes progress. UC02 reviews boxes, tracks and source-linked summaries. UC03 exports annotated media and structured data. UC04 reviews history, recovers failed jobs through new submissions, and cleans up terminal jobs. UC05 prepares data and evaluates models offline. Detailed scenarios are included in Appendix A.

#### 4.7.2 Activity and State Models

[[FIG:activity|Figure 4.2 Media processing activity with separate image and video paths]]

An uploaded image follows decoding, detection and a single-frame summary. A video follows sequential frame decoding, detection, association and observed-segment generation before media finalization. Both routes preserve structured evidence. A failure at any processing stage records the stage and error rather than allowing the UI to continue showing a fictional successful result.

[[FIG:states|Figure 4.3 Job state transitions and terminal-state rules]]

The normal sequence is VALIDATING, QUEUED, RUNNING, FINALIZING and SUCCEEDED. Each active stage may fail. On startup, persisted nonterminal work from a previous process becomes INTERRUPTED. A retry creates a new job; it does not mutate a failed job into a successful historical result. Deletion is tracked separately from processing status.

#### 4.7.3 System Sequence

[[FIG:sequence|Figure 4.4 Successful submission and asynchronous result retrieval]]

A successful admission returns HTTP 202 with a job ID; this acknowledges a registered asynchronous task, not completed inference. The browser polls status and requests results only when available. The worker claims one queued job using a conditional state change. Request-level validation and admission conflicts are answered synchronously. Full media-content validation may fail asynchronously on an existing job.

### 4.8 Architecture and Module Design

[[FIG:modules|Figure 4.5 Module responsibilities and evidence flow]]

| Module | Purpose, main input and output | Failure and integrity responsibility |
| --- | --- | --- |
| Web client | Upload selection, status, source-time review, filters and download; consumes API records. | Clearly label mockups versus real results; never fabricate progress or fill missing observations. |
| API and admission | Validate request/options and atomically reserve the single active-job slot. | Reject busy/invalid requests; use server-generated IDs and registered resources. |
| Decoder and validator | Inspect content/limits and stream source frames with timing. | Fail corrupt or unsupported media; preserve zero-based frame and timestamp mapping. |
| Detector | Apply the selected weights and class map; return source-coordinate boxes/confidences. | Record preprocessing and weight hash; do not silently substitute a model/device. |
| Tracker | Associate video detections; return temporary IDs and internal association state. | Reset per video; expose unassociated detections; keep predictions separate from observations. |
| Summary engine | Compute visible class/region counts and observed intervals, then render fixed templates. | Attach evidence and rule version; prohibit identity, real-speed and incident claims. |
| Result writer | Stream frame/detection records and annotated media into staging. | Bound memory, validate record counts/encoding, and publish only complete output. |
| Job repository | Store metadata, events, config references and asset indexes in SQLite. | Enforce active-slot transactions, immutable snapshots and recoverable cleanup. |
| Offline evaluator | Prepare manifests and compare detection/tracking/summary outputs with references. | Enforce split independence, valid adapters and frozen criteria; never substitute predictions for truth. |

#### 4.8.1 Atomic Admission and Worker Ownership

The server uses a SQLite transaction and one singleton active-slot row. An admission transaction checks that the slot is empty, inserts the job and assigns its ID to the slot before committing. A concurrent request sees the occupied slot and returns 409. Disabling an upload button is helpful feedback but is not the concurrency guarantee. The worker claims QUEUED work with a conditional update and verifies one-row ownership before inference.

An instance lock and controlled startup prevent two worker processes from interpreting each other's active jobs as abandoned. Only after acquiring the application instance lock does startup mark old nonterminal jobs INTERRUPTED, release stale ownership and record recovery events. A live instance is not interrupted merely because another browser tab opens.

#### 4.8.2 Publication and Recovery

Files and SQLite do not share a cross-system atomic transaction. The writer therefore stages output in a job-specific temporary directory, finishes encoding, validates media/record integrity, and renames or publishes assets within the same volume. A SQLite transaction then registers those verified assets and sets SUCCEEDED while releasing the slot. Normal result routes require both a committed success record and valid registered assets.

If the process stops after file publication but before database commit, restart treats the job as interrupted and retains diagnostic information; orphan output is not silently exposed as success. A missing asset on a previously successful job is reported as an inconsistency. Repair or cleanup is explicit. This publication order and startup reconciliation are the planned means of achieving consistent user-visible results.

#### 4.8.3 Deletion Lifecycle

Only terminal jobs can be deleted. A separate cleanup marker records requested, in-progress, complete or failed cleanup without adding a new processing state. The service records the asset inventory before removal and retains a tombstone or diagnostic record on partial failure. It does not delete the database index first and then lose the ability to locate residual files. Successful cleanup returns 204 and invalidates normal asset access; failure returns an actionable retry response. Research dataset storage and document backups are outside user-job deletion.

### 4.9 Intelligent Methods and Summary Rules

#### 4.9.1 Detection and Model Selection

A supported YOLO26 detector is initialized from upstream pretrained weights and adapted to the audited VisDrone training data. The plan prioritizes PC-based accuracy and includes larger supported candidates after a memory/time pilot. A compact model remains a baseline. Exact architecture size, input resolution, batch, epoch budget, seed and confidence/overlap parameters remain unset until the installed release and hardware budget are verified [3].

Candidate comparisons use controlled train/validation manifests. The pretrained versus fine-tuned comparison keeps model size and class mapping consistent. Resolution and model-size comparisons are reported separately. Sliced inference may be examined only if small-object misses justify its additional complexity and runtime. The chosen checkpoint and operating point are frozen on validation data before final testing. There is no claim that model size alone improves every aerial target.

#### 4.9.2 Tracking by Detection

ByteTrack supplies a low-overhead association baseline; BoT-SORT provides a comparison that may benefit from camera-motion compensation [4]-[6]. Both receive detections under identical detector settings or from the same recorded detection stream. A threshold that suppresses potentially useful low-score detections too early may affect the tracker, so the complete detector-to-tracker confidence policy is recorded and validated.

The application assigns no cross-video meaning to track IDs. Trackers may use predicted positions internally for association, but only matched detector observations enter the displayed observed trajectory. A missing decoded-frame observation breaks the segment or creates a visible gap. If an ID later reappears, the software reports that ID's observations without asserting that a real identity was recovered correctly.

#### 4.9.3 Finite Scene Summary

For each valid selected-class box, compute its horizontal centre in source pixels and divide by source width. The left region covers [0, 1/3), middle [1/3, 2/3), and right [2/3, 1]. Boundary values belong to the region on the right. Count each retained detection once, including detections with null track ID. The counts describe visible detections under the fixed pipeline; they are not an estimate of all physical vehicles outside the frame or under occlusion.

For video only, group observed records by (job_id, track_id), retaining first/last source time and contiguous observed frame segments. Missing observations are recorded as gaps. A template may state that a temporary track was observed at a source time and that later frames contain a gap. It must not infer a traffic event, physical speed or direction of ground movement. Source frame, time, detection/track references and rule version are saved for every statement.

#### 4.9.4 Timing and Coordinate Contract

Source frame indexes begin at zero. Raw annotation indexing is translated explicitly in the conversion manifest. Boxes use continuous x1/y1/x2/y2 source-pixel boundaries with positive width/height. Coordinates equal to the source extent are valid continuous boundaries; invalid or out-of-range records follow the documented validation policy.

The compatible result/export field is timestamp_ms, measured relative to the source start. Decoder PTS and its rational time base are retained when available. The summary evidence alias timestamp_seconds is explicitly derived as timestamp_ms divided by 1000; it is not a separately estimated time. Images use frame_index=0 and null temporal fields. Numeric conversion is performed once and recorded. Frame timestamps, not a guessed FPS, drive video results; unsupported nonmonotonic or unmappable input is rejected. The encoder stores a source-to-output timeline mapping and is tested for pause/seek agreement.

### 4.10 Data Sources and Experimental Design

#### 4.10.1 Acquisition and Class Mapping

VisDrone2019-DET is the proposed detector source; VisDrone-MOT sequences provide tracking references [1], [2]. The exact downloaded task release, permitted usage, sequence IDs, class fields, ignore conventions and sample counts will be recorded before training. No project-acquired sample count is claimed here. The ten-class DET taxonomy must not be assumed to match every MOT evaluation protocol.

| Local ID and class | Candidate VisDrone source ID | Candidate COCO source ID | Verification |
| --- | --- | --- | --- |
| 0 car | 4 | 2 | Pending source-version and common-class audit. |
| 1 bus | 9 | 5 | Pending source-version and common-class audit. |
| 2 truck | 6 | 7 | Pending source-version and common-class audit. |

Raw data and annotations remain untouched under model/data/raw. Conversion produces a new version and preserves filtering/ignore records. Missing or incompatible classes block the affected experiment or require a documented scope change; they are not assigned fabricated test scores.

#### 4.10.2 Splits and Leakage Control

Training, validation and final-test manifests identify source images/sequences and hashes. Frame grouping follows source video. DET-to-MOT overlap is checked using available metadata, exact hashes and near-duplicate review. Unresolved overlap is excluded from the principal independent test, with residual uncertainty disclosed. Nearby frames must not be randomly split into train and test. The validation set selects configurations; the final test does not select the winning model or threshold.

#### 4.10.3 Experiments and Metrics

| Experiment | Controlled comparison | Measurements |
| --- | --- | --- |
| A | Pretrained versus VisDrone-fine-tuned detector of the same scale. | Per-class precision/recall and mAP50/mAP50-95; false positives/negatives. |
| B | Supported larger models and input resolutions on fixed validation data. | Quality, VRAM, training cost and end-to-end processing time. |
| C | ByteTrack versus BoT-SORT with the fixed detector and sequences. | HOTA, IDF1, MOTA, ID switches and fragmentation under verified ignore/identity rules. |
| D | Deterministic summary logic, then reference-labelled end-to-end summaries. | Exact logic outcomes, per-class count MAE, region error, matched-track time error and unsupported-statement rate. |
| E | Full application and fault/recovery behaviour. | Functional matrix, three repeated performance runs, ten-job stability plan and observed usability. |

Detection confidence is an output score, not accuracy. Tracking metrics must record scales and evaluator configuration. The report will not equate project-specific protocol results with an official leaderboard if ignore or matching rules differ [7], [8].

For summary logic, hand-checkable cases include zero targets, region boundaries, null IDs and observation gaps. For end-to-end testing, human boxes/IDs generate reference statistics under frozen rules with manual checks. Time-boundary errors are reported with matching coverage and unmatched/ID-error counts. When no statements or evaluable samples exist, the relevant ratio is N/A rather than a false zero or pass. Real uploaded videos without annotations can demonstrate operation, but cannot yield verified accuracy claims.

### 4.11 Data and Storage Design

[[FIG:entities|Figure 4.6 Proposed metadata entities and external observation stores]]

SQLite stores small transactional metadata. Large frame and detection collections are streamed into registered structured files rather than requiring every box to be a database row. The diagram distinguishes database entities from logical observation stores. All physical resources belong to a server-generated job directory.

| Entity | Key and selected fields | Invariants |
| --- | --- | --- |
| Job | job_id PK; media_type, source_hash, status, config_id, progress, errors, timestamps, cleanup_status. | One mode per job; state transitions conditional; completed result not silently overwritten. |
| ActiveSlot | slot_id=1 PK; job_id nullable FK. | Singleton, transactionally assigned/released; protects active admission. |
| ConfigSnapshot | config_id PK; canonical JSON, hash, schema/rule version, model/data references. | Immutable after admission; weights/class/parameter association retained. |
| JobEvent | event_id PK; job_id FK, sequence_no, stage, event_time, error_code. | Ordered, diagnostic, no sensitive stack traces in user responses. |
| OutputAsset | (job_id, asset_name) key; relative path, hash, size, media type, verification marker. | Paths resolved from registry; normal access requires committed output. |
| Observation files | frames, detections, summaries and metadata indexed by job. | Empty frames retained; track key includes job_id; missing ID remains null. |

| Result field | Type and unit | Meaning |
| --- | --- | --- |
| schema_version, job_id | strings | Result schema and owner job. |
| frame_index | integer, zero-based | Source decoded-frame order; image is zero. |
| timestamp_ms | number or null, milliseconds | Source-relative canonical export time; null for image. |
| timestamp_seconds | derived number or null | Summary evidence alias = timestamp_ms/1000. |
| class_id, class_name | integer/string | Local class-table identity, not mixed source IDs. |
| detection_id | job-local record identifier | Stable evidence reference for one detected box. |
| detection_confidence | number, 0 to 1 | Detector score; not tracking correctness. |
| x1, y1, x2, y2 | numbers, source pixels | Continuous box boundaries; positive area required. |
| track_id | integer or null | Video-local temporary association; null for image/unassociated detection. |
| observation_type | enumeration | Detected observation; separate internal predictions are not counted as observations. |
| region, rule_version | string/string | Frozen centre-based image region and rule configuration. |

Export comprises metadata.json, frames.csv, detections.csv and a JSON result containing the same logical records; summary/evidence records are included in the structured package. Frames with no detections are represented in frames.csv. CSV empty IDs correspond to JSON null. The data dictionary accompanies export. Browser filters do not rewrite the complete export.

### 4.12 Interface and API Design

#### 4.12.1 Page Responsibilities

| Existing mockup page | Planned functional behaviour | Important empty/error state |
| --- | --- | --- |
| workspace.html | Select a single input and registered mode/configuration; inspect active job. | Busy state, supported limits and no-result guidance. |
| image-detection.html | View boxes, class/score and single-frame count/region summary. | No selected-class detections; invalid image; no temporal controls. |
| index.html | Review processed video, class/ID filters, observed trajectories and timed summaries. | Unassociated ID, gap, missing/unready output and unsupported playback. |
| task-history.html | Reopen terminal jobs, inspect errors and delete with confirmation. | No history, interrupted task, partial cleanup or missing asset. |
| evaluation.html | Display saved offline experiment records and metric definitions. | No measured scores until an experiment is actually registered. |

The current HTML pages provide layout and navigation only. No image or numerical sample from the mockup is presented as a completed experimental result. New interactions will use meaningful labels, keyboard focus and textual status cues. The inference worker will not block the browser request cycle.

#### 4.12.2 API Contract

| ID and route | Success | Principal rejection or error |
| --- | --- | --- |
| IR01 POST /api/jobs | 202 with job_id and status URL after admission. | 409 busy, 413 excessive upload, 415 unsupported type, 422 invalid options. |
| IR02 GET /api/jobs and /api/jobs/{id} | 200 with bounded history or job stage/progress/config reference. | 404 unknown/deleted task; invalid paging rejected. |
| IR03 GET /api/jobs/{id}/results | 200 with bounded frame/detection/summary data and supported filters. | 409 not ready, 422 invalid filter/time/page. |
| IR04 GET /api/jobs/{id}/outputs/{name} | Verified asset download; video range requests supported for playback. | 404 unregistered asset, 409 not ready; no arbitrary filesystem path. |
| IR05 DELETE /api/jobs/{id} | 204 after registered result/source cleanup. | 409 nonterminal, 404 unknown, 500 partial cleanup with retry guidance. |
| IR06 GET /api/config | 200 with deployed classes, supported limits, modes and config IDs. | No host paths, secrets or undeployed model choices exposed. |

Errors share code, message, optional job_id and retryable. Request-level rejections do not create a fake successful job. Detailed asynchronous validation failure is stored against the admitted job. Internal paths and stack traces remain in controlled developer logs, not normal user messages. Pagination and media limits must be bounded and pilot-tested.

### 4.13 Technology and Deployment

| Layer | Proposed technology | Reason and validation need |
| --- | --- | --- |
| Client | Existing HTML/CSS, planned JavaScript, Chromium browser. | Reuse mockup structure; implement real asynchronous API interaction and codec-tested playback. |
| API | Python with FastAPI as the proposed framework. | Typed request validation and local HTTP endpoints; framework version to be pinned during environment work. |
| Processing | PyTorch, Ultralytics YOLO26, OpenCV/FFmpeg. | Detection/tracker access and streaming media handling; verify decoder timestamps and encoding. |
| Persistence | SQLite plus local job directories. | Appropriate for one local user; transactional admission and explicit output reconciliation. |
| Deployment | Windows host; Docker configuration and direct development commands. | CPU path required; optional CUDA/GPU path independently verified. |
| Evaluation | Audited conversion scripts and a verified tracking evaluator/adapter. | Independent measures with frozen manifests and documented protocol. |

An earlier host query recorded an RTX 4070 SUPER with approximately 12,282 MiB VRAM. This is historical inventory evidence, not a fresh hardware benchmark or a guarantee of large-model batch sizes. Available RAM, disk capacity, driver, CUDA/container compatibility and actual usable VRAM must be checked before downloading and training. No drone, Raspberry Pi, camera or simulation environment is required.

The application binds to 127.0.0.1. Same-origin/Host checks and a local session token protect state-changing requests. Original filenames are display metadata only and are never concatenated into file-operation paths. GPU failure does not silently replace weights or claim equivalent CPU speed. Training and application inference are scheduled separately to avoid resource contention.

### 4.14 Verification and Acceptance Strategy

The acceptance matrix contains nineteen cases because AT16 is separated into logic and end-to-end checks. All cases currently have status NOT_EXECUTED. The forty-four covered requirement IDs comprise FR01-FR19, NFR01-NFR12, DR01-DR07 and IR01-IR06. Appendix C gives traceability; the executable definition validator checks file consistency, not model or application correctness.

Before final testing, freeze class mapping, dataset manifests, weights, model resolution, operating thresholds, tracker settings, ignore/matching protocol, input/codec limits, summary regions and numerical pass criteria. Threshold entries are currently null. They must be justified by pilot evidence and frozen by the specified gate before independent final testing. A test cannot pass merely because a model improves on its baseline or because its confidence is high.

Planned tests include legal/illegal input, busy admission, refresh/restart, pause/seek synchronization, zero targets, empty IDs, occlusion gaps, consistent exports, media corruption, inference failure, storage/encoding faults, interrupted jobs and partial cleanup. Detection and tracking evaluation is supplemented by inspection of small-target, dense, occluded and camera-motion cases. Performance uses at least three measured runs; stability uses ten consecutive allowed samples. These are plans, not achieved results.

Each experiment log records time, purpose, test IDs, code state/commit, model/data/weight/config hashes, environment, commands, expected and actual outcomes, metrics, evidence paths, failures, repairs and next actions. The final report must identify passed, failed, blocked and unexecuted cases separately. Unlabelled new video is an operation demonstration, not a quantitative accuracy test.

### 4.15 SDG Alignment and Responsible Use

The strongest alignment is with SDG 9, particularly the learning and research contribution of a reproducible visual-analysis system. SDG 11 provides a contextual connection to understanding urban visual data, but this prototype does not itself demonstrate safer cities, reduced congestion or public-safety outcomes [9], [10]. Its report should not convert these potential contexts into measured impact claims.

Source/model licenses, attribution and redistribution conditions must be recorded. The existence of a public GitHub repository is not unrestricted permission to republish raw imagery or weights. User media remains local until deliberately exported; public examples require appropriate rights. Face/plate recognition and identity profiling are excluded. An aerial prototype with detection errors should not be used to make safety or enforcement decisions.

## 5 Conclusion

This analysis defines a bounded UAV image/video application and its proposed implementation. The design joins audited data preparation, YOLO-based recognition, controlled tracking comparisons and finite evidence-linked summaries to a local web workflow. It specifies transactional job admission, explicit timing/coordinate contracts, staged publication, recoverable deletion, interface behaviour and independent acceptance evidence.

The project is conditionally feasible. Public annotations and reusable components reduce the need for collecting a new dataset, but data access, class compatibility, leakage control, evaluator correctness, compute capacity and codec behaviour remain implementation gates. The current completed work is the requirements/definition package and static UI mockup. Model training, functional integration and acceptance have not been completed. The next action is a small VisDrone DET/MOT audit followed by an image-to-video-to-evaluation technical loop; broad training and interface integration should proceed only after that route is verified.

## 6 References

[1] P. Zhu et al., "Detection and Tracking Meet Drones Challenge," IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 44, no. 11, pp. 7380-7399, 2022. doi: 10.1109/TPAMI.2021.3119563.

[2] VisDrone, "VisDrone Dataset," official dataset repository. https://github.com/VisDrone/VisDrone-Dataset (accessed 17 November 2026).

[3] Ultralytics, "Ultralytics YOLO26," model documentation. https://docs.ultralytics.com/models/yolo26/ (accessed 17 November 2026).

[4] Ultralytics, "Multi-Object Tracking with Ultralytics YOLO," official documentation. https://docs.ultralytics.com/modes/track/ (accessed 17 November 2026).

[5] Y. Zhang et al., "ByteTrack: Multi-Object Tracking by Associating Every Detection Box," in Proceedings of ECCV, 2022. https://arxiv.org/abs/2110.06864.

[6] N. Aharon, R. Orfaig and B.-Z. Bobrovsky, "BoT-SORT: Robust Associations Multi-Pedestrian Tracking," arXiv:2206.14651, 2022. https://arxiv.org/abs/2206.14651.

[7] J. Luiten et al., "TrackEval," tracking evaluation software. https://github.com/JonathonLuiten/TrackEval (accessed 17 November 2026).

[8] J. Luiten et al., "HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking," International Journal of Computer Vision, 2021. https://arxiv.org/abs/2009.07736.

[9] United Nations, "Goal 9: Industry, Innovation and Infrastructure." https://sdgs.un.org/goals/goal9 (accessed 17 November 2026).

[10] United Nations, "Goal 11: Sustainable Cities and Communities." https://sdgs.un.org/goals/goal11.

[11] Z. Xiaohui, UAV project SRS 1.2 and first-step definition package, local project records, 17 November 2026. Files: model/configs/project_scope.json, model/configs/classes.json, model/configs/acceptance_targets.json, docs/step1_scope_and_acceptance.md and docs/acceptance_matrix.csv.

## 7 Appendices

### Appendix A Detailed Use Case Specifications

[[USECASES]]

### Appendix B Processing Pseudocode

The following is proposed logic, not implemented source code. Its checks complement the activity/state diagrams.

[[PSEUDOCODE]]

### Appendix C Requirements and Acceptance Traceability

All rows below are planned tests with status NOT_EXECUTED. The expected outcome is not an observed result. Detailed input/evidence fields remain in docs/acceptance_matrix.csv.

[[TRACEABILITY]]

### Appendix D Pilot Freeze and Evidence Checklist

| Freeze item | Required record | Present status |
| --- | --- | --- |
| Class/taxonomy | Downloaded source meanings, numeric mapping and common MOT evaluation classes. | Pending audit. |
| Data independence | Versioned train/validation/test lists, hashes and overlap decisions. | Pending audit. |
| Model | Supported architecture/weight hash, training model/data/config, checkpoint choice and validation evidence. | Not selected. |
| Tracker | Candidate comparison, fixed detector, parameters and enabled motion/appearance options. | ByteTrack baseline planned; final selection pending. |
| Timing/codec | Supported profiles, PTS mapping and source/output synchronization tests. | Pending pilot. |
| Limits/resources | Input boundaries, VRAM/RAM/disk and error behaviour on the actual host. | Candidate values only. |
| Evaluation | Matching/ignore/class/scaling protocol, adapter sanity cases and sample counts. | Pending validation. |
| Pass targets | Absolute detection, tracking and summary criteria, tolerances and rationale approved before final testing. | Null/unset; final acceptance blocked. |
| Evidence | Commands, versions, hashes, actual logs and final-test outputs. | Template exists; experiments not executed. |


## Implementation status 20 November 2026

As of 20 November 2026, version 0.2.0-alpha.3 provides a local offline test interface. The workspace links to image detection and video tracking pages, which call the YOLO26l and ByteTrack pipeline through a local Python service. They support file selection or drag-and-drop, job state polling, annotated results, downloads and Chinese/English text. Task history and evaluation pages remain placeholders.

The service binds only to 127.0.0.1:8765. Images use detection only; recorded video uses detection and temporary within-video tracking. One input is processed at a time and busy submissions return HTTP 409. Job records are held in memory and are lost on server restart. Cancellation suppresses publication after the worker returns; it does not immediately stop inference.

Development checks comprise 12 backend/API tests and six Playwright scripts covering media, invalid inputs, task states, cancellation, navigation, language switching, drag-and-drop, downloads and refresh recovery. Results and evidence locations are documented in docs/validation/2026-11-20/README.md. These checks are not detector accuracy, performance or formal system acceptance.

The 256 MiB upload guard and parameters imgsz 640, conf 0.25, IoU 0.7 and max_det 1000 remain unfrozen pilot values. Input duration/resolution guards, filtering, a dedicated export flow and frame-synchronized playback are not implemented. IDs are temporary within one video and trajectories are image-plane observations. Fine-tuning, representative quantitative evaluation and all 19 system acceptance cases remain incomplete.
