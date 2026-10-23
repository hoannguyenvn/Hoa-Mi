# LỘ TRÌNH

Nguồn gốc: `PHASE2-DANH-GIA-DU-AN-CU.md` (đánh giá dự án cũ + đề xuất Phase 2)
đối chiếu với code v2.3 hiện tại. Roadmap này **không** lặp lại lý thuyết; chỉ
nói thứ tự, phạm vi, tiêu chí xong.

## Nguyên tắc thứ tự

1. **An toàn trước:** có lưới test + context trước khi thêm tính năng.
2. **Giá trị người học trước:** đúng/sai chữ + vòng lặp luyện + tiến bộ.
3. **Chỉ công bố điều chứng minh được:** không thêm điểm khi chưa hiệu chuẩn.
4. **Tiếng Việt trước hay tiếng Anh trước** phụ thuộc câu trả lời Q-01
   (`docs/DECISIONS.md`). Các phase dưới đây độc lập để có thể đảo thứ tự.

## P0 — Nền vận hành (đã xong 2026-10-22)

- [x] `AGENTS.md`, `docs/*`, bộ 11 skills, `context-map.json`.
- [x] `tools/context_check.py` + `tools/smoke_test.py`.
- [x] Ghi lại bất biến và các cách làm bị loại.

**Xong khi:** model mới đọc 3 file là tiếp tục được; check chạy PASS.

## P1 — Lưới an toàn (1–2 ngày)

- [ ] Mở rộng `tools/smoke_test.py`: 20+ case cho `score_pronunciation`
      (n/l, th, s/sh, âm cuối, thanh điệu, từ thừa/thiếu), `cues_to_srt`,
      `_fix_cues`, `split_long_cues`, `enhance_audio`, `resample_to_16k`.
- [ ] Fixture SRT/VTT/json3 trong `tools/fixtures/`.
- [ ] Test `lessons_en.json`: id duy nhất, đủ `target/words/tips/pairs`,
      audio `mau/en/<id>.wav` + `_slow.wav` tồn tại.
- [ ] `py_compile` toàn bộ trong check.

**Xong khi:** `smoke_test.py` > 30 assert, chạy < 10 s, không cần mạng/mic/model.

## P2 — Hoàn thiện Phase 2A (4–6 ngày)

- [ ] Bài học có cấu trúc cho **tiếng Việt** (n/l, s/x, tr/ch, r/d/gi, 6 thanh,
      âm cuối) theo schema D-14; hoặc bổ sung tiếng Anh nếu Q-01 chọn EN.
- [ ] Tab 2 thành **3 cột**: `Bài học | Thu âm | Kết quả`.
- [ ] Chip lỗi theo âm (đúng / nghi sai / sai) sinh từ `items` + `flag_pair`.
- [ ] Vòng lặp: nghe mẫu → đọc → nghe lại A/B → "Thử lại" (giữ bài, xóa kết quả).
- [ ] "Âm yếu nhất" theo tuần + đếm theo âm (đã có nền `hist["ph"]`).
- [ ] Không thêm dependency nặng.

**Xong khi:** người học làm trọn một bài mà không cần hướng dẫn ngoài; mọi lỗi
hiển thị đều truy được về từ + âm + mẹo.

## P3 — Thanh điệu tiếng Việt bằng F0 (3–5 ngày)

- [ ] Phân loại contour 6 thanh (ngang/huyền/sắc/hỏi/ngã/nặng) từ `prosody.f0_track`.
- [ ] So với mẫu **cùng âm tiết** (không so người khác câu khác).
- [ ] Hiện "bạn đọc thanh sắc, mẫu là thanh huyền" + contour thu nhỏ.
- [ ] Chỉ kết luận khi đủ voiced frames + SNR; thiếu thì "chưa đủ rõ".

**Xong khi:** trên 20 bản ghi tự thu, phân loại đúng ≥ 80%; không báo sai khi
im lặng/nhiễu.

## P4 — Hiệu chuẩn (2 ngày + dữ liệu)

- [ ] Thu ~100 bản ghi (10 câu × 10 người hoặc 20 câu × 5).
- [ ] 2 giáo viên chấm độc lập 1–5.
- [ ] Tính Spearman giữa điểm app và điểm người; chỉnh ngưỡng theo dữ liệu.
- [ ] Ghi báo cáo vào `docs/CALIBRATION.md` (kể cả kết quả xấu).

**Xong khi:** có báo cáo công khai, nêu rõ giới hạn; không chỉnh ngưỡng bằng cảm tính.

## P5 — Đóng gói & vận hành (2–3 ngày)

- [ ] `git init`, `.gitignore` (model, downloads, `__pycache__`, `*.wav` tạm).
- [ ] Script cài đặt kiểm tra dependency + đường dẫn Conda.
- [ ] Đóng gói `.exe` (PyInstaller) **hoặc** bản portable kèm Python.
- [ ] Icon, phiên bản, thông báo cập nhật thủ công.
- [ ] Backup/restore `config.json`, `practice_history.json`.

**Xong khi:** máy Windows sạch chạy được bằng 1 lần double-click; gỡ sạch không để lại rác.

## P6 — Phase 2B / GOP nâng cao (tùy chọn, 4–6 ngày)

Chỉ làm sau P4 và khi Q-02 được trả lời.

- [ ] Cân nhắc `onnxruntime` thay `torch` để giảm dung lượng.
- [ ] Nút "cài gói phân tích chuyên sâu" + tiến trình tải model.
- [ ] Hiệu chuẩn riêng cho GOP trên bản ghi có nhãn.
- [ ] Hiển thị độ tin cậy + ẩn kết luận khi thiếu bằng chứng.

**Xong khi:** top-1 phát hiện âm sai ≥ 70% trên 30 bản ghi có nhãn; ≤ 1 báo động giả/câu.

## Tiêu chí nghiệm thu toàn sản phẩm

Trích `PHASE2…` §5.8, dùng làm "definition of shipped":

- Đọc đúng câu mẫu 10/10 lần → điểm ≥ 90, không báo lỗi âm vị.
- Đọc sai 1 từ ("think" → "tink") → đúng từ, đúng âm /θ/, gợi ý khớp, ≥ 9/10 lần.
- Im lặng / mic hỏng / SNR thấp → **không** hiện điểm, hiện "chưa đủ rõ".
- Chấm 1 câu ≤ 3 s (model `base`, CPU, không tính lần nạp model đầu).
- 20 lần thử liên tiếp: không crash, không rò rỉ file tạm.
- (GOP) 30 bản ghi có nhãn: top-1 ≥ 70%, ≤ 1 báo động giả/câu.

## Không nằm trong roadmap (cố tình)

- Chấm "chất giọng"/"timbre" bằng MFCC/DTW (R-01).
- So cao độ Hz tuyệt đối (R-02).
- Formant/KMeans nguyên âm (R-03).
- PDF nhiều trang biểu đồ (chờ Q-04).
- Tải video để lấy audio ngắn (R-09).
- API đám mây/đăng nhập/tài khoản.
