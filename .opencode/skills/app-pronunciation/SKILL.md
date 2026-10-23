---
name: App Pronunciation Scoring (L1)
description: Sửa cách chấm phát âm theo từ, luật lỗi n/l, th, s/sh, âm cuối, thanh điệu tiếng Việt, cổng tin cậy và màn hình kết quả trong Oriole. Dùng khi người dùng nhắc tới điểm phát âm, từ đúng/sai, lỗi thanh điệu, "máy nghe thành gì", hoặc Tab 2.
---

# Pronunciation Scoring — L1

Đây là lớp **đúng/sai nội dung**: so câu mẫu với câu ASR nghe được. Nó là nguồn
duy nhất của `score`. Âm vị (`app-phonemes`) và ngữ điệu (`app-prosody`) chỉ bổ sung,
không đổi điểm.

## Đọc trước

- `docs/ARCHITECTURE.md` §6.
- Bất biến I2, I3, I4.
- Các cách làm bị loại R-01…R-08 trong `docs/DECISIONS.md`.

## Symbol (app.py, phần lớn là hàm thuần)

| Nhóm | Symbol |
|---|---|
| Chuẩn hóa | `norm_words`, `strip_tone_vi`, `_rest_sim`, `_TONE_MARKS` |
| Luật | `flag_pair`, `score_pronunciation` |
| Worker | `App._w_prac` |
| Hiển thị | `App._prac_done`, `App._prac_error`, `App._prac_stop_and_score` |
| View (D-31) | `build_result_view`, `gop_level`, `App._render_result_text` |
| Lịch sử | `App._load_hist`, `App._save_hist`, `App._record_hist`, `App._update_prog`, `hist_add_try`, `hist_weakest` |

Module liên quan: `pron_en.analyze_pairs` (chỉ tiếng Anh), `gop.score`,
`prosody.compare`.

## Công thức và trạng thái

```
score = round(100 * correct / total, 1)
```

- `correct` = số item trạng thái `ok`.
- `total` = số từ trong **câu mẫu**.
- `warns` (nghi lỗi quen thuộc) và `tones` (sai thanh điệu) **không trừ điểm**.
- Từ **thừa** không làm giảm điểm, chỉ hiện cảnh báo (tối đa 3 từ + tổng).
- Câu mẫu rỗng → `score = 0.0`, `total = 0`.

### Trạng thái item

| State | Nghĩa | UI |
|---|---|---|
| `ok` | từ khớp | xanh (`ok`) |
| `warn` | khớp luật lỗi quen thuộc (`flag_pair`) | cam (`warn`) |
| `tone` | bỏ dấu thì giống → sai thanh điệu | cam (`warn`) |
| `bad` | sai/thiếu từ | đỏ (`bad`) |
| `extra` | từ người học đọc thêm | ghi chú `[thừa: …]` |

### Cách căn

1. **Lượt theo vị trí đọc:** với từ thứ `i` của mục tiêu và từ thứ `i` của hyp,
   gọi `flag_pair`. Lưu gợi ý vào `pos_flag` — dùng khi SequenceMatcher xếp cặp khác.
2. `difflib.SequenceMatcher` trên danh sách từ.
3. Gộp cặp `delete` + `insert` kề nhau thành `replace`: "thiếu A + thừa B" thực chất
   là "đọc A thành B" (ví dụ `nam` → `lam`).
4. Với mỗi cặp `(target, heard)`:
   - `flag_pair` → `warn` + gợi ý;
   - tiếng Việt/auto và `strip_tone_vi(t) == strip_tone_vi(h)` → `tone`;
   - có `pos_flag[i]` → `warn`;
   - còn lại → `bad`.
5. Target không có hyp tương ứng → `bad` + "thiếu chữ".
6. Hyp không có target → `extra`.

`strip_tone_vi` bỏ **dấu thanh** nhưng giữ dấu chữ (ă/â/ê/ô/ơ/ư), trả chuỗi NFD —
khi so với chuỗi khác hãy chuẩn hóa NFC trước nếu cần hiển thị.

