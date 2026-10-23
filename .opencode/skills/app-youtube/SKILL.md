---
name: App YouTube Download & Subtitles
description: Sửa luồng tải YouTube trong Oriole, gồm yt-dlp, chọn phụ đề có sẵn hay Whisper, tải MP4/MP3, đặt tên file, nhúng phụ đề mềm, hủy tác vụ và dọn file tạm. Dùng khi người dùng nhắc tới YouTube, yt-dlp, phụ đề tải về, SRT/VTT, hoặc nhúng subtitle.
---

# YouTube Download & Subtitles

Phạm vi: nút **Bắt đầu** khi nguồn là link YouTube; 3 chế độ trong ô `Lấy`.

## Đọc trước

- `docs/ARCHITECTURE.md` §5.
- Bất biến I9, I10, I11, I16.

## Symbol (app.py)

| Nhóm | Symbol |
|---|---|
| Worker | `App._w_yt` (điểm vào thread, bọc lỗi — D-24), `App._w_yt_body`, `App._yt_fetch_sub_cues` (D-25), `App._w_whisper_cues` |
| Tùy chọn tải | `yt_build_opts`, `yt_ffmpeg_location`, `yt_progress_fraction` (hook → 0..1) |
| Chọn phụ đề | `pick_subtitle_source`, `_yt_first_info` |
| Tìm file | `pick_downloaded_file`, `find_subtitle_file`, `safe_stem` |
| Đọc phụ đề | `read_subtitle_file`, `_parse_sub_text`, `_parse_json3`, `_parse_ts` |
| Làm sạch cue | `_dedupe_cues`, `_fix_cues`, `split_long_cues` |
| Nhúng | `mux_subtitles_into_video`, `_SUB_CODEC`, `_LANG3` |
| Hằng số | `YT_KINDS`, `YT_KIND_NAMES`, `YT_QUALITIES`, `YT_SUB_LANGS` |

## Ba chế độ

| `kind` | Tải gì | Phụ đề | Nhúng |
|---|---|---|---|
| `subs` | **không tải video**; chỉ tải phụ đề (`skip_download`) | có sẵn; nếu không → tải audio tạm → Whisper | không |
| `video` | video + audio, merge `mp4` | có sẵn hoặc Whisper | có, nếu checkbox |
| `audio` | chỉ audio, postprocess `mp3` 192 kbps | có sẵn hoặc Whisper | không |

Chất lượng: `best`/`1080`/`720`/`480`/`360`. Với `audio` và `subs`, app ép `best`
(format audio) để tránh tải video không cần thiết.

## Chọn phụ đề — `pick_subtitle_source(info, pref)`

Thứ tự:
1. Nếu `pref != "auto"` (người dùng chọn `vi`/`en`): tìm đúng mã đó.
2. Nếu `auto`: thử **ngôn ngữ gốc của video → `vi` → `en`**.
3. Trong mỗi ngôn ngữ: **phụ đề thủ công trước**, rồi tự động.
4. Nếu không khớp: lấy thủ công đầu tiên, rồi tự động đầu tiên.
5. Không có gì → `(None, None)` → fallback Whisper.

`find()` khớp chính xác trước, rồi `vi-*`/`vi_*` (biến thể vùng).

**Cảnh báo dịch (D-25):** log nói rõ "đây là bản dịch máy của YouTube" khi
(a) phụ đề **tự động** có mã khác ngôn ngữ gốc (kể cả `en`), hoặc (b) mã không phải
`en` và khác ngôn ngữ gốc. Đừng bỏ cảnh báo này: người dùng rất dễ tưởng là bản gốc.

## Quy trình `_w_yt`

```
1. extract_info(download=False, noplaylist=True)
2. _yt_first_info → title, id, language, subtitles, automatic_captions
3. base = safe_stem(title, id)
4. chọn phụ đề (nếu subs)
5. nhánh:
   a. kind == "subs":
      - _yt_fetch_sub_cues (skip_download, thử lại 1 lần khi 429)
        → find_subtitle_file → read_subtitle_file → xóa file thô
      - nếu rỗng: tải audio tạm vào tempfile.mkdtemp("stt_yt_")
        → _w_whisper_cues → xóa file + thư mục trong finally
   b. kind == "video"/"audio":
      - yt_build_opts(...) → download
      - pick_downloaded_file(info, out_dir, vid, t0)
      - nếu subs: _yt_fetch_sub_cues (lệnh riêng, D-25); rỗng → Whisper
6. ghi <base>.srt + <base>.txt (UTF-8)
7. nếu video + embed + có srt: mux_subtitles_into_video
8. queue result {cues, media, srt, txt, base, note}
```

- Logic nằm trong `_w_yt_body`; `_w_yt` chỉ bọc và **luôn** gửi `result`/`error`
  (kể cả `__cancelled__`). Không thêm lối thoát bỏ qua lớp bọc (D-24).
- Mọi bước dài phải kiểm tra `self.cancel_flag`; hook tải ném `_YtCancelled`
  (kể cả lần tải audio tạm cho Whisper).
- `find_subtitle_file` nhận cả file cũ **cùng tên video + đúng lang** (vì yt-dlp
  có thể bỏ qua tải lại). Đừng thay bằng "chỉ file mới" — sẽ mất phụ đề có sẵn.
