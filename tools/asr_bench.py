#!/usr/bin/env python3
"""Đo chất lượng chuỗi thu âm → nhận dạng của tab Luyện phát âm.

Chạy đúng code của app: frames int16 ở rate gốc của mic → `save_frames_wav`
(resample + `enhance_audio`) → `transcribe_practice` → `score_pronunciation`
→ `evidence_gate`. In bảng WER / số từ đúng / cổng bằng chứng / thời gian.

Hai nguồn dữ liệu:
- Mặc định: câu mẫu trong `mau/` (TTS) + biến dạng giả lập mic (48 kHz, mic yếu,
  ồn, tiếng click). Chỉ để **so sánh trước/sau** một thay đổi của pipeline —
  TTS không dùng để hiệu chuẩn điểm (I13).
- `--dir THƯ_MỤC`: bản ghi người thật, mỗi `x.wav` (hoặc `.m4a/.mp3/.flac…`, giải mã bằng
  ffmpeg) kèm `x.txt` (dòng 1 = câu mẫu). Chạy nguyên trạng, không thêm biến dạng.
  Lưu ý: bản m4a từ app Ghi âm của Windows (2026-10-24) có nền giữa các từ gần 0 (lọc ồn)
  nên SNR chạm trần 60 dB; muốn đo SNR phải thu bằng chính app (tab Luyện).

Ví dụ:
    python tools\\asr_bench.py --out bench_before.json
    python tools\\asr_bench.py --compare bench_before.json
    python tools\\asr_bench.py --asr vad_filter=false --asr temperature=0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

import app  # noqa: E402

MIC_RATE = 48000

# Biến dạng giả lập: (tên, đỉnh giọng, RMS ồn trắng ở 48 kHz, có click).
# Ồn trắng 48 kHz có 2/3 năng lượng trên 8 kHz — chính phần resample phải lọc bỏ.
CONDITIONS = (
    ("clean48k", 0.30, 0.0, False),
    ("weak", 0.02, 0.0004, False),      # mic array laptop (D-21): đỉnh ~2 %
    ("weak_click", 0.02, 0.0004, True),  # như trên + một tiếng gõ bàn
    ("noisy", 0.10, 0.0060, False),     # phòng ồn, SNR thấp
)


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        sr, nch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError("chỉ hỗ trợ WAV 16-bit: %s" % path)
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)
    return x, sr


AUDIO_EXTS = (".wav", ".m4a", ".mp3", ".flac", ".ogg", ".aac", ".wma")


def read_audio(path):
    """WAV 16-bit đọc trực tiếp; định dạng khác (m4a của Ghi âm Windows…) giải mã bằng
    ffmpeg của app sang mono 48 kHz — giữ rate mic để chạy qua bộ resample của app."""
    if path.suffix.lower() == ".wav":
        return read_wav(path)
    import subprocess
    ff = app.yt_ffmpeg_location()
    if not ff:
        raise RuntimeError("thiếu ffmpeg (imageio-ffmpeg) để đọc %s" % path.name)
    raw = subprocess.run([ff, "-v", "error", "-i", str(path), "-ac", "1", "-ar",
                          str(MIC_RATE), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0, MIC_RATE


def builtin_items():
    """Câu mẫu có sẵn: câu mẫu tiếng Việt cơ bản (giọng TTS — chỉ so trước/sau, I13)."""
    items = [("vi_cau", ROOT / "mau" / "vi_cau.wav", "Lan năm nay lên lớp.", "vi")]
    return [it for it in items if it[1].exists()]


def dir_items(folder):
    items = []
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() not in AUDIO_EXTS or p.stem.endswith("_goc"):
            continue   # x_goc.wav = đoạn gốc YouTube do "Lưu bản thu…" lưu kèm, không phải bản đọc
        t = p.with_suffix(".txt")
        if not t.exists():
            print("bỏ qua %s (thiếu %s)" % (p.name, t.name))
            continue
        target = t.read_text(encoding="utf-8").splitlines()[0].strip()
        lang = app.guess_lang(target) if hasattr(app, "guess_lang") else "auto"
        items.append((p.stem, p, target, lang or "auto"))
    return items


def degrade(x, sr, peak, noise_rms, click, seed):
    """Giả lập mic: đưa lên 48 kHz, chỉnh đỉnh giọng, thêm ồn trắng/click."""
    rng = np.random.default_rng(seed)
    n = int(round(len(x) * MIC_RATE / float(sr)))
    # upsample nội suy tuyến tính: giọng TTS không có năng lượng > 8 kHz, ồn thì có
    y = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    y = np.concatenate([np.zeros(MIC_RATE // 2), y, np.zeros(MIC_RATE // 2)])  # đệm 0,5 s
    y = y / max(1e-9, float(np.max(np.abs(y)))) * peak
    if noise_rms:
        y = y + rng.standard_normal(len(y)) * noise_rms
    if click:
        i = MIC_RATE // 4
        y[i:i + 24] += 0.6 * np.hanning(24)
    return (np.clip(y, -1, 1) * 32767).astype(np.int16), MIC_RATE


def wer(target, hyp):
    t, h = app.norm_words(target), app.norm_words(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(t) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (t[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)] / float(max(1, len(t)))


def run_one(model, frames, rate, target, lang, overrides):
    t0 = time.time()
    path, secs, info = app.save_frames_wav([frames], "bench_", rate)
    t_front = time.time() - t0
    try:
        t0 = time.time()
        asr = app.transcribe_practice(model, path, lang, **overrides)
        t_asr = time.time() - t0
    finally:
        app.remove_temp(path)
    res = app.score_pronunciation(target, asr["hyp"], lang)
    res["target"] = target
    probs = asr["probs"]
    res["conf"] = (sum(probs) / len(probs)) if probs else 1.0
    res["low_conf"] = bool(probs) and res["conf"] < 0.35
    res["words_t"], res["det_lang"] = asr["words_t"], lang
    gate = app.evidence_gate(res) if asr["hyp"] else "empty"
    # từ chấm đúng nhưng Whisper nghe với xác suất thấp ("máy chưa chắc", D-37)
    unsure = len(app.build_result_view(res).get("unsure_words") or {}) if asr["hyp"] else 0
    # xác suất Whisper của các từ chấm ĐÚNG — để chọn ngưỡng WORD_UNSURE_P từ dữ liệu
    ok_ti = {i for i, it in enumerate(t for t in res["items"] if t[0] is not None)
             if it[1] == "ok"}
    idx = app.map_to_target(target, [w["w"] for w in asr["words_t"]])
    ok_p = [round(w["p"], 3) for w, ti in zip(asr["words_t"], idx) if ti in ok_ti]
    # …và của từ chấm SAI — ngưỡng chỉ có ích nếu hai nhóm tách nhau
    bad_p = [round(w["p"], 3) for w, ti in zip(asr["words_t"], idx)
             if ti is not None and ti not in ok_ti]
    return {"hyp": asr["hyp"], "wer": round(wer(target, asr["hyp"]), 3),
            "correct": res["correct"], "total": res["total"],
            "conf": round(res["conf"], 3), "gate": gate,
            "peak0": round(float(info.get("peak0", 0)), 4),
            "snr_db": info.get("snr_db"), "unsure": unsure, "ok_p": ok_p, "bad_p": bad_p,
            "t_front": round(t_front, 3), "t_asr": round(t_asr, 3)}


def parse_overrides(pairs):
    out = {}
    for kv in pairs or []:
        k, _, v = kv.partition("=")
        lv = v.strip().lower()
        if lv in ("true", "false"):
            out[k] = lv == "true"
        else:
            try:
                out[k] = float(v) if "." in v else int(v)
            except ValueError:
                out[k] = v
    return out


def summarize(rows):
    by = {}
    for r in rows:
        by.setdefault(r["cond"], []).append(r)
    out = {}
    for cond, rs in by.items():
        out[cond] = {
            "n": len(rs),
            "wer": round(float(np.mean([r["wer"] for r in rs])), 3),
            "correct": sum(r["correct"] for r in rs),
            "total": sum(r["total"] for r in rs),
            "gated": sum(1 for r in rs if r["gate"]),
            "unsure": sum(r.get("unsure", 0) for r in rs),
            "snr_db": round(float(np.median([r["snr_db"] for r in rs
                                             if r.get("snr_db") is not None] or [0])), 1),
            "t_front": round(sum(r["t_front"] for r in rs), 2),
            "t_asr": round(sum(r["t_asr"] for r in rs), 2)}
    return out


def print_summary(summ, old=None):
    print("\n%-11s %4s %7s %11s %6s %7s %7s %8s %7s" % (
        "điều kiện", "n", "WER", "đúng/tổng", "chặn", "chưa_ch", "SNR dB", "front s", "asr s"))
    for cond, s in summ.items():
        line = "%-11s %4d %7.3f %5d/%-5d %6d %7d %7.1f %8.2f %7.2f" % (
            cond, s["n"], s["wer"], s["correct"], s["total"], s["gated"],
            s.get("unsure", 0), s.get("snr_db", 0), s["t_front"], s["t_asr"])
        o = (old or {}).get(cond)
        if o:
            line += "   (trước: WER %.3f, đúng %d, chặn %d)" % (o["wer"], o["correct"],
                                                              o["gated"])
        print(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="base",
                    help="cỡ Whisper (mặc định base); bài Việt trong app dùng small (D-37)")
    ap.add_argument("--dir", help="thư mục bản ghi thật (x.wav + x.txt)")
    ap.add_argument("--only", help="chỉ chạy item có tên chứa chuỗi này")
    ap.add_argument("--asr", action="append", metavar="KEY=VALUE",
                    help="ghi đè tham số Whisper, vd vad_filter=false")
    ap.add_argument("--out", help="ghi kết quả JSON")
    ap.add_argument("--compare", help="JSON của lần chạy trước để so")
    ap.add_argument("-v", "--verbose", action="store_true", help="in từng dòng")
    a = ap.parse_args()

    overrides = parse_overrides(a.asr)
    items = dir_items(a.dir) if a.dir else builtin_items()
    if a.only:
        items = [it for it in items if a.only in it[0]]
    conds = (("real", None, None, None),) if a.dir else CONDITIONS
    print("model %s · %d mẫu × %d điều kiện · ghi đè %s" % (a.model, len(items),
                                                         len(conds), overrides or "-"))
    rows = []
    for k, (name, path, target, lang) in enumerate(items):
        # chọn model như app (bài Việt dùng small nếu đã có trên máy — practice_model)
        model = app.load_model(app.practice_model(a.model, lang)[0])
        x, sr = read_audio(path)
        for cname, peak, noise, click in conds:
            if a.dir:
                frames, rate = (np.clip(x, -1, 1) * 32767).astype(np.int16), sr
            else:
                frames, rate = degrade(x, sr, peak, noise, click, seed=k)
            r = run_one(model, frames, rate, target, lang, overrides)
            r.update({"item": name, "cond": cname, "target": target})
            rows.append(r)
            if a.verbose:
                print("%-16s %-10s WER %.2f %d/%d %-13s %s" % (
                    name, cname, r["wer"], r["correct"], r["total"], r["gate"] or "",
                    r["hyp"]))
    summ = summarize(rows)
    old = None
    if a.compare:
        with open(a.compare, encoding="utf-8") as f:
            old = json.load(f).get("summary")
    print_summary(summ, old)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"model": a.model, "overrides": overrides, "summary": summ,
                       "rows": rows}, f, ensure_ascii=False, indent=1)
        print("đã ghi %s" % a.out)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
