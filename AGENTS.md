# AGENTS.md — Hoa Mi

> Hướng dẫn bắt buộc cho mọi AI agent (và người) làm việc trong repo này.
> Đọc file này trước khi sửa bất cứ thứ gì. Giữ ngắn; chi tiết nằm trong `docs/`.

## 0. Tóm tắt 60 giây

- App desktop **offline** cho Windows: **luyện phát âm tiếng Việt** (N/L, thanh điệu, vần)
  cho người nói tiếng Việt, kèm chuyển audio/video thành văn bản + phụ đề.
- Tách từ **Oriole** (app luyện tiếng Anh) ngày 2026-10-25 tại commit `957f995` (HM-01).
  Phần tiếng Anh (bài, `pron_en`, GOP, đọc to YouTube) **không** thuộc repo này.
- Công nghệ: Python 3.13 (Miniforge Conda), `tkinter`, `faster-whisper` (CPU int8),
  `yt-dlp`, `sounddevice`, `numpy`.
- Kiến trúc: gần như **một file** `app.py` (UI + pipeline), `prosody.py` (F0), dữ liệu `mau/`.
- Git repo `hoannguyenvn/Hoa-Mi` (nhánh `main`); chưa có test suite chính thức.
  `tools/smoke_test.py` + `tools/ui_check.py` là lưới an toàn tối thiểu. Commit sau mỗi bước xong.
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
| `app.py` | Toàn bộ UI Tk + pipeline + chấm điểm L1 + bài (`PRACTICE_SETS`, `GUIDES`) | `App._run`, `App._w_file`, `App._w_yt`, `App._w_prac`, `App._prac_done` |
| `prosody.py` | F0 autocorrelation, contour bán cung, DTW | `compare`, `contour`, `f0_track` |
| `mau/` | âm mẫu tiếng Việt (TTS, chỉ để nghe) | `mau/vi_*.wav` |
| `gen_mau.py` | Sinh lại âm mẫu | `CLIPS` |
| `tools/ui_check.py` | Chạy App thật qua mọi màn/bài, bắt lỗi callback Tk | `main()` |
| `config.json` | Cài đặt người dùng (tự tạo) | `load_config` / `save_config` |
| `practice_history.json` | Tiến bộ luyện cũ (chỉ đọc một lần để chép, D-48) | `learners_load` |
| `learners.json` | Người học + lịch sử bài câu (tự tạo, D-48) | `learners_load` / `learners_save` |

## 4. Bất biến kỹ thuật (không được phá)

| # | Quy tắc | Vì sao |
|---|---|---|
| I1 | Worker thread **không** chạm widget. Mọi cập nhật UI đi qua `self._queue` và `_poll()` (80 ms). | Tk không thread-safe; crash ngẫu nhiên. |
| I2 | Chấm điểm bằng ASR trên **bản ghi của người học**, không dùng transcript của file mẫu. | Lỗi cũ #4 trong `PHASE2-DANH-GIA-DU-AN-CU.md`. |
| I3 | Không chấm khi tín hiệu gần như im lặng (đỉnh < 0,8% ≈ -42 dB, sàn cho mic array laptop yếu; nền nhiễu mic thường < 0,1% — xem D-21), < 0,5 s, hoặc không nghe thấy giọng. | Whisper "bịa" trên nền im lặng. |
| I4 | Điểm chính chỉ là `correct / total` theo từ. `warns`/`tones` là cảnh báo, **không trừ điểm**. | Con số phải giải thích được. |
| I5 | F0 luôn quy về **bán cung so với trung vị của chính người nói**, không so Hz tuyệt đối. | Khác giới tính/độ tuổi. |
| I6 | (Oriole: GOP) — không áp dụng; Hoa Mi không có GOP. Nếu thêm chấm âm học cho tiếng Việt, phải so **bản mẫu người thật cùng câu**. | Tránh báo oan do model yếu. |
| I7 | Mọi con số âm học (nếu có) **không phải % phát âm đúng**; ghi chú trong UI. | Tránh hiểu sai. |
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

