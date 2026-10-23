---
name: App Lessons & Sample Audio
description: Thêm hoặc sửa bài luyện trong Oriole — schema lessons_en.json, 14 bài tiếng Anh, audio mẫu mau/en/<id>.wav, <id>_slow.wav, w_<word>.wav, và tools/build_lessons.py. Dùng khi người dùng nhắc tới bài học, thêm bài, audio mẫu, giọng đọc mẫu, lessons_en.json, hoặc build_lessons.py.
---

# Lessons & Sample Audio

Bài luyện tiếng Anh là **dữ liệu**, không phải code. Thêm bài = sửa `LESSONS` trong
`tools/build_lessons.py` → sinh lại `lessons_en.json` + audio → cập nhật test/đếm.

Đọc trước: `docs/FEATURES.md` §3, §5; `docs/DECISIONS.md` D-13 (TTS chỉ để nghe),
D-14 (nội dung bằng JSON).

## 1. Schema `lessons_en.json`

```json
{
  "version": 1,
  "lessons": [
    {
      "id": "en_th",
      "group": "Phụ âm",
      "title": "Anh — Âm /θ/ và /ð/ (think, this)",
      "focus": ["TH", "DH"],
      "target": "Think about this thing.",
      "words": ["think", "about", "this", "thing"],
      "tips": ["...", "..."],
      "pairs": [["think", "tink"], ["this", "dis"]],
      "ipa": "θɪŋk əˈbaʊt ðɪs θɪŋ",
      "focus_ipa": "/θ/ /ð/",
      "samples": {"normal": "en_th.wav", "slow": "en_th_slow.wav"}
    }
  ]
}
```

### Trường bắt buộc (theo `docs/context-map.json`)

`id`, `target`, `words`, `tips`, `pairs`, `ipa`, `focus_ipa`, `samples`.
`pairs` được phép `[]` nhưng **phải có khóa**. `samples.normal` và `samples.slow`
phải trỏ tới file tồn tại trong `mau/en/`.

### Trường app thực sự đọc (`load_en_lessons`)

| Trường | Dùng để |
|---|---|
| `id` | khóa trong `PRACTICE_SETS`, tên file audio |
| `title` | tên trong combobox |
| `target` | câu mẫu để chấm |
| `words` | từ khóa; app lấy **2 từ đầu** làm nút nghe mẫu |
| `tips` | danh sách gạch đầu dòng ở thẻ hướng dẫn |
| `ipa` | dòng `IPA: ...` |
| `focus_ipa` | đầu dòng gợi ý `Âm trọng tâm: ...` |
| `pairs` | 3 cặp đầu vào gợi ý `Cặp dễ lẫn: ...` |
| `hint` | **có đọc nhưng build_lessons không sinh ra** → hiện luôn rỗng |

`group`, `focus`, `samples` **app bỏ qua** khi nạp; `samples` chỉ để
`context_check` xác minh asset. Đừng giả định sửa `samples` trong JSON là đổi được
đường dẫn phát — app tự ghép `en/<id>.wav`, `en/<id>_slow.wav`, `en/w_<word>.wav`.

### Audio

| File | Nội dung | Tốc độ |
|---|---|---|
| `mau/en/<id>.wav` | cả câu `target` | `+0%` |
| `mau/en/<id>_slow.wav` | cả câu `target` | `-30%` |
| `mau/en/w_<word>.wav` | từng từ, đọc `"<word>."` | `+0%` |

Tất cả 16 kHz mono PCM (do `gen_mau.mp3_to_wav16k`). Không dùng TTS để **chấm** (D-13).

## 2. Sinh lại (`tools/build_lessons.py`)

```powershell
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\ADMIN\miniforge3\python.exe" tools\build_lessons.py          # bỏ qua file đã có
& "C:\Users\ADMIN\miniforge3\python.exe" tools\build_lessons.py --force  # ghi đè tất cả
```

- Cần mạng + `edge-tts` (`VOICE = "en-US-AriaNeural"`).
- `sentence_ipa()` ghép `pron_en.word_ipa()` từng từ; từ lạ giữ chữ thường.
- `focus_text()` đổi mã ARPAbet → `/ipa/`.
- `main()` ghi JSON UTF-8, newline `\n`, indent 2; sau đó TTS.
- `make_wav()` bỏ qua file đã tồn tại trừ `--force`; file MP3 tạm luôn xóa trong
  `finally` (I10).
