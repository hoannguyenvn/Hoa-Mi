# UI PLAN — Oriole visual overhaul

> Status: **GATE A passed 2026-10-22** — user approved the spec and accepted the default
> answers for Q-01…Q-07 (§6). **GATE B passed 2026-10-22** (D-29…D-32). **Phase 3 build
> in progress: B1, B2 done 2026-10-22 (§5.1–5.2), next B3.** Design
> — canvas: https://claude.ai/artifact/L1oNuJ2Wq89LK7b8dFfRhK (private to the user).
> No code is written until GATE B passes. Source of the issues: visual audits on
> 2026-10-22 (`docs/HANDOFF.md` entries "tiếp 10" and "tiếp 11").
> UI copy stays Vietnamese (D-18); this plan is in English for review.

## 0. How this plan works

```
Phase 0  Baseline      tools + screenshots of today's app            (done partly)
Phase 1  Specification what each screen must do and say            → GATE A: user approves spec
Phase 2  Design        tokens, components, mockups for every state → GATE B: user approves design
Phase 3  Build         5 increments, each shippable on its own
Phase 4  Verify        smoke tests + screenshot matrix + manual checks
Phase 5  Document      skills, DECISIONS, README, FEATURES
```

Rules that apply to every phase:
- Keep the project invariants: worker threads never touch widgets (I1), the score stays
  `correct / total` (I4), GOP is never shown as "% correct" (I7), no heavy dependencies —
  tk/ttk/Canvas only, no PIL/customtkinter (I8), no debug text in the UI (I14),
  single-file `app.py` (D-01), pitch chart is descriptive, never scored (D-10).
- Every change must look right in **light and dark**, at **100 %, 150 % and 250 %** Windows
  scaling, and at the **minimum window size**.
- No fake data is ever written to `config.json` or `practice_history.json` by tools.

## 1. Issue inventory

IDs are used in the rest of the plan. Sev: **H** = misleads the learner or hides
information, **M** = looks broken/confusing, **L** = polish.

### 1.1 Widgets and theme (whole app)

| ID | Issue | Sev | Where |
|---|---|---|---|
| V-01 | Dark theme: unselected radio looks filled, selected looks empty | H | `_apply_theme` (`indicatorbackground` not themed) |
| V-02 | Ticked checkbox draws "✕" (clam default) — reads as "off" | M | `_apply_theme` |
| V-03 | Disabled combobox looks identical to an enabled one | M | `_apply_theme` (`TCombobox` disabled map) |
| V-04 | Notebook tabs: selected tab sits lower and looks sunken, others look raised | M | `_apply_theme` (`TNotebook.Tab`) |
| V-05 | Combobox arrows are tiny, almost invisible | L | `_apply_theme` (`arrowsize`) |
| V-06 | Header button "Chế độ: Tối" names the *other* mode — confusing | L | `_build_ui`, `_apply_theme` |
| V-07 | No scrollbars on any `tk.Text` (transcript, SRT, log, result) | M | `_mk_text` |
| V-08 | No window icon (default Tk feather) | L | `App.__init__` |
| V-09 | At minimum size: score line overlaps the "Kết quả chấm" title and is cut; Micro row cut off; left column cannot scroll | H | `_build_practice_tab` |
| V-10 | First layout: left pane may flash at width 0 (sash set after 60 ms) | L | `_init_sash`, `_sash` |
| V-11 | Idle progress bars mislead: tab 1 stays full blue after a job; tab 2 shows an empty track | M | `_on_result`, `pbar_p` |
| V-12 | All buttons have the same weight; no grouping of primary/secondary/rare actions | M | all `_build_*` |
| V-13 | Mixed language / raw codes in UI: "Copy", "auto", "vi", "en" | L | `LANGS`, `_build_result` |
| V-14 | Model + Ngôn ngữ appear in both the header and Settings | L | `_build_ui`, `_build_settings_tab` |
| V-15 | Long mic names are truncated in the combobox, no tooltip | L | `_mk_mic_row` |

### 1.2 Tab 1 — Chuyển thành văn bản

| ID | Issue | Sev | Where |
|---|---|---|---|
| T-01 | Empty result area is a big blank box; no guidance | M | `_render_preview` |
| T-02 | Log panel takes half of the left column though few people need it | M | `_build_text_tab` |
| T-03 | Transcript lines run the full width (~170 characters) — hard to read | L | `txt_out` |
| T-04 | Recording level is an ASCII bar `[######····]` | L | `Recorder.level_bar`, `_rec_tick` |

