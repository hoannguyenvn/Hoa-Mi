---
name: App Lessons & Sample Audio
description: Thêm hoặc sửa bài luyện tiếng Việt trong Hoa Mi — bộ câu PRACTICE_SETS (vi1–vi3, Tùy chỉnh), bài Học âm GUIDES (N, L, so sánh N–L), audio mẫu mau/vi_*.wav và gen_mau.py. Dùng khi người dùng nhắc tới bài học, thêm bài, Học âm, audio mẫu, giọng đọc mẫu, hoặc gen_mau.py.
---

# Lessons & Sample Audio

Hoa Mi chỉ có bài **tiếng Việt** (HM-01). Bài hiện nằm **trong code** (`app.py`), chưa
có file JSON riêng.

Đọc trước: `docs/FEATURES.md` §3, §5; `docs/DECISIONS.md` D-13 (TTS chỉ để nghe), D-38
(giọng Bắc r/d/gi, s/x, tr/ch được tính đúng).

## 1. Nơi khai báo

| Thành phần | Ở đâu | Ghi chú |
|---|---|---|
| Bộ câu luyện | `PRACTICE_SETS` + `_VI_IDS` + `SET_IDS` | khóa `name`, `lang` (luôn `"vi"`), `target`, `hint`; tùy chọn `ipa`, `tips`, `samples` |
| Câu tự gõ | `PRACTICE_SETS["custom"]` | `lang = "vi"`, chữ lấy từ ô nhập |
| Học âm | `GUIDES` + `GUIDE_IDS` | `name`, `lang`, `target`, `instruction`, `samples=[(nhãn, file trong mau/)]` |
| Audio mẫu | `mau/vi_*.wav` | 16 kHz mono, sinh bằng `gen_mau.py` |

`samples` của bộ câu: phần tử đầu là bản mẫu dùng cho biểu đồ ngữ điệu (`_prac_record`
lấy `samples[0]`). Bộ `vi1–vi3` hiện **chưa có** mẫu → không có biểu đồ (đúng: TTS không
dùng để chấm, I13; chờ bản ghi người thật).

## 2. Sinh lại audio mẫu (`gen_mau.py`)

```powershell
& "C:\Users\ADMIN\miniforge3\python.exe" gen_mau.py          # bỏ qua file đã có
& "C:\Users\ADMIN\miniforge3\python.exe" gen_mau.py --force  # ghi đè
```

- Giọng `vi-VN-HoaiMyNeural` (edge-tts, cần mạng lúc tạo; app chạy offline).
- `CLIPS` = (chữ, giọng, tên file). Thêm dấu chấm sau từ đơn để TTS ngắt tự nhiên.
- **Đã biết:** `GUIDES["n"]` trỏ `vi_nen.wav`, `GUIDES["l"]` trỏ `vi_len.wav` nhưng hai file
  này **chưa có** trong `mau/` → nút ▶ tương ứng bị xám. Chạy `gen_mau.py` để tạo.

## 3. Thêm một bài câu

1. Thêm khóa mới vào `PRACTICE_SETS` (`"lang": "vi"`), thêm id vào `_VI_IDS`.
2. `hint` ngắn, nói âm cần chú ý; `target` có dấu đầy đủ.
3. Cập nhật test `lessons_loaded` trong `tools/smoke_test.py` (danh sách `SET_IDS`).
4. Chạy `tools/smoke_test.py`, `tools/ui_check.py`, `tools/context_check.py`.

## 4. Thêm một bài Học âm

1. Thêm dict vào `GUIDES`, id vào `GUIDE_IDS`; `instruction` là các bước khẩu hình + "Lỗi
   hay gặp".
2. Thêm clip vào `CLIPS` của `gen_mau.py`, chạy lại.
3. Cập nhật `lessons_loaded` (danh sách `GUIDE_IDS`).

## 5. Bẫy

- Bài cho cặp r/d/gi, s/x, tr/ch: `score_pronunciation` gộp theo giọng Bắc (D-38) → một bài
  luyện riêng các cặp này cần cờ chấm theo bài (ROADMAP).
- Đổi `id` làm lịch sử cũ trong `learners.json` không còn bài khớp (vẫn giữ, chỉ bị bỏ qua).
- Không dùng audio TTS để chấm (I13).

## 6. Triệu chứng → nguyên nhân

| Triệu chứng | Nguyên nhân |
|---|---|
| Nút ▶ bị xám | file trong `samples` không có trong `mau/` |
| Bài mới không hiện | quên thêm id vào `_VI_IDS` / `GUIDE_IDS` |
| Không có biểu đồ ngữ điệu | bài không có `samples` (bình thường) |
