# BẢN ĐỒ TÍNH NĂNG

Mỗi dòng trả lời: tính năng nằm ở đâu, ai chịu trách nhiệm, kiểm thử thế nào,
và skill nào cần nạp. Dùng file này thay vì grep toàn repo.

## 1. Chuyển văn bản (Tab 1)

| # | Tính năng | Hành vi người dùng | Code | Skill | Kiểm chứng |
|---|---|---|---|---|---|
| F1.1 | Chọn file | `Ctrl+O` hoặc `Chọn…`, nhận audio/video | `_pick_file`, `SUPPORTED` | `app-transcription` | mở file mp4/mp3, thấy tên |
| F1.2 | Nhận dạng file | bấm Bắt đầu → tiến trình → text + SRT | `_run`, `_w_file`, `load_model` | `app-transcription` | đọc 1 file ngắn, so text |
| F1.3 | Ghi âm 15 phút | nút thu → tự dừng → chuyển text | `Recorder`, `_rec_start`, `save_frames_wav` | `app-recording` | nói 3 s, im lặng 1,5 s → tự dừng |
| F1.4 | Hủy tác vụ | nút Hủy / `Esc` | `_cancel`, `_YtCancelled` | `app-transcription` | hủy giữa lúc nhận dạng, UI về idle |
| F1.5 | Xem trước Văn bản/SRT | nút ghép Văn bản \| Phụ đề SRT, chữ ≤ ~90 ký tự/dòng | `_render_preview`, `_stt_res_view`, `_on_result` | `app-transcription` | bật/tắt mốc thời gian |
| F1.6 | Xuất file | Copy / Lưu .txt / .srt / mở thư mục | `_copy`, `_save_txt`, `_save_srt`, `_open_folder` | `app-transcription` | lưu ra file, mở lại đúng UTF-8 |
| F1.7 | Nhật ký & tiến trình | tiến trình dưới ô nguồn; nhật ký thu gọn ở đáy cột phải (bấm để mở) | `_log`, `_pbar`, `_toggle_log`, `_poll` | `app-transcription` | thấy bước tải model/nhận dạng |
| F1.8 | Phím tắt | Ctrl+O/Ctrl+Enter/Ctrl+S/Esc | `__init__` binds | `app-ui` | thử từng phím |

## 2. YouTube (trong Tab 1)

| # | Tính năng | Hành vi | Code | Skill | Kiểm chứng |
|---|---|---|---|---|---|
| F2.1 | Dán link | chỉ nhận `http(s)` + `youtu` | `_run`, `_paste_url` | `app-youtube` | link sai → cảnh báo |
| F2.2 | Chế độ chỉ transcript | tải phụ đề, không tải video | `_w_yt` nhánh `subs` | `app-youtube` | video có phụ đề → không tải mp4 |
| F2.3 | Chế độ video/audio | tải + ghép + tạo phụ đề | `yt_build_opts` | `app-youtube` | thấy mp4/mp3 trong thư mục |
| F2.4 | Chọn phụ đề | auto/vi/en, thủ công trước tự động | `pick_subtitle_source` | `app-youtube` | log đúng ngôn ngữ + nguồn |
| F2.5 | Fallback Whisper | không có phụ đề → ASR | `_w_whisper_cues` | `app-youtube` | video không phụ đề vẫn ra SRT |
| F2.6 | Nhúng phụ đề mềm | checkbox → ffmpeg `-c copy` | `mux_subtitles_into_video` | `app-youtube` | VLC bật/tắt phụ đề |
| F2.7 | Ghi .srt/.txt cạnh video | tên theo tiêu đề + id | `safe_stem`, `cues_to_srt/txt` | `app-youtube` | so format SRT chuẩn |

## 3. Luyện phát âm (Tab 2)

