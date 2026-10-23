# ĐÁNH GIÁ DỰ ÁN CŨ & ĐỀ XUẤT PHASE 2 — LUYỆN PHÁT ÂM / PHÂN TÍCH ÂM VỊ

> Đối tượng đánh giá: `PHANTICHTIENGANH-main/` (Streamlit, ~1.105 dòng Python)
> Đích đến: Phase 2 của app `Audio → Text` v2.0 (Tkinter, một file `app.py`)
> Ngày: 22/10/2026

---

## 0. KẾT LUẬN NGẮN (đọc 60 giây)

| Câu hỏi | Trả lời |
|---|---|
| Dự án cũ có làm "phân tích âm vị" không? | **Không.** Nó so sánh *tín hiệu âm thanh* giữa 2 file, hoàn toàn không có khái niệm âm vị (phoneme), không có text mục tiêu, không có IPA, không align theo âm. |
| Vì sao kết quả chưa tốt? | 8 lỗi thiết kế (mục 2.2): so sánh 2 người khác nhau bằng MFCC/DTW, so cao độ tuyệt đối bằng Hz, formant không chuẩn hoá giới tính, gắn lỗi của **người bản xứ** lên đầu người học, ngưỡng toàn cục giả vờ là "lỗi từng từ", điểm không hiệu chuẩn. |
| Có nên chuyển toàn bộ sang? | **Không.** Chuyển toàn bộ = bê nguyên 8 lỗi đó vào app mới. Nên **giữ ~15–20% (ý tưởng + primitive DSP), viết lại phần chấm, xoá phần còn lại.** |
| Giá trị thật của dự án cũ | 3 thứ: (1) ý tưởng *vẽ* đường cao độ/cường độ sau khi warp thời gian, (2) ý tưởng *vẽ* không gian nguyên âm F1–F2, (3) vài đoạn code DSP ngắn. Tất cả đều phải sửa chuẩn hoá trước khi dùng. |
| Nội dung bài học chuyển được? | **0 dòng.** Dự án cũ không có bài học/âm mẫu; nội dung trong app mới (`GUIDES`, `PRACTICE_SETS`) đã nhiều và tốt hơn. |
| Phase 2 nên làm gì trước? | **2A (không thêm dependency nặng):** bài học có text + IPA + cặp tối thiểu, chấm theo từ/âm bằng ASR đã có, phân tích thanh điệu tiếng Việt bằng F0, vòng lặp "nghe → đọc → sửa → đọc lại", thống kê tiến bộ. **2B (tuỳ chọn):** GOP/forced-alignment cho tiếng Anh. |

---

## 1. DỰ ÁN CŨ GỒM NHỮNG GÌ

### 1.1. Kiến trúc

```
PHANTICHTIENGANH-main/
├── app.py                  462 dòng  Streamlit UI + toàn bộ luồng xử lý
├── core/
│   ├── audio_utils.py       27 dòng  librosa.load → 16 kHz mono + normalize
│   ├── acoustic.py          86 dòng  Praat: F0, intensity, formant F1/F2; librosa: mel-spec, MFCC; KMeans cụm nguyên âm
│   ├── aligner.py           70 dòng  Whisper word-timestamps + fastdtw trên MFCC + warp tín hiệu theo thời gian
│   ├── scoring.py           85 dòng  4 điểm: pitch / timbre / formant / rate → điểm tổng
│   ├── reporting.py        235 dòng  PDF A4 (fpdf + matplotlib): 6 chỉ số, danh sách lỗi, 3 biểu đồ
│   └── youtube_utils.py    140 dòng  yt-dlp tải audio + pydub cắt 1–10 phút + youtube-transcript-api
├── assets/DejaVuSerif.*             Font cho PDF
├── cookies.txt              9 KB    Cookie tài khoản YouTube (!)
├── requirements.txt          15 gói  (torch, openai-whisper, librosa, parselmouth, sklearn, fpdf…)
└── packages.txt                     ffmpeg (cho Streamlit Cloud)
```

### 1.2. Luồng hoạt động thực tế

```
[Nguồn mẫu]  upload file native  HOẶC  link YouTube (1–10 phút)  +  ghi âm bằng micro
      ↓
load_audio → 16 kHz mono
      ↓
AcousticFeatureExtractor × 2 (native & user):
   F0 (Praat) · intensity · F1/F2 · mel-spectrogram · MFCC(13) · KMeans(k=3) cụm nguyên âm
      ↓
Whisper("base") phiên âm **chỉ file native** → text + timestamp từng từ
      ↓
fastdtw(MFCC native, MFCC user) → đường warp → kéo giãn tín hiệu user theo thời gian native
      ↓
4 điểm: pitch (corr 70% + range 30%) · timbre (exp(-0.02·DTW)) · formant (lệch tâm /300 Hz) · rate
      ↓
Điểm tổng = 0.25·pitch + 0.35·timbre + 0.25·formant + 0.15·rate
      ↓
"Lỗi": nếu điểm toàn cục < ngưỡng → gắn lỗi lên các câu/từ (dùng timestamp của **native**)
      ↓
PDF 3 trang + 3 tab biểu đồ trên web
```

