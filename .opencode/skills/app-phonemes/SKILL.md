---
name: App Phoneme Diagnosis & GOP
description: Sửa phần chẩn đoán âm vị tiếng Anh trong Oriole — CMUdict, IPA, căn chuỗi Needleman-Wunsch, gợi ý sửa /θ/ /ð/ /ʃ/ /r/ /l/, âm cuối, và GOP wav2vec2 tùy chọn. Dùng khi người dùng nhắc tới âm vị, IPA, CMUdict, "nghe thành âm gì", GOP, wav2vec2, hoặc dòng "lỗi âm vị" ở Tab 2.
---

# Phoneme Diagnosis & GOP

Hai lớp bằng chứng khác nhau, **không thay nhau**:

| Lớp | Câu hỏi | Module | Có đổi `score`? |
|---|---|---|---|
| Âm vị từ chữ | Máy nghe ra từ nào, lệch âm nào? | `pron_en.py` | Không |
| GOP acoustic | Model nghe âm đó có giống âm mẫu không? | `gop.py` | Không |

`score` vẫn là `correct / total` của `app-pronunciation`. Đọc trước: `docs/DECISIONS.md`
D-08, D-09; bất biến I6, I7; `docs/ARCHITECTURE.md` §3.3.

## 1. Chuỗi âm vị (`pron_en.py`)

| Symbol | Hợp đồng |
|---|---|
| `phonemes(word, raw=False)` | `list[str]` ARPAbet hoặc `None`. `raw=False` bỏ số trọng âm; `raw=True` giữ `0/1/2`. |
| `_load_dict()` | Nạp `cmudict` **một lần** (`_DICT_TRIED`). Thiếu thư viện → `{}`, không crash. |
| `_EXTRA` | Bảng tay cho từ ASR hay nghe sai mà CMUdict không có (`tink`, `dis`, `tousand`…). |
| `ipa(phs, stress=False)` | Ghép IPA; `stress=True` thêm `ˈ` trước âm có số 1. |
| `word_ipa(word)` | IPA 1 từ, đặt `ˈ` ở đầu âm tiết nhấn khi từ có ≥ 2 nguyên âm. |
| `align(a, b)` | Needleman–Wunsch → `[(a_i|None, b_j|None, "same"|"sub"|"del"|"ins")]`. |
| `compare_words(exp, got)` | Danh sách issue cho **một cặp từ**. |
| `analyze_pairs(pairs)` | Tổng hợp nhiều cặp → `issues`, `counts`, `top`, `by_phoneme`, `unknown`. |

`pairs` do `_w_prac` truyền vào: `(chỉ_số_item, từ_mục_tiêu, từ_máy_nghe)` chỉ với
item `st != "ok"` **và** có đủ hai từ. Chỉ chạy khi `det_lang == "en"`.

### `compare_words` — thứ tự quyết định

1. Từ mục tiêu không có trong từ điển → `[]` (không đoán bừa).
2. Từ nghe được không có trong từ điển → `_letter_issues` (suy theo **chữ**,
   mọi issue có `approx=True`). Không được coi là bằng chứng chắc.
3. Từ nghe được là **tiền tố** của từ mục tiêu (`cat` → `ca`, `cats` → `cat`) →
   báo `k = min(2, len(exp) - len(got))` âm cuối bị mất. Đây là mất âm cuối,
   không phải đổi nguyên âm.
4. Còn lại: `align`; `sub`/`del` → issue; `ins` **bỏ qua** (ASR thêm âm thường nhiễu).

`analyze_pairs` sắp issue **phụ âm trước, nguyên âm sau** vì ASR dễ nhầm nguyên âm
hơn. `top` sắp theo `-n` rồi theo mã âm.

### Hợp đồng một issue

```python
{"exp": "TH", "got": "T", "word": "think", "pos": "đầu từ",
 "ipa_exp": "θ", "ipa_got": "t", "label": "/θ/ → [t]",
 "tip": "...", "approx": False, "kind": "cons",
 "i": 0, "heard_word": "tink"}          # i/heard_word do analyze_pairs thêm
```

`pos` ∈ `đầu từ` / `giữa từ` / `cuối từ` / `âm`. `kind` ∈ `cons` / `vowel`.
Khóa `label` và `tip` được `_prac_done` in trực tiếp — đổi tên phải sửa cả UI.

### Gợi ý sửa

- `TIPS[(âm_mục_tiêu, âm_nghe_được | None)]`. `None` = âm bị mất.
- `LETTER_TIPS[(đoạn_chữ_mục_tiêu, đoạn_chữ_nghe)]` cho từ lạ.
- Không có mục trong `TIPS` → câu generic trong `_issue`. Đừng để trống.
- Viết tiếng Việt, mô tả **khẩu hình** (lưỡi/răng/môi/rung), không viết "âm X".
- Thêm cặp mới = thêm khóa `TIPS` + 1 case `smoke_test.py`.

## 2. GOP acoustic (`gop.py`)

Chỉ chạy khi `gop.available()` (có `torch` + `transformers`) và câu là tiếng Anh.
Thiếu model/thư viện → `score()` trả `None`, UI bỏ qua. Lần đầu tải model ~1,2 GB.

