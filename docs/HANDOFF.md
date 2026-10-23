# HANDOFF — nhật ký bàn giao giữa các phiên / AI model

File này là **bộ nhớ dài hạn** của dự án. Mỗi phiên thêm một mục ở cuối.
Không sửa/xóa mục cũ (trừ khi sửa lỗi chính tả); nếu cần đính chính, thêm mục mới.

Giữ tối đa ~10 mục gần nhất trong file này; mục cũ hơn chuyển sang
`docs/handoff-archive/YYYY.md` (append, không sửa).

## 1. Quy trình 5 phút

### Mở phiên
1. Chạy `tools/context_check.py` (xem `AGENTS.md` §2).
2. Đọc `docs/PROJECT-STATE.md` mục 1–2.
3. Đọc **mục cuối** của file này.
4. Đọc `docs/DECISIONS.md` nếu sắp đổi hành vi.
5. Nạp đúng skill trong `.opencode/skills/`.
6. Viết 1 dòng vào "Đang làm" của `PROJECT-STATE` (nếu việc kéo dài nhiều bước).

### Đóng phiên
1. Cập nhật `PROJECT-STATE`: trạng thái, 3 việc tiếp, nợ kỹ thuật mới.
2. Thêm mục vào cuối file này theo template §2.
3. Chạy `context_check.py` + `smoke_test.py`; dán kết quả vào mục handoff.
4. Ghi rõ phần **chưa kiểm chứng** (mic, model tải, YouTube, DPI…).

## 2. Template mục handoff

```markdown
## YYYY-MM-DD HH:MM — <model/agent> — <việc chính>

**Mục tiêu phiên:**
- ...

**Đã làm:**
- `file.py:symbol` — thay đổi cụ thể
- ...

**Quyết định mới:** D-xx (hoặc "không")

**Đã kiểm chứng:**
- [ ] `tools/context_check.py` → PASS/FAIL
- [ ] `tools/smoke_test.py` → x/y pass
- [ ] `py_compile` → sạch
- [ ] thủ công: ...

**Chưa kiểm chứng / cần người dùng thử:**
- ...

**Việc tiếp theo (ưu tiên giảm dần):**
1. ...

**Cảnh báo cho model sau:**
- ...
```

## 3. Prompt dán sẵn khi chuyển model

> Bạn đang tiếp quản dự án **Audio to Text** tại `D:\Audio to text`.
> Hãy làm đúng thứ tự sau, không đọc toàn bộ repo:
> 1. Đọc `AGENTS.md`.
> 2. Chạy `C:\Users\ADMIN\miniforge3\python.exe tools\context_check.py`.
> 3. Đọc `docs/PROJECT-STATE.md`, mục cuối `docs/HANDOFF.md`, `docs/DECISIONS.md`.
> 4. Nạp skill khớp việc cần làm trong `.opencode/skills/`.
> 5. Tóm tắt lại: hiện trạng, việc đang dở, rủi ro, rồi mới đề xuất bước tiếp.
> Không phá các bất biến I1–I16 trong `AGENTS.md`. Kết thúc phiên phải cập nhật
> `PROJECT-STATE` + thêm mục `HANDOFF`.

## 4. Nhật ký

## 2026-10-22 — DeepSeek V4.1 Flash — Khảo sát & dựng hệ context/skills

**Mục tiêu phiên:**
- Khảo sát dự án, đối chiếu chuẩn Agent Skills trên GitHub/OpenCode.
- Dựng bộ skills theo từng tính năng.
- Dựng cơ chế giữ context khi chuyển AI model.

**Đã làm:**
- `AGENTS.md` — luật làm việc, bất biến I1–I16, nghi thức phiên, bản đồ code.
- `docs/ARCHITECTURE.md` — 4 luồng dữ liệu, contract dữ liệu, điểm mở rộng.
- `docs/FEATURES.md` — bản đồ tính năng → code → skill → cách kiểm chứng.
- `docs/DECISIONS.md` — 19 quyết định, 14 cách làm bị loại, 4 câu hỏi mở.
- `docs/PROJECT-STATE.md` — hiện trạng, nợ kỹ thuật, 3 việc tiếp.
- `docs/ROADMAP.md` — lộ trình Phase 2A/2B + tiêu chí nghiệm thu.
- `.opencode/skills/` — 11 skill (xem `AGENTS.md` §6).
- `tools/context_map.json` (trong `docs/`) + `tools/context_check.py` —
  kiểm tra drift tài liệu/symbol/skill/asset.
- `tools/smoke_test.py` — test khói hàm thuần, không cần mic/model.

**Quyết định mới:** D-17 (skills + context là nguồn sự thật vận hành).

**Đã kiểm chứng:**
- [ ] `tools/context_check.py` → chạy sau khi tạo file
- [ ] `tools/smoke_test.py` → chạy sau khi tạo file
- [ ] `py_compile` → chạy sau khi tạo file
- [x] Đọc code thực tế: `app.py` (các luồng), `pron_en.py`, `gop.py`, `prosody.py`
- [x] Đối chiếu chuẩn skills: OpenCode V2 docs, `anthropics/skills`, `obra/superpowers`

**Chưa kiểm chứng / cần người dùng thử:**
- Chưa mở app, chưa thu âm, chưa chạy Whisper/YouTube trong phiên này.
- Chưa kiểm tra hiển thị tiếng Việt trên console (đã dùng `PYTHONIOENCODING=utf-8`).
- Chưa khởi tạo git/CI.

**Việc tiếp theo:**
1. Chạy `tools/context_check.py` + `smoke_test.py`, sửa nếu FAIL.
2. Mở app, thử luồng file ngắn + thu âm 3 giây để xác nhận không hồi quy.
3. Bắt đầu P1/P2 trong `docs/PROJECT-STATE.md`.

**Cảnh báo cho model sau:**
- `app.py` rất lớn: dùng `docs/context-map.json` + skill, đừng đọc cả file.
- `lessons_en.json` có `samples` nhưng app bỏ qua; đừng sửa trường đó rồi tưởng có tác dụng.
- Console mặc định cp1252: luôn đặt `PYTHONIOENCODING=utf-8` trước khi in tiếng Việt.

## 2026-10-22 18:29 — DeepSeek V4.1 Flash — Hoàn tất 11 skill + sửa nút theme

**Mục tiêu phiên:**
- Viết nốt 6 skill còn thiếu và làm cho `context_check` xanh hoàn toàn.
- Sửa lỗi người dùng thấy được nếu phát hiện trong lúc đọc code.

**Đã làm:**
- `.opencode/skills/app-phonemes/SKILL.md` — CMUdict, IPA, `align`, `compare_words`,
  `analyze_pairs`, `TIPS`/`LETTER_TIPS`; GOP `gop.score`, ngưỡng tương đối với mẫu.
- `.opencode/skills/app-prosody/SKILL.md` — `f0_track`, `contour`, `compare`, DTW,
  `_show_intonation`/`_draw_intonation`, quy tắc bán cung, không chấm điểm.
