---
name: App Prosody & Intonation Chart
description: Sửa phần ngữ điệu trong Oriole — tách F0 bằng autocorrelation, quy đổi bán cung so với trung vị người nói, DTW, và biểu đồ Canvas ở Tab 2. Dùng khi người dùng nhắc tới ngữ điệu, cao độ, F0, contour, lên/xuống giọng, biểu đồ cao độ, hoặc prosody.py.
---

# Prosody & Intonation

Nguyên tắc duy nhất: **chỉ hiển thị cái đo được**. Không có "điểm ngữ điệu",
không xếp hạng giọng, không so Hz tuyệt đối giữa hai người.

Đọc trước: `docs/DECISIONS.md` D-10, D-11; bất biến I5, I8;
`docs/ARCHITECTURE.md` §3.3 (`inton`) và §8.

## 1. Đường ống

```
WAV ──read_wav──► mono 16 kHz float32
                  │
                  ├─ f0_track: khung 40 ms, bước 10 ms, 60–420 Hz
                  │            → (times, f0) với NaN ở khung câm/vô thanh
                  ├─ contour: lọc sạch + 12*log2(f0 / median)  → bán cung
                  └─ compare: lưới 101 điểm + DTW dải 15  → dict cho UI
```

Không dùng librosa, Praat, torchaudio. Chỉ `wave` + `numpy` (I8).

## 2. Hợp đồng hàm (`prosody.py`)

| Symbol | Vào | Ra |
|---|---|---|
| `read_wav(path)` | WAV PCM 8/16/24/32-bit | `(float32 mono [-1..1], 16000)` |
| `f0_track(x, sr, fmin=60, fmax=420, frame_ms=40, hop_ms=10)` | mảng mẫu | `(times, f0)`; `f0` có `NaN` |
| `contour(path)` | đường dẫn | `{t, st, dur, median, voiced}` hoặc `None` |
| `contour_cached(path)` | đường dẫn | như `contour`, cache 40 mục theo mtime+size |
| `compare(ref_path, usr_path)` | 2 WAV | dict hiển thị hoặc `None` |

### `read_wav`

- 1/2/3/4 byte mẫu → scale đúng (`/128`, `/32768`, `/8388608`, `/2147483648`).
- Nhiều kênh → trung bình cộng.
- Khác 16 kHz → nội suy tuyến tính (`np.interp`). Đủ tốt cho F0, **không** dùng
  để chấm âm vị (GOP đọc lại bằng cùng hàm này nhưng cần đúng mẫu).
- Định dạng lạ → `ValueError("định dạng WAV không hỗ trợ")`.

### `f0_track` — các ngưỡng không được tùy tiện đổi

- Cửa sổ Hanning, autocorrelation qua FFT, tìm đỉnh trong `[sr/fmax, sr/fmin]`.
- Đỉnh chuẩn hóa `< 0.32` → coi là vô thanh (`NaN`).
- Nội suy parabol quanh đỉnh để mịn.
- Ngưỡng năng lượng: `max(0.004, 0.10 * percentile(rms, 95))`.
- `_clean`: trung vị 5 khung, sửa nhảy quãng tám (`> 1.8×` → chia 2,
  `< 0.55×` → nhân 2).
- `times` là tâm khung: `(i*hop + frame/2) / sr`.

Đổi `frame_ms`/`hop_ms` làm lệch cả `contour` và test `f0_track_sine`.

### `contour`

- `< 6` khung hữu thanh → `None` (không đủ bằng chứng).
- `st = 12 * log2(f0 / median(f0 hữu thanh))`; khung vô thanh giữ `None`.
- `t` chuẩn hóa 0..1 theo `times[-1]`; `dur` = độ dài thật (giây).
- `median` (Hz) chỉ để ghi chú, **không** dùng để so hai người (I5).

### `compare`

- Mẫu dùng `contour_cached` (bản mẫu lặp lại nhiều lần); bản người đọc luôn tính mới.
- `_grid`: nội suy 101 điểm trên `t ∈ [0,1]`, cần ≥ 8 điểm hữu thanh.
- `_dtw`: dải Sakoe–Chiba `band=15`, chi phí `|a-b|`, chia `max(n,m)`.
- `_final_slope`: hồi quy tuyến tính 30% cuối, chia 10 → **bán cung / 10% độ dài**.
- `_range`: `max(st) - min(st)` nếu ≥ 4 điểm.

Trả về:

