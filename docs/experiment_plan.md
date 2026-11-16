# Kế hoạch thực nghiệm

Ngày lập: 2026-11-16 (v2). Dựa trên [proposal.md](proposal.md). Bản v1 (2026-09-28, 12 module) xem bằng `git show 6e76b38:experiment_plan.md`.

Trạng thái: chưa quay dữ liệu, chưa chạy model. Mọi ngưỡng bên dưới là **mục tiêu đặt trước** (pre-registered), chỉnh sau literature review, không phải kết quả.

---

## 0. Quy tắc chung

### 0.1 Vòng 6 pha cho mỗi thí nghiệm

| Pha | Việc | Qua pha khi |
|---|---|---|
| P0 Khóa cấu hình | Chốt repo, commit, checkpoint + sha256, preprocessing, ngưỡng ban đầu | Chạy được 1 mẫu, lưu ảnh/âm thanh overlay để xem bằng mắt/tai |
| P1 Dữ liệu | Tải, checksum, manifest, chuyển nhãn, chia tập theo người | File split đã đóng băng |
| P2 Tái lập benchmark | Chạy checkpoint gốc trên benchmark công khai đúng protocol | Lệch so với số công bố nằm trong mức giải thích được |
| P3 Đúng miền | Chạy trên dữ liệu tự quay, tách theo điều kiện khó (slice) | Có bảng lỗi theo slice |
| P4 Hiệu chỉnh | Chọn ngưỡng trên val; fine-tune **chỉ khi** P3 chỉ ra lỗi cụ thể | So trước/sau trên cùng split |
| P5 Locked test | Chạy **một lần** trên tập test khóa, đóng gói (mục 7) | Kết luận: đạt / không đạt / chưa đủ dữ liệu |

### 0.2 Quy tắc đánh giá

- Chia tập theo **người**, không theo khung hình hay clip. Một người chỉ nằm trong một tập.
- Tập test khóa không dùng để chọn ngưỡng hay model.
- Mọi kết quả ghi rõ **đơn vị** (khung, giây, sự kiện, buổi), số người, số buổi, số sự kiện dương, số giờ âm tính.
- **95% CI bootstrap theo người.**
- Mất tín hiệu (mất mặt, camera tắt, mất audio) phải có cờ + lý do, không tự coi là âm tính.
- Đo riêng **model-only** và **end-to-end** (gồm decode, đồng bộ, IO).

### 0.3 Định dạng sự kiện chung

Mọi nhánh xuất `events.csv`, mọi bước đánh giá đọc file này:

```text
session_id, branch, label, start_s, end_s, score, evidence_path
```

Nhãn ground truth (`data/annotations/<session_id>.csv`): `session_id, label, actor, start_s, end_s`.

### 0.4 Chỉ số

| Chỉ số | Nghĩa |
|---|---|
| **Event recall** | Số sự kiện thật được ghép với ≥ 1 cờ / tổng sự kiện thật |
| **False alerts/giờ** | Số cờ không ghép với sự kiện thật nào / số giờ thi |
| **Phút xem lại/giờ** | Tổng thời lượng clip giám thị phải xem / số giờ thi |
| Precision, F2 | Phụ; F2 ưu tiên recall |
| Theo slice | Mọi chỉ số tách theo kịch bản và điều kiện khó |

**Luật ghép sự kiện (đề xuất, cần chốt trước mọi locked test):** ghép một-một theo temporal IoU **≥ 0,3** (chỉ số chính), báo thêm IoU ≥ 0,5. Sự kiện ngắn hơn 1 giây được ghép nếu cờ phủ ≥ 50% thời lượng của nó.

### 0.5 Thẻ thí nghiệm

Mỗi lần chạy có `experiments/<RQ>/<yyyymmdd>_<tên>/config.yaml`: model, commit, checkpoint sha256, phiên bản dữ liệu, file split, preprocessing, ngưỡng, độ phân giải, FP16/FP32, GPU, seed. Kết quả nặng để trong `outputs/` (không commit).

---

## 1. Quyết định còn mở

| Quyết định | Chặn | Cần trước |
|---|---|---|
| Đồng ý cắt VideoMamba, CHEESE fusion, SelectiveNet, Co-DETR, OSD/TS-VAD, dựng phòng 3D | Toàn bộ kế hoạch | Ngay |
| Ai làm nhánh mặt | Lịch | Giai đoạn 1 |
| Bài Listening qua loa hay tai nghe | A2-f, kịch bản quay | Mục 3 |
| Hội đồng đạo đức + mẫu giấy đồng ý | Quay dữ liệu | Mục 3 (pilot) |
| Luật ghép sự kiện (mục 0.4) | Mọi P5 | Trước locked test |
| Detector cho bàn/phòng (license: Ultralytics YOLO là AGPL-3.0) | E-desk, E-scene | P0 của hai nhánh |