## Luật `flag_pair` (giữ nguyên hoặc mở rộng có test)

Tiếng Việt/auto:
- `n/l` đầu từ, phần còn lại giống ≥ 0,5 (`_rest_sim`) → `nl`.

Tiếng Anh/auto:
- `th` → `t/d/s/z` (không phải `th`) → `th`.
- `sh ↔ s` đầu từ → `sh`.
- Mất phụ âm cuối `t/d/k/p/g/b/s` (`cat` → `ca`) → `final`.
- Mất cụm `-te/-de/-ke…` (`cats` → `cat` xử lý riêng bằng nhánh trên).

Muốn thêm cặp: thêm nhánh + case trong `tools/smoke_test.py`. Không thêm luật
dựa trên ngưỡng toàn cục.

## Cổng tin cậy trong `_w_prac`

```
wav_peak < MIC_MIN_PEAK (0.008) → prac_error, không chấm
                       (file không phải WAV → wav_peak trả 1.0, gate bị bỏ qua)
không có hyp           → prac_error "Không nghe được chữ nào"
conf = mean(word.probability)
low_conf = conf < 0.35 → ghi chú "máy nghe chưa chắc"
garbage = hyp_words >= 8 và >= 2 * target_words và score < 35
        → cảnh báo mic nhiễu, không tin kết quả
```

ASR cho luyện phát âm dùng:
```python
model.transcribe(wav_path,
    language=None if lang == "auto" else lang,
    beam_size=5, word_timestamps=True,
    vad_filter=True, condition_on_previous_text=False)
```
`condition_on_previous_text=False` + VAD là biện pháp chống Whisper "bịa" — không bỏ.

## View-model (D-31) — sửa NỘI DUNG ở đây, không ở UI

`_prac_done` = `build_result_view(res, lesson)` → `_set_prac_state(v["state"])` →
`_render_result_text(v)`. Mọi quyết định (khen hoàn hảo, ghi chú nào ẩn vì đã có lỗi âm vị,
cặp "Chưa khớp", mức GOP, câu tóm tắt, dòng điểm, đếm âm cho lịch sử) nằm trong
`build_result_view` và có test (`result_view_*`). Renderer chỉ chèn text/tag.
Lịch sử: `hist_add_try(hist, sid, view, ts)` thêm `tries` (≤ 30), bỏ qua view `unsure`;
`hist_weakest(hist, lang)` chỉ cộng bài cùng ngôn ngữ (bài Việt: mã `nl`, `tone`).
`_w_prac` lưu `res["words_t"]` (mốc từng từ) cho biểu đồ ngữ điệu.

## Hiển thị `_prac_done`

Dòng điểm:
```
86.5%  (13/15 từ)  ·  2 chỗ cần sửa  ·  1 lỗi thanh điệu  ·  3 lỗi âm vị
```
- "Hoàn hảo — đúng cả N từ." hiện ngay dưới dòng "Bạn đọc" cho **mọi ngôn ngữ** khi
  `score >= 95`, không từ thừa, không ghi chú cần sửa, không lỗi âm vị, không warns/tones
  (biến `perfect` trong `_prac_done`).
- Nhãn và mẹo âm vị chèn với tag `"ipa"` (Segoe UI) — font giao diện thiếu ký tự IPA (D-28).
- Đổi bài/chế độ gọi `_clear_prac_result()` (trừ khi đang chấm) — không để kết quả cũ.
- Không hiện "0% · 11 lỗi âm vị" nhưng vẫn "Hoàn hảo" (lỗi cũ đã sửa).
- Với tiếng Anh, ghi chú cấp từ bị ẩn nếu đã có lỗi âm vị chi tiết (tránh trùng).
- Giới hạn 5 lỗi âm vị hiển thị; phần còn lại ghi "… và N âm khác".
- Dòng "Bạn đọc": item `bad` in **từ máy nghe được** (`hw`), hoặc `∅` khi thiếu —
  không in từ mẫu (trước đây in từ mẫu nên 0% trông như đọc đúng).