- `pick_downloaded_file` ưu tiên đường dẫn yt-dlp báo; fallback quét thư mục theo
  `[video_id]` rồi theo mtime.

## Tùy chọn yt-dlp — không phá các khóa sau

```python
format: "ba/b"                                      # audio
        "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b"         # best video
        "bv*[ext=mp4][height<=H]+ba[ext=m4a]/..."    # giới hạn height
outtmpl: "<out>/%(title).80s [%(id)s].%(ext)s"
noplaylist: True
windowsfilenames: True
continuedl: True
ffmpeg_location: imageio_ffmpeg.get_ffmpeg_exe()
merge_output_format: "mp4" (video) | None (audio)
postprocessors: FFmpegExtractAudio mp3 192 (audio)
```

**Video/audio tải KHÔNG kèm phụ đề** (`yt_build_opts(..., None)`); phụ đề tải riêng
bằng `App._yt_fetch_sub_cues` (D-25) — yt-dlp coi lỗi phụ đề là lỗi chết, HTTP 429 sẽ
làm mất cả video. Helper thử lại 1 lần khi 429, lỗi thì trả `[]` → Whisper.

Phụ đề (trong helper): `writesubtitles`, `writeautomaticsub`, `subtitleslangs=[lang]`,
`subtitlesformat="srt/vtt/best"`.

## Nhúng phụ đề mềm

`mux_subtitles_into_video(video, srt, ffmpeg, lang)`:
- Codec theo đuôi: `mp4/m4v/mov → mov_text`, `mkv → srt`, `webm → webvtt`.
- Map `0:v?`, `0:a?`, `1:0` → **không nhân đôi phụ đề** khi chạy lại.
- `-c copy` + `-c:s <codec>` → nhanh, không re-encode hình.
- Ghi ra `.subtmp.<ext>` rồi `os.replace`; lỗi thì xóa temp.
- Gắn metadata `language=vie/eng/...`.
- Trả `(path, None)` hoặc `(None, lỗi)`; lỗi chỉ log, **không** làm hỏng cả tác vụ.

## Đọc phụ đề

`read_subtitle_file(path)`:
- `.json3` → `_parse_json3` (YouTube timedtext).
- còn lại → `_parse_sub_text` cho SRT và VTT (bỏ header `WEBVTT`, số thứ tự,
  tag HTML đơn giản).
- `_dedupe_cues` gộp cue trùng/lặp của phụ đề tự động.
- `_fix_cues` + `split_long_cues` trước khi xuất.

Nếu thêm định dạng mới: viết parser trả **cùng kiểu cue**, thêm fixture, và cập
nhật `read_subtitle_file`.

## Kiểm chứng

```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\smoke_test.py
```

Thủ công (cần mạng):
1. Video **có** phụ đề tiếng Anh, chế độ "Chỉ transcript" → chỉ thấy `.srt/.txt`,
   **không** có `.mp4` mới.
2. Video **không** phụ đề, chế độ "Chỉ transcript" → log "dùng Whisper", có `.srt`,
   không còn thư mục `stt_yt_*` trong `%TEMP%`.
3. Chế độ Video MP4 + nhúng → mở bằng VLC, bật/tắt phụ đề được.
4. Bấm Hủy khi đang tải → không có file dở dang mới (file `.part` có thể còn, ghi nhận).
5. Link sai → cảnh báo, không bắt đầu worker.

## Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| Tải cả video khi chỉ cần transcript | quên `skip_download` hoặc format |
| Không tìm thấy file vừa tải | bỏ qua `filepath` của yt-dlp, chỉ quét mtime |
| Nhặt nhầm phụ đề video khác | dùng `lang` mà bỏ điều kiện tên gốc |
| Nhân đôi phụ đề sau khi nhúng lại | map cả `0:s?` thay vì chỉ `1:0` |
| Rác `stt_yt_*` | thiếu `finally` dọn temp |
| "Tải video lỗi: Unable to download video subtitles … HTTP 429" | tải phụ đề chung lệnh với video; phải tách (D-25) |
| Bấm Hủy/ lỗi giữa chừng → UI kẹt bận mãi | ngoại lệ thoát khỏi thread không qua lớp bọc `_w_yt` (D-24) |
| Log yt-dlp: "No supported JavaScript runtime" | chưa cài `deno`; hiện vẫn tải được nhưng có thể thiếu format/403 về sau |
| Lỗi ffmpeg im lặng | không đọc `stderr`/`returncode` |
| Thanh tiến trình đầy ngay khi bắt đầu tải | gửi `progress` theo thang 0..100; phải dùng `yt_progress_fraction(d)` (0..1, `_pbar` tự nhân 100) |
| Phụ đề là bản dịch | không log cảnh báo theo `info["language"]` |

## Rủi ro bên ngoài

- YouTube đổi API/format liên tục → `yt-dlp` phải cập nhật.
- Chỉ tải nội dung người dùng có quyền; app không lưu cookie/tài khoản (I16).
- `ffmpeg` lấy từ `imageio-ffmpeg`; máy thiếu gói này phải báo lỗi rõ, không crash.