### 1.3. Đánh giá từng thành phần (một dòng)

| Thành phần | Có gì | Đánh giá |
|---|---|---|
| `audio_utils.py` | Chuẩn hoá 16 kHz mono | Đúng, nhưng app mới đã có `enhance_audio()` tốt hơn (khử DC, HPF, cắt im lặng, fade, chống vỡ). **Trùng lặp → bỏ.** |
| `acoustic.py` | F0, intensity, F1/F2, mel-spec, MFCC, KMeans | Primitive dùng được; **cách dùng thì sai** (xem 2.2). |
| `aligner.py` | DTW + warp | Ý tưởng đúng, **cài đặt sai đơn vị thời gian** (0.023 s vs 0.032 s thực tế). |
| `scoring.py` | 4 công thức điểm | **Không hiệu chuẩn, không có ground truth.** Đây là gốc của "kết quả chưa tốt". |
| `reporting.py` | PDF + 3 biểu đồ | Chết về sản phẩm: 3 trang biểu đồ tĩnh, lời khuyên soạn sẵn theo ngưỡng. |
| `youtube_utils.py` | Tải audio + script | Trùng chức năng app mới (đã tốt hơn), lại dùng `cookies.txt`. |
| `app.py` | Streamlit UI | Không cùng công nghệ với app mới; UI có 2 nút "phân tích" trùng nhau + text debug. |

### 1.4. Những gì dự án cũ **không** có

Đây là điểm quan trọng nhất khi đánh giá độ phù hợp:

- ❌ Không có **văn bản mục tiêu** (target text) → không biết người học có đọc đúng câu không.
- ❌ Không có **kho âm vị / IPA / phiên âm** → không thể nói "sai âm /θ/".
- ❌ Không có **cặp tối thiểu** (minimal pairs) → không luyện đối lập âm.
- ❌ Không có **lịch sử / tiến bộ** → mỗi lần chấm xong là hết.
- ❌ Không có **vòng lặp sửa** (retry, so sánh A/B, nghe chậm).
- ❌ Không có test, không có hiệu chuẩn, không có người dùng thật để đánh giá.

Nói cách khác: dự án cũ là **một bản demo DSP so sánh 2 tệp âm thanh**, được trình bày như một "AI Pronunciation Coach".

---

## 2. ĐÁNH GIÁ KỸ THUẬT SÂU

### 2.1. Những chỗ làm đúng (giữ lại tinh thần)

1. **Tách lớp rõ ràng**: feature → align → score → report. Cấu trúc này đúng và nên giữ khi viết lại.
2. **Chuẩn hoá đầu vào 16 kHz mono** trước mọi phép phân tích — đúng chuẩn cho Whisper và Praat.
3. **Warp theo thời gian trước khi so sánh** — đúng hướng: người học nói nhanh/chậm hơn mẫu là chuyện bình thường, phải căn chỉnh rồi mới so.
4. **Lọc formant theo cường độ và biên sinh lý** (F1 200–1200, F2 500–3500) — cần thiết, dù ngưỡng còn thô.
5. **Vẽ không gian nguyên âm F1–F2 với trục đảo** — đúng quy ước ngữ âm học.
6. **Có ý thức bảo mật cơ bản**: upload đổi tên bằng UUID (chống path traversal).

### 2.2. Tám lỗi thiết kế khiến kết quả không đáng tin

#### Lỗi 1 — So sánh hai con người khác nhau bằng MFCC/DTW rồi gọi là "chất giọng"

`scoring.py:36-48`:

```python
avg_dist = dtw_distance / path_length
score = 100 * np.exp(-0.02 * avg_dist)
```

MFCC mã hoá **đường bao phổ**, mà đường bao phổ phụ thuộc: nội dung phát âm **+ chiều dài ống thanh của từng người + micro + phòng**. Giữa nam và nữ, khoảng cách MFCC do khác kích thước thanh quản **luôn** lớn, dù phát âm chuẩn đến đâu. Hệ quả: nữ đọc mẫu giọng nam (hoặc ngược lại) gần như không thể vượt 80 điểm; đổi micro cũng đổi điểm.

Việc so sánh này chỉ có nghĩa khi **cùng một người, cùng micro, cùng câu** (đo tiến bộ), không có nghĩa khi so người học với người bản xứ.

#### Lỗi 2 — So cao độ tuyệt đối bằng Hz

`scoring.py:7-34` dùng `np.corrcoef(native_f0, user_f0)` trên Hz thô.