---

## 2. Thứ tự và phụ thuộc

```text
Giai đoạn 0  Đọc tài liệu (C, F, A)                       ──┐
Giai đoạn 1  [E-infra] io + eval + benchmark tốc độ          │
             [E-C1] giả lập đặt camera ──► vị trí C2, C3     │
             [E-D1] kịch bản + giấy đồng ý                   │
Giai đoạn 2  [E-D2] quay pilot 3–5 người                     │
             P0–P3 mọi nhánh trên pilot ◄────────────────────┘
             [E-C2] model ở góc camera đã chọn
Giai đoạn 3  [E-D3] quay bản chính 20–30 người + gán nhãn
             P4 mọi nhánh (val)
Giai đoạn 4  [E-S] fusion luật, ablation, P5 locked test ─► paper WACV 2028
```

Một GPU T4 (16 GB) là đủ: mọi model đều nhỏ và chạy offline. Chạy từng nhánh tuần tự, lưu `events.csv` + đặc trưng vào `outputs/` để fusion không phải chạy lại model.

---

## 3. E-infra — hạ tầng dùng chung (làm trước mọi nhánh)

Code trong `src/cheating_detection/io` và `eval`, có test trong `tests/`.

1. **Đồng bộ** (`io`): phát tiếng bíp (chuỗi tần số biết trước) lúc bắt đầu và kết thúc buổi; tìm vị trí bíp trong audio của từng thiết bị bằng cross-correlation; suy ra lệch thời gian + trôi đồng hồ (drift) giữa hai mốc.
   - Kiểm tra: vỗ tay giữa buổi, sai lệch sau đồng bộ **≤ 1 khung hình (33 ms)** trên buổi 30 phút.
   - Tham khảo: Ochi và cs. 2016 (xem [research/audio.md](research/audio.md)).
2. **Đọc/ghi** `events.csv` + nhãn ground truth; kiểm tra schema.
3. **Bộ đánh giá** (`eval`): event matching theo mục 0.4, event recall, false alerts/giờ, phút xem lại/giờ, bootstrap CI theo người. **Viết và test trước khi chạy nhánh đầu tiên** để mọi nhánh dùng chung một định nghĩa.
4. **Đo tốc độ**: thời gian thực / thời lượng video (RTF), peak VRAM, RAM; model-only và end-to-end.
5. **Report**: timeline + clip ngắn cho mỗi cờ (xem/nghe được), dùng cho giám thị và để tự kiểm tra kết quả bằng mắt.

---

## 4. E-D — bộ dữ liệu

### E-D1 Kịch bản và quy trình quay

1. Danh sách kịch bản (chỉnh sau khi đọc Atoum 2017, Bergmans 2021):

   | Nhóm | Kịch bản | Nhánh nên bắt |
   |---|---|---|
   | Gian lận | điện thoại trên đùi / dưới bàn phím | desk |
   | | giấy giấu dưới bàn phím | desk |
   | | tai nghe | face (C1), desk |
   | | người nhắc ở cửa, nói vọng vào | audio, scene |
   | | người vào phòng | scene |
   | | màn hình thứ hai, nhìn ra ngoài đọc | face (gaze), scene |
   | | đổi người làm bài | face (identity) |
   | Vô tội | nhẩm bài, nhìn lên suy nghĩ, gãi đầu, cúi nhặt đồ, uống nước | không được báo |
   | | người nhà nói ngoài hành lang (không nhắc bài) | audio báo → giám thị xem lại |
   | Red team | biết sơ đồ camera, tự nghĩ cách né | – |

2. Quy trình một buổi: đặt camera theo hướng dẫn (từ E-C1) → kiểm tra preview → **check-in** (ảnh mặt, đọc 20 s văn bản, nhìn 4 góc màn hình) → bíp → làm bài 20–30 phút → bíp kết thúc.
3. Mỗi người: 1 buổi trung thực + 1 buổi theo kịch bản. Thứ tự kịch bản xáo trộn giữa người.
4. Giấy đồng ý: nêu rõ quay mặt, tay, phòng, giọng; mục đích; thời gian lưu; có công bố dữ liệu hay không (công bố cần đồng ý riêng).

### E-D2 Pilot (3–5 người)