- `.opencode/skills/app-ui/SKILL.md` — DPI `self.S`/`px()`, `THEMES`, `_queue`/`_poll`,
  `DEFAULT_CFG`, phím tắt, đóng app.
- `.opencode/skills/app-lessons/SKILL.md` — schema `lessons_en.json`, `build_lessons.py`,
  quy ước `mau/en/<id>.wav`, `<id>_slow.wav`, `w_<word>.wav`, lưu ý `samples` bị bỏ qua.
- `.opencode/skills/app-qa-release/SKILL.md` — 3 lệnh kiểm tra, ma trận test thủ công,
  dependency, `run.bat`, giới hạn phát hành.
- `.opencode/skills/skill-authoring/SKILL.md` — quy ước frontmatter/body, đăng ký
  `docs/context-map.json`, template.
- `app.py:App._flip_theme` — nút "Chế độ" ở header trước đây gọi `_toggle_theme`
  nhưng không đổi `theme_name`, nên bấm không có tác dụng. Thêm hàm đảo theme riêng;
  radio trong Cài đặt vẫn dùng `_toggle_theme` (không đảo lần hai).
- `docs/context-map.json` — thêm symbol `App._flip_theme`.
- `AGENTS.md` §5 — sửa lệnh `py_compile`: PowerShell **không** tự mở rộng
  `tools\*.py`, phải liệt kê từng file.
- `README.md` — thêm mục 9 (context & skills), ghi chú nút theme, danh sách file.
- `docs/PROJECT-STATE.md` — đánh dấu P1 xong, cập nhật rủi ro test/skill, thêm lệnh
  `py_compile` đúng.

**Quyết định mới:** không (D-17 đã phủ).

**Đã kiểm chứng:**
- [x] `tools/context_check.py` → **40 OK · 0 WARN · 0 FAIL**
- [x] `tools/context_check.py --snapshot` → đã ghi `docs/CONTEXT-SNAPSHOT.md`
- [x] `tools/smoke_test.py` → **21/21 PASS**
- [x] `py_compile` (8 file, liệt kê tường minh) → sạch
- [x] UI smoke: `App()` → `_flip_theme()` → `light → dark`, gọi lại → về `light`,
      `a.P["bg"]` đổi đúng; đã trả theme gốc vào `config.json`.

**Chưa kiểm chứng / cần người dùng thử:**
- Chưa thu âm, chưa chạy Whisper, chưa tải YouTube trong phiên này.
- Chưa thử DPI 150%/250% và cả 2 theme bằng mắt trên toàn bộ 3 tab.
- Chưa chấm thử GOP (cần torch + model 1,2 GB).
- Chưa kiểm tra `run.bat` trên máy khác (đường dẫn Python hard-code).

**Việc tiếp theo (ưu tiên giảm dần):**
1. Mở app, thử M1 (file ngắn), M5 (ghi âm 3 s), M12–M13 (`en_th`), M17–M18 (theme/DPI).
2. Làm P2 trong `PROJECT-STATE`: bố cục 3 cột + chip lỗi theo âm.
3. Làm P3: phân loại 6 thanh tiếng Việt bằng F0 (cần thêm test + `D-xx`).

**Cảnh báo cho model sau:**
- `_toggle_theme` **không** đảo theme; đừng "sửa" nó thành tự đảo, radio sẽ ngược.
- `py_compile tools\*.py` trong PowerShell sẽ lỗi `[Errno 22]`; dùng lệnh ở `AGENTS.md` §5.
- `smoke_test.lessons_loaded` assert cứng 18 `SET_IDS`; thêm bài phải sửa test.
- Skill mới phải thêm vào `docs/context-map.json → skills`, nếu không `context_check` FAIL.

## 2026-10-22 (tiếp) — DeepSeek V4.1 Flash — Sửa lỗi mic im lặng

**Mục tiêu phiên:**
- Người dùng không dùng được tab luyện phát âm: app báo "mic im lặng" / "không nghe
  thấy giọng" với mọi lựa chọn micro.

**Chẩn đoán (số đo thật trên máy):**
- `config.json` đang lưu `Microphone (Realtek HD Audio Mic input) [Windows WDM-KS]`.
  Mọi thiết bị WDM-KS đều lỗi `InputStream`: `Blocking API not supported` → 0 khung.
- Micro dùng được: dev 1 (MME), dev 5 (DirectSound), dev 9 (WASAPI) — cùng là
  Microphone Array Intel SST. Đo khi người dùng nói, `channels=1` (2 kênh cho ~0%):
  DirectSound **2,01%**, MME 0,42%, WASAPI 0,31% đỉnh.
- Hệ quả: ngưỡng RMS bắt giọng cũ 1,2% cao hơn RMS thực (~0,5%) → `speech_seen`
  không bao giờ bật → báo "không nghe thấy giọng".

**Đã làm:**
- `app.py:list_usable_mics` — lọc WDM-KS khỏi ô chọn micro (fallback nếu máy chỉ có WDM-KS).
- `app.py:App._refresh_mics` — dùng `list_usable_mics`; config cũ trỏ WDM-KS tự được thay.
- `app.py:pick_default_mic` — DirectSound (+2) > WASAPI (+1) > MME (0); trừ điểm thiết bị
  alias ("Sound Mapper"/"Primary Sound"); WDM-KS -1.
- `app.py`: thêm `MIC_MIN_PEAK=0.008`, `MIC_GOOD_PEAK=0.03`, `REC_GAIN_MAX=16.0`.
- `app.py:Recorder.start` — ngưỡng bắt giọng `max(0.004, noise*2.2)`, giữ giọng
  `max(0.0025, noise*1.2)`.
- `app.py:enhance_audio` — gain tối đa +24 dB (trước +12 dB).
- `app.py:App._prac_stop_and_score` — cổng im lặng dùng `MIC_MIN_PEAK`.
- `app.py:App._test_mic` — thu 2 s, báo đỉnh % + dB + RMS, 4 mức TỐT/NHỎ/IM LẶNG/VỠ.
- `app.py:App._find_mic_auto` — dò 1 s/mic, timeout 20 s.
- `tools/smoke_test.py` — thêm `usable_mics_drops_wdmks`, `pick_default_prefers_real_mic`,
  `enhance_lifts_weak_mic` → **24 test**.
- `AGENTS.md` I3 — sàn "im lặng" 2% → 0,8% (kèm lý do); `docs/DECISIONS.md` D-20, D-21;
  `.opencode/skills/app-recording/SKILL.md`; `docs/PROJECT-STATE.md`.

**Quyết định mới:** D-20 (lọc WDM-KS + ưu tiên host API), D-21 (hỗ trợ micro yếu).

**Đã kiểm chứng:**
- [x] `py_compile app.py tools/smoke_test.py` → sạch
- [x] `tools/smoke_test.py` → **24/24 PASS · 0 FAIL**
- [x] `tools/context_check.py` → **40 OK · 0 WARN · 0 FAIL**
- [x] Đo thiết bị thật + đo tín hiệu khi người dùng nói (bảng ở trên)
- [x] `app.pick_default_mic` trên máy này → dev 5 (DirectSound)