- F0 tuyệt đối phụ thuộc giới tính/độ tuổi: nữ ~200 Hz, nam ~110 Hz.
- Correlation của 2 đường lệch nhau 1 quãng tám vẫn có thể đúng hình dạng, nhưng nhiễu và range (`np.ptp`) thì lệch hoàn toàn → điểm range sụp.
- Đúng ra phải dùng **nửa cung (semitone) so với trung vị của chính người nói**, hoặc so *hình dạng contour đã chuẩn hoá*, không so Hz.

#### Lỗi 3 — Formant + KMeans(k=3) vừa vô nghĩa vừa không công bằng

`acoustic.py:62-83`: gom **toàn bộ** mẫu F1/F2 của cả câu thành 3 cụm, không biết cụm nào là /a/, /i/, /u/.

- Trong một câu bất kỳ, số nguyên âm khác nhau ≠ 3 và tỉ lệ xuất hiện khác nhau → cụm bị kéo lệch theo tần suất, không theo âm vị.
- `scoring.py:68`: `score = 100 - (avg_shift / 300 * 100)` — lệch 300 Hz = 0 điểm. Nhưng F1/F2 **khác nhau tự nhiên** giữa nam/nữ/trẻ em tới 20–30%. Không có chuẩn hoá chiều dài ống thanh (VTLN) thì phụ nữ so với mẫu nam luôn "sai khẩu hình".
- Formant của TTS (edge-tts) lại càng không đại diện cho người thật.

#### Lỗi 4 — Gắn lỗi của **người bản xứ** lên đầu người học

`app.py:303` chỉ phiên âm file **native**:

```python
transcript_text, segments = aligner.transcribe(n_path)
```

rồi `app.py:334` truyền `segments` đó vào `analyze_detailed_errors(...)`, trong đó:

```python
for w_data in seg.get('words', []):
    ...
    if overall_timbre_score < TIMBRE_THRESHOLD and len(clean_word) > 4:
        word_errors.append({'word': clean_word, 'start': w_start, ...})
```

Hệ quả: danh sách "từ cần cải thiện" là **các từ của người bản xứ**, ở **thời điểm của người bản xứ**, với điểm `overall_timbre - 5` (con số bịa). Người học chưa từng được phiên âm, nên app không biết họ đọc gì.

#### Lỗi 5 — Lỗi đơn vị thời gian trong warp (sai ~28%)

`aligner.py:30` mặc định `mfcc_frame_duration=0.023`, nhưng `librosa.feature.mfcc` dùng `hop_length=512` ở `sr=16000` → **0.032 s/frame**.

- Trục thời gian bị nén còn 72% so với thực tế.
- `interp1d(..., fill_value="extrapolate")` (dòng 49) sẽ **ngoại suy tuyến tính** cho ~28% cuối clip → đường user bị bóp méo đúng ở phần cuối, nơi thường chứa thông tin ngữ điệu kết câu.

#### Lỗi 6 — "Phát hiện lỗi" chỉ là ngưỡng toàn cục

`app.py:206-257`: nếu `overall_pitch_score < 75` thì **mọi câu dài > 1,5 s** bị đánh lỗi; nếu `overall_timbre < 80` thì **mọi từ dài > 4 ký tự** bị đánh lỗi (tối đa 8 từ). Lời khuyên là chuỗi soạn sẵn ("Phát âm chưa rõ nguyên âm hoặc phụ âm cuối") bất kể từ đó là gì.

Đây không phải phân tích âm vị; đây là **rải cùng một kết luận lên nhiều mốc thời gian**.

#### Lỗi 7 — Điểm số không hiệu chuẩn, không kiểm chứng

- `exp(-0.02·d)`: hằng số 0.02 do tác giả "giả sử".
- `0.7·corr + 0.3·range`, trọng số `25/35/25/15`, phạt `abs(rate_diff)*20`: tất cả tuỳ ý.
- Không có tập dữ liệu nào để trả lời: "điểm 75 có tương ứng với 'nghe được, hơi lỗi' không?"
- Hệ quả: người học **không thể tin** con số, và cũng **không biết nên sửa gì** — đúng như cảm nhận của bạn.

#### Lỗi 8 — Không có "đúng/sai nội dung"

Vì không có text mục tiêu, người đọc sai hẳn từ vẫn có thể được 85 điểm nếu âm sắc/ngữ điệu tình cờ giống. DTW còn "nuốt" luôn khác biệt nội dung: một câu khác nhưng cùng nhịp vẫn warp được.

### 2.3. Lỗi phụ (nhưng đáng nói vì gây cảm giác "dàn trải, chưa xong")

