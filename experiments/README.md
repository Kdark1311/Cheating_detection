# experiments/

Ghi lại **từng lần chạy thí nghiệm** để tái lập được. Chỉ chứa file nhẹ (config, chỉ số, bảng); video, đặc trưng, dự đoán lớn để ở `outputs/` (không commit).

```text
experiments/
  <RQ>/                    vd. A1, C1, F2, S2
    <yyyymmdd>_<tên>/      vd. 20270215_silero_wespeaker
      config.yaml          model, commit, checkpoint sha256, dữ liệu, split, ngưỡng, GPU, seed
      metrics.json         chỉ số + support + CI
      report.md            kết luận ngắn, bảng theo slice, ví dụ lỗi
```

Quy tắc:
- Mỗi lần chạy một thư mục mới, không ghi đè lần cũ.
- Ngưỡng chọn trên `val`; chạy `test` chỉ một lần ở pha P5 và ghi rõ trong `report.md`.
- Checklist bàn giao: [docs/experiment_plan.md](../docs/experiment_plan.md) mục 7.
