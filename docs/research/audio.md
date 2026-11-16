# Nhánh audio: research questions và nguồn đọc

Ngày lập: 2026-11-16. Thứ tự làm: **research question → literature review → implement để trả lời câu hỏi**. Chưa có code cho nhánh mới; code cũ (VAD/OSD/TS-VAD, commit `6e76b38`) đã xóa, xem lại được bằng git.

## 1. Vai trò mới của audio

Audio chỉ là **tín hiệu phụ**. Nó làm đúng một việc:

> Gắn nhãn `other_voice` cho đoạn thời gian nghe thấy **giọng của người không phải thí sinh** trong phòng, kèm độ tin cậy.

Audio không tự kết luận gian lận:

| Audio | Hình ảnh cùng khoảng thời gian | Kết luận |
|---|---|---|
| `other_voice` | có bằng chứng (nhìn ra cửa, người thứ hai, điện thoại…) | **Gian lận** (đánh dấu) |
| `other_voice` | không có gì | Giám thị nghe lại |
| không có | – | Do nhánh hình ảnh quyết định |

Bối cảnh đã chốt (2026-11-08): thi kiểu IELTS Listening/Reading/Writing trong Safe Exam Browser, không giấy nháp, phòng đóng cửa, camera phủ cả phòng, thí sinh phải im lặng nhưng **có thể nhẩm bài**. Xử lý offline sau buổi thi. Mic chính là mic laptop (thêm 2 điện thoại nếu cần). GPU T4.

Vì thí sinh được nhẩm, "có tiếng nói = gian lận" sai. Phải phân biệt **giọng thí sinh** với **giọng người khác**.

**Còn mở, cần chốt với nhóm:** bài Listening phát qua loa hay tai nghe. Nếu qua loa, giọng trong bài nghe sẽ bị coi là "người khác" (xem RQ2-f).

### Audio bắt được gì, không bắt được gì

| Tình huống | Audio? |
|---|---|
| Người nhắc đứng sau cửa/tường, nói vọng vào | **Có** (lý do chính để giữ audio, camera không thấy) |
| Giọng phát từ điện thoại/loa giấu trong phòng | Có (nghe như người khác) |
| Thí sinh tự nhẩm, tự đọc đề | Không flag (đúng) |
| Tai nghe giấu, thí sinh chỉ nghe và im lặng | **Không** (giới hạn, ghi rõ trong paper) |
| Nhắn tin, đồng hồ thông minh | Không |

## 2. Thuật ngữ

- **VAD** (Voice Activity Detection): tìm đoạn nào có tiếng người nói.
- **Speaker verification**: so 2 đoạn giọng xem có cùng người không. Mô hình biến giọng thành 1 vector (**embedding**), rồi đo độ giống (**cosine similarity**).
- **Enrollment**: đoạn giọng mẫu thí sinh đọc lúc check-in (vd. 20 giây), làm "giọng chuẩn" để so.
- **EER**: tỷ lệ lỗi tại ngưỡng mà nhận nhầm = từ chối nhầm. Càng thấp càng tốt.
- **Event recall**: trong các lần người khác thật sự nói, hệ thống bắt được bao nhiêu %.
- **False alerts/giờ**: số lần báo động sai mỗi giờ thi. Đây là chi phí cho giám thị.
- **Far-field**: người nói ở xa mic, giọng nhỏ, vang và lẫn nhiễu.
- **Ablation**: bỏ một thành phần ra để đo nó đóng góp bao nhiêu.

## 3. Research questions

### RQ1 — Phát hiện được không?

**Câu hỏi:** Chỉ với một đoạn enrollment lúc check-in, bộ phát hiện ghép từ mô hình có sẵn (**VAD → speaker verification so với enrollment**) bắt được bao nhiêu % sự kiện `other_voice` trong ghi âm phòng thi bằng mic laptop, khi giới hạn cảnh báo sai ≤ N lần/giờ? Lỗi chủ yếu đến từ VAD bỏ sót tiếng nói hay từ so giọng nhầm?

**Vì sao hỏi:** đây là cách đơn giản nhất, không cần train. Nếu nó đủ tốt thì không cần TS-VAD hay diarization (chia "ai nói lúc nào" cho nhiều người).

