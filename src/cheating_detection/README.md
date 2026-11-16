# src/cheating_detection/

Code của hệ thống. Mỗi thư mục con là một bước trong pipeline, giao tiếp với nhau qua file `events.csv` (định dạng ở [docs/experiment_plan.md](../../docs/experiment_plan.md) mục 0.3).

```text
data/raw ──► io (đồng bộ) ──► face / desk / scene / audio ──► events.csv ──► fusion ──► report
                                                                   │
                                          data/annotations ──► eval ◄┘
placement: chạy riêng, trước khi quay, để chọn vị trí camera
```

| Thư mục | Làm gì | Vào | Ra | RQ |
|---|---|---|---|---|
| `io/` | Đọc video/audio; tìm tiếng bíp để đồng bộ các thiết bị; đọc/ghi `events.csv` và nhãn | `data/raw/<session>/` | luồng đã đồng bộ | – |
| `placement/` | Mô hình phòng 3D đơn giản + ray casting, chấm điểm vị trí camera | kích thước phòng, vị trí thử | coverage từng vùng | C1 |
| `face/` | C1 webcam: phát hiện + theo dõi mặt, xác minh danh tính, head pose, gaze | video C1 + ảnh check-in + hiệu chỉnh 4 góc | `identity_mismatch`, `face_missing`, `look_away` | F1–F3 |
| `desk/` | C2 cạnh bàn: tay, điện thoại, giấy, tai nghe | video C2 | `hand_off_desk`, `object` | C2 |
| `scene/` | C3 quay phòng: người thứ hai, hoạt động ở cửa | video C3 | `extra_person`, `door_activity` | C2 |
| `audio/` | VAD + so giọng với enrollment | audio + 20 s giọng check-in | `other_voice` | A1–A2 |
| `fusion/` | Ghép sự kiện các nhánh bằng luật → nghi gian lận / xem lại / bình thường | `events.csv` mọi nhánh | kết luận theo đoạn | S1–S3 |
| `eval/` | Ghép sự kiện dự đoán với nhãn; event recall, false alerts/giờ, phút xem lại/giờ, bootstrap CI | `events.csv` + nhãn | `metrics.json` | mọi RQ |

Quy tắc:
- Một nhánh không import nhánh khác; chỉ dùng chung `io` và `eval`.
- Nhánh **không** tự kết luận gian lận, chỉ xuất sự kiện + độ tin cậy + đường dẫn bằng chứng.
- `io`, `eval`, `fusion` phải có test trong `tests/`.

Trạng thái: mới có khung (mỗi thư mục chỉ có `__init__.py` ghi nhiệm vụ).
