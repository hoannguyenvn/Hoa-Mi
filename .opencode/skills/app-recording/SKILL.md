---
name: App Recording & Microphone
description: Sửa thu âm, chọn micro, tự dò micro có tín hiệu, tự dừng khi im lặng, chuẩn hóa âm lượng và ghi WAV 16 kHz trong Oriole. Dùng khi người dùng nhắc tới micro, thu âm, sounddevice, tín hiệu yếu, WDM-KS, hoặc chất lượng bản ghi.
---

# Recording & Microphone

Phạm vi: `Recorder`, chọn/kiểm tra micro, `save_frames_wav`, `enhance_audio`,
`resample_to_16k`, phát lại.

## Đọc trước

- `docs/ARCHITECTURE.md` §7–8.
- Bất biến I3, I10, I15.

## Symbol (app.py)

| Nhóm | Symbol |
|---|---|
| Thu | `Recorder.start`, `Recorder.stop`, `Recorder.level_bar` |
| Thiết bị | `list_input_mics`, `list_usable_mics`, `rescan_audio_devices`, `headset_mic_missing`, `pick_default_mic`, `query_mic_rate` |
| Dò tín hiệu | `probe_input_levels`, `best_input_mic` |
| Xử lý | `resample_to_16k`, `enhance_audio`, `save_frames_wav`, `wav_peak` |
| Phát | `play_wav_file`, `App._stop_play` |
| UI | `App._refresh_mics`, `App._on_tab_changed`, `App._open_sound_settings`, `App._resolve_mic`, `App._test_mic`, `App._find_mic_auto` |
| Hằng số | `REC_RATE=16000`, `REC_MAX_SEC=180`, `REC_LONG_SEC=900`, `REC_TARGET_PEAK=0.70`, `REC_GAIN_MAX=16.0`, `MIC_MIN_PEAK=0.008`, `MIC_GOOD_PEAK=0.03` |

Phân biệt giới hạn:
- Tab chuyển văn bản: `REC_LONG_SEC = 900` (15 phút).
- Tab luyện phát âm: `REC_MAX_SEC = 180` (3 phút, dư sức cho 1–2 câu).

## Vòng lặp thu — hành vi chính xác

`Recorder.start(device, rate, max_sec, on_autostop, on_error, auto_stop)`:

- **Callback mode + queue** (D-23): `sd.InputStream(callback=...)` đẩy block 100 ms vào
  `queue.Queue`; luồng xử lý lấy block, tính RMS. **Không** dùng `stream.read` —
  DirectSound trên máy này trả 100 % số 0 ở chế độ blocking.
- `stop()` đặt `active=False`, chờ 150 ms, **drain queue** rồi trả `(frames, rate)`.
- Đọc block **100 ms** (`step = rate * 0.1`), mono `int16`.
- 0,5 giây đầu: đo **nhiễu nền** bằng median RMS, chưa xét giọng.
- Trước khi thấy giọng: ngưỡng `max(0.004, min(0.024, noise*2.2))`.
- Sau khi thấy giọng: ngưỡng thấp hơn `max(0.0025, min(0.022, noise*1.2))`
  (hysteresis) để người nói nhỏ không bị cắt giữa chừng.
  Sàn thấp vì micro array laptop chỉ cho RMS ~0,5% khi nói bình thường (D-21).
- `speech_seen = True` khi vượt ngưỡng; `voice_t` cập nhật mỗi block còn tiếng.
- Tự dừng:
  - `"nospeech"`: chưa thấy giọng và quá `start_timeout = 7 s`.
  - `"silence"`: đã thấy giọng, im lặng > `silence = 1.3 s`, và đã thu > `min_speech = 0.4 s`.
  - `"max"`: chạm `max_sec`.
- Lỗi `"Blocking API not supported"` → thông điệp WDM-KS thân thiện, không crash.

Frames có thể rỗng nếu stream không mở được (khi đó `on_error` đã được gọi) — caller
phải kiểm tra rỗng trước khi concat.

## Chuẩn hóa — `enhance_audio(samples_i16, rate)`

Thứ tự bắt buộc:
1. int16 → float, đo `peak0`, phát hiện `clipped` (≥ 0,99).
2. Trừ DC.
3. High-pass 1 cực ~75 Hz (IIR), **không** FFT brick-wall (gây "rè kim loại").
4. Gain về `0.70` (-3 dB); nếu đầu vào đã vỡ thì chỉ giảm, không tăng;
   tối đa `REC_GAIN_MAX = 16.0` (+24 dB) để micro yếu vẫn nghe được.
