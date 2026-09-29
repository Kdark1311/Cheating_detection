# Cheating Detection – Hệ thống hỗ trợ giám sát thi trực tuyến

Dự án nghiên cứu xây dựng hệ thống **phát hiện hành vi gian lận trong thi trực tuyến** từ video webcam và âm thanh micro của thí sinh.

Hệ thống **không thay thế giám thị**. Nó đánh dấu những đoạn đáng nghi, đồng thời nói rõ những ca nó không chắc chắn để giám thị xem lại. Nhờ vậy giám thị không phải xem toàn bộ video mà chỉ tập trung vào các đoạn cần thiết.

## Hệ thống làm gì?

Hệ thống quan sát thí sinh qua ba nhóm tín hiệu:

- **Khuôn mặt**: người đang thi có đúng là người đã đăng ký không, thí sinh có quay đầu hay nhìn ra ngoài màn hình lâu không.
- **Cơ thể và đồ vật**: có điện thoại, sách, tai nghe hay người thứ hai trong khung hình không; thí sinh có các hành động bất thường như với tay hay rời chỗ không.
- **Âm thanh**: có tiếng nói không, có nhiều người nói cùng lúc không, và giọng nói đó có phải của thí sinh không.

Sau đó hệ thống kết hợp các tín hiệu này để đưa ra một trong ba kết luận cho mỗi tình huống: **nghi vấn**, **bình thường**, hoặc **chưa chắc chắn – cần giám thị xem lại**.

## Sơ đồ tổng quan

```mermaid
flowchart TD
    video["Video webcam"]
    mic["Âm thanh micro"]

    subgraph faceBranch["Nhánh khuôn mặt"]
        faceTrack["Phát hiện và theo dõi khuôn mặt"]
        identity["Xác minh danh tính"]
        headPose["Hướng đầu"]
        gaze["Hướng nhìn của mắt"]
    end

    subgraph bodyBranch["Nhánh cơ thể và đồ vật"]
        objects["Phát hiện điện thoại, sách, tai nghe"]
        actions["Nhận biết hành động"]
    end

    subgraph audioBranch["Nhánh âm thanh"]
        speech["Phát hiện tiếng nói"]
        overlap["Phát hiện nhiều người nói cùng lúc"]
        speaker["Giọng thí sinh hay người khác"]
    end

    fusion["Kết hợp các tín hiệu"]
    decision{"Ra quyết định"}
    normal["Bình thường"]
    suspicious["Nghi vấn"]
    unsure["Chưa chắc chắn, giám thị xem lại"]
    swapAlert["Cảnh báo thay người"]

    video --> faceTrack
    video --> objects
    video --> actions
    mic --> speech

    faceTrack --> identity
    faceTrack --> headPose
    faceTrack --> gaze
    speech --> overlap
    speech --> speaker

    headPose --> fusion
    gaze --> fusion
    objects --> fusion
    actions --> fusion
    overlap --> fusion
    speaker --> fusion

    fusion --> decision
    decision --> normal
    decision --> suspicious
    decision --> unsure
    identity --> swapAlert
```

## Nguyên tắc của dự án

- **Ưu tiên không bỏ sót**: mục tiêu là phát hiện được ít nhất 95% các tình huống gian lận.
- **Minh bạch khi không chắc chắn**: khi hình ảnh mờ, mất mặt hoặc mất tiếng, hệ thống ghi rõ lý do và chuyển cho người xem lại, không tự đoán.
- **Một tín hiệu đơn lẻ chưa phải là vi phạm**: ví dụ cúi xuống nhìn giấy nháp hợp lệ không bị coi là gian lận.
- **Đánh giá nghiêm túc**: dữ liệu kiểm tra cuối cùng được tách riêng theo từng người và chỉ dùng một lần.

## Trạng thái hiện tại

Dự án đang ở **giai đoạn lập kế hoạch thực nghiệm**: đã chọn mô hình cho từng thành phần, chưa tải dữ liệu và chưa có kết quả. Kế hoạch chi tiết từng bước nằm trong [experiment_plan.md](experiment_plan.md).

## Hạ tầng dự kiến

- 1–2 GPU RTX 3060 (12GB)
- Python ≥ 3.12
