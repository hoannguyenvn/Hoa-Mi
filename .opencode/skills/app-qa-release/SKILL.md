---
name: App QA & Release
description: Nghiệm thu và đóng gói Oriole — chạy context_check, smoke_test, py_compile, ma trận kiểm thử thủ công (file, YouTube, micro, luyện phát âm, theme/DPI), dependency, run.bat và giới hạn khi phát hành. Dùng khi người dùng nhắc tới test, kiểm thử, nghiệm thu, đóng gói, run.bat, requirements, cài đặt máy mới, hoặc trước khi bàn giao.
---

# QA & Release

Không có pytest, không có CI, chưa có git. Lưới an toàn là **3 lệnh** + ma trận
kiểm thử thủ công. Không bịa kết quả: mục nào không chạy được thì ghi
"chưa kiểm chứng" kèm lý do.

## 1. Ba lệnh bắt buộc

```powershell
$PY = "C:\Users\ADMIN\miniforge3\python.exe"
$env:PYTHONIOENCODING='utf-8'          # console hay là cp1252

& $PY tools\context_check.py            # tài liệu/symbol/skill/asset
& $PY tools\context_check.py --snapshot # sinh docs/CONTEXT-SNAPSHOT.md
& $PY tools\smoke_test.py               # 64 test khói
& $PY tools\ui_shots.py before          # chụp 21 trạng thái UI vào %TEMP%\oriole_shots\before
& $PY -m py_compile app.py pron_en.py gop.py prosody.py gen_mau.py tools\build_lessons.py tools\context_check.py tools\smoke_test.py
```

- `context_check` FAIL ⇒ **dừng**, sửa drift trước khi thêm tính năng.
- `smoke_test` in `TỔNG: N/N PASS`; exit code 1 nếu có FAIL.
- `py_compile` không in gì = OK; `__pycache__` không được commit/chia sẻ.
  Liệt kê file rõ ràng: PowerShell **không** mở rộng `tools\*.py` cho lệnh native.

### `smoke_test.py` phủ gì (64 case)

| Nhóm | Case |
|---|---|
| Bài học | `lessons_loaded` (18 SET_IDS), `lessons_have_samples` |
| L1 | đọc đúng 100%, th/tink, n/l, sai thanh điệu, `strip_tone_vi`, từ thừa, `norm_words`, `flag_pair` |
| Cue/SRT | timestamp, txt có giờ, `_fix_cues`, `split_long_cues` |
| Audio | `resample_length`, silence quiet, chuẩn hóa gain |
| Âm vị/F0 | IPA `think`, `analyze_pairs`, sine 150 Hz |
| Audio (tiếp) | `enhance_lifts_weak_mic` (D-21) |
| Config | khóa + kiểu khớp `DEFAULT_CFG` |
| Micro | `usable_mics_drops_wdmks`, `pick_default_prefers_real_mic`, `headset_without_mic_is_detected`, `recorder_uses_callback_not_blocking_read` (D-20/22/23) |
| YouTube | `yt_worker_always_reports_back` (D-24), `yt_subtitle_429_falls_back_not_fatal` (D-25), `yt_progress_is_a_fraction` |
| File tạm (I10) | `remove_temp_is_safe`, `practice_replay_wav_is_replaced_not_leaked`, `w_file_removes_temp_recording_on_error` |
| Luyện / recorder | `practice_hyp_falls_back_to_segment_text`, `recording_belongs_to_one_tab` |
| View / trạng thái / lịch sử (B2) | `result_view_english_errors`, `result_view_perfect_and_extras`, `result_view_vietnamese_counts_by_lesson_language`, `result_view_gop_levels_not_percent`, `screen_states_drive_controls`, `history_keeps_tries_and_migrates`, `weakest_sound_is_per_language`, `practice_keeps_word_timings` |
| Cổng bằng chứng / tiếng Việt (B3) | `evidence_gate_blocks_hallucination_and_noise`, `unsure_view_shows_no_score_and_is_not_stored`, `perfect_needs_every_word`, `vietnamese_rhyme_state_named`, `vi_spell_splits_syllable`, `ipa_text_detected_for_font`, `wav_segment_bounds_clamped`, `theme_text_contrast_ok` |
| Khung app-style (B4a) | `stage_words_mark_each_original_word`, `shell_helpers` |
| Ngữ điệu, trọng âm, tiến bộ (B4b) | `stress_picks_loud_high_word`, `heard_words_map_to_target`, `intonation_caption_rules`, `speed_and_stress_sentences`, `intonation_view_labels_and_markers`, `progress_summary_lines` |
| Màn Văn bản (B5) | `transcription_screen_states` |
| GOP trên câu (D-35) | `gop_clearly_off_marks_stage_word` |
| Giao diện (B1) | `ui_font_bundled_and_registered`, `indicator_images_follow_theme`, `window_icon_drawn_in_code`, `language_names_map_to_codes` |