- Quay đủ quy trình, đo: tỷ lệ buổi hỏng (thiếu luồng, mất đồng bộ), thời gian setup mỗi người, dung lượng lưu trữ / buổi.
- Gán nhãn thử 10 phút video, đo **công gán nhãn / giờ video** để ước lượng bản chính.
- Sửa kịch bản và hướng dẫn đặt camera theo lỗi gặp phải.

### E-D3 Bản chính (20–30 người)

- Gán nhãn theo `data/annotations` (công cụ dự kiến: ELAN, xem nhiều luồng cùng timeline).
- **Hai người gán độc lập** trên ≥ 10% số buổi; báo độ đồng thuận (event F1 giữa hai người gán).
- Chia `train / val / test` theo người, khoảng 50 / 20 / 30. Đóng băng `data/splits/`.
- Dữ liệu công khai dùng thêm: OEP (Atoum 2017), Roboflow Online Proctoring v1 và Mendeley mjrfmvsh7d (kiểm trùng ảnh giữa train/test và có ID người hay không).

---

## 5. Thí nghiệm theo nhánh

### E-C — đặt camera ([research/camera-position.md](research/camera-position.md))

**E-C1 — Giả lập coverage (RQ-C1).** Code: `src/cheating_detection/placement`.
1. P0: mô hình phòng hộp + bàn + người ngồi + laptop (kích thước đo từ 3 phòng thật). Định nghĩa vùng trọng yếu bằng điểm lấy mẫu 3D + trọng số. Định nghĩa "thấy được": trong FOV, không bị chắn (ray casting, Open3D), đủ **pixel/vật** (ngưỡng lấy từ RQ-C2, tạm 32 px cho điện thoại).
2. Lưới vị trí: C2 (bên trái/phải × khoảng cách 0,4–1,0 m × độ cao 0,7–1,2 m × góc), C3 (4 góc phòng × độ cao 1,2–2,0 m × góc). Điện thoại phổ biến: FOV ngang ~65–80°, kiểm lại máy thật.
3. So: rule template vs vị trí tốt nhất theo từng phòng. Báo coverage từng vùng, vùng chỉ 1 camera thấy.
4. Độ nhạy: lệch ±20 cm, ±10° → coverage giảm bao nhiêu.
5. Kiểm chứng: quay thật ở 2–3 phòng, đánh dấu vùng thấy được trên ảnh, so với giả lập.

**E-C2 — Model ở góc đã chọn (RQ-C2).** Chạy trên pilot: tỷ lệ khung phát hiện được tay (MediaPipe), điện thoại (detector), người (C3) theo khoảng cách/góc; pixel trên vật. Trả về ngưỡng pixel cho E-C1 (lặp lại E-C1 nếu ngưỡng khác giả định).

**E-C3 — Có khó gian lận hơn không (RQ-C3).** Trên bản chính + red team: event recall theo kịch bản cho 3 cấu hình (chỉ C1 / rule template / vị trí tối ưu), số cách né red team tìm được. Cần quay cùng người với các cấu hình khác nhau, hoặc dùng 2 cấu hình song song nếu đủ điện thoại.

### E-F — mặt (C1)

**E-F0 — Phát hiện + theo dõi mặt** (đầu vào chung cho F1–F3; giữ lựa chọn v1).
- SCRFD-10G-KPS (InsightFace `buffalo_l`) + ByteTrack; nối lại track bằng similarity AdaFace.
- P2: WIDER FACE val (Easy/Medium/Hard). P3: face recall @ IoU ≥ 0,5, IDF1, số lần mất track; slice: cúi đầu, quay mặt, thiếu sáng, người thứ hai xuất hiện.
- Mục tiêu: face recall ≥ 95%, IDF1 ≥ 90%. Khung mất mặt vẫn tính trong mẫu số.
- Xuất: `face_tracks.parquet` (session, frame, track_id, box, score, landmarks, visibility).

**E-F1 — Xác minh danh tính liên tục (RQ-F1).**
- AdaFace IR-100 (ghi rõ checkpoint WebFace4M hay MS1MV2). Align 5 landmark → 112×112, kiểm 20 crop bằng mắt.
- P2: AgeDB-30, CFP-FP (evaluator AdaFace; AgeDB cần email xin mật khẩu, gửi sớm); LFW chỉ để kiểm evaluator. Độ bền chất lượng thấp: TinyFace (1:N, Rank-1/5).
- P3: enrollment = ảnh check-in; probe từ chính buổi thi. Chèn đoạn người khác vào buổi (giả lập đổi người) + kịch bản đổi người thật.
  - Chỉ số: TAR @ FAR = 0,1%; **event recall đổi người**; **độ trễ phát hiện** (giây từ lúc đổi đến lúc cờ); false alarm trên người thật/giờ.
  - Slice: cúi mặt, quay ngang, kính, thiếu sáng, webcam độ phân giải thấp.