| Bước | Hàm | Ghi chú |
|---|---|---|
| Sẵn sàng | `available()` | Chỉ kiểm tra `importlib.util.find_spec`; model tải ở lần chấm đầu. |
| Nạp model | `_ensure_loaded()` | `MODEL_ID = facebook/wav2vec2-lv-60-espeak-cv-ft`; lỗi → `_BROKEN=True`, không thử lại. |
| Dựng chuỗi | `_seq(words)` | Dùng `pron_en.phonemes(..., raw=True)`; `ER0` riêng cho ER không nhấn; `AH0` không chấm. |
| Suy luận | `_run()` | Đọc WAV qua `prosody.read_wav`, chuẩn hóa mean/std, CTC Viterbi. |
| Chấm | `_rows()` | `gop = mean(log p(âm đúng) - log p(âm mạnh nhất còn lại))`. |
| Quy đổi | `_score(gop)` | Logistic `100 / (1 + exp(-(gop - 0.2) / 2.2))`. **Không phải % đúng.** |
| Cache mẫu | `_run_cached()` | Key = đường dẫn + mtime + size + chuỗi âm; tối đa 24 mục. |
| Giải phóng | `forget()` | Dùng trong test; xóa model + cache. |

### Ngưỡng "yếu" (I6)

```python
# Có bản mẫu cùng câu (ref_gop):
score < 55 and gop < ref_gop - 1.5      # kém rõ rệt
score < 25 and gop < ref_gop - 0.5      # rất thấp
# Không có bản mẫu:
score < 50 and gop < -1.0
```

Không đổi sang ngưỡng tuyệt đối khi **có** bản mẫu: model yếu ở một số âm sẽ báo oan.
`ok` = số âm có `score >= 55`; `total` = số âm có khung và được chấm.

### Kết quả `gop.score()` trả về

```python
{"rows": [...], "issues": [...], "ok": int, "total": int,
 "skipped": [từ_không_có_trong_từ_điển], "has_ref": bool}
```

`issues[]` là issue của `pron_en._issue` **cộng** `gop`, `score`, `ref_score`,
`heard`, `frames`, `wi`, `ph`. `_prac_done` chỉ đọc: `label`, `pos`, `word`,
`score`, `ref_score`, `tip`, `has_ref`. Đổi khóa → sửa UI cùng lúc.

Thứ tự issue: `score` tăng dần, cùng điểm thì nhiều khung trước (lỗi rõ hơn).

## 3. Hiển thị

- Có GOP: tiêu đề `Âm vị (GOP):`, tối đa 5 issue, mỗi issue 1 dòng `label`, `pos`,
  `word`, `%`, `mẫu %` nếu có, rồi `↳ tip`.
- Không có GOP: dùng `phon.issues` (từ chữ) và ẩn ghi chú cấp từ đã được giải thích
  để tránh trùng.
- Luôn ghi chú GOP 0–100 **không phải % phát âm đúng** (I7).
- Không hiện `approx` như bằng chứng chắc; nếu cần, ghi "có thể".

## 4. Khi sửa — checklist

1. `pron_en` là hàm thuần: test trước, không cần UI/mic/model.
2. Thêm từ vào `_EXTRA` chỉ khi nó là lỗi ASR **thường gặp**; đừng nhồi từ điển.
3. Không đổi `phonemes` sang trả chuỗi có số trọng âm mặc định — `align` sẽ lệch.
4. Không bỏ nhánh "tiền tố = mất âm cuối": nếu bỏ, `cat` → `ca` sẽ báo sai nguyên âm.
5. Không chấm GOP cho tiếng Việt (model là âm vị tiếng Anh).
6. Không cache model trong `app.py`; cache nằm trong `gop.py`.
7. Thêm case vào `tools/smoke_test.py`:
   - `word_ipa("think")` có `θ`;
   - `analyze_pairs([(0, "think", "tink")])` có `exp == "TH"`;
   - `analyze_pairs([(0, "cat", "ca")])` báo âm cuối;
   - từ lạ → `approx is True`;
   - `phonemes("") is None`.
8. Chạy `py_compile`, `smoke_test.py`, `context_check.py`.

## 5. Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| Mọi từ đều báo lỗi nguyên âm | `align` nhận chuỗi còn số trọng âm (`raw=True` nhầm chỗ) |
| `cat` → `ca` báo sai `/æ/` | thiếu nhánh tiền tố trước `align` |
| Báo lỗi âm cuối sai vị trí | `pos` tính theo index ops thay vì index âm mục tiêu |
| Từ lạ không báo gì | `_letter_issues` không khớp `LETTER_TIPS`, hoặc hai từ giống nhau |
| GOP báo oan gần như mọi âm | thiếu `ref_wav` hoặc `ref_rows` lệch độ dài → rơi về ngưỡng tuyệt đối |
| Lần chấm thứ hai vẫn chậm | cache mẫu bị clear do quá 24 mục, hoặc `_BROKEN` sau lỗi tải |
| Điểm GOP 90% nhưng nghe rõ sai | GOP là tương quan log-posterior, không phải phần trăm đúng (I7) |
| `TypeError` khi `gop.score` trả `None` | UI quên `if g:` trước khi đọc `issues` |

## Mẫu lỗi hay gặp (D-42)

`pron_en.error_patterns(từ_mẫu, từ_nghe)` → mã trong `PATTERNS` (final, th, nl, diph, cluster, short).
`app.error_pattern_view(fixes)` gom cho panel ÂM HAY SAI (chế độ Từ YouTube). Chống báo oan: âm vị giống
< `PATTERN_MIN_SIM` (0,3) → không xếp; /r/ cuối không tính; "short" chỉ khi thiếu từ; từ có `unread`
(người học dừng trước cuối đoạn) bị bỏ qua. Thêm mẫu mới: thêm vào `PATTERNS` + luật trong
`error_patterns` + ví dụ thật vào test `english_error_patterns_from_real_reading`.