| Chỗ | Vấn đề |
|---|---|
| `app.py:79` và `app.py:191` | **Hai** nút "BẮT ĐẦU PHÂN TÍCH" ở 2 tab, cùng ghi vào `n_path/u_path` → dễ bấm sai, trạng thái chồng chéo. |
| `app.py:167-186` | Text debug lộ ra UI: "Báo cáo debug 1/2/3", "Đã lưu file tạm thành công tại…". |
| `app.py:173` | Ghi âm luôn vào **một tên cố định** `user_record_debug.wav` → 2 phiên Streamlit chạy song song sẽ ghi đè nhau. |
| Không có | Dọn `temp_upload/`, `temp_plot_*.png`, `AI_Report_*.pdf` → thư mục phình mãi. |
| `cookies.txt` | **Cookie tài khoản YouTube nằm trong repo** (9 KB). Rủi ro bảo mật; không bao giờ chuyển sang app mới. |
| `youtube_utils.py:81` | `format: 'best'` tải **cả video** rồi mới rút audio → chậm, tốn băng thông gấp nhiều lần. |
| `youtube_utils.py:36` | Chỉ lấy phụ đề tiếng Anh (`find_transcript(['en', …])`) → nội dung Việt/khác bị bỏ. |
| `requirements.txt` | Kéo `torch`, `torchaudio`, `openai-whisper` (~2,5 GB) cho một model `base`, trong khi app mới đã có `faster-whisper` nhẹ hơn nhiều. |
| `reporting.py:10-26` | `add_font` gọi lại trong `header()` **mỗi trang**; PDF là 3 trang biểu đồ tĩnh, không tương tác. |
| `aligner.py:63-75` | Đếm âm tiết bằng nhóm nguyên âm + trừ chữ "e" cuối → sai với "she sells seashells" và với tiếng Việt có dấu. |
| `acoustic.py:85-94` | `get_stats()` gọi lại `get_pitch_track()` + `get_intensity()`; `get_vowel_centroids()` gọi lại `get_formants()` → pitch/intensity/formant mỗi thứ tính 2 lần, chậm gấp đôi. |

---

## 3. VÌ SAO CẢM GIÁC LÀ "DÀN TRẢI MÀ KẾT QUẢ CHƯA TỐT"

Một app luyện phát âm cần **7 năng lực**. Dự án cũ phủ được 3, và 3 cái phủ được đều ở mức nửa vời:

| # | Năng lực | Dự án cũ | Ghi chú |
|---|---|---|---|
| 1 | Nội dung học (âm nào, mẫu nào, mẹo) | ⚠️ không có bài học, chỉ có câu PDF soạn sẵn | app mới đã có 5 guide |
| 2 | Nghe mẫu | ✅ YouTube / TTS | nhưng tải cả video, cần cookies |
| 3 | Ghi âm | ⚠️ có, nhưng nằm lẫn trong tab YouTube | không ghi âm được ở luồng upload |
| 4 | Biết **đúng/sai nội dung** | ❌ không có text mục tiêu | |
| 5 | Biết **sai âm nào** | ❌ chỉ là ngưỡng toàn cục | trái với tên "phân tích âm vị" |
| 6 | Biết **sửa thế nào** | ⚠️ lời khuyên soạn sẵn | không khớp với lỗi thật |
| 7 | Lặp lại & thấy tiến bộ | ❌ không có lịch sử | mỗi lần chấm là "một phát bắn tỉa" |

Vì thiếu (4) và (5), mọi thứ còn lại — biểu đồ, PDF, điểm số — chỉ trang trí cho một con số không có nghĩa. Đó chính xác là lý do "dàn trải nhiều khía cạnh nhưng kết quả chưa tốt": **càng nhiều chỉ số (pitch, timbre, formant, rate, spectrogram) thì càng khó biết chỉ số nào đáng tin, và không chỉ số nào được kiểm chứng.**

---

## 4. TÍNH PHÙ HỢP VỚI PHASE 2

### 4.1. Bảng quyết định: Giữ / Sửa / Bỏ / Viết lại

