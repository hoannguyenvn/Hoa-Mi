# NHẬT KÝ QUYẾT ĐỊNH (ADR)

Quy tắc:
- Quyết định đã ghi **không bị xóa**; nếu đổi, thêm quyết định mới ghi
  "thay thế D-xx".
- Mỗi quyết định phải nói **vì sao**, để model sau không "tối ưu" ngược lại.
- Khi code mâu thuẫn với file này: code là hiện trạng, nhưng phải hoặc sửa code,
  hoặc sửa quyết định — không để lệch.

## A. Quyết định đang có hiệu lực

### D-01 — Desktop Tkinter, một file `app.py`
**Quyết định:** giữ app desktop offline, UI `tkinter`, pipeline chung trong `app.py`.
**Vì sao:** người dùng cần app cài sẵn trên Windows, không cần server; chuyển sang
Streamlit/web là viết lại UI và mất offline. Tách file dần theo tính năng, không
tái cấu trúc big-bang.
**Hệ quả:** file lớn; phải kỷ luật symbol + skill để tránh đọc cả file.

### D-02 — `faster-whisper`, CPU, int8
**Quyết định:** `WhisperModel(model_size, device="cpu", compute_type="int8")`,
`beam_size=5`.
**Vì sao:** nhẹ hơn `openai-whisper`, chạy tốt trên CPU, không cần CUDA.
**Hệ quả:** `medium` chậm; cần cache model (chưa làm); lần đầu tải model cần mạng.

### D-03 — Một kiểu cue dùng chung cho mọi nguồn
**Quyết định:** `(start, end, text)` cho file, YouTube, bản ghi; mọi xuất file đi qua
`cues_to_srt` / `cues_to_txt`.
**Vì sao:** tránh 3 pipeline xuất khác nhau; dễ test hàm thuần.
**Hệ quả:** mọi nguồn mới phải trả cue, không trả text thô.

### D-04 — Worker thread + `queue` + `_poll` 80 ms
**Quyết định:** worker chỉ đẩy message; UI cập nhật ở main thread.
**Vì sao:** Tk không thread-safe.
**Hệ quả:** thêm loại message mới phải xử lý trong `_poll`; không gọi widget trong worker.

### D-05 — Điểm chính = tỉ lệ từ đúng
**Quyết định:** `score = 100 * correct / total`; `warns`/`tones` chỉ là cảnh báo.
**Vì sao:** con số phải giải thích được ("bạn đọc think thành tink"); tránh thang điểm
tùy ý kiểu 0,25·pitch + 0,35·timbre.
**Hệ quả:** điểm có thể 100% dù còn cảnh báo nhẹ; UI phải hiển thị cả hai.

### D-06 — Cổng tin cậy trước khi chấm
**Quyết định:** không chấm khi `peak0 < 2%`, bản ghi `< 0,5 s`, `nospeech`, hoặc
`garbage` (câu nghe dài bất thường + điểm < 35). `low_conf < 0,35` thì ghi chú.
**Vì sao:** Whisper bịa trên im lặng/nhiễu; thà nói "chưa đủ rõ" hơn bịa điểm.
**Hệ quả:** thêm gate mới phải có test và thông điệp tiếng Việt rõ ràng.

### D-07 — Thanh điệu tiếng Việt: so chữ, chưa phân tích F0
**Quyết định:** hiện chỉ phát hiện khi bỏ dấu thì hai từ giống nhau
(`strip_tone_vi(t) == strip_tone_vi(h)`), trạng thái `tone`.
**Vì sao:** làm đúng, giải thích được, không cần model; dữ liệu F0 chưa đủ tin cậy.
**Hệ quả:** **giới hạn đã biết** — phải ghi rõ trong UI/README; đây là việc của P3
trong roadmap, không được giả vờ đã chấm thanh điệu.

### D-08 — Âm vị tiếng Anh bằng CMUdict + căn chuỗi
**Quyết định:** chuỗi ARPAbet mục tiêu vs chuỗi của từ ASR nghe được, căn
Needleman–Wunsch; chỉ báo thay/thêm/bớt âm.
**Vì sao:** không so phổ hai người; lỗi phụ âm rất đáng tin.
**Hệ quả:** nguyên âm có thể bỏ sót/báo nhầm với model `base`; từ ngoài từ điển
được suy theo chữ và đánh dấu `approx`.

### D-09 — GOP tùy chọn, so với bản mẫu cùng câu
**Quyết định:** nếu có `torch` + model, chấm CTC Viterbi; chỉ báo "yếu" khi
`score < 55` **và** `gop < ref_gop - 1.5` (hoặc nhánh tuyệt đối khi không có mẫu).
**Vì sao:** model yếu ở một số âm/giọng; so bản mẫu cùng câu loại bỏ thiên lệch.
**Hệ quả:** GOP không phải % đúng; phải ghi chú; lần đầu chậm; thiếu model thì
im lặng quay về D-08 (không lỗi).

