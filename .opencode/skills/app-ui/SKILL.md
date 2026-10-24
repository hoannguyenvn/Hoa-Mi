---
name: App UI (Tkinter Shell)
description: Sửa giao diện Tkinter của Oriole — theme sáng/tối, DPI scaling px(), khung app-style (thanh điều hướng + 3 màn hình), queue/_poll 80 ms, config.json, phím tắt và đóng app. Dùng khi người dùng nhắc tới giao diện, cửa sổ, tab, màu, theme, DPI, phóng to, phím tắt, config, hoặc app.py phần App.
---

# UI Shell (Tkinter)

`app.py` là **một file** chứa cả UI và pipeline (D-01). Đừng tách package trong một
phiên không liên quan.

Đọc trước: bất biến I1 (worker không chạm widget), I12 (`config.json` whitelist),
I14 (không đưa debug kỹ thuật lên UI); `docs/DECISIONS.md` D-04, D-15, D-18.

## 1. Cấu trúc `App`

```
App(tk.Tk)
├─ __init__: cfg, DPI self.S, geometry, StringVar, _queue, _texts
├─ _apply_theme()  → ttk.Style("clam") + màu cho tk.Text
├─ _build_ui()     → thanh điều hướng `rail` + `content` chứa 3 màn hình (B4a, D-28)
│   ├─ _build_rail()            (logo · 2 mục · chân: Model·Ngôn ngữ ▾, theme, Cài đặt)
│   ├─ _build_text_screen()     → toolbar + nút ghép nguồn · thanh nguồn · vùng chữ · panel (B5)
│   ├─ _build_practice_tab()    → toolbar · sân khấu _build_stage · panel _build_side
│   └─ _build_settings_screen() → toolbar · 2 cột nhóm hàng (`_set_group`/`_set_row`) · lưu ngay
├─ _show_screen(key) → "stt" | "prac" | "set" (thay ttk.Notebook; vào "set" quét lại mic)
├─ _on_root_resize   → nav_compact(): < 1240×S thì thanh 60 px chỉ biểu tượng
├─ _poll()         → vòng 80 ms đọc self._queue
└─ _on_close()     → lưu geometry + config
```

Widget dùng lại: `self.screens` (`tab_stt`/`tab_prac`/`tab_set` là tên cũ của 3 màn hình),
`self.status`, `self.pbar`, `self.log_txt`, `self.p_words`, `self.p_side`, `self.p_int`.

## 2. DPI — quy tắc tuyệt đối

```python
self.S = max(1.0, min(3.0, self.winfo_fpixels("1i") / 96.0))
def px(self, v): return int(round(float(v) * self.S))
```

- Mọi số đo thiết kế **phải** đi qua `self.px(...)` (padding, width, height,
  wraplength, canvas margin, sashpos, font size thì dùng point).
- Không hard-code pixel trong widget mới.
- Cửa sổ: `min(1480*S, 94% màn hình)` × `min(940*S, 92%)`; `minsize(980*S, 640*S)`.
- Geometry trong config chỉ được nhận nếu `>= 900*S × 600*S`; nhỏ hơn → bỏ qua.
- Test tay: Windows scaling 100%, 150%, 250%; chữ không bị cắt, nút không chồng.

## 3. Theme

- `THEMES = {"light": {...}, "dark": {...}}`; mọi màu lấy từ `self.P[...]`.
- Khóa màu (D-32): `bg card card2 side nav_sel border fg muted accent accent2 field sel
  ok_bg bad_bg warn_bg ok_fg bad_fg warn_fg accent_fg info_bg log_bg btn btn_hover disabled
  disabled_fg track ring_ok ring_warn ring_bad rec rec_ring warn_line bad_line band`.
  Test `theme_text_contrast_ok` kiểm tra mọi cặp chữ/nền ≥ 4,5 : 1 ở cả hai theme.
  Thêm màu mới → thêm ở **cả hai** bảng, nếu không `KeyError` khi đổi theme.
- `_apply_theme()` dựng lại `ttk.Style` (theme `clam`) và style:
  `App.TFrame`, `Card.TFrame`, `CardInner.TFrame`, `Card2.TFrame`, `Header.TFrame`,
  `H1.TLabel`, `Sub.TLabel`, `Card.Title.TLabel`, `Card.Hint.TLabel`,
  `Card.Mono.TLabel`, `Card.Big.TLabel`, `Muted.TLabel`, `Rec.TLabel`,
  `TButton`, `Accent.TButton`, `Ghost.TButton`, `TEntry`, `TCombobox`,
  `TNotebook(.Tab)`, `Card.TNotebook(.Tab)`, `TProgressbar`, `TSeparator`,
  `TPanedwindow`, `Vertical.TScrollbar`, `TCheckbutton`, `TRadiobutton`.
