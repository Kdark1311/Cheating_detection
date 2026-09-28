# Kế hoạch experiment chi tiết theo từng module

Ngày lập: 2026-09-28. Nguồn: [capacity.md](capacity.md) (bản tổng hợp 2026-09-16). Tài liệu này **không thay đổi** quyết định, dataset hay ngưỡng trong `capacity.md`; nó chỉ biến chúng thành các bước thực hiện theo thứ tự.

Trạng thái hiện tại: chưa tải dataset, chưa chạy checkpoint, chưa đo tốc độ. Mọi ngưỡng bên dưới là **mục tiêu pilot**, không phải kết quả.

---

## 0. Cách đọc kế hoạch

Mỗi module đi qua cùng một vòng 6 pha, lấy từ chuỗi "pretrained evaluation → calibration → fine-tune có điều kiện → test độc lập" trong capacity.md §2:

| Pha | Tên | Việc chính | Điều kiện qua pha |
|---|---|---|---|
| P0 | Khóa cấu hình | Chốt repo, commit, checkpoint + checksum, config, preprocessing | Chạy được 1 mẫu, ghi lại hash |
| P1 | Dữ liệu | Tải, checksum, manifest, chuyển nhãn, split theo người/phiên | Manifest + split file được đóng băng |
| P2 | Tái lập benchmark | Chạy checkpoint gốc trên benchmark chuyên biệt đúng official protocol | Sai lệch so với số công bố nằm trong mức giải thích được |
| P3 | Đánh giá đúng miền | Chạy trên dữ liệu thi (OEP/Drive/Roboflow/Mendeley) và các nhóm khó | Có bảng lỗi theo slice |
| P4 | Calibrate / fine-tune có điều kiện | Chọn threshold trên validation theo ràng buộc recall; chỉ fine-tune nếu P3 chỉ ra lỗi cụ thể | So trước/sau trên cùng split |
| P5 | Locked test + bàn giao | Chạy một lần trên locked test, đóng gói kết quả (capacity.md §7.4) | Kết luận: đạt / không đạt / chưa đủ dữ liệu |

Quy tắc chung áp dụng cho mọi module (capacity.md §7):
- Tách split theo **người/phiên**, không random frame. Locked test không dùng để chọn threshold hay model.
- Mọi kết quả phải ghi rõ **unit** (frame, giây, clip, event, session), số người, số phiên, support từng lớp.
- Báo **95% CI bootstrap theo cụm người/phiên** khi dữ liệu cho phép.
- Missing (mất mặt, mất audio) phải có mask + lý do, không tự coi là âm tính.
- Đo riêng **model-only** và **end-to-end** (gồm decode, crop, tracking, IO).

---

## 1. Bước chung trước khi làm module (Step 0)

Ước tính: 2–3 ngày-người. Làm một lần, dùng cho mọi module.

### 0.1 Chốt các quyết định đang mở (blocker)

Những điểm dưới đây capacity.md §8 ghi là **chưa chốt**. Không cần chốt hết để bắt đầu, nhưng mỗi module cần điểm tương ứng trước pha P0:

| Quyết định | Chặn module nào | Cần trước |
|---|---|---|
| ~~Face detector/tracker~~ → **đã chốt (đề xuất, 2026-09-28):** SCRFD-10G-KPS (InsightFace) + ByteTrack + nối lại track bằng AdaFace; identity dùng AdaFace | Face detect/track, AdaFace, 6DRepNet, L2CS-Net | – |
| Co-DETR config/backbone/checkpoint | Co-DETR, Fusion | Module 5 P0 |
| VideoMamba variant (DST chưa khóa) + kích thước embedding | VideoMamba, Fusion | Module 6 P0 |
| ~~VAD / OSD / TS-VAD implementation~~ → **đã chốt (đề xuất, 2026-09-28):** pyannote `segmentation-3.0` cho VAD + OSD, Silero VAD để so/hợp; TS-VAD baseline = segmentation-3.0 + WeSpeaker ResNet34 so với enrollment, AED-TSVAD là phương án nâng cấp. Xem mục 2.1 | Nhánh audio | – |
| Taxonomy event thi (IELTS phần nào, giấy/điện thoại/nói nhỏ/âm Listening) | P3 của mọi module, Fusion, SelectiveNet | Module 10 P1 |
| Quy tắc event matching (temporal IoU chính 0,3 hay 0,5, thời lượng tối thiểu) | Fusion, SelectiveNet, event recall mọi module | Trước mọi locked test |
| Giới hạn workload giám thị (phút xem lại / giờ thi) | Operating point Fusion/SelectiveNet | Module 11 P4 |
| Số người, deadline, VRAM/RAM thực, dung lượng lưu trữ | Lịch và phân GPU | Step 0 |

### 0.2 Hạ tầng thực nghiệm

1. **Cấu trúc thư mục** (đề xuất):
   ```text
   data/raw/<dataset>/            # archive gốc + checksum
   data/manifests/<dataset>.csv   # 1 dòng / mẫu: path, subject_id, session_id, split, label_path
   data/splits/<module>/<dataset>/{train,val,calib,test}.txt
   models/<module>/<name>@<commit>/  # checkpoint + sha256
   experiments/<module>/<exp_id>/    # config.yaml, predictions, metrics.json, report.md
   cache/features/<module>/<version>/ # feature dùng cho fusion
   ```
2. **Experiment card** bắt buộc cho mỗi lần chạy (`experiments/<module>/<exp_id>/config.yaml`): model, commit, checkpoint sha256, dataset version, split file, preprocessing, threshold, batch, resolution, FP16/FP32, GPU, seed.
3. **Bộ công cụ đánh giá dùng chung**: recall/precision/F1/F2, PR-AUC, event matching one-to-one theo temporal IoU, false alerts/giờ, bootstrap CI theo cụm, automatic recall / routing recall / coverage / selective risk (công thức ở capacity.md §7.2). Viết và unit test **trước** khi chạy module đầu tiên để mọi module dùng chung một định nghĩa.
4. **Script benchmark tốc độ**: đo throughput (ảnh/s, clip/s, RTF), peak VRAM, p50/p95, warmup, số lần lặp — cho cả model-only và end-to-end. Ghi RAM hệ thống.
5. **Kiểm tra phần cứng**: xác nhận VRAM từng RTX 3060, RAM, ổ đĩa; ghi vào `experiments/hardware.md`.

