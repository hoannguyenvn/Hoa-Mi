# Oriole · Chuyển audio thành văn bản & luyện phát âm (v2.3)

App desktop offline (giao diện `tkinter`), chạy bằng **Miniforge Conda** có sẵn tại
`C:\Users\ADMIN\miniforge3` (Python 3.13).

## 1. Chạy

Double-click `run.bat`, hoặc:

```
C:\Users\ADMIN\miniforge3\python.exe app.py
```

## 2. Có gì mới

**Làm mới giao diện (B1–B5, xem `docs/UI-PLAN.md`)**

- **Bố cục mới kiểu ứng dụng**: thanh điều hướng bên trái (Chuyển thành văn bản ·
  Luyện phát âm; dưới cùng: Model · Ngôn ngữ, Giao diện tối/sáng, Cài đặt). Cửa sổ hẹp
  thì thanh chỉ còn biểu tượng (rê chuột để xem tên).
- **Luyện phát âm**: câu cần đọc nằm giữa màn hình; sau khi chấm, **chính câu đó** cho biết
  kết quả — từ sai được gạch chân, bên dưới ghi máy nghe thành gì. Nút thu tròn màu đỏ có
  thanh mức âm khi đang thu. Kết quả chi tiết, "Cần sửa" và ngữ điệu nằm ở cột bên phải;
  nút **Thử lại** luôn ở đáy cột. Đổi bài bằng ô chọn bài hoặc **◀ Bài trước / Bài sau ▶**.
- **Ngữ điệu dễ đọc hơn**: một câu nhận xét thay cho các con số; biểu đồ có nhãn từng từ;
  thêm **trọng âm** (từ nào được nhấn, bạn so với mẫu) và **tốc độ đọc** — chỉ để tham
  khảo, không tính điểm. Đáy cột phải có **đường tiến bộ** của 10 lần gần nhất.
- **Chuyển thành văn bản** và **Cài đặt** theo cùng kiểu: chọn nguồn bằng nút ghép, văn bản
  đọc dễ hơn, nhật ký thu gọn; Cài đặt lưu ngay khi đổi, công tắc thay ô đánh dấu.

- Font **Be Vietnam Pro** (đi kèm app trong `assets/fonts/`, không cần cài vào Windows);
  ký hiệu phiên âm IPA vẫn hiển thị bằng Segoe UI cho đủ ký tự.
- Ô chọn/ô đánh dấu vẽ lại rõ ràng ở cả giao diện sáng và tối (dấu ✓ thay cho dấu ✕),
  ô bị tắt hiện màu xám; ô Ngôn ngữ hiện tên ("Tự động", "Tiếng Việt"…); nút "Sao chép".
- Mọi ô văn bản có thanh cuộn; thanh tiến trình chỉ hiện khi đang xử lý; có biểu tượng app.
- Đổi bài luyện thì kết quả cũ được xóa; đọc đúng hết (cả tiếng Anh) hiện "Hoàn hảo".

**v2.3 — thu âm tự dừng & chặn "nghe nhầm" khi mic im lặng**

- **Tự dừng khi đọc xong**: sau khi đã nghe thấy giọng, app tự dừng thu khi im
  lặng ~1,3 giây (nay 1,8 giây) và chấm luôn — không cần bấm gì. Nếu 7 giây đầu không có tiếng
  nói, app dừng và báo mic im lặng thay vì ghi tiếp.
- **Không chấm khi mic im lặng**: bản thu gần như không có tín hiệu (đỉnh < 0,8%
  ≈ -42 dB) không được đưa cho Whisper — tránh kiểu "bịa" câu lặp vô nghĩa trên nền
  im lặng. App báo rõ và hướng dẫn bật micro trong Windows. Sàn thấp này để micro
  array của laptop (thường chỉ ~2% đỉnh) vẫn dùng được.
- **Tự dò micro có tín hiệu**: khi mic đang chọn không thu được gì, app thử các
  micro khác trên máy và chọn cái có tín hiệu (bỏ qua WDM-KS vì không hỗ trợ thu
  liên tục).
- **Sửa kết quả tự mâu thuẫn**: không còn "0% · 11 lỗi âm vị" mà vẫn "Hoàn hảo";
  chỉ hiện "Hoàn hảo" khi đúng 100%. Từ thừa chỉ hiện tối đa 3 từ + tổng số, câu
  máy nghe được quá dài sẽ được rút gọn và cảnh báo.
