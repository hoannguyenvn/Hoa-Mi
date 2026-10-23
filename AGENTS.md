# AGENTS.md — Oriole

> Hướng dẫn bắt buộc cho mọi AI agent (và người) làm việc trong repo này.
> Đọc file này trước khi sửa bất cứ thứ gì. Giữ ngắn; chi tiết nằm trong `docs/`.

## 0. Tóm tắt 60 giây

- App desktop **offline** cho Windows: chuyển audio/video thành văn bản + phụ đề,
  và luyện phát âm tiếng Việt/Anh.
- Công nghệ: Python 3.13 (Miniforge Conda), `tkinter`, `faster-whisper` (CPU int8),
  `yt-dlp`, `sounddevice`, `numpy`. Tùy chọn: `torch` + `transformers` cho GOP.
- Kiến trúc: gần như **một file** `app.py` (UI + pipeline), 3 module thuật toán
  (`pron_en.py`, `gop.py`, `prosody.py`), dữ liệu (`lessons_en.json`, `mau/`).
- Chưa có git repo, chưa có test suite chính thức. `tools/smoke_test.py` là lưới an toàn tối thiểu.
- Ngôn ngữ sản phẩm: **tiếng Việt**. Code/identifier: tiếng Anh.

## 1. Thứ tự đọc bắt buộc

1. `docs/PROJECT-STATE.md` — hiện trạng, việc đang làm, việc kế tiếp.
2. `docs/HANDOFF.md` — mục cuối cùng: phiên trước đã làm gì, còn gì treo.
3. `docs/DECISIONS.md` — các quyết định **không được phá**.
4. Skill khớp tính năng trong `.opencode/skills/` (xem bảng §6).
5. `docs/ARCHITECTURE.md` khi cần hiểu luồng dữ liệu/thread.
6. `docs/FEATURES.md` khi cần biết một tính năng nằm ở đâu.

Thứ tự ưu tiên khi tài liệu >< code: **code là sự thật**, nhưng phải sửa tài liệu
trong cùng phiên. Không để drift.

## 2. Nghi thức đầu/cuối phiên (bắt buộc)

### Đầu phiên
```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\context_check.py
```
- Nếu check FAIL: sửa drift trước khi thêm tính năng.
- Đọc 3 mục đầu của `docs/PROJECT-STATE.md`; xác nhận việc sẽ làm.
- Không đọc lại toàn bộ `app.py` (150 KB). Dùng `grep`/`read` theo symbol trong
  `docs/context-map.json` và skill tương ứng.

### Cuối phiên
1. Cập nhật `docs/PROJECT-STATE.md`: trạng thái, việc kế tiếp, rủi ro mới.
2. **Append** một mục vào `docs/HANDOFF.md` theo template (không sửa mục cũ).
3. Nếu có quyết định kiến trúc mới: thêm `D-xx` vào `docs/DECISIONS.md`.
4. Chạy lại `tools/context_check.py` và `tools/smoke_test.py`.
5. Ghi rõ việc gì **chưa** kiểm chứng được (mic, model tải, YouTube…).

Mục tiêu: một model khác mở repo, đọc 3 file (`PROJECT-STATE`, `HANDOFF`,
`DECISIONS`) là tiếp tục được ngay, không cần hỏi lại người dùng.

## 3. Bản đồ code

| File | Vai trò | Điểm vào chính |
|---|---|---|
| `app.py` | Toàn bộ UI Tk + pipeline + chấm điểm L1 | `App._run`, `App._w_file`, `App._w_yt`, `App._w_prac`, `App._prac_done` |
| `pron_en.py` | CMUdict, IPA, căn chỉnh âm vị, gợi ý sửa | `analyze_pairs`, `compare_words`, `TIPS` |
| `gop.py` | GOP acoustic (wav2vec2 CTC), tùy chọn | `available`, `score` |
| `prosody.py` | F0 autocorrelation, contour bán cung, DTW | `compare`, `contour` |
| `lessons_en.json` | 14 bài tiếng Anh | `lessons[].id/target/words/tips/pairs` |
| `mau/` | 12 clip Việt/Anh + 74 clip bài Anh | `mau/en/<id>.wav`, `<id>_slow.wav`, `w_<word>.wav` |
| `tools/build_lessons.py` | Sinh lại bài + audio mẫu | `main()` |
| `gen_mau.py` | Sinh lại bộ âm mẫu cơ bản | `main()` |
| `config.json` | Cài đặt người dùng (tự tạo) | `load_config` / `save_config` |
| `practice_history.json` | Tiến bộ luyện (tự tạo) | `_load_hist` / `_save_hist` |

## 4. Bất biến kỹ thuật (không được phá)