### 1.3 Tab 2 — Luyện phát âm (practice and results)

| ID | Issue | Sev | Where |
|---|---|---|---|
| P-01 | Switching lesson or mode keeps the previous lesson's score and result | H | `_refresh_practice` |
| P-02 | "Bạn đọc" colours the **target** words, not what was heard ("think" shown, "tink" heard) | H | `_prac_done` |
| P-03 | A big score is shown when the app is unsure (`low_conf`) or Whisper invented text | H | `_prac_done`, `_w_prac` |
| P-04 | Whisper's made-up sentence ("cảm ơn các bạn đã theo dõi…") shown in red as if the learner said it; `garbage` only fires at ≥ 2× length | H | `_w_prac` |
| P-05 | `warn` tag spans newlines → full-width yellow band | M | `_prac_done` (0-word branch) |
| P-06 | Three different percentages on one screen (word score, GOP, GOP of sample) | H | `_prac_done` |
| P-07 | Vietnamese errors are machine wording, no tip, no listen button; vowel+tone mix-ups ("lắm" → "lám") are only listed as "Chưa khớp" | M | `flag_pair`, `_prac_done` |
| P-08 | Perfect English read: no praise ("Hoàn hảo" exists only for Vietnamese) | L | `_prac_done` |
| P-09 | Score text "50.0%" — decimal, cold, no visual | L | `_prac_done` |
| P-10 | Red ⚠ for GOP issues looks alarming; GOP note is tiny grey text | M | `_prac_done` |
| P-11 | Record button uses a white dot on blue, not a recording affordance; no pulsing/recording state | L | `_build_practice_tab` |
| P-12 | No "Thử lại" / A-B listening loop next to the result | M | `_build_practice_tab` |
| P-13 | Left column crowded; right column mostly empty space | M | `_build_practice_tab` |

### 1.4 Pitch chart (Ngữ điệu)

| ID | Issue | Sev | Where |
|---|---|---|---|
| C-01 | No word labels on the time axis — learner cannot tell where each word is | H | `_draw_intonation`; word times dropped in `_w_prac` |
| C-02 | Caption uses jargon (st, DTW, "độ lệch đường cong") and gives no plain verdict | M | `_inton_text` |
| C-03 | Y axis "+12 … -12" has no meaning for learners | L | `_draw_intonation` |
| C-04 | Legend only in caption text | L | `_draw_intonation` |
| C-05 | Vietnamese lessons and sound guides never get a chart (no sample audio) | M | `_prac_score` (content gap, see §6 Q-07) |

### 1.5 Progress and history

| ID | Issue | Sev | Where |
|---|---|---|---|
| H-01 | Progress is one grey text line; no trend | M | `_update_prog` |
| H-02 | History stores only `n/best/last`, not each attempt → no trend possible | M | `_record_hist` (data model) |
| H-03 | "Âm yếu nhất" sums all lessons and languages (Vietnamese readings misdetected as English add AA/OW) | H | `_weakest`, `_record_hist` |

### 1.6 Architecture (root cause of several issues)

| ID | Issue | Sev | Where |
|---|---|---|---|
| A-01 | No per-tab UI state: ~8 flags (`busy`, `p_working`, `recording`, `rec_owner`, `playing`, `_mic_probing`…) and buttons toggled by hand in many places → causes P-01, V-11, stuck buttons | H | `App` |
| A-02 | Result rendering mixes "what to say" with "how to draw" inside `_prac_done` (180 lines of `t.insert`) → impossible to unit-test the wording | M | `_prac_done` |

Total: 42 issues (10 H, 18 M, 14 L).

## 2. Phase 0 — Baseline (½ day)

Goal: be able to see every screen state on demand, safely.