- **Không báo "lỗi âm vị" cho tiếng Việt** (chỉ tiếng Anh mới chấm âm vị).
- **Chống bịa của Whisper**: bật VAD của faster-whisper và tắt nối ngữ cảnh giữa
  các đoạn (`condition_on_previous_text=False`).
- **Nút Sáng/Tối ở thanh trên** đổi theme ngay (trước đây chỉ đổi được trong tab
  Cài đặt).

**v2.2 — GOP: chấm âm vị bằng acoustic**

- **GOP thật** (Goodness of Pronunciation): model `wav2vec2` đa ngữ chuyên âm vị
  (IPA) nghe lại bản đọc, căn CTC từng âm vị của câu mẫu vào audio rồi chấm
  log-posterior cho từng âm. Không còn chỉ dựa vào chữ Whisper nghe được.
- **So với bản mẫu cùng câu**: bản mẫu (giọng đọc chuẩn) cũng được chấm y như vậy;
  chỉ báo "yếu" khi bản đọc của bạn kém rõ rệt so với bản mẫu ở đúng vị trí đó —
  tránh báo oan vì model yếu ở một số âm/giọng.
- Mỗi âm yếu hiện: `%` mức khớp, `%` của bản mẫu, âm mà model nghiêng về
  (`/θ/ → [t]`) và cách sửa khẩu hình.
- Cần `torch` + `transformers`; model ~1.2 GB tự tải lần đầu (xem mục 8).

**v2.1 — luyện tiếng Anh theo âm vị**

- **14 bài luyện tiếng Anh** cho người Việt: /θ/ /ð/, /ʃ/ /s/, âm cuối /p t k/,
  cụm cuối -sks/-xts/-fts, /s/ /z/ số nhiều, /v/ /w/, /r/ /l/, /æ/, /ɪ/ /iː/,
  /ʊ/ /uː/, /ŋ/, /tʃ/ /dʒ/ /ʃ/, âm lướt /ə/.
- **Phân tích âm vị thật**: lấy chuỗi âm vị chuẩn của câu (CMUdict) và chuỗi âm vị
  của từ mà máy *nghe được*, căn chỉnh Needleman–Wunsch → chỉ ra đúng âm bị thay
  hoặc bị nuốt (`/θ/ → [t] ở đầu từ "think"`), kèm cách sửa theo khẩu hình.
  Không dùng điểm acoustic giả, không so Hz giữa hai người.
- **Nghe mẫu offline**: mỗi bài có câu đọc thường, đọc chậm và 2 từ khoá
  (giọng `en-US-AriaNeural`, file trong `mau/en/`).
- **Nhớ tiến bộ**: `practice_history.json` lưu số lần, điểm cao nhất, lần trước và
  các âm hay sai; thẻ bài học hiện "Âm yếu nhất".
- **Biểu đồ ngữ điệu**: vẽ đường cao độ (F0) của câu mẫu và bản đọc trên cùng
  trục thời gian, quy về bán cung so với trung vị của từng người — kèm nhận xét
  cuối câu lên/xuống, khoảng cao độ và độ lệch đường cong.
- IPA của câu hiện ngay dưới câu mẫu, có dấu trọng âm.

**v2.0**

- **Một luồng duy nhất**: tab *Chuyển thành văn bản* nhận 3 nguồn — **File máy tính**,
  **Link YouTube**, **Ghi âm trực tiếp** — tất cả cho ra cùng một chỗ kết quả.
  Không còn cảnh tải MP3 ở tab YouTube rồi "nạp sang tab 1".
- **Thanh trên dùng chung**: Model + Ngôn ngữ + nút đổi Sáng/Tối, áp dụng cho mọi tab.
- **Nhớ cài đặt** trong `config.json`: model, ngôn ngữ, thư mục lưu, chế độ tải,
  phụ đề, micro, kích thước cửa sổ.
- **Giao diện mới**: thẻ (card) bo viền mảnh, màu nhấn xanh, bố cục 2 cột
  (trái = điều khiển + nhật ký, phải = kết quả), **dark mode**, tự co giãn theo DPI
  (màn hình 250% vẫn không bị bóp chữ).
- **Hủy được** việc đang chạy, có **nhật ký từng bước**, thanh tiến trình thật.
- Kết quả có **2 tab xem trước: Văn bản / SRT**, xuất `.txt` + `.srt` bằng một nút.

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