- `tk.Text` không theo ttk: dùng `_mk_text()` để đăng ký vào `self._texts`,
  `_style_text()` để tô lại khi đổi theme.
- Tag trong Text: `ok` `bad` `warn` `note` `err` `big`. Không đặt màu trực tiếp
  trong `insert` — dùng tag.
- Thanh tiêu đề Windows: `_set_titlebar()` dùng DWM attribute 20/19, bọc `try`.
- Font: `Segoe UI` cho UI, `Consolas` cho mono.

### Hai đường đổi theme

- Thanh điều hướng: mục "Giao diện tối/sáng" → `_flip_theme()` → đảo `theme_name` →
  `_toggle_theme()`.
- Tab Cài đặt: radio đã set `theme_name` → gọi `_toggle_theme()` (không đảo lần nữa).

Đừng gộp hai đường này: nếu `_toggle_theme` tự đảo, radio sẽ bị đảo ngược.
Cả hai đều kết thúc bằng `_apply_theme()` + `_save_cfg()` để nhớ khi mở lại.

## 4. Luồng worker → UI (I1)

Worker **không** gọi widget, kể cả `StringVar.set`. Chỉ `self._queue.put((kind, payload))`.

`_poll()` xử lý các `kind`:

| kind | payload | Hành động |
|---|---|---|
| `log` | `str` hoặc `tuple` | `_log(...)` |
| `status` | `str` | status bar |
| `progress` | `float 0..1` hoặc `None` (indeterminate) | `_pbar` (nhân 100) |
| `result` | `payload` dict | `_on_result` |
| `error` | `str` | `_on_error` |
| `rec_autostop` | — | `_rec_stop_and_transcribe` |
| `rec_error` | `str` | dừng thu, hộp thoại |
| `prac_status` | `str` | dòng trạng thái Tab 2 |
| `prac_autostop` | `reason`: `"silence"`/`"nospeech"`/`"max"` | `_prac_stop_and_score(reason)` |
| `prac_done` | `res` dict | `_prac_done` |
| `prac_error` | `str` | `_prac_error` |
| `yt_ready` | `YtReadSession` | `_yt_ready` (đọc to YouTube, D-39) |
| `yt_fail` | `str` hoặc `"__cancelled__"` | `_yt_fail` |
| `yt_done` | `(idx, res, gate)` | `_yt_done` → `ytread_view` → `_yt_render` |
| `yt_listen_done` | `(id(phiên), idx)` | nghe xong đoạn gốc → bắt đầu thu (chế độ Nghe rồi đọc) |
| `mic_found` | `(idx, name, api, peak)` hoặc `None` | chọn micro nếu `peak >= MIC_MIN_PEAK` |

Thêm loại mới: xử lý trong `_poll`, không tạo `after` riêng trong thread.
`self.cancel_flag` là cờ chung; worker dài phải kiểm tra (I11).

## 5. Cấu hình

`DEFAULT_CFG` (nguồn sự thật của khóa):

```python
model, lang, out_dir, theme, yt_kind, yt_quality,
subs, embed, sub_lang, mic, geometry
```

- `load_config()` chỉ nhận khóa có trong `DEFAULT_CFG`; JSON lỗi → mặc định.
- `save_config()` ghi UTF-8, `ensure_ascii=False`, indent 2; lỗi thì bỏ qua.
- `_cfg_from_vars()` là nơi duy nhất chuyển UI → dict.
- Thêm khóa: `DEFAULT_CFG` + `__init__` đọc + `_cfg_from_vars` + `_reset_cfg`
  + `config.json` hiện có (nếu không, `context_check` báo khóa lạ).
- `smoke_test.config_is_whitelisted` kiểm tra kiểu dữ liệu từng khóa — giữ đúng kiểu.

## 6. Phím tắt & đóng app

| Phím | Hành vi |
|---|---|
| `Ctrl+O` | chọn file |
| `Ctrl+S` | lưu `.txt` |
| `Ctrl+Enter` | `_primary()` — bắt đầu chuyển hoặc bắt đầu thu |
| `Esc` | `_cancel()` |

- Hiển thị lại ở status bar **và** tab Cài đặt; đổi phím phải sửa cả hai chỗ.
- `_on_close`: cập nhật `cfg["geometry"] = self.geometry()` → `_save_cfg()` →
  đặt `cancel_flag` → dừng recorder (nếu đang thu) → `_stop_play()` →
  `_set_last_wav(None)` (xóa bản ghi luyện tạm) → `destroy()`.