- [ ] Promote the scratch screenshot script to `tools/ui_shots.py`:
  - builds `App()`, feeds fixed sample results, captures each state to `%TEMP%\oriole_shots\`
    (outside the repo, I10);
  - **blocks** `save_config`, `App._save_hist`, `App._record_hist` (lesson learnt 2026-10-22);
  - states: tab 1 empty / YouTube / recording / result; tab 2 idle / recording / result ×6
    (VI errors, EN errors, EN perfect, GOP, unsure, garbage) / guide; settings;
    light + dark; normal + minimum window.
  - optional `ORIOLE_SCALE=1.0|1.5|2.5` env var read **only** by the tool (forces `App.S`)
    so 100/150 % layouts can be checked on this 250 % screen. Not a user setting.
- [ ] Keep today's 13 + 6 screenshots as "before" set.

Exit: one command renders all ~30 states in < 60 s, writes nothing to user files.

## 3. Phase 1 — Specification (1 day) → GATE A

Deliverable: this section, finalised and approved. Each spec item lists the issues it closes.

### S-1 UI state model (A-01, P-01, V-11)

Each tab owns one state value; one function redraws the tab from it.

| Tab | States | Allowed transitions |
|---|---|---|
| Tab 1 | `idle` → `recording` → `processing` → `result` \| `error` | any → `idle` on Hủy/Esc |
| Tab 2 | `idle` → `recording` → `scoring` → `result` \| `unsure` \| `error` | lesson change → `idle` (clears result) |

- `App._set_stt_state(state, **data)` and `App._set_prac_state(state, **data)` are the
  **only** places that enable/disable buttons, change button text, start/stop progress bars.
- Worker messages (`_poll`) map to state changes; nothing else toggles widgets.
- `rec_owner` (D-26) stays; it becomes derivable from which tab is in `recording`.

### S-2 Result view-model (A-02, P-02…P-10)

A pure function `build_result_view(res, lesson) -> dict` (no Tk), unit-tested in
`smoke_test.py`. `_prac_done` only draws what it returns.

```python
{
  "state": "result" | "unsure",           # unsure ⇒ no score shown (S-3)
  "headline": "Đúng 2/4 từ",               # or "Hoàn hảo — đúng cả 4 từ"
  "summary": "Lỗi chính: âm /θ/ và /ð/ — lưỡi chưa đặt giữa răng.",
  "score": {"correct": 2, "total": 4, "tone": "warn" | "ok" | "bad"},
  "chips": [{"target": "think", "heard": "tink", "kind": "warn"}, ...],   # per target word
  "extras": ["um"],                       # words heard but not in the sentence (max 3 shown)
  "cards": [{"title": "/θ/ trong “think”", "tip": "...", "play_word": "think",
             "level": "lệch rõ" | "hơi lệch", "source": "gop" | "chữ"}],
  "notes": ["..."],                        # e.g. GOP explanation, low confidence
}
```

Rules:
- **Chips show both sides** when wrong: target big, "→ nghe ‘tink’" small (P-02).
  Missing word: "→ (thiếu)". Extra words: grey chips "+ um" at the end.
- **One number family on screen**: the headline is a fraction of words ("2/4 từ") (P-06, P-09).
  GOP is shown as a **level word**, not a percent: `score < 25` → "lệch rõ",
  `< 55` → "hơi lệch"; the sample's value moves to a tooltip / details line (I7 kept).
- Colour is never the only signal: chips carry an icon (✓ / ! / ✕) and the heard word (accessibility).
- Max 4 cards; consonant cards before vowel cards (existing rule in `analyze_pairs`).
- Praise: score = 100 % and no warns → headline "Hoàn hảo — đúng cả N từ" for **every**
  language (P-08).

### S-3 Evidence gate for showing a score (P-03, P-04) — needs D-29

Show the `unsure` state (no number, no red words) when **any** of:
1. `low_conf` (mean word probability < 0.35) **and** `correct / total < 0.5`;
2. `garbage` — widened: heard words ≥ 1,6 × target words and score < 35, **or** the
   hypothesis contains a known Whisper hallucination phrase
   (`"cảm ơn các bạn đã theo dõi"`, `"hẹn gặp lại các bạn"`, `"subscribe"`,
   `"thanks for watching"`, `"ghiền mì gõ"` …, list kept in code + tested);
3. `correct == 0` and `low_conf`.

Unsure screen copy: headline "Máy chưa nghe rõ bài đọc", body "Thử lại: nói gần mic hơn
(10–20 cm), đọc to và chậm. Với tiếng Việt nên chọn model small.", buttons **Thử lại**,
**Nghe lại bản thu**. The heard text appears only under a collapsed "Máy nghe được…" line,
in grey, never in red. History is **not** updated for unsure attempts.

### S-4 Vietnamese feedback (P-07)

- Wording table replaces machine phrasing:
  `nl` → "“lan” nghe thành “nan” — âm L bị đọc thành N".
  `tone` → "“má” nghe thành “ma” — sai dấu thanh".
  vowel+tone ("lắm" → "lám") → new state `rhyme` "sai vần/dấu" (closes the gap in
  `strip_tone_vi`; base letters differ only in breve/circumflex/horn).
- Each Vietnamese error card gets the matching tip from `GUIDES` (n / l / nl) and a ▶ button
  when a sample clip exists (`mau/vi_*.wav`).
- `flag_pair` and `score_pronunciation` stay the source of truth; only the wording and the
  new `rhyme` state are added (with smoke tests).

### S-5 Pitch chart (C-01…C-04)

- Keep Whisper word timings (`w.start`, `w.end`) in `_w_prac` → `res["words_t"]`.
- Draw word labels under the **learner** curve on the normalised time axis; highlight the
  span of words that have errors (light amber band). The sample curve is time-normalised,
  so labels are approximate — say so in the legend tooltip, not in the caption.
- Remove the numeric y axis; show only a mid line and the words "cao" / "thấp".
- Legend inside the chart: dashed = "Mẫu", solid = "Bạn".
- Caption becomes **one plain sentence**, chosen by rules (no score, D-10 kept):
  final slope same direction as sample → "Cuối câu bạn lên/xuống giọng giống mẫu ✓";
  opposite → "Cuối câu mẫu xuống giọng, bạn lại lên giọng";
  range < 50 % of sample → "Giọng bạn hơi đều — thử nhấn mạnh từ khoá hơn".
  Numbers (st, DTW) move to a "Chi tiết" toggle.

### S-6 Practice layout (P-11…P-13, V-09) — depends on Q-06

Option A (recommended, = roadmap Phase 2A): three columns
`Bài học | Thu âm | Kết quả`, each column scrollable.
Option B: keep two columns, move the mic block into Settings + a compact mic status line.

Either way:
- Record button: round, red when recording, label "Thu âm" / "Dừng & chấm", elapsed time
  and a canvas level meter beside it (T-04 shared component).
- Under the result: **Thử lại** (primary), **▶ Mẫu**, **▶ Bạn** (A-B loop, P-12).
- Score header wraps instead of overflowing (V-09).

### S-7 Progress (H-01…H-03) — needs D-30 (data model)

- `practice_history.json` per lesson gains `"tries": [{"ts", "c", "t", "ph": {...}}]`,
  last 30 kept. Old files load unchanged (missing `tries` = empty list).
- Phoneme counts are recorded **only** when the detected language equals the lesson's
  language, and "Âm yếu nhất" is computed **per language** (EN lessons show EN sounds,
  VI lessons show n/l/tone counts).
- UI: a 120 × 28 sparkline of the last 10 tries (correct/total), plus
  "5 lần · tốt nhất 3/4 · /θ/ sai 4 lần liền". Unsure attempts are not stored.

### S-8 Tab 1 (T-01…T-03, V-11)

- Empty state inside the result card: icon, "Chọn file, dán link YouTube hoặc ghi âm",
  three shortcut buttons, and a drop hint (drag & drop only if feasible without new deps;
  otherwise omit — open question Q-05).
- Log collapses to a one-line "Nhật ký ▸" bar showing the last message; expands on click.
- Transcript text width capped (~90 characters) with comfortable line spacing (1.5).
- Progress bar hidden in `idle` and `result`; shown only in `processing`.

### S-9 Theme, widgets and copy (V-01…V-08, V-12…V-15)

- Theme tokens gain: `rec` (red), `chip_ok_*`, `chip_warn_*`, `chip_bad_*`, `focus`,
  `disabled_fg`, `track`. Both themes defined; contrast ≥ 4.5:1 for text (checked by a
  small script in the smoke test).
- Radio/check indicators: themed `indicatorbackground` + `indicatorforeground` per state;
  checkbox uses a ✓ glyph image (PhotoImage drawn in code, no files) instead of "✕".
- Disabled state: muted text + field colour for `TCombobox`, `TEntry`, buttons.
- Tabs: selected tab = card colour + accent underline; unselected = flat, muted text, same
  baseline.
- Buttons: 3 weights — `Accent` (one per area), `Ghost`, `Link` (text-only for rare actions).
- Copy: "Copy" → "Sao chép"; language list shown as "Tự động / Tiếng Việt / Tiếng Anh / …";
  header shows a theme icon toggle (☀/☾) with tooltip instead of "Chế độ: Tối".
- Header keeps Model + Ngôn ngữ; Settings shows them read-only with "đổi ở thanh trên" —
  or the reverse (Q-04).
- All `tk.Text` get a themed `ttk.Scrollbar` (V-07). Mic combobox gets a tooltip with the
  full name (V-15).
- Window icon: 32×32 + 16×16 PNGs generated once into `assets/oriole.png` (D-14 style data),
  set with `iconphoto` (V-08).

### S-10 Acceptance criteria (used in Phase 4)

| Area | Must be true |
|---|---|
| Trust | No number is shown in the `unsure` state; hallucination fixtures all land in `unsure` |
| Honesty | Every wrong chip shows the heard word; no screen shows the target word as "Bạn đọc" |
| Clarity | Only one percentage-like value family per screen (word fraction) |
| Help | Every error card has a tip; ≥ 1 ▶ button when a clip exists |
| Chart | Words are labelled; caption is one sentence without "st"/"DTW" |
| State | Changing lesson clears the result; no button stays in a wrong label after Esc/error |
| Layout | Nothing clipped at minimum size in light/dark at 100/150/250 % |
| Theme | Radio/checkbox/disabled states read correctly in both themes |
| Safety | Smoke tests pass; screenshot tool writes nothing to user files |

## 4. Phase 2 — Design (1–1,5 days) → GATE B

Deliverables (HTML mockups shown in chat / published page, plus PNG renders kept outside repo):

1. **Token sheet** — light + dark colours, type scale (Segoe UI 9/10/12/16/22 pt), spacing
   scale (4/8/12/16/24 px × `S`), radius, chip styles. Contrast table.
2. **Component sheet** — buttons (3 weights × states), chips (ok/warn/bad/extra), error card,
   score header (result / perfect / unsure), record button + level meter, tabs, radio/check,
   combobox (normal/disabled), empty state, collapsed log, sparkline, pitch chart.
3. **Screen mockups** — every state from §2 list at 1480 × 940 and at minimum size:
   tab 1 ×4, tab 2 ×8, settings ×1, in light; 4 key ones in dark.
4. **Copy deck** — every new/changed Vietnamese string in one table (old → new).
5. Review with the user; record decisions as D-29… in `docs/DECISIONS.md`.

The mockup already shown in chat (scorecard with ring, chips, cards, labelled chart,
sparkline) is the starting point for item 3.

### 4.0 Open before GATE B (user feedback 2026-10-22)

User: the font "looks not modern" and the app "looks like a dashboard, not an application".
Added to the canvas: **Font options** (current Segoe UI vs A Segoe UI Variable — installed,
B Be Vietnam Pro — recommended, C Inter, D Lexend; B–D bundled as OFL files in `assets/` and
registered at start-up with `AddFontResourceExW(FR_PRIVATE)`, no pip package) and an
**app-style direction** for Tab 2 (navigation rail instead of tabs, no boxed cards, the target
sentence itself shows the result, a right-hand details panel, one primary action), light + dark,
with a `font` switch.

| Q | Question | Status |
|---|---|---|
| Q-08 | Which UI font: A, B, C or D? | **B — Be Vietnam Pro** (D-28) |
| Q-09 | Adopt the app-style direction (nav rail, no cards) for all screens? Model/language then move to the rail footer (changes Q-04 placement) | **Yes** (D-28); all artboards redone |

### 4.1 Delivered (2026-10-22, redone in app style after D-28) — 19 artboards

| Row | Artboards |
|---|---|
| Foundations | Token sheet (Be Vietnam Pro, surface tokens rail/content/side panel), Component sheet (both themes: nav item, segmented control, pill buttons, record button + meter, underlined result words, score ring, fix row, tip/info box, settings row with switch), Font options (B chosen) |
| Luyện phát âm | idle · recording · result EN · result VI · perfect · unsure — one component `PracticeResultEN` with `state`/`theme` |
| Dark / min / Văn bản / Cài đặt | result EN dark · minimum window 980×640 (icon-only rail) · Văn bản empty · YouTube source · processing · result · result dark (one component `SttResult`) · Cài đặt |
| Copy / shared | Copy deck: 35 strings old → new; shared `NavRail` |

Layout (supersedes S-6 three columns and S-9 header/tabs; D-28):
- **Navigation rail** 232 px (60 px icon-only at minimum size): Oriole, Chuyển thành văn bản,
  Luyện phát âm; footer: "Model small · Tự động ▾", Giao diện tối/sáng, Cài đặt.
- **Toolbar** 60 px per screen: title or lesson picker, segmented switch (Luyện câu | Học âm,
  or File | YouTube | Ghi âm), Bài trước / Bài sau.
- **Practice stage** (centre): "Đọc to câu này", the sentence at 30 pt (24 pt for long
  Vietnamese sentences); after scoring each word is underlined with "nghe ‘…’" or ✓ beneath;
  pill buttons ▶ Nghe mẫu / Chậm / Bản thu của bạn; tip box; big red record button with ring.
  The unsure state never colours the sentence.
- **Details panel** (right, 400 px practice / 320 px transcription): score ring + headline,
  CẦN SỬA rows, NGỮ ĐIỆU mini chart with word labels, progress sparkline, one primary button.
- **Transcription**: source bar under the toolbar, document view (max 720 px text, 12 pt,
  line 1.6) with Văn bản | Phụ đề SRT switch, panel with stats and export, collapsed log.
- **Settings**: Windows 11-style grouped rows (label left, control right), switches instead of
  checkboxes; header says "Thay đổi được lưu ngay" → **behaviour change: save on change**
  instead of the "Lưu cài đặt" button (add to S-1/B5).

Design choices to check at GATE B:
- Palette keeps today's blue; record red `#C8282E` in both themes; all text pairs ≥ 4.9 : 1.
- Tk feasibility: rail, rows and panels are Frames (square); pills, segmented control, switch,
  ring, meter, underlined words, sparkline are Canvas-drawn; record button is a circle.