Chạy **trước và sau** mỗi thay đổi. Thêm hành vi mới ⇒ thêm case, không sửa case cũ
cho "xanh" trừ khi hành vi cố ý đổi (ghi lý do vào `DECISIONS.md`).

## 2. Ma trận kiểm thử thủ công

Đánh dấu ✅ / ❌ / ⚠ chưa kiểm chứng. Ghi tên file thật đã dùng.

| # | Luồng | Cách thử | Kỳ vọng |
|---|---|---|---|
| M1 | File audio | chọn `.mp3` 10–30 s → Bắt đầu | có văn bản + SRT, tiến trình chạy |
| M2 | File video | chọn `.mp4` có tiếng | có văn bản, không tải lại video |
| M3 | Xuất file | Lưu `.txt`, Lưu `.srt` | mở lại đúng tiếng Việt UTF-8 |
| M4 | Hủy | bấm Hủy giữa lúc nhận dạng | UI về idle, không treo, không rác |
| M5 | Ghi âm Tab 1 | nói 3 s → im lặng 1,5 s | tự dừng, ra văn bản |
| M6 | YouTube có phụ đề | link có vi/en | tải đúng ngôn ngữ, không chạy Whisper |
| M7 | YouTube không phụ đề | link không có sub | fallback Whisper ra SRT |
| M8 | YouTube video/audio | chọn MP4/MP3 | file trong `downloads/`, tên an toàn |
| M9 | Nhúng phụ đề | bật checkbox, mở VLC | bật/tắt phụ đề mềm được |
| M10 | Mic | Cài đặt → Kiểm tra mic → nói "a" | dB hợp lý, trạng thái TỐT/NHỎ/TO |
| M11 | Mic ngoài | kết nối tai nghe/USB → Quét lại → Tự dò | thấy thiết bị mới; bluetooth thiếu Hands-Free thì có gợi ý |
| M12 | Luyện đúng | đọc đúng câu bài `en_th` | điểm cao, không cảnh báo |
| M13 | Luyện sai âm | "think" → "tink" | báo âm vị TH, gợi ý lưỡi/răng |
| M14 | Im lặng | chấm file im lặng | **không** có điểm, báo lỗi rõ |
| M15 | Tiến bộ | luyện 2 lần | `n` tăng, best/last đúng |
| M16 | Ngữ điệu | bài có mẫu | biểu đồ hiện, nét đứt + nét liền |
| M17 | Theme | đổi Sáng/Tối | mọi widget đổi, mở lại vẫn nhớ |
| M18 | DPI | Windows 150% | chữ/nút không cắt, không chồng |
| M19 | Phím tắt | Ctrl+O/Ctrl+Enter/Ctrl+S/Esc | đúng hành vi |
| M20 | Đóng/mở | đổi kích thước → thoát → mở | geometry được nhớ |
| M21 | Rác tạm | luyện 5 lần → đóng app → xem `%TEMP%` | không còn `luyen_*.wav`/`stt_*.wav` mới (đã sửa 2026-10-22, chưa thử tay) |

Không thử được vì thiếu mic/model/mạng ⇒ ghi rõ, **không** ghi PASS.

## 3. Dependency

`requirements.txt`:

```
faster-whisper==1.2.1
av==19.0.1
sounddevice>=0.4
numpy>=1.24
yt-dlp>=2024.8.6
imageio-ffmpeg>=0.5.1
cmudict>=0.1.3
# tùy chọn
torch>=2.6
transformers>=4.40
edge-tts>=7.3.1        # chỉ khi sinh lại audio mẫu
```

