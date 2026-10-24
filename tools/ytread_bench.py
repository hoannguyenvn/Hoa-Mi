#!/usr/bin/env python3
"""Đo phần chuẩn bị của "Đọc to transcript YouTube" (D-39) trên video thật.

Với mỗi link: `ytread_prepare` (phụ đề tiếng Anh + audio gốc) → chia đoạn → Whisper nghe
từng đoạn GỐC → `read_aloud_diff(phụ đề, lời gốc, lời gốc)`. Từ không khớp ở bước này là
**trần** số từ "phụ đề có thể sai" mà người học sẽ thấy (người đọc đúng y phụ đề vẫn bị
ghi các từ này). Cần mạng (YouTube) + model Whisper.

Ví dụ:
    python tools\\ytread_bench.py https://youtu.be/<id> --paras 4 -v
    python tools\\ytread_bench.py <link> --prefer auto      # phụ đề tự động thay thủ công
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402


def bench(url, model_size, paras, prefer, verbose):
    t0 = time.time()
    s = app.ytread_prepare(url, model_size, prefer=prefer)
    try:
        t_prep = time.time() - t0
        ps = s.paragraphs
        print("\n%s\n  phụ đề %s · %d đoạn · chuẩn bị %.1f s" % (s.title, s.sub_kind, len(ps), t_prep))
        model = app.load_model(model_size)
        tot = doubt = 0
        t0 = time.time()
        for i, p in enumerate(ps[:paras]):
            orig = app.ytread_orig_hyp(s, i, model)
            if orig is None:
                print("  (transcript do Whisper tạo — không đo được phụ đề sai)")
                break
            r = app.read_aloud_diff(p["text"], orig, orig)
            n = r["total"] + r["doubts"]
            tot, doubt = tot + n, doubt + r["doubts"]
            print("  đoạn %d  %5.1f–%5.1f s  %3d từ  %3d wpm  nghi phụ đề sai %d (%.0f%%)" % (
                i + 1, p["start"], p["end"], p["words"], p["wpm"], r["doubts"],
                100.0 * r["doubts"] / max(1, n)))
            if verbose:
                bad = [(it[0], it[2]) for it in r["items"] if it[1] == "doubt"]
                print("     ", ", ".join("%s→%s" % (t, h or "∅") for t, h in bad[:12]))
        if tot:
            print("  TỔNG nghi phụ đề sai: %d/%d token (%.1f%%) · Whisper gốc %.1f s" % (
                doubt, tot, 100.0 * doubt / tot, time.time() - t0))
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--model", default="base")
    ap.add_argument("--paras", type=int, default=4, help="số đoạn đầu để đo (mặc định 4)")
    ap.add_argument("--prefer", choices=("manual", "auto"), default="manual")
    ap.add_argument("-v", "--verbose", action="store_true", help="in các từ nghi sai")
    a = ap.parse_args()
    for u in a.urls:
        try:
            bench(u, a.model, a.paras, a.prefer, a.verbose)
        except Exception as e:
            print("\n%s\n  LỖI: %s" % (u, e))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
