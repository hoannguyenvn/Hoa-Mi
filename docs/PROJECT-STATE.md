# PROJECT STATE — Oriole

- **Cập nhật lần cuối:** 2026-10-25 (D-49 tách sản phẩm: Oriole = tiếng Anh; ROADMAP thêm phase S, L, A)
- **Phiên bản code:** 2.3 (`VERSION` trong `app.py`)
- **Trạng thái:** chạy được trên máy hiện tại; git repo `main` (D-33); chưa có test tự động đầy đủ.
- **Nguồn sự thật:** code + `docs/context-map.json`. Tài liệu này chỉ tóm tắt.

## 1. Đang làm / làm tiếp

> Cập nhật mục này ở **cuối mỗi phiên**. Tối đa 3 việc.

- [ ] **S — Tách sản phẩm (D-49, ROADMAP phase S):** Oriole chỉ còn cho người học tiếng Anh; luyện
  tiếng Việt (N/L, thanh) sang app riêng. **Kế tiếp: S1** — người dùng trả lời Q-06 (tên + repo app
  mới) và Q-05 (giữ tab Chuyển văn bản?); tag `split-base-vi`; rồi S2 (dựng app mới từ bản clone).
  **Chưa gỡ gì khỏi Oriole** — S3 chỉ sau khi app mới chạy được. Sau đó theo "Thứ tự đề xuất" trong
  ROADMAP: A1–A4 (âm mẫu 24 kHz, cắt đuôi âm cuối, tanh, cảnh báo bluetooth) → P1 + CI → L2 → L1.

- [ ] **P2 — Đại tu giao diện theo `docs/UI-PLAN.md`**: GATE A (D-27), font + app-style (D-28),
  GATE B (D-29…D-32) đã duyệt. **B1–B5 xong** (§5.1–5.6). **Kế tiếp: Phase 4** (UI-PLAN §7)
  — người dùng thử tay: file thật, YouTube thật, ghi âm 15 phút, luyện VI + EN, Esc giữa
  chừng, đổi bài, tối, cửa sổ nhỏ; scaling 100/150 % nếu có máy khác. Rồi Phase 5 (đóng
  gói tài liệu).
- [ ] **P5 — Đọc to transcript YouTube tiếng Anh (D-39, `docs/YT-READING-PLAN.md`):** Y1–Y3
  xong — chế độ **Từ YouTube** trong Luyện chạy được (thử bằng `ytread_e2e`, chưa thử mic thật).
  Người dùng thử với mic: chạy được, yêu cầu phản hồi cả câu → D-40 (R1–R6). **R1 xong** (giữ bản
  thu từng đoạn, Lưu bản thu…, từng câu ▶ Mẫu/▶ Bạn đọc, TRÔI CHẢY). Lưu bản thu thành nút rõ ràng (Documents\Oriole,
  lưu cả các đoạn). Đã phân tích 4 đoạn thật (HANDOFF): `PAUSE_*` giữ nguyên; bản đọc
  chấm bằng `medium` (D-41). Mục ÂM HAY SAI (D-42) và báo cáo cuối phiên + kết thúc sớm (D-43) xong. R2 ngữ điệu (D-44), R3 nhịp (D-45), R4 nối âm (D-46) xong; đoạn văn tách câu + in đậm
  từ nên nhấn + biểu đồ báo cáo (D-47); R6 hồ sơ người học + Tiến bộ (D-48). **Kế hoạch R1–R6 xong.**
  Còn ngỏ: nuốt âm (elision), xóa người học, so lần đọc lại cùng đoạn.
  Kế tiếp theo kế hoạch: **R6 lịch sử theo hồ sơ người học cục bộ** (D-39).
- [ ] **P4 — Chất lượng thu âm/nhận dạng + hiệu chuẩn điểm:** đợt 1 (D-36) + đợt 2 (D-37) xong.
  Bản thu thật đầu tiên (2026-10-24, `sound calibrate/`, 1 người đọc đoạn văn Việt 66 từ ~20 s,
  mic laptop + AirPods): đã đo, xem HANDOFF; giọng Bắc r/d/gi, s/x, tr/ch nay tính đúng (D-38).
  Kế tiếp: (a) thu thêm **bằng chính app** (tab Luyện, câu ngắn của bài
  — không phải đoạn văn) để kiểm `SNR_LOW_DB`, 1,8 s; (b) cổng SNR khi có dữ liệu phòng ồn thật;
  (c) so với giáo viên, chỉnh ngưỡng trước khi hứa "điểm phát âm".