- Microphone block lives in Cài đặt › Micro; practice shows one status line with “Đổi”.
- IPA line stays in Segoe UI until Be Vietnam Pro's IPA glyphs are verified in Tk (D-28).

## 5. Phase 3 — Build (5 increments, ~5–6 days total)

Each increment: code → smoke tests → `tools/ui_shots.py` → compare with design → docs →
user checks in the real app. Increments are ordered so each one is useful alone.

| Inc | Content | Closes | Est. |
|---|---|---|---|
| B1 Quick fixes ✅ | V-01…V-05, V-07, V-08, V-10, V-11, V-13, P-01, P-05, P-08 + font (D-28) | 13 issues, no layout change | done |
| B2 Foundations ✅ | S-1 state model, S-2 `build_result_view` + tests, keep word timings (S-5 data), history `tries` (S-7 data) | A-01, A-02, H-02 (+ H-03 data side) | done |
| B3 Trust and feedback | S-3 evidence gate, S-4 Vietnamese wording + `rhyme`, chips + cards drawn from view-model | P-02, P-03, P-04, P-06, P-07, P-09, P-10 | 1,5 d |
| B4 Layout and chart | S-6 practice layout, S-5 chart, S-7 progress UI, V-09, V-12, V-15 | P-11…P-13, C-01…C-04, H-01, H-03, V-09, V-12, V-15 | 1,5–2 d |
| B5 Tab 1 and polish | S-8, V-06, V-14, T-04, final contrast pass | T-01…T-04, V-06, V-14 | 0,5–1 d |