- `context_check` bắt buộc 6 gói đầu: `faster-whisper`, `av`, `sounddevice`,
  `numpy`, `yt-dlp`, `imageio-ffmpeg`. Bỏ gói nào ⇒ FAIL.
- `torch`/`transformers` là **tùy chọn** cho GOP; thiếu thì app vẫn chạy, chỉ ẩn GOP.
- `edge-tts` chỉ dùng khi build bài/audio, không cần lúc chạy.
- Cài torch CPU:
  `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- Không thêm dependency nặng nếu numpy làm được (I8). Thêm gói ⇒ ghi `DECISIONS.md`.

## 4. `run.bat`

Luồng: `cd` về thư mục app → kiểm tra `C:\Users\ADMIN\miniforge3\python.exe` →
`import faster_whisper, sounddevice, yt_dlp, imageio_ffmpeg` → nếu thiếu thì
`pip install -r requirements.txt` → chạy `app.py` → `pause`.

- Đường dẫn Python **hard-code**; máy khác phải sửa `CONDA_PY`.
- `HF_HUB_DISABLE_SYMLINKS_WARNING=1` để bớt cảnh báo HuggingFace trên Windows.
- Không đặt `pip install` vào luồng chạy bình thường (chậm, cần mạng).
- Muốn đóng gói: giữ nguyên cấu trúc tương đối vì `BASE_DIR` lấy theo vị trí
  `app.py`; `mau/`, `lessons_en.json`, `README.md` phải nằm cạnh `app.py`.

## 5. Phát hành

### Trước khi bàn giao
- [ ] 3 lệnh ở §1 xanh.
- [ ] `VERSION` trong `app.py` khớp `v...` trong 400 ký tự đầu `README.md`
      (`context_check` kiểm tra).
- [ ] `docs/PROJECT-STATE.md` + `docs/HANDOFF.md` cập nhật kết quả **thật**.
- [ ] Không có `config.json`/`practice_history.json` chứa dữ liệu cá nhân,
      không có cookie/token (I16), không có `__pycache__`, model, file tải về.
- [ ] `mau/` đủ 12 + 74 WAV; `lessons_en.json` parse được.

### Gói tối thiểu để chạy
```
app.py  pron_en.py  gop.py  prosody.py
lessons_en.json  mau/  assets/fonts/  requirements.txt  run.bat  README.md
```
`config.json` và `practice_history.json` do app tự tạo.

### Chưa có (đừng hứa)
- Không `.exe`, không installer, không icon, không auto-update.
- Không GPU, không hàng đợi nhiều file, không xuất PDF/CSV.
- Lần chạy đầu cần mạng để tải model Whisper; GOP tải thêm ~1,2 GB.

## 6. Khi FAIL — xử lý

| Lỗi | Việc làm |
|---|---|
| `context_check`: thiếu symbol | symbol bị đổi tên → sửa `docs/context-map.json` hoặc khôi phục tên |
| `context_check`: thiếu skill/asset | tạo file, hoặc gỡ tên khỏi `context-map.json` nếu cố ý bỏ |
| `context_check`: VERSION lệch README | sửa một trong hai, không bỏ qua |
| `smoke_test`: `SET_IDS` | thêm/bớt bài → cập nhật assert |
| `smoke_test`: cue/SRT | sửa hàm thuần, không sửa test để né |
| `py_compile`: SyntaxError | sửa ngay; không chạy app khi compile lỗi |
| App mở rồi treo | xem console; thường do model tải hoặc mic độc quyền |

## 7. Báo cáo cuối phiên (mẫu)

```
Đã chạy:
  context_check.py        -> X OK / Y FAIL
  smoke_test.py           -> 64/64 PASS
  py_compile              -> OK
Đã thử tay:
  M1 (file mp3 14s)       -> PASS
  M12/M13 (en_th)         -> PASS
Chưa kiểm chứng:
  M6–M9 (YouTube)         -> không có mạng trong phiên
  M10–M11 (mic)           -> không có thiết bị
```