**Chưa kiểm chứng / cần người dùng thử:**
- **Chưa** thu âm + chấm điểm thật sau khi sửa. Chưa biết Whisper có nhận đúng với
  bản ghi đỉnh ~2% đã khuếch đại +24 dB hay không.
- Chưa xác nhận Microphone Level trong Windows là bao nhiêu (không đọc được nếu
  không thêm dependency). Người dùng cần đặt 100% + Boost nếu có.
- Chưa thử Tab 1 (ghi âm dài) sau khi đổi ngưỡng.

**Việc tiếp theo:**
1. Người dùng tăng Microphone Level (Settings → System → Sound → Input → Properties →
   Levels = 100%, Microphone Boost) rồi mở app: Tab Cài đặt → Kiểm tra mic → báo
   đỉnh %/dB/RMS. Ô Micro phải **không** còn dòng `[Windows WDM-KS]`.
2. Nếu đỉnh vẫn < 3%: thử Tab 2 đọc 1 câu; nếu Whisper không ra chữ, cân nhắc
   `MIC_MIN_PEAK`/gain hoặc khuyên dùng mic ngoài (ghi D-xx mới).
3. Sau đó mới tiếp M1/M5/M12–M13/M17–M18 và P2.

**Cảnh báo cho model sau:**
- Đừng nâng lại ngưỡng về 2%/RMS 1,2% mà không đọc D-21: micro array máy này chỉ ~2%.
- `sd.rec(..., channels=2)` cho ~0% trên máy này; luôn đo `channels=1`.
- WDM-KS **không bao giờ** dùng được với `Recorder` (blocking read). Đừng "thử lại".
- `best_input_mic` đo 1 s; nếu người dùng im lặng đúng lúc đó sẽ không tìm thấy gì.

## 2026-10-22 (tiếp 2) — DeepSeek V4.1 Flash — Mic ngoài (AirPods/USB)

**Mục tiêu phiên:**
- Người dùng kết nối AirPods Pro qua Bluetooth nhưng app không nhận;
  yêu cầu "bổ sung thêm chọn mic ngoài".

**Chẩn đoán:**
- Liệt kê thiết bị (tiến trình mới): AirPods **chỉ có ở danh sách OUTPUT**
  (`Headphones (AirPods Pro - Find My)` ở MME/DirectSound/WASAPI/WDM-KS), **không có
  thiết bị input** nào → Windows chưa mở profile Hands-Free (HFP), nên không app nào
  (kể cả app này) chọn được mic AirPods. Đây là vấn đề cấu hình Windows, không phải bug app.
- Nguyên nhân phụ trong app: PortAudio chỉ liệt kê thiết bị **một lần** lúc khởi tạo,
  nên nút "Làm mới" cũ không bao giờ thấy thiết bị cắm sau khi mở app.

**Đã làm:**
- `app.py:rescan_audio_devices` — `sd._terminate()` + `sd._initialize()` để đọc lại
  danh sách thiết bị (chỉ gọi khi không có stream đang chạy).
- `app.py:headset_mic_missing` + `_device_brand_key` — phát hiện tai nghe bluetooth chỉ
  có chiều nghe, trả tên để UI hiện gợi ý bật Hands-Free.
- `app.py:App._refresh_mics(rescan=False)` — nhận cờ rescan; cập nhật gợi ý mic.
- `app.py:App._mic_hint_text`, `App._update_mic_hint`, `App._open_sound_settings`,
  `App._on_tab_changed` — gợi ý dưới ô Micro, nút **Âm thanh Windows**
  (`ms-settings:sound`), tự quét lại khi mở tab Cài đặt.
- `app.py:App._mk_mic_row` — nút "Làm mới" → **Quét lại** (có rescan), thêm nút
  **Âm thanh Windows** + nhãn gợi ý; cập nhật 2 thông báo cũ còn ghi "Làm mới".
- `app.py:App._mic_help_text` — thêm hướng dẫn mic ngoài/bluetooth.
- `tools/smoke_test.py` — `headset_without_mic_is_detected` → **25 test**.
- `docs/context-map.json` — thêm `rescan_audio_devices`, `headset_mic_missing`,
  `App._on_tab_changed`, `App._open_sound_settings`.
- `docs/DECISIONS.md` D-22; skill `app-recording` + `app-qa-release` (M11);
  `README.md`; `docs/PROJECT-STATE.md`.

**Quyết định mới:** D-22.

**Đã kiểm chứng:**
- [x] `py_compile` → sạch
- [x] `tools/smoke_test.py` → **25/25 PASS · 0 FAIL**
- [x] `tools/context_check.py` → **40 OK · 0 WARN · 0 FAIL**
- [x] UI headless: `App()` → mic 5 mục, `_mic_hint_text()` báo đúng AirPods thiếu mic,
      `_on_tab_changed()` và `_refresh_mics(rescan=True)` chạy không lỗi
- [x] `headset_mic_missing()` trên máy thật → trả `Headphones (AirPods Pro - Find My)`
- [x] `rescan_audio_devices()` trên máy thật → True

**Chưa kiểm chứng / cần người dùng thử:**
- Chưa xác nhận AirPods sau khi bật Hands-Free có hiện thành thiết bị thu hay không
  (phụ thuộc driver/Windows; có máy không hỗ trợ).
- Chưa thu âm + chấm điểm bằng mic ngoài.
- Chưa thử cắm/rút USB mic thật.

**Việc tiếp theo:**
1. Người dùng bật Hands-Free cho AirPods (hướng dẫn hiện ngay dưới ô Micro) → **Quét lại**
   → Kiểm tra mic → báo đỉnh %/dB/RMS.
2. Nếu AirPods không lên được: dùng mic array + tăng Microphone Level, hoặc mic USB.
3. Sau đó chạy ma trận thủ công M1/M5/M11–M13/M17–M18 rồi mới làm P2.

**Cảnh báo cho model sau:**
- App **không thể** tạo thiết bị thu mà Windows không cấp; đừng hứa "chọn được AirPods".
- `rescan_audio_devices` gọi `sd._terminate()` — **chỉ** gọi khi không thu/phát/dò,
  nếu không sẽ làm đứt stream (đã có cờ chặn trong `_refresh_mics`).
- `headset_mic_missing(devices=None)` nhận danh sách giả để test; giữ tham số này.

## 2026-10-22 (tiếp 3) — DeepSeek V4.1 Flash — `stream.read` trả toàn số 0 (DirectSound)

**Mục tiêu:** giải thích vì sao bản ghi AirPods cho 0/10 từ, "nhận diện sai".

**Phát hiện chính (đã đo, không suy đoán):**
- `Recorder` cũ dùng `InputStream.read()` blocking. Trên **DirectSound (dev 5)** cách này
  trả **100 % số 0** ở cả `blocksize=0` và `4410`, trong khi `sd.rec` và **callback** trên
  *cùng thiết bị* thu bình thường (nền 0,006–0,09 % đỉnh). Đây là nguyên nhân thật của
  "mic im lặng" và các file `luyen_*.wav` dài 180 s toàn im lặng.