### 5.1 B1 result (2026-10-22)

- Done: Be Vietnam Pro bundled + registered (IPA stays Segoe UI: the font has 22/43 IPA
  symbols and no ▶ ✓ ✕ arrows; Tk falls back per glyph, which looked mismatched for IPA and
  acceptable for symbols); themed image indicators; disabled combobox/entry colours; tab
  baseline; larger combobox arrows; scrollbars on every text area; window icon; sash set at
  start-up; progress bars only while working; language names; "Sao chép"; result cleared
  on lesson change; no full-width tag bands; praise for perfect reads in every language.
- Tooling: `tools/ui_shots.py` (Phase 0) — 11 states, before/after sets in `%TEMP%`.
- Still open by design (later steps): score shown when unsure (B3), header/tabs and
  layout (B4), chart caption (B4), mic block placement (B4), settings auto-save (B5).
- Not verified: 100 % / 150 % Windows scaling (this PC is 250 %), real mic use.

### 5.2 B2 result (2026-10-22)

- `build_result_view(res, lesson)` + `_render_result_text(v)`: renderer reproduces the B1
  output **pixel-identically** (checked with `tools/ui_shots.py`, 11 states), so B3 only
  changes presentation. View already carries chips with heard words, GOP levels,
  headline/summary, `sounds`; `state` is always `result` until the D-29 gate (B3).