### D-10 — Ngữ điệu chỉ để nhìn, không chấm điểm
**Quyết định:** F0 → bán cung so với trung vị người nói; hiển thị contour mẫu vs bạn,
nhận xét cuối câu/khoảng cao độ/độ lệch DTW.
**Vì sao:** chấm ngữ điệu cần hiệu chuẩn; hiển thị trung thực vẫn hữu ích.
**Hệ quả:** không thêm điểm "ngữ điệu" vào `score`.

### D-11 — DSP bằng numpy, không librosa/Praat
**Quyết định:** F0 autocorrelation, high-pass 1 cực, resample nội suy tuyến tính.
**Vì sao:** giữ app nhẹ, không kéo numba/llvmlite; đủ tốt cho giọng nói.
**Hệ quả:** formant/spectrogram chất lượng cao (nếu làm) cần bàn riêng.

### D-12 — Offline khi chạy
**Quyết định:** chỉ YouTube và tải model lần đầu cần mạng.
**Vì sao:** sản phẩm quảng cáo là app offline; tránh phụ thuộc dịch vụ.
**Hệ quả:** không gọi API đám mây trong luồng chấm; không lưu cookie.

### D-13 — TTS chỉ để nghe mẫu
**Quyết định:** `edge-tts` sinh audio mẫu; không dùng TTS làm chuẩn để chấm.
**Vì sao:** TTS không đại diện formant/ngữ điệu người thật.
**Hệ quả:** cần bản ghi người thật cho hiệu chuẩn sau này.

### D-14 — Nội dung/trạng thái bằng JSON, không DB
**Quyết định:** `lessons_en.json`, `config.json`, `practice_history.json`.
**Vì sao:** dễ sửa tay, không cần migration, phù hợp app nhỏ.
**Hệ quả:** ghi lịch sử phải nguyên tử (`.tmp` + `os.replace`); dữ liệu lớn sẽ cần
định dạng khác.

### D-15 — `config.json` whitelist
**Quyết định:** chỉ đọc khóa có trong `DEFAULT_CFG`; khóa lạ bỏ qua.
**Vì sao:** bền vững khi đổi phiên bản, tránh rác.
**Hệ quả:** thêm cài đặt mới phải thêm vào `DEFAULT_CFG` + UI + README.

### D-16 — Test bằng script stdlib
**Quyết định:** `tools/smoke_test.py` + `tools/context_check.py`, không pytest.
**Vì sao:** môi trường hiện tại không có pytest; giảm dependency.
**Hệ quả:** nếu thêm pytest phải ghi quyết định mới; test hiện chỉ phủ hàm thuần.

### D-17 — Skills + tài liệu context là "hệ điều hành" cho AI
**Quyết định:** mọi tính năng có skill; mọi phiên cập nhật `PROJECT-STATE` +
`HANDOFF`; `context-map.json` là nguồn kiểm tra drift.
**Vì sao:** người dùng chuyển giữa nhiều AI model; context phải nằm trong repo,
không nằm trong trí nhớ của một model.
**Hệ quả:** thêm tính năng phải thêm/cập nhật skill + map; `context_check` là cổng.

### D-18 — Giao diện tiếng Việt, code tiếng Anh
**Quyết định:** chuỗi UI, thông báo, README bằng tiếng Việt; identifier/API tiếng Anh.
**Vì sao:** người dùng cuối là người Việt; code dễ bảo trì.
**Hệ quả:** dịch chuỗi mới, giữ thuật ngữ IPA/GOP nhất quán.

### D-19 — Không credential trong repo
**Quyết định:** không cookie/token/API key; không tải nội dung không có quyền.
**Vì sao:** bảo mật + điều khoản dịch vụ.
**Hệ quả:** mọi tích hợp cần đăng nhập phải hỏi người dùng và lưu ngoài repo.

### D-20 — Lọc WDM-KS khỏi ô chọn micro
**Quyết định:** UI chỉ liệt kê micro qua `list_usable_mics()` (bỏ host API WDM-KS).
Nếu `config.json` lưu micro WDM-KS thì không khớp danh sách nữa → app tự chọn mặc định.
Máy chỉ có WDM-KS: vẫn hiện để không bỏ trắng ô chọn (kèm hướng dẫn).
**Vì sao:** `Recorder` dùng `InputStream` + `stream.read()` (blocking); PortAudio báo
`Blocking API not supported` trên WDM-KS → thu được 0 khung → app báo "mic im lặng"
dù người dùng chọn đúng thiết bị. Máy hiện tại có 9 thiết bị WDM-KS, rất dễ chọn nhầm.
**Hệ quả:** giảm lựa chọn trong ô Micro; `list_input_mics()` vẫn dùng cho chẩn đoán.
Đổi lại phải cập nhật `tools/smoke_test.py` (`usable_mics_drops_wdmks`) + skill `app-recording`.