5. `tanh` + clip.
6. Cắt im lặng đầu/cuối, ngưỡng `max(0.015, 0.04 * peak1)`, giữ 80 ms đệm.
7. Fade 8 ms hai đầu.
8. Trả `(int16, {peak0, peak1, quiet, clipped, trimmed})`.

`save_frames_wav`:
```
frames → concat int16 → /32768 → resample_to_16k → enhance_audio
→ tempfile.mkstemp(prefix, ".wav") → WAV mono 16-bit
→ (path, seconds, info)
```
File tạm do `tempfile` tạo; caller chịu trách nhiệm xóa.

Ai xóa file nào (I10):
- Tab 1 (`_rec_stop_and_transcribe`): `stt_*.wav` thuộc về `_w_file(delete_after=True)`,
  xóa trong `finally` (xong/hủy/lỗi); bản thu `< 0,4 s` bị `remove_temp` ngay. Tab 1
  **không** gán `last_wav`.
- Tab 2 (`_prac_stop_and_score`): `luyen_*.wav` gán qua `App._set_last_wav` — xóa bản cũ
  khi có bản mới, khi Chấm file…, và khi đóng app.
- Xóa bằng `remove_temp(path)`: bỏ qua file đã mất; trả `False` nếu file đang bị khóa.

Recorder dùng chung hai tab: bắt đầu thu bằng `_set_stt_state("recording")` hoặc
`_set_prac_state("recording")` (đặt `recording`/`rec_owner`), dừng bằng
`App._stop_recorder()` (tab đang thu về `idle`) — xem `app-ui` §8, §10 (D-26, D-31).

## Cổng chất lượng (không được hạ)

| Điều kiện | Hành vi |
|---|---|
| `frames` rỗng | "Chưa thu được gì — thử lại." |
| `peak0 < MIC_MIN_PEAK` (0.008) | **không chấm**, báo gần như im lặng, tự dò mic |
| `secs < 0.5` (luyện) / `< 0.4` (tab 1) | không chấm/chuyển |
| `reason == "nospeech"` | không chấm, mở hướng dẫn mic |
| `info["clipped"]` | cảnh báo "đầu vào bị VỠ", đề nghị lùi mic/giảm volume |
| `info["peak0"] < 0.03` | cảnh báo "hơi NHỎ", đề nghị gần mic hơn |

`peak1` luôn ~0,70 sau chuẩn hóa → **không dùng `peak1` để đánh giá mic**;
`quality_note` và gate dùng `peak0`.

## Micro

- `list_input_mics()` trả **tất cả** thiết bị thu (kể cả WDM-KS) — dùng cho chẩn đoán.
- `list_usable_mics()` lọc bỏ WDM-KS vì PortAudio không hỗ trợ blocking read
  (`Blocking API not supported`) → `Recorder` không bao giờ thu được. Ô chọn micro
  của UI (`_refresh_mics`) dùng hàm này. Máy chỉ có WDM-KS → trả danh sách gốc để
  không bỏ trắng ô chọn.
- Nếu `config.json` lưu mic WDM-KS, sau khi lọc tên sẽ không khớp → app tự chọn
  mặc định tốt hơn (`pick_default_mic`). Đây là đường sửa tự động cho lỗi
  "mic im lặng" do WDM-KS.
- `pick_default_mic()` chấm điểm: micro thật +2; **DirectSound +2 > WASAPI +1 > MME 0**
  (WASAPI có thể làm tín hiệu mic array nhỏ đi — xem `D-20`); thiết bị alias
  ("Sound Mapper", "Primary Sound Capture") -3; loopback -10; WDM-KS -1.

### Mic ngoài (USB / tai nghe bluetooth)

- PortAudio chỉ liệt kê thiết bị **một lần** lúc khởi tạo → mic cắm sau khi mở app
  không tự hiện. `rescan_audio_devices()` gọi `sd._terminate()/_initialize()`; ô Micro
  làm việc này khi bấm **Quét lại** và khi mở tab **Cài đặt** (chỉ khi đang rảnh).
