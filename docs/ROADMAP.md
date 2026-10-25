# LỘ TRÌNH — Hoa Mi

Hoa Mi = luyện phát âm **tiếng Việt** cho người nói tiếng Việt (tách từ Oriole, HM-01).
Roadmap chỉ nói thứ tự, phạm vi, tiêu chí xong.

## Nguyên tắc thứ tự

1. **An toàn trước:** lưới test + context trước khi thêm tính năng.
2. **Giá trị người học trước:** đúng/sai chữ + vòng lặp luyện + tiến bộ.
3. **Chỉ công bố điều chứng minh được:** không thêm điểm khi chưa hiệu chuẩn; việc không sinh
   điểm mới (nội dung, nghe phân biệt, ôn tập) làm trước.
4. **Sửa phần dùng chung** (thu âm, Whisper, UI khung) thì chuyển sang/nhận từ Oriole bằng
   `git cherry-pick` (`docs/UPSTREAM.md`).

## Thứ tự đề xuất

| # | Việc | Vì sao trước |
|---|---|---|
| 1 | **P1** + CI (GitHub Action: py_compile + smoke + ui_check + context_check) | lưới an toàn cho repo mới |
| 2 | **C1** âm mẫu còn thiếu (`vi_nen.wav`, `vi_len.wav`) | nút ▶ của Học âm N/L đang xám |
| 3 | **C2** thêm bài có cấu trúc | 3 câu N/L quá ít |
| 4 | **C3** nghe phân biệt N/L | không cần mic, không rủi ro chấm |
| 5 | **A** nhận bản sửa âm thanh từ Oriole (A1, A3–A6) | thu/nghe tốt hơn |
| 6 | **T1** thanh điệu bằng F0 | cốt lõi của app, cần dữ liệu |
| 7 | **P4** hiệu chuẩn | trước khi gọi là "điểm phát âm" |

## P0 — Nền vận hành (xong, kế thừa Oriole)

- [x] `AGENTS.md`, `docs/*`, 10 skill, `context-map.json`, `context_check`, `smoke_test`.
- [x] `tools/ui_check.py` chạy App thật (cả Linux/Xvfb).

## P1 — Lưới an toàn

- [ ] CI GitHub Action (Ubuntu + Xvfb + `python3-tk`): `py_compile`, `smoke_test`, `ui_check`,
      `context_check`.
- [ ] Thêm case `score_pronunciation` tiếng Việt: n/l hai chiều, thanh, vần, giọng Bắc, thiếu/thừa từ.

**Xong khi:** mỗi push đều chạy 4 kiểm tra, < 2 phút.

## C — Nội dung tiếng Việt

- [ ] **C1** sinh `vi_nen.wav`, `vi_len.wav` (`gen_mau.py`) — `GUIDES` đã trỏ tới nhưng file chưa có.
- [ ] **C2** bài có cấu trúc (schema JSON riêng, `lang="vi"`): n/l đầu từ, s/x, tr/ch, r/d/gi
      (cần cờ chấm theo bài vì D-38 gộp theo giọng Bắc — HQ-02), 6 thanh, âm cuối -n/-ng, -t/-c.
      Mỗi bài 4–6 câu, đặt âm ở nhiều vị trí.
- [ ] **C3** nghe phân biệt: "bạn nghe từ nào?" với cặp tối thiểu thật (na/la, nên/lên, no/lo,
      nặng/lặng) — không cần mic.
- [ ] **C4** ôn tập hằng ngày từ lỗi của chính mình (giãn cách 1 → 3 → 7 ngày; chỉ thêm khi
      `evidence_gate` qua) — dùng chung thiết kế L1 của Oriole.

## T — Thanh điệu bằng F0 (P3 cũ của Oriole)

- [ ] **T1** phân loại contour 6 thanh (ngang/huyền/sắc/hỏi/ngã/nặng) từ `prosody.f0_track`.
- [ ] So với mẫu **người thật cùng âm tiết** (không TTS — I13; cần Q-03).
- [ ] Hiện "bạn đọc thanh sắc, mẫu là thanh huyền" + contour thu nhỏ.
- [ ] Chỉ kết luận khi đủ khung có giọng + SNR; thiếu thì "chưa đủ rõ".

**Xong khi:** trên 20 bản ghi tự thu, phân loại đúng ≥ 80 %; không báo sai khi im lặng/nhiễu.

## A — Âm thanh & nhận dạng (dùng chung với Oriole, ROADMAP A của Oriole)

Làm ở Oriole trước rồi cherry-pick, hoặc ngược lại — ghi `docs/UPSTREAM.md`.

- [ ] A3 cảnh báo mic bluetooth (HFP) · A4 cắt im lặng không nuốt âm cuối (-t, -c, -p quan trọng
      với tiếng Việt) · A5 "▶ Bạn đọc" phát bản thu gốc · A6 kiểm tra mic 5 giây.
- [ ] A10 lưu bản thu tự nguyện để hiệu chuẩn (nguồn dữ liệu cho T1/P4).
- [ ] Đo model tiếng Việt tốt hơn `small` (vd bản Whisper tinh chỉnh tiếng Việt chuyển sang
      CTranslate2) bằng `asr_bench --dir` trên bản ghi thật.

## P4 — Hiệu chuẩn

- [ ] Thu ~100 bản ghi tiếng Việt (A10), 2 giáo viên chấm 1–5, Spearman, chỉnh ngưỡng theo dữ liệu.
- [ ] Ghi `docs/CALIBRATION.md` (kể cả kết quả xấu).

## P7 — Đóng gói

- [ ] Bỏ đường dẫn cứng Conda; `.exe` (PyInstaller) hoặc bản portable; icon riêng (chim họa mi —
      icon hiện vẫn là logo Oriole vẽ bằng code, `logo_rows`).

## Đã biết khi tách (2026-10-25)

- Thanh trái ở cửa sổ hẹp: nhãn "Người học" bị cắt ("ười h") — có từ Oriole.
- Code ngữ điệu/trọng âm (`inton_view`, `stress_note`, `speed_note`) kế thừa từ tiếng Anh, chưa
  bài nào dùng; khi làm T1 thay bằng phân tích thanh điệu.

## Không nằm trong roadmap (cố tình)

- Bài/luật tiếng Anh (thuộc Oriole, HM-01).
- Chấm "chất giọng" bằng MFCC/DTW (R-01); so cao độ Hz tuyệt đối (R-02).
- Khử ồn trước khi chấm; API đám mây/đăng nhập/tài khoản.