- Hộp thoại: dùng `messagebox` cho lỗi chặn; lỗi thường ghi vào Nhật ký (I14).

## 7. Khi sửa — checklist

1. Widget mới: dùng style có sẵn, `px()` cho kích thước, màu từ `self.P`.
2. Nếu là `tk.Text`/`tk.Canvas`: đăng ký hoặc vẽ lại trong `_apply_theme`.
3. Worker mới: chỉ `_queue.put`, thêm nhánh trong `_poll`.
4. Cập nhật `docs/FEATURES.md` §4 nếu thêm tính năng cài đặt.
5. Chạy `py_compile`; mở app thật để kiểm tra 2 theme + 2 mức DPI.
6. Không thêm dependency UI (customtkinter, PIL…) nếu tk/ttk làm được (I8).

## 8. Trạng thái dùng chung giữa các tab (dễ sai)

- `self.recording` và `self.recorder` **dùng chung** cho Tab 1 và Tab 2; `self.rec_owner`
  (`"stt"` | `"prac"` | `None`) cho biết tab nào đang thu. Nút chính của tab kia chỉ báo
  "đang thu ở tab …", không dừng/chấm hộ. `rec_autostop`/`prac_autostop`/`rec_error`/
  `prac_error` đều kiểm tra owner trước khi đụng recorder.
- Mọi chỗ dừng thu đi qua `App._stop_recorder()`: dừng, xóa owner, reset UI đúng tab
  (Luyện: nút tròn "Thu âm" + `lbl_plevel` + thanh mức âm; Văn bản: `lbl_rec_level`).
  `Esc` dùng nó.
  Test: `recording_belongs_to_one_tab`.
- `self.busy` chỉ khóa Tab 1; `self.p_working` khóa Tab 2 (`scoring` **và** `loading`).
- Chế độ **Từ YouTube** dùng lại sân khấu Luyện: `_stage_repack("yt", …)` thay câu bằng
  `yt_head` + `yt_text` và đặt khối thu âm thành **cột bên phải** đoạn văn (không bên dưới —
  người học phải thấy cả đoạn khi thu); panel phải hẹp hơn (`YT_SIDE_FRAC`); khối thu âm, `p_samples`, panel phải (`pp_yt`) dùng chung. Rẽ nhánh
  ở `_prac_start`, `_prac_score`, `_step_lesson`, `_prac_mode_changed`. Hủy tải bằng cờ
  riêng `_yt_cancel` (không dùng `cancel_flag` của Tab 1).

## 9. Font, chỉ báo, thanh cuộn (B1 — D-28/D-32)

- Font: `register_ui_fonts()` (gọi ở đầu `App.__init__`, **trước** `super().__init__()`)
  đăng ký `assets/fonts/BeVietnamPro-*.ttf` bằng `AddFontResourceExW(FR_PRIVATE)`;
  `self.F = pick_ui_font(...)` (Be Vietnam Pro → Segoe UI Variable Text → Segoe UI).
  Widget mới dùng `self.F`, **không** ghi cứng "Segoe UI".
- IPA: Be Vietnam Pro thiếu 21/43 ký tự IPA (θ ŋ ə ɪ ʃ ˈ…), Tk mượn glyph nên lệch cỡ →
  mọi chữ IPA dùng `FONT_IPA` (Segoe UI): style `Card.Ipa.TLabel`, `Card.HintIpa.TLabel`,
  tag Text `"ipa"` (nhãn/mẹo âm vị trong `_prac_done`).
- Radio/checkbox: layout `TCheckbutton`/`TRadiobutton` dùng element ảnh
  `Oriole.Check.indicator` / `Oriole.Radio.indicator`; ảnh vẽ bằng `indicator_rows`
  (hàm thuần, khử răng cưa) và **vẽ lại** trong `_theme_indicators` mỗi lần đổi theme.
  Khoảng cách tới chữ nằm trong ảnh (cột trong suốt) vì element ảnh bỏ qua `-padding`.
- `TCombobox`/`TEntry`: map `disabled` đứng **trước** `readonly`.
- Tab notebook: map `padding` của `selected` bằng padding thường (clam làm tab chọn tụt chữ).
- `_mk_text(..., scroll=True)` đặt Text trong khung có `ttk.Scrollbar`; nơi gọi pack
  **`w.holder`** (vd `before=self.txt_out.holder`). `scroll=False` thì `w.holder is w`.
- Thanh tiến trình: chỉ hiện ở trạng thái `processing` (tab Văn bản) / `scoring` (tab Luyện)
  — do `_set_stt_state` / `_set_prac_state` quyết (D-31), không pack/forget ở chỗ khác.