| Thành phần cũ | Quyết định | Lý do |
|---|---|---|
| **Ý tưởng warp thời gian rồi so contour** | ✅ **Giữ (ý tưởng)** | Đúng hướng, nhưng phải warp theo **từ** (word boundary) chứ không theo frame MFCC toàn clip; và so **semitone**, không so Hz. |
| **Ý tưởng biểu đồ không gian nguyên âm F1–F2** | ✅ **Giữ (ý tưởng)** | Chỉ dùng cho **nguyên âm mục tiêu đã biết** (1 âm/lần), kèm chuẩn hoá VTLN; chỉ hiển thị, **không chấm điểm**. |
| **Vẽ spectrogram A/B** | 🟡 **Giữ, hạ ưu tiên** | Hữu ích để "nhìn thấy" âm cuối/phụ âm xát; nhưng người học phổ thông không đọc được spectrogram → để tab "nâng cao". |
| `acoustic.py` (Praat/librosa primitives) | 🟡 **Viết lại** | Cần F0, intensity, formant, spectrogram — nhưng bỏ `sklearn`, bỏ KMeans; thêm chuẩn hoá semitone/VTLN; dùng numpy thuần để không kéo `librosa`+`numba` (~80 MB). |
| `aligner.py` (DTW MFCC) | ❌ **Bỏ cách làm** | Frame-level DTW trên cả clip là nguồn gốc của điểm "timbre" vô nghĩa. Thay bằng: timestamp từ ASR (đã có) + (tuỳ chọn) forced alignment theo âm vị. |
| `scoring.py` (4 điểm) | ❌ **Bỏ toàn bộ** | Không hiệu chuẩn, so sánh sai đối tượng. Thay bằng thang điểm 2 lớp (mục 5.2). |
| `reporting.py` (PDF) | 🟡 **Hoãn** | Không cần cho MVP. Nếu sau này cần, viết lại bằng matplotlib→PDF với nội dung do kết quả mới sinh ra, không dùng lời khuyên soạn sẵn. |
| `youtube_utils.py` | ❌ **Bỏ** | App mới đã có `yt-dlp` + phụ đề + ffmpeg tốt hơn, không cần `pydub`, không cần `youtube-transcript-api`, không cần cookies. |
| `audio_utils.py` | ❌ **Bỏ** | `enhance_audio()` + `resample_to()` trong `app.py` đã tốt hơn. |
| `app.py` (Streamlit) | ❌ **Bỏ** | Khác công nghệ; UI mới đã hoàn chỉnh. |
| `cookies.txt` | ❌ **Xoá ngay** | Bảo mật. Không chuyển, không backup vào repo mới. |
| `requirements.txt` cũ | ❌ **Không dùng** | Kéo torch/openai-whisper/librosa/sklearn không cần thiết. |
| Nội dung bài học | — | **Không có gì để chuyển**; app mới đã có `GUIDES` + `PRACTICE_SETS` tốt hơn. |

**Tỉ lệ chuyển thực tế: ~15% (ý tưởng) + ~150 dòng DSP viết lại; xoá ~900 dòng.**

### 4.2. Vì sao "chuyển toàn bộ" là sai

1. **Nhập luôn 8 lỗi thiết kế** vào một app đang chạy tốt.
2. **Nhân đôi dependency**: `torch` + `openai-whisper` bên cạnh `faster-whisper`; `librosa` + `parselmouth` cho những phép tính numpy làm được.
3. **Nhân đôi pipeline**: app mới đã chuẩn hoá 16 kHz, đã có ASR, đã có micro, đã có xuất file.
4. **Không tương thích UI**: Streamlit là web, app là desktop Tk; không "chuyển" được, chỉ có thể *viết lại* — mà viết lại thì nên viết đúng ngay từ đầu.

---

## 5. CÁCH CHUYỂN SANG DỰ ÁN MỚI

### 5.1. Nguyên tắc

> **Chuyển tri thức, không chuyển code.**
> Mỗi thành phần cũ phải trả lời được: *"Nó giúp người học biết mình sai âm nào và sửa thế nào?"* — nếu không, bỏ.

### 5.2. Kiến trúc Phase 2 (4 lớp)

```
┌─ L0. NỘI DUNG ────────────────────────────────────────────────┐
│ lessons.py / lessons.json                                    │
│  • text mục tiêu, IPA, âm trọng tâm, mẹo khẩu hình           │
│  • cặp tối thiểu, audio mẫu (thường + chậm)                  │
│  • nhóm: Âm đơn · Cặp tối thiểu · Câu · Tự do                │
└──────────────────────────────────────────────────────────────┘
                    ↓
┌─ L1. ĐÚNG/SAI NỘI DUNG (đã có, chỉ mở rộng) ─────────────────┐
│ ASR (faster-whisper) → word match (score_pronunciation)      │
│ + luật nhầm âm (flag_pair): n/l, th→t, s/sh, âm cuối…        │
│ + thanh điệu tiếng Việt (strip_tone_vi)                      │
│ → điểm "đọc đúng chữ" + danh sách từ cần sửa  ← TIN CẬY      │
└──────────────────────────────────────────────────────────────┘
                    ↓
┌─ L2. ÂM VỊ (mới — trái tim của Phase 2) ─────────────────────┐
│ Việt: luật hoá từ chính tả + tín hiệu                        │
│   • 6 thanh: phân loại contour F0 (ngang/huyền/sắc/hỏi/ngã/nặng)
│   • âm cuối: mũi (-m,-n,-ng,-nh) vs tắc (-p,-t,-c,-ch)       │
│   • cặp dễ lẫn: n/l, s/x, tr/ch, r/d/gi, v/d                 │
│ Anh: forced-alignment (tuỳ chọn 2B)                          │
│   • CMUdict/g2p → chuỗi âm vị mong đợi                       │
│   • wav2vec2-CTC + forced_align → posterior từng âm → GOP    │
│   • confusion: /θ/→[t], /ð/→[d], /s/→[ʃ], /æ/→[ɛ]…          │
│ → "âm yếu nhất" + "bạn đọc thành gì"  ← CHỈ KHI ĐỦ TIN CẬY  │
└──────────────────────────────────────────────────────────────┘
                    ↓
┌─ L3. NGỮ ĐIỆU & HÌNH ẢNH (tuỳ chọn, không chấm điểm) ────────┐
│ contour F0 theo semitone (chuẩn hoá theo trung vị người nói) │
│ intensity, spectrogram A/B, formant của nguyên âm mục tiêu   │
│ → chỉ để NHÌN, kèm chú thích; không quy ra điểm              │
└──────────────────────────────────────────────────────────────┘
                    ↓
┌─ L4. VÒNG HỌC & TIẾN BỘ ────────────────────────────────────┐
│ nghe mẫu (thường/chậm) → đọc → chấm → nghe lại A/B → đọc lại │
│ lịch sử: theo bài, theo âm, theo ngày                        │
│ "âm yếu nhất tuần này", streak, xuất CSV/TXT                 │
└──────────────────────────────────────────────────────────────┘
```

