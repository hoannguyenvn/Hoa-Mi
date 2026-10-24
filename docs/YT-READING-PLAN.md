# YT-READING-PLAN — Đọc to đoạn transcript YouTube (tiếng Anh)

> Kế hoạch tính năng mới (D-39). Mỗi bước Y1…Y5 một commit. Cập nhật mục 4 khi xong bước.

## 1. Luồng người học

1. Xem video YouTube tiếng Anh, chép link vào Oriole (Luyện phát âm → nguồn **Từ YouTube**).
2. Oriole lấy phụ đề tiếng Anh (thiếu thì Whisper) **và** âm thanh gốc (cache tạm trong phiên).
3. Transcript chia thành **đoạn** ~20–45 s (D-39: đọc cả đoạn, không từng câu).
4. Với mỗi đoạn, hai chế độ (D-39: có cả hai):
   - **Nghe rồi đọc** (mặc định): ▶ đoạn gốc của video → thu → chấm.
   - **Đọc thẳng**: chỉ nhìn chữ → thu → chấm.
5. Kết quả: cả đoạn hiện lại, từ khác gạch màu, dưới từ ghi "nghe ‘…’"; từ có thể do phụ đề sai
   gạch xám "phụ đề có thể sai" và **không tính** điểm. ▶ Mẫu từng từ (đoạn video) + ▶ Bạn đọc.
6. **Đọc lại đoạn này** → so lần trước (vd 38/52 → 45/52); "Từ cần luyện" gom từ sai nhiều lần.
7. Phiên là **một lần** (không lưu video/đoạn để mở lại), nhưng **lịch sử học** (điểm từng
   lần, từ hay sai) lưu theo **người học** để xem tiến bộ.

## 2. Nguyên nhân khác biệt (đừng đổ hết cho người học)

| Nguồn | Cách nhận | Hiển thị |
|---|---|---|
| Người học đọc sai/thiếu | phụ đề = lời gốc (Whisper trên audio gốc), người học khác | đỏ/cam như bài luyện |
| Phụ đề sai | Whisper trên audio gốc **không** nghe ra từ của phụ đề | xám "phụ đề có thể sai", bỏ khỏi tổng |
| Cách viết khác | chuẩn hóa: rút gọn (don't = do not), gonna, số, từ đệm um/uh | coi như giống |
| Số viết bằng chữ số | đọc khác cách viết được ("1990") | xám "số — có thể đọc khác", bỏ khỏi tổng |
| Whisper nghe nhầm người học | chưa phân biệt được (D-37) | giữ cổng bằng chứng + "máy chưa chắc" |

Điểm = đúng / (tổng − từ không tính). Luôn ghi rõ "N từ không tính" để con số giải thích được (I4).

## 3. Bước làm

| Bước | Nội dung | Trạng thái |
|---|---|---|
| Y1 | Hàm thuần + test: `yt_read.py` (làm sạch phụ đề, chia đoạn, chuẩn hóa tiếng Anh) + `read_aloud_diff` trong `app.py` | ✅ |
| Y2 | `ytread_prepare` (link → phụ đề tiếng Anh + audio gốc 16 kHz vào thư mục tạm, Hủy qua `cancel()`, dọn khi lỗi) + `ytread_orig_hyp` (Whisper đoạn gốc, khi cần, có cache) + `tools/ytread_bench.py`. Thread worker gắn UI làm ở Y3 | ✅ |
| Y3 | Chế độ "Từ YouTube" trong Luyện: ô link + Lấy transcript (state `loading`, Esc hủy), ◀ ▶ đoạn, Nghe rồi đọc / Đọc thẳng, ô chữ cả đoạn tô màu (`ytread_view`), panel CẦN SỬA + PHỤ ĐỀ CÓ THỂ SAI với ▶ Mẫu / ▶ Bạn đọc từng từ (`token_spans`); tự dừng sau 3,5 s im lặng, tối đa 150 s | ✅ |
| Y4 | Đọc lại + so lần trước, "Từ cần luyện", lịch sử theo người học (hồ sơ cục bộ) | ⛔ |
| Y5 | GOP/ngữ điệu so audio gốc khi đoạn đủ sạch (không nhạc nền) | ⛔ |

## 4. Rủi ro

- Đoạn dài: Whisper dễ bịa/trôi căn chỉnh → giữ đoạn ≤ 45 s, cổng bằng chứng, VAD khi > 30 s (D-36).
- Phụ đề tự động không dấu câu → chia đoạn theo khoảng lặng giữa cue + độ dài, không theo câu.
- Âm thanh gốc có nhạc nền: Whisper trên audio gốc có thể sai → "phụ đề có thể sai" báo nhiều;
  Y2 đo trên vài video thật trước khi chốt.
- Bản quyền: audio chỉ để nghe trong phiên, xóa khi đóng phiên (không lưu lâu).
- "Tài khoản người học" = **hồ sơ cục bộ** trên máy: chọn tên, không đăng nhập (người dùng xác nhận
  2026-10-24, D-39).

## 5. Số đo Y2 (2026-10-24, `ytread_bench`, base, 5 đoạn đầu)

| Video | Phụ đề | Đoạn | Nghi phụ đề sai |
|---|---|---|---|
| Ken Robinson (TED) | thủ công | ~22 s, ~60 từ | 3,7 % |
| Tim Urban (TED) | thủ công | ~22 s, ~70 từ | 4,2 % |
| Ken Robinson | tự động | ~43 s, ~120 từ | 8,9 % |
| Tim Urban | tự động | ~42 s, ~120 từ | 6,4 % |

- Chuẩn bị 6–20 s; Whisper đoạn gốc ~1–2 s/đoạn → làm khi người học chọn đoạn, không làm trước.
- Nhiều cờ ở phụ đề tự động là lỗi thật của phụ đề ("pr rr inators", "prorated" ← procrastinator);
  phần còn lại do Whisper bỏ từ khi nói nhanh. Cờ chỉ hiện khi người học **cũng** khác phụ đề.
- Phụ đề tự động không có dấu câu → đoạn bị cắt ở 45 s (~120 từ, dài). Xem lại ở Y3 sau khi thử
  đọc thật; có thể hạ `PARA_MAX_SEC` cho phụ đề tự động.

## 6. Y3 — ghi chú

- Phiên giữ đến khi lấy video khác hoặc đóng app (không xóa khi đổi chế độ — người học có thể
  quay lại). `_on_close` gọi `close()`.
- "Bản thu = audio gốc" (`tools/ytread_e2e.py`, Tim Urban đoạn 2): tải 6,8 s, chấm 7,1 s,
  "Hoàn hảo — đúng cả 63 từ".
- Chưa làm (Y4): so lần trước, "Từ cần luyện", lịch sử theo hồ sơ người học; ô panel tiến bộ
  trống ở chế độ này.