- `tts()` thử 4 lần, chờ tăng dần — mạng chập chờn không làm hỏng cả bộ.

**Quan trọng:** sửa `target` mà chạy **không** `--force` sẽ giữ audio cũ → câu mẫu
và audio lệch nhau. Sửa nội dung câu/từ ⇒ luôn `--force`.

## 3. Thêm một bài — các bước

1. Thêm dict vào `LESSONS` trong `tools/build_lessons.py`:
   - `id` duy nhất, kebab/snake ngắn, bắt đầu `en_` (quy ước hiện tại);
   - `group` ∈ `Phụ âm` / `Âm cuối` / `Nguyên âm` / `Nâng cao`;
   - `title` tiếng Việt, có ví dụ;
   - `focus` là mã ARPAbet **có trong** `pron_en.ARPABET_IPA`;
   - `target` 1 câu, độ dài vừa phải (5–10 từ), có âm trọng tâm;
   - `words` là các từ **xuất hiện trong** `target`;
   - `tips` 2–3 dòng, mô tả khẩu hình;
   - `pairs` cặp đúng/sai, mỗi cặp `[đúng, máy_hay_nghe_sai]`.
2. Chạy `tools\build_lessons.py --force` (hoặc không `--force` nếu chỉ thêm bài mới).
3. Kiểm tra file mới trong `mau/en/` và `len(lessons)`.
4. Cập nhật `tools/smoke_test.py → lessons_loaded`: hiện assert **18** `SET_IDS`
   (3 Việt + 14 Anh + `custom`). Thêm 1 bài ⇒ 19. Quên bước này là FAIL ngay.
5. Cập nhật số đếm trong `docs/FEATURES.md` §5, `docs/PROJECT-STATE.md`,
   `README.md` nếu có ghi "14 bài / 74 clip".
6. Chạy `context_check.py` + `smoke_test.py`.

`context_check` chỉ kiểm tra **tối thiểu** (`min_lessons: 14`, `mau/en/*.wav: 74`),
nên thêm bài không làm FAIL, nhưng thiếu audio của bài mới thì FAIL.

## 4. Sửa bài đang có

- Chỉ đổi `tips`/`title`/`focus_ipa`: chạy lại không `--force` cũng được, nhưng
  nhớ `build_lessons` **ghi đè toàn bộ** `lessons_en.json` từ `LESSONS`, nên mọi
  sửa tay trong JSON sẽ mất.
- Đổi `target` hoặc `words`: bắt buộc `--force` để audio khớp.
- Đổi `id`: sinh file mới; file cũ còn trong `mau/en/`, phải xóa tay nếu muốn sạch.
- Không sửa `lessons_en.json` trực tiếp rồi coi đó là nguồn sự thật.

## 5. Bài tiếng Việt

- 3 bài Việt (`vi1`, `vi2`, `vi3`) và 5 guide (`n`, `l`, `nl`, `th`, `sh`) nằm
  **trong code** (`PRACTICE_SETS`, `GUIDES`), không nằm trong JSON.
- Muốn thêm bài Việt có cấu trúc như tiếng Anh: phải mở rộng schema + loader +
  `build_lessons` (hoặc file JSON riêng), cập nhật `docs/DECISIONS.md`.
  Đừng nhét bài Việt vào `lessons_en.json` — `load_en_lessons` gán cứng `lang="en"`.

## 6. Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| Nút ▶ phát câu cũ | sửa `target` nhưng chạy build không `--force` |
| Nút ▶ bị xám | thiếu `mau/en/<id>.wav` hoặc `_slow.wav` |
| Không thấy nút từ khóa thứ 3 | app chỉ lấy `words[:2]` |
| `smoke_test` FAIL `SET_IDS=19` | chưa cập nhật assert 18 |
| `context_check` FAIL "thiếu audio từ khóa" | build lỗi giữa chừng, hoặc `words` có từ chưa sinh |
| JSON mất sửa tay | `build_lessons.py` ghi đè từ `LESSONS` |
| Giọng đọc sai/không đúng âm | `edge-tts` đọc theo chính tả; kiểm tra `target` và từ viết thường |
| `edge-tts` treo | mạng/proxy; chạy lại, file đã có sẽ được bỏ qua |
| Bài mới không xuất hiện | `id` trùng, hoặc JSON lỗi khiến `load_en_lessons` trả `[]` |