### 5.3. Nguyên tắc chấm điểm (để không lặp lại lỗi cũ)

1. **Chỉ chấm cái biết chắc.** Điểm chính = tỉ lệ từ đúng (ASR + luật). Đây là con số *giải thích được*: "bạn đọc 'think' thành 'tink'".
2. **Điểm âm vị chỉ hiện khi có bằng chứng.** Nếu ASR không nghe ra hoặc SNR thấp → "chưa đủ rõ, đọc lại gần mic", **không** bịa điểm.
3. **Không so tuyệt đối giữa hai người.** F0 → semitone so với trung vị; formant → chuẩn hoá VTLN; MFCC → chỉ dùng để so **cùng người, cùng micro, qua thời gian** (tiến bộ), không hiển thị như điểm phát âm.
4. **Mọi lời khuyên phải gắn với một lỗi cụ thể** (từ + âm + vị trí). Không có "ngữ điệu chưa tự nhiên" chung chung.
5. **Hiệu chuẩn trước khi công bố thang điểm.** Thu ~100 bản ghi, 2 giáo viên chấm 1–5, tính tương quan Spearman; chỉnh ngưỡng theo dữ liệu, không theo cảm tính.

### 5.4. Data model

`lessons.json` (tách khỏi code, dễ thêm bài):

```json
{
  "id": "en_th_01",
  "lang": "en",
  "group": "am-don",
  "text": "Think about this: three thousand thanks.",
  "ipa": "θɪŋk əˈbaʊt ðɪs θriː ˈθaʊzənd θæŋks",
  "focus": [
    {"ph": "θ", "words": ["think", "three", "thousand", "thanks"]},
    {"ph": "ð", "words": ["this"]}
  ],
  "tips": [
    "Đầu lưỡi giữa hai răng cửa, thổi hơi ra.",
    "Không rung dây thanh với /θ/, rung với /ð/."
  ],
  "pairs": [["think", "tink"], ["three", "tree"], ["thick", "tick"]],
  "samples": {"normal": "mau/en_th_01.wav", "slow": "mau/en_th_01_slow.wav"}
}
```

`history.json` (tiến bộ):

```json
{"attempts": [{
  "ts": "2026-10-22T08:10:00",
  "lesson": "en_th_01",
  "score": 86.5,
  "heard": "tink about this three thousand thanks",
  "errors": [
    {"word": "think", "heard": "tink", "ph": "θ", "got": "t", "conf": 0.82}
  ],
  "acoustic": {"f0_semitone": [[0.0, 0.0], [0.02, 1.5]], "snr_db": 24.1},
  "audio": "history/20261022_0810_en_th_01.wav"
}]}
```

### 5.5. Bảng migration chi tiết (file → file)

| File cũ | Dòng | Hành động | Đích trong app mới |
|---|---:|---|---|
| `app.py` | 462 | ❌ Xoá | UI đã có ở `app.py` tab 2 |
| `core/acoustic.py` | 86 | ✍️ Viết lại ~250 dòng numpy | `pron/dsp.py` — `pitch_yin()`, `semitone_contour()`, `intensity()`, `lpc_formants()`, `mel_spectrogram()` |
| `core/aligner.py` | 70 | ❌ Bỏ; giữ ý tưởng warp | `pron/prosody.py` — warp **theo từ** bằng timestamp ASR |
| `core/scoring.py` | 85 | ❌ Bỏ | `pron/score.py` — L1 (word match) + L2 (âm vị) |
| `core/reporting.py` | 235 | 🟡 Hoãn | `pron/report.py` (chỉ khi cần PDF) |
| `core/youtube_utils.py` | 140 | ❌ Bỏ | `app.py` đã có |
| `core/audio_utils.py` | 27 | ❌ Bỏ | `enhance_audio()` đã có |
| `assets/*` | — | ❌ Bỏ | chỉ giữ font nếu làm PDF |
| `cookies.txt` | 9 KB | ❌ **Xoá** | — |
| `requirements.txt` | 15 gói | ❌ Không dùng | xem 5.6 |