| # | Tính năng | Hành vi | Code | Skill | Kiểm chứng |
|---|---|---|---|---|---|
| F3.1 | Chọn bài | combobox 18 mục | `PRACTICE_SETS`, `SET_IDS` | `app-lessons` | đủ 3 Việt + 14 Anh + Tùy chỉnh |
| F3.2 | Học âm | 5 guide N/L/TH/SH | `GUIDES` | `app-lessons` | hiện hướng dẫn khẩu hình |
| F3.3 | Nghe mẫu | nút ▶ thường/chậm/từ khóa | `_fill_samples`, `play_wav_file` | `app-lessons` | nghe được, nút xám nếu thiếu file |
| F3.4 | Thu & tự chấm | đọc → tự dừng → điểm | `_prac_start`, `_prac_stop_and_score` | `app-recording`, `app-pronunciation` | đọc đúng → ~100% |
| F3.5 | Chấm file có sẵn | `Chấm file…` | `_prac_from_file` | `app-pronunciation` | file im lặng → từ chối chấm |
| F3.6 | Điểm theo từ | vòng điểm "c/t từ" + chip ✓/!/✕ kèm từ máy nghe | `score_pronunciation`, `build_result_view`, `App._render_result` | `app-pronunciation` | "think"→ chip "! think → nghe ‘tink’" |
| F3.7 | Lỗi thanh điệu / vần | thẻ "sai dấu thanh" / "sai vần/dấu" + cách đọc tách | `strip_tone_vi`, `strip_marks_vi`, `vi_north_key`, `vi_spell` | `app-pronunciation` | "má"→"ma" tone; "lắm"→"lám" rhyme |
| F3.7b | Máy chưa nghe rõ | không hiện điểm khi máy không chắc/bịa câu (D-29) | `evidence_gate` | `app-pronunciation` | hyp "cảm ơn các bạn đã theo dõi" → "Máy chưa nghe rõ bài đọc" |
| F3.8 | Âm vị CMUdict | `/θ/ → [t]` + mẹo | `pron_en.analyze_pairs` | `app-phonemes` | câu th → báo TH |
| F3.9 | GOP acoustic | mức "lệch rõ"/"hơi lệch"; số trong "Chi tiết số đo" | `gop.score`, `gop_level` | `app-phonemes` | có torch → log "chấm GOP" |
| F3.10 | Ngữ điệu | một câu nhận xét + đồ thị có nhãn từ (không trục số) | `prosody.compare`, `inton_view`, `_draw_intonation` | `app-prosody` | bài Anh có mẫu → "Cuối câu bạn … giống mẫu ✓" |
| F3.10b | Trọng âm + tốc độ | chấm nhấn bạn/mẫu, "Mẫu nhấn …, bạn nhấn …", "Bạn đọc chậm hơn mẫu ~x %" — không điểm | `prosody.word_stress`, `stress_note`, `speed_note`, `mau/en/word_times.json` | `app-prosody` | bài Anh → có câu trọng âm + tốc độ |
| F3.11 | Tiến bộ | đường xu hướng ≤ 10 lần + "tốt nhất c/t" + âm hay sai theo ngôn ngữ | `progress_summary`, `_update_prog`, `_draw_spark` | `app-pronunciation` | luyện 2 lần → hiện đường xu hướng |
| F3.13 | Đọc to transcript YouTube (D-39) | link → đoạn 20–45 s → nghe gốc/đọc → đoạn tô màu, "phụ đề có thể sai" không tính | `ytread_prepare`, `ytread_orig_hyp`, `read_aloud_diff`, `ytread_view`, `App._yt_*` | `app-youtube`, `app-pronunciation` | `tools/ytread_e2e.py <link>` đọc = audio gốc → "Hoàn hảo" |
| F3.14 | Trôi chảy + từng câu (D-40 R1) | tốc độ, từ/hơi, ngừng giữa cụm "/" , ▶ Mẫu/▶ Bạn đọc mỗi câu | `fluency_view`, `yt_read.sentence_ranges`, `App._yt_render` | `app-prosody` | `tools/ytread_e2e.py` in "trôi chảy: …" |
| F3.15 | Lưu bản thu | x.wav + x.txt + x.json (+ x_goc.wav) | `App._save_recording` | `app-recording` | lưu rồi `asr_bench --dir` đọc được |
| F3.12 | Mic & kiểm tra | chọn, làm mới, kiểm tra | `_refresh_mics`, `_test_mic`, `_find_mic_auto` | `app-recording` | nói "a" → dB/TỐT |

## 4. Cài đặt & nền tảng (Tab 3)

| # | Tính năng | Hành vi | Code | Skill | Kiểm chứng |
|---|---|---|---|---|---|
| F4.1 | Model/ngôn ngữ dùng chung | **chỉ** ở chân thanh điều hướng (menu có mô tả model, V-14) | `self.model_name`, `self.lang`, `App._model_menu`, `MODEL_DESC` | `app-ui` | đổi → áp cho cả 2 màn hình |
| F4.2 | Thư mục lưu | chọn, mặc định `downloads/` | `out_dir`, `_pick_out_dir` | `app-ui` | lưu video đúng chỗ |
| F4.3 | Theme sáng/tối | đổi ngay, nhớ khi mở lại | `THEMES`, `_apply_theme` | `app-ui` | khởi động lại vẫn đúng |
| F4.4 | DPI scaling | 100–250% không bóp chữ | `self.S`, `px()` | `app-ui` | đổi scaling Windows 150% |
| F4.5 | Lưu/mặc định | lưu ngay khi đổi (`_autosave`, 0,4 s) + "Khôi phục mặc định" | `_cfg_from_vars`, `_save_cfg`, `_autosave`, `_reset_cfg` | `app-ui` | đổi công tắc → đóng/mở app vẫn giữ |
| F4.6 | Thông tin phiên bản/thư viện | Cài đặt › Giới thiệu | `_fill_info` | `app-qa-release` | hiện đúng có/không |
| F4.7 | Kích thước cửa sổ | nhớ geometry | `_on_close`, `geometry` | `app-ui` | mở lại đúng kích thước |

## 5. Nội dung & dữ liệu

| # | Thành phần | Nguồn | Sinh lại | Skill |
|---|---|---|---|---|
| F5.1 | 14 bài tiếng Anh | `lessons_en.json` | `tools/build_lessons.py --force` | `app-lessons` |
| F5.2 | 74 clip bài Anh | `mau/en/` | `tools/build_lessons.py --force` | `app-lessons` |
| F5.3 | 12 clip Việt/Anh cơ bản | `mau/` | `gen_mau.py --force` | `app-lessons` |
| F5.4 | Lịch sử luyện | `practice_history.json` | tự tạo | `app-pronunciation` |
| F5.5 | Cài đặt | `config.json` | tự tạo | `app-ui` |

## 6. Việc chưa có (đừng giả định là có)

- Không có test framework, không có CI, không có git.
- Không có phân loại 6 thanh tiếng Việt bằng F0 (chỉ so chữ).
- Không có chip lỗi theo âm vị cho tiếng Việt.
- Không có bài học tiếng Việt có cấu trúc (IPA/mẹo/cặp tối thiểu) như tiếng Anh.
- Không có xuất PDF/CSV lịch sử.
- Không có spectrogram/formant.
- Không có hàng đợi nhiều file (mỗi lần một file).
- Không có chế độ dùng GPU.
- Không có đóng gói `.exe`, icon, installer.

Danh sách này là nguồn cho roadmap; khi làm xong, chuyển sang bảng trên và cập nhật
`docs/PROJECT-STATE.md`.