# Chạy App thật qua mọi màn/bài (không mic/model); --shots cần Pillow
& $PY tools\ui_check.py --shots $env:TEMP\hoami_ui

# Đo chuỗi thu âm → nhận dạng (cần model Whisper; chạy trước/sau khi sửa audio/ASR — D-36)
& $PY tools\asr_bench.py --out $env:TEMP\b_before.json
& $PY tools\asr_bench.py --compare $env:TEMP\b_before.json

# Cú pháp toàn bộ module Python
& $PY -m py_compile app.py prosody.py gen_mau.py tools\context_check.py tools\smoke_test.py tools\asr_bench.py tools\ui_check.py
```

- Không có `pytest`; test là script stdlib. Nếu thêm pytest, phải ghi vào
  `requirements.txt` và `DECISIONS.md`.
- Model Whisper mặc định `base`; bài tiếng Việt tự dùng `small` nếu có trên máy (D-37).
- Đường dẫn có dấu cách: luôn quote trong PowerShell.

## 6. Bộ skills

| Skill ID | Dùng khi |
|---|---|
| `project-context` | Mở/đóng phiên, chuyển AI model, khôi phục context, cập nhật handoff |
| `app-transcription` | File/ghi âm → văn bản, SRT/TXT, model Whisper, hủy, tiến trình |
| `app-youtube` | yt-dlp, chọn phụ đề, tải video/audio, nhúng phụ đề |
| `app-recording` | Micro, thu âm tự dừng, chuẩn hóa audio, WAV 16k |
| `app-pronunciation` | Chấm L1, lỗi n/l, thanh điệu, vần, giọng Bắc, kết quả UI |
| `app-prosody` | F0, ngữ điệu, biểu đồ cao độ |
| `app-ui` | Tkinter, theme, DPI, bố cục, cài đặt, phím tắt |
| `app-lessons` | Thêm/sửa bài (`PRACTICE_SETS`, `GUIDES`), audio mẫu, `gen_mau.py` |
| `app-qa-release` | Nghiệm thu, smoke test, dependency, đóng gói, `run.bat` |
| `skill-authoring` | Tạo/sửa skill trong repo này |

Skill chỉ được nạp khi cần. Nếu một skill mâu thuẫn với code, sửa skill ngay.

## 7. Definition of Done

Một thay đổi chỉ "xong" khi:
- [ ] Chạy được `tools/context_check.py`, `tools/smoke_test.py` và `tools/ui_check.py`.
- [ ] `py_compile` sạch.
- [ ] Luồng liên quan được thử thủ công (hoặc ghi rõ "chưa thử được vì …").
- [ ] Không phá bất biến §4.
- [ ] `PROJECT-STATE` + `HANDOFF` đã cập nhật.
- [ ] Nếu đổi hành vi người dùng: cập nhật `README.md` và copy UI tiếng Việt.

## 8. Không làm

- Không tự ý tái cấu trúc `app.py` thành nhiều package trong một phiên không liên quan.
- Không thêm tính năng "chấm ngữ điệu/giọng" bằng cách so MFCC/DTW hai người.
- Không hiển thị điểm khi thiếu bằng chứng.
- Không thêm lại phần tiếng Anh — thuộc Oriole (HM-01). Sửa lỗi phần dùng chung: `git cherry-pick`
  từ Oriole (xem `docs/UPSTREAM.md`).
- Không đổi khóa kết quả (`cues`, `score`, `items`, `gop`, `inton`…) mà không cập nhật
  `_prac_done`/`_on_result`.
- Không commit file tải về, model, `__pycache__`, hay dữ liệu cá nhân.
- Không bịa kết quả kiểm thử. Ghi "chưa kiểm chứng" nếu chưa chạy.
