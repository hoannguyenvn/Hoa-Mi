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
| Chuẩn hóa | `norm_words`, `strip_tone_vi`, `strip_marks_vi`, `_rest_sim`, `_TONE_MARKS`, `vi_spell` |
| Luật | `flag_pair`, `score_pronunciation` |
| Worker | `App._w_prac` |
| Hiển thị | `App._prac_done`, `App._prac_error`, `App._prac_stop_and_score` |
| Cổng bằng chứng (D-29) | `evidence_gate`, `HALLUCINATION_PHRASES`, `UNSURE_RATIO`, `GARBAGE_RATIO`, `GARBAGE_SCORE`, `UNSURE_TIPS` |
| View (D-31) | `build_result_view`, `gop_level`, `_vi_cards`, `App._render_result` |
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
- `rhymes` (sai vần/dấu, B3) là từ **sai** (không tính `correct`), chỉ được đặt tên rõ.
- Từ **thừa** không làm giảm điểm, chỉ hiện cảnh báo (tối đa 3 từ + tổng).
- Câu mẫu rỗng → `score = 0.0`, `total = 0`.

### Trạng thái item

| State | Nghĩa | UI |
|---|---|---|
| `ok` | từ khớp | xanh (`ok`) |
| `warn` | khớp luật lỗi quen thuộc (`flag_pair`) | cam (`warn`) |
| `tone` | bỏ dấu thì giống → sai thanh điệu | cam (`warn`) |
| `rhyme` | bỏ **mọi** dấu (`strip_marks_vi`) thì giống: "lắm"→"lám" | đỏ (`bad`) |
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
   - tiếng Việt/auto và `strip_marks_vi(t) == strip_marks_vi(h)` → `rhyme`;
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
        → cờ cũ, vẫn lưu trong res
```

Sau đó `build_result_view` gọi `evidence_gate(res)` (D-29) → view `state="unsure"` khi:
1. hyp chứa nguyên cụm trong `HALLUCINATION_PHRASES` mà câu mẫu không có (khớp **nguyên
   từ**: "subscribe" ≠ "subscribers") → `"hallucination"`;
2. số từ nghe ≥ `GARBAGE_RATIO` (1,6) × số từ mẫu và `score < GARBAGE_SCORE` (35) → `"garbage"`;
3. `low_conf` và đúng < `UNSURE_RATIO` (50 %) → `"low_conf"`.
`unsure` ⇒ không số, không chip màu, không đếm âm, `hist_add_try` bỏ qua. Thêm cụm mới
vào `HALLUCINATION_PHRASES` kèm case trong `evidence_gate_blocks_hallucination_and_noise`.

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
`_render_result(v)`. Mọi quyết định (cổng bằng chứng, khen hoàn hảo, thẻ "Cần sửa", ghi chú
nào ẩn vì đã có thẻ, mức GOP, câu tóm tắt, vòng điểm, đếm âm cho lịch sử) nằm trong
`build_result_view` và có test. Renderer chỉ vẽ (B4 sẽ thay bố cục, giữ nguyên view).
Lịch sử: `hist_add_try(hist, sid, view, ts)` thêm `tries` (≤ 30), bỏ qua view `unsure`;
`hist_weakest(hist, lang)` chỉ cộng bài cùng ngôn ngữ (bài Việt: mã `nl`, `tone`, `rhyme`).
`_w_prac` lưu `res["words_t"]` (mốc từng từ) cho biểu đồ ngữ điệu.

## Hiển thị `_render_result` (B3)

- Đầu kết quả `p_head`: vòng điểm `_draw_ring(v["ring"])` ("2/4", "✓", hoặc "?" khi
  `unsure`), `headline` ("Đúng 2/4 từ" / "Hoàn hảo — đúng cả N từ" / "Máy chưa nghe rõ bài
  đọc"), `summary` ("Lỗi chính: …"). `score_line` = "c/t từ" — **một** họ số (P-06).
- "Hoàn hảo" chỉ khi `correct == total` (không dùng `score >= 95`: câu 21 từ sai 1 vẫn
  95,2 %), không từ thừa, không ghi chú, không thẻ, không lỗi âm vị, không warns/tones —
  cho **mọi ngôn ngữ** (test `perfect_needs_every_word`).
- Câu trên sân khấu (B4a): `stage_words(target, view)` (hàm thuần) → mỗi từ GỐC (giữ hoa,
  dấu câu) gạch chân cam/đỏ + "nghe ‘…’" / "(thiếu)" / ✓ bên dưới (P-02); `unsure` hoặc
  chưa chấm → không tô màu. Từ thừa: dòng "Đọc thêm: …" trong panel, **chỉ** khi `result`
  (khi `unsure` đó là chữ bịa — D-29).
- "CẦN SỬA" trong panel: tối đa 4 dòng `_mk_fix`. EN: theo GOP
  (mức chữ "lệch rõ"/"hơi lệch") hoặc âm vị CMUdict. VI (`_vi_cards`): gom N/L theo chiều
  + mẹo `_VI_TIPS` + mẫu `vi_la.wav`/`vi_na.wav`; mỗi lỗi thanh/vần một thẻ với cách đọc
  tách `vi_spell`. Mỗi thẻ: ▶ Mẫu (nếu file tồn tại), ▶ Bạn đọc (`_play_heard` →
  `play_wav_segment` theo `words_t`).
- Số GOP chỉ trong "Chi tiết số đo ▸" (`_toggle_details`, Q-03, I7).
- `unsure`: hộp "Thử lại như sau" (`UNSURE_TIPS`), câu máy nghe ẩn dưới
  "Máy nghe được gì? ▸" (`_toggle_heard`), màu xám, không bao giờ đỏ.
- Chữ IPA dùng `FONT_IPA` (`has_ipa`) — Be Vietnam Pro thiếu ký tự IPA (D-28).
- Đổi bài/chế độ gọi `_clear_prac_result()` (trừ khi đang chấm) — không để kết quả cũ.

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