- Nút **Âm thanh Windows** → `os.startfile("ms-settings:sound")`.
- `headset_mic_missing()` trả tên tai nghe bluetooth **chỉ có chiều nghe** → UI hiện
  gợi ý bật Hands-Free (Sound → Recording → Show Disabled Devices, hoặc Devices and
  Printers → Properties → Services). AirPods/headset bluetooth **không** thu được gì
  nếu Windows chưa mở HFP; app không thể tự bật (D-22).
- `query_mic_rate()`: thu ở rate gốc rồi resample mềm; **không** ép 16k trong
  `InputStream` (PortAudio resample thô, dễ rè).
- `probe_input_levels(dur=0.5)`:
  - bỏ loopback/"sound mapper",
  - **bỏ WDM-KS** (blocking read không hỗ trợ),
  - thu thử, xếp giảm dần theo đỉnh.
- `_find_mic_auto()` chạy nền, chọn mic có đỉnh cao nhất; có timeout 20 s để
  không kẹt cờ `_mic_probing`.
- Nếu mic lưu trong config không còn, `_refresh_mics` chọn mặc định.

## Khi sửa

- Đổi ngưỡng auto-stop: phải thử cả 3 kịch bản — nói đều, nói nhỏ, im lặng.
  Ghi lý do vào `DECISIONS.md` nếu đổi số.
- Thêm hiệu ứng âm thanh: giữ hàm thuần, trả `(int16, info)`, cập nhật test.
- Đừng bỏ `noise` calibration: đây là thứ giúp máy có quạt/điều hòa vẫn dùng được.
- Đừng chấm điểm khi `peak0` thấp, kể cả khi người dùng bấm "Dừng & chấm".
- Không phát âm thanh trên main thread (`play_wav_file` blocking).

## Kiểm chứng

```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\smoke_test.py
```

Thủ công:
1. Tab 1 → Ghi âm: nói 3 s rồi im → tự dừng, ra text.
2. Tab 2 → Thu âm & chấm: nói 2 s → tự dừng sau ~1,3 s.
3. Bịt mic / mute → sau 7 s báo "không nghe thấy giọng", mở hướng dẫn, không chấm.
4. Nói quá nhỏ (đỉnh < 0,8%) → không chấm, tự dò mic khác.
5. Nói quá to/gần → cảnh báo VỠ nhưng vẫn xử lý.
6. Kiểm tra mic trong Cài đặt → hiện đỉnh %, dB, RMS + TỐT/NHỎ/IM LẶNG/TO.
7. Đổi sample rate Windows (44,1 ↔ 48 kHz) → vẫn ra WAV 16k.
8. Ô Micro **không** liệt kê thiết bị `[Windows WDM-KS]` (trừ khi máy chỉ có loại đó).
9. Config cũ lưu mic WDM-KS → mở app, ô Micro tự chọn bản DirectSound/WASAPI cùng tên.
10. Kết nối tai nghe bluetooth/USB **sau** khi mở app → bấm **Quét lại** (hoặc mở tab
    Cài đặt) là thấy thiết bị mới.
11. Tai nghe bluetooth chưa bật Hands-Free → ô Micro hiện gợi ý bật profile, app
    **không** liệt kê được micro (đúng: Windows không cấp thiết bị).

## Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| `Blocking API not supported` | chọn WDM-KS — đã bị `list_usable_mics` lọc khỏi ô chọn |
| Mic thu ra **toàn số 0** (DirectSound) | dùng `stream.read` blocking — phải dùng callback + queue (D-23) |
| `WdmSyncIoctl … prop_id = 10` khi mở WASAPI | thiết bị đang bận / stream cũ chưa đóng — báo "đóng app khác, Quét lại" |
| Tự dừng ngay khi mới nói | `silence` quá nhỏ hoặc `min_speech` sai |
| Không bao giờ tự dừng | `speech_seen` không bật do ngưỡng quá cao |
| Tiếng rè kim loại | dùng FFT brick-wall thay vì high-pass 1 cực |
| Điểm mic "tốt" nhưng file im lặng | đọc `peak1` thay vì `peak0` |
| UI đứng khi phát mẫu | gọi `sd.play/wait` trên main thread |
| Thu 16k bị méo | ép InputStream 16k thay vì thu rate gốc + resample |
| Ghi âm 15 phút xong phải chờ lâu mới ra text | high-pass trong `enhance_audio` là vòng lặp Python từng mẫu (~14 triệu vòng cho 15 phút), chạy trên main thread |
| `%TEMP%` đầy `luyen_*.wav` | gán `self.last_wav` trực tiếp thay vì `_set_last_wav` |