Chọn chế độ ở góc trên (**Luyện câu** | **Học âm** | **Từ YouTube**), chọn bài ở ô bên
cạnh hoặc bấm **◀ Bài trước / Bài sau ▶**. Trong lúc thu và chấm, không đổi được bài.

Ba chế độ:

- **Luyện câu**: 3 bộ tiếng Việt (n/l), **14 bài tiếng Anh**, và `Tùy chỉnh`.
- **Học âm**: N, L, so sánh N–L, TH, S/SH — hướng dẫn đặt lưỡi/luồng hơi
  và nút nghe **âm mẫu** giọng bản ngữ (offline).
- **Từ YouTube** (tiếng Anh, cần mạng để tải): dán link video, bấm **Lấy transcript**.
  Oriole lấy phụ đề tiếng Anh gốc (không có thì Whisper tự tạo) và âm thanh gốc, chia
  thành **đoạn ~20–45 giây** (◀ Đoạn trước / Đoạn sau ▶).
  - **Nghe rồi đọc** (mặc định): bấm Thu âm → app phát đoạn gốc → nghe xong tự bắt đầu
    thu. **Đọc thẳng**: thu ngay. Đọc hết đoạn, ngừng ~4 giây là app tự chấm.
  - Kết quả: cả đoạn tô màu — đỏ (sai/thiếu), cam (lỗi quen thuộc, vd nuốt âm cuối), xám
    (**phụ đề có thể sai**: chính người nói trong video cũng không nói như phụ đề — từ này
    **không tính** điểm). Panel phải liệt kê từng từ với ▶ Mẫu (giọng trong video) và
    ▶ Bạn đọc. "Đọc lại đoạn này" để thử lại.
  - Nếu máy đã có model `medium`, bản đọc của bạn được nghe bằng medium (chính xác hơn, chấm
    ~10 giây/đoạn); đoạn gốc được nghe sẵn trong lúc bạn nghe/đọc.
  - Cách viết khác nhau vẫn tính là đúng: I'm = I am, gonna = going to, 1990 = nineteen
    ninety; từ đệm (um, uh) bỏ qua.
  - **Âm hay sai**: lỗi được gom theo thói quen — âm cuối & -s số nhiều, âm th, n đọc thành l,
    nguyên âm đôi (bacon, odor), cụm phụ âm đầu (smell, sniff), từ ngắn bị nuốt — kèm số từ, ví dụ
    từ chính bài đọc của bạn, mẹo sửa, ▶ Mẫu / ▶ Bạn đọc. Đọc từ 2 đoạn: thêm tổng cả video.
  - **Báo cáo cuối**: bấm **Kết thúc · xem báo cáo** bất cứ lúc nào (vd đọc 3/6 đoạn rồi dừng) hoặc
    **Xem báo cáo →** ở đoạn cuối. Báo cáo gồm tổng điểm, 3 điều nên tập trung, âm hay sai cả bài,
    trôi chảy, từng đoạn (nghe lại, mở lại đoạn) và từ cần luyện, kèm **biểu đồ**: % từ đúng từng
    đoạn, bạn vs người nói (tốc độ, dao động cao độ, độ dài từ ngắn), số từ theo mẫu lỗi. **Lưu báo cáo** ghi `bao-cao.html`
    (mở bằng trình duyệt, có nút nghe lại) cùng các bản thu vào Documents\Oriole.
  - **Ngữ điệu**: so độ dao động cao độ mỗi câu của bạn với người nói (vd bạn ~5 bán cung, người
    nói ~12 → "giọng bạn đều hơn nhiều"), kèm đường cao độ thu nhỏ từng câu (chấm = người nói,
    liền = bạn) để bắt chước chỗ lên/xuống giọng. Chỉ mô tả, không tính điểm.
  - **Nhịp**: so độ dài từ ngắn (to, of, the, and…) của bạn với người nói — người Việt hay đọc
    đều từng tiếng nên kéo dài từ ngắn (vd bạn ~380 ms, người nói ~200 ms), kèm ví dụ và ▶.
  - **Đoạn văn dễ đọc**: các câu cách nhau rõ; **từ nên nhấn in đậm**, chỗ nối âm gạch chân (gợi ý để
    tập — bấm "Ẩn gợi ý" để tắt).
  - **Nối âm**: chỗ nên đọc nối (phụ âm cuối + nguyên âm đầu: talk about, think of) được gạch chân
    ở mối nối ngay trong đoạn trước khi đọc (bấm "Ẩn gạch chân nối âm" để tắt); mục NỐI ÂM có
    ▶ Mẫu / ▶ Bạn đọc từng cụm. App chỉ chỉ ra để tập, không chấm nối/ngắt.
  - **Trôi chảy** (so với người nói, không tính điểm): tốc độ đọc, số từ mỗi hơi, chỗ bạn
    ngừng giữa cụm từ (dấu **/** đỏ trong đoạn), chỗ người nói ngừng mà bạn đọc liền.
  - **Từng câu**: ▶ Mẫu (người nói) và ▶ Bạn đọc cho mỗi câu, kèm thời lượng hai bên.
  - Bản thu + kết quả của từng đoạn được giữ khi chuyển đoạn qua lại. Nút **Lưu bản thu**
    (cạnh "Bản thu của bạn") lưu ngay vào **Documents\Oriole**: bản đọc `.wav`, đoạn văn `.txt`,
    chi tiết `.json`, đoạn gốc `_goc.wav`; hộp xác nhận ghi rõ thư mục và hỏi có mở không.
    Đã đọc từ 2 đoạn trở lên: **Lưu cả N đoạn đã đọc** gom tất cả vào một thư mục con. Đã lưu
    thì nút đổi thành **Đã lưu ✓** (bấm để mở thư mục). Luyện câu cũng có nút Lưu bản thu.
  - Phiên dùng một lần: âm thanh gốc và bản thu nằm trong thư mục tạm, xóa khi lấy video khác
    hoặc đóng app. Ngữ điệu, nhấn & nhịp, nối âm, lịch sử theo người học: bản sau (D-40).

Mỗi bài tiếng Anh có: câu mẫu, **IPA**, âm trọng tâm, cặp dễ lẫn (`think–tink`),
nút nghe **Nghe mẫu / Chậm / 2 từ khoá**, và hộp gợi ý khẩu hình. Sau khi thu, có thêm
nút **Bản thu của bạn** để nghe lại.

Quy trình: bấm **nút tròn đỏ** (Thu âm) → đọc → app **tự dừng sau ~1,8 giây im lặng**
và chấm; hoặc bấm lại nút (lúc này là ■ **Dừng & chấm**) để dừng ngay. Trong lúc thu có
thanh mức âm, đồng hồ và trạng thái ("đã nghe giọng" / "chưa nghe thấy giọng"). Dưới
nút là micro đang dùng và liên kết **Đổi** (sang Cài đặt › Micro; nên dùng
**DirectSound** hoặc WASAPI, cách miệng 10–20 cm). **Chấm file có sẵn…** để nộp file.

Bài **tiếng Việt** được chấm bằng model `small` (nghe tiếng Việt rõ hơn hẳn `base`) nếu máy
đã có model này, kể cả khi thanh trái đang chọn `base`/`tiny`. Dòng "Đã xử lý" sau khi thu báo
đầu vào nhỏ/vỡ, **phòng hơi ồn** (giọng chỉ to hơn nền dưới ~15 dB) và đoạn âm bị mất khi máy bận.

Nếu mic gần như im lặng (đỉnh < 0,8%), app **không chấm** — báo rõ và tự dò micro
khác có tín hiệu. Nếu 7 giây đầu không có tiếng nói, app cũng dừng và nhắc kiểm tra
micro (Windows: Settings → System → Sound → Input — bỏ Mute, tăng Volume lên 100%).

Kết quả gồm:

1. **Đầu kết quả** (cột phải) — vòng điểm + "Đúng 2/4 từ" (hoặc "Hoàn hảo — đúng cả
   N từ" khi đúng **mọi** từ, kèm nút **Bài tiếp theo →**) và lỗi chính.
2. **Từng từ** (ngay trên câu ở giữa màn hình) — từ đúng có ✓ bên dưới; từ cần sửa
   gạch chân cam (lỗi quen thuộc/sai thanh) hoặc đỏ (sai/thiếu/sai vần), bên dưới ghi
   **từ máy nghe được** ("Think" → nghe “tink”) hoặc "(thiếu)". Tiếng Anh có GOP: từ máy
   nghe đúng nhưng có âm **lệch rõ** cũng gạch cam, ghi "âm /θ/ lệch" — vẫn tính là từ
   đúng trong điểm. Từ đúng mà chính máy nghe **rất không chắc** gạch xám, ghi "máy chưa
   chắc" (vẫn tính đúng, nhưng không hiện "Hoàn hảo"). Bài tiếng Việt chấp nhận giọng
   Bắc: đọc r/d/gi, s/x, tr/ch như nhau ("rừng" → "dừng") vẫn tính đúng; n/l thì không.
3. **Cần sửa** — tối đa 4 mục: tiếng Việt gom lỗi N/L, sai dấu thanh, sai vần/dấu
   ("lắm" → "lám", kèm cách đọc tách "l + ăm + thanh sắc"); tiếng Anh theo âm vị.
   Mỗi mục có ▶ Mẫu (nếu có file mẫu) và ▶ Bạn đọc (nghe lại đúng từ đó trong bản thu).
4. **Âm vị (GOP)** (tiếng Anh, khi đã cài model acoustic) — chấm từng âm vị bằng
   CTC trên chính bản đọc, so với bản mẫu cùng câu. Chỉ liệt kê âm **kém rõ rệt**
   so với bản mẫu, ghi bằng chữ "lệch rõ" / "hơi lệch"; số đo nằm trong
   "Chi tiết số đo".
   Nếu chưa có model, app quay về cách cũ: so chuỗi âm vị của từ Whisper nghe được
   với chuỗi chuẩn (CMUdict) — cũng hiện `/âm/ → [âm nghe được]`.
5. **Tiến bộ** (đáy cột phải) — đường xu hướng của tối đa 10 lần gần nhất, số lần,
   tốt nhất / lần trước (theo số từ đúng, vd "3/4"), âm hay sai của ngôn ngữ đó.
6. **Ngữ điệu** — một câu nhận xét dễ hiểu (vd "Cuối câu bạn xuống giọng giống mẫu ✓",
   "Cuối câu mẫu xuống giọng, bạn lại lên giọng", "Giọng bạn hơi đều…"), rồi biểu đồ cao
   độ: nét đứt = mẫu, nét liền = bạn, cao/thấp so với giọng của chính mỗi người; dưới
   biểu đồ là **nhãn từng từ**, từ cần sửa có nền nhạt. **Trọng âm**: chấm đặc = từ bạn
   nhấn, vòng nét đứt = từ mẫu nhấn, kèm câu "Mẫu nhấn “think”, bạn nhấn “about”".
   **Tốc độ**: "Bạn đọc chậm hơn mẫu ~30 %" (đọc chậm khi luyện là bình thường). Tất cả
   **chỉ mô tả, không tính điểm**; số đo (bán cung, độ lệch) nằm trong "Chi tiết số đo".
   Hiện cho 14 bài tiếng Anh (có audio mẫu); bài tiếng Việt chờ bản ghi mẫu người thật.

**Máy chưa nghe rõ:** khi máy không chắc (độ tin thấp và đúng < 50 %), nghe ra chuỗi
dài bất thường, hoặc nghe ra câu Whisper hay tự sinh ("cảm ơn các bạn đã theo dõi"…),
app **không hiện điểm**, không tô đỏ câu, không lưu vào tiến bộ — chỉ gợi ý cách thu lại.

**GOP chấm thế nào (nói thẳng):**

- Model nghe lại audio, ép căn chuỗi âm vị **mong đợi** (CMUdict) vào các khung
  20 ms bằng CTC Viterbi; mỗi âm vị lấy log xác suất của nó trừ log xác suất của
  âm cạnh tranh mạnh nhất → **GOP** (log posterior ratio).
- Số 0–100 (trong "Chi tiết số đo") là quy đổi logistic từ GOP, **không phải % phát âm đúng**;
  chỉ để so sánh tương đối giữa các lần đọc.
- Chỉ báo lỗi khi bạn kém bản mẫu **≥ 1.5 log** ở cùng âm (và dưới 55%), nên bản
  mẫu tự so với chính nó luôn 0 lỗi.
- Âm giảm lược **schwa (AH0)** không chấm (biến thiên quá lớn); các biến thể hợp lệ
  được gộp (flap `ɾ` cho /t/, `eə` cho /e/ + /r/, âm tiết `ɹ` cho ER0...).
- **Giới hạn**: model phân biệt **phụ âm tốt hơn nguyên âm**; giọng vùng miền và
  chất lượng mic ảnh hưởng; câu quá ngắn/nhiều tiếng ồn có thể không căn được.
  Đây vẫn là ước lượng acoustic, không phải giám khảo bản ngữ.

**Cách cũ (khi chưa cài model):** app so chuỗi âm vị của từ Whisper nghe được với
chuỗi chuẩn, nên:

- lỗi **phụ âm** (θ/t, s/ʃ, âm cuối, cụm cuối) rất đáng tin;
- lỗi **nguyên âm** có thể bỏ lọt hoặc báo nhầm khi model nhỏ (`base`) — ví dụ câu
  mẫu "ship" từng bị nghe thành "shape". Chọn model `small` trở lên sẽ chắc hơn;
- **trọng âm** chưa chấm điểm; biểu đồ ngữ điệu chỉ mô tả đường cao độ;
- từ ngoài từ điển CMUdict và không đoán được theo chữ sẽ không có kết luận âm vị.

Whisper đôi khi "tự sửa hộ" lỗi phát âm theo ngữ cảnh nên có thể bỏ lọt lỗi nhỏ.

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
- `pron_en.py` — engine âm vị tiếng Anh (CMUdict, căn chỉnh, gợi ý sửa)
- `gop.py` — chấm âm vị bằng acoustic (wav2vec2 CTC, tùy chọn; cần torch)
- `prosody.py` — đo cao độ F0 + so đường ngữ điệu (numpy, không cần librosa)
- `lessons_en.json` — 14 bài luyện tiếng Anh (câu, IPA, từ khoá, gợi ý, cặp dễ lẫn)
- `tools/build_lessons.py` — tạo lại `lessons_en.json` + audio mẫu (`--force` để ghi đè)
- `config.json` — cài đặt đã lưu (tự tạo, xóa đi để về mặc định)
- `practice_history.json` — lịch sử luyện (tự tạo sau lần chấm đầu tiên)
- `mau/` — 12 âm mẫu Việt/Anh + `mau/en/` 74 clip cho 14 bài tiếng Anh
- `assets/fonts/` — font Be Vietnam Pro (3 file) + giấy phép `OFL.txt`
- `tools/ui_shots.py` — chụp màn hình các trạng thái giao diện để so sánh trước/sau
- `gen_mau.py` — tạo lại thư viện mẫu (cần mạng 1 lần)
- `requirements.txt` — faster-whisper, av, sounddevice, numpy, yt-dlp,
  imageio-ffmpeg, cmudict, edge-tts, torch, transformers
- `run.bat` — double-click để chạy (dùng Conda Python)
- `downloads/` — thư mục lưu mặc định cho video/phụ đề tải từ YouTube
- `docs/` — tài liệu dự án: hiện trạng, kiến trúc, tính năng, quyết định, handoff
- `.opencode/skills/` — 11 skill hướng dẫn AI sửa đúng từng phần
- `AGENTS.md` — luật làm việc cho AI agent (đọc trước khi sửa)

## 8. Cài GOP (model âm vị, tùy chọn)

GOP cần thêm `torch` + `transformers` và model ~1.2 GB. Máy này đã cài sẵn; nếu
chuyển sang máy khác:

```
C:\Users\ADMIN\miniforge3\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
C:\Users\ADMIN\miniforge3\python.exe -m pip install transformers
```

Lần chấm đầu tiên app tự tải model
`facebook/wav2vec2-lv-60-espeak-cv-ft` vào
`%USERPROFILE%\.cache\huggingface` (cần mạng một lần, sau đó offline).
Nếu thiếu torch/model, app **không báo lỗi** — tự quay về cách so âm vị cũ
(Whisper + CMUdict).

## 9. Context & skills cho AI

Repo tự chứa ngữ cảnh để một AI model khác tiếp quản mà không cần hỏi lại:

- `AGENTS.md` — luật bắt buộc, bất biến kỹ thuật, nghi thức đầu/cuối phiên.
- `docs/PROJECT-STATE.md` — đang làm gì, trạng thái từng tính năng, rủi ro.
- `docs/HANDOFF.md` — nhật ký bàn giao; mục cuối là việc còn treo.
- `docs/DECISIONS.md` — quyết định không được phá + cách làm đã bị loại.
- `docs/ARCHITECTURE.md`, `docs/FEATURES.md` — luồng dữ liệu và bản đồ tính năng.
- `.opencode/skills/` — 11 skill theo tính năng, chỉ nạp khi đúng việc.

Kiểm tra tài liệu/skill/symbol có bị lệch code không:

```
C:\Users\ADMIN\miniforge3\python.exe tools\context_check.py
C:\Users\ADMIN\miniforge3\python.exe tools\context_check.py --snapshot
C:\Users\ADMIN\miniforge3\python.exe tools\smoke_test.py
```