- MME (dev 1) và WASAPI (dev 9) vẫn thu được ở chế độ blocking, nhưng callback chạy cho cả ba.
- WASAPI đôi lúc mở stream lỗi `WdmSyncIoctl … prop_id = 10` (thiết bị bận/stream cũ chưa đóng).
- Hai bản ghi AirPods của người dùng (`luyen_qwidcubj.wav` 4,6 s, `luyen_tir4eswm.wav`
  5,7 s): có năng lượng (RMS 6–9 %, đỉnh 60 %, không vỡ, 14–21 % khung im lặng) nhưng
  Whisper **base** và **small** với `language="vi"` đều **không ra chữ** (`'Mỡ Mỡ Mỡ'`,
  `''`, hoặc hallucination "subscribe…"), thử cả 8 hệ số tốc độ 0,33–2,0 → không hệ số nào ra
  câu đúng ⇒ **audio không đủ rõ cho ASR**, không phải lỗi tốc độ mẫu.
- Đối chứng: `mau/vi_cau.wav` (TTS sạch) với model `base` → `"là nằm này lên lắm"`;
  các mẫu Anh → đúng. Nên `base` yếu với tiếng Việt, cần khuyến nghị `small`.

**Đã sửa:**
- `app.py:Recorder.start` — **callback + `queue.Queue`** (block 100 ms), không dùng
  `stream.read`; `stop()` drain queue trước khi trả frames; `__init__` thêm `_blocks`.
  Thông điệp lỗi mới cho `WdmSyncIoctl`/`Unanticipated host error` (thiết bị bận).
- `app.py:App._prac_done` — dòng "Bạn đọc" hiện **từ máy nghe được** (`hw`) cho mục `bad`,
  `∅` nếu không nghe thấy. Trước đây hiện **từ mẫu** nên trông như đọc đúng dù 0 %.
  Thêm mục "Chưa khớp (mẫu → máy nghe)" khi có từ nghe sai (chỉ tiếng Việt, `correct > 0`).
- Nhánh 0 từ: nếu `garbage` thì giải thích mic ồn/tai nghe chưa đeo đúng + gợi ý `small`.
- `app.py:App._w_prac` — ngưỡng file dùng `MIC_MIN_PEAK` thay vì `0.02` hard-code.

**Đã kiểm chứng:**
- [x] `Recorder` dev1/dev5 (MME/DirectSound) sau sửa: peak nền 0,024 % / 0,092 %, frames 1,90 s
- [x] `py_compile`, `tools/smoke_test.py` (26/26), `tools/context_check.py` (40 OK)
- [x] Thêm test hồi quy `recorder_uses_callback_not_blocking_read` (chặn quay lại `stream.read`)
- [x] Callback trên dev9 (WASAPI) chạy khi thiết bị không bận

**Chưa kiểm chứng / cần người dùng thử:**
- Thu âm + chấm điểm thật end-to-end sau D-23 (mic array và AirPods).
- AirPods đang **ngắt kết nối** lúc phân tích → không đo lại được; các bản ghi cũ có thể
  được thu khi tai nghe không đeo đúng.
- Mic array có đủ rõ cho Whisper `small` sau +24 dB hay không.

**Việc tiếp theo:**
1. Người dùng **đeo** AirPods → Cài đặt (tự Quét lại) → chọn `Headset (… Hands-Free)`
   → **Kiểm tra** 2 s → báo %/dB/RMS; rồi thu 1 câu.
2. Nếu bản ghi vẫn không ra chữ: dùng mic array (DirectSound) hoặc mic USB.
3. Chọn model **small** cho tiếng Việt; chạy ma trận M1/M5/M11–M13/M17–M18.

**Cảnh báo cho model sau:**
- Tuyệt đối **không** quay lại `stream.read` cho `Recorder` (D-23); muốn đổi phải đo lại
  bằng `sd.rec` + callback trên dev 5.
- Callback **không** được chạm widget (chỉ `queue.put`) — giữ I1.
- Đừng kết luận "mic yếu" chỉ từ file đã qua `enhance_audio` (đã chuẩn hóa đỉnh).
- AirPods chỉ thu khi **đeo**; nếu để trên bàn, mic thu tiếng ù rất nhỏ.

## 2026-10-22 (tiếp 4) — Claude Opus 5.5 — YouTube: UI kẹt bận sau Hủy/lỗi

**Nguyên nhân gốc (đã tái hiện bằng worker thật + mạng):**
- `App._w_yt` chạy trực tiếp trong `Thread` mà **không có** `try/except` ngoài cùng
  (khác `_w_file`). Bấm Hủy khi đang tải → hook ném `_YtCancelled`, được `raise` lại
  ở `except _YtCancelled: raise` → thread chết, không gửi `result`/`error` →
  `_on_error`/`_set_busy(False)` không bao giờ chạy → UI kẹt "Đang hủy…", khóa nút.
  Cùng hậu quả với mọi lỗi ngoài các `try` nhỏ (tải audio tạm cho Whisper, load model,
  ghi `.srt`, …).
- Phụ: nhánh "Chỉ transcript" → Whisper tải audio tạm **ngoài** `finally` và không có
  hook → Hủy vô tác dụng khi tải, lỗi để lại `stt_yt_*` trong `%TEMP%` (phá I10/I11).

**Đã sửa:**
- `app.py:App._w_yt` → lớp bọc gọi `App._w_yt_body` (thân cũ); hủy → `__cancelled__`,
  lỗi → `"Lỗi YouTube: …"` (nếu `cancel_flag` thì coi là hủy). D-24.
- Nhánh Whisper: thêm `progress_hooks`, tải + nhận dạng trong `try/finally`
  `shutil.rmtree(tmp_dir)`. Thêm `import shutil`.
- Test khói `yt_worker_always_reports_back`. Cập nhật skill `app-youtube`, `DECISIONS`
  (D-24), `ARCHITECTURE`, `context-map.json`, `PROJECT-STATE` (2 rủi ro mới).

**Đã kiểm chứng (mạng thật, yt-dlp 2026.08.19):**
- [x] Trước sửa: Hủy giữa lúc tải video → hàng đợi chỉ có `log`/`status`, không `error`.
- [x] Sau sửa: cùng kịch bản → `("error", "__cancelled__")`; thư mục ra không hợp lệ →
  `error` có thông điệp; chế độ "Chỉ transcript" (dQw4w9WgXcQ) → `result` + `.srt/.txt`,
  không tải mp4.
- [x] Video MP4 720 + phụ đề en và Audio MP3 (jNQXAC9IVRw) tải + tìm file đúng.
- [x] `py_compile`, `smoke_test` (27/27), `context_check`.

**Chưa kiểm chứng:**
- Chưa bấm thử trong GUI thật; chưa thử nhúng phụ đề rồi mở bằng VLC; chưa chạy nhánh
  Whisper thật (đã stub) trong phiên này.
- File `*.part` vẫn có thể còn trong thư mục đích sau Hủy (đã ghi nhận trong skill).

