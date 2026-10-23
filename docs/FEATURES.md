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
| F1.5 | Xem trước Văn bản/SRT | 2 tab trong panel phải | `_render_preview`, `_on_result` | `app-transcription` | bật/tắt mốc thời gian |
| F1.6 | Xuất file | Copy / Lưu .txt / .srt / mở thư mục | `_copy`, `_save_txt`, `_save_srt`, `_open_folder` | `app-transcription` | lưu ra file, mở lại đúng UTF-8 |
| F1.7 | Nhật ký & tiến trình | log từng bước + progressbar | `_log`, `_pbar`, `_poll` | `app-transcription` | thấy bước tải model/nhận dạng |
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
| F3.6 | Điểm theo từ | xanh/đỏ/cam | `score_pronunciation`, `_prac_done` | `app-pronunciation` | "think"→"tink" tô cam |
| F3.7 | Lỗi thanh điệu | "sai thanh điệu" | `strip_tone_vi` trong `score_pronunciation` | `app-pronunciation` | "má" vs "ma" → tone |
| F3.8 | Âm vị CMUdict | `/θ/ → [t]` + mẹo | `pron_en.analyze_pairs` | `app-phonemes` | câu th → báo TH |
| F3.9 | GOP acoustic | % khớp, so mẫu | `gop.score` | `app-phonemes` | có torch → log "chấm GOP" |
| F3.10 | Ngữ điệu | đồ thị F0 bán cung | `prosody.compare`, `_show_intonation` | `app-prosody` | bài có mẫu → hiện canvas |
| F3.11 | Tiến bộ | số lần/best/last/âm yếu | `_update_prog`, `_record_hist` | `app-pronunciation` | luyện 2 lần → n=2 |
| F3.12 | Mic & kiểm tra | chọn, làm mới, kiểm tra | `_refresh_mics`, `_test_mic`, `_find_mic_auto` | `app-recording` | nói "a" → dB/TỐT |

## 4. Cài đặt & nền tảng (Tab 3)

| # | Tính năng | Hành vi | Code | Skill | Kiểm chứng |
|---|---|---|---|---|---|
| F4.1 | Model/ngôn ngữ dùng chung | thanh trên + tab 3 | `self.model_name`, `self.lang` | `app-ui` | đổi → áp cho cả 2 tab |
| F4.2 | Thư mục lưu | chọn, mặc định `downloads/` | `out_dir`, `_pick_out_dir` | `app-ui` | lưu video đúng chỗ |
| F4.3 | Theme sáng/tối | đổi ngay, nhớ khi mở lại | `THEMES`, `_apply_theme` | `app-ui` | khởi động lại vẫn đúng |
| F4.4 | DPI scaling | 100–250% không bóp chữ | `self.S`, `px()` | `app-ui` | đổi scaling Windows 150% |
| F4.5 | Lưu/mặc định | `config.json` | `_cfg_from_vars`, `_save_cfg`, `_reset_cfg` | `app-ui` | sửa → lưu → mở lại |
| F4.6 | Thông tin phiên bản/thư viện | tab 3 | `_fill_info` | `app-qa-release` | hiện đúng có/không |
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