Kèm theo: `pick_default_mic` đổi thứ tự ưu tiên host API thành
DirectSound (+2) > WASAPI (+1) > MME (0), và trừ 3 điểm cho thiết bị alias
("Sound Mapper", "Primary Sound Capture"). **Lý do:** đo trên máy hiện tại với cùng
một mic vật lý (Microphone Array Intel SST) và cùng câu đọc: DirectSound ~2,0%,
MME ~0,4%, WASAPI ~0,3% đỉnh tín hiệu. WASAPI rơi vào nhánh xử lý của driver làm
tín hiệu nhỏ đi ~6 lần → dễ bị cổng "đỉnh < 2%" chặn oan.
Test khoá hành vi: `smoke_test.pick_default_prefers_real_mic`.

### D-21 — Hỗ trợ micro yếu (sàn tín hiệu 0,8%, gain +24 dB)
**Quyết định:** hạ sàn "có tín hiệu" và ngưỡng bắt giọng, nới gain chuẩn hóa:
- `MIC_MIN_PEAK = 0.008` (-42 dB) thay cho 0,02 ở cổng chấm điểm và dò micro.
- `MIC_GOOD_PEAK = 0.03`: dưới mức này chỉ **cảnh báo**, vẫn chấm.
- `Recorder`: ngưỡng bật giọng `max(0,004; noise*2,2)`, ngưỡng giữ giọng
  `max(0,0025; noise*1,2)` (trước là 0,012/0,008) — vẫn cao hơn nền nhiễu đo được
  (0,01–0,05% đỉnh) hàng chục lần.
- `REC_GAIN_MAX = 16.0` (+24 dB) thay cho 4.0 (+12 dB).
**Vì sao:** Microphone Array Intel SST trên máy hiện tại chỉ cho đỉnh ~2% khi nói
bình thường (RMS ~0,5%), dưới ngưỡng RMS 1,2% cũ → app báo "không nghe thấy giọng"
và "bản thu gần như im lặng" dù micro hoàn toàn bình thường. Đo cùng câu: DirectSound
2,01%, MME 0,42%, WASAPI 0,31%.
**Hệ quả:** I3 đổi từ "đỉnh < 2%" thành "đỉnh < 0,8%". Vẫn không chấm khi im lặng
thật, quá ngắn, hoặc không thấy giọng; nền nhiễu mic thường thấp hơn sàn này rất xa.
Test: `smoke_test.enhance_lifts_weak_mic`. Nếu gặp máy có nền nhiễu cao, tăng
`MIC_MIN_PEAK` chứ đừng bỏ hẳn cổng.

### D-22 — Mic ngoài: quét lại thiết bị + cảnh báo tai nghe bluetooth thiếu micro
**Quyết định:**
- Thêm `rescan_audio_devices()` gọi `sd._terminate()` + `sd._initialize()` để PortAudio
  đọc lại danh sách thiết bị. Ô Micro gọi nó khi bấm **Quét lại** và mỗi lần mở tab
  **Cài đặt**, nhưng **chỉ khi** không có stream nào đang chạy (thu âm/phát mẫu/dò mic).
- Thêm `headset_mic_missing()`: nhận ra thiết bị **nghe** là tai nghe bluetooth nhưng
  không có thiết bị **thu** cùng hãng → hiện gợi ý bật profile Hands-Free/Telephony.
- Ô Micro có thêm nút **Âm thanh Windows** (`os.startfile("ms-settings:sound")`).
**Vì sao:** PortAudio liệt kê thiết bị **một lần** khi khởi tạo; nút "Làm mới" chỉ đọc
lại bộ nhớ đệm nên mic cắm/kết nối sau khi mở app không bao giờ hiện. Đo trên máy hiện
tại: AirPods Pro chỉ xuất hiện ở danh sách **output** (`Headphones (AirPods Pro - Find My)`),
không có thiết bị input nào → Windows chưa mở chế độ Hands-Free, app không thể tự bật.
**Hệ quả:** app **không** tự tạo được micro vốn không có trong Windows; chỉ phát hiện và
hướng dẫn. Test: `smoke_test.headset_without_mic_is_detected`.

### D-23 — Thu âm bằng callback + queue, không dùng `stream.read`
**Quyết định:** `Recorder.start` mở `sd.InputStream(callback=...)`; callback đẩy từng
block 100 ms vào `queue.Queue`, luồng xử lý lấy block từ queue để tính RMS, phát hiện
giọng và auto-stop. `stop()` vớt nốt block còn trong queue trước khi trả frames.
**Vì sao:** đo trên máy hiện tại, `InputStream.read()` (blocking) trên **DirectSound**
trả **100 % số 0** ở cả `blocksize=0` và `blocksize=4410`, trong khi `sd.rec` và
callback trên **cùng thiết bị** thu bình thường (nền 0,006–0,09 %). Đây là nguyên nhân
thật của "mic im lặng" và các file `luyen_*.wav` dài 180 s toàn im lặng — không phải
do micro bị mute. MME và WASAPI thì blocking read vẫn chạy, nhưng callback chạy cho cả ba.
**Hệ quả:** bỏ hẳn `stream.read`; callback **không** chạm widget (chỉ đẩy queue — vẫn
đúng I1). `stop()` phải drain queue, nếu không mất ~100 ms đuôi. WDM-KS vẫn lỗi
`Blocking API not supported` khi mở stream (không liên quan).

