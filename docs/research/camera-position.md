# Vị trí đặt camera: research questions và nguồn đọc

Ngày lập: 2026-11-16. Thứ tự làm giống nhánh audio: **research question → literature review → implement để trả lời câu hỏi**. Chưa có code.

## 1. Bài toán

Mỗi thí sinh có 3 camera, mỗi camera một việc:

| Camera | Thiết bị | Vị trí | Dùng cho |
|---|---|---|---|
| **C1 – mặt** | Webcam laptop | Cố định trước mặt (không chọn được) | Head pose (hướng đầu), eye gaze (hướng nhìn), xác minh danh tính |
| **C2 – tay & bàn** | Điện thoại 1 | Cạnh bên bàn (**cần tìm**) | Cử chỉ tay, vật thể trên bàn (điện thoại, giấy, tai nghe) |
| **C3 – bối cảnh** | Điện thoại 2 | Trong phòng (**cần tìm**) | Toàn phòng: cửa, sau lưng thí sinh, người thứ hai, màn hình laptop |

Mục tiêu: tìm vị trí (độ cao, khoảng cách, góc xoay) của **C2 và C3** sao cho **ít góc chết nhất** và **thí sinh khó gian lận nhất**.

Phác thảo nhìn từ trên xuống (chỉ là giả thuyết ban đầu, chưa phải kết quả):

```text
   ┌──────────────── tường ────────────────┐
   │                                C3 ◣   │  C3: góc phòng sau lưng chéo, cao ~1,8 m
   │                                       │      thấy cửa + lưng + màn hình
 cửa          [ ghế + thí sinh ]           │
   │          ┌───────────────┐            │
   │   C2 ▶   │ laptop  (C1)  │            │  C2: cạnh bàn, ngang/hơi cao hơn mặt bàn,
   │          └─── bàn ───────┘            │      chéo ~45° phía trước, thấy 2 tay + mặt bàn
   └───────────────────────────────────────┘
```

Bối cảnh đã chốt (2026-11-08): thi kiểu IELTS Listening/Reading/Writing trong Safe Exam Browser, không giấy nháp, trên bàn chỉ có laptop, chuột, bàn phím. Phòng đóng cửa, camera phải phủ cả phòng. Hai điện thoại quay bằng app của nhóm. Xử lý offline.

### Vùng cần nhìn thấy (vùng trọng yếu)

Góc chết chỉ đáng lo khi nó che **vùng trọng yếu**. Danh sách ban đầu (chỉnh sau khi đọc + thử):

| Vùng | Gian lận có thể xảy ra | Camera nên thấy |
|---|---|---|
| Hai tay + bàn phím + chuột | Cầm điện thoại, giấy giấu dưới bàn phím | C2 |
| Mặt bàn | Vật thể lạ | C2 (+C3) |
| **Đùi / dưới bàn** | Điện thoại trên đùi | C2 (khó nhất) |
| Màn hình laptop | Mở cửa sổ khác, màn hình thứ hai | C3 |
| Cửa ra vào | Người vào phòng, người nhắc ở cửa | C3 |
| Sau lưng thí sinh | Người đứng sau, giấy dán tường | C3 |
| Tai, mặt | Tai nghe | C1 (+C2 từ bên cạnh) |

## 2. Thuật ngữ

- **Góc chết (blind spot)**: chỗ trong phòng không camera nào thấy.
- **Coverage**: % vùng trọng yếu có ít nhất một camera thấy rõ. Có thể đòi "thấy bởi ≥ 2 camera" cho vùng quan trọng nhất.
- **Che khuất (occlusion)**: vật nằm trong khung hình nhưng bị cơ thể, laptop, bàn che mất.
- **Ray casting**: mô phỏng bằng máy tính: bắn "tia nhìn" từ camera, xem tia có chạm tới điểm cần thấy hay bị vật chắn. Dùng để tính coverage mà không cần quay thật.
- **FOV (field of view)**: góc nhìn của camera. Góc rộng thấy nhiều nhưng vật nhỏ đi.
- **Pixel trên vật thể**: một vật (vd. điện thoại) chiếm bao nhiêu pixel trong ảnh. Quá ít thì model không nhận ra (COCO coi vật < 32×32 pixel là "nhỏ", khó phát hiện).
- **Rule template**: cách đặt theo luật cố định cho mọi phòng (vd. "C2 đặt bên tay phải, cách 60 cm, cao ngang bàn").
- **Red team**: người được giao cố tình tìm cách gian lận mà không bị phát hiện.