- Ô Ngôn ngữ: combobox gắn `self.lang_label` (tên tiếng Việt, `LANG_LABELS`); `self.lang`
  vẫn giữ mã và là thứ được lưu/đọc — hai biến tự đồng bộ qua trace.
- Icon cửa sổ: `_set_icon()` vẽ bằng `logo_rows` (không file ảnh).
- Kiểm tra bằng mắt: `tools/ui_shots.py <nhãn>` chụp 21 trạng thái vào
  `%TEMP%\oriole_shots\<nhãn>\` mà không ghi config/lịch sử.

### Màn Văn bản + Cài đặt (B5, S-8)

- Văn bản: `stt_view(state, has_result)` (hàm thuần) → vùng chữ `sd_empty` (cũng dùng khi
  đang thu, biểu tượng mic đỏ) / `sd_proc` (thanh xương) / `sd_res` (`txt_out` role `"doc"`:
  không viền, tag `doc` có `rmargin` giới hạn ~720 px, tag `time` mờ cho `[hh:mm:ss]` —
  chữ giữ đúng `cues_to_txt` để Lưu/Sao chép không đổi), panel `ss_empty` (mẹo) /
  `ss_busy` / `ss_res` (thống kê `st_vals`, `btn_copy`, `btn_txt`, `btn_srt`, link
  `btn_folder`/`btn_open` qua `_link_state`). `_stt_view()` gọi từ `_set_stt_state`,
  `_on_result`, `_on_error`, `_src_changed`. `btn_cancel` chỉ pack khi `cancel_enabled`;
  tiến trình `stt_prog` (pbar + `status`) chỉ khi `processing`; ghi âm: `stt_meter` (T-04).
  Nhật ký: `log_txt` trong `log_box` ẩn; thanh `log_last` hiện dòng cuối, `_toggle_log`.
- Cài đặt: `_set_group(parent, title)` + `_set_row(g, label, sub, sub_var, last, vertical,
  compact)`; công tắc `_mk_switch(var)`; theme bằng `_mk_seg`. Lưu ngay: trace các biến cấu
  hình → `_autosave` (gom 0,4 s) → `_save_cfg` + "✓ Đã lưu"; chỉ bật sau khi dựng xong
  (`_autosave_on`) nên khởi động không ghi `config.json`. Thử mic → queue `mic_test` →
  `mic_test_msg`. Model/Ngôn ngữ chỉ ở menu thanh điều hướng (V-14, `MODEL_DESC`).

### Khung app-style (B4a, D-28) — widget tk thuần theo theme

- Phần mới dùng `tk.Frame/Label/Canvas` (không ttk) cho đúng màu thiết kế. Tạo qua
  `_frame(parent, bg=token)`, `_lbl(parent, text, bg=, fg=, size=)`, `_link_lbl`, `_hline`;
  hoặc `_tw(widget, bg="side", fg="muted")` — đăng ký vào `self._themed` để `_retheme_tk()`
  tô lại khi đổi theme. Phần **vẽ Canvas** đăng ký hàm vào `self._redraws`
  (`_draw_rail`, nút ghép `_mk_seg`, công tắc `_mk_switch`, `_draw_rec_btn`, `_redraw_words`, `_redraw_pills`,
  `_draw_intonation`, vòng điểm). Widget tk không đăng ký sẽ **giữ màu theme cũ**.
- Thanh điều hướng: `_rail_item` (vạch accent 3 px + biểu tượng + nhãn);
  `_draw_icon(c, name, color, s, ox=, oy=, clear=)` vẽ doc/mic/gear/moon/sun/stop bằng nét.
  Chế độ gọn ẩn nhãn, rê chuột hiện `_tooltip`. Model/Ngôn ngữ: `_model_menu()` (tk.Menu
  radiobutton gắn `model_name` / `lang_label`) ở chân thanh; Cài đặt vẫn có (V-14 ở B5).
- Thanh công cụ 60 px: `_toolbar(parent, title)`. Màn Luyện: chế độ dạng nút ghép
  (`_mk_seg` dùng chung, `locked=` khi đang thu/chấm), `cb_prac` style `Toolbar.TCombobox`, `p_pos` "Bài k / n",
  `_step_lesson(±1)`. Đang thu/chấm: khóa đổi bài/chế độ (trong `_set_prac_state`).
- Sân khấu: `p_words` xếp từ bằng `place` (`_layout_words`, chạy **sau idle** — đo ngay thì
  mọi từ rộng 1 px; không gọi `update_idletasks` trong vòng đo: gọi lồng làm hủy widget
  giữa chừng); viên thuốc nghe `_mk_pill`/`_pill_show` (tự xuống dòng bằng `_flow`, như từ); hộp mẹo `p_tip`; nút thu tròn
  `btn_prec` (`_draw_rec_btn`, token `rec*`) + `p_meter` (`meter_cells`) + `lbl_plevel`;
  dòng micro `_update_mic_line` (`short_mic_name`) + "Đổi" → màn Cài đặt; dòng
  `p_status` chỉ chiếm chỗ khi có chữ (`_sync_status_line`).
- Panel phải `p_side`: bề rộng `side_width()` ≈ 48 % vùng nội dung, kẹp 340–640 px × S
  (đổi theo `_prac_body_resized`) để cả kết quả nằm trên một trang; `_scroll_area` (Canvas + Frame + thanh cuộn tự ẩn),
  cuộn chuột qua `_on_wheel` (bind_all, chỉ panel dưới con trỏ). Mục theo thứ tự cố định
  `_panel_show([...])`: wait · head · heard · unsure · fix · notes · inton · detail.
  Đáy ghim: `p_prog` + `_show_actions(primary, cmd, secondary, cmd)`.
  Chữ xuống dòng: `_wrap(label, margin)` → `_side_wrap` cập nhật `wraplength`.

## 10. Trạng thái màn hình (D-31)

- Tab Văn bản: `STT_STATES` = idle/recording/processing/result/error →
  `App._set_stt_state(state)`; tab Luyện: `PRAC_STATES` = idle/recording/scoring/result/
  unsure/error → `App._set_prac_state(state)`.
- Hai hàm này là nơi **duy nhất** bật/tắt nút chính, nút Hủy, viên "Bản thu của bạn",
  nhãn + biểu tượng nút thu (`rec_label`/`rec_icon`), khóa đổi bài, nội dung panel chờ,
  hiện thanh tiến trình, xóa dòng mức âm; bảng quyết định là hàm thuần `stt_controls` /
  `prac_controls` (test `screen_states_drive_controls`).
- `busy`, `p_working`, `recording`, `rec_owner` chỉ được gán trong hai hàm trên.
  `_stop_recorder()` → state `idle` của tab đang thu. Đổi bài → `idle`.

## 11. Cạm bẫy

| Triệu chứng | Nguyên nhân |
|---|---|
| `RuntimeError: main thread is not in main loop` | worker gọi widget/StringVar (I1) |
| Chữ/nút nhỏ xíu trên màn 4K | quên `px()` hoặc hard-code padding |
| `KeyError` khi đổi theme | màu mới chỉ thêm ở một bảng `THEMES` |
| Text vẫn trắng khi theme tối | widget không nằm trong `self._texts` |
| Combobox dropdown sai màu | thiếu `option_add("*TCombobox*Listbox...")` |
| Mất geometry sau khi mở lại | không lưu trong `_on_close`, hoặc cửa sổ nhỏ hơn ngưỡng |
| `config.json` bị context_check báo khóa lạ | thêm khóa mà không thêm `DEFAULT_CFG` |
| Radio Cài đặt đảo ngược theme | cho `_toggle_theme` tự đảo; radio đã set biến trước |
| Radio/checkbox trông sai ở theme tối, checkbox hiện "✕" | quay lại chỉ báo mặc định của clam thay vì ảnh `Oriole.*.indicator` |
| IPA lẫn cỡ chữ (θ, ŋ to nhỏ khác nhau) | hiện IPA bằng font giao diện thay vì `FONT_IPA` |
| Dải màu tràn hết chiều ngang trong kết quả | tag (`ok`/`warn`) phủ cả ký tự `\n` — chèn xuống dòng ngoài tag |
| `TclError: ... is not managed` khi đổi bài | pack/`before=` vào Text có thanh cuộn thay vì `.holder` |
| App không thoát | thread không daemon hoặc `after` loop không dừng |
| Widget mới giữ màu cũ khi đổi theme | tạo `tk.*` mà không qua `_tw`/`_frame`/`_lbl` hoặc chưa thêm hàm vẽ vào `_redraws` |
| Nhãn hàng Cài đặt bị cắt ở cửa sổ hẹp | điều khiển rộng đặt bên phải — với hàng có ≥ 2 nút, dùng `vertical=True` và xếp nút dưới chữ |
| Glyph thành ô vuông (vd "⬇") | Be Vietnam Pro thiếu ký tự — chỉ dùng ▶ ■ ● ✓ ✕ (đã thử) hoặc bỏ ký hiệu |
| Thanh cuộn panel không hiện | pack thanh cuộn sau Canvas đã `expand` — phải `before=cv` |