### D-24 — Worker YouTube luôn báo về UI (`_w_yt` bọc `_w_yt_body`)
**Quyết định:** `App._w_yt` chỉ là điểm vào thread, bọc `App._w_yt_body` bằng
`try/except`: `_YtCancelled` → `("error", "__cancelled__")`; lỗi khác → nếu
`cancel_flag` đã bật thì coi là hủy, ngược lại `("error", "Lỗi YouTube: …")`.
Nhánh Whisper của chế độ "Chỉ transcript" tải audio tạm **trong** `try/finally`
(`shutil.rmtree`) và có `progress_hooks` để Hủy có tác dụng.
**Vì sao:** trước đây `_w_yt` không có lớp bọc nào; Hủy khi đang tải (hook ném
`_YtCancelled`) hoặc bất kỳ lỗi ngoài các `try` nhỏ (tải audio tạm, Whisper, ghi file)
làm thread chết im lặng → không có `result`/`error` → `_set_busy(False)` không bao giờ
chạy, UI kẹt "Đang hủy…"/"Đang tải…", phải tắt app. Đã tái hiện bằng worker thật.
**Hệ quả:** mọi thay đổi trong luồng YouTube viết vào `_w_yt_body`; không gọi
`_w_yt_body` trực tiếp từ `Thread`. Test khói `yt_worker_always_reports_back` giữ bất biến.

### D-25 — Tải video/audio và phụ đề bằng hai lệnh yt-dlp riêng
**Quyết định:** chế độ Video/Audio gọi `yt_build_opts(..., sub_lang=None)`; phụ đề tải sau
bằng `App._yt_fetch_sub_cues` (`skip_download`, outtmpl = tên file media). Helper thử lại
1 lần khi HTTP 429 (chờ ~4 s, vẫn nghe nút Hủy), lỗi khác/lần 2 → log + trả `[]` → Whisper.
Nút chính đổi tên theo chế độ: `⬇ Tải video` / `⬇ Tải audio` / `▶ Lấy transcript`.
Cảnh báo "bản dịch máy" cũng bật khi phụ đề **tự động** khác ngôn ngữ gốc (kể cả `en`).
**Vì sao:** `YoutubeDL._write_subtitles` ném `DownloadError` khi tải phụ đề lỗi (trừ khi
`ignoreerrors=True`), nên một lỗi 429 ở phụ đề `en` dịch máy của video tiếng Việt
(2UIqadUjQf8) làm hỏng **cả** tác vụ tải MP4. Đã tái hiện 429 thật trên máy người dùng.
Không dùng `ignoreerrors=True` vì nó nuốt cả lỗi tải video thật.
**Hệ quả:** không gộp lại `writesubtitles` vào lệnh tải media. Test khói
`yt_subtitle_429_falls_back_not_fatal`.

### D-26 — Recorder dùng chung có chủ (`rec_owner`); file tạm có một chỗ xóa
**Quyết định:**
- Giữ **một** `Recorder` cho cả hai tab, nhưng mỗi lần thu đặt `App.rec_owner`
  (`"stt"` | `"prac"`). Nút/autostop/lỗi của tab này không dừng bản thu của tab kia.
  Mọi chỗ dừng đi qua `App._stop_recorder()` (dừng + xóa owner + reset UI đúng tab).
- Bản Nghe lại của tab Luyện (`luyen_*.wav`) chỉ gán qua `App._set_last_wav()`, hàm này
  xóa bản cũ; `_on_close` gọi `_set_last_wav(None)`. Bản thu tab 1 (`stt_*.wav`) thuộc
  về `_w_file(delete_after=True)` và bị xóa trong `finally`.
**Vì sao:** rà soát 2026-10-22 thấy (1) 15 file `luyen_*.wav` / 45 MB rò rỉ trong `%TEMP%`
vì `last_wav` bị ghi đè không xóa (phá I10); (2) đang ghi âm ở tab 1 mà bấm "Thu âm &
chấm" ở tab 2 thì app chấm nhầm bản thu tab 1; Esc khi luyện để nút tab 2 kẹt
"■ Dừng & chấm". Tách hai `Recorder` không cần: hai stream cùng micro dễ lỗi thiết bị bận.
**Hệ quả:** bắt đầu thu phải đặt cả `recording=True` và `rec_owner`; dừng thu không đặt
`recording=False` trực tiếp mà gọi `_stop_recorder()`; không gán `last_wav` trực tiếp. Test khói
`recording_belongs_to_one_tab`, `practice_replay_wav_is_replaced_not_leaked`,
`w_file_removes_temp_recording_on_error`.

