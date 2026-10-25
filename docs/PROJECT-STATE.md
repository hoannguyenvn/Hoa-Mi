# PROJECT STATE — Hoa Mi

- **Cập nhật lần cuối:** 2026-10-25 (HM-01: tạo Hoa Mi từ Oriole @957f995)
- **Phiên bản code:** 1.0 (`VERSION` trong `app.py`)
- **Trạng thái:** luyện phát âm tiếng Việt (N/L, thanh, vần) + chuyển văn bản; kiểm bằng smoke 72/72,
  `ui_check`, `context_check` trên Linux — **chưa chạy trên Windows sau khi tách**.
- **Nguồn sự thật:** code + `docs/context-map.json`. Tài liệu này chỉ tóm tắt.

## 1. Đang làm / làm tiếp

> Cập nhật mục này ở **cuối mỗi phiên**. Tối đa 3 việc.

- [ ] **Người dùng thử Hoa Mi trên Windows** (`run.bat`): Luyện câu vi1–vi3, Học âm N/L, thu âm thật,
  Chuyển văn bản. Báo lỗi nếu có.
- [ ] **P1 + C1** (ROADMAP): CI GitHub Action; sinh `vi_nen.wav`, `vi_len.wav`.
- [ ] **C2/C3**: bài có cấu trúc, nghe phân biệt N/L; rồi **T1** thanh điệu bằng F0.

## 2. Trạng thái từng tính năng

Ký hiệu: ✅ chạy ổn · 🟡 chạy nhưng có giới hạn · ⛔ chưa có.

| Tính năng | Trạng thái | Ghi chú ngắn |
|---|---|---|
| Chuyển file audio/video → text + SRT | ✅ | `faster-whisper` CPU int8, beam 5 |
| Ghi âm trực tiếp → text (tối đa 15 phút) | ✅ | dừng bằng tay; chặn mic im lặng |
| YouTube: transcript / MP4 / MP3 + phụ đề | ✅ | phụ thuộc `yt-dlp`/`ffmpeg`; giữ theo HQ-01 |
| Giao diện sáng/tối, DPI cao, nhớ cài đặt | ✅ | khung app-style (D-28), `config.json` whitelist |
| 3 bộ câu N/L + Tùy chỉnh + 3 bài Học âm | ✅ | `PRACTICE_SETS`, `GUIDES`; 2 clip mẫu Học âm thiếu (C1) |
| Chấm L1 theo từ (đúng/sai/thiếu/thừa) | ✅ | "Đúng c/t từ"; "Hoàn hảo" chỉ khi đúng mọi từ |
| Không chấm khi máy không chắc (D-29) | 🟡 | `evidence_gate`; ngưỡng chưa hiệu chuẩn |
| Lỗi N/L, sai dấu thanh, sai vần | 🟡 | so **chữ** Whisper nghe; chưa phân tích F0 (T1) |
| Giọng Bắc r/d/gi, s/x, tr/ch tính đúng (D-38) | ✅ | chuẩn Nam: HQ-02 |
| Bài Việt chấm bằng `small` nếu có (D-37) | ✅ | không tự tải model (I9) |
| Biểu đồ ngữ điệu | ⛔ | code có; chưa bài nào có mẫu người thật (Q-03) |
| Người học + lịch sử bài câu (D-48) | ✅ | `learners.json`; không còn màn Tiến bộ YouTube |
| Lưu bản thu (Documents\Hoa Mi) | ✅ | wav + txt + json |
| Mic: chọn, kiểm tra, tự dò, mic ngoài | 🟡 | D-20…D-23; chưa thử lại sau khi tách |
| Test tự động | 🟡 | 72 smoke + `ui_check` + `context_check`; chưa CI |
| Đóng gói `.exe` | ⛔ | chỉ `run.bat` + Conda |

## 3. Nợ kỹ thuật & rủi ro đã biết

