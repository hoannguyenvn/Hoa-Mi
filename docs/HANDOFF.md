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
3. Chạy `context_check.py` + `smoke_test.py` + `ui_check.py`; dán kết quả vào mục handoff.
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

> Bạn đang tiếp quản dự án **Hoa Mi** (luyện phát âm tiếng Việt).
> Hãy làm đúng thứ tự sau, không đọc toàn bộ repo:
> 1. Đọc `AGENTS.md`.
> 2. Chạy `C:\Users\ADMIN\miniforge3\python.exe tools\context_check.py`.
> 3. Đọc `docs/PROJECT-STATE.md`, mục cuối `docs/HANDOFF.md`, `docs/DECISIONS.md`.
> 4. Nạp skill khớp việc cần làm trong `.opencode/skills/`.
> 5. Tóm tắt lại: hiện trạng, việc đang dở, rủi ro, rồi mới đề xuất bước tiếp.
> Không phá các bất biến I1–I16 trong `AGENTS.md`. Kết thúc phiên phải cập nhật
> `PROJECT-STATE` + thêm mục `HANDOFF`.

## 4. Nhật ký

> Nhật ký trước khi tách khỏi Oriole: `docs/handoff-archive/oriole-truoc-tach.md`.

## 2026-10-25 — Claude Code — Tạo Hoa Mi từ Oriole (HM-01)

**Mục tiêu phiên:** người dùng quyết: Oriole chỉ còn luyện tiếng Anh; phần luyện tiếng Việt (N/L)
chuyển sang repo mới `hoannguyenvn/Hoa-Mi`.

**Đã làm:**
- Clone lịch sử Oriole tại `957f995` vào repo trống; đổi danh tính (`APP_TITLE`, rail,
  `Documents\Hoa Mi`, tiền tố `hoami_`, `VERSION = "1.0"`).
- H1–H2 (`f31de82`): bỏ 14 bài Anh, Học âm TH/SH, `mau/en`, clip `en_*`, `lessons_en.json`,
  `tools/build_lessons.py`; bỏ chế độ **Từ YouTube** (đọc to tiếng Anh: `yt_read.py`, báo cáo,
  màn Tiến bộ, `tools/ytread_*`); câu Tùy chỉnh chỉ tiếng Việt; `headset_mic_missing` không import
  sounddevice khi đã có danh sách thiết bị (test hỏng trên máy không có PortAudio).
- H3 (`fd6a3a8`): bỏ `pron_en.py`, `gop.py`, cmudict/torch/transformers; view giữ khóa
  `has_gop`/`gop_marks`/`phon` (rỗng); `tools/ui_check.py` thay `ui_shots.py`; `context_check`
  bỏ qua `config.json`/`practice_history.json` khi chưa có; context-map cập nhật; bỏ skill
  `app-phonemes`.
- H4: tài liệu — `AGENTS.md`, `README.md`, `docs/PROJECT-STATE.md`, `ROADMAP.md`, `DECISIONS.md`
  (HM-01, HQ-01, HQ-02), `FEATURES.md`, `ARCHITECTURE.md`, `UPSTREAM.md` (mới), skill sửa theo.

**Quyết định mới:** HM-01.

**Đã kiểm chứng (container Linux, Python 3.12 + Xvfb — không phải máy Windows):**
- [x] `tools/smoke_test.py` → 72/72 PASS
- [x] `tools/ui_check.py` → 0 lỗi callback (3 màn, 3 bài + kết quả giả, 3 bài Học âm, tối, hẹp)
- [x] `tools/context_check.py` → 0 FAIL
- [x] `py_compile` + `pyflakes` sạch (trừ 2 cảnh báo có từ trước)

**Chưa kiểm chứng / cần người dùng thử:**
- Chạy trên Windows bằng Conda; thu âm thật; chấm bằng Whisper thật; YouTube tải.

**Việc tiếp theo (ưu tiên giảm dần):**
1. CI GitHub Action (P1) · sinh `vi_nen.wav`, `vi_len.wav` (C1).
2. Bài có cấu trúc (C2), nghe phân biệt N/L (C3).
3. Thanh điệu bằng F0 (T1) — cần bản ghi người thật (Q-03).

**Cảnh báo cho model sau:**
- Không thêm lại phần tiếng Anh. Sửa phần dùng chung → ghi `docs/UPSTREAM.md`, cherry-pick sang Oriole.
- `GUIDES` trỏ `vi_nen.wav`/`vi_len.wav` chưa có file (nút ▶ xám) — có từ trước khi tách.

## 2026-10-25 (tiếp) — Claude Code — HM-02: nhận bản sửa âm thanh từ Oriole + CI

**Đã làm:** `soft_clip`, `REC_TRIM_TAIL_SEC` 0,25 s, `mic_is_bluetooth`, `preload_model` (+ `_preload_model`
dùng `practice_model(..., "vi")`), `prac_timing_line`, `listen_path` + `MAU_HQ_DIR`, `gen_mau.py` sinh thêm
bản 24 kHz; `ui_check` chặn preload + bước mic bluetooth; `.github/workflows/ci.yml`; context-map, UPSTREAM.
**Quyết định mới:** HM-02.
**Đã kiểm chứng (Linux + Xvfb):** smoke 77/77, `ui_check` 0 lỗi, `context_check` 0 FAIL.
**Chưa kiểm chứng:** `asr_bench`, thu âm thật, `gen_mau.py` (máy chủ TTS bị chặn ở container), CI chạy lần đầu.
**Việc tiếp theo:** như PROJECT-STATE mục 1; chạy `gen_mau.py` để có `vi_nen.wav`, `vi_len.wav` + bản hq.

## 2026-10-25 (tiếp 2) — Claude Code — HM-03: A5, A6, A10 từ Oriole

**Đã làm:** `_write_wav16`, `listen_copy_path`, `listen_recording`, `remove_recording`, `save_frames_wav(listen=)`,
`enhance_audio(trim_at=)`; `mic_check_verdict` + `_test_mic` 5 s + link "Kiểm tra"; `calib_save` (config, Cài
đặt, `calib_dir`, `calib_info`, `_calib_save`); `tools/fixtures/` + 4 test.
**Đã kiểm chứng (Linux + Xvfb):** smoke 81/81, `ui_check` 0 lỗi (xem ảnh Cài đặt), `context_check` 0 FAIL.
**Chưa kiểm chứng:** mic/loa thật, Whisper thật.