- Không phải tiếng Anh và `correct > 0`: thêm mục "Chưa khớp (mẫu → máy nghe)",
  tối đa 6 cặp.
- `correct == 0` + `garbage`: giải thích mic ồn/tai nghe chưa đeo đúng, gợi ý model `small`.

## Lịch sử

`practice_history.json`:
```json
{
  "en_th": {"n": 3, "best": 92.0, "last": 80.0,
            "ts": "2026-10-22 10:00", "ph": {"TH": 2, "DH": 1}}
}
```
- Chỉ ghi khi `sid` tồn tại và khác `custom` (guide không có id).
- `ph` lấy từ `gop.issues[].ph`, nếu không có GOP thì từ `phon.counts`.
- Ghi nguyên tử `.tmp` + `os.replace`.
- "Âm yếu nhất" = âm có tổng đếm lớn nhất trong các bài **cùng ngôn ngữ** (D-30).

## Khi sửa — checklist

1. Sửa `score_pronunciation` (hàm thuần) trước, không sửa UI trước.
2. Thêm case vào `tools/smoke_test.py`: đúng hoàn toàn, 1 lỗi, thiếu từ, thừa từ,
   sai thanh điệu, câu rỗng.
3. Nếu đổi khóa trả về, cập nhật `_w_prac`, `_prac_done`, `_record_hist`,
   `docs/ARCHITECTURE.md` §3.3.
4. Nếu đổi công thức điểm, ghi `D-xx` + lý do; mặc định **không** trừ điểm warns.
5. Chạy `context_check.py` (symbol) + `smoke_test.py`.

## Tiêu chí nghiệm thu

- Đọc đúng câu 10/10 lần → `score >= 90`, `warns = 0`.
- "think" → "tink": phát hiện đúng từ, gợi ý âm th, 9/10 lần.
- "năm" → "lăm": `warn` n/l.
- "má" → "ma": `tone`, không phải `bad`.
- Im lặng: **không** có điểm.
- 20 lần thử liên tiếp: không crash, không rò rỉ WAV tạm.

## File tạm & generator

- `luyen_*.wav` là bản Nghe lại duy nhất: luôn gán qua `App._set_last_wav(path)` — hàm
  này xóa bản cũ. `_prac_from_file` và `_on_close` gọi `_set_last_wav(None)`. Đừng gán
  `self.last_wav = ...` trực tiếp (rò rỉ, I10). Test: `practice_replay_wav_is_replaced_not_leaked`.
- `segs` của `model.transcribe` là **generator**, chỉ duyệt một lần: `_w_prac` gom text
  dự phòng (`texts`) ngay trong vòng lặp lấy `words`. Test: `practice_hyp_falls_back_to_segment_text`.

## Nợ đã biết (chưa sửa)

- `load_model()` tạo `WhisperModel` mới **mỗi lần chấm** → mỗi câu tốn thêm vài giây.
- 3 bài Việt (`vi1`–`vi3`) không có audio mẫu → không có nút nghe, không có ngữ điệu.

## Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| Điểm 100% nhưng đầy cảnh báo | đúng thiết kế (I4); đừng "sửa" bằng cách trừ điểm |
| Báo sai thanh điệu khi phụ âm cũng sai | thứ tự kiểm tra: `flag_pair` trước, `tone` sau |
| Cặp từ bị lệch vị trí | bỏ bước gộp delete+insert |
| Whisper nghe ra câu lặp | thiếu VAD/`condition_on_previous_text=False` |
| Điểm cao trên im lặng | thiếu gate `peak0`/`wav_peak` |
| Lịch sử ghi cả `custom` | quên kiểm tra `sid` |
| "Hoàn hảo" khi có từ thừa | điều kiện phải gồm `extra_total == 0` |