### 5.6. Dependency: hiện trạng & 3 lựa chọn

Môi trường hiện tại (đã kiểm tra):

```
✅ có: numpy 2.5.3 · faster-whisper 1.2.1 · yt-dlp · av
❌ chưa có: torch, torchaudio, openai-whisper, librosa, parselmouth,
            scikit-learn, fastdtw, scipy, soundfile, matplotlib, fpdf
```

| Phương án | Thêm gì | Dung lượng | Đánh giá |
|---|---|---:|---|
| **A. numpy thuần (khuyến nghị)** | không (hoặc `scipy` ~40 MB) | 0 | YIN/autocorr cho F0, LPC cho formant, mel-spec bằng FFT — ~300–400 dòng. Giữ app nhẹ, khởi động nhanh, không phụ thuộc mạng. |
| **B. Thêm onnxruntime + wav2vec2 CTC** (cho 2B) | `onnxruntime` + model ~95 MB | ~120 MB | GOP tiếng Anh không cần torch. Tải model 1 lần, chạy offline. |
| **C. Bê nguyên stack cũ** | torch, torchaudio, librosa, sklearn, parselmouth, openai-whisper | ~2,5 GB | ❌ Trùng lặp ASR, khởi động chậm, đóng gói nặng, kéo theo `numba/llvmlite`. Không nên. |

### 5.7. Lộ trình & ước lượng

| Giai đoạn | Nội dung | Ước lượng |
|---|---|---|
| **2A. MVP (không thêm dependency)** | `lessons.json` 24–30 bài (vi: n/l, s/x, tr/ch, r/d/gi, 6 thanh, âm cuối; en: θ/ð, s/ʃ, âm cuối, æ/ɛ, v/w); UI 3 cột; chấm L1 + luật; thanh điệu F0; nghe mẫu thường/chậm; A/B; lịch sử + "âm yếu nhất" | 4–6 ngày |
| **2A+. Hình ảnh** | contour semitone + intensity + spectrogram (numpy), formant cho nguyên âm mục tiêu | 1–2 ngày |
| **2B. Âm vị tiếng Anh** | onnxruntime + wav2vec2 CTC + CMUdict → GOP từng âm, confusion pair, độ tin cậy | 4–6 ngày |
| **Hiệu chuẩn** | thu ~100 bản ghi, 2 giáo viên chấm, chỉnh ngưỡng | 2 ngày |
| **Tổng** | | **~2–3 tuần** |

### 5.8. Tiêu chí nghiệm thu (định lượng, tránh "cảm giác")

- Đọc **đúng** câu mẫu 10/10 lần → điểm ≥ 90 và không báo lỗi âm vị.
- Đọc **sai 1 từ** (vd "think" → "tink") → phát hiện đúng từ đó, đúng âm /θ/, gợi ý khớp guide, ≥ 9/10 lần.
- Im lặng / mic hỏng / SNR thấp → **không** hiện điểm, hiện "chưa đủ rõ".
- Thời gian chấm 1 câu ≤ 3 s (model `base`, CPU).
- 20 lần thử liên tiếp: không crash, không rò rỉ file tạm.
- (2B) Trên 30 bản ghi có nhãn giáo viên: phát hiện đúng âm sai top-1 ≥ 70%, không quá 1 báo động giả/câu.

---

## 6. NHỮNG THỨ PHẢI TRÁNH (checklist khi viết Phase 2)