**Giả thuyết H1 (mục tiêu đặt trước, chỉnh lại sau khi đọc):** event recall ≥ 90% tại ≤ 2 cảnh báo sai/giờ với giọng nói bình thường trong phòng. Lỗi chính là VAD bỏ sót giọng nhỏ, không phải so giọng nhầm (bảng DER của pyannote cho thấy phần "nhầm người" chỉ 3,8–7,5%, còn bỏ sót + báo nhầm chiếm phần lớn).

**So sánh tối thiểu:**
1. Baseline ngây thơ: có tiếng nói là flag (để chứng minh vì sao cần so giọng).
2. VAD + speaker verification (phương pháp chính).
3. (Tùy chọn) mô hình kiểu Personal VAD: VAD có điều kiện theo giọng thí sinh.

**Đo:** event recall, false alerts/giờ, EER của bước so giọng, tách lỗi theo bước (VAD miss / so giọng nhầm).

### RQ2 — Hỏng ở điều kiện nào?

**Câu hỏi:** Độ chính xác của RQ1 giảm bao nhiêu trong các điều kiện đặc thù phòng thi:

- (a) giọng vọng qua cửa/tường đóng (nhỏ, mất âm cao, vang);
- (b) thì thầm;
- (c) câu ngắn < 2 giây;
- (d) giọng người khác chồng lên tiếng thí sinh đang nhẩm;
- (e) enrollment dài 10 / 20 / 30 giây;
- (f) bài Listening phát qua loa (nếu cho phép), và cách loại nó bằng tín hiệu tham chiếu đã biết trước;
- (g) giọng phát từ loa điện thoại.

Câu phụ (tùy chọn): mic điện thoại đặt gần cửa có cứu được (a) không?

**Giả thuyết H2:** (a) và (b) là điểm yếu nhất. Speaker verification far-field (VOiCES) có EER khoảng 5%, gấp 5–7 lần dữ liệu sạch (~1%); thì thầm còn khó hơn vì không có rung thanh quản.

**Đo:** cùng chỉ số RQ1, tách theo từng điều kiện. Trước khi có dữ liệu thật, giả lập (a)(c)(d) bằng cách trộn giọng + phòng vang + nhiễu; sau đó kiểm lại trên ghi âm pilot thật.

### RQ3 — Ghép với hình ảnh có đáng không?

**Câu hỏi:** Khi ghép cờ `other_voice` với bằng chứng hình ảnh trong cùng khoảng thời gian (luật bảng mục 1), hệ thống bắt thêm được bao nhiêu kịch bản gian lận mà hình ảnh bỏ lỡ, và đổi lại tăng bao nhiêu cảnh báo sai / phút giám thị phải xem lại?

**Vì sao hỏi:** các nguồn đã rà soát không có số liệu công bố về đóng góp riêng của audio trong giám sát thi (vendor chỉ quảng cáo, các bài học thuật không tách riêng audio). Đây là **khoảng trống nghiên cứu** để viết paper.

**Giả thuyết H3:** audio giúp rõ nhất ở kịch bản người nhắc ngoài khung hình (sau cửa); với kịch bản trong khung hình, hình ảnh đã đủ và audio chỉ tăng độ chắc chắn.

**Đo:** ablation có/không audio trên cùng các phiên pilot, cùng người: event recall theo kịch bản, false alerts/giờ, phút xem lại/giờ thi.

## 4. Nguồn đọc theo từng RQ

Đã kiểm tra tên bài và link (2026-11-16). Đọc abstract + phần được ghi; chỉ đọc toàn văn khi cần.

### Cho RQ1

