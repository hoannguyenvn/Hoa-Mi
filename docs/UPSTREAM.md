# PHẦN DÙNG CHUNG VỚI ORIOLE

Hoa Mi tách từ Oriole (`hoannguyenvn/oriole`) tại commit `957f995` (2026-10-25, HM-01).
Hai repo có **chung lịch sử git** trước điểm đó, nên sửa lỗi phần dùng chung chuyển qua lại
bằng `git cherry-pick` — không chép tay.

## Cách lấy một bản sửa từ Oriole

```powershell
git remote add oriole https://github.com/hoannguyenvn/oriole   # một lần
git fetch oriole main
git cherry-pick <sha>          # xung đột → giữ phần Hoa Mi, áp phần sửa
& $PY tools\smoke_test.py; & $PY tools\ui_check.py; & $PY tools\context_check.py
```

Ghi vào bảng dưới mỗi lần chuyển (cả hai chiều).

## Phần dùng chung (sửa ở đâu thì nên chuyển sang bên kia)

| Nhóm | Symbol trong `app.py` |
|---|---|
| Thu âm + micro | `Recorder`, `list_input_mics`, `list_usable_mics`, `rescan_audio_devices`, `headset_mic_missing`, `pick_default_mic`, `probe_input_levels`, `best_input_mic` |
| Xử lý audio | `resample_to_16k`, `lowpass_kernel`, `highpass_1pole_kernel`, `enhance_audio`, `speech_peak`, `estimate_snr_db`, `save_frames_wav`, `play_wav_file`, `play_wav_segment` |
| Nhận dạng | `load_model`, `transcribe_practice`, `PRAC_ASR_OPTS`, `whisper_model_on_disk` |
| Chấm L1 + cổng | `norm_words`, `score_pronunciation`, `evidence_gate`, `build_result_view` (khung), `stage_words` |
| Phụ đề / YouTube tải | `_parse_sub_text`, `_fix_cues`, `split_long_cues`, `cues_to_srt`, `pick_subtitle_source`, `yt_build_opts`, `mux_subtitles_into_video` |
| Người học | `learners_load`, `learners_save`, `learner_add`, `learner_rename`, `hist_add_try` |
| UI khung | theme, font, `px`, thanh điều hướng, `_poll` |
| Công cụ | `tools/smoke_test.py` (phần chung), `tools/ui_check.py`, `tools/context_check.py`, `tools/asr_bench.py` |

## Nhật ký chuyển

| Ngày | Chiều | Commit | Nội dung |
|---|---|---|---|
| 2026-10-25 | Hoa Mi → Oriole | (Hoa Mi `f31de82`) | `headset_mic_missing` không import sounddevice khi đã truyền danh sách thiết bị |
