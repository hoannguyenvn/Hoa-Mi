#!/usr/bin/env python3
"""Chạy App thật (Tk) qua các màn hình/bài/kết quả giả — báo lỗi nếu callback Tk ném ngoại lệ.

Không cần mic/model/mạng; KHÔNG ghi config.json / learners.json. Chạy được trên Windows
và Linux (CI dùng Xvfb). Có Pillow thì chụp ảnh từng bước vào thư mục chỉ định.

    python tools/ui_check.py                 # chỉ kiểm tra
    python tools/ui_check.py --shots DIR     # kèm ảnh PNG (cần Pillow)

Exit code 0 = không có lỗi callback, 1 = có lỗi.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import app  # noqa: E402

# ---- an toàn: không đụng file của người dùng ----
app.save_config = lambda cfg: None
app.learners_save = lambda *a, **k: True
app.App._save_hist = lambda self: None
app.App._record_hist = lambda self, *a, **k: None

EMPTY_PHON = {"issues": [], "counts": {}, "top": [], "by_phoneme": {}, "unknown": []}


def fake_result(target, hyp, lang):
    res = app.score_pronunciation(target, hyp, lang)
    res.update(target=target, words_t=[], model="base", det_lang=lang, conf=0.9,
               low_conf=False, garbage=False, phon=dict(EMPTY_PHON), inton=None,
               stress=None, gop=None)
    return res


def one_error(target):
    """Đổi một chữ để kết quả có lỗi (n↔l nếu có, không thì bỏ từ cuối)."""
    for a, b in (("n", "l"), ("l", "n"), ("N", "L"), ("L", "N")):
        if a in target:
            return target.replace(a, b, 1)
    return " ".join(target.split()[:-1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", help="thư mục ghi ảnh PNG (cần Pillow)")
    args = ap.parse_args()
    grab = None
    if args.shots:
        os.makedirs(args.shots, exist_ok=True)
        try:
            from PIL import ImageGrab
            grab = ImageGrab.grab
        except Exception:
            print("Không có Pillow — bỏ qua chụp ảnh.")

    errors: list[str] = []
    a = app.App()
    a.report_callback_exception = lambda e, v, tb: errors.append(
        "".join(traceback.format_exception(e, v, tb)))
    a.geometry("1400x900+0+0")

    def step(name, fn=None):
        try:
            if fn:
                fn()
            a.update()
            a.update_idletasks()
        except Exception:
            errors.append("%s:\n%s" % (name, traceback.format_exc()))
        if grab:
            x, y = a.winfo_rootx(), a.winfo_rooty()
            grab(bbox=(x, y, x + a.winfo_width(), y + a.winfo_height())).save(
                os.path.join(args.shots, name + ".png"))

    step("00_start")
    for key in list(a.screens):
        step("01_screen_" + key, lambda k=key: a._show_screen(k))
    step("02_prac", lambda: a._show_screen("prac"))
    for i, sid in enumerate(app.SET_IDS):
        if sid == "custom":
            continue

        def scored(i=i, sid=sid):
            a._set_prac_mode("set")
            a.cb_prac.current(i)
            a._refresh_practice()
            lang = app.PRACTICE_SETS[sid]["lang"]
            a._prac_done(fake_result(a._p_target, one_error(a._p_target), lang))
        step("10_result_" + sid, scored)
    step("20_guide", lambda: a._set_prac_mode("guide"))
    for i, gid in enumerate(app.GUIDE_IDS):
        step("21_guide_" + gid, lambda i=i: (a.cb_prac.current(i), a._refresh_practice()))
    step("30_set", lambda: a._set_prac_mode("set"))
    step("31_dark", a._toggle_theme)
    step("32_narrow", lambda: a.geometry("1000x760+0+0"))
    step("33_light", a._toggle_theme)
    a.destroy()

    for e in errors:
        print(e)
    print("ui_check: %d lỗi callback" % len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