## 3. Research questions

### RQ1 — Đặt ở đâu thì ít góc chết nhất?

**Câu hỏi:** Với một phòng học ở nhà điển hình (bàn sát tường hoặc giữa phòng, cửa ở các vị trí khác nhau), vị trí nào của C2 và C3 cho **coverage vùng trọng yếu** cao nhất? Vùng nào vẫn là góc chết dù đặt thế nào?

**Cách trả lời:** dựng mô hình phòng 3D đơn giản (hộp phòng + bàn + người ngồi + laptop), thử lưới vị trí (độ cao × góc × khoảng cách) cho C2, C3, tính coverage bằng ray casting. Sau đó quay thật ở 2–3 phòng để kiểm tra mô phỏng có khớp không.

**Giả thuyết H1:** C2 ở cạnh bàn, chéo ~45° phía trước, cao ngang hoặc hơi trên mặt bàn thấy được tay + mặt bàn nhưng thấy đùi kém. C3 ở góc phòng phía sau chéo, cao 1,6–2 m, phủ được cửa + lưng + màn hình. **Đùi/dưới bàn** là góc chết khó nhất.

**Câu phụ (độ lệch khi thí sinh tự đặt):** nếu thí sinh đặt lệch 20 cm hoặc 10° so với hướng dẫn, coverage giảm bao nhiêu? Cần dung sai lớn để người thường đặt được.

**Đo:** coverage từng vùng trọng yếu (%), số vùng chỉ có 1 camera thấy, coverage khi lệch vị trí.

### RQ2 — Ở góc đó, model còn hoạt động không?

**Câu hỏi:** Ở các vị trí tốt nhất của RQ1, ảnh có còn đủ tốt cho model có sẵn không: head pose + gaze trên C1 (webcam laptop nằm thấp, nhìn từ dưới lên), hand tracking + phát hiện vật thể trên C2 (nhìn nghiêng), phát hiện người trên C3 (góc rộng, vật nhỏ)? Thấy được (RQ1) chưa chắc là nhận ra được.

**Giả thuyết H2:** có đánh đổi giữa phủ rộng và độ rõ. C3 phủ cả phòng thì điện thoại trong ảnh quá nhỏ để phát hiện, nên C3 chỉ đáng tin cho "người thứ hai" và "cửa", còn vật nhỏ phải dựa vào C2. Gaze trên C1 kém khi thí sinh cúi nhìn bàn phím (góc đầu lớn).

**Đo:** số pixel trên tay/điện thoại ở mỗi vị trí; độ chính xác của từng model trên ảnh thật ở các góc khác nhau (vd. hand tracking phát hiện được bao nhiêu % khung có tay; object detector bắt được điện thoại ở mấy pixel trở lên).

### RQ3 — Đặt như vậy có thật sự khó gian lận hơn không?

**Câu hỏi:** So với (a) chỉ có webcam laptop và (b) cách đặt theo rule template đơn giản, vị trí tối ưu từ RQ1–2 có bắt được nhiều kịch bản gian lận hơn không? Khi người gian lận **biết trước** vị trí camera (red team), họ còn tìm được cách né không?

**Cách trả lời:** quay thử các kịch bản gian lận có kịch bản (điện thoại trên đùi, giấy dưới bàn phím, người nhắc ở cửa, màn hình thứ hai, tai nghe) và hành vi vô tội dễ báo nhầm (cúi nhặt bút, gãi đầu, nhìn ra cửa sổ). Giám thị (hoặc model) xem video từ từng cấu hình. Thêm vòng red team: cho người thử xem sơ đồ camera rồi tự nghĩ cách gian lận.

**Giả thuyết H3:** 3 camera tối ưu bắt được nhiều kịch bản hơn rõ rệt so với chỉ webcam; nhưng so với rule template thì chênh lệch nhỏ ở phòng bình thường, chỉ đáng kể ở phòng khó (chật, cửa sau lưng, cửa sổ ngược sáng). Nếu đúng vậy thì nên dùng **rule template + bước kiểm tra preview lúc check-in** thay vì tối ưu riêng từng phòng.

**Đo:** tỷ lệ bắt đúng theo từng kịch bản, số cách né red team tìm được, cảnh báo sai/giờ, phút giám thị phải xem lại/giờ thi.