| Mức | Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|---|
| Cao | `app.py` ~8.700 dòng, UI + pipeline + scoring chung một file | khó review, dễ tạo circular change | tách dần theo skill; không tái cấu trúc big-bang |
| Cao | Chưa có test ASR/mic; `smoke_test` phủ hàm thuần, `ui_check` chạy UI với kết quả giả | sửa UI/luồng có thể phá mà không báo | mở rộng dần; ghi rõ "chưa kiểm chứng" |
| TB | Skill/tài liệu có thể lệch code nếu sửa mà không cập nhật | model sau làm sai chỗ | luôn chạy `context_check` + sửa tài liệu cùng phiên |
| Cao | Chưa hiệu chuẩn thang điểm với giáo viên | người học không biết tin điểm đến đâu | thu ~100 bản ghi, 2 giáo viên chấm, Spearman |
| Thấp | Chưa thử UI ở Windows scaling 100 %/150 % (máy này 250 %) | chữ/nút có thể lệch | thử trên máy khác hoặc đổi scaling rồi chạy `tools/ui_shots.py` |
| Thấp | `save_frames_wav` (resample + `enhance_audio`, đã vector hóa) chạy trên main thread | bản ghi 15 phút làm UI đứng ~1,7 s | đưa vào worker nếu người dùng thấy khó chịu |
| TB | `asr_bench` mặc định dùng giọng TTS + mic giả lập | cải thiện trên bộ đo chưa chắc đúng với giọng thật | thêm bản ghi thật vào `--dir`; không dùng để hiệu chuẩn điểm (I13) |
| TB | SRT/VTT parser tự viết | format lạ có thể sai | thêm fixture test |
| TB | Phụ thuộc YouTube/yt-dlp | gãy theo thời gian | log lỗi rõ, test thủ công định kỳ |
| TB | yt-dlp 2026.08 cảnh báo thiếu JS runtime (`deno`) — app ẩn cảnh báo (`no_warnings`) | YouTube có thể trả thiếu format/403 khi đổi API | cân nhắc cài `deno` hoặc gói `yt-dlp[default]`; hiện tải vẫn chạy (2026-10-22) |
| Thấp | `bv*[ext=mp4]` có thể chọn AV1 (`av01`) | máy thiếu AV1 codec không phát được MP4 | cân nhắc ưu tiên `vcodec^=avc1` — cần quyết định, skill đang khóa chuỗi format |
| **Cao** | Mic array Intel SST cho tín hiệu yếu (~2% đỉnh, RMS ~0,5%) | phải hạ sàn + tăng gain; chưa kiểm chứng Whisper nhận đúng ở mức này | tăng Microphone Level 100%/Boost; nếu vẫn kém, dùng mic ngoài; theo dõi D-21 |
| **Cao** | Người Việt đọc trôi chảy đoạn văn 66 từ chỉ được **67–74 %** từ đúng với `small` (2026-10-24, sau D-38); phần lớn "lỗi" là Whisper nghe nhầm (hươu nai→"hiệu nay") | điểm tiếng Việt dễ làm người học nản / hiểu sai | đo lại với câu ngắn của bài; P3 (F0) |
| Thấp | `base` yếu với tiếng Việt (`vi_cau.wav` → "là nằm này lên lắm") | bài Việt nay tự dùng `small` nếu có trên máy (D-37); máy chưa tải `small` vẫn dùng `base` | nút/hướng dẫn tải `small` nếu người dùng gặp |
| Thấp | Chưa có icon/ bản cài | khó phát hành | packaging sau khi 2A ổn |
| Thấp | Console cp1252 làm mất tiếng Việt khi in | script log lỗi | luôn đặt `PYTHONIOENCODING=utf-8` |
| **Cao** | Whisper là mô hình ngôn ngữ: "sửa" từ đọc sai thành từ đúng theo ngữ cảnh — với tiếng Việt dễ bỏ lọt **sai dấu thanh** | điểm dễ dãi | T1 (F0) |
| TB | `GUIDES` trỏ `vi_nen.wav`, `vi_len.wav` chưa có trong `mau/` | nút ▶ xám ở Học âm N/L | C1: chạy `gen_mau.py` |
| Thấp | Icon vẫn là logo Oriole (`logo_rows`); nhãn "Người học" bị cắt ở thanh trái hẹp | nhận diện, thẩm mỹ | P7 |
| TB | Code ngữ điệu/trọng âm kế thừa từ tiếng Anh, chưa bài nào dùng | dư code | thay khi làm T1 |


## 4. Câu hỏi cần người dùng quyết

Xem `docs/DECISIONS.md` §C: **HQ-01** (giữ tab Chuyển văn bản?), **HQ-02** (chuẩn giọng Nam?),
**Q-03** (âm mẫu người thật cho thanh điệu?).

## 5. Cách xác minh nhanh hiện trạng

```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\context_check.py
& "C:\Users\ADMIN\miniforge3\python.exe" tools\smoke_test.py
& "C:\Users\ADMIN\miniforge3\python.exe" tools\ui_check.py
& "C:\Users\ADMIN\miniforge3\python.exe" -m py_compile app.py prosody.py gen_mau.py tools\context_check.py tools\smoke_test.py tools\ui_check.py
```

Kết quả lần chạy gần nhất: xem `docs/CONTEXT-SNAPSHOT.md` (file sinh tự động).

Ghi chú chẩn đoán mic: test `recorder_uses_callback_not_blocking_read` chặn việc quay lại
`stream.read`. Muốn kiểm tra mic thật: tab Cài đặt → **Kiểm tra** (2 s), hoặc thu bằng
`Recorder` trên dev 5 — peak nền phải **> 0** (trước D-23 là đúng 0,000 %).