Việc đang dở (nếu có): **chẩn đoán micro** — đã sửa 4 lỗi: lọc WDM-KS, ưu tiên
DirectSound, hạ sàn tín hiệu + gain +24 dB (D-20/D-21), hỗ trợ **mic ngoài** (Quét lại,
cảnh báo tai nghe bluetooth thiếu Hands-Free — D-22) và **thu bằng callback + queue**
(D-23: `stream.read` trên DirectSound trả toàn số 0 — nguyên nhân thật của "mic im lặng").
Còn **chưa kiểm chứng**: thu âm thật end-to-end **trong app** sau D-23. Bản ghi AirPods mới
(2026-10-24, thu bằng app Ghi âm Windows) đã nhận dạng tốt ngang mic laptop → lỗi "không ra
chữ" trước đó là do cách đeo/mic HFP, không phải pipeline.

## 2. Trạng thái từng tính năng

Ký hiệu: ✅ chạy ổn · 🟡 chạy nhưng có giới hạn · ⛔ chưa có.

| Tính năng | Trạng thái | Ghi chú ngắn |
|---|---|---|
| Chuyển file audio/video → text + SRT | ✅ | `faster-whisper` CPU int8, beam 5 |
| Ghi âm trực tiếp → text (tối đa 15 phút) | ✅ | dừng bằng tay (không tự dừng theo im lặng); chặn mic im lặng |
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
| Mic ngoài (USB/bluetooth): Quét lại, cảnh báo Hands-Free | 🟡 | `rescan_audio_devices`, `headset_mic_missing` (D-22); bản ghi AirPods 2026-10-24 nhận dạng ngang mic laptop (chưa thử thu trong app) |
| Context + skills cho AI | ✅ | `AGENTS.md`, `docs/`, 11 skill; `context_check` 40 OK |
| Test tự động | 🟡 | 74 test khói + `context_check` + `tools/ui_shots.py` (chụp UI, xem bằng mắt) + `tools/asr_bench.py` (thu → nhận dạng trên mẫu TTS + mic giả lập, D-36); chưa có test mic thật |
| Đóng gói `.exe` | ⛔ | chỉ có `run.bat` + Conda Python |
| Git / CI | 🟡 | git `main` + GitHub riêng tư (D-33); chưa có CI |

## 3. Nợ kỹ thuật & rủi ro đã biết

