# data/

Không commit dữ liệu (đã có trong `.gitignore`). Chỉ file này được commit.

```text
data/
  raw/<session_id>/        c1.mp4, c2.mp4, c3.mp4, mic_laptop.wav, mic_phone*.wav, enrollment/ (ảnh mặt, 20 s giọng, nhìn 4 góc)
  annotations/<session_id>.csv   session, label, actor, start_s, end_s
  splits/{train,val,test}.txt    danh sách session, chia theo người
  external/<dataset>/      bộ dữ liệu công khai (OEP, VOiCES, ...)
```

`session_id` = `<person_id>_<honest|cheat>_<nn>`. Giấy đồng ý lưu riêng, không để trong repo.
