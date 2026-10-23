---
name: App UI (Tkinter Shell)
description: Sửa giao diện Tkinter của Oriole — theme sáng/tối, DPI scaling px(), bố cục 3 tab, queue/_poll 80 ms, config.json, phím tắt và đóng app. Dùng khi người dùng nhắc tới giao diện, cửa sổ, tab, màu, theme, DPI, phóng to, phím tắt, config, hoặc app.py phần App.
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
├─ _build_ui()     → header + Notebook 3 tab + status bar
│   ├─ _build_text_tab()      (Tab 1: nguồn, nhật ký, kết quả)
│   ├─ _build_practice_tab()  (Tab 2: bài, thu âm, kết quả, ngữ điệu)
│   └─ _build_settings_tab()  (Tab 3: nhận dạng, lưu file, phím tắt, info)
├─ _poll()         → vòng 80 ms đọc self._queue
└─ _on_close()     → lưu geometry + config
```

Widget dùng lại: `self.nb`, `self.tab_stt`, `self.tab_prac`, `self.tab_set`,
`self.status`, `self.pbar`, `self.log_txt`, `self.p_txt`, `self.p_int`.

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
- Khóa màu đang dùng: `bg card card2 border fg muted accent accent2 field sel
  ok_bg bad_bg warn_bg ok_fg bad_fg log_bg btn btn_hover disabled`.
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

- Header: `btn_theme` → `_flip_theme()` → đảo `theme_name` → `_toggle_theme()`.
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
  (Tab 2: nút "● Thu âm & chấm" + `lbl_plevel`; Tab 1: `lbl_rec_level`). `Esc` dùng nó.
  Test: `recording_belongs_to_one_tab`.
- `self.busy` chỉ khóa Tab 1; `self.p_working` khóa Tab 2.

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
  **`w.holder`** (vd `before=self.p_txt.holder`). `scroll=False` thì `w.holder is w`.
- Thanh tiến trình: chỉ hiện ở trạng thái `processing` (tab Văn bản) / `scoring` (tab Luyện)
  — do `_set_stt_state` / `_set_prac_state` quyết (D-31), không pack/forget ở chỗ khác.
- Ô Ngôn ngữ: combobox gắn `self.lang_label` (tên tiếng Việt, `LANG_LABELS`); `self.lang`
  vẫn giữ mã và là thứ được lưu/đọc — hai biến tự đồng bộ qua trace.
- Icon cửa sổ: `_set_icon()` vẽ bằng `logo_rows` (không file ảnh).
- Kiểm tra bằng mắt: `tools/ui_shots.py <nhãn>` chụp 11 trạng thái vào
  `%TEMP%\oriole_shots\<nhãn>\` mà không ghi config/lịch sử.

### Thành phần kết quả luyện (B3)

- Vòng điểm `_draw_ring` (Canvas 60 px × `S`), chip từ `_mk_chip` (Canvas đa giác bo góc,
  đo chữ bằng `tkfont.Font.measure`), thẻ lỗi `_mk_card` (Frame viền 1 px) — nhúng vào
  `p_txt` bằng `window_create` qua `_embed`; `_destroy_embeds` dọn khi vẽ lại.
- Token màu B3 trong `THEMES` (cả sáng/tối): `ok_bg/ok_fg`, `warn_bg/warn_fg`,
  `bad_bg/bad_fg`, `ring_ok/ring_warn/ring_bad`, `info_bg`, `track`.
- Frame co theo nội dung: muốn các thẻ cùng rộng phải có **thanh chống** (Frame cao 0,
  `width=`) bên trong; `f.configure(width=)` một mình không có tác dụng khi con được pack.
- Đã biết (B4 phải sửa): ở cửa sổ tối thiểu 980×640, đầu kết quả (vòng điểm) đẩy ô
  `p_txt` còn ~1 dòng → chip bị che (V-09). Bố cục app-style (D-28) thay hẳn phần này.

## 10. Trạng thái màn hình (D-31)

- Tab Văn bản: `STT_STATES` = idle/recording/processing/result/error →
  `App._set_stt_state(state)`; tab Luyện: `PRAC_STATES` = idle/recording/scoring/result/
  unsure/error → `App._set_prac_state(state)`.
- Hai hàm này là nơi **duy nhất** bật/tắt nút chính, nút Hủy, Nghe lại, đổi nhãn nút thu,
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
