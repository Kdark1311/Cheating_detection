# Đề xuất hệ thống và research questions

Ngày lập: 2026-11-16. **Bản đề xuất để duyệt**, chưa chốt. Các bước thực nghiệm chi tiết: [experiment_plan.md](experiment_plan.md).

## 1. Ý tưởng chính

**Bộ dữ liệu là trung tâm.** Nhóm tự quay một bộ dữ liệu thi thử gồm 3 camera và audio, có kịch bản gian lận và có nhóm làm bài trung thực. Các nhánh phân tích dùng model có sẵn, chạy trên bộ dữ liệu đó để trả lời research question. Đóng góp chính của paper là bộ dữ liệu + kết quả đo, không phải model mới.

Phạm vi thi (đã chốt 2026-11-08): kiểu IELTS Listening/Reading/Writing trong Safe Exam Browser, không giấy nháp, phòng đóng cửa, trên bàn chỉ có laptop + chuột + bàn phím. Xử lý **offline** sau buổi thi. Hệ thống **hỗ trợ giám thị**, không tự kết tội.

## 2. Hệ thống

```text
 Check-in (trước giờ thi)                      Trong giờ thi
 ─────────────────────────                     ─────────────────────────────
 ảnh mặt  ─┐                                   C1 webcam laptop ─┐
 20 s giọng ├─► hồ sơ thí sinh                 C2 điện thoại bên ├─► đồng bộ ─► các nhánh
 nhìn 4 góc ┘   (enrollment)                   C3 điện thoại phòng│   (bíp)
 màn hình                                      mic laptop + phone ┘

 Nhánh            Camera   Mô hình có sẵn (dự kiến)                Sự kiện xuất ra
 ───────────────  ───────  ─────────────────────────────────────  ───────────────────────────
 face/identity    C1       SCRFD + AdaFace                         identity_mismatch, face_missing
 face/gaze+head   C1       L2CS-Net + 6DRepNet + hiệu chỉnh 4 góc  look_away
 desk             C2       MediaPipe Hands + detector nhẹ (YOLO)  hand_off_desk, object (phone/paper/earphone)
 scene            C3       detector người                         extra_person, door_activity
 audio            mic      Silero/pyannote VAD + WeSpeaker         other_voice

                       ▼ tất cả về một định dạng: events.csv
      session, branch, label, start_s, end_s, score, evidence_path

 fusion (luật):  ≥ 2 nhánh độc lập trùng khoảng thời gian, hoặc 1 sự kiện mạnh
                 (extra_person, identity_mismatch, object=phone)  → NGHI GIAN LẬN
                 1 sự kiện yếu đơn lẻ (look_away, other_voice)   → GIÁM THỊ XEM LẠI
                 không có gì                                      → BÌNH THƯỜNG

 report: timeline + clip ngắn của từng cờ (xem/nghe được) cho giám thị
```

Nguyên tắc:
- **Mỗi nhánh chỉ xuất sự kiện có thời gian + độ tin cậy + đường dẫn bằng chứng.** Không nhánh nào tự kết luận gian lận.
- **Fusion bằng luật trước.** Chỉ học fusion bằng model (MIL, graph) khi luật đã được đo và thấy hụt.
- **Mất tín hiệu** (mất mặt, camera tắt, mất audio) là một sự kiện riêng có lý do, không coi là "bình thường".
- **Bỏ so với v1:** VideoMamba, CHEESE graph fusion, SelectiveNet, Co-DETR (đổi sang detector nhẹ), OSD/TS-VAD, dựng phòng 3D. Lý do: chưa có dữ liệu để train và chưa có câu hỏi nào cần. Thêm lại khi có lý do.

## 3. Bộ dữ liệu

| Mục | Đề xuất |
|---|---|
| Người tham gia | Pilot 3–5 người → bản chính 20–30 người, có giấy đồng ý, xin phê duyệt đạo đức của trường nếu có |
| Mỗi người | 1 buổi trung thực + 1 buổi theo kịch bản gian lận, mỗi buổi 20–30 phút |
| Kịch bản gian lận | điện thoại trên đùi / dưới bàn phím, giấy giấu, tai nghe, người nhắc ở cửa (nói vọng vào), người vào phòng, màn hình thứ hai, đổi người làm bài |
| Hành vi vô tội (dễ báo nhầm) | nhẩm bài, nhìn lên suy nghĩ, gãi đầu, cúi nhặt đồ, uống nước, người nhà nói ngoài hành lang |
| Red team | vài người được xem sơ đồ camera trước, tự nghĩ cách né |
| Nhãn | khoảng thời gian + loại sự kiện + ai làm, gán trên timeline nhiều luồng (công cụ dự kiến: ELAN) |
| Chia tập | theo **người**, không theo khung hình; tập test khóa, chỉ chạy một lần |

## 4. Research questions

Mỗi RQ có file chi tiết + nguồn đọc trong [research/](research/).

### Đặt camera — [research/camera-position.md](research/camera-position.md) (đã viết)
- **RQ-C1** Vị trí nào của C2, C3 cho coverage vùng trọng yếu cao nhất? Vùng nào vẫn là góc chết?
- **RQ-C2** Ở vị trí đó, model có sẵn còn nhận ra tay / vật / người không (đánh đổi phủ rộng và độ rõ)?
- **RQ-C3** Vị trí tối ưu có bắt được nhiều kịch bản hơn rule template và chỉ-webcam không, kể cả khi red team biết vị trí camera?