| # | Nguồn | Đọc để lấy gì |
|---|---|---|
| 1 | Ding và cs., **Personal VAD: Speaker-Conditioned Voice Activity Detection**, Odyssey 2020. [arXiv 1908.04284](https://arxiv.org/abs/1908.04284) | Bài gần nhất với bài toán: VAD biết giọng người đăng ký. Cách họ đo, so với "VAD + so giọng" |
| 2 | Plaquet & Bredin, **Powerset multi-class cross entropy loss for neural speaker diarization**, Interspeech 2023. [arXiv 2310.13025](https://arxiv.org/abs/2310.13025) | Nền của pyannote `segmentation-3.0` (VAD dùng được). Dữ liệu train, để biết test nào là "đã thấy" |
| 3 | pyannote **speaker-diarization-3.1** model card. [HF](https://huggingface.co/pyannote/speaker-diarization-3.1) | Bảng DER tách miss / false alarm / confusion: căn cứ cho H1 |
| 4 | **Silero VAD** + trang Quality Metrics. [GitHub](https://github.com/snakers4/silero-vad), [wiki](https://github.com/snakers4/silero-vad/wiki/Quality-Metrics) | VAD nhẹ, chạy CPU, MIT. Số do tác giả tự báo, chưa ai kiểm lại độc lập |
| 5 | Desplanques và cs., **ECAPA-TDNN**, Interspeech 2020. [arXiv 2005.07143](https://arxiv.org/abs/2005.07143) | Model speaker verification chuẩn; EER trên VoxCeleb |
| 6 | Wang và cs., **WeSpeaker**, ICASSP 2023. [arXiv 2210.17016](https://arxiv.org/abs/2210.17016) | Toolkit có sẵn ECAPA/ResNet34/CAM++ pretrained; cách chấm điểm cosine |
| 7 | Medennikov và cs., **Target-Speaker VAD (TS-VAD)**, Interspeech 2020. [arXiv 2005.07272](https://arxiv.org/abs/2005.07272) | Hiểu TS-VAD để viết 1 đoạn **vì sao không cần**: nó làm cho tiệc 4 người, cần profile mọi người nói; mình chỉ có 1 thí sinh |
| 8 | Mesaros, Heittola, Virtanen, **Metrics for Polyphonic Sound Event Detection**, Applied Sciences 6(6):162, 2016. [MDPI](https://www.mdpi.com/2076-3417/6/6/162) | Cách đo theo sự kiện (event-based) thay vì theo khung, để báo event recall đúng chuẩn |

### Cho RQ2

| # | Nguồn | Đọc để lấy gì |
|---|---|---|
| 9 | Richey và cs., **VOiCES corpus**, Interspeech 2018. [arXiv 1804.05053](https://arxiv.org/abs/1804.05053) | Dữ liệu giọng xa mic, phòng thật, có nhiễu: gần điều kiện (a). Có thể mượn làm test |
| 10 | Cai, Qin và cs. (DKU), **The DKU System for the Speaker Recognition Task of the 2019 VOiCES from a Distance Challenge**. [arXiv 1907.02194](https://arxiv.org/abs/1907.02194) | Số EER far-field (~5%) và mẹo làm bền (augmentation) |
| 11 | Nagrani và cs., **VoxCeleb**, Interspeech 2017. [arXiv 1706.08612](https://arxiv.org/abs/1706.08612) | Model so giọng train trên gì → khác gì với phòng thi (không dùng VoxCeleb để test) |
| 12 | Snyder, Chen, Povey, **MUSAN**, 2015. [arXiv 1510.08484](https://arxiv.org/abs/1510.08484) và **RIRS_NOISES** [OpenSLR 28](https://www.openslr.org/28/) | Nhiễu + phản xạ phòng có sẵn để giả lập (a)(d) |
| 13 | Scheibler và cs., **Pyroomacoustics**, ICASSP 2018. [arXiv 1710.04196](https://arxiv.org/abs/1710.04196) | Tự giả lập phòng, khoảng cách người nói–mic |
| 14 | Tao và cs., Interspeech 2015 (VAD cho thì thầm). [ISCA](https://www.isca-archive.org/interspeech_2015/tao15_interspeech.html); luận án IISc về thì thầm [link](https://etd.iisc.ac.in/handle/2005/5516) | Vì sao thì thầm làm hỏng VAD và so giọng (điều kiện b) |
| 15 | Sridhar và cs., **ICASSP 2021 Acoustic Echo Cancellation Challenge**. [arXiv 2009.04972](https://arxiv.org/abs/2009.04972) | Điều kiện (f): loại âm thanh đã biết trước (bài Listening) khỏi ghi âm mic |
| 16 | Chen và cs., **LibriCSS**, ICASSP 2020. [arXiv 2001.11482](https://arxiv.org/abs/2001.11482) | Dữ liệu có nói chồng thật trong phòng, điều kiện (d) |
| 17 | (Tùy chọn) Wang và cs., **ASVspoof 2019**. [arXiv 1911.01601](https://arxiv.org/abs/1911.01601) | Điều kiện (g): giọng phát lại qua loa khác giọng thật thế nào |
| 18 | (Tùy chọn) Ochi và cs., Interspeech 2016, mảng mic điện thoại. [ISCA](https://www.isca-archive.org/interspeech_2016/ochi16b_interspeech.html) | Chỉ đọc nếu dùng mic điện thoại: đồng bộ nhiều máy ghi |

### Cho RQ3

| # | Nguồn | Đọc để lấy gì |
|---|---|---|
| 19 | Atoum và cs., **Automated Online Exam Proctoring**, IEEE TMM 2017. [PDF tác giả](https://cvlab.cse.msu.edu/pdfs/Atoum_Chen_Liu_Hsu_Liu_OEP.pdf) | Hệ giám sát có mic; họ phát hiện tiếng nói thế nào, dữ liệu OEP có audio không |
| 20 | Liu và cs., **CHEESE: MIL for Cheating Detection**, IEEE TCDS 2024. [arXiv 2402.06107](https://arxiv.org/abs/2402.06107), mục V-D Ablation | Cách làm ablation từng nhánh; họ để audio là future work |
| 21 | Bergmans và cs., **On the Efficacy of Online Proctoring using Proctorio**, CSEDU 2021. [PDF](https://ris.utwente.nl/ws/portalfiles/portal/275927505/3e2a9e5b2fad237a3d35f36fa2c5f44552f2.pdf) | Cách thiết kế thử nghiệm: nhóm gian lận + nhóm trung thực nhưng lo lắng |
| 22 | Baltrušaitis, Ahuja, Morency, **Multimodal Machine Learning: A Survey and Taxonomy**, TPAMI 2019. [arXiv 1705.09406](https://arxiv.org/abs/1705.09406), phần Fusion | Late fusion (ghép kết quả từng nhánh bằng luật) vs ghép sớm; lý do chọn luật đơn giản |
| 23 | Geifman & El-Yaniv, **SelectiveNet**, ICML 2019. [PMLR](https://proceedings.mlr.press/v97/geifman19a.html) | Khái niệm "không chắc thì chuyển giám thị" và cách đo đánh đổi |
| 24 | Honorlock **Voice Detection** [trang](https://honorlock.com/voice-detection/) + hướng dẫn APSU [PDF](https://apsu.edu/online/technology/honorlock/files/honorlock_voice_detection.pdf) | Thị trường làm gì (bắt từ khóa "Hey Siri", flag theo âm lượng bị báo sai nhiều). Nguồn vendor, không có số liệu |
| 25 | (Tùy chọn) Liao và cs., **Light-ASD**, CVPR 2023. [arXiv 2303.04439](https://arxiv.org/abs/2303.04439); Tao và cs., **TalkNet**, ACM MM 2021. [arXiv 2107.06592](https://arxiv.org/abs/2107.06592) | Bằng chứng hình ảnh bổ sung: có tiếng nói mà môi thí sinh không động → không phải thí sinh nói |

## 5. Cách làm literature review

Thứ tự đọc: **1 → 7 → 5 → 9 → 19 → 20 → 21** (đủ để trả lời "đã ai làm chưa, làm thế nào"), rồi phần còn lại theo RQ.

Với mỗi bài, ghi một dòng vào bảng (tạo `docs/research/audio_literature_review.md` khi bắt đầu đọc):

| Bài | Bài toán | Dữ liệu | Chỉ số + kết quả | Điều kiện thử (xa mic? nhiễu? thì thầm?) | Giới hạn | Dùng cho RQ nào |
|---|---|---|---|---|---|---|

Đọc xong cần trả lời được:
1. Đã có ai đo riêng "giọng người khác" trong phòng thi chưa? (dự kiến: chưa; nếu có, RQ phải sửa.)
2. Chọn VAD nào, model so giọng nào, vì sao (có số liệu dẫn chứng).
3. Ngưỡng H1/H2 có hợp lý so với số đã công bố không.
4. Dữ liệu test: mượn bộ nào (VOiCES, LibriCSS) và phải tự ghi pilot những kịch bản nào.

## 6. Đã bỏ so với kế hoạch cũ

- **OSD** (phát hiện nói chồng) và **TS-VAD** riêng: thay bằng một câu hỏi "có giọng không phải thí sinh không". Nói chồng chỉ còn là điều kiện thử (RQ2-d).
- **Diarization đầy đủ**, **AED-TSVAD**: không cần cho 1 thí sinh.
- Mục tiêu "recall ≥ 98% / 95%" cho từng module: thay bằng event recall + cảnh báo sai/giờ của đúng một nhãn `other_voice`.
