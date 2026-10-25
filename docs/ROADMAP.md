# LỘ TRÌNH

Nguồn gốc: `PHASE2-DANH-GIA-DU-AN-CU.md` (đánh giá dự án cũ + đề xuất Phase 2)
đối chiếu với code hiện tại; cập nhật 2026-10-25 theo buổi đánh giá "góc nhìn người
học tiếng Anh" + rà hạ tầng âm thanh, và quyết định tách sản phẩm (D-49). Roadmap này
**không** lặp lại lý thuyết; chỉ nói thứ tự, phạm vi, tiêu chí xong.

## Nguyên tắc thứ tự

1. **An toàn trước:** có lưới test + context trước khi thêm tính năng.
2. **Giá trị người học trước:** đúng/sai chữ + vòng lặp luyện + tiến bộ.
3. **Chỉ công bố điều chứng minh được:** không thêm điểm khi chưa hiệu chuẩn.
   Việc **không sinh điểm mới** (nội dung, nghe phân biệt, ôn tập, nghe-nhắc lại) làm
   trước; việc sinh điểm/"trình độ" mới chờ dữ liệu P4.
4. **Oriole chỉ dành cho người Việt học tiếng Anh (D-49).** Phần luyện tiếng Việt
   (N/L, thanh điệu) chuyển sang app riêng — xem phase **S**. Q-01 đã đóng.

## Thứ tự đề xuất

| # | Việc | Vì sao trước |
|---|---|---|
| 1 | **S1–S2** chốt điểm tách + tạo app tiếng Việt | Oriole không xóa gì cho tới khi app mới chạy |
| 2 | **A1–A4** sửa nhanh âm thanh (mẫu 24 kHz, cắt đuôi, tanh, cảnh báo bluetooth) | rẻ, người học nghe/thu tốt hơn ngay |
| 3 | **P1 + A12** lưới test + CI | trước khi xóa phần Việt và thêm tính năng |
| 4 | **S3** gỡ phần tiếng Việt khỏi Oriole | sau khi app mới chạy được |
| 5 | **L2** thêm câu mỗi bài + nghe phân biệt cặp tối thiểu | không rủi ro chấm |
| 6 | **L1** ôn tập hằng ngày từ lỗi của chính mình | giá trị lớn nhất |
| 7 | **A10 + P4** thu dữ liệu thật + hiệu chuẩn | mở khóa L3, L6, ngưỡng |
| 8 | **L3 + A9** chống Whisper "sửa hộ", GOP gọn | cần dữ liệu P4 |
| 9 | **L4, L5, A5–A8** | trải nghiệm luyện |
| 10 | **L6**, **P7** đóng gói | cuối cùng |

## P0 — Nền vận hành (đã xong 2026-10-22)

- [x] `AGENTS.md`, `docs/*`, bộ 11 skills, `context-map.json`.
- [x] `tools/context_check.py` + `tools/smoke_test.py`.
- [x] Ghi lại bất biến và các cách làm bị loại.

**Xong khi:** model mới đọc 3 file là tiếp tục được; check chạy PASS.

## P1 — Lưới an toàn (1–2 ngày)

- [ ] Mở rộng `tools/smoke_test.py`: case cho `score_pronunciation` tiếng Anh
      (th, s/sh, âm cuối, từ thừa/thiếu), `cues_to_srt`, `_fix_cues`,
      `split_long_cues`, `enhance_audio`, `resample_to_16k`.
- [ ] Fixture SRT/VTT/json3 trong `tools/fixtures/`.
- [ ] Test `lessons_en.json`: id duy nhất, đủ `target/words/tips/pairs`,
      audio `mau/en/<id>.wav` + `_slow.wav` tồn tại.
- [ ] `py_compile` toàn bộ trong check.

**Xong khi:** `smoke_test.py` chạy < 10 s, không cần mạng/mic/model; CI (A12) chạy nó.

## S — Tách sản phẩm: Oriole = tiếng Anh, luyện tiếng Việt sang app riêng (D-49)

Nguyên tắc: **tạo app mới trước, gỡ khỏi Oriole sau**; mỗi bước một commit, chạy
`py_compile` + `smoke_test` + `context_check` + mở app sau mỗi commit. Không xóa dữ liệu
người học.

- [ ] **S1 — Chốt điểm tách.** Oriole: smoke + context PASS, `git tag split-base-vi`,
      ghi hash vào D-49. Người dùng tạo repo GitHub riêng tư cho app mới (tên: Q-06).
