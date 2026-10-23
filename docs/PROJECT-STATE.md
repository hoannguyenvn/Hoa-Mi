# PROJECT STATE — Oriole

- **Cập nhật lần cuối:** 2026-10-23 (xong B5: màn Văn bản + Cài đặt mới; panel kết quả rộng theo thử nghiệm thật)
- **Phiên bản code:** 2.3 (`VERSION` trong `app.py`)
- **Trạng thái:** chạy được trên máy hiện tại; git repo `main` (D-33); chưa có test tự động đầy đủ.
- **Nguồn sự thật:** code + `docs/context-map.json`. Tài liệu này chỉ tóm tắt.

## 1. Đang làm / làm tiếp

> Cập nhật mục này ở **cuối mỗi phiên**. Tối đa 3 việc.

- [ ] **P2 — Đại tu giao diện theo `docs/UI-PLAN.md`**: GATE A (D-27), font + app-style (D-28),
  GATE B (D-29…D-32) đã duyệt. **B1–B5 xong** (§5.1–5.6). **Kế tiếp: Phase 4** (UI-PLAN §7)
  — người dùng thử tay: file thật, YouTube thật, ghi âm 15 phút, luyện VI + EN, Esc giữa
  chừng, đổi bài, tối, cửa sổ nhỏ; scaling 100/150 % nếu có máy khác. Rồi Phase 5 (đóng
  gói tài liệu) và quyết định GOP vs câu trên sân khấu (xem rủi ro bên dưới).
- [ ] **P3 — Thanh điệu tiếng Việt bằng F0:** phân loại 6 thanh từ contour, so với mẫu
  cùng âm tiết; hiện "bạn đọc thanh sắc, mẫu là thanh huyền".
- [ ] **P4 — Hiệu chuẩn điểm:** thu bản ghi người thật, so với giáo viên, chỉnh ngưỡng
  trước khi hứa "điểm phát âm".

Việc đang dở (nếu có): **chẩn đoán micro** — đã sửa 4 lỗi: lọc WDM-KS, ưu tiên
DirectSound, hạ sàn tín hiệu + gain +24 dB (D-20/D-21), hỗ trợ **mic ngoài** (Quét lại,
cảnh báo tai nghe bluetooth thiếu Hands-Free — D-22) và **thu bằng callback + queue**
(D-23: `stream.read` trên DirectSound trả toàn số 0 — nguyên nhân thật của "mic im lặng").
Còn **chưa kiểm chứng**: thu âm thật end-to-end sau D-23; hai bản ghi AirPods của người
dùng (4,6 s và 5,7 s) có năng lượng nhưng Whisper `base` **và** `small` đều không nhận ra
chữ nào → nghi tai nghe chưa đeo đúng hoặc mic HFP kém; cần thử lại khi đã đeo tai nghe.

## 2. Trạng thái từng tính năng

Ký hiệu: ✅ chạy ổn · 🟡 chạy nhưng có giới hạn · ⛔ chưa có.

