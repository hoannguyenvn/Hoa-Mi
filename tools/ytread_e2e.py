#!/usr/bin/env python3
"""Chạy thật màn "Từ YouTube" (D-39) không cần micro: App thật → dán link → Lấy transcript
→ "bản thu của người học" = chính đoạn gốc của video (cắt từ audio gốc) → chấm qua đúng
worker/queue của app. Đọc gốc thì phải gần như đúng hết; in kết quả + lỗi callback.

Cần mạng (YouTube) + model Whisper. Không ghi config/lịch sử.
    python tools\\ytread_e2e.py https://youtu.be/<id> [chỉ_số_đoạn]
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import app  # noqa: E402

app.save_config = lambda cfg: None
app.App._save_hist = lambda self: None


def wait(A, cond, secs):
    t0 = time.time()
    while not cond() and time.time() - t0 < secs:
        A.update()
        time.sleep(0.05)
    return cond()


def main():
    url = sys.argv[1]
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    A = app.App()
    errors = []
    A.report_callback_exception = lambda *a: errors.append(a[1])
    A._show_screen("prac")
    A.prac_mode.set("yt")
    A._prac_mode_changed()
    A.yt_read_url.set(url)
    t0 = time.time()
    A._yt_load()
    ok = wait(A, lambda: A.prac_state != "loading", 300)
    s = A._yt_sess
    print("tải: %.1f s · trạng thái %s · %s" % (time.time() - t0, A.prac_state, A.p_status.get()))
    if not ok or not s:
        A.destroy()
        return 1
    print("video: %s · %d đoạn · %s" % (s.title, len(s.paragraphs), s.sub_kind))
    for _ in range(idx):
        A._step_lesson(1)
    p = s.paragraphs[A._yt_idx]
    print("đoạn %d: %s" % (A._yt_idx + 1, p["text"][:120]))
    # "người học" đọc = chính audio gốc của đoạn
    fd, wav = tempfile.mkstemp(prefix="luyen_e2e_", suffix=".wav")
    os.close(fd)
    with wave.open(s.wav, "rb") as r, wave.open(wav, "wb") as w:
        a, b = app.wav_segment_bounds(r.getnframes(), r.getframerate(), p["start"], p["end"], 0.3)
        r.setpos(a)
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(r.getframerate())
        w.writeframes(r.readframes(b - a))
    A._set_last_wav(wav)
    t0 = time.time()
    A._prac_score(wav)
    wait(A, lambda: A.prac_state != "scoring", 300)
    v = A._yt_view
    print("chấm: %.1f s · trạng thái %s" % (time.time() - t0, A.prac_state))
    if v:
        print("  %s · %s" % (v["headline"], v["summary"]))
        for f in v["fixes"][:8]:
            print("  sửa:", f["text"])
        for d in v["doubts"][:8]:
            print("  phụ đề?:", d["text"])
        rows = [w for w in A.pp_yt.winfo_children()]
        print("  dòng panel: %d" % len(rows))
        flu = getattr(A, "_yt_flu", None) or {}
        for ln in flu.get("lines", []):
            print("  trôi chảy:", ln)
        print("  %d câu" % len(flu.get("sentences", [])))
    # "Lưu bản thu…" ra thư mục tạm (không hỏi hộp thoại)
    out = tempfile.mkdtemp(prefix="oriole_e2e_save_")
    app.filedialog.asksaveasfilename = lambda **kw: os.path.join(out, kw["initialfile"])
    A._save_recording()
    saved = sorted(os.listdir(out))
    print("đã lưu:", saved)
    kept = A.last_wav
    A._yt_step(1)                       # đổi đoạn → màn của đoạn mới, bản thu đoạn cũ được giữ
    print("sau Đoạn sau: kết quả %s · last_wav %s · file cũ còn %s" % (
        A._yt_view, A.last_wav, os.path.exists(kept)))
    A._yt_step(-1)                      # quay lại → kết quả + bản thu hiện lại
    print("quay lại: %s · last_wav khớp %s" % (
        A._yt_view and A._yt_view["headline"], A.last_wav == kept))
    work = s.work_dir
    A._on_close()
    print("thư mục phiên còn không:", bool(work and os.path.exists(work)),
          "· bản thu giữ còn không:", os.path.exists(kept))
    import shutil
    shutil.rmtree(out, ignore_errors=True)
    print("lỗi callback:", errors or "không")
    return 1 if errors else 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    raise SystemExit(main())