### Mặt — `research/face.md` (viết sau khi duyệt)
- **RQ-F1 Xác minh liên tục:** so mặt suốt bài thi với ảnh check-in, phát hiện đổi người trong bao lâu? Độ chính xác giảm bao nhiêu khi cúi mặt, thiếu sáng, webcam kém?
- **RQ-F2 Nhìn trong / ngoài màn hình:** hiệu chỉnh riêng từng thí sinh (nhìn 4 góc lúc check-in) có hơn model chung không? Gaze có thêm gì so với chỉ head pose?
- **RQ-F3 Ngưỡng bất thường:** nhìn ra ngoài bao lâu, hướng nào thì tách được người gian lận khỏi người trung thực đang suy nghĩ? Đo trên nhóm trung thực của bộ dữ liệu.

### Audio — [research/audio.md](research/audio.md) (đã viết)
- **RQ-A1** VAD + so giọng với enrollment bắt được bao nhiêu % `other_voice` ở mức cảnh báo sai cho phép?
- **RQ-A2** Hỏng ở điều kiện nào (qua cửa, thì thầm, câu ngắn, chồng tiếng nhẩm, bài Listening qua loa)?
- **RQ-A3** Thêm audio vào hình ảnh bắt thêm được kịch bản nào?

### Toàn hệ thống
- **RQ-S1** So với chỉ webcam laptop, 3 camera + audio + fusion luật tăng event recall bao nhiêu ở cùng mức cảnh báo sai/giờ?
- **RQ-S2** Bỏ từng nhánh (face, desk, scene, audio) thì mất bao nhiêu? Nhánh nào đáng tiền nhất?
- **RQ-S3** Mỗi giờ thi giám thị phải xem lại bao nhiêu phút? Bao nhiêu % cờ là báo nhầm do hành vi vô tội?

Nhánh desk và scene không có RQ riêng: dùng model có sẵn, được đánh giá qua RQ-C2 và RQ-S2.

**Chỉ số chung cho mọi RQ:** event recall (bắt được bao nhiêu % sự kiện thật), false alerts/giờ, phút xem lại/giờ thi, tách theo kịch bản; khoảng tin cậy bootstrap theo người.

## 5. Paper dự kiến

| Paper | Trả lời | Nơi nộp (xem lại hạn chính thức) |
|---|---|---|
| Bộ dữ liệu + hệ thống | RQ-C1–C3, RQ-S1–S3, kết quả cơ sở của F, A | **WACV 2028 Applications** (CORE A, dự kiến ~8/2027); dự phòng ICMI / ICIP |
| Audio `other_voice` | RQ-A1–A2 | ICASSP 2028 (~9/2027) hoặc Interspeech 2028 (~2/2028) |
| Mặt trong phòng thi | RQ-F1–F3 | FG 2028 / IJCB (CORE B), tùy kết quả |

## 6. Thứ tự làm

| Giai đoạn | Việc | Ra được |
|---|---|---|
| 0 (11–12/2026) | Đọc tài liệu cho RQ-C, A, F (nhẹ, vì thi cuối kỳ + SOICT) | bảng literature review mỗi nhánh |
| 1 (1/2027) | Giả lập đặt camera (RQ-C1); viết danh sách kịch bản; giấy đồng ý | vị trí C2/C3 + kịch bản |
| 2 (2–3/2027) | Quay pilot 3–5 người; viết `io` (đồng bộ bíp) + chạy từng nhánh bằng model có sẵn | events.csv đầu tiên, sửa kịch bản |
| 3 (4–6/2027) | Quay bản chính 20–30 người; gán nhãn | bộ dữ liệu v1 |
| 4 (6–8/2027) | Fusion luật, ablation, đo; viết paper | bản nộp WACV 2028 |

## 7. Khung repo

```text
docs/            proposal.md (file này), experiment_plan.md, research/<nhánh>.md
data/            không commit: raw/ (video, audio gốc), annotations/, splits/
src/cheating_detection/
  io/            đọc video/audio, đồng bộ bằng bíp, ghi/đọc events.csv
  placement/     giả lập phòng + ray casting cho RQ-C1
  face/  desk/  scene/  audio/      mỗi nhánh: luồng vào → events
  fusion/        luật ghép sự kiện
  eval/          event recall, false alerts/giờ, bootstrap
experiments/     mỗi lần chạy: <RQ>/<ngày>_<tên>/ gồm config + metrics (không chứa dữ liệu nặng)
scripts/         lệnh chạy từ đầu đến cuối
tests/           test cho io, eval, fusion
paper/           bản thảo
```

## 8. Cần bạn quyết

1. Đồng ý cắt các phần ở mục 2 không?
2. Nhánh mặt bạn tự làm hay bạn khác trong nhóm làm?
3. Bài Listening phát qua loa hay tai nghe?
4. Trường có hội đồng đạo đức / mẫu giấy đồng ý cho nghiên cứu có người tham gia không?