- P4: ngưỡng similarity trên val; gộp theo cửa sổ k khung chất lượng tốt nhất; khung chất lượng thấp → `face_low_quality`, không quyết định.
- Mục tiêu: TAR ≥ 95% @ FAR ≤ 0,1%; event recall đổi người ≥ 95%, độ trễ ≤ 10 s. AdaFace không chống giả mạo ảnh/video (liveness); ghi là giới hạn.
- Xuất: sự kiện `identity_mismatch`, `face_missing`.

**E-F2 — Nhìn trong / ngoài màn hình (RQ-F2).**
- Head pose: 6DRepNet (checkpoint train 300W-LP). P2: AFLW2000-3D, BIWI (nếu không lấy được ảnh thì dùng Pandora). Kiểm quy ước trục yaw/pitch/roll trước. Mục tiêu tái lập: MAE ≤ 5° AFLW2000.
- Gaze: L2CS-Net (ghi rõ checkpoint MPIIGaze hay Gaze360). P2: MPIIFaceGaze leave-one-person-out, Gaze360 (ghi mask). Mục tiêu tái lập: ≤ 5° MPIIFaceGaze.
- P3 (chính):
  - Định nghĩa vùng nhìn **trước khi chấm**: màn hình / ngoài màn hình (trái, phải, lên, xuống bàn phím).
  - So 4 cấu hình: head pose / gaze / head + gaze / head + gaze + **hiệu chỉnh 4 góc màn hình lúc check-in** (học ánh xạ góc → vị trí trên màn hình cho từng người).
  - Chỉ số: recall + precision theo vùng, macro-F1, theo khung và theo sự kiện.
  - Slice: mắt liếc khi đầu đứng yên, đầu quay nhưng mắt vẫn nhìn màn hình, kính, chớp mắt, webcam thấp nhìn từ dưới lên.
- Mục tiêu: macro-F1 vùng nhìn ≥ 0,80; hiệu chỉnh cá nhân cải thiện có ý nghĩa (CI không chứa 0).
- Xuất: `gaze.parquet` (session, frame, yaw, pitch, roll, gaze_vec, region, quality).

**E-F3 — Ngưỡng bất thường (RQ-F3).**
- Trên buổi **trung thực** của train: phân bố thời lượng và hướng nhìn ra ngoài (người thật suy nghĩ nhìn đi đâu, bao lâu).
- Trên buổi gian lận: cùng phân bố cho kịch bản màn hình thứ hai / đọc tài liệu ngoài.
- Chọn luật `look_away` (vùng + thời lượng tối thiểu + số lần/phút) trên val; báo đường event recall – false alerts/giờ khi đổi ngưỡng.
- Xuất: sự kiện `look_away`.

### E-desk — tay và vật trên bàn (C2)

Không có RQ riêng; đánh giá qua E-C2 và E-S2.
1. P0: MediaPipe Hands; detector nhẹ (chốt ở mục 1) với lớp phone / paper / earphone. Khóa phiên bản, ngưỡng.
2. P3 trên pilot: recall tay theo khung; event recall vật thể theo kịch bản; slice: tay che vật, vật nhỏ, ánh sáng.
3. P4: nếu detector hụt với điện thoại nhìn nghiêng, fine-tune trên ảnh train của bộ dữ liệu (chia theo người) + Roboflow/Mendeley.
4. Luật: `hand_off_desk` (tay ra khỏi vùng bàn > t giây), `object` (vật lạ ≥ k khung liên tiếp).

### E-scene — bối cảnh phòng (C3)

1. P0: detector người (cùng detector của E-desk, lớp person).
2. Luật: `extra_person` (≥ 2 người ≥ k khung), `door_activity` (người/chuyển động trong vùng cửa đã đánh dấu lúc setup).
3. P3: event recall kịch bản người vào phòng / người ở cửa; false alerts (bóng, vật treo, gương, TV).

### E-A — audio ([research/audio.md](research/audio.md))

