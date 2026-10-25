# KIẾN TRÚC — Hoa Mi v1.0

Mục đích: đủ để một model chưa từng đọc repo hiểu luồng dữ liệu, chỗ sửa, và
các ràng buộc thread/UI mà không phải đọc 3.300 dòng `app.py`.

## 1. Sơ đồ tổng thể

```
┌──────────────────────────── Tk main thread ────────────────────────────┐
│  App(tk.Tk)                                                            │
│  ├─ Tab 1 "Chuyển thành văn bản": nguồn File / YouTube / Ghi âm        │
│  ├─ Tab 2 "Luyện phát âm": Bài luyện | Kết quả | Ngữ điệu              │
│  ├─ Tab 3 "Cài đặt": model, ngôn ngữ, micro, thư mục, theme            │
│  ├─ _poll() mỗi 80 ms: đọc self._queue → cập nhật widget                │
│  └─ Recorder (sounddevice InputStream) chạy thread riêng               │
└───────────────▲───────────────────────────────────────┬────────────────┘
                │ queue.put(("status"|"progress"|...))  │
┌───────────────┴───────────────────────────────────────▼────────────────┐
│  Worker threads (daemon)                                               │
│  ├─ App._w_file      : Whisper → cues → payload                        │
│  ├─ App._w_yt        : yt-dlp → phụ đề/Whisper → .srt/.txt → mux       │
│  ├─ App._w_prac      : Whisper word timestamps → L1 → inton (nếu mẫu)  │
│  └─ mic probe / play / test mic                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Quy tắc vàng:** worker chỉ `queue.put(...)`; mọi thứ chạm `tk`/`ttk` nằm ở
main thread (`_poll`, `_on_result`, `_prac_done`, `_prac_error`).

## 2. Các module

| Module | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `app.py` | UI, điều phối, ASR, subtitle I/O, mic, L1 scoring, lịch sử | tkinter, numpy, faster-whisper, sounddevice, yt-dlp |
| `prosody.py` | đọc WAV, F0 autocorrelation, contour bán cung, DTW | numpy |
| `mau/` | audio mẫu tiếng Việt offline (TTS, edge-tts, chỉ để nghe) | — |
| `gen_mau.py` | sinh âm mẫu `vi_*.wav` | edge-tts, mạng |
| `tools/ui_check.py` | chạy App thật qua mọi màn/bài, bắt lỗi callback | tkinter (Pillow tùy chọn) |

## 3. Mô hình dữ liệu

### 3.1. Cue (đơn vị phụ đề)

Một cue là tuple 3 phần tử: `(start_sec: float, end_sec: float, text: str)`.
Toàn bộ pipeline văn bản dùng chung kiểu này.

```python
cues = [(0.0, 2.4, "Xin chào"), (2.4, 5.1, "hôm nay trời đẹp")]
```

Các hàm thuần (dễ test, không phụ thuộc UI):
- `_parse_ts`, `_clean_cue`, `_parse_sub_text`, `_parse_json3`
- `_dedupe_cues` (cả phụ đề tự động dạng cuộn), `_fix_cues` (sort + chống chồng lấn + đảm bảo duration tối thiểu)
- `split_long_cues(cues, max_chars=92)`
- `cues_to_srt`, `cues_to_txt`

### 3.2. Kết quả chuyển văn bản (`payload`)

`_on_result(p)` đọc các khóa:

| Khóa | Kiểu | Ý nghĩa |
|---|---|---|
| `cues` | `list[tuple]` | nội dung chính |
| `media` | `str \| None` | file media gốc/bản tải (None nếu chỉ transcript) |
| `base` | `str` | tên file không phần mở rộng để lưu |
| `srt`, `txt` | `str \| None` | file đã ghi (YouTube), None nếu chưa ghi |
| `note` | `str` | dòng trạng thái cuối |

### 3.3. Kết quả chấm phát âm (`res`)

`_w_prac` tạo dict, `_prac_done` render:

| Khóa | Kiểu | Ý nghĩa |
|---|---|---|
| `items` | `list[(target, state, heard, note)]` | state ∈ `ok/warn/tone/bad/extra` |
| `score`, `correct`, `total`, `warns`, `tones` | số | L1 |
| `hyp` | `str` | chuỗi máy nghe được |
| `target`, `det_lang` | `str` | câu mẫu, ngôn ngữ phát hiện |
| `conf`, `low_conf`, `garbage` | số/bool | cổng tin cậy |
| `phon` | `dict` | luôn rỗng ở Hoa Mi (khóa giữ cho ổn định, HM-01) |
| `gop` | `None` | luôn `None` ở Hoa Mi |
| `inton` | `dict \| None` | `prosody.compare(ref, usr)` |
| `words_t` | `list[{w, s, e, p}]` | từ Whisper nghe + giây bắt đầu/kết thúc + xác suất (cho nhãn biểu đồ, S-5) |
| `stress` | `{"usr", "ref", "ref_words"}` \| `None` | trọng âm từng từ (`prosody.word_stress`) của bạn và của mẫu + mốc từ mẫu — chỉ mô tả (S-5b, D-34) |

`build_result_view(res, lesson)` (hàm thuần, D-31) biến `res` thành **view** mà giao diện
chỉ việc vẽ: `state` (`result` | `unsure` theo `evidence_gate`, D-29) + `gate`, `words`/`chips`
(`target`, `heard`, `kind` ∈ ok/warn/tone/rhyme/bad/missing/extra, `code` nl/th/sh/final/tone/
rhyme), `extras`, `notes`, `cards` (≤ 4: `title`, `level`, `kind`, `tip`, `word`, `sample`,
`heard`, `detail`), `perfect`, `ring`, `headline`, `summary`, `score_line`, `status_line`,
`heard_text`/`heard_note`/`tips` (cho `unsure`), `sounds` (đếm âm theo ngôn ngữ bài).

### 3.4. Cài đặt & lịch sử

- `config.json` — `DEFAULT_CFG` trong `app.py`: `model`, `lang`, `out_dir`, `theme`,
  `yt_kind`, `yt_quality`, `subs`, `embed`, `sub_lang`, `mic`, `geometry`.
- `practice_history.json` — map `set_id → {n, best, last, ts, ph:{mã: count},
  tries:[{ts, c, t, ph}] (30 lần gần nhất, D-30)}`. `ph` của bài Anh là mã ARPAbet, của bài
  Việt là `nl`/`tone`. Ghi nguyên tử qua file `.tmp` + `os.replace`; hàm thuần
  `hist_add_try`/`hist_weakest`.

## 4. Luồng 1 — File / bản ghi → văn bản

```
File chọn/temp WAV
  → App._run() (validate, _set_stt_state("processing"), thread)
  → App._w_file(fp, model_size, lang, delete_after, base)
      load_model(model_size)                 # WhisperModel CPU int8, cache theo cỡ
      model.transcribe(fp, language, beam_size=5)
      mỗi segment → ("progress", end/duration)
      _fix_cues(split_long_cues(cues))
      queue.put(("result", {cues, media, base, note}))
  → App._poll() → App._on_result()  (_set_stt_state("result"))
      render tab Văn bản + tab SRT + bật nút xuất