| # | Quy tắc | Vì sao |
|---|---|---|
| I1 | Worker thread **không** chạm widget. Mọi cập nhật UI đi qua `self._queue` và `_poll()` (80 ms). | Tk không thread-safe; crash ngẫu nhiên. |
| I2 | Chấm điểm bằng ASR trên **bản ghi của người học**, không dùng transcript của file mẫu. | Lỗi cũ #4 trong `PHASE2-DANH-GIA-DU-AN-CU.md`. |
| I3 | Không chấm khi tín hiệu gần như im lặng (đỉnh < 0,8% ≈ -42 dB, sàn cho mic array laptop yếu; nền nhiễu mic thường < 0,1% — xem D-21), < 0,5 s, hoặc không nghe thấy giọng. | Whisper "bịa" trên nền im lặng. |
| I4 | Điểm chính chỉ là `correct / total` theo từ. `warns`/`tones` là cảnh báo, **không trừ điểm**. | Con số phải giải thích được. |
| I5 | F0 luôn quy về **bán cung so với trung vị của chính người nói**, không so Hz tuyệt đối. | Khác giới tính/độ tuổi. |
| I6 | GOP chỉ báo lỗi khi kém **bản mẫu cùng câu** rõ rệt (≥1,5 log và <55%); không có mẫu mới dùng ngưỡng tuyệt đối. | Tránh báo oan do model yếu. |
| I7 | Điểm GOP 0–100 là logistic của log-posterior ratio, **không phải % phát âm đúng**. Phải ghi chú trong UI. | Tránh hiểu sai. |
| I8 | Không thêm dependency nặng (librosa, praat, sklearn, openai-whisper, torchaudio) nếu numpy làm được. | Giữ app nhẹ, offline, khởi động nhanh. |
| I9 | Runtime offline. Mạng chỉ dùng cho YouTube và tải model lần đầu. | Sản phẩm là app offline. |
| I10 | Mọi file tạm phải xóa trong `finally`; không ghi rác vào thư mục chạy. | Rò rỉ file. |
| I11 | Vòng lặp dài phải kiểm tra `self.cancel_flag` và ném `_YtCancelled`. | Nút Hủy/Esc phải có tác dụng. |
| I12 | `config.json` chỉ chứa khóa trong `DEFAULT_CFG`; thiếu/khóa lạ phải bỏ qua an toàn. | Bền vững khi nâng cấp. |
| I13 | Âm mẫu TTS chỉ để **nghe**, không dùng để **chấm** phát âm. | TTS không đại diện người thật. |
| I14 | Không đưa text debug kỹ thuật lên UI; log vào panel Nhật ký. | Trải nghiệm người dùng. |
| I15 | Mọi file text ghi/đọc bằng **UTF-8**. Console Windows có thể là cp1252 — đặt `PYTHONIOENCODING=utf-8` khi chạy script in tiếng Việt. | Mojibake. |
| I16 | Không lưu cookie/credential/token trong repo. | Bảo mật. |

## 5. Môi trường & lệnh

```powershell
# Python chuẩn của máy (không dùng venv)
$PY = "C:\Users\ADMIN\miniforge3\python.exe"

# Chạy app
& $PY app.py

# Kiểm tra context/tài liệu/skills
$env:PYTHONIOENCODING='utf-8'
& $PY tools\context_check.py            # kiểm tra
& $PY tools\context_check.py --snapshot # sinh lại docs/CONTEXT-SNAPSHOT.md

# Test khói (không cần mic/model)
& $PY tools\smoke_test.py

# Cú pháp toàn bộ module Python
& $PY -m py_compile app.py pron_en.py gop.py prosody.py gen_mau.py tools\build_lessons.py tools\context_check.py tools\smoke_test.py
```

- Không có `pytest`; test là script stdlib. Nếu thêm pytest, phải ghi vào
  `requirements.txt` và `DECISIONS.md`.
- Model Whisper mặc định `base`. GOP cần `torch` (~1,2 GB model tải lần đầu).
- Đường dẫn có dấu cách: luôn quote trong PowerShell.

## 6. Bộ skills

| Skill ID | Dùng khi |
|---|---|
| `project-context` | Mở/đóng phiên, chuyển AI model, khôi phục context, cập nhật handoff |
| `app-transcription` | File/ghi âm → văn bản, SRT/TXT, model Whisper, hủy, tiến trình |
| `app-youtube` | yt-dlp, chọn phụ đề, tải video/audio, nhúng phụ đề |
| `app-recording` | Micro, thu âm tự dừng, chuẩn hóa audio, WAV 16k |
| `app-pronunciation` | Chấm L1, lỗi n/ l, th, s/sh, âm cuối, thanh điệu, kết quả UI |
| `app-phonemes` | CMUdict, IPA, căn chỉnh âm vị, GOP/wav2vec2 |
| `app-prosody` | F0, ngữ điệu, biểu đồ cao độ |
| `app-ui` | Tkinter, theme, DPI, bố cục, cài đặt, phím tắt |
| `app-lessons` | Thêm/sửa bài, audio mẫu, `build_lessons.py` |
| `app-qa-release` | Nghiệm thu, smoke test, dependency, đóng gói, `run.bat` |
| `skill-authoring` | Tạo/sửa skill trong repo này |

Skill chỉ được nạp khi cần. Nếu một skill mâu thuẫn với code, sửa skill ngay.

## 7. Definition of Done

Một thay đổi chỉ "xong" khi:
- [ ] Chạy được `tools/context_check.py` và `tools/smoke_test.py`.
- [ ] `py_compile` sạch.
- [ ] Luồng liên quan được thử thủ công (hoặc ghi rõ "chưa thử được vì …").
- [ ] Không phá bất biến §4.
- [ ] `PROJECT-STATE` + `HANDOFF` đã cập nhật.
- [ ] Nếu đổi hành vi người dùng: cập nhật `README.md` và copy UI tiếng Việt.

## 8. Không làm

- Không tự ý tái cấu trúc `app.py` thành nhiều package trong một phiên không liên quan.
- Không thêm tính năng "chấm ngữ điệu/giọng" bằng cách so MFCC/DTW hai người.
- Không hiển thị điểm khi thiếu bằng chứng.
- Không đổi khóa kết quả (`cues`, `score`, `items`, `gop`, `inton`…) mà không cập nhật
  `_prac_done`/`_on_result`.
- Không commit file tải về, model, `__pycache__`, hay dữ liệu cá nhân.
- Không bịa kết quả kiểm thử. Ghi "chưa kiểm chứng" nếu chưa chạy.