**E-A1 — VAD + so giọng (RQ-A1).**
1. P0: Silero VAD và pyannote `segmentation-3.0` (gated, cần token HF); WeSpeaker ResNet34 / ECAPA. Khóa phiên bản, ngưỡng.
2. Pipeline: VAD → cắt đoạn → embedding mỗi đoạn → cosine với enrollment 20 s → `other_voice` nếu dưới ngưỡng.
3. So 3 cấu hình: "có tiếng nói = cờ" / VAD + so giọng / (tùy chọn) kiểu Personal VAD.
4. Tách lỗi: VAD bỏ sót vs so giọng nhầm.
5. Mục tiêu: event recall ≥ 90% @ ≤ 2 false alerts/giờ.

**E-A2 — Điều kiện khó (RQ-A2).**
- Trước pilot: giả lập bằng LibriSpeech/VoxCeleb test + RIR (OpenSLR 28) + nhiễu MUSAN + lọc thấp (giọng qua cửa); dùng VOiCES, LibriCSS làm test ngoài.
- Trên dữ liệu thật: slice (a)–(g) theo research/audio.md; enrollment 10/20/30 s.
- Nếu Listening qua loa: thử loại tín hiệu tham chiếu đã biết (căn thời gian bằng cross-correlation rồi trừ / che đoạn).

**E-A3 → gộp vào E-S2** (ablation có/không audio).

---

## 6. E-S — fusion và toàn hệ thống

**E-S0 — Luật fusion** (`src/cheating_detection/fusion`):

| Kết luận | Điều kiện |
|---|---|
| Nghi gian lận | ≥ 2 nhánh độc lập có cờ trùng cửa sổ ±W giây, hoặc 1 sự kiện mạnh (`extra_person`, `identity_mismatch`, `object=phone`) |
| Giám thị xem lại | 1 sự kiện yếu đơn lẻ (`look_away`, `other_voice`, `hand_off_desk`, `door_activity`) hoặc mất tín hiệu |
| Bình thường | còn lại |

W và danh sách "mạnh/yếu" chọn trên val. Chỉ thử fusion học (vd. logistic regression trên đặc trưng sự kiện) nếu luật hụt rõ, và so trên cùng split.

**E-S1 (RQ-S1).** Event recall theo kịch bản ở cùng mức false alerts/giờ: chỉ C1 vs đầy đủ 3 camera + audio.

**E-S2 (RQ-S2, gồm RQ-A3).** Bỏ lần lượt face / desk / scene / audio; báo phần recall mất đi theo từng kịch bản.

**E-S3 (RQ-S3).** Phút xem lại/giờ; % cờ do hành vi vô tội; xem từng cờ sai để phân loại nguyên nhân.

**E-S4 — Locked test end-to-end.**
1. Khóa mọi commit, checkpoint, ngưỡng, luật; viết protocol trước khi chạy.
2. Chạy từ video + audio thô (không dùng nhãn ground truth ở bước nào).
3. Báo: event recall, false alerts/giờ, phút xem lại/giờ theo kịch bản; lỗi truyền từ upstream (mất mặt, VAD cắt tiếng, lệch đồng bộ) gây bao nhiêu sự kiện bị bỏ sót; CI bootstrap theo người; thời gian chạy trên T4.
4. Kết luận ba mức: **đạt / không đạt / chưa đủ dữ liệu**.

---

## 7. Gói bàn giao mỗi thí nghiệm

Mỗi `experiments/<RQ>/<thí nghiệm cuối>/` có:

- [ ] config.yaml (mục 0.5)
- [ ] phiên bản dữ liệu, file split, schema nhãn
- [ ] preprocessing đủ để tái lập
- [ ] ngưỡng đã khóa + chọn trên split nào
- [ ] `events.csv` dự đoán
- [ ] metrics.json: chỉ số + support + CI
- [ ] bảng theo slice + 10–20 ví dụ lỗi (clip/âm thanh)
- [ ] thời gian chạy model-only + end-to-end, peak VRAM, RAM
- [ ] kết luận: dùng pretrained / chỉ hiệu chỉnh / fine-tune + lý do

---

## 8. Ánh xạ RQ → thí nghiệm → paper

| RQ | Thí nghiệm | Paper |
|---|---|---|
| C1, C2, C3 | E-C1, E-C2, E-C3 | WACV 2028 |
| F1, F2, F3 | E-F0–E-F3 | WACV 2028 (kết quả cơ sở); FG/IJCB (bài riêng) |
| A1, A2 | E-A1, E-A2 | ICASSP 2028 / Interspeech 2028 |
| A3, S1, S2, S3 | E-S1–E-S4 | WACV 2028 |
| (bộ dữ liệu) | E-D1–E-D3 | WACV 2028 |