### D-27 — Duyệt spec giao diện (GATE A của `docs/UI-PLAN.md`)
**Quyết định:** người dùng duyệt spec S-1…S-10 và chọn mặc định cho Q-01…Q-07:
- Q-01: khi máy không chắc (S-3) **ẩn hẳn điểm**, chỉ hiện "Máy chưa nghe rõ bài đọc" + Thử lại.
- Q-02: tiêu đề kết quả là **phân số từ** ("Đúng 2/4 từ"), không hiện "50.0%".
- Q-03: số GOP chi tiết chỉ nằm trong nút "Chi tiết"; mặt chính hiện mức chữ.
- Q-04: Model + Ngôn ngữ **chỉ ở thanh trên**; tab Cài đặt không lặp lại.
- Q-05: **không** kéo-thả file (tránh thêm `tkinterdnd2`, I8).
- Q-06: Tab 2 dùng **3 cột** `Bài học | Thu âm | Kết quả` (= Phase 2A).
- Q-07: thu âm mẫu tiếng Việt người thật **để sau** (C-05 ngoài phạm vi).
**Vì sao:** đợt rà soát 2026-10-22 thấy app hiện điểm khi thiếu bằng chứng, nhiều loại %
cùng màn hình, và bố cục Tab 2 chật/thừa. Các mặc định trên là phương án đề xuất trong plan.
**Hệ quả:** thiết kế (GATE B) và code phải theo các lựa chọn này; đổi lại phải thêm mục mới
"thay thế D-27". Các D-28…D-30 dự kiến trong plan sẽ ghi khi được duyệt.

