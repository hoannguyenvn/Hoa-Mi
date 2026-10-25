# Hoa Mi · Luyện phát âm tiếng Việt & chuyển audio thành văn bản (v1.0)

App desktop offline (giao diện `tkinter`) giúp **người nói tiếng Việt sửa phát âm** — trước hết
là lẫn **N/L**, sai **dấu thanh** và **vần** — bằng cách đọc to, để máy nghe lại và chỉ ra từng
từ cần sửa. Chạy bằng **Miniforge Conda** tại `C:\Users\ADMIN\miniforge3` (Python 3.13).

Hoa Mi tách ra từ **Oriole** (app luyện tiếng Anh) ngày 2026-10-25: phần luyện tiếng Việt
chuyển sang đây, Oriole chỉ còn luyện tiếng Anh. Lịch sử git trước ngày tách là của chung.

## 1. Chạy

Double-click `run.bat`, hoặc:

```
C:\Users\ADMIN\miniforge3\python.exe app.py
```

## 2. Có gì

- **Luyện câu**: 3 bộ câu N/L (câu ngắn, câu dài, cặp tối thiểu na/la…) và **Tùy chỉnh** (tự
  gõ câu tiếng Việt).
- **Học âm**: N, L, so sánh N–L — hướng dẫn đặt lưỡi, luồng hơi (mẹo **bịt mũi**), nghe âm mẫu.
- **Chuyển thành văn bản**: file audio/video, link YouTube, ghi âm trực tiếp → văn bản + SRT.
- **Người học** (thanh trái): nhiều người dùng chung máy, lịch sử riêng, không cần tài khoản.

## 3. Chuyển thành văn bản

Chọn **nguồn** ở thanh trên cùng (**File máy tính** | **Link YouTube** | **Ghi âm**):

| Nguồn | Cách dùng |
|---|---|
| **File máy tính** | `Chọn file…` (hoặc dán đường dẫn) → mp3/wav/m4a/flac/ogg/mp4/mov/mkv/webm → `▶ Bắt đầu` |
| **Link YouTube** | Dán link → chọn *Lấy*, *Chất lượng*, công tắc **Kèm phụ đề** + ngôn ngữ, **Nhúng phụ đề vào video** → `Tải video` / `Tải audio` / `▶ Lấy transcript` (tên nút đổi theo ô *Lấy*). Nếu YouTube chặn tải phụ đề (lỗi 429), video vẫn được lưu và phụ đề do Whisper tạo |
| **Ghi âm** | `● Bắt đầu thu âm` → nói (tối đa 15 phút; có thanh mức âm và đồng hồ) → `■ Dừng & chuyển thành văn bản` |

Sau khi bấm nút chạy:

1. Thanh tiến trình + dòng trạng thái hiện ngay dưới ô nguồn; nút **Hủy (Esc)** chỉ hiện
   khi có việc để hủy.
2. Xong: giữa màn hình là **Văn bản** (chữ to, dòng không quá dài; công tắc
   `Kèm mốc thời gian` cho `[00:00:01] …`) hoặc **Phụ đề SRT**.
3. Cột phải: số dòng / số từ / thời lượng, nút **Sao chép văn bản**, `Lưu .txt`,
   `Lưu .srt`, `Mở thư mục`, `Mở file gốc`.
4. **Nhật ký** thu gọn ở đáy cột phải (hiện dòng mới nhất) — bấm để mở toàn bộ.

Phím tắt: `Ctrl+O` chọn file · `Ctrl+Enter` bắt đầu · `Ctrl+S` lưu .txt · `Esc` hủy.

## 4. Luyện phát âm

Chọn chế độ ở góc trên (**Luyện câu** | **Học âm**), chọn bài ở ô bên cạnh hoặc bấm
**◀ Bài trước / Bài sau ▶**. Trong lúc thu và chấm, không đổi được bài.

Quy trình: bấm **nút tròn đỏ** (Thu âm) → đọc → app **tự dừng sau ~1,8 giây im lặng**
và chấm; hoặc bấm lại nút (■ **Dừng & chấm**) để dừng ngay. Dưới nút là micro đang dùng
và liên kết **Đổi** (sang Cài đặt › Micro). **Chấm file có sẵn…** để nộp file. Sau khi thu
có nút **Bản thu của bạn** (nghe lại) và **Lưu bản thu** (vào `Documents\Hoa Mi`).

Bài được chấm bằng model `small` (nghe tiếng Việt rõ hơn hẳn `base`) nếu máy đã có model
này, kể cả khi thanh trái đang chọn `base`/`tiny`.

Kết quả gồm:

1. **Đầu kết quả** (cột phải) — vòng điểm + "Đúng 9/10 từ" (hoặc "Hoàn hảo — đúng cả
   N từ" khi đúng **mọi** từ, kèm nút **Bài tiếp theo →**) và lỗi chính.
2. **Từng từ** (ngay trên câu ở giữa màn hình) — từ đúng có ✓; từ cần sửa gạch chân cam
   (N/L, sai thanh) hoặc đỏ (sai/thiếu/sai vần), bên dưới ghi **từ máy nghe được**
   ("Lan" → nghe “nan”) hoặc "(thiếu)". Từ đúng mà máy nghe **rất không chắc** gạch xám,
   "máy chưa chắc" (vẫn tính đúng, nhưng không hiện "Hoàn hảo"). App chấp nhận giọng
   Bắc: đọc r/d/gi, s/x, tr/ch như nhau ("rừng" → "dừng") vẫn tính đúng; **n/l thì không**.
3. **Cần sửa** — tối đa 4 mục: lỗi N/L gom theo chiều (đọc N thành L hay ngược lại) kèm mẹo,
   sai dấu thanh, sai vần/dấu ("lắm" → "lám", kèm cách đọc tách "l + ăm + thanh sắc"). Mỗi
   mục có ▶ Mẫu (nếu có file mẫu) và ▶ Bạn đọc (nghe lại đúng từ đó trong bản thu).
4. **Tiến bộ** (đáy cột phải) — đường xu hướng của tối đa 10 lần gần nhất, số lần, tốt nhất /
   lần trước, âm hay sai (N/L, dấu thanh, vần).

**Điểm là gì:** số từ máy nghe đúng / tổng số từ. Máy so **chữ** nghe được, chưa phân tích
cao độ — nên lỗi **thanh điệu** chỉ bắt được khi máy nghe ra chữ khác dấu; Whisper đôi khi
"tự sửa hộ" theo ngữ cảnh. Phân tích thanh điệu bằng cao độ (F0) nằm trong lộ trình.

**Máy chưa nghe rõ:** khi máy không chắc, nghe ra chuỗi dài bất thường, hoặc nghe ra câu
Whisper hay tự sinh ("cảm ơn các bạn đã theo dõi"…), app **không hiện điểm**, không tô đỏ
câu, không lưu vào tiến bộ — chỉ gợi ý cách thu lại.

Nếu mic gần như im lặng (đỉnh < 0,8%), app **không chấm** — báo rõ và tự dò micro khác có
tín hiệu. Nếu 7 giây đầu không có tiếng nói, app dừng và nhắc kiểm tra micro.

Nếu mic bị **tắt tiếng** ở Windows, app dừng và báo rõ chứ không chấm — đây là lỗi
môi trường, không phải lỗi nhận dạng. Micro WDM-KS không dùng được (PortAudio không
hỗ trợ thu blocking) nên app **ẩn khỏi ô chọn**; hãy dùng bản `[Windows DirectSound]`,
`[Windows WASAPI]` hoặc `[MME]` cùng tên.

**Mic ngoài (USB, tai nghe bluetooth):** PortAudio chỉ liệt kê thiết bị lúc khởi động,
nên sau khi cắm/kết nối hãy bấm **Quét lại** (hoặc mở tab Cài đặt — app tự quét). Với
tai nghe bluetooth, Windows chỉ mở micro khi bật profile **Hands-Free**: Control Panel →
Sound → tab *Recording* → chuột phải → *Show Disabled Devices* → Enable
`Headset (… Hands-Free AG Audio)`; hoặc Control Panel → *Devices and Printers* →
chuột phải thiết bị → *Properties* → *Services* → tích *Hands-Free Telephony*. App sẽ
hiện gợi ý ngay dưới ô Micro nếu thấy tai nghe mà chưa thấy micro của nó. Nút
**Âm thanh Windows** mở thẳng trang âm thanh của hệ điều hành.

## 5. Cài đặt

**Thay đổi được lưu ngay** (không còn nút "Lưu cài đặt"); `Khôi phục mặc định` ở góc trên.

- **Micro**: chọn thiết bị thu âm, `Thử 2 giây` (kết quả hiện ngay dưới dòng "Kiểm tra
  micro"), `Quét lại`, `Âm thanh Windows`.
- **Giao diện và lưu file**: Sáng / Tối, thư mục lưu video và phụ đề.
- **Phụ đề YouTube mặc định**: kèm phụ đề, ngôn ngữ phụ đề, nhúng vào video.
- **Phím tắt** và **Giới thiệu** (phiên bản, tình trạng thư viện, ffmpeg).
- **Model / Ngôn ngữ nhận dạng** chỉ đổi ở góc dưới thanh điều hướng (menu có ghi chú
  từng model, vd "small — khuyên dùng cho tiếng Việt").

## 6. Phụ đề khi tải YouTube

Ba chế độ ở ô **Lấy**:

| Chế độ | Việc app làm |
|---|---|
| **Chỉ transcript (.srt/.txt)** | Chỉ tải phụ đề (vài KB). Không có phụ đề thì mới tải tạm audio để Whisper tạo, xong xóa audio tạm |
| **Video MP4 (+ phụ đề)** | Tải video, tạo `.srt`/`.txt`, có thể **nhúng phụ đề mềm** vào MP4 |
| **Audio MP3 (+ phụ đề)** | Tải audio, tạo `.srt`/`.txt`, không nhúng |

Thứ tự lấy phụ đề:

1. **Phụ đề có sẵn** của video (thủ công trước, rồi tới phụ đề tự động YouTube).
2. Nếu **không có** → app **tự tạo bằng Whisper**, dùng đúng `Model` + `Ngôn ngữ` đang chọn.

Ngôn ngữ phụ đề: `Tự động` (ưu tiên ngôn ngữ gốc của video → Việt → Anh), hoặc ép `Tiếng Việt` / `Tiếng Anh`.

> Lưu ý: rất nhiều video (TED, phim, khóa học…) có sẵn **phụ đề dịch** do YouTube/ cộng đồng tạo. Nếu log ghi
> `vi (Vietnamese)` kèm dòng nhắc "bản dịch của YouTube" thì đó là bản dịch, không phải bản gốc. Muốn lấy bản gốc
> tiếng Anh, chọn `Ngôn ngữ phụ đề = Tiếng Anh`.

Kết quả nằm cạnh file video:

- `Tên video.srt` — SRT chuẩn: số thứ tự, `00:00:01,234 --> 00:00:03,500`, dòng trống.
- `Tên video.txt` — text kèm mốc thời gian `[00:00:01] …`.
- Phụ đề tự động kiểu "chạy chữ" của YouTube được gộp & lọc trùng, câu dài được chia nhỏ.
- Ô **Nhúng phụ đề vào video**: nhúng phụ đề mềm (bật/tắt được trong VLC, mpv, PotPlayer…)
  bằng ffmpeg — không re-encode hình nên rất nhanh.

Cần `yt-dlp` + `imageio-ffmpeg` (kèm sẵn ffmpeg). Chỉ tải nội dung bạn có quyền dùng —
tải video YouTube vi phạm Điều khoản dịch vụ khi dùng cho nội dung không thuộc quyền của bạn.

## 7. File trong thư mục

- `app.py` — giao diện (thanh điều hướng + 3 màn hình) + xử lý audio/phụ đề + chấm điểm
- `prosody.py` — đo cao độ F0 (nền cho phân tích thanh điệu sau này)
- `config.json` — cài đặt đã lưu (tự tạo, xóa đi để về mặc định)
- `learners.json` — người học + lịch sử luyện (tự tạo)
- `mau/` — âm mẫu tiếng Việt (`vi_*.wav`, giọng TTS — **chỉ để nghe**, không dùng để chấm)
- `gen_mau.py` — tạo lại âm mẫu (cần mạng 1 lần)
- `assets/fonts/` — font Be Vietnam Pro (3 file) + giấy phép `OFL.txt`
- `requirements.txt` — faster-whisper, av, sounddevice, numpy, yt-dlp, imageio-ffmpeg, edge-tts
- `run.bat` — double-click để chạy (dùng Conda Python)
- `downloads/` — thư mục lưu mặc định cho video/phụ đề tải từ YouTube
- `tools/` — `smoke_test.py`, `ui_check.py`, `context_check.py`, `asr_bench.py`
- `docs/`, `.opencode/skills/`, `AGENTS.md` — tài liệu cho người và AI tiếp quản

## 8. Context & skills cho AI

- `AGENTS.md` — luật bắt buộc, bất biến kỹ thuật, nghi thức đầu/cuối phiên.
- `docs/PROJECT-STATE.md` — đang làm gì, trạng thái từng tính năng, rủi ro.
- `docs/HANDOFF.md` — nhật ký bàn giao; mục cuối là việc còn treo.
- `docs/DECISIONS.md` — quyết định không được phá + cách làm đã bị loại.
- `.opencode/skills/` — 10 skill theo tính năng, chỉ nạp khi đúng việc.

```
C:\Users\ADMIN\miniforge3\python.exe tools\context_check.py
C:\Users\ADMIN\miniforge3\python.exe tools\smoke_test.py
C:\Users\ADMIN\miniforge3\python.exe tools\ui_check.py
```
