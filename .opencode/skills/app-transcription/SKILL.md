---
name: App Transcription Pipeline
description: Sửa luồng chuyển file audio/video hoặc bản ghi thành văn bản, SRT/TXT, tải model Whisper, tiến trình, hủy tác vụ, xem trước và xuất file trong Oriole. Dùng khi người dùng nhắc tới nhận dạng giọng nói, transcript, phụ đề, Faster-Whisper, hoặc Tab 1.
---

# Transcription Pipeline

Phạm vi: Tab 1, nguồn **File máy tính** và **bản ghi trực tiếp**. YouTube có skill
riêng (`app-youtube`).

## Đọc trước

- `docs/ARCHITECTURE.md` §4 (luồng 1) và §3.1–3.2 (cue, payload).
- Bất biến I1, I3, I10, I11, I15 trong `AGENTS.md`.

## Symbol liên quan (app.py)

| Nhóm | Symbol |
|---|---|
| Điều phối | `App._run`, `App._primary`, `App._cancel`, `App._set_stt_state`, `stt_controls` |
| Worker | `App._w_file`, `App._w_whisper_cues` |
| Model | `load_model`, `ensure_av_patched` |
| Cue | `_fix_cues`, `split_long_cues`, `cues_to_srt`, `cues_to_txt` |
| Kết quả | `App._on_result`, `App._on_error`, `App._render_preview` (chữ = `cues_to_txt`, tag `time` mờ) |
| Màn hình (B5) | `stt_view`, `App._stt_view`, `App._stt_res_view`, `App._toggle_log`, `short_duration` — xem skill `app-ui` "Màn Văn bản + Cài đặt" |
| Xuất | `App._copy`, `App._save_txt`, `App._save_srt`, `App._open_folder` |
| Hằng số | `MODELS`, `LANGS`, `REC_LONG_SEC` (900 s, ghi âm Tab 1) |

## Hợp đồng dữ liệu

Một cue luôn là `(start: float, end: float, text: str)`.

Worker đẩy message qua `self._queue`:

| kind | payload | Xử lý |
|---|---|---|
| `status` | `str` | dòng trạng thái |
| `log` | `str` hoặc `(str, level)` | panel Nhật ký |
| `progress` | `float 0..1` hoặc `None` | determinate / indeterminate |
| `result` | dict | `_on_result` |
| `error` | `str` (`"__cancelled__"` = hủy) | `_on_error` |

`result` cho luồng file:
```python
{
  "cues": [(0.0, 2.1, "…")],
  "media": fp_or_None,     # None khi bản ghi tạm đã xóa
  "base": "tên file",
  "note": "Xong: N dòng · vi (98%)",
}
```

## Quy trình chuẩn của `_w_file`

```
status "Bước 1/2: tải model …"
model = load_model(model_size)          # CPU int8
status "Bước 2/2: đang nhận dạng …"
segs, info = model.transcribe(fp, language=lang, beam_size=5)
for s in segs:
    check cancel → raise _YtCancelled
    progress = s.end / info.duration
    cues.append((s.start, s.end, " ".join(s.text.split())))
cues = _fix_cues(split_long_cues(cues))
queue result
```

Quy ước:
- `lang=None` khi người dùng chọn `auto`.
- Câu quá dài bị chia theo từ ở 92 ký tự (`split_long_cues`).
- `_fix_cues` chỉ **sắp theo start** và đảm bảo `end > start`; nó **không** cắt
  chồng lấn giữa cue trước và cue sau.
- Bản ghi: `save_frames_wav` tạo WAV tạm → `_w_file(..., delete_after=True)`;
  file được xóa trong `finally` của `_w_file` (thành công, hủy **và** lỗi); bản thu
  `< 0,4 s` bị `remove_temp` trước khi tới worker. Test: `w_file_removes_temp_recording_on_error`.

## Thêm nguồn đầu vào mới

1. Thêm nhánh trong `App._run` (validate trước, rồi `_set_stt_state("processing")`).
2. Viết `App._w_<nguồn>`:
   - không chạm widget,
   - kiểm tra `self.cancel_flag` trong vòng lặp dài,
   - dọn temp trong `finally`,
   - kết thúc bằng `("result", payload)` hoặc `("error", str)`.
3. Thêm nhánh UI trong `_build_src_*` + `_src_changed`.
4. Cập nhật `docs/FEATURES.md`, `docs/context-map.json`, `tools/smoke_test.py`
   nếu có hàm thuần mới.

## Quy tắc sửa

- **Không** gọi `load_model` trong main thread (đóng băng UI).
- **Không** thay `beam_size`/`vad_filter` tùy tiện. Luồng file cố tình không bật VAD;
  `_w_whisper_cues` và luyện phát âm bật VAD vì đầu vào có im lặng.
- `condition_on_previous_text=False` chỉ dùng cho **luyện phát âm** (chống bịa);
  luồng file/YouTube giữ mặc định để câu liền mạch.
- Nếu đổi khóa `result`, sửa đồng thời `_on_result`, `_save_*`, `_open_*`.
- `ensure_av_patched()` phải chạy trước khi tạo `WhisperModel` (PyAV ≥ 15 vs
  faster-whisper 1.2.1). Đừng bỏ.

## Nợ đã biết

- `load_model()` **không cache**: mỗi lần bấm Bắt đầu tạo model mới. Nếu sửa,
  dùng cache theo `(model_size)` + khóa, và cân nhắc giải phóng RAM.
- Chưa có hàng đợi nhiều file; mỗi lần một file.
- `medium` có thể rất chậm trên CPU.
- Không có thời gian còn lại/ETA; tiến trình chỉ là `s.end / duration`.
- `enhance_audio` lọc high-pass bằng vòng lặp Python → bản ghi 15 phút xử lý chậm
  trên main thread (UI đứng vài giây) trước khi worker chạy.

## Kiểm chứng

```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\smoke_test.py
& "C:\Users\ADMIN\miniforge3\python.exe" -m py_compile app.py
```

Thủ công:
1. Chọn một file `.mp3`/`.mp4` ngắn, model `base`, ngôn ngữ `auto` → có text + SRT.
2. Bật "Kèm mốc thời gian" → mỗi dòng có `[hh:mm:ss]`.
3. Bấm Hủy giữa lúc nhận dạng → không có messagebox lỗi, UI về trạng thái sẵn sàng.
4. Lưu `.txt`/`.srt` → mở lại bằng Notepad, tiếng Việt không lỗi font.
5. Ghi âm 3 giây rồi im lặng → tự dừng, ra text, file tạm không còn trong `%TEMP%`.

## Cạm bẫy

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| UI treo khi bấm Bắt đầu | gọi model/transcribe trên main thread |
| Crash ngẫu nhiên | worker chạm widget |
| Hủy không tác dụng | thiếu check `cancel_flag` trong vòng lặp |
| `KeyError: 'base'` | đổi payload mà quên `_default_base`/`_save_*` |
| Text dính chùm | quên `split_long_cues` hoặc `max_chars` quá lớn |
| SRT chồng thời gian | `_fix_cues` không cắt overlap (hành vi hiện tại) |
| Lỗi PyAV `metadata_errors` | quên `ensure_av_patched()` |