```

- Ghi âm dùng cùng worker với `delete_after=True`: `save_frames_wav` tạo WAV tạm,
  `_w_file` xóa trong `finally` (xong/hủy/lỗi); bản thu < 0,4 s bị xóa ngay.
- Hủy: `_cancel()` đặt `cancel_flag`; `_w_file` kiểm tra trong vòng lặp segment
  và ném `_YtCancelled`; `_on_error("__cancelled__")` không hiện messagebox.
  Đang thu thì `_cancel()` gọi `_stop_recorder()` — dừng bản thu của tab sở hữu
  (`rec_owner`, D-26) và bỏ frames.

## 5. Luồng 2 — YouTube

```
App._run()
  → App._w_yt(url, kind, quality, out_dir, subs, sub_pref, embed, model, lang)
     (bọc App._w_yt_body; luôn gửi result/error — D-24)
      1. extract_info(download=False) → title/id/subtitles
      2. pick_subtitle_source(info, pref)  # manual ưu tiên, rồi auto; auto: gốc→vi→en
      3a. kind == "subs": skip_download, tải .srt/.vtt; nếu không có → tải audio tạm
          → _w_whisper_cues → xóa temp trong finally
      3b. kind == "video"/"audio": yt_build_opts(...) → tải + merge (mp4/mp3)
          → tìm phụ đề đã tải; nếu không có → Whisper
      4. ghi <base>.srt + <base>.txt
      5. nếu video + embed: mux_subtitles_into_video (ffmpeg -c copy)
      6. queue result