## 4. Nguồn đọc theo từng RQ

Đã kiểm tra tên bài và link (2026-11-16). Đọc abstract + phần được ghi; chỉ đọc toàn văn khi cần.

### Cho RQ1 — đặt camera, coverage, góc chết

| # | Nguồn | Đọc để lấy gì |
|---|---|---|
| 1 | Mavrinac & Chen, **Modeling Coverage in Camera Networks: A Survey**, IJCV 2013. [DOI](https://doi.org/10.1007/s11263-012-0587-7) | **Đọc đầu tiên.** Cách định nghĩa "camera thấy một điểm": FOV, độ phân giải, góc nhìn, che khuất. Lấy định nghĩa coverage cho dự án |
| 2 | Liu, Sridharan, Fookes, **Recent Advances in Camera Planning for Large Area Surveillance**, ACM Computing Surveys 2016. [DOI](https://doi.org/10.1145/2906148) | Tổng quan các cách tìm vị trí (quy hoạch nguyên, tìm kiếm heuristic). Chọn cách đơn giản nhất đủ dùng |
| 3 | Mantini & Shah, **Camera Placement Optimization Conditioned on Human Behavior and 3D Geometry**, VISAPP 2016. [PDF](https://www.scitepress.org/papers/2016/56776/56776.pdf) | Gần nhất với bài toán: chấm điểm vị trí theo **hành vi người cần thấy**, không chỉ diện tích. Học cách đặt trọng số cho vùng trọng yếu |
| 4 | Chen & Davis, **Camera Placement Considering Occlusion for Robust Motion Capture**, báo cáo Stanford. [trang](https://graphics.stanford.edu/papers/OcclusionMetric/) | Che khuất do chính cơ thể người: vì sao 2 camera đủ cho độ rõ nhưng cần thêm để chống che (liên quan tay che điện thoại trên đùi) |
| 5 | Kumar và cs., **Efficient Mathematical Programming Formulation and Algorithmic Framework for Optimal Camera Placement**, 2024. [arXiv 2411.17942](https://arxiv.org/abs/2411.17942) | Bài toán đặt camera là bài toán phủ tập (set cover), khó giải tuyệt đối. Biện minh cho việc chỉ thử lưới vị trí nhỏ |
| 6 | Malhotra và cs., **Optimizing Camera Placements for Overlapped Coverage with 3D Camera Projections**, ICRA 2022. [arXiv 2203.10479](https://arxiv.org/abs/2203.10479) | Yêu cầu vùng được **≥ 2 camera** cùng thấy; cách chiếu 3D để tính coverage |
| 7 | Zhou, Park, Koltun, **Open3D**, 2018. [arXiv 1801.09847](https://arxiv.org/abs/1801.09847) | Thư viện có sẵn ray casting để tự tính coverage trong mô hình phòng |
| 8 | (Tùy chọn) Wang và cs., **VGGT**, CVPR 2025. [arXiv 2503.11651](https://arxiv.org/abs/2503.11651) | Chỉ đọc nếu muốn dựng mô hình phòng thật từ video quay quanh phòng. Ghi chú cũ đánh giá phần này **chưa được chứng minh**, nên mặc định dùng mô hình phòng đơn giản |

### Cho RQ2 — model còn chạy được ở góc đó không

| # | Nguồn | Đọc để lấy gì |
|---|---|---|
| 9 | Zhang và cs., **MPIIGaze**, TPAMI 2017. [arXiv 1711.09017](https://arxiv.org/abs/1711.09017) | Gaze **từ webcam laptop** trong đời thực: sai số bao nhiêu độ, giảm thế nào theo góc đầu và ánh sáng (C1) |
| 10 | Zhang và cs., **ETH-XGaze**, ECCV 2020. [arXiv 2007.15837](https://arxiv.org/abs/2007.15837) | Gaze khi đầu xoay/cúi nhiều: trường hợp thí sinh cúi nhìn bàn phím |
| 11 | Abdelrahman và cs., **L2CS-Net**, 2022. [arXiv 2203.03339](https://arxiv.org/abs/2203.03339) | Model gaze nhóm đang chọn; sai số trên MPIIGaze |
| 12 | Hempel và cs., **6DRepNet** (head pose), ICIP 2022. [arXiv 2202.12555](https://arxiv.org/abs/2202.12555) | Model head pose nhóm đang chọn; sai số theo góc đầu |
| 13 | Zhang và cs., **MediaPipe Hands**, 2020. [arXiv 2006.10214](https://arxiv.org/abs/2006.10214) | Hand tracking nhẹ cho C2; điều kiện nào thì mất tay |
| 14 | Shan và cs., **Understanding Human Hands in Contact at Internet Scale** (100DOH), CVPR 2020. [arXiv 2006.06669](https://arxiv.org/abs/2006.06669) | Phát hiện tay **đang cầm vật gì**: sát với "tay cầm điện thoại" trên C2 |
| 15 | Lin và cs., **Microsoft COCO**, ECCV 2014. [arXiv 1405.0312](https://arxiv.org/abs/1405.0312) | Định nghĩa vật nhỏ (< 32×32 px) và vì sao AP vật nhỏ thấp: căn cứ cho H2 về C3 |

### Cho RQ3 — giám sát thi nhiều camera và né tránh

| # | Nguồn | Đọc để lấy gì |
|---|---|---|
| 16 | Atoum và cs., **Automated Online Exam Proctoring**, IEEE TMM 2017. [PDF tác giả](https://cvlab.cse.msu.edu/pdfs/Atoum_Chen_Liu_Hsu_Liu_OEP.pdf) | Hệ thống dùng webcam + **camera đeo** (camera thứ hai). Camera thứ hai thêm được gì; danh sách kịch bản gian lận họ quay |
| 17 | Bergmans và cs., **On the Efficacy of Online Proctoring using Proctorio**, CSEDU 2021. [PDF](https://ris.utwente.nl/ws/portalfiles/portal/275927505/3e2a9e5b2fad237a3d35f36fa2c5f44552f2.pdf) | Người gian lận chủ động né hệ thống: **0/6** bị phần mềm bắt. Mẫu thiết kế thử nghiệm red team + nhóm vô tội |
| 18 | Liu và cs., **CHEESE**, IEEE TCDS 2024. [arXiv 2402.06107](https://arxiv.org/abs/2402.06107), mục V-A Datasets | Bộ dữ liệu OEP có những góc quay nào, có dùng lại để thử RQ2 được không |
| 19 | Talview **Dual-camera proctoring** [trang](https://www.talview.com/dual-camera-proctoring); Proctortrack [trang](https://proctortrack.com/?p=5783) | Thị trường đặt camera thứ hai thế nào. Nguồn vendor, không có số liệu, không mô tả hình học vị trí |
| 20 | (Tùy chọn) Erasmus Magazine 2020, tranh cãi camera thứ hai. [bài báo](https://www.erasmusmagazine.nl/en/2020/09/10/eur-considers-using-second-camera-in-proctored-online-exams/) | Quyền riêng tư: C3 quay cả phòng ở nhà, cần nêu trong paper |

## 5. Cách làm literature review

Thứ tự đọc: **1 → 3 → 16 → 17 → 9 → 15**, rồi phần còn lại theo RQ.

Với mỗi bài, ghi một dòng vào bảng (tạo `docs/research/camera-position_literature_review.md` khi bắt đầu đọc):

| Bài | Bài toán | Định nghĩa coverage / dữ liệu | Chỉ số + kết quả | Điều kiện (góc, khoảng cách, che khuất) | Giới hạn | Dùng cho RQ nào |
|---|---|---|---|---|---|---|

Đọc xong cần trả lời được:
1. Đã có ai tìm vị trí camera cho **một người ngồi bàn** (không phải giám sát diện rộng) chưa? Ghi chú cũ chưa tìm thấy; nếu có, sửa RQ1.
2. Định nghĩa "camera thấy được" cho dự án: cần bao nhiêu pixel, góc nhìn tối đa bao nhiêu.
3. Danh sách vùng trọng yếu + trọng số, có dẫn chứng từ bài về kịch bản gian lận.
4. Các ngưỡng trong H2 (pixel tối thiểu cho tay/điện thoại, góc đầu tối đa cho gaze) lấy từ đâu.

## 6. Liên quan tới nhánh khác

- Audio ([audio.md](audio.md)): cờ `other_voice` cần bằng chứng hình ảnh cùng lúc. C3 nhìn thấy cửa là nguồn bằng chứng chính cho "người nhắc ở cửa".
- 3 camera cần đồng bộ thời gian (tiếng bíp đầu buổi thi). Chưa thuộc phạm vi thư mục này.