```python
{"ref": {"t": [...], "st": [...]}, "usr": {...},
 "dur_ref": 2.31, "dur_usr": 2.05,
 "med_ref": 182.4, "med_usr": 201.0,
 "range_ref": 5.2, "range_usr": 3.8,
 "final_ref": -0.42, "final_usr": -0.18,
 "diff": 1.37, "voiced_ref": 0.61, "voiced_usr": 0.55}
```

`final_*` âm = xuống giọng; `diff` = độ lệch DTW trung bình (bán cung), **chỉ tham khảo**.
Bất kỳ lỗi/thiếu dữ liệu → `None`; UI ẩn thẻ.

## 3. Nối vào app

- `_w_prac` chỉ gọi khi có `ref_wav`:
  ```python
  res["inton"] = prosody.compare(ref_wav, wav_path) if ref_wav else None
  ```
- `ref_wav` lấy từ `PRACTICE_SETS[sid]["samples"][0][1]` — tức **câu đầy đủ**, không
  phải clip từ khóa, và không có cho `custom`.
- Hệ quả: **Học âm** (guide, `sid=None`) và 3 bài Việt `vi1`–`vi3` (không có
  `samples`) **không bao giờ** có biểu đồ — chỉ 14 bài tiếng Anh có.
- `_prac_done` gọi `_show_intonation(res.get("inton"))`.
- `_show_intonation(d)`: lưu `self._inton` rồi vẽ lại panel; mục NGỮ ĐIỆU chỉ hiện khi kết
  quả là `result` (không khi `unsure`). Canvas `p_int` cao 110 px trong panel phải (B4a);
  nhãn từ, trọng âm, tốc độ là B4b (UI-PLAN S-5/S-5b, D-34).
- `_inton_text`: 2–4 câu tiếng Việt (thời lượng, cuối câu, khoảng cao độ, độ lệch).
- `_draw_intonation`:
  - trục dọc giới hạn `lim = max(6, min(18, ceil(max|st|/3)*3))`;
  - nét đứt = mẫu (`P["muted"]`), nét liền = người đọc (`P["accent"]`);
  - ngắt nét khi gặp `None` (không nối qua khoảng lặng);
  - lưới ngang mỗi 3 hoặc 6 bán cung, dọc 0/25/50/75/100%.
- Đổi theme → `_apply_theme` gọi `_draw_intonation()` lại.
- Đổi bài → `_refresh_practice` đặt `_inton = None` và ẩn thẻ.

**Không** đưa `diff` vào `score`, không tô đỏ theo ngưỡng, không xếp hạng.

## 4. Khi sửa — checklist

1. Sửa `prosody.py` trước; UI chỉ đọc khóa, không tự tính.
2. Test tối thiểu trong `tools/smoke_test.py`:
   - sine 150 Hz → trung vị F0 trong `[135, 165]`;
   - `contour` trên file toàn số 0 → `None`;
   - `compare` với file thiếu → `None` (không ném lỗi);
   - `final_*` của sine phẳng ≈ 0.
3. Không thêm dependency nặng (I8).
4. Không so Hz tuyệt đối giữa mẫu và người đọc (I5).
5. Nếu đổi khóa `inton`, cập nhật `_inton_text`, `_draw_intonation`,
   `docs/ARCHITECTURE.md` §3.3.
6. Chạy `py_compile`, `smoke_test.py`, `context_check.py`.

## 5. Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| Đồ thị toàn đường thẳng đứng | nối điểm qua `None` thay vì ngắt nét |
| Hai người khác giọng bị báo lệch nặng | so Hz thay vì bán cung so trung vị |
| Không hiện biểu đồ | `ref_wav` rỗng, `custom`, hoặc `samples[0]` không tồn tại |
| Biểu đồ hiện rồi mất khi resize | `_draw_intonation` trả sớm vì `W/H` chưa đủ; cần `after(60, …)` |
| F0 của giọng nam cao bất thường | `fmin=60` quá thấp gặp rung cửa sổ; kiểm tra `_clean` |
| Đường cong nhảy quãng tám | `_clean` bị bỏ hoặc ngưỡng 1.8/0.55 bị đổi |
| Test sine fail sau khi đổi hop | `times`/`frame` lệch, hoặc ngưỡng peak 0.32 quá cao |
| Thẻ ngữ điệu còn hiện sau khi đổi bài | `_refresh_practice` không gọi `pack_forget` |