- [ ] **S2 — Dựng app tiếng Việt từ bản sao có lịch sử** (`git clone` Oriole → repo mới,
      đổi `origin`; không copy thư mục — tránh mang theo `learners.json`/`config.json`/
      `sound calibrate/`):
  1. Đổi danh tính trước khi xóa: `APP_TITLE`, icon, `recordings_dir()` (đang
     `Documents\Oriole`), tên `config.json`/`learners.json` → hai app cùng máy không ghi đè.
  2. Gỡ tiếng Anh theo thứ tự **người gọi trước, module sau**: bài `en*` + `lessons_en.json`
     + `mau/en/` + `tools/build_lessons.py` → nhánh EN trong kết quả → `pron_en.py` +
     `cmudict` → `gop.py` + torch → tính năng YouTube tiếng Anh (`yt_read.en_tokens`, nhịp,
     nối âm, nhấn) → tab Chuyển văn bản nếu không cần. Test EN xóa **cùng commit** với tính năng.
  3. Viết lại `AGENTS.md`, `DECISIONS.md` (D-01: tách từ Oriole @hash, giữ bất biến còn áp
     dụng), `context-map.json`, bỏ skill `app-phonemes`; thêm `docs/UPSTREAM.md` liệt kê hàm
     dùng chung (thu âm, resample, enhance, mic, Whisper, evidence gate, hồ sơ người học).
  4. Lộ trình riêng của app mới: thanh điệu bằng F0 (P3 cũ, chuyển sang đây), bài có cấu
     trúc n/l, s/x, tr/ch, r/d/gi, âm cuối; chuẩn giọng Bắc/Nam (D-38 cần cờ theo bài).
- [ ] **S3 — Gỡ phần tiếng Việt khỏi Oriole** (chỉ sau khi S2 chạy được):
  1. Danh sách bài: bỏ `vi1–vi3`, `_VI_IDS`; Học âm bỏ `n`, `l`, `nl` (giữ `th`, `sh`);
     Tùy chỉnh chỉ nhận câu tiếng Anh.
  2. Chấm: bỏ nhánh `lang == "vi"` trong `score_pronunciation`/`flag_pair`/`build_result_view`,
     `strip_tone_vi`, `strip_marks_vi`, `vi_north_key`, `vi_spell`, `_vi_cards`, `_VI_TIPS`,
     `VI_SOUND_CODES`, `PRAC_VI_MODEL` (nhánh Việt của `practice_model`).
  3. Dữ liệu: bỏ `mau/vi_*.wav` + clip Việt trong `gen_mau.py`. `learners.json` **giữ nguyên**
     mục `vi*` cũ — màn Tiến bộ chỉ bỏ qua id không còn bài (không xóa dữ liệu).
  4. Test: bỏ `nl_confusion_flagged`, `vietnamese_tone_flagged`, `northern_accent_is_correct`,
     `tone_strip_keeps_letters`, `vietnamese_practice_uses_small_when_on_disk`,
     `result_view_vietnamese_counts_by_lesson_language`, `vietnamese_rhyme_state_named`,
     `vi_spell_splits_syllable` cùng commit với code; không nới test của phần giữ lại.
  5. Tài liệu: README, FEATURES, skill `app-pronunciation`/`app-lessons`, bất biến liên quan.
  6. **Giữ** (Oriole vẫn cần): giao diện tiếng Việt, font Be Vietnam Pro, chữ tiếng Việt
     trong `evidence_gate` (Whisper bịa câu Việt cả trên bản đọc tiếng Anh), tab Chuyển
     văn bản đa ngôn ngữ (chờ Q-05).
- [ ] **S4 — Sửa lỗi phần dùng chung giữa hai app:** thêm Oriole làm remote thứ hai ở app mới,
      chuyển bản sửa bằng `git cherry-pick <sha>`; chưa tách gói `audio_core` chung cho tới khi
      hai app ổn định (AGENTS §8).

**Xong khi:** app tiếng Việt tự chạy được bài N/L + Học âm N/L; Oriole không còn bài/luật
tiếng Việt, smoke + context PASS ở cả hai repo; dữ liệu người học cũ không mất.

## L — Trải nghiệm người học tiếng Anh (đánh giá 2026-10-25)

- [ ] **L1 — Ôn tập hằng ngày từ lỗi của chính mình.** Gom từ sai + âm yếu từ bài câu và
      buổi YouTube vào hàng ôn theo người học (`learners.json`), giãn cách 1 → 3 → 7 ngày;
      mở app thấy "Hôm nay: 8 từ, 2 âm, ~5 phút". Chỉ thêm khi `evidence_gate` qua; người học
      bỏ được mục. *Xong khi:* một tuần dùng thật, hàng ôn không đầy rác do máy nghe nhầm.
- [ ] **L2 — Thêm nội dung + nghe phân biệt.** 4–6 câu mỗi bài, đặt âm trọng tâm ở đầu/giữa/
      cuối từ, chọn ngẫu nhiên. Bài nghe "bạn nghe từ nào?" với cặp tối thiểu **từ thật**
      (ship/sheep, sin/sing, vest/west, light/right) — không cần mic, không chấm phát âm.
      `pairs` hiện chỉ hiện chữ (`load_en_lessons`). *Xong khi:* mỗi bài ≥ 4 câu + ≥ 3 cặp nghe.
