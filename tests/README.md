# tests/

Test tự động cho phần code dễ sai âm thầm: đồng bộ (`io`), cách tính chỉ số (`eval`), luật ghép (`fusion`). Sai ở đây làm sai mọi kết quả mà không báo lỗi.

Ví dụ cần có:
- Hai luồng lệch nhau 1,5 s → đồng bộ trả về đúng 1,5 s.
- Một sự kiện thật + một cờ trùng 40% → ghép được với IoU 0,3, không ghép với IoU 0,5.
- Hai nhánh cùng báo trong cửa sổ W → "nghi gian lận"; một nhánh yếu → "xem lại".

Chạy: `uv run pytest`.