### 0.3 Audit dữ liệu thi (làm song song, ảnh hưởng mọi module)

1. **OEP** (Kaggle mirror + trang MSU): đếm người/phiên/giờ, liệt kê stream (webcam, wearcam, mic), schema nhãn thời gian, so với poster (24 người, 569 instances, 7.235 giây cheating). Ghi license.
2. **Drive người dùng**: đếm số video, thời lượng, số người, có audio không, chất lượng. Chưa gán nhãn → lên kế hoạch annotation.
3. **Roboflow Online Proctoring v1**: tải COCO JSON, đếm ảnh gốc vs augmentation (10.213 vs 25.173), phát hiện near-duplicate giữa train/val/test.
4. **Mendeley mjrfmvsh7d** (15.051 ảnh, 3 người) và **Mendeley 39xs8th543** (5.500 records CSV): kiểm tra có subject/session ID không.
5. **Thiết kế annotation cho tập thi đúng miền** (dùng cho P3 nhiều module): face box + track ID, object box, event interval (loại + actor), speech/speaker timeline, enrollment check-in riêng. Đo công gán nhãn trên 10 phút video mẫu để ước lượng tổng.

Đầu ra Step 0: `data_audit.md`, bộ eval toolkit có test, script benchmark, bảng quyết định đã chốt.

---

## 2. Thứ tự làm và phân GPU

Thứ tự theo phụ thuộc dữ liệu: nhánh mặt phụ thuộc face detect; fusion phụ thuộc feature của mọi nhánh; SelectiveNet phụ thuộc fusion.

```text
Step 0 (chung)
  ├─ Nhánh mặt:   [1] Face detect/track → [2] AdaFace
  │                                     → [3] 6DRepNet
  │                                     → [4] L2CS-Net
  ├─ Nhánh thân:  [5] Co-DETR   ‖  [6] VideoMamba
  └─ Nhánh audio: [7] VAD → [8] OSD → [9] TS-VAD
                         ↓ (cache feature mọi nhánh)
                  [10] CHEESE-style Fusion/MIL
                         ↓
                  [11] SelectiveNet
                         ↓
                  [12] End-to-end locked test
```

### 2.1 Implementation đã chọn cho nhánh audio (đề xuất, 2026-09-28)