| Tính năng | Trạng thái | Ghi chú ngắn |
|---|---|---|
| Chuyển file audio/video → text + SRT | ✅ | `faster-whisper` CPU int8, beam 5 |
| Ghi âm trực tiếp → text (tối đa 15 phút) | ✅ | tự dừng sau 1,3 s im lặng; chặn mic im lặng |
| YouTube: chỉ transcript (không tải video) | ✅ | ưu tiên phụ đề có sẵn, fallback Whisper |
| YouTube: MP4/MP3 + phụ đề + nhúng mềm | ✅ | phụ thuộc `yt-dlp`/`ffmpeg`; dễ gãy khi YouTube đổi |
| Chọn ngôn ngữ phụ đề auto/vi/en | ✅ | có cảnh báo khi lấy bản dịch của YouTube |
| Xuất `.txt` / `.srt`, copy, mở thư mục | ✅ | SRT sinh từ cue chuẩn |
| Giao diện sáng/tối, DPI cao | ✅ | khung app-style (thanh điều hướng, D-28); mục theme ở thanh + radio Cài đặt cùng đổi; scale `winfo_fpixels` |
| Nhớ cài đặt | ✅ | `config.json`, chỉ khóa trong `DEFAULT_CFG` |
| 3 bộ câu Việt + 14 bài Anh + 5 bài "Học âm" | ✅ | tổng 18 mục trong combobox luyện câu |
| Chấm L1 theo từ (đúng/sai/thiếu/thừa) | ✅ | "Đúng c/t từ" + chip kèm từ máy nghe; "Hoàn hảo" chỉ khi đúng mọi từ |
| Không chấm khi máy không chắc (D-29) | 🟡 | `evidence_gate`: bịa câu/chuỗi rác/độ tin thấp → "Máy chưa nghe rõ"; ngưỡng chưa hiệu chuẩn với bản thu thật |
| Luật lỗi quen thuộc n/l, th, s/sh, âm cuối | ✅ | `flag_pair`, dựa trên chữ ASR |
| Phát hiện sai thanh điệu / vần tiếng Việt | 🟡 | so **chữ**: `tone` (bỏ dấu thanh), `rhyme` (bỏ mọi dấu) — chưa phân tích F0 |
| Phân tích âm vị tiếng Anh (CMUdict) | 🟡 | phụ âm đáng tin; nguyên âm có thể bỏ sót |
| GOP acoustic (wav2vec2 CTC) | 🟡 | tùy chọn, cần torch; chưa hiệu chuẩn với giáo viên |
| Biểu đồ ngữ điệu (F0, bán cung) | ✅ | câu nhận xét + nhãn từ; trọng âm + tốc độ (D-34); chỉ mô tả, **không chấm điểm** |
| Lịch sử tiến bộ | ✅ | lưu từng lần (`tries` ≤ 30, D-30), đường xu hướng 10 lần, âm hay sai theo ngôn ngữ |
| Mic: chọn, kiểm tra, tự dò mic có tín hiệu | 🟡 | lọc WDM-KS, ưu tiên DirectSound, sàn 0,8% + gain +24 dB (D-20/D-21), thu bằng callback + queue (D-23) |
| Mic ngoài (USB/bluetooth): Quét lại, cảnh báo Hands-Free | 🟡 | `rescan_audio_devices`, `headset_mic_missing` (D-22); AirPods đã lên thiết bị thu (WASAPI) nhưng bản ghi thử chưa nhận dạng được — xem mục 3 |
| Context + skills cho AI | ✅ | `AGENTS.md`, `docs/`, 11 skill; `context_check` 40 OK |
| Test tự động | 🟡 | 63 test khói + `context_check` + `tools/ui_shots.py` (chụp UI, xem bằng mắt); chưa có test ASR/mic |
| Đóng gói `.exe` | ⛔ | chỉ có `run.bat` + Conda Python |
| Git / CI | 🟡 | git `main` + GitHub riêng tư (D-33); chưa có CI |

## 3. Nợ kỹ thuật & rủi ro đã biết