- State model: `stt_controls`/`prac_controls` + `App._set_stt_state`/`_set_prac_state`;
  `_set_busy` removed; all button/progress toggles go through them.
- `res["words_t"]` keeps word start/end; history `tries` (≤ 30) via `hist_add_try`;
  "Âm yếu nhất" per lesson language via `hist_weakest` — visible change: Vietnamese
  lessons no longer show English phoneme counts recorded under misdetection.
- Tests: 46/46 (8 new). Not verified: real mic recording through the new states.

Not in this plan: C-05 (needs real Vietnamese sample recordings — content work, Q-07).

## 6. Questions for the user (answer before GATE A)

**Answered 2026-10-22: user chose the defaults for all seven** (hide score when unsure ·
fraction headline · GOP numbers in a details toggle · model/language in header only ·
no drag & drop · 3-column practice layout · Vietnamese sample recordings later).

| Q | Question | Default if no answer |
|---|---|---|
| Q-01 | When the app is unsure, hide the score completely (recommended) or show it greyed out? | hide |
| Q-02 | Headline as a fraction "2/4 từ" (recommended) or keep a percentage "50%"? | fraction |
| Q-03 | Keep the detailed GOP numbers anywhere (details toggle) or drop them from the UI? | details toggle |
| Q-04 | Model/language controls: header only, Settings only, or both? | header only |
| Q-05 | Drag & drop files onto tab 1? Needs `tkinterdnd2` (small, but a new dependency) | no |
| Q-06 | Practice layout: 3 columns (roadmap Phase 2A) or improved 2 columns? | 3 columns |
| Q-07 | Record real Vietnamese sample sentences (enables chart + listen buttons for VI)? | later |