- [ ] **L3 — Chống Whisper "sửa hộ" + làm rõ khi không có GOP.** (a) thử `initial_prompt`
      chứa cả từ đúng lẫn lỗi dự kiến **chỉ** cho bài từ đơn/câu ngắn, đo báo động giả bằng
      `asr_bench` (cân nhắc với I2 — ghi D mới nếu dùng); (b) UI ghi "chỉ kiểm tra theo từ, chưa
      kiểm tra âm" khi GOP tắt; (c) cài GOP thành bước rõ ràng (A9). Chờ P4 trước khi gọi là điểm.
- [ ] **L4 — Nghe-nhắc lại → nhại theo (shadowing) cho YouTube.** Trước: "nhắc lại sau mẫu" (đọc
      trong khoảng ngừng sau từng câu, không cần tai nghe). Sau: nói cùng lúc với audio gốc —
      cần tai nghe có dây (tiếng loa lọt mic; bluetooth HFP — A3).
- [ ] **L5 — Luyện hẹp + phản hồi gọn.** (a) Sửa một từ: đọc riêng từ ×3 rồi ghép lại câu; cần
      ngưỡng `evidence_gate` riêng cho 1 từ. (b) Từ YouTube mỗi đoạn hiện **một** điểm chính, phần
      còn lại trong "Xem chi tiết"; chế độ Cơ bản/Nâng cao theo hồ sơ người học.
- [ ] **L6 — Tính năng mới sau P4:** (a) trọng âm từ nhiều âm tiết (PHOtograph/phoTOgraphy) —
      dạy + nghe trước, không chấm (như D-46), dùng dấu nhấn CMUdict; (b) nghe-chép chính tả
      đoạn YouTube trước khi đọc (so chữ gõ với phụ đề, không cần mic); (c) bài chẩn đoán đầu
      vào 10 câu → "3 âm yếu nhất, bắt đầu từ bài X, Y, Z" — ghi "gợi ý", không phải "trình độ".

## A — Hạ tầng âm thanh, nhận dạng, kỹ thuật (rà soát 2026-10-25)

Mọi thay đổi chuỗi thu/nhận dạng đo trước/sau bằng `tools/asr_bench.py --compare` (D-36).

Âm người học nghe:
- [ ] **A1 — Âm mẫu 24 kHz để nghe.** `mau/` hiện 16 kHz mono → mất mọi thứ > 8 kHz (vùng
      phân biệt /s/–/ʃ/, /θ/–/f/). Giữ bản 24 kHz (edge-tts xuất 24 kHz) cho nút ▶; Whisper/GOP/
      `word_times` dùng bản 16 kHz như cũ. Sửa `tools/build_lessons.py`, `gen_mau.py`.
- [ ] **A2 — Thêm giọng mẫu.** ≥ 1 giọng nam và 1 giọng Anh-Anh (TTS); bản chậm cân nhắc đọc
      chậm có ngắt thay vì chỉ giảm `rate`. Bản ghi người thật cho 14 câu bài chờ Q-03.
- [ ] **A3 — Cảnh báo mic bluetooth (HFP).** Khi mic đang chọn là tai nghe bluetooth: một dòng
      "mic bluetooth làm giảm chất lượng cả tiếng nghe — nên dùng mic có dây/mic laptop".

Chất lượng thu:
- [ ] **A4 — Cắt im lặng không nuốt âm cuối.** `enhance_audio` cắt ở `max(0,015; 4 % đỉnh)` +
      80 ms; /s/, /t/ bật hơi cuối nhỏ hơn mức đó → bị cắt trước khi Whisper nghe (bài
      `en_final`, `en_plural`, `en_cluster`). Nới đuôi ~250 ms hoặc dò theo năng lượng dải cao.
      Cùng đợt: chỉ soft-clip (`tanh`) khi > ~0,9 thay vì mọi mẫu.
- [ ] **A5 — "▶ Bạn đọc" phát bản thu gốc.** Giữ bản tần số gốc (chưa high-pass/gain/cắt) để
      nghe lại; bản 16 kHz đã xử lý chỉ để chấm. Xóa cả hai trong `finally` (I10).
- [ ] **A6 — Kiểm tra mic 5 giây trước buổi đầu.** Đọc một câu → mức, ồn (SNR), vỡ tiếng +
      một lời khuyên cụ thể. Không thêm khử ồn (mất dải cao GOP/Whisper cần; I8).

Nhận dạng & chấm:
- [ ] **A7 — Thời gian chờ.** Nạp model nền khi mở app; đo `large-v3-turbo`/`distil` qua
      faster-whisper so với `medium` (D-41) bằng `asr_bench`/`ytread_bench`. Mục tiêu ≤ 3 s/câu.