### D-28 — Font Be Vietnam Pro + hướng giao diện "app" (thay một phần D-27/Q-04)
**Quyết định:** (Q-08) font giao diện là **Be Vietnam Pro** (OFL), đóng gói 3 file
(Regular/SemiBold/Bold) trong `assets/fonts/`, đăng ký lúc khởi động bằng
`AddFontResourceExW(path, FR_PRIVATE, 0)` qua ctypes; lỗi đăng ký → quay về
`Segoe UI Variable Text` rồi `Segoe UI`. (Q-09) toàn bộ app theo hướng "app-style":
thanh điều hướng trái thay cho tab (Chuyển thành văn bản · Luyện phát âm · Cài đặt),
bỏ khung thẻ viền, một mặt phẳng nội dung, panel chi tiết bên phải, một hành động chính
mỗi màn hình. Model + Ngôn ngữ chuyển xuống chân thanh điều hướng (thay cho "chỉ ở thanh
trên" của Q-04 trong D-27).
**Vì sao:** người dùng đánh giá font Segoe UI cũ "không hiện đại" và bố cục nhiều thẻ trông
như dashboard; Be Vietnam Pro được thiết kế cho dấu tiếng Việt và cho cùng một diện mạo trên
mọi bản Windows; không cần gói pip (I8), chạy offline (I9).
**Hệ quả:** phải kiểm tra glyph IPA (θ ð ŋ ɪ ʊ ə ˈ) của Be Vietnam Pro trong Tk trước B1; nếu
thiếu, dòng IPA dùng `Segoe UI`. File font không phải "file tải về" — được phép trong repo
(kèm giấy phép OFL). Thiết kế GATE B làm lại theo hướng này.

### D-29 — Cổng bằng chứng trước khi hiện điểm (spec S-3, GATE B)
**Quyết định:** Tab Luyện hiện trạng thái "Máy chưa nghe rõ bài đọc" — **không số, không tô
màu câu, không lưu lịch sử** — khi: (1) `low_conf` (xác suất từ TB < 0,35) **và**
`correct/total < 0,5`; (2) `garbage` mở rộng: số từ nghe ≥ 1,6 × số từ mẫu và điểm < 35,
**hoặc** câu chứa cụm "ảo giác" quen thuộc của Whisper (danh sách trong code, có test);
(3) `correct == 0` và `low_conf`.
**Vì sao:** rà soát 2026-10-22: app hiện "0.0%"/"75.0%" to khi chính nó không chắc, và hiện câu
Whisper bịa ("cảm ơn các bạn đã theo dõi…") màu đỏ như thể người học nói. Mở rộng R-06/I3.
**Hệ quả:** ngưỡng là hằng số có tên + fixture trong `smoke_test.py`; hiệu chuẩn lại ở P4.

### D-30 — Lịch sử lưu từng lần luyện (`tries`) (spec S-7)
**Quyết định:** `practice_history.json` mỗi bài thêm `"tries": [{"ts","c","t","ph"}]`, giữ 30 lần
gần nhất; file cũ thiếu `tries` = danh sách rỗng. Đếm âm vị chỉ khi ngôn ngữ nhận ra = ngôn ngữ
bài; "Âm hay sai" tính **theo ngôn ngữ**. Lần "chưa nghe rõ" (D-29) không lưu.
**Vì sao:** cần vẽ xu hướng; "Âm yếu nhất" cũ cộng lẫn bài Việt bị nhận nhầm là tiếng Anh.
**Hệ quả:** ghi nguyên tử như D-14; test di trú file cũ.

### D-31 — Mỗi màn hình có một trạng thái UI (spec S-1)
**Quyết định:** Tab/màn hình Văn bản: `idle → recording → processing → result | error`;
Luyện: `idle → recording → scoring → result | unsure | error`. Chỉ `App._set_stt_state` và
`App._set_prac_state` bật/tắt nút, đổi nhãn, hiện/ẩn thanh tiến trình; `_poll` chuyển message
thành đổi trạng thái. Đổi bài → `idle` (xóa kết quả). `rec_owner` (D-26) suy ra từ trạng thái.
Kết quả luyện vẽ từ hàm thuần `build_result_view(res, lesson)` (có test), không `t.insert` rời rạc.
**Vì sao:** ~8 cờ rời rạc gây kết quả cũ còn lại, nút kẹt nhãn, thanh tiến trình sai (A-01/A-02).

### D-32 — Token và thành phần giao diện (spec S-9 + thiết kế GATE B)
**Quyết định:** màu, chữ, khoảng cách và thành phần theo canvas thiết kế đã duyệt 2026-10-22
(`docs/UI-PLAN.md` §4.1): token sáng/tối (bg/card/side/card2/nav_sel/border/fg/muted/accent/
accent_fg/rec/rec_ring/ok/warn/bad/info/track/disabled), font Be Vietnam Pro (D-28), thanh điều
hướng trái, panel chi tiết phải, chỉ báo radio/checkbox vẽ bằng ảnh theo theme, thanh cuộn có
theme cho mọi `tk.Text`, icon cửa sổ. Tương phản chữ ≥ 4,5 : 1 ở cả hai theme.
**Vì sao:** người dùng duyệt GATE B; một bộ token chung tránh lệch màu giữa các màn hình.
**Hệ quả:** thêm màu mới phải thêm cả hai theme; widget mới dùng token, không mã màu rời.

### D-33 — Git + GitHub riêng tư (2026-10-23)
**Quyết định:** thư mục dự án là git repo, nhánh `main`, đẩy lên repo GitHub **riêng tư**
`hoannguyenvn/oriole`. `.gitignore` loại `downloads/`, `__pycache__/`, `config.json`,
`practice_history.json`; `.gitattributes` giữ LF (`.bat` CRLF), WAV/TTF nhị phân. Danh tính
commit cục bộ dùng địa chỉ no-reply GitHub. Mỗi bước (B3, B4…) kết thúc bằng một commit.
**Vì sao:** phiên B3 dừng giữa chừng mà không có cách xem/hoàn tác thay đổi; dự án chỉ
nằm trên một ổ đĩa; cần thử ở máy khác (scaling 100/150 %).
**Hệ quả:** không commit file tải về, model, dữ liệu cá nhân (AGENTS §8, I16); đổi sang
công khai cần quyết định giấy phép trước.

### D-34 — Trọng âm từ và tốc độ đọc: chỉ mô tả (2026-10-23, UI-PLAN S-5b)
**Quyết định:** dùng lại (đã sửa) hai phân tích của dự án cũ: cường độ + cao độ **theo từ**
(mốc `words_t`) để đánh dấu từ được nhấn của mẫu và của người học, và một câu về tốc độ đọc
(`dur_ref`/`dur_usr`). Cả hai **không có điểm**, không trừ điểm, không vào lịch sử; quy về
trung vị của chính người nói (I5), numpy thuần (I8). Không dùng điểm tổng, "timbre",
formant/KMeans, lỗi rải theo ngưỡng toàn cục của dự án cũ (R-01…R-08).
**Vì sao:** trọng âm là lỗ hổng thật (README: "trọng âm chưa chấm"); số đo theo từ truy được
về từ cụ thể, khác cách cũ gán một điểm toàn đoạn lên mọi từ. Chưa hiệu chuẩn ⇒ chỉ mô tả.
**Hệ quả:** mốc từng từ của audio mẫu sinh sẵn bằng `tools/build_lessons.py`; thiếu mốc mẫu
thì chỉ hiện đánh dấu của người học. Muốn chấm trọng âm phải có quyết định mới + hiệu chuẩn (P4).

### D-35 — Từ đúng chữ nhưng GOP thấy âm "lệch rõ" → gạch cam trên câu (2026-10-23)
**Quyết định:** khi Whisper nghe **đúng** một từ nhưng GOP (I6) xếp một âm trong từ đó mức
"lệch rõ" (`GOP_LEVEL_STRONG`), câu trên sân khấu gạch cam từ đó và ghi "âm /θ/ lệch" (tối
đa 2 âm) thay cho ✓. Mức "hơi lệch" không gạch. Lỗi cấp từ (máy nghe sai chữ) vẫn ưu tiên
ghi "nghe ‘…’". Điểm **không đổi**: vẫn là số từ đúng (I4), vòng điểm/tiêu đề giữ "Đúng c/t từ".
**Vì sao:** người dùng thử thật thấy "Think ✓" trên câu nhưng CẦN SỬA báo /θ/ trong "Think"
lệch rõ — hai tín hiệu trái nhau trên cùng màn. Cảnh báo cam (không trừ điểm) giữ cả hai
đúng: chữ được nghe đúng, nhưng âm cần luyện.
**Hệ quả:** `build_result_view` trả `gop_marks` {chỉ số từ tách khoảng trắng: [ipa]} (cùng
chỉ số `wi` của `gop.score`); `stage_words` dùng nó; test `gop_clearly_off_marks_stage_word`.

### D-36 — Đầu vào âm thanh + tham số Whisper cho bài luyện, đo bằng `asr_bench` (2026-10-23)
**Quyết định:**
- `resample_to_16k` lọc chống gập (FIR Kaiser, numpy) trước khi nội suy: giữ tới 7,9 kHz,
  chặn ≥ 80 dB từ 8,6 kHz. High-pass 75 Hz của `enhance_audio` vẫn là bộ lọc 1 cực của D-11,
  chỉ tính bằng FFT với đáp ứng xung của nó (không còn vòng lặp Python).
- Gain của `enhance_audio` theo `speech_peak` (đỉnh khung 10 ms ở top 2 %) thay vì một mẫu
  cao nhất; giữ trần +24 dB (D-21) và nhánh "đầu vào vỡ thì chỉ giảm".
- Bản ghi luyện: `transcribe_practice` + `PRAC_ASR_OPTS` — `temperature=0`, **không VAD**
  khi file WAV ≤ 30 s (file dài/không phải WAV vẫn VAD), vẫn `condition_on_previous_text=False`,
  không `initial_prompt` (I2). Câu tự gõ: ngôn ngữ cho Whisper = `guess_lang(target)`.
- `load_model` cache một `WhisperModel` theo cỡ.
- `tools/asr_bench.py` là thước đo bắt buộc khi đổi các số trên (`--compare`).
**Vì sao:** đo 2026-10-23, model `base`, 30 câu mẫu × 4 điều kiện mic giả lập (đúng/tổng từ):
nội suy trần để lọt 87 % tiếng 10 kHz xuống 6 kHz (dải s/sh/th); một tiếng click trên mic yếu
quyết định gain → giọng gần như không được khuếch đại → Silero VAD bỏ hết → 22/30 câu rỗng hoặc
bị chặn (26/146 từ đúng). Sau thay đổi: sạch 126 → 129, mic yếu 125 → 128, mic yếu + click
26 → 122, ồn 118 → 119. Biên lọc 7,4 kHz làm "sells" thành "fell" (ồn 114) nên chọn 7,9/8,6.
`temperature=0` trung tính trên bộ đo; giữ vì nhánh lấy mẫu dự phòng là nơi sinh câu bịa.
**Hệ quả:** I3 và các ngưỡng D-21 **không đổi** (`peak0` vẫn là đỉnh thô). Bộ đo dùng TTS
nên chỉ so trước/sau, **không** hiệu chuẩn điểm (I13); bản ghi thật chạy `--dir`. Test:
`resample_blocks_aliasing`, `highpass_matches_one_pole_loop`, `enhance_gain_ignores_click`,
`guess_lang_from_target_text`, `practice_asr_options`, `whisper_model_is_cached`.

### D-37 — Đợt 2: "máy chưa chắc", small cho bài Việt, ghi chú ồn, chỉnh Recorder (2026-10-23)
**Quyết định:**
- Từ chấm **đúng** mà xác suất Whisper < `WORD_UNSURE_P` (0,25) → câu trên sân khấu ghi
  "máy chưa chắc" (kind `unsure`, gạch xám) thay ✓, và không còn "Hoàn hảo". Điểm **không đổi** (I4).
  GOP "lệch rõ" (D-35) ưu tiên hơn.
- Bài tiếng Việt (ngôn ngữ ASR = vi) chấm bằng **`small`** khi model chọn nhỏ hơn và `small` đã có
  trên máy (`practice_model`, `whisper_model_on_disk` — không tự tải, I9); `load_model` giữ tối đa
  2 cỡ (bỏ cỡ dùng lâu nhất).
- `enhance_audio` trả `snr_db` (RMS khung 20 ms, phân vị 90 / 10); `quality_note` ghi "phòng hơi
  ồn" khi < `SNR_LOW_DB` (15 dB). **Chỉ ghi chú, không thành cổng chấm.**
- `Recorder`: nền nhiễu 0,5 s đầu theo phân vị 20 (thay trung vị); đếm `dropped` (input overflow)
  → `quality_note` "mất N đoạn âm"; bài luyện tự dừng sau `PRAC_SILENCE_SEC` = 1,8 s im lặng.
**Vì sao:** đo 2026-10-23. (1) Whisper `small` nghe TTS đọc sai "Tink" thành "Think" với p 0,80,
từ đọc đúng có khi chỉ 0,72 → xác suất từ **không** phát hiện được Whisper "sửa hộ"; ở 0,5 dấu này
báo oan ~1/5 câu đọc đúng; ở 0,25 không báo oan câu sạch/ồn, 1–2 từ ở mic yếu → chỉ là lưới an
toàn khi chính Whisper rất không chắc. (2) `base` nghe câu mẫu sạch "Lan năm nay lên lớp" thành
"là nằm này lên lắm" (1/5), `small` 5/5 ở mic yếu; asr_bench tổng: đúng 129→131 (sạch), 128→132
(yếu), 122→126 (click), 119→121 (ồn). (3) Ngưỡng SNR/cổng chưa hiệu chuẩn với phòng thật — ghi chú
trước, cổng sau P4. (4) Đọc ngay khi bấm làm trung vị 0,5 s đầu là giọng → ngưỡng bật giọng quá
cao; người học hay dừng giữa câu để nhớ từ, 1,3 s cắt ngang.
**Hệ quả:** kind mới `unsure` ở `stage_words`/`_redraw_words`; view có `unsure_words`, `model`.
Bài Việt chấm chậm hơn (small). Test: `unsure_word_loses_tick_not_points`,
`vietnamese_practice_uses_small_when_on_disk`, `snr_estimate_and_quality_note`,
`recorder_noise_floor_and_practice_silence`, `whisper_model_is_cached`.

### D-38 — Bài tiếng Việt chấp nhận giọng Bắc: r/d/gi, s/x, tr/ch (2026-10-24)
**Quyết định:** khi chấm bài tiếng Việt (`lang == "vi"`), `score_pronunciation` so từ theo
`vi_north_key`: phụ âm đầu r/d/gi → z, x → s, tr → ch. Máy nghe "dừng" cho "rừng", "sinh" cho
"xinh", "chong" cho "trong" → **đúng** (item `ok`, giữ từ máy nghe ở cột heard). Thanh và vần vẫn
phải đúng: "rủ" nghe "dù" → `tone`. N/L **không** thuộc nhóm này (vẫn báo `warn`). Không áp cho
tiếng Anh/`auto` ("red"/"dead" vẫn khác).
**Vì sao:** người dùng quyết 2026-10-24. Giọng Hà Nội nhập r/d/gi và s/x, tr/ch là phát âm chuẩn
được chấp nhận, không phải lỗi; Whisper ghi đúng chữ theo âm nghe được nên app cũ trừ oan. Bản thu
thật (đoạn văn 66 từ): AirPods 47→49, mic laptop 43→44 từ đúng.
**Hệ quả:** người học giọng Nam/Trung đọc nhầm hai âm này cũng không bị báo — chấp nhận; nếu sau
này có bài luyện riêng r/d/gi, s/x, tr/ch (ROADMAP) thì bài đó cần cách chấm khác (cờ theo bài).
Mã `đ` không đổi. Test: `northern_accent_is_correct`.

## B. Những cách làm đã bị loại (đừng lặp lại)

Nguồn: `PHASE2-DANH-GIA-DU-AN-CU.md` §2.2 và §6.

| Mã | Cách làm bị loại | Vì sao |
|---|---|---|
| R-01 | Điểm "timbre" bằng MFCC/DTW giữa hai người | phụ thuộc giới tính/micro/phòng, không phải phát âm |
| R-02 | So F0 bằng Hz tuyệt đối | nữ ~200 Hz, nam ~110 Hz → điểm range vô nghĩa |
| R-03 | KMeans gom nguyên âm rồi so tâm cụm | không biết cụm là âm gì, lệch theo tần suất |
| R-04 | Ngưỡng toàn cục rồi rải lỗi lên timestamp | lỗi phải truy được về từ/âm cụ thể |
| R-05 | Dùng transcript file mẫu làm transcript người học | phải ASR chính bản ghi người học |
| R-06 | Hiện điểm khi im lặng/nhiễu/câu quá ngắn | phải nói "chưa đủ rõ" |
| R-07 | Lời khuyên soạn sẵn theo ngưỡng | lời khuyên phải sinh từ lỗi cụ thể |
| R-08 | Nhiều chỉ số cùng lúc (pitch+timbre+formant+rate) | không chỉ số nào được hiệu chuẩn |
| R-09 | Tải cả video để lấy 10 giây audio | dùng `ba/b`, `skip_download` khi chỉ cần phụ đề |
| R-10 | Bê stack cũ (torchaudio, librosa, sklearn, openai-whisper) | nặng ~2,5 GB, trùng ASR |
| R-11 | Đưa text debug lên UI | log vào panel Nhật ký |
| R-12 | Ghi file tạm không dọn | dùng `tempfile` + `finally` |
| R-13 | Chấm bằng TTS làm chuẩn | TTS chỉ để nghe mẫu |
| R-14 | Cookie tài khoản trong repo | bảo mật |

## C. Quyết định đang chờ người dùng

| Mã | Câu hỏi | Ảnh hưởng |
|---|---|---|
| Q-01 | Ưu tiên tiếng Việt hay tiếng Anh ở Phase 2? | thứ tự roadmap, nội dung bài |
| Q-02 | Thêm ~120 MB cho GOP/onnxruntime? | dependency, đóng gói |
| Q-03 | Âm mẫu TTS hay bản ghi người thật? | chất lượng mẫu, chi phí |
| Q-04 | Có cần xuất PDF không? | UI, dependency |

Khi có câu trả lời: thêm `D-20…` tương ứng và xóa dòng khỏi bảng chờ.