**Cảnh báo cho model sau:**
- yt-dlp in "No supported JavaScript runtime" (thiếu `deno`) — app đang ẩn qua
  `no_warnings`. Hiện vẫn tải được; nếu người dùng báo 403/"Requested format is not
  available" thì đây là nghi phạm số 1.
- `bv*[ext=mp4]` chọn AV1 (format 395/399/401); xem rủi ro trong `PROJECT-STATE` §3.

## 2026-10-22 (tiếp 5) — Claude Opus 5.5 — YouTube: lỗi 429 phụ đề làm hỏng tải video

**Người dùng báo:** video 2UIqadUjQf8 (tiếng Việt), Video MP4 + phụ đề Tiếng Anh →
hộp thoại "Tải video lỗi: Unable to download video subtitles for 'en': HTTP Error 429",
không có MP4. Và "app không có nút tải".

**Nguyên nhân gốc:** media + phụ đề tải trong **một** lệnh yt-dlp; yt-dlp coi lỗi tải
phụ đề là lỗi chết (`YoutubeDL._write_subtitles`). YouTube trả 429 cho phụ đề `en`
dịch máy → mất cả video. Phụ: log không cảnh báo `en` là bản dịch máy (luật cũ bỏ qua `en`).
Nút "Bắt đầu" không gợi ý là nút tải.

**Đã sửa:** D-25 — tách lệnh (media không kèm phụ đề), helper `App._yt_fetch_sub_cues`
(thử lại 1 lần khi 429, lỗi → Whisper), cờ `from_video` để ghi đúng "do Whisper tạo",
cảnh báo dịch máy cho phụ đề tự động khác ngôn ngữ gốc, nút đổi tên theo chế độ.
README + skill `app-youtube` + `context-map.json` + test khói mới (28/28).

**Đã kiểm chứng (mạng thật):** video người dùng, chế độ Video + `en` → 429 thật →
MP4 vẫn lưu, phụ đề sang Whisper (Whisper đã stub); 429 giả lập ở cả 2 chế độ; chế độ
Chỉ transcript + Tự động → lấy được phụ đề `vi` gốc (57 dòng).

**Chưa kiểm chứng:** Whisper thật trên video này; nhúng phụ đề rồi mở bằng VLC;
người dùng chưa xác nhận trong GUI.

## 2026-10-22 (tiếp 6) — Claude Opus 5.5 — Đặt tên app: **Oriole**