```

- `outtmpl = "%(title).80s [%(id)s].%(ext)s"`, `windowsfilenames=True`.
- `find_subtitle_file(..., since=t0)` chỉ nhận file mới, tránh nhặt file cũ.
- `pick_downloaded_file` lọc theo `vid`, thời gian, đuôi media.
- `_YtCancelled` được kiểm tra trong `progress_hooks`.
- Phụ đề "auto" có thể là **bản dịch** của YouTube; app log cảnh báo khi ngôn ngữ
  không phải bản gốc.

## 6. Luồng 3 — Luyện phát âm

```
Chọn bài (PRACTICE_SETS / GUIDES / custom)
  → App._prac_start()  (mic resolve, Recorder.start auto_stop)
  → Recorder (thread): 100 ms/block, 0,5 s calib, hysteresis, speech_seen
      auto stop: "silence" (1,8 s) | "nospeech" (7 s) | "max"; nền = phân vị 20
  → _prac_stop_and_score(reason)
      reason nospeech → báo, dò mic, KHÔNG chấm
      save_frames_wav → enhance_audio → WAV 16k
      peak0 < MIC_MIN_PEAK (0,8%) → KHÔNG chấm, dò mic
      < 0,5 s → KHÔNG chấm
  → App._w_prac(wav, model, lang, target, ref_wav)
      wav_peak gate
      transcribe_practice (PRAC_ASR_OPTS: word_timestamps, temperature 0,
              condition_on_previous_text=False, VAD chỉ khi file > 30 s;
              câu tự gõ: ngôn ngữ = guess_lang(target);
              bài Việt: practice_model → small nếu có trên máy)
      score_pronunciation(target, hyp, lang)          # L1
      prosody.compare(ref_wav, wav) nếu có mẫu (chưa bài nào có)
  → App._prac_done(res)
      v = build_result_view(res, lesson)      # hàm thuần, có test
      _set_prac_state(v["state"])
      _render_result(v)                       # chỉ vẽ (vòng điểm, chip, thẻ)
      vẽ ngữ điệu (Canvas), _record_hist(sid, res, v) → hist_add_try
```

**Trạng thái màn hình (D-31).** Tab Chuyển văn bản: `idle → recording → processing →
result | error`; tab Luyện: `idle → recording → scoring → result | unsure | error`.
Chỉ `App._set_stt_state` / `App._set_prac_state` bật-tắt nút, đổi nhãn, hiện thanh tiến
trình; bảng điều khiển theo trạng thái là hàm thuần `stt_controls` / `prac_controls`.
`busy`, `p_working`, `recording`, `rec_owner` được **suy ra** trong hai hàm này.

## 7. Luồng 4 — Mic

- `list_input_mics()` → `[(index, name, hostapi, samplerate)]`.
- `pick_default_mic()` ưu tiên micro thật; DirectSound > WASAPI > MME (D-20); tránh loopback.
- `probe_input_levels()` thu thử 0,5 s từng mic, bỏ WDM-KS và loopback, xếp theo đỉnh.
- `query_mic_rate()` lấy sample rate gốc; thu ở rate gốc rồi `resample_to_16k`
  (tốt hơn ép PortAudio resample).
- WDM-KS không dùng được vì `InputStream.read()` blocking không được hỗ trợ.

## 8. Xử lý âm thanh

`enhance_audio(samples_i16, rate)` — hàm thuần:
1. int16 → float [-1,1], đo `peak0`, phát hiện clip.
2. Trừ DC.
3. High-pass 1 cực ~75 Hz (không ringing), tính bằng FFT với đáp ứng xung của bộ lọc.
4. Chuẩn hóa về -3 dB (`REC_TARGET_PEAK=0.70`) theo `speech_peak` (bỏ click), tối đa +24 dB.
5. `tanh` + clip.
6. Cắt im lặng đầu/cuối (ngưỡng `max(0.015, 0.04*peak)`), giữ 80 ms đệm.
7. Fade 8 ms hai đầu.
8. Trả `(int16, info)` với `peak0, peak1, quiet, clipped, trimmed`.

`save_frames_wav` ghép frame → resample 16k (lọc chống gập FIR Kaiser 7,9/8,6 kHz) → enhance
→ ghi WAV mono 16-bit. `load_model` giữ một `WhisperModel` trong `_MODEL_CACHE` (D-36).
Đo cả chuỗi bằng `tools/asr_bench.py`.

## 9. Điểm mở rộng

| Muốn thêm | Sửa ở đâu | Bắt buộc kèm |
|---|---|---|
| Nguồn đầu vào mới (vd. URL khác) | `_run` + một `_w_*` mới | validate, cancel, queue contract |
| Định dạng phụ đề mới | `_parse_*` + `read_subtitle_file` | fixture test |
| Bài học mới | `PRACTICE_SETS` / `GUIDES` + audio `mau/vi_*.wav` | `app-lessons` skill |
| Phép chấm mới | `_w_prac` sau `score_pronunciation` | khóa kết quả mới + UI + tài liệu |
| Theme mới | `THEMES` | kiểm tra tương phản cả 2 theme |
| Model ASR khác | `load_model` | cùng interface `transcribe` |

## 10. Những chỗ dễ sai

1. Gọi widget từ worker → crash ngẫu nhiên (I1).
2. Quên `cancel_flag` trong vòng lặp dài → nút Hủy vô dụng.
3. Quên xóa file temp khi lỗi → rác trong `%TEMP%`.
4. Đổi khóa dict kết quả mà không sửa `_prac_done`/`_on_result` → KeyError.
5. Dùng `open(...)` không `encoding="utf-8"` → hỏng tiếng Việt trên Windows.
6. Thêm bài mà quên id trong `_VI_IDS` / `GUIDE_IDS` → bài không hiện.
7. Chấm điểm khi `peak0 < MIC_MIN_PEAK` (0,008) → Whisper bịa.