| Mức | Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|---|
| Cao | `app.py` ~8.700 dòng, UI + pipeline + scoring chung một file | khó review, dễ tạo circular change | tách dần theo skill; không tái cấu trúc big-bang |
| Cao | Chưa có test UI/ASR/mic; `smoke_test` chỉ phủ hàm thuần | sửa UI/luồng có thể phá mà không báo | mở rộng dần; ghi rõ "chưa kiểm chứng" |
| TB | Skill/tài liệu có thể lệch code nếu sửa mà không cập nhật | model sau làm sai chỗ | luôn chạy `context_check` + sửa tài liệu cùng phiên |
| Cao | Chưa hiệu chuẩn thang điểm với giáo viên | người học không biết tin điểm đến đâu | thu ~100 bản ghi, 2 giáo viên chấm, Spearman |
| TB | Trọng âm từ dựa trên cường độ + cao độ, chưa thử với bản thu người thật; mốc từ Whisper có thể lệch ±50 ms | đánh dấu nhầm từ được nhấn | chỉ mô tả (D-34); hiệu chuẩn cùng P4 |
| Thấp | Chưa thử UI ở Windows scaling 100 %/150 % (máy này 250 %) | chữ/nút có thể lệch | thử trên máy khác hoặc đổi scaling rồi chạy `tools/ui_shots.py` |
| Thấp | `save_frames_wav` (resample + `enhance_audio`, đã vector hóa) chạy trên main thread | bản ghi 15 phút làm UI đứng ~1,7 s | đưa vào worker nếu người dùng thấy khó chịu |
| TB | `asr_bench` mặc định dùng giọng TTS + mic giả lập | cải thiện trên bộ đo chưa chắc đúng với giọng thật | thêm bản ghi thật vào `--dir`; không dùng để hiệu chuẩn điểm (I13) |
| **Cao** | Whisper là mô hình ngôn ngữ: "sửa" từ đọc sai thành từ đúng với xác suất cao (TTS "Tink" → "Think" p 0,80) | chấm theo từ dễ dãi; xác suất từ (D-37) **không** bắt được | tiếng Anh: GOP gạch cam (D-35); tiếng Việt: chưa có — cần F0/âm học (P3) |
| TB | `lessons_en.json` có trường `samples` nhưng app bỏ qua, tự ghép `en/<id>.wav` | sửa JSON không có tác dụng | thống nhất một nguồn; ghi trong skill `app-lessons` |
| TB | SRT/VTT parser tự viết | format lạ có thể sai | thêm fixture test |
| TB | Phụ thuộc YouTube/yt-dlp | gãy theo thời gian | log lỗi rõ, test thủ công định kỳ |
| TB | yt-dlp 2026.08 cảnh báo thiếu JS runtime (`deno`) — app ẩn cảnh báo (`no_warnings`) | YouTube có thể trả thiếu format/403 khi đổi API | cân nhắc cài `deno` hoặc gói `yt-dlp[default]`; hiện tải vẫn chạy (2026-10-22) |
| Thấp | `bv*[ext=mp4]` có thể chọn AV1 (`av01`) | máy thiếu AV1 codec không phát được MP4 | cân nhắc ưu tiên `vcodec^=avc1` — cần quyết định, skill đang khóa chuỗi format |
| **Cao** | Mic array Intel SST cho tín hiệu yếu (~2% đỉnh, RMS ~0,5%) | phải hạ sàn + tăng gain; chưa kiểm chứng Whisper nhận đúng ở mức này | tăng Microphone Level 100%/Boost; nếu vẫn kém, dùng mic ngoài; theo dõi D-21 |
| **Cao** | Người Việt đọc trôi chảy đoạn văn 66 từ chỉ được **67–74 %** từ đúng với `small` (2026-10-24, sau D-38); phần lớn "lỗi" là Whisper nghe nhầm (hươu nai→"hiệu nay") | điểm tiếng Việt dễ làm người học nản / hiểu sai | đo lại với câu ngắn của bài; P3 (F0) |
| Thấp | `base` yếu với tiếng Việt (`vi_cau.wav` → "là nằm này lên lắm") | bài Việt nay tự dùng `small` nếu có trên máy (D-37); máy chưa tải `small` vẫn dùng `base` | nút/hướng dẫn tải `small` nếu người dùng gặp |
| TB | GOP tải model 1,2 GB lần đầu | lần chấm đầu rất chậm | thông báo tiến trình, cache, có nút cài |
| Thấp | Chưa có icon/ bản cài | khó phát hành | packaging sau khi 2A ổn |
| Thấp | Console cp1252 làm mất tiếng Việt khi in | script log lỗi | luôn đặt `PYTHONIOENCODING=utf-8` |

## 4. Câu hỏi cần người dùng quyết

Từ `PHASE2-DANH-GIA-DU-AN-CU.md` §8, vẫn còn mở:

1. ~~Ưu tiên tiếng Việt hay tiếng Anh?~~ — đóng bởi D-49: Oriole = tiếng Anh.
2. Có chấp nhận thêm ~120 MB cho gói GOP tiếng Anh (onnxruntime + model) không,
   hay giữ app thuần nhẹ?
3. Âm mẫu: tiếp tục TTS (edge-tts) hay thu/kiếm bản ghi người thật cho ~20 bài cốt lõi?
4. Có cần xuất PDF báo cáo không, hay TXT/CSV là đủ?
5. (Q-05) Oriole giữ tab Chuyển văn bản hay chỉ còn luyện tiếng Anh? Đề xuất: giữ.
6. (Q-06) Tên + repo GitHub của app luyện tiếng Việt?

Khi người dùng trả lời, ghi thành `D-xx` trong `docs/DECISIONS.md` và cập nhật mục 1.

## 5. Cách xác minh nhanh hiện trạng

```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\context_check.py
& "C:\Users\ADMIN\miniforge3\python.exe" tools\smoke_test.py
& "C:\Users\ADMIN\miniforge3\python.exe" -m py_compile app.py pron_en.py gop.py prosody.py yt_read.py gen_mau.py tools\build_lessons.py tools\context_check.py tools\smoke_test.py
```

Kết quả lần chạy gần nhất: xem `docs/CONTEXT-SNAPSHOT.md` (file sinh tự động).

Ghi chú chẩn đoán mic: test `recorder_uses_callback_not_blocking_read` chặn việc quay lại
`stream.read`. Muốn kiểm tra mic thật: tab Cài đặt → **Kiểm tra** (2 s), hoặc thu bằng
`Recorder` trên dev 5 — peak nền phải **> 0** (trước D-23 là đúng 0,000 %).