| Module | Implementation chính | So sánh / dự phòng | Lý do |
|---|---|---|---|
| VAD | [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) qua pipeline `VoiceActivityDetection` của `pyannote.audio` (khóa version) | [Silero VAD](https://github.com/snakers4/silero-vad) (MIT, không cần đăng ký, chạy CPU); thử **hợp (OR)** hai VAD để tăng recall | Cùng một lượt forward cho cả VAD và OSD; MIT; mono 16 kHz, cửa sổ 10 s hợp xử lý offline |
| OSD | Cùng `segmentation-3.0`, pipeline `OverlappedSpeechDetection` | – (chỉ đổi sang model khác nếu P3 hụt recall) | Output powerset 7 lớp có sẵn vùng ≥ 2 người nói; tối đa 3 người cục bộ / 2 người cùng lúc là đủ cho phòng thi |
| TS-VAD – bước 1 (baseline) | segmentation-3.0 tách người nói cục bộ → embedding [WeSpeaker ResNet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM) (CC-BY-4.0) → cosine với embedding check-in → timeline target / non-target / im lặng | – | Không cần train; enrollment là 1 thí sinh (khác bài toán diarization nhiều profile) nên cách so embedding là baseline sát nhiệm vụ nhất. **Đây không phải mạng TS-VAD thực thụ** — ghi rõ khi báo cáo |
| TS-VAD – bước 2 (chỉ khi baseline hụt) | [AED-TSVAD](https://github.com/Clovermax/AED-TSVAD) (dựa trên pyannote/DiariZen/NSD-MS2S, có checkpoint qua Google Drive) | TS-VAD+ và các repo khác trong [Awesome-Speaker-Diarization](https://github.com/DongKeon/Awesome-Speaker-Diarization) | Là mạng TS-VAD có checkpoint công khai. **Chưa xác minh:** license, VRAM, và việc nhận embedding enrollment từ ngoài thay vì profile từ clustering — kiểm tra ở P0 Module 9 |

Lưu ý bắt buộc:
- `segmentation-3.0` là **gated model**: phải đăng nhập Hugging Face, chấp nhận điều kiện, dùng access token.
- `segmentation-3.0` đã train trên **AMI, VoxConverse, AliMeeting, DIHARD**, AISHELL, AVA-AVD, Ego4D, MSDWild, REPERE. Kết quả trên test của các bộ này là **in-domain, dễ lạc quan**. Vì vậy mọi module audio phải báo thêm ít nhất một bộ ngoài tập train: **LibriCSS, CHiME-6, AVA Speech** (chỉ VAD), và dữ liệu thi OEP/Drive.
- WeSpeaker ResNet34-LM train trên VoxCeleb → không dùng VoxCeleb để test enrollment.

Gợi ý chia 2 GPU (job độc lập, không giả định chia đôi thời gian hay gộp VRAM):
- **GPU A**: nhánh mặt (1→2→3→4) rồi VideoMamba (6).
- **GPU B**: nhánh audio (7→8→9) rồi Co-DETR (5).
- Fusion/SelectiveNet chạy trên cache, dùng GPU nào rảnh.

Nếu chỉ có 1 GPU: làm theo thứ tự 1, 7, 2, 3, 4, 8, 9, 5, 6, 10, 11 — xen audio vào giữa để tận dụng thời gian chuẩn bị dữ liệu.

---

## Module 1 — Face detection / tracking

**Vai trò:** cửa vào của nhánh mặt. Mất mặt ở đây = mất đồng thời AdaFace, head pose, gaze.
**Công dự kiến:** 2–3 ngày-người, 1–3 giờ máy (pilot 1 giờ video có box/track ID).
**Cấu hình đã chốt (đề xuất, người dùng đồng ý 2026-09-28):**

| Thành phần | Lựa chọn | Lý do | Dự phòng |
|---|---|---|---|
| Detector | **SCRFD-10G có keypoints** (`scrfd_10g_bnkps`, detector trong model pack `buffalo_l` của InsightFace) | Cùng hệ sinh thái nhóm ArcFace như người dùng muốn; trả 5 landmark nên align thẳng về template 112×112 mà AdaFace dùng; nhẹ hơn RetinaFace-R50 nên dư VRAM trên RTX 3060 cho các model khác | RetinaFace-R50 nếu SCRFD hụt recall ở mặt nghiêng/che khuất; SCRFD-2.5G nếu cần nhanh |
| Tracker | **ByteTrack** | Giữ cả box score thấp để nối track → hợp ưu tiên recall; không cần train | OC-SORT nếu ID switch nhiều khi chuyển động nhanh |
| Nối lại track sau khi rời khung | Similarity **AdaFace** giữa track cũ và track mới | Đúng sơ đồ "AdaFace → Re-ID/Tracking"; không đưa vào fusion | – |
| Nhận diện danh tính | **AdaFace IR-100** (Module 2) | Theo capacity.md và ghi chú workbook AB13; **không** dùng embedding ArcFace đi kèm `buffalo_l` | – |

Số WIDER công bố của SCRFD/RetinaFace phải lấy từ bảng trong repo InsightFace ở P2, chưa dùng số nhớ.
**Chặn bởi:** không còn blocker lựa chọn model; cần dữ liệu thi có face box + track ID cho P3.

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| Benchmark detection | WIDER FACE (val, 3 mức Easy/Medium/Hard) | Official protocol |
| Benchmark detection độc lập | FDDB | Chấm theo **ellipse** official, không coi ellipse là box |
| Ổn định landmark theo thời gian | 300-VW | Landmark error / failure rate, **không** tính IDF1 |
| Đúng miền | OEP/Drive sau khi gán face box + track ID + visibility | Cần annotation |

### Các bước
1. **P0 – Khóa cấu hình:** khóa phiên bản package `insightface`, file `scrfd_10g_bnkps.onnx` + commit ByteTrack, kiểm tra 5 landmark của SCRFD align đúng template AdaFace (so vài crop với pipeline align gốc của repo AdaFace), khóa commit, checkpoint sha256, input resolution, score threshold ban đầu, NMS. Chạy thử 1 video OEP, lưu ảnh overlay.
2. **P1 – Dữ liệu:** tải WIDER val, FDDB, 300-VW; viết converter về một format chung (`frame_id, box, score, track_id`). Từ OEP/Drive: chọn ~1 giờ video, **tách theo người** thành val/test, gán face box + track ID + visibility (VALID/occluded/out-of-frame).
3. **P2 – Tái lập benchmark:** WIDER AP theo Easy/Medium/Hard; FDDB discrete/continuous ROC. So với số công bố của detector đã chọn.
4. **P3 – Đúng miền:** trên video thi đo:
   - face recall @ IoU ≥ 0,5, AP, missing rate;
   - IDF1, số ID switch, số lần mất track rồi quay lại;
   - slice: mặt nghiêng, che mặt, mặt nhỏ, thiếu sáng, rời khung rồi quay lại, người thứ hai xuất hiện;
   - đối chứng: cúi đầu/đổi tư thế không được làm đổi ID.
5. **P4 – Calibrate:** hạ score threshold trên val đến khi recall ≥ 95%, ghi FP/frame tương ứng. Chỉnh tham số ByteTrack (track_thresh, low-score thresh, match_thresh, track_buffer) và ngưỡng similarity AdaFace để nối track. Chỉ fine-tune detector nếu lỗi tập trung vào 1 slice rõ ràng (vd. thiếu sáng) và có đủ box.
6. **P5 – Locked test + bàn giao:** chạy test; xuất `face_tracks.parquet` (session, frame, track_id, box, score, visibility) — **đây là input chuẩn cho module 2–4**. Đo throughput end-to-end.

### Tiêu chí (capacity.md §3.1)
- Face recall **≥ 95%** @ IoU ≥ 0,5 trên video thi; IDF1 **≥ 90%**.
- Báo riêng mặt nhỏ / che khuất. Không bỏ frame mất mặt khỏi mẫu số end-to-end.

---

## Module 2 — AdaFace IR-100 (xác minh danh tính)

**Vai trò:** xác minh 1:1 người đang thi = người đã check-in; phát hiện thay người. **Không** đưa embedding vào fusion; chạy như nhánh nghiệp vụ riêng.
**Công dự kiến:** 2–3 ngày-người, 0,5–2 giờ máy (pilot 10.000 crops + pairs).
**Chặn bởi:** Module 1 (crop + track).

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| Benchmark P1 | AgeDB-30 | Cần email xin password zip |
| Benchmark P1 | CFP-FP | Qua evaluator AdaFace; xác minh bản hợp lệ |
| Robustness P2 | QMUL-SurvFace | Low-quality, open-set |
| Robustness P2 | TinyFace | **1:N**, Rank-1/5; không dùng như verification 1:1 |
| Sanity | LFW | Chỉ kiểm tra evaluator |
| Đúng miền | OEP/Drive: enrollment check-in + probe **khác phiên** | Cần xây protocol |
| Loại | IJB-C | NIST ngừng phân phối; chỉ dùng nếu nhóm đã có bản hợp lệ |

### Các bước
1. **P0:** khóa checkpoint (ghi rõ WebFace4M hay MS1MV2 — không trộn số), sha256, pipeline align (5 landmark → 112×112). Kiểm tra align trên 20 crop bằng mắt.
2. **P1:** gửi email xin AgeDB ngay từ Step 0 (thời gian chờ không tính vào lịch GPU). Tải SurvFace, TinyFace. Với dữ liệu thi: mỗi người 1 đoạn check-in làm enrollment; probe lấy từ **phiên/đoạn khác**, không phải frame liền kề. Tạo danh sách genuine pairs và impostor pairs (đủ nhiều impostor để FAR 0,1% có nghĩa: cần ≥ vài chục nghìn impostor trials).
3. **P2:** chạy evaluator AdaFace trên AgeDB-30, CFP-FP, LFW; so với số của tác giả. SurvFace: TAR@FAR; TinyFace: Rank-1/5.
4. **P3:** trên dữ liệu thi dùng crop từ Module 1 (end-to-end) **và** crop GT (chẩn đoán), tách 2 bảng:
   - ROC, TAR@FAR = 0,1%, failure-to-acquire;
   - slice: kính, quay mặt, ánh sáng khác, crop mờ/nhỏ;
   - mô phỏng thay người: chèn đoạn người khác vào phiên → đo **event recall thay người** và **số false alarm trên người thật/giờ**.
5. **P4:** chọn threshold similarity trên val (không trên test); thêm quality score → trạng thái LOW_QUALITY/UNKNOWN thay vì quyết định. Luật gộp theo track (vd. trung bình k frame tốt nhất). Fine-tune chỉ khi có đủ identity riêng và lỗi domain rõ — nếu không, **không** fine-tune.
6. **P5:** locked test; xuất `identity_events.parquet` (session, t_start, t_end, track_id, similarity, decision, quality).

### Tiêu chí
- Verification: **TAR ≥ 95% @ FAR ≤ 0,1%**.
- Phát hiện thay người: **event recall ≥ 95%** (đề xuất bổ sung) + báo false alarm người thật.
- Hai chỉ số khác nhau, báo riêng. AdaFace không chống giả mạo/liveness.

---

## Module 3 — 6DRepNet (head pose)

**Công dự kiến:** 1–2 ngày-người, 0,5–2 giờ máy (pilot 10.000 crop có GT góc).
**Chặn bởi:** Module 1 (cho P3).

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| Benchmark P1 | AFLW2000-3D | Protocol train-300W-LP |
| Benchmark P1 | BIWI | HF card chỉ là loading script → nếu không lấy được ảnh, dùng Pandora |
| Dự phòng / P2 | Pandora | IMU GT, 22 người |
| P2 | EYEDIAP | Head pose từ preprocessing, không phải IMU |
| Chỉ train | 300W-LP | Không dùng làm test |
| Đúng miền (hướng thô) | Mendeley mjrfmvsh7d (3 người), OEP/Drive | Chỉ categorical, không tính MAE |

### Các bước
1. **P0:** khóa checkpoint train-300W-LP (không lẫn checkpoint BIWI 70/30), crop protocol, quy ước trục yaw/pitch/roll (dấu, thứ tự Euler).
2. **P1:** tải AFLW2000 (qua 3DDFA), xác minh BIWI tải được ảnh thật; nếu không → Pandora. Áp đúng filter góc (vd. |angle| ≤ 99°) theo protocol gốc.
3. **P2:** tính MAE yaw/pitch/roll + trung bình; geodesic error. So với số công bố 3,97° (AFLW2000) / 3,47° (BIWI). Nếu lệch > ~0,5° → kiểm tra crop/convention trước khi đi tiếp.
4. **P3:**
   - Định nghĩa mapping góc → nhóm hướng (trái/phải/xuống/lên/thẳng) **trước khi** nhìn kết quả; ghi vào config.
   - Mendeley/OEP: confusion matrix, macro-F1, recall từng hướng.
   - Định nghĩa sự kiện head-away (ngưỡng góc + thời lượng tối thiểu) → event recall trên video thi.
   - Slice: góc lớn, che khuất; đối chứng nhìn xuống giấy hợp lệ.
   - Chạy trên crop Module 1 và crop GT, báo riêng.
5. **P4:** tinh chỉnh ngưỡng góc/thời lượng trên val theo ràng buộc recall. Fine-tune chỉ khi có GT góc tin cậy (Pandora/BIWI); **không** fine-tune trên nhãn hướng thô.
6. **P5:** locked test; xuất `head_pose.parquet` (session, frame, track_id, yaw, pitch, roll, quality) + event head-away.

### Tiêu chí
- MAE **≤ 5°** AFLW2000, **≤ 4,5°** BIWI; hướng thô macro-F1 **≥ 0,85**; event head-away recall **≥ 95%** (đề xuất bổ sung).
- Head-away tự nó chưa phải vi phạm.

---

## Module 4 — L2CS-Net (gaze)

**Công dự kiến:** 2–3 ngày-người, 0,5–2 giờ máy (pilot 10.000 crop có GT gaze).
**Chặn bởi:** Module 1; nên làm sau Module 3 để so head vs gaze.

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| Benchmark P1 | MPIIFaceGaze | Leave-one-person-out; cùng họ với MPIIGaze, không tính là 2 nguồn |
| Benchmark P1 | Gaze360 | Khóa preprocessing + valid-angle mask |
| P1/P2 | EYEDIAP | Dựng gaze vector theo convention camera |
| P3 có điều kiện | ETH-XGaze | Cần institutional email, học thuật |
| Đúng miền (categorical) | Mendeley mjrfmvsh7d, OEP/Drive | Recall vùng nhìn, **không** angular error |

### Các bước
1. **P0:** khóa checkpoint (MPIIGaze-trained và Gaze360-trained là hai checkpoint khác nhau), normalization (camera/face normalization), input size.
2. **P1:** tải MPIIFaceGaze, Gaze360 (xin qua site chính thức), EYEDIAP. Ghi rõ subset/mask Gaze360 dùng (vd. front 180° hay all 360°).
3. **P2:** mean/median angular error; MPIIFaceGaze theo leave-one-out 15 người; Gaze360 theo mask đã chọn. Báo failure coverage.
4. **P3:**
   - Định nghĩa vùng nhìn (màn hình / ngoài màn hình / xuống bàn) + calibration (nếu có) **trước** khi chấm.
   - Recall từng vùng, macro-F1 trên Mendeley/OEP.
   - Event gaze-away (vùng + thời lượng) → event recall.
   - Slice: mắt đổi hướng khi đầu đứng yên, đầu quay nhưng mắt nhìn màn hình, kính, blink, mắt khó thấy.
   - So sánh với Module 3: gaze có thêm thông tin so với head pose không.
5. **P4:** ưu tiên sửa preprocessing/normalization trước; chỉnh ngưỡng vùng trên val. Fine-tune chỉ khi có nhãn gaze liên tục phù hợp.
6. **P5:** locked test; xuất `gaze.parquet` (session, frame, track_id, gaze_vec, region, quality) + event gaze-away.

### Tiêu chí
- **≤ 5°** MPIIGaze, **≤ 12°** Gaze360 (theo mask đã chọn); vùng nhìn macro-F1 **≥ 0,80**; event gaze-away recall **≥ 95%** (đề xuất bổ sung).

---

## Module 5 — Co-DETR (phát hiện vật thể / bối cảnh)

**Công dự kiến:** 3–5 ngày-người, 1–4 giờ máy (pilot 5.000 ảnh có box). Là module nặng nhất của nhánh thân → đo VRAM sớm.
**Chặn bởi:** chọn config/backbone/checkpoint Co-DETR.

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| Đúng miền, P1 | Roboflow Online Proctoring v1 | 6 lớp: person, cell phone, book, laptop, headphone, tv; audit augmentation/duplicate |
| Baseline, P1 | COCO 2017 val | Map lớp person/cell phone/book/laptop/tv; checkpoint có thể đã train trên COCO |
| P2 | Open Images V7 (subset lớp mục tiêu) | Tôn trọng verified negatives |
| P2 | CharadesDet | Tương tác người–vật trong nhà; không độc lập với Charades |
| P3 | Objects365 | Cần đăng ký; chỉ lấy lớp cần |
| Đúng miền | OEP/Drive sau gán box | Điện thoại nhỏ, giấy, người thứ hai |

### Các bước
1. **P0:** khóa config Co-DETR (backbone, resolution), checkpoint sha256. Đo **ngay** peak VRAM + ảnh/s trên RTX 3060 ở FP16/FP32; nếu không vừa 12GB → giảm resolution hoặc đổi backbone và ghi lại. Kiểm tra claim 13–15 ms/frame trong Model List (chưa xác minh).
2. **P1:**
   - Roboflow: tải COCO JSON; tách ảnh gốc khỏi bản augmentation; dò near-duplicate (perceptual hash) giữa các split; nếu rò rỉ → tạo split mới theo nguồn ảnh.
   - COCO: class map sang 6 lớp mục tiêu.
   - Định nghĩa policy nhãn: vật bị che bao nhiêu thì vẫn gán; "giấy" vs "sách".
3. **P2:** COCO val mAP@0,5:0,95 để xác nhận checkpoint chạy đúng. Checkpoint zero-shot trên Roboflow test (chỉ các lớp trùng COCO).
4. **P3:**
   - Recall + precision từng lớp tại threshold cố định, mAP, FP/ảnh.
   - Slice theo kích thước (small/medium/large) và che khuất.
   - Đối chứng: vật giống điện thoại, tài liệu được phép, laptop/TV không tự là vi phạm.
   - Trích **query embedding** / output cho fusion; kiểm tra shape và cách gán vật cho actor.
5. **P4:** fine-tune trên Roboflow train (sau khi sửa split) nếu lớp mục tiêu (điện thoại, headphone, giấy) chưa đạt recall; ưu tiên thêm lớp mới/vật nhỏ. Ghi thời gian/step để ước lượng chi phí (công thức capacity.md §6.3). Chọn score threshold trên val sao cho recall ≥ 95%.
6. **P5:** locked test (Roboflow test sạch + tập exam); xuất `objects.parquet` (session, frame, class, box, score) + cache embedding cho fusion.

### Tiêu chí
- Lớp mục tiêu: recall **≥ 95%** @ IoU ≥ 0,5; mAP **≥ 0,50** trên tập exam. Precision phải báo (mốc cũ ≥ 0,90 là phụ).

---

## Module 6 — VideoMamba (hành vi cơ thể)

**Công dự kiến:** 3–5 ngày-người, 1–4 giờ máy (pilot 2.000 clip × 3 giây).
**Chặn bởi:** chọn variant VideoMamba; taxonomy hành vi thi.

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| Đúng miền, P1 | OEP | Nhãn hành vi theo thời gian (cần audit schema) |
| Ngoài miền, P1 | Charades | 157 lớp, multi-label; chọn lớp liên quan |
| P2 | AVA Actions | Crop người, adapt head |
| P3 | Cheatomaly | Thi tại lớp, xin tác giả |
| Đúng miền | Drive sau annotation | |

### Các bước
1. **P0:** khóa variant + checkpoint (Kinetics pretrained), số frame/clip, stride, resolution. Đo VRAM + clip/s trên 3060.
2. **P1:**
   - OEP: cắt clip 3 giây có overlap (vd. stride 1,5 s), gán nhãn clip từ interval; split **theo người**.
   - Chốt taxonomy hành vi mục tiêu (với tay, rời chỗ, dùng đồ vật, nói chuyện, ...) + lớp "bình thường" + lớp dễ nhầm (gãi đầu, chỉnh tư thế, nhặt đồ).
   - Charades: chọn subset lớp liên quan, giữ official split.
3. **P2:** Charades mAP (multi-label, official) với linear probe/head để xác nhận feature tốt.
4. **P3:**
   - Train **linear probe/head** trên embedding đóng băng (OEP train) → đánh giá val: recall từng lớp, macro-recall, macro-F1, PR-AUC.
   - Event recall khi gộp clip thành event (quy tắc gộp chốt trước).
   - Slice: hành vi ngắn hơn 3 giây, hành vi kéo dài, nhiều người.
   - Xuất embedding cho fusion; ghi shape thực (Model List ghi 128D — chưa xác minh).
5. **P4:** nếu head chưa đủ → mở dần các block cuối của backbone (partial fine-tune) khi có đủ video độc lập; so trước/sau trên cùng split. Chọn threshold theo lớp trên val để recall ≥ 95%.
6. **P5:** locked test; xuất `actions.parquet` (session, clip_start, clip_end, class_scores) + cache embedding.

### Tiêu chí
- Recall từng lớp mục tiêu **≥ 95%**; macro-F1 **≥ 0,80** (phụ). Clip accuracy không thay event recall.

---

## Module 7 — VAD (phát hiện tiếng nói)

**Công dự kiến:** 1–2 ngày-người + phần chuẩn hóa audio dùng chung 3–5 ngày-người (AMI + VoxConverse, dùng chung cho 7–9, không cộng 3 lần). 0,5–2 giờ máy (pilot 5 giờ audio).
**Implementation:** pyannote `segmentation-3.0` (chính) + Silero VAD (so sánh / hợp) — xem mục 2.1.
**Chặn bởi:** xin quyền gated model trên Hugging Face.

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| P1 | AMI | Hợp các đoạn speaker = speech |
| P1 | VoxConverse v0.3 | RTTM đã sửa, khóa version |
| P2 | AVA Speech | Speech trong noise/music, **chỉ VAD** |
| P2 | CHiME-6, AliMeeting, DIHARD III (LDC) | |
| Đúng miền | OEP audio / Drive sau gán nhãn speech | |

### Các bước — chuẩn hóa audio dùng chung (làm một lần cho 7, 8, 9)
1. Tải AMI (chọn kênh gần webcam nhất, vd. single distant mic), VoxConverse v0.3; ghi checksum.
2. Chuẩn hóa **mono 16 kHz**; xuất RTTM thống nhất cho mọi corpus.
3. Từ RTTM sinh 3 loại nhãn: speech (hợp), overlap (giao ≥ 2 speaker), per-speaker timeline.
4. Chốt quy tắc: pause tối thiểu để tách segment, xử lý ho/cười/vocalization, UEM scoring region.
5. Tách enrollment (cho TS-VAD) khỏi vùng chấm điểm ngay từ bước này.
6. Nghe thử 3–5 phiên để kiểm tra nhãn khớp audio.

### Các bước VAD
1. **P0:** khóa version `pyannote.audio`, revision `segmentation-3.0`, version Silero VAD; khóa onset/offset threshold, `min_duration_on/off`, padding. Chạy thử 1 file OEP, so timeline hai VAD bằng mắt. Đo RTF trên GPU (pyannote) và CPU (Silero).
2. **P2:** chạy AMI + VoxConverse test (in-domain với pyannote) **và** LibriCSS/CHiME-6/AVA Speech (ngoài tập train): duration recall, event recall, precision, false-positive seconds/hour.
3. **P3:**
   - Slice: nói nhỏ, nói xa, câu ngắn, tiếng Việt/Anh, speech trong noise (AVA Speech).
   - Đối chứng: gõ phím, quạt, ho, âm phòng.
   - Trên OEP/Drive (khi có nhãn).
4. **P4:** so 3 cấu hình trên val: pyannote, Silero, pyannote OR Silero. Hạ threshold + tăng padding đến khi duration recall ≥ 98%; ghi precision tương ứng. Không được "luôn trả speech". Fine-tune chỉ khi calibration không giải quyết lỗi chuyển miền.
5. **P5:** locked test; xuất `vad.rttm` + probability timeline. **Đây là gate cho 8, 9** — ghi lại lượng speech bị cắt.

### Tiêu chí
- Speech duration recall **≥ 98%**; precision **≥ 90%** (phụ). Báo riêng event ngắn/nói nhỏ.
- VAD không đo dB: "nhẩm quá to" cần đo mức âm riêng.

---

## Module 8 — OSD (phát hiện nói chồng)

**Công dự kiến:** 2–3 ngày-người, 0,5–2 giờ máy (cùng 5 giờ audio).
**Implementation:** pyannote `segmentation-3.0`, pipeline `OverlappedSpeechDetection` — dùng lại cùng output forward của Module 7, gần như không tốn thêm GPU.
**Chặn bởi:** Module 7 (cho chế độ end-to-end).

### Dữ liệu
AMI, VoxConverse v0.3 (P1); AliMeeting, CHiME-6, LibriCSS, DIHARD III (P2). **Không** dùng AVA Speech (không có số speaker).

### Các bước
1. **P0:** khóa cùng version/revision như Module 7; khóa onset/offset và min overlap duration. Lưu output powerset gốc để tái dùng cho Module 9.
2. **P2 – độc lập:** chạy trên **toàn timeline** (không qua VAD): overlap duration recall, precision, F1, F2.
3. **P3 – end-to-end:** chạy sau VAD của Module 7; đoạn bị VAD cắt vẫn tính FN. So độc lập vs end-to-end.
   - Slice: độ dài overlap (< 0,5 s, 0,5–2 s, > 2 s), chênh âm lượng giữa 2 người.
   - Đối chứng: hai người nói nối tiếp, một giọng + nhạc/noise.
4. **P4:** chỉnh threshold trên val cho recall ≥ 95%; fine-tune theo lỗi thực (vd. AliMeeting/CHiME-6 cho overlap khó).
5. **P5:** locked test; xuất `osd.rttm`.

### Tiêu chí
- Overlap recall **≥ 95%**; F1 **≥ 0,80** (phụ).

---

## Module 9 — TS-VAD (tiếng nói của thí sinh vs người khác)

**Công dự kiến:** 3–5 ngày-người, 1–4 giờ máy. LibriCSS thêm 1–2 ngày-người chuẩn bị.
**Implementation:** bước 1 baseline segmentation-3.0 + WeSpeaker ResNet34-LM so với enrollment; bước 2 AED-TSVAD nếu baseline hụt — xem mục 2.1.
**Chặn bởi:** Module 7; protocol enrollment (độ dài check-in, cách thu).

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| P1 | LibriCSS | Enrollment dùng `unused_uttid` (khuyến nghị của tác giả) |
| P1 | AMI | Tự dựng enrollment tách khỏi vùng test |
| P2 | AliMeeting, CHiME-6, VoxConverse, DIHARD III | Cần dựng protocol |
| Hỗ trợ | VoxCeleb1/2 | Chỉ cho speaker embedding/enrollment, không làm test |
| Đúng miền | OEP/Drive: check-in voice + phiên thi | |

### Các bước
1. **P0:** khóa revision WeSpeaker ResNet34-LM; độ dài enrollment (không ép 3 giây; đề xuất thử 10 s, 20 s, 30 s check-in). Viết baseline:
   - lấy speaker cục bộ từ output powerset của Module 7/8 trên cửa sổ 10 s;
   - trích embedding từng speaker cục bộ (bỏ vùng overlap khi trích), cosine với embedding enrollment;
   - gán target nếu cosine ≥ ngưỡng, non-target nếu thấp hơn, im lặng nếu không có speech.
   Đồng thời clone AED-TSVAD, đọc license và kiểm tra có nhận profile ngoài không — chỉ ghi nhận, chưa chạy.
2. **P1:** LibriCSS: tạo enrollment từ `unused_uttid`; AMI: lấy enrollment từ đoạn đầu hoặc phiên khác của cùng speaker, loại speaker thiếu enrollment. Speaker ID trong một recording không coi là danh tính toàn cục.
3. **P2:** target-speech recall/F1; non-target recall (nếu có output); confusion duration; DER nếu làm đủ diarization.
4. **P3:**
   - Kịch bản: giọng check-in, người lạ, đổi mic, target + người khác cùng lúc.
   - Đối chứng: im lặng, target không nói (phân biệt im lặng vs non-target speech), audio playback (chưa có module xử lý — chỉ ghi nhận).
   - End-to-end sau VAD.
5. **P4:** chỉnh ngưỡng cosine trên val; báo tỷ lệ nhận nhầm giọng khác thành target. Nếu baseline không đạt target recall ≥ 95% hoặc nhầm > 5%, chuyển sang bước 2: chạy AED-TSVAD với enrollment làm profile, so trên cùng split; fine-tune chỉ khi có lỗi chuyển miền rõ.
6. **P5:** locked test; xuất `tsvad.rttm` (target / non-target / silence) + embedding audio cho fusion.

### Tiêu chí
- Target-speech recall **≥ 95%**; target F1 **≥ 0,90**; nhận nhầm non-target thành target **≤ 5%** thời lượng non-target speech.
- Target không hoạt động ≠ có người lạ nói.

---

## Module 10 — CHEESE-style graph fusion / MIL

**Công dự kiến:** 5–8 ngày-người, 0,5–2 giờ máy inference (pilot cache 2.000 clip + event labels). Phần fusion/head **có thể phải train từ đầu** — chưa gồm trong ngân sách.
**Chặn bởi:** cache feature của Module 3, 4, 5, 6, 7–9; taxonomy event; quy tắc event matching.

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| Đúng miền, P1 | OEP (event labels, split theo người) | |
| Kiểm tra thuật toán MIL | UCF-Crime | Re-extract feature bằng backbone của pipeline |
| P2 | ShanghaiTech | Tạo validation riêng, không chọn model trên test |
| P3 | Cheatomaly (nếu xin được), Drive sau nhãn event | |

### Các bước
1. **P0 – thiết kế:** khóa định nghĩa node (actor/object/face/audio), projection về cùng chiều, cạnh không gian–thời gian, mask cho modality thiếu. Checkpoint CHEESE **không** mặc nhiên tương thích với feature mới.
2. **P1 – cache feature:** chạy các module đã khóa trên OEP, lưu feature theo clip 3 giây với timestamp căn chỉnh + mask + quality state. Kiểm tra dimension và alignment trên vài clip bằng tay. Chỉ trích một lần, versioned.
3. **P2 – kiểm tra MIL:** chạy phần MIL trên UCF-Crime với feature re-extract; frame ROC-AUC để xác nhận implementation hoạt động (tham chiếu CHEESE 87,58% AUC trên OEP chỉ để so hướng, không phải mục tiêu).
4. **P3 – train + đánh giá trên OEP:**
   - Train fusion trên OEP train, chọn epoch/threshold trên val.
   - Metric: automatic event recall từng nhóm, precision, PR-AUC, F2, false alerts/giờ.
   - **Ablation:** bỏ từng nhánh (mặt, thân, audio, object) để xem nhánh nào đóng góp.
   - Kịch bản: bằng chứng nhiều nhánh cùng lúc, event ngắn, một modality yếu; đối chứng: tín hiệu lệch thời gian không được ghép, cue hợp lệ theo policy.
   - Temporal IoU 0,3 và 0,5 (độ nhạy).
5. **P4:** chọn operating point theo recall ≥ 95%/nhóm; vẽ đường precision/false-alerts/workload để người dùng chọn giới hạn workload.
6. **P5:** locked test; xuất `events.parquet` (session, t_start, t_end, type, actor, score, contributing_branches).

### Tiêu chí
- Automatic event recall **≥ 95%** mỗi nhóm mục tiêu. Precision ≥ 0,90 và FP ≤ 0,2/giờ chỉ là mốc tham khảo.

---

## Module 11 — SelectiveNet (quyết định + UNKNOWN)

**Công dự kiến:** 2–3 ngày-người, 0,5–2 giờ máy inference. Có phần học riêng.
**Chặn bởi:** Module 10 (feature/score); giới hạn workload giám thị.

### Dữ liệu
| Vai trò | Dataset | Ghi chú |
|---|---|---|
| Kiểm tra implementation | CIFAR-10 / SVHN (repo tác giả) | Chỉ xác nhận code đúng |
| Proxy decision | Mendeley 39xs8th543 (5.500 records) | Input bảng riêng, kiểm tra leak theo nhóm |
| Chính | OEP feature/event split (từ cache Module 10) | train / calibration / test tách biệt |
| P2 | UCF-Crime/ShanghaiTech feature; Cheatomaly nếu có | |

### Các bước
1. **P0:** khóa implementation, target coverage, λ loss.
2. **P2:** tái lập risk–coverage trên CIFAR-10 so với paper → xác nhận code.
3. **P2b – proxy:** chạy trên Mendeley CSV (split theo nhóm nếu có ID); báo là proxy, không nghiệm thu pipeline.
4. **P3 – chính:** train selective head trên feature OEP train; trên calibration: đường risk–coverage, automatic recall, **routing recall**, workload (phút/giờ thi) tại nhiều coverage. UNKNOWN phải kèm reason (mờ/mất mặt, mất audio, bằng chứng mâu thuẫn, chuyển miền).
5. **P4:** chọn coverage/threshold trên calibration set theo: automatic recall ≥ 95% và workload trong giới hạn đã chốt. Nếu không đạt đồng thời → báo trade-off, kết luận "needs revision", không giấu FN dưới UNKNOWN.
6. **P5:** locked test; xuất `decisions.parquet` (event, class, selection_score, decision ∈ {positive, negative, UNKNOWN}, reason).

### Tiêu chí
- End-to-end automatic event recall **≥ 95%**; báo routing recall riêng; selective error **≤ 5%** @ coverage **≥ 80%** là điểm tham khảo.
- Không bỏ ca dương khỏi mẫu số recall.

---

## Module 12 — Đánh giá end-to-end (locked test toàn hệ thống)

**Chặn bởi:** mọi module đã qua P5 và pipeline đã khóa.

1. Khóa toàn bộ: commit, checkpoint, threshold, quy tắc event, taxonomy. Ghi pre-registration (protocol viết trước khi chạy).
2. Chuẩn bị locked test: người/phiên/thiết bị **chưa dùng** ở bất kỳ module nào; nhãn event + actor đầy đủ; thời lượng âm tính được chú giải đầy đủ.
3. Chạy pipeline end-to-end trên video + audio thô (không dùng crop/segment GT).
4. Báo cáo:
   - automatic event recall, routing recall, precision, F2, false alerts/giờ, workload — theo từng loại event;
   - lỗi truyền từ upstream (mất mặt, VAD cắt speech) → bao nhiêu FN cuối đến từ đâu;
   - identity events (AdaFace) báo riêng;
   - 95% CI bootstrap theo người/phiên; số người, phiên, event dương, giờ âm tính;
   - thời gian máy thực, VRAM, RTF toàn pipeline trên 1–2 RTX 3060.
5. Kết luận theo ba mức: **đạt / không đạt / chưa đủ dữ liệu**.

---

## 13. Gói bàn giao sau mỗi module (checklist)

Theo capacity.md §7.4, mỗi `experiments/<module>/<final_exp>/` phải có:

- [ ] config.yaml: model, commit, checkpoint sha256
- [ ] dataset version, manifest, split files, label schema
- [ ] preprocessing mô tả đủ để tái lập
- [ ] threshold đã khóa + cách chọn (trên split nào)
- [ ] predictions theo sample/event
- [ ] metrics.json: metric + support từng lớp, CI
- [ ] confusion matrix / PR curve
- [ ] timing (model-only + end-to-end), peak VRAM, RAM
- [ ] error slices + 10–20 ví dụ lỗi đại diện
- [ ] kết luận: dùng pretrained / chỉ calibrate / fine-tune + lý do

---

## 14. Tóm tắt công và máy (pilot, chưa gồm annotation, tải toàn bộ, fine-tune)

| # | Module | Ngày-người | Giờ máy | Phụ thuộc |
|---|---|---:|---:|---|
| 0 | Step 0 chung | 2–3 | – | – |
| 1 | Face detect/track | 2–3 | 1–3 | – (SCRFD + ByteTrack) |
| 2 | AdaFace | 2–3 | 0,5–2 | 1 |
| 3 | 6DRepNet | 1–2 | 0,5–2 | 1 |
| 4 | L2CS-Net | 2–3 | 0,5–2 | 1 |
| 5 | Co-DETR | 3–5 | 1–4 | chọn config |
| 6 | VideoMamba | 3–5 | 1–4 | taxonomy |
| 7 | VAD (+ audio chung 3–5) | 1–2 | 0,5–2 | quyền gated HF |
| 8 | OSD | 2–3 | 0,5–2 | 7 |
| 9 | TS-VAD | 3–5 | 1–4 | 7 |
| 10 | Fusion | 5–8 | 0,5–2 | 3–9 |
| 11 | SelectiveNet | 2–3 | 0,5–2 | 10 |
| 12 | End-to-end | chưa ước tính | chưa ước tính | 1–11 |
| | **Tổng (1–11, theo capacity.md)** | **26–42** | **7,5–29** | |

Sau khi đo throughput thật ở P0 mỗi module, thay các khoảng trên bằng công thức capacity.md §6.3.