1. ❌ **Điểm "timbre" bằng DTW/MFCC giữa hai người** — phụ thuộc giới tính/micro, không phải phát âm.
2. ❌ **So F0 bằng Hz thô** — dùng semitone so với trung vị người nói.
3. ❌ **KMeans gom nguyên âm rồi so tâm cụm** — vô nghĩa khi không biết cụm là âm gì.
4. ❌ **Ngưỡng toàn cục rồi rải lỗi lên timestamp** — mỗi lỗi phải truy được về từ/âm cụ thể.
5. ❌ **Lấy transcript của file mẫu làm transcript của người học** — phải ASR chính bản ghi của người học.
6. ❌ **Hiển thị điểm khi không đủ dữ liệu** (im lặng, nhiễu, câu quá ngắn) — phải nói "chưa đủ rõ".
7. ❌ **Lời khuyên soạn sẵn theo ngưỡng** — lời khuyên phải sinh từ lỗi cụ thể.
8. ❌ **Nhiều chỉ số cùng lúc** (pitch + timbre + formant + rate + spectrogram) — chọn 1 điểm chính, còn lại là "xem thêm".
9. ❌ **Tải cả video YouTube để lấy 10 giây audio** — dùng `ba/b` (app mới đã đúng).
10. ❌ **Cookie/credential trong repo** — không bao giờ.
11. ❌ **Ghi file tạm vào thư mục chạy mà không dọn** — dùng `tempfile` + `finally`.
12. ❌ **Đưa text debug lên UI** — log kỹ thuật để ở panel Nhật ký (app mới đã có).
13. ❌ **So sánh âm học với giọng TTS** rồi kết luận về khẩu hình — TTS chỉ để *nghe mẫu*, không để *chấm điểm*.

---

## 7. ĐỀ XUẤT PHẠM VI MVP (Phase 2A)

Nếu chỉ được làm một vòng, tôi đề nghị đúng ngần này:

1. **Bài học có cấu trúc** (30 bài) thay cho 7 bộ câu hiện tại; mỗi bài: text, IPA, âm trọng tâm, 2–3 mẹo, 3 cặp tối thiểu, audio mẫu thường/chậm.
2. **Tab 2 thành 3 cột**: `Bài học | Thu âm | Kết quả` — bỏ kiểu "một cột dài" hiện tại.
3. **Chấm L1 nâng cấp**: giữ `score_pronunciation`, thêm hiển thị *theo âm* (chip màu: đúng / nghi sai / sai) dựa trên `flag_pair` mở rộng + âm cuối + thanh điệu.
4. **Thanh điệu tiếng Việt**: contour F0 6 thanh, so với mẫu cùng âm tiết, hiện "bạn đọc thanh sắc, mẫu là thanh huyền".
5. **Vòng lặp**: nghe mẫu → đọc → nghe lại A/B → "Thử lại" (giữ nguyên bài, xoá kết quả cũ).
6. **Tiến bộ**: đếm số lần đúng/sai theo từng âm, gợi ý "âm yếu nhất" ở đầu tab.
7. **Không** làm ở 2A: GOP, PDF, spectrogram, formant, YouTube trong tab luyện.

Sau khi 2A chạy ổn và có người dùng thật, mới quyết định 2B (GOP tiếng Anh) — vì 2B là nơi tốn kém nhất và cũng dễ "ảo giác chính xác" nhất.

---

## 8. RỦI RO & ĐIỂM CẦN BẠN QUYẾT

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| Kỳ vọng "AI chấm như giáo viên" | Cao | Chỉ công bố điểm từ bằng chứng; ghi rõ "tham khảo", kèm hướng dẫn nghe lại |
| Âm mẫu là TTS (edge-tts) | TB | Dùng TTS để *nghe*, không để *chấm*; thay dần bằng bản ghi người thật cho 20–30 bài cốt lõi |
| Tiếng Việt không có model âm vị | TB | Dùng luật chính tả + F0 (khả thi, giải thích được) thay vì cố dùng model tiếng Anh |
| Model 2B nặng, khó đóng gói | TB | `onnxruntime` + model tải lần đầu, có nút "cài gói phân tích chuyên sâu" |
| Thời gian | TB | 2A làm trước, độc lập hoàn toàn với 2B |

**Cần bạn quyết:**
1. Phase 2 ưu tiên **tiếng Việt** hay **tiếng Anh** trước? (nội dung và kỹ thuật khác nhau: vi = luật + thanh điệu; en = GOP)
2. Có chấp nhận **thêm ~120 MB** cho gói phân tích âm vị tiếng Anh (2B) không, hay giữ app thuần nhẹ?
3. Âm mẫu: tiếp tục dùng TTS, hay bạn thu/kiếm được **bản ghi người thật** cho ~20 bài cốt lõi?
4. Có cần **xuất PDF** như dự án cũ không, hay chỉ TXT/CSV là đủ?

---

## 9. TÓM TẮT MỘT CÂU

> Dự án cũ là một **máy đo độ giống tín hiệu**, không phải **máy chẩn đoán âm vị**; nó dàn trải vì cố đo 5 thứ cùng lúc mà không có cái nào được hiệu chuẩn, và nó gắn lỗi của người bản xứ lên người học. Phase 2 nên giữ **3 ý tưởng hình ảnh + 5 bài học**, viết lại toàn bộ phần chấm theo hướng "chỉ nói điều mình chứng minh được", và bắt đầu bằng **L1 (đúng/sai chữ) + thanh điệu + vòng lặp luyện** — đó là 80% giá trị với 20% công sức.
