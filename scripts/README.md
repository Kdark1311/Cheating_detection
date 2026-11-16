# scripts/

Lệnh chạy từ dòng lệnh, ghép các bước trong `src/` lại. Không chứa logic chính (logic nằm trong `src/`, để test được).

Dự kiến:

| Script | Làm gì |
|---|---|
| `run_session.py <session_id>` | Chạy toàn bộ pipeline cho một buổi: đồng bộ → các nhánh → fusion → report |
| `evaluate.py <RQ> <exp_dir>` | Chấm `events.csv` với nhãn, ghi `metrics.json` |
| `simulate_placement.py` | Chạy giả lập vị trí camera (RQ-C1) |

Chạy bằng `uv run python scripts/<tên>.py ...`.