- [ ] **A8 — Đo độ trễ thật trong app** (log thời gian chấm mỗi lần vào Nhật ký) để biết A7 có tác dụng.
- [ ] **A9 — GOP gọn (thay P6 cũ).** `onnxruntime` + model int8 thay `torch` (~4× nhỏ/nhanh hơn);
      nút "Cài gói phân tích âm" + tiến trình tải; hiệu chuẩn GOP trên bản ghi có nhãn; hiện độ
      tin cậy, ẩn kết luận khi thiếu bằng chứng. Cần Q-02.
      *Xong khi:* top-1 phát hiện âm sai ≥ 70 % trên 30 bản ghi có nhãn; ≤ 1 báo động giả/câu.
- [ ] **A10 — Thu dữ liệu thật (tự nguyện).** Tùy chọn "lưu lần thử này để hiệu chuẩn": wav +
      câu đích + kết quả + model vào thư mục cục bộ (không mạng, .gitignore — I16); đọc được
      bằng `asr_bench --dir`. Nguồn dữ liệu cho P4.

Kỹ thuật:
- [ ] **A11 — Sửa drift tài liệu:** `PROJECT-STATE` ghi `app.py` ~4.500 dòng (thực tế ~8.700);
      `FEATURES §6` còn "không có git".
- [ ] **A12 — CI:** GitHub Action chạy `py_compile` + `smoke_test.py` + `context_check.py` mỗi lần push.

## P2 — Hoàn thiện màn Luyện (phần còn lại)

- [ ] Vòng lặp: nghe mẫu → đọc → nghe lại A/B → "Thử lại" (giữ bài, xóa kết quả).
- [ ] "Âm yếu nhất" theo tuần + đếm theo âm (đã có nền `hist["ph"]`) — nhập vào L1.
- [ ] Phase 4 UI-PLAN: người dùng thử tay (file, YouTube, ghi âm 15 phút, Esc, tối, cửa sổ
      nhỏ, scaling 100/150 %), rồi Phase 5 (đóng gói tài liệu).
- [ ] Không thêm dependency nặng.

**Xong khi:** người học làm trọn một bài mà không cần hướng dẫn ngoài; mọi lỗi
hiển thị đều truy được về từ + âm + mẹo.

## P5 — Đọc to transcript YouTube tiếng Anh (D-39)

- [x] Y1–Y3, R1–R6 (D-40…D-48). Chi tiết: `docs/YT-READING-PLAN.md`.
- [ ] Còn ngỏ: nuốt âm (elision), xóa người học, so lần đọc lại cùng đoạn.

## P3 — Thanh điệu tiếng Việt bằng F0 → chuyển sang app tiếng Việt (D-49)

Không làm trong Oriole. Nội dung giữ nguyên làm điểm khởi đầu cho lộ trình app mới (S2.4):
phân loại 6 thanh từ `prosody.f0_track`, so mẫu cùng âm tiết, chỉ kết luận khi đủ voiced
frames + SNR; *xong khi* phân loại đúng ≥ 80 % trên 20 bản ghi tự thu.

## P4 — Hiệu chuẩn (2 ngày + dữ liệu)

- [ ] Thu ~100 bản ghi tiếng Anh (10 câu × 10 người hoặc 20 câu × 5) — dùng A10.
- [ ] 2 giáo viên chấm độc lập 1–5.
- [ ] Tính Spearman giữa điểm app và điểm người; chỉnh ngưỡng theo dữ liệu
      (`evidence_gate`, `WORD_UNSURE_P`, `SNR_LOW_DB`, GOP).
- [ ] Ghi báo cáo vào `docs/CALIBRATION.md` (kể cả kết quả xấu).

**Xong khi:** có báo cáo công khai, nêu rõ giới hạn; không chỉnh ngưỡng bằng cảm tính.

## P7 — Đóng gói & vận hành (2–3 ngày)

- [x] git + `.gitignore` (D-33).
- [ ] Bỏ phụ thuộc đường dẫn cứng `C:\Users\ADMIN\miniforge3`; script cài kiểm tra dependency.
- [ ] Đóng gói `.exe` (PyInstaller) **hoặc** bản portable kèm Python.
- [ ] Icon, phiên bản, thông báo cập nhật thủ công.
- [ ] Backup/restore `config.json`, `learners.json`.

**Xong khi:** máy Windows sạch chạy được bằng 1 lần double-click; gỡ sạch không để lại rác.

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
- Khử ồn trước khi chấm (mất dải cao; A6).
- PDF nhiều trang biểu đồ (chờ Q-04).
- Tải video để lấy audio ngắn (R-09).
- API đám mây/đăng nhập/tài khoản.
- Bài luyện tiếng Việt trong Oriole (D-49).