## 7. Phase 4 — Verification

- `tools/smoke_test.py`: new pure tests for `build_result_view` (VI errors, EN errors,
  perfect, unsure, hallucination phrases, extras), `rhyme` state, history migration,
  per-language weakest sound, chart caption rules, theme contrast.
- `tools/ui_shots.py`: full matrix before/after; side-by-side review against the mockups.
- `tools/context_check.py`, `py_compile`.
- Manual (user, real mic): 5 practice tries VI + EN, one noisy try, Esc mid-recording,
  switch lessons, dark mode, resize to minimum. Record results in HANDOFF; anything not
  tried is written as "chưa kiểm chứng".

## 8. Phase 5 — Documentation

- Skills: `app-ui` (state model, tokens, components), `app-pronunciation` (view-model,
  evidence gate, `rhyme`), `app-prosody` (labels, caption rules), `app-qa-release`
  (`ui_shots.py`, new tests, manual matrix rows).
- `docs/DECISIONS.md`: D-29 evidence gate, D-30 history `tries`, D-31 UI state model,
  D-32 design tokens/components (D-27 = GATE A answers, D-28 = font + app-style).
- `docs/ARCHITECTURE.md` §6 (result flow), `docs/FEATURES.md` §3, `README.md` screenshots
  and wording, `docs/context-map.json` new symbols, `PROJECT-STATE` + `HANDOFF`.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Tk widgets limit polish (no rounded corners, no shadows) | Draw chips, ring, meter, sparkline on `Canvas`; accept flat style |
| Canvas text at 250 % blurs or misaligns | Always size with `px()`; screenshot matrix per increment |
| Evidence gate hides scores for real but quiet learners | Thresholds behind constants + fixtures; review with real recordings (P4 calibration) |
| Bigger `app.py` | New UI code grouped in clearly named `App._view_*` methods; no package split (D-01) |
| Word timings missing with some models | Chart falls back to today's unlabeled version |