- Người dùng đặt tên app là **Oriole** (trước đây chỉ là mô tả "Audio to Text").
- Đã đổi: `APP_TITLE` (thanh tiêu đề), nhãn H1 ở header, `README.md` (dòng tiêu đề),
  `run.bat`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT-STATE.md`,
  `docs/context-map.json` (`project.name`), 11 skill, docstring `tools/*.py`.
- **Không** đổi: thư mục `D:\Audio to text` (người dùng chưa yêu cầu; `config.json`
  `out_dir` trỏ vào đó), các mục HANDOFF cũ, `PHASE2-DANH-GIA-DU-AN-CU.md` (lịch sử).
- Đã kiểm chứng: `py_compile`, `smoke_test`, `context_check`; mở app thấy tên mới.

## 2026-10-22 (tiếp 7) — Claude Opus 5.5 — Đổi thư mục dự án thành `D:\Oriole`

- Thư mục `D:\Audio to text` → `D:\Oriole` (theo yêu cầu người dùng).
- Đã sửa đường dẫn tuyệt đối: `config.json` (`out_dir` → `D:\Oriole\downloads`),
  skill `project-context` (dòng "tiếp quản dự án"). Code dùng `BASE_DIR` tương đối nên
  không cần sửa; `run.bat` dùng đường dẫn tương đối.
- Các mục HANDOFF cũ vẫn ghi `D:\Audio to text` — là lịch sử, không sửa.
- Bộ nhớ của Claude Code gắn theo đường dẫn thư mục → phiên mới mở `D:\Oriole` bắt đầu
  bộ nhớ trống; mọi thứ cần thiết đã nằm trong `docs/`.

## 2026-10-22 (tiếp 8) — Claude Opus 5.5 — Rà soát code + cập nhật 11 skill

**Mục tiêu phiên:** người dùng yêu cầu đọc kỹ code để hiểu chức năng chính, đề xuất cải
tiến, và rà soát/cập nhật skill. **Không sửa code** trong phiên này.

**Đã làm (chỉ tài liệu):**
- Skill lệch code đã sửa: `app-recording` (sàn 0,008 thay 0,02; timeout dò mic 20 s; hiện
  trạng xóa file tạm), `app-pronunciation` (gate `MIC_MIN_PEAK`; dòng "Bạn đọc" in từ máy
  nghe; mục "Nợ đã biết"), `app-ui` (payload `progress` 0..1, `prac_autostop` là `reason`,
  `mic_found` có thể `None`; `_on_close` thực tế không dừng recorder; mục trạng thái dùng
  chung giữa tab), `app-transcription` (`REC_LONG_SEC`; khi nào file tạm **không** bị xóa),
  `app-youtube` (luật cảnh báo dịch máy theo D-25; luồng dùng `_yt_fetch_sub_cues`; lỗi
  thanh tiến trình), `app-prosody` (guide + bài Việt không có biểu đồ), `app-qa-release`
  (28 test, lệnh `py_compile` đầy đủ, bảng phủ test, M21 rác tạm), `app-phonemes` (lỗi gõ
  tên skill), `project-context` (ví dụ ngưỡng 0,8%).
- `docs/ARCHITECTURE.md`: 2 chỗ ngưỡng `peak0 < 2%` → `MIC_MIN_PEAK`.
- `docs/PROJECT-STATE.md` §3: thêm 4 lỗi mới (rò rỉ WAV tạm, thanh tiến trình YouTube,
  trạng thái thu dùng chung, `enhance_audio` chậm).
- `DECISIONS.md` **không** sửa (D-06 ghi 2% là lịch sử; D-21 đã thay thế).

**Quyết định mới:** không.

**Lỗi tìm thấy (chưa sửa, đã xác minh bằng đọc code):**
1. `_prac_stop_and_score` / `last_wav`: `luyen_*.wav` không bao giờ xóa — đo được 15 file,
   45 MB trong `%TEMP%`. `_rec_stop_and_transcribe` bỏ lại `stt_*.wav` khi < 0,4 s.
2. `_w_yt_body.hook`: `("progress", 100.0 * done / total)` nhưng `_pbar` nhân thêm 100.
3. `_prac_record` dùng chung `self.recording` với Tab 1; `_cancel` chỉ reset UI Tab 1.
4. `_w_prac`: fallback `"".join(s.text for s in segs)` luôn rỗng (generator đã cạn).
5. `_w_file`: lỗi thường (không phải hủy) không xóa file tạm khi `delete_after=True`.

**Đã kiểm chứng:** xem kết quả lệnh cuối phiên bên dưới.

**Chưa kiểm chứng:** không chạy thử GUI/mic/YouTube trong phiên này; các lỗi trên kết
luận từ đọc code (riêng lỗi 1 đã đếm file thật trong `%TEMP%`).

**Việc tiếp theo (ưu tiên giảm dần):**
1. Sửa lỗi 1–5 (nhỏ, an toàn, có thể thêm test khói cho lỗi 2 và 4).
2. Cache `WhisperModel` theo `model_size` (nhanh rõ rệt khi luyện nhiều câu).
3. Tiếp P2/P3 như `PROJECT-STATE` §1.

**Cảnh báo cho model sau:**
- Các skill giờ ghi rõ hành vi **hiện tại** kể cả lỗi (mục "Nợ đã biết"/"Cạm bẫy"). Sửa
  lỗi nào thì xóa dòng tương ứng trong skill + `PROJECT-STATE` §3 cùng phiên.

## 2026-10-22 (tiếp 9) — Claude Opus 5.5 — Sửa 5 lỗi từ đợt rà soát

**Mục tiêu phiên:** sửa 5 lỗi ghi ở mục (tiếp 8), thêm test khói, cập nhật skill/tài liệu.

**Đã làm (`app.py`):**
- `remove_temp(path)` (mới, hàm thuần) — xóa file tạm an toàn.
- `App._set_last_wav(path)` (mới) — đổi bản Nghe lại, xóa `luyen_*.wav` cũ. Dùng trong
  `_prac_stop_and_score`, `_prac_from_file`, `_on_close`. (Lỗi 1)
- `App._rec_stop_and_transcribe` — không gán `last_wav` nữa; bản thu < 0,4 s bị xóa. (Lỗi 1)
- `App._w_file` — xóa bản ghi tạm trong `finally` (cả khi lỗi). (Lỗi 5)
- `yt_progress_fraction(d)` (mới) — hook YouTube gửi `progress` 0..1. (Lỗi 2)
- `App.rec_owner` + `App._stop_recorder()` (mới); `_primary`, `_prac_record`, `_cancel`,
  `_rec_stop_and_transcribe`, `_prac_stop_and_score`, `_poll` (`rec_error`),
  `_prac_error` kiểm tra owner. Esc khi luyện reset nút tab 2. (Lỗi 3)
- `App._w_prac` — gom text dự phòng trong cùng vòng lặp generator. (Lỗi 4)
- `App._on_close` — đặt `cancel_flag`, dừng recorder/phát, xóa bản ghi luyện tạm.

**Quyết định mới:** D-26 (recorder có chủ; một chỗ xóa file tạm).

**Tài liệu:** skill `app-recording`, `app-pronunciation`, `app-ui`, `app-transcription`,
`app-youtube`, `app-qa-release`; `ARCHITECTURE.md`, `DECISIONS.md` (D-26),
`PROJECT-STATE.md` (§2 số test, §3 bỏ 3 rủi ro đã sửa), `context-map.json` (+4 symbol).

**Đã kiểm chứng:**
- [x] `tools/smoke_test.py` → 34/34 PASS (6 test mới: `remove_temp_is_safe`,
  `practice_replay_wav_is_replaced_not_leaked`, `w_file_removes_temp_recording_on_error`,
  `yt_progress_is_a_fraction`, `practice_hyp_falls_back_to_segment_text`,
  `recording_belongs_to_one_tab`)
- [x] `py_compile` sạch; `context_check` → xem lần chạy cuối phiên
- [x] Dựng `App()` thật rồi gọi `_on_close` sau 2,5 s → đóng sạch, `rec_owner=None`

**Chưa kiểm chứng / cần người dùng thử:**
- Thu âm thật ở tab 2 nhiều lần → `%TEMP%` chỉ còn tối đa 1 `luyen_*.wav` khi app mở,
  0 sau khi đóng.
- Tải YouTube thật → thanh tiến trình chạy dần.
- Bấm chéo tab khi đang thu; Esc khi đang luyện.
- 15 file `luyen_*.wav` cũ (~45 MB) vẫn còn trong `%TEMP%` — chờ người dùng đồng ý xóa.
- Cửa sổ app mở từ trước (pid 6348) vẫn chạy code cũ — phải mở lại.

**Việc tiếp theo:** cache `WhisperModel` theo `model_size`; vector hóa high-pass trong
`enhance_audio`; P2/P3.

**Cảnh báo cho model sau:** đọc D-26 trước khi đụng `recording`/`last_wav`.

- Cập nhật cùng ngày: người dùng đồng ý → đã xóa 15 file `luyen_*.wav` cũ trong `%TEMP%`; mở lại app bằng code mới (pid 8016).

## 2026-10-22 (tiếp 10) — Claude Opus 5.5 — Rà soát giao diện (chỉ đánh giá, không sửa code)

**Cách làm:** script ngoài repo dựng `App()` thật, nạp dữ liệu giả (kết quả chuyển văn bản,
kết quả chấm `en_th` có lỗi th/dh + ngữ điệu), chụp 13 ảnh: 3 tab × sáng/tối × kích thước
tối thiểu. Máy người dùng: màn 3840×2400, Windows scaling 250% (`App.S ≈ 2,5`).
Không ghi `config.json` (đã chặn `save_config`).

**Lỗi hiển thị thấy được (chưa sửa):**
1. Tab 2: đổi bài/chế độ giữ nguyên điểm + kết quả của bài trước (`_refresh_practice`).
2. Theme tối: radio **chưa** chọn tô trắng đặc, radio đã chọn rỗng — ngược nghĩa.
3. Checkbox đã chọn vẽ "X" (mặc định `clam`) — đọc như "tắt".
4. Combobox disabled (vd Ngôn ngữ phụ đề khi tắt phụ đề) không khác combobox bật.
5. Tab notebook: tab đang chọn thấp hơn và "chìm", tab không chọn nổi như nút — ngược affordance.
6. Kích thước tối thiểu: dòng điểm Tab 2 đè lên "Kết quả chấm" và bị cắt; hàng Micro bị cắt
   đáy; cột trái không cuộn được.
7. `tk.Text` (kết quả, nhật ký, SRT) không có thanh cuộn; không có icon cửa sổ (lông vũ Tk).
8. Dòng "Bạn đọc" tô màu **từ mẫu** cho mục `warn` (hiện "think" dù máy nghe "tink").
9. Thanh tiến trình Tab 1 đứng 100 % xanh sau khi xong; Tab 2 luôn có rãnh xám trống.
10. Ô chọn bài/thanh bên trái lần dựng đầu có thể bị sash = 0 (cột trái biến mất ~60 ms).

**Việc tiếp theo đề xuất:** sửa nhanh 1–4, 8, 9 (đều trong `_apply_theme`/`_refresh_practice`/
`_prac_done`); sau đó làm Phase 2A (bố cục 3 cột, chip lỗi, vòng lặp luyện) theo đề xuất
trong báo cáo cho người dùng.

## 2026-10-22 (tiếp 11) — Claude Opus 5.5 — Đánh giá màn hình kết quả cho người học

**Sự cố đã khắc phục:** script chụp màn hình ở (tiếp 10) gọi `_prac_done` thật → `_record_hist`
ghi mục giả `en_th` (5 lần) vào `practice_history.json`. Đã xóa đúng mục đó; file trở về
272 byte như đầu phiên (chỉ còn `vi1`, `vi2` thật). Script chụp sau này phải chặn
`App._save_hist`/`_record_hist` và `save_config`.

**Phát hiện (chưa sửa, kết luận từ ảnh chụp 6 tình huống):**
1. Vẫn hiện điểm to ("0.0%", "75.0%") khi `low_conf` — cảnh báo chỉ là dòng xám nhỏ; mâu
   thuẫn nguyên tắc "không hiện điểm khi thiếu bằng chứng".
2. Câu Whisper bịa ("cảm ơn các bạn đã theo dõi…") hiện ở dòng "Bạn đọc" màu đỏ — đổ lỗi cho
   người học. `garbage` chỉ bật khi ≥ 2× độ dài câu mẫu nên ca này không bị bắt.
3. Tag `warn` phủ cả ký tự xuống dòng → dải vàng tràn hết chiều ngang (`_prac_done`, nhánh 0 từ).
4. Lời nhắc lỗi tiếng Việt là câu máy ("nghi nhầm n/l: mục tiêu 'lan', bạn đọc 'nan'"),
   không có mẹo khẩu hình, không có nút nghe; "lắm"→"lám" không được gọi là lỗi thanh điệu
   (vì `strip_tone_vi` giữ ă).
5. Ba loại phần trăm khác nghĩa cùng màn hình (điểm từ, GOP âm, GOP mẫu).
6. Biểu đồ ngữ điệu không có nhãn từ trên trục thời gian; chú thích dùng thuật ngữ (st, DTW);
   không có kết luận bằng lời.
7. "Âm yếu nhất" cộng dồn mọi bài (cả bài Việt bị nhận nhầm là tiếng Anh: AA/OW trong `vi2`)
   → bài `vi1` hiện "/n/ (10 lần)". Lịch sử không lưu từng lần nên không vẽ được xu hướng.
8. Đọc đúng 100 % tiếng Anh: không có lời khen/"Hoàn hảo" (chỉ có cho tiếng Việt).

**Đề xuất:** thẻ kết quả mới (vòng điểm "2/4 từ", chip từ có "→ nghe ‘tink’", thẻ lỗi theo âm
có ▶ Mẫu/▶ Bạn, biểu đồ có nhãn từ + một câu kết luận, sparkline tiến bộ) — mockup đã gửi
người dùng; cần lưu từng lần luyện (`hist[sid]["tries"]`) trước khi vẽ xu hướng.

## 2026-10-22 (tiếp 12) — Claude Opus 5.5 — Kế hoạch đại tu giao diện

- Viết `docs/UI-PLAN.md`: 42 lỗi (V-/T-/P-/C-/H-/A-, 10 H · 18 M · 14 L), quy trình
  Phase 0 baseline → Phase 1 spec (GATE A) → Phase 2 design (GATE B) → Phase 3 build 5 đợt
  (B1–B5) → Phase 4 verify → Phase 5 docs; 7 câu hỏi Q-01…Q-07 cho người dùng.
- Đăng ký trong `docs/context-map.json` (docs + mục neo). `PROJECT-STATE` §1 P2 trỏ về plan.
- **Không** viết code. Bước kế: người dùng trả lời Q-01…Q-07 → chốt spec (GATE A) → làm
  token/component/mockup (GATE B) → B1.
- Cảnh báo: plan đề xuất D-27 (cổng bằng chứng hiện điểm), D-28 (`tries` trong lịch sử),
  D-29 (state model UI), D-30 (token/component) — **chưa** ghi vào DECISIONS vì chưa duyệt.

## 2026-10-22 (tiếp 13) — Claude Opus 5.5 — GATE A duyệt; Phase 2 thiết kế đã gửi

- Người dùng chọn mặc định Q-01…Q-07 và duyệt spec → ghi **D-27** trong `DECISIONS.md`,
  cập nhật trạng thái `docs/UI-PLAN.md`.
- Phase 2: canvas thiết kế (riêng tư của người dùng) https://claude.ai/artifact/L1oNuJ2Wq89LK7b8dFfRhK
  — 17 artboard: token sheet, component sheet, 6 trạng thái Tab 2, bản tối, cửa sổ tối thiểu,
  3 trạng thái Tab 1 + bản tối, Cài đặt, copy deck (28 chuỗi), header dùng chung.
  Tóm tắt lựa chọn thiết kế: `docs/UI-PLAN.md` §4.1.
- Chưa viết code. Chưa tự xem bản render của canvas (loại artifact này không cho kiểm tra
  bằng render) — người dùng xem trực tiếp.
- Bước kế: người dùng góp ý / duyệt GATE B → ghi D-28…D-30 → làm B1 (`UI-PLAN` §5).

## 2026-10-22 (tiếp 14) — Claude Opus 5.5 — Góp ý thiết kế: font và cảm giác "dashboard"

- Người dùng: font chưa hiện đại; app trông như dashboard hơn là phần mềm.
- Máy có sẵn `Segoe UI Variable Text/Display` (Windows 11); không có Inter/Be Vietnam Pro/Lexend
  → nếu chọn phải đóng gói file font (OFL) và đăng ký lúc khởi động (`AddFontResourceExW`,
  ctypes, không thêm gói pip). IPA phải kiểm tra trong Tk trước khi chốt font.
- Canvas thêm 3 artboard: `FontOptions`, `AppDirection` (thanh điều hướng trái, bỏ khung thẻ,
  câu mẫu hiển thị kết quả, panel chi tiết bên phải; tweak `font` + `theme`), `AppDirectionDark`.
- Câu hỏi chờ người dùng: Q-08 (font), Q-09 (theo hướng app-style) — ghi trong `UI-PLAN` §4.0.

## 2026-10-22 (tiếp 15) — Claude Opus 5.5 — D-28: Be Vietnam Pro + làm lại thiết kế theo "app-style"

- Người dùng chọn font B (Be Vietnam Pro) và hướng app-style cho mọi màn hình → **D-28**
  (thay vị trí Model/Ngôn ngữ của Q-04 trong D-27). Số quyết định dự kiến trong plan dời thành
  D-29 cổng bằng chứng · D-30 `tries` · D-31 state model · D-32 token/component.
- Canvas làm lại 19 artboard: `NavRail` dùng chung (bỏ `AppHeader`, `AppDirection*`),
  `PracticeResultEN` (6 state), `PracticeMin` (rail chỉ biểu tượng), `SttResult` (empty /
  youtube / processing / result) + `SttYoutube` mới, `Settings` kiểu Windows 11, token sheet,
  component sheet, copy deck 35 chuỗi. Tóm tắt bố cục: `docs/UI-PLAN.md` §4.1.
- Thay đổi hành vi mới phát sinh từ thiết kế (cần đưa vào spec/B5): Cài đặt **tự lưu khi đổi**
  (bỏ nút "Lưu cài đặt"); nút "▶ Bản thu của bạn" cạnh nút nghe mẫu.
- Chưa viết code; chưa tự xem bản render (loại artifact không cho kiểm tra render).
- Bước kế: người dùng duyệt GATE B → ghi D-29…D-32 → B1.

## 2026-10-22 (tiếp 16) — Claude Opus 5.5 — GATE B duyệt; B1 giao diện + font Be Vietnam Pro

**Quyết định mới:** D-29 (cổng bằng chứng), D-30 (`tries`), D-31 (state model), D-32 (token/thành phần).

**Font (D-28):** tải 3 file Be Vietnam Pro + `OFL.txt` từ kho chính thức google/fonts
(`ofl/bevietnampro/`, 410 KB) vào `assets/fonts/`. Đọc bảng cmap: đủ 74/74 chữ Việt nhưng chỉ
**22/43 ký tự IPA** (thiếu θ ŋ ə ɪ ʊ ʃ ˈ…) và thiếu ▶ ◀ ▾ ✓ ✕ →. Thử trong Tk: Tk mượn glyph
từng ký tự → IPA lệch cỡ/nét (xấu), ký hiệu ▶ ✓ thì ổn. ⇒ IPA dùng `FONT_IPA = "Segoe UI"` (43/43).

**Đã làm (`app.py`):** `register_ui_fonts`, `pick_ui_font`, `indicator_rows`, `logo_rows`,
`rows_to_photo`, `_raster` (hàm thuần); `App._theme_indicators` (radio/checkbox ảnh theo theme),
`App._set_icon`, `App._clear_prac_result`, `App._init_sash` (đặt ngay khi dựng), `_mk_text(scroll=)`
+ `.holder`, `lang_label` ↔ `lang`, map disabled cho combobox/entry, tab cùng baseline, mũi tên
combobox to hơn, thanh tiến trình chỉ hiện khi bận, "Sao chép", tag `ipa`, lời khen mọi ngôn ngữ,
bỏ dải màu tràn ngang (`warn`/`ok` không phủ `\n`).
**Công cụ:** `tools/ui_shots.py` (Phase 0) — 11 trạng thái → `%TEMP%\oriole_shots\<nhãn>`,
chặn ghi config/lịch sử (đã kiểm tra hash 2 file trước/sau: không đổi).

**Đã kiểm chứng:** `smoke_test` 38/38 (4 test mới), `py_compile`, `context_check`; ảnh trước/sau
11 trạng thái (sáng/tối/tối thiểu) đã xem từng ảnh.
**Chưa kiểm chứng:** Windows scaling 100/150 % (máy 250 %); thu âm thật; máy không có file font
(đường lùi Segoe UI Variable chỉ thử bằng test thuần).

**Việc tiếp theo:** B2 (`UI-PLAN` §5).
**Cảnh báo:** pack Text có thanh cuộn qua `.holder`; widget mới dùng `self.F`, chữ IPA dùng
`FONT_IPA`; đừng quay lại chỉ báo mặc định của clam.

## 2026-10-22 (tiếp 17) — Claude Opus 5.5 — B2: state model, view-model, mốc từng từ, `tries`

**Đã làm (`app.py`):**
- `build_result_view(res, lesson)` (D-31, hàm thuần) + `gop_level`; `_prac_done` = view →
  `_set_prac_state` → `_render_result_text(v)` (chỉ vẽ). Ảnh chụp 11 trạng thái trước/sau:
  phần kết quả **giống từng pixel** ⇒ renderer trung thành; B3 chỉ đổi cách trình bày.
- State model: `STT_STATES`/`PRAC_STATES`, `stt_controls`/`prac_controls` (thuần),
  `App._set_stt_state`/`_set_prac_state` — nơi duy nhất bật/tắt nút & thanh tiến trình; gán
  `busy`/`p_working`/`recording`/`rec_owner`. Bỏ `_set_busy`; `_stop_recorder` → `idle`;
  `_update_primary` dùng `_src_label` + trạng thái.
- `_w_prac` lưu `res["words_t"]` = [{w, s, e, p}].
- Lịch sử: `hist_add_try` (thêm `tries` ≤ 30, bỏ qua `unsure`), `hist_weakest(hist, lang)` chỉ
  cộng bài cùng ngôn ngữ; bài Việt đếm mã `nl`/`tone` (`VI_SOUND_CODES`). Thay đổi thấy được:
  bài Việt không còn hiện "Âm yếu nhất: /n/ (10 lần)" (số đó là mã âm vị Anh ghi nhầm ở `vi2`).
  `practice_history.json` của người dùng **không** bị sửa; `tries` chỉ xuất hiện từ lần luyện tới.

**Đã kiểm chứng:** `smoke_test` 46/46 (8 test mới), `py_compile`, `context_check`; chạy app thật
và gọi chuyển trạng thái (scoring/processing/result) → nút đúng; ảnh trước/sau + so pixel.
**Chưa kiểm chứng:** thu âm thật qua các trạng thái mới (cần mic); YouTube thật.

**Việc tiếp theo:** B3 (`UI-PLAN` §5).
**Cảnh báo:** không gán `busy`/`p_working`/`recording`/`rec_owner` hay bật/tắt nút ngoài
`_set_*_state`; sửa nội dung kết quả trong `build_result_view`, không trong renderer.

## 2026-10-22 (tiếp 18) — Claude Opus 5.5 — B3 ĐANG DỞ (dừng vì hết hạn mức sử dụng)

**Đã làm (`app.py`, chưa kiểm tra bằng ảnh):**
- Trạng thái `rhyme` ("lắm"→"lám", `strip_marks_vi`), lời nhắc mới (`flag_pair`, tone, "Thiếu từ").
- Cổng bằng chứng D-29: `evidence_gate` + `HALLUCINATION_PHRASES`; view `state="unsure"`.
- `build_result_view` B3: `cards` (EN GOP/âm vị, VI gom N/L + thanh + vần với `vi_spell`),
  `ring`, `headline`, `summary`, `tips`, `heard_text`; `score_line` = "c/t từ".
- UI: `p_head` (vòng điểm `_draw_ring` + `p_headline` + `p_summary`), `_render_result`
  (chip `_mk_chip`, thẻ `_mk_card`, "Chi tiết số đo" `_toggle_details`, panel "chưa nghe rõ"
  + `_toggle_heard`), ▶ Bạn đọc qua `play_wav_segment`/`words_t`; token THEMES mới.
- `smoke_test` 46/46 (3 test B2 sửa theo khóa mới); app mở được.

**Chưa làm:** test mới cho `evidence_gate`, `rhyme`, `vi_spell`, `has_ipa`,
`wav_segment_bounds`; chạy `tools/ui_shots.py b3_after` + so với `b3_before` (đã chụp);
cập nhật skill/UI-PLAN §5.3/PROJECT-STATE/context-map (symbol mới); `context_check`.
**Rủi ro cần xem khi chụp:** độ rộng thẻ khi Text chưa có kích thước; màu chip ở theme tối.