| Mức | Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|---|
| Cao | `app.py` ~4.500 dòng, UI + pipeline + scoring chung một file | khó review, dễ tạo circular change | tách dần theo skill; không tái cấu trúc big-bang |
| Cao | Chưa có test UI/ASR/mic; `smoke_test` chỉ phủ hàm thuần | sửa UI/luồng có thể phá mà không báo | mở rộng dần; ghi rõ "chưa kiểm chứng" |
| TB | Skill/tài liệu có thể lệch code nếu sửa mà không cập nhật | model sau làm sai chỗ | luôn chạy `context_check` + sửa tài liệu cùng phiên |
| Cao | Chưa hiệu chuẩn thang điểm với giáo viên | người học không biết tin điểm đến đâu | thu ~100 bản ghi, 2 giáo viên chấm, Spearman |
| TB | Câu trên sân khấu theo chữ Whisper nghe ("Think ✓") nhưng CẦN SỬA (GOP) có thể báo âm /θ/ trong chính từ đó lệch rõ — người dùng thấy ở lần thử thật | hai tín hiệu trái nhau trên cùng màn | cần quyết định: gạch chân cam (không trừ điểm, I4) cho từ GOP báo lệch rõ? |
| TB | Trọng âm từ dựa trên cường độ + cao độ, chưa thử với bản thu người thật; mốc từ Whisper có thể lệch ±50 ms | đánh dấu nhầm từ được nhấn | chỉ mô tả (D-34); hiệu chuẩn cùng P4 |
| Thấp | Chưa thử UI ở Windows scaling 100 %/150 % (máy này 250 %) | chữ/nút có thể lệch | thử trên máy khác hoặc đổi scaling rồi chạy `tools/ui_shots.py` |
| TB | `enhance_audio` high-pass là vòng lặp Python từng mẫu, chạy trên main thread | bản ghi 15 phút làm UI đứng vài giây | vector hóa (numpy) hoặc đưa vào worker |
| TB | `load_model()` tạo model mới mỗi lần chấm | chậm, tốn RAM; mỗi câu luyện tốn thêm vài giây | cache theo `model_size` + khóa |
| TB | `lessons_en.json` có trường `samples` nhưng app bỏ qua, tự ghép `en/<id>.wav` | sửa JSON không có tác dụng | thống nhất một nguồn; ghi trong skill `app-lessons` |
| TB | SRT/VTT parser tự viết | format lạ có thể sai | thêm fixture test |
| TB | Phụ thuộc YouTube/yt-dlp | gãy theo thời gian | log lỗi rõ, test thủ công định kỳ |
| TB | yt-dlp 2026.08 cảnh báo thiếu JS runtime (`deno`) — app ẩn cảnh báo (`no_warnings`) | YouTube có thể trả thiếu format/403 khi đổi API | cân nhắc cài `deno` hoặc gói `yt-dlp[default]`; hiện tải vẫn chạy (2026-10-22) |
| Thấp | `bv*[ext=mp4]` có thể chọn AV1 (`av01`) | máy thiếu AV1 codec không phát được MP4 | cân nhắc ưu tiên `vcodec^=avc1` — cần quyết định, skill đang khóa chuỗi format |
| **Cao** | Mic array Intel SST cho tín hiệu yếu (~2% đỉnh, RMS ~0,5%) | phải hạ sàn + tăng gain; chưa kiểm chứng Whisper nhận đúng ở mức này | tăng Microphone Level 100%/Boost; nếu vẫn kém, dùng mic ngoài; theo dõi D-21 |
| **Cao** | Hai bản ghi AirPods (4,6 s / 5,7 s) có năng lượng nói nhưng Whisper `base` và `small` đều **không ra chữ** (hallucination) | chưa chấm được điểm; dễ hiểu nhầm là "app nhận dạng sai" | thử lại khi **đeo** tai nghe (mic AirPods nằm trên thân); nếu vẫn kém → mic USB hoặc mic array |
| TB | `base` yếu với tiếng Việt: file mẫu sạch `mau/vi_cau.wav` → "là nằm này lên lắm" | người dùng tưởng do phát âm | khuyến nghị model `small` cho tiếng Việt; ghi trong UI/README |
| TB | GOP tải model 1,2 GB lần đầu | lần chấm đầu rất chậm | thông báo tiến trình, cache, có nút cài |
| Thấp | Chưa có icon/ bản cài | khó phát hành | packaging sau khi 2A ổn |
| Thấp | Console cp1252 làm mất tiếng Việt khi in | script log lỗi | luôn đặt `PYTHONIOENCODING=utf-8` |

## 4. Câu hỏi cần người dùng quyết

Từ `PHASE2-DANH-GIA-DU-AN-CU.md` §8, vẫn còn mở:

1. Ưu tiên Phase 2: **tiếng Việt** (luật + thanh điệu) hay **tiếng Anh** (GOP) trước?
2. Có chấp nhận thêm ~120 MB cho gói GOP tiếng Anh (onnxruntime + model) không,
   hay giữ app thuần nhẹ?
3. Âm mẫu: tiếp tục TTS (edge-tts) hay thu/kiếm bản ghi người thật cho ~20 bài cốt lõi?
4. Có cần xuất PDF báo cáo không, hay TXT/CSV là đủ?

Khi người dùng trả lời, ghi thành `D-xx` trong `docs/DECISIONS.md` và cập nhật mục 1.

## 5. Cách xác minh nhanh hiện trạng

```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\context_check.py
& "C:\Users\ADMIN\miniforge3\python.exe" tools\smoke_test.py
& "C:\Users\ADMIN\miniforge3\python.exe" -m py_compile app.py pron_en.py gop.py prosody.py gen_mau.py tools\build_lessons.py tools\context_check.py tools\smoke_test.py
```

Kết quả lần chạy gần nhất: xem `docs/CONTEXT-SNAPSHOT.md` (file sinh tự động).

Ghi chú chẩn đoán mic: test `recorder_uses_callback_not_blocking_read` chặn việc quay lại
`stream.read`. Muốn kiểm tra mic thật: tab Cài đặt → **Kiểm tra** (2 s), hoặc thu bằng
`Recorder` trên dev 5 — peak nền phải **> 0** (trước D-23 là đúng 0,000 %).
