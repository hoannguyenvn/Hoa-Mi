import os
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # tắt cảnh báo symlink dài dòng của huggingface trên Windows

try:  # chữ nét hơn trên màn hình DPI cao (Windows)
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import difflib
import json
import math
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import wave
from tkinter import filedialog, messagebox, ttk
from datetime import timedelta

import gop  # chấm âm vị bằng model acoustic (wav2vec2 CTC) — tùy chọn
import pron_en  # phân tích âm vị tiếng Anh (CMUdict + căn chỉnh âm vị)
import prosody  # phân tích ngữ điệu (cao độ) bằng numpy

APP_TITLE = "Oriole"
VERSION = "2.3"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAU_DIR = os.path.join(BASE_DIR, "mau")  # thư viện âm mẫu giọng bản ngữ (offline)
HISTORY_PATH = os.path.join(BASE_DIR, "practice_history.json")
LESSONS_PATH = os.path.join(BASE_DIR, "lessons_en.json")

SUPPORTED = [
    ("Audio/Video", "*.mp3 *.wav *.m4a *.flac *.ogg *.wma *.mp4 *.mov *.avi *.mkv *.webm"),
    ("Tất cả file", "*.*"),
]

# ---------- tải video YouTube (yt-dlp + ffmpeg) ----------
YT_DIR_DEFAULT = os.path.join(BASE_DIR, "downloads")
YT_FORMATS = [("video", "Video MP4"), ("audio", "Chỉ audio MP3")]
YT_QUALITIES = [("best", "Tốt nhất (mp4)"), ("1080", "1080p"), ("720", "720p"),
                ("480", "480p"), ("360", "360p")]
YT_FMT_BY_NAME = {n: c for c, n in YT_FORMATS}
YT_QUAL_BY_NAME = {n: c for c, n in YT_QUALITIES}
YT_SUB_LANGS = [("auto", "Tự động (ưu tiên tiếng Việt)"), ("vi", "Tiếng Việt"),
                ("en", "Tiếng Anh")]
YT_SUB_LANG_NAMES = [n for _, n in YT_SUB_LANGS]
YT_SUB_LANG_BY_NAME = {n: c for c, n in YT_SUB_LANGS}
YT_HINT = ("Dán link YouTube (dạng youtu.be/... hoặc watch?v=...). Tải về rồi xem offline; "
           "chọn “Chỉ audio MP3” để nạp thẳng vào tab 1 (chuyển audio → text).")

MODELS = ["tiny", "base", "small", "medium"]
MODEL_DESC = {"tiny": "nhanh nhất", "base": "nhanh",
              "small": "chuẩn — khuyên dùng cho tiếng Việt", "medium": "chuẩn nhất, chậm nhất"}
LANGS = ["auto", "vi", "en", "zh", "ja", "ko", "fr", "de"]
# Tên hiển thị cho ô Ngôn ngữ (V-13); biến self.lang vẫn giữ mã ("auto", "vi"…).
LANG_LABELS = [("auto", "Tự động"), ("vi", "Tiếng Việt"), ("en", "Tiếng Anh"),
               ("zh", "Tiếng Trung"), ("ja", "Tiếng Nhật"), ("ko", "Tiếng Hàn"),
               ("fr", "Tiếng Pháp"), ("de", "Tiếng Đức")]
LANG_NAMES = [n for _, n in LANG_LABELS]
LANG_BY_NAME = {n: c for c, n in LANG_LABELS}
LANG_NAME = {c: n for c, n in LANG_LABELS}

# ---------- font giao diện (D-28) ----------
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")
UI_FONT_FILES = ("BeVietnamPro-Regular.ttf", "BeVietnamPro-SemiBold.ttf",
                 "BeVietnamPro-Bold.ttf")
UI_FONT_PREFS = ("Be Vietnam Pro", "Segoe UI Variable Text", "Segoe UI")
# Be Vietnam Pro thiếu 21/43 ký tự IPA (θ ŋ ə ɪ ʃ ˈ…): Tk mượn glyph font khác nên
# dòng IPA lẫn cỡ chữ. IPA và nhãn âm vị luôn dùng Segoe UI (đủ 43/43).
FONT_IPA = "Segoe UI"

REC_RATE = 16000          # đích sau khi resample (Whisper cần 16k mono)
REC_MAX_SEC = 180
REC_TARGET_PEAK = 0.70  # -3dB: đủ to mà không rè/vỡ khi phát lại
REC_FADE_MS = 8         # fade đầu/cuối chống "tách" khi cắt im lặng
REC_GAIN_MAX = 16.0     # +24dB: đủ kéo micro array yếu lên mức Whisper nghe được
MIC_MIN_PEAK = 0.008    # -42dB: sàn "có tín hiệu"; nền nhiễu mic thường < 0,1%
MIC_GOOD_PEAK = 0.03    # dưới mức này: cảnh báo "đầu vào hơi nhỏ"

PRACTICE_SETS = {
    "vi1": {"name": "Việt 1 — Câu ngắn (n/l)", "lang": "vi",
            "target": "Lan năm nay lên lớp, nói năng lưu loát lắm.",
            "hint": "Đọc chậm, phân biệt rõ n và l ở đầu mỗi chữ."},
    "vi2": {"name": "Việt 2 — Câu dài (n/l)", "lang": "vi",
            "target": "Nắng lên, lúa non lên xanh. Lan lo làm nương, Nam lo nấu nướng.",
            "hint": "Chú ý các chữ: nắng, non, Lan, lo, làm, nương, Nam, nấu, nướng."},
    "vi3": {"name": "Việt 3 — Cặp tối thiểu na/la…", "lang": "vi",
            "target": "na la, năm lăm, nên lên, no lo, ni li, nu lu",
            "hint": "Đọc từng cặp, ngắt nhịp rõ giữa hai chữ."},
    "en1": {"name": "Anh 1 — Âm th", "lang": "en",
            "target": "Think about this: three thousand thanks.",
            "hint": "Đặt đầu lưỡi giữa hai răng cho âm th."},
    "en2": {"name": "Anh 2 — s và sh", "lang": "en",
            "target": "She sells seashells by the seashore.",
            "hint": "Phân biệt s (xì nhẹ) và sh (chu môi, xì mạnh)."},
    "en3": {"name": "Anh 3 — Âm cuối", "lang": "en",
            "target": "I like cats and dogs, big and small.",
            "hint": "Bật rõ phụ âm cuối: -ke, -ts, -gs, -g, -ll."},
    "custom": {"name": "Tùy chỉnh — tự gõ câu", "lang": "auto",
               "target": "",
               "hint": "Gõ câu của bạn vào ô bên dưới (Việt hoặc Anh)."},
}
_VI_IDS = ["vi1", "vi2", "vi3"]


def load_en_lessons():
    """Nạp lessons_en.json vào PRACTICE_SETS; trả list id (rỗng nếu lỗi)."""
    try:
        with open(LESSONS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    ids = []
    for L in data.get("lessons") or []:
        lid = L.get("id")
        if not lid:
            continue
        words = L.get("words") or []
        samples = [("Cả câu", "en/%s.wav" % lid),
                   ("Chậm", "en/%s_slow.wav" % lid)]
        samples += [(w, "en/w_%s.wav" % w) for w in words[:2]]
        hint = L.get("hint") or ""
        if L.get("focus_ipa"):
            hint = ("Âm trọng tâm: %s." % L["focus_ipa"]) + \
                   (("  " + hint) if hint else "")
        pairs = L.get("pairs") or []
        if pairs:
            hint += "  ·  Cặp dễ lẫn: " + ", ".join(
                "%s–%s" % (a, b) for a, b in pairs[:3])
        PRACTICE_SETS[lid] = {
            "name": L.get("title") or lid, "lang": "en",
            "target": L.get("target") or "", "hint": hint.strip(),
            "ipa": L.get("ipa") or "", "tips": L.get("tips") or [],
            "samples": samples, "id": lid,
        }
        ids.append(lid)
    return ids


SET_IDS = _VI_IDS + load_en_lessons() + ["custom"]
SET_NAMES = [PRACTICE_SETS[k]["name"] for k in SET_IDS]

GUIDES = {
    "n": {"name": "Âm N — tiếng Việt", "lang": "vi", "target": "na năm nên",
          "instruction": ("1. Đầu lưỡi đặt CHẶT vào lợi trên (gờ cứng ngay sau chân răng cửa hàm trên), "
                          "bít kín đường miệng.\n"
                          "2. Dồn hơi lên MŨI, tiếng thoát ra bằng mũi. Cổ họng rung.\n"
                          "3. Tự kiểm tra: BỊT MŨI rồi đọc “na” — đúng âm N thì tiếng nghẹt hẳn.\n"
                          "Lỗi hay gặp: đặt lưỡi hờ, hơi thoát ra miệng → thành L (“năm” thành “lăm”)."),
          "samples": [("na", "vi_na.wav"), ("năm", "vi_nam.wav"), ("nên", "vi_nen.wav")]},
    "l": {"name": "Âm L — tiếng Việt", "lang": "vi", "target": "la lăm lên",
          "instruction": ("1. Đầu lưỡi chạm NHẸ vào lợi trên (đúng chỗ của N nhưng chạm hờ, không bít kín).\n"
                          "2. Hai bên mép lưỡi hạ xuống, hơi thoát ra HAI BÊN (qua miệng, không qua mũi). "
                          "Cổ họng rung.\n"
                          "3. Tự kiểm tra: BỊT MŨI rồi đọc “la” — tiếng vẫn ra bình thường.\n"
                          "Lỗi hay gặp: ấn lưỡi quá chặt + đẩy hơi lên mũi → thành N (“lên” thành “nên”)."),
          "samples": [("la", "vi_la.wav"), ("lăm", "vi_lam.wav"), ("lên", "vi_len.wav")]},
    "nl": {"name": "So sánh N – L", "lang": "vi", "target": "na la năm lăm nên lên",
           "instruction": ("Đọc xen kẽ từng cặp, giữ nguyên vị trí lưỡi, chỉ đổi đường thoát hơi "
                           "(mũi/miệng): na–la, năm–lăm, nên–lên.\n"
                           "Mẹo nhớ: BỊT MŨI — N thì nghẹt, L thì vẫn ra.\n"
                           "Bấm “Thu âm & kiểm tra” rồi xem máy nghe ra chữ nào."),
           "samples": [("na", "vi_na.wav"), ("la", "vi_la.wav"), ("câu mẫu", "vi_cau.wav")]},
    "th": {"name": "Âm TH — tiếng Anh", "lang": "en", "target": "think this three thanks",
           "instruction": ("1. Đặt ĐẦU LƯỠI GIỮA hai răng cửa, thổi hơi ra ngoài.\n"
                           "2. “think” (không rung) và “this” (rung cổ họng).\n"
                           "Lỗi người Việt hay gặp: rụt lưỡi vào trong → thành t/d (“think” thành “tink”)."),
           "samples": [("think", "en_think.wav"), ("this", "en_this.wav")]},
    "sh": {"name": "S và SH — tiếng Anh", "lang": "en", "target": "she sea sells seashells",
           "instruction": ("“s” (sea): lưỡi gần lợi, môi bình thường, xì nhẹ.\n"
                           "“sh” (she): CHU MÔI tròn, lưỡi lùi lại, xì mạnh.\n"
                           "Lỗi hay gặp: đọc “sh” thành “s” (“she” thành “see”)."),
           "samples": [("she", "en_she.wav"), ("sea", "en_sea.wav"), ("câu mẫu", "en_cau.wav")]},
}
GUIDE_IDS = ["n", "l", "nl", "th", "sh"]
GUIDE_NAMES = [GUIDES[k]["name"] for k in GUIDE_IDS]


def format_time(s):
    return str(timedelta(seconds=int(s)))


# ---------- phụ đề: mốc thời gian, SRT/VTT -> SRT chuẩn ----------
def clock_time(sec):
    """00:01:23 — dùng để hiển thị/xuất text kèm mốc thời gian."""
    sec = max(0, int(sec or 0))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def short_duration(sec):
    """0:18 · 12:05 · 1:02:03 — thời lượng gọn cho thẻ thống kê."""
    sec = max(0, int(round(sec or 0)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def srt_time(sec):
    """00:01:23,456 — chuẩn SubRip (dấu phẩy cho phần mili giây)."""
    ms = max(0, int(round(float(sec or 0) * 1000)))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


_TS_RE = re.compile(r"(?:(\d+):)?(\d{1,3}):(\d{2})(?:[.,](\d{1,3}))?")
_SUB_TAG_RE = re.compile(r"<[^>]*>")
_SUB_BRACE_RE = re.compile(r"\{\\[^}]*\}")
_HTML_ENTS = {"&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
              "&quot;": '"', "&#39;": "'", "&apos;": "'"}


def _parse_ts(txt):
    """Đọc '00:01:02,500' / '01:02.500' / '62.5' -> giây (float)."""
    txt = (txt or "").strip()
    m = _TS_RE.search(txt)
    if not m:
        try:
            return float(txt)
        except ValueError:
            return 0.0
    h = int(m.group(1) or 0)
    mi = int(m.group(2))
    s = int(m.group(3))
    frac = (m.group(4) or "0").ljust(3, "0")[:3]
    return h * 3600 + mi * 60 + s + int(frac) / 1000.0


def _clean_cue(s):
    s = _SUB_TAG_RE.sub("", s or "")
    s = _SUB_BRACE_RE.sub("", s)
    for k, v in _HTML_ENTS.items():
        s = s.replace(k, v)
    return " ".join(s.split())


def _parse_sub_text(text):
    """Đọc nội dung .srt hoặc .vtt -> [(start, end, text)] (chưa lọc trùng)."""
    norm = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    norm = norm.replace("\ufeff", "")
    cues = []
    start = None
    end = 0.0
    body = []

    def flush():
        nonlocal start, end, body
        if start is not None:
            tx = _clean_cue(" ".join(body))
            if tx:
                cues.append((start, end, tx))
        start, end, body = None, 0.0, []

    for ln in norm.split("\n"):
        if "-->" in ln:
            flush()
            left, _, right = ln.partition("-->")
            start = _parse_ts(left)
            end = _parse_ts(right.strip().split()[0] if right.strip() else "")
            continue
        if start is None:          # WEBVTT / NOTE / số thứ tự SRT…
            continue
        if not ln.strip():         # dòng trắng: YouTube chèn ngay sau mốc giờ
            if body:
                flush()
            continue
        body.append(ln)
    flush()
    return cues


def _parse_json3(text):
    """Phụ đề json3 của YouTube (chỉ dùng khi không có vtt/srt)."""
    cues = []
    try:
        data = json.loads(text)
    except Exception:
        return cues
    for ev in data.get("events") or []:
        body = _clean_cue("".join(s.get("utf8") or "" for s in (ev.get("segs") or [])))
        if not body:
            continue
        st = (ev.get("tStartMs") or 0) / 1000.0
        du = (ev.get("dDurationMs") or 0) / 1000.0
        cues.append((st, st + du, body))
    return cues


def _dedupe_cues(cues):
    """Gộp phụ đề tự động của YouTube (dạng chạy chữ, lặp lại từng dòng)."""
    out = []
    for st, en, tx in cues:
        tx = " ".join((tx or "").split())
        if not tx:
            continue
        if out:
            pst, pen, ptx = out[-1]
            if tx == ptx:
                out[-1] = (pst, max(pen, en), ptx)
                continue
            if ptx.endswith(tx):        # dòng cũ đã chứa trọn dòng mới
                out[-1] = (pst, max(pen, en), ptx)
                continue
            if tx.startswith(ptx):      # dòng mới dài hơn: giữ bản đầy đủ
                out[-1] = (pst, max(pen, en), tx)
                continue
            # phụ đề tự động dạng "cuộn": dòng mới mở đầu bằng đuôi dòng cũ
            # ("…government major which" → "college I was a government major which means…")
            pw, cw = ptx.split(), tx.split()
            k = _overlap_words(pw, cw)
            if k:
                if k >= len(cw):
                    out[-1] = (pst, max(pen, en), ptx)
                    continue
                tx = " ".join(cw[k:])
        out.append((st, en, tx))
    return out


def _overlap_words(prev, cur, min_k=3):
    """Số từ dài nhất k ≥ min_k mà prev kết thúc bằng cur[:k] (0 nếu không có)."""
    for k in range(min(len(prev), len(cur)), min_k - 1, -1):
        if prev[-k:] == cur[:k]:
            return k
    return 0


def _fix_cues(cues, min_dur=0.4):
    """Bỏ cue rỗng, đảm bảo end > start và thứ tự thời gian hợp lệ."""
    out = []
    for st, en, tx in cues:
        tx = " ".join((tx or "").split())
        if not tx:
            continue
        st = max(0.0, float(st or 0))
        en = float(en or 0)
        if en <= st:
            en = st + min_dur
        if out and st < out[-1][0]:
            st = out[-1][0]
        if en <= st:
            en = st + min_dur
        out.append((st, en, tx))
    return out


def split_long_cues(cues, max_chars=92):
    """Chia câu quá dài thành nhiều dòng phụ đề dễ đọc (chia theo từ)."""
    out = []
    for st, en, tx in cues:
        words = (tx or "").split()
        if not words:
            continue
        chunks, cur = [], []
        for w in words:
            if cur and len(" ".join(cur + [w])) > max_chars:
                chunks.append(" ".join(cur))
                cur = [w]
            else:
                cur.append(w)
        if cur:
            chunks.append(" ".join(cur))
        if len(chunks) <= 1:
            out.append((st, en, " ".join(words)))
            continue
        dur = max(float(en) - float(st), 0.1)
        total = sum(len(c) for c in chunks) or 1
        t = float(st)
        for c in chunks:
            d = dur * len(c) / total
            out.append((t, min(t + d, float(en)), c))
            t += d
    return out


def cues_to_srt(cues):
    """Xuất SRT chuẩn: số thứ tự, mốc thời gian, dòng trống giữa các cue."""
    blocks = []
    for i, (st, en, tx) in enumerate(cues, 1):
        blocks.append(f"{i}\n{srt_time(st)} --> {srt_time(en)}\n{tx}\n")
    return "\n".join(blocks) + ("\n" if blocks else "")


def cues_to_txt(cues, with_time=True):
    lines = []
    for st, en, tx in cues:
        lines.append(f"[{clock_time(st)}] {tx}" if with_time else tx)
    return "\n".join(lines).strip() + "\n"


def read_subtitle_file(path):
    """Đọc file phụ đề tải về (.srt/.vtt/.json3) -> cues đã làm sạch."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if path.lower().endswith(".json3"):
        cues = _parse_json3(text)
    else:
        cues = _parse_sub_text(text)
    return _fix_cues(split_long_cues(_dedupe_cues(cues)))


def pick_subtitle_source(info, pref="auto"):
    """Chọn phụ đề tốt nhất: (mã ngôn ngữ, 'manual'|'auto') hoặc (None, None)."""
    info = _yt_first_info(info)
    manual = [k for k in (info.get("subtitles") or {}) if k]
    auto = [k for k in (info.get("automatic_captions") or {}) if k]
    orig = (info.get("language") or "").strip().lower()

    def find(codes, want):
        want = (want or "").lower()
        if not want:
            return None
        for c in codes:
            if c.lower() == want:
                return c
        for c in codes:
            if c.lower().startswith(want + "-") or c.lower().startswith(want + "_"):
                return c
        return None

    if pref and pref != "auto":
        wants = [pref]
    else:
        wants = [orig, "vi", "en"] if orig else ["vi", "en"]
    wants = [w for w in wants if w]
    for kind, codes in (("manual", manual), ("auto", auto)):
        for w in wants:
            hit = find(codes, w)
            if hit:
                return hit, kind
    if orig:
        for kind, codes in (("manual", manual), ("auto", auto)):
            hit = find(codes, orig)
            if hit:
                return hit, kind
    if manual:
        return manual[0], "manual"
    if auto:
        return auto[0], "auto"
    return None, None


def _yt_first_info(info):
    """Nếu là playlist/entries thì lấy video đầu tiên."""
    if not info:
        return {}
    entries = info.get("entries")
    if entries:
        for e in entries:
            if e:
                return e
    return info


MEDIA_EXTS = (".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".mov", ".opus", ".ogg", ".flac")


def pick_downloaded_file(info, out_dir, vid="", since=0.0):
    """Tìm đúng file media vừa tải.

    Ưu tiên đường dẫn do yt-dlp báo (filepath/requested_downloads), vì file có thể
    đã tồn tại từ lần tải trước (yt-dlp bỏ qua tải -> mtime cũ, không dò theo giờ được).
    """
    cands = []
    for key in ("filepath", "_filename"):
        p = info.get(key)
        if p:
            cands.append(p)
    for rd in (info.get("requested_downloads") or []):
        if not isinstance(rd, dict):
            continue
        for key in ("filepath", "_filename"):
            p = rd.get(key)
            if p:
                cands.append(p)
    found = []
    for p in cands:
        stem = os.path.splitext(p)[0]
        for q in (p, stem + ".mp4", stem + ".mkv", stem + ".webm",
                  stem + ".mp3", stem + ".m4a", stem + ".opus"):
            if os.path.isfile(q) and os.path.getsize(q) > 0:
                found.append(q)
    if found:
        return max(set(found), key=os.path.getsize)

    # Dự phòng: quét thư mục, ưu tiên file có [video_id] trong tên
    try:
        names = [os.path.join(out_dir, n) for n in os.listdir(out_dir)]
    except OSError:
        return None
    names = [x for x in names if os.path.isfile(x) and x.lower().endswith(MEDIA_EXTS)
             and os.path.getsize(x) > 0]
    if vid:
        hit = [x for x in names if f"[{vid}]" in os.path.basename(x)]
        if hit:
            return max(hit, key=os.path.getsize)
    recent = [x for x in names if os.path.getmtime(x) >= since - 2]
    if recent:
        return max(recent, key=os.path.getsize)
    return None


def find_subtitle_file(out_dir, media_path, lang, since):
    """Tìm file phụ đề đã tải (.srt/.vtt/.json3) trong thư mục đích.

    Ưu tiên file khớp đúng tên video + ngôn ngữ — kể cả file có sẵn từ lần tải
    trước, vì yt-dlp bỏ qua tải lại nên mtime có thể cũ. Sau đó mới tới file mới.
    """
    base = os.path.splitext(media_path)[0] if media_path else ""
    base_l = os.path.normcase(base)
    exact = None
    best = None
    try:
        names = os.listdir(out_dir)
    except OSError:
        return None
    for name in names:
        low = name.lower()
        if not low.endswith((".srt", ".vtt", ".json3")):
            continue
        p = os.path.join(out_dir, name)
        if not os.path.isfile(p):
            continue
        try:
            fresh = os.path.getmtime(p) >= since - 2
        except OSError:
            fresh = False
        near = bool(base_l) and os.path.normcase(p).startswith(base_l + ".")
        lang_ok = bool(lang) and f".{str(lang).lower()}." in low
        if near and lang_ok:
            if exact is None or os.path.getmtime(p) > os.path.getmtime(exact):
                exact = p
        if not fresh:
            continue
        if near or lang_ok:
            if best is None or os.path.getmtime(p) > os.path.getmtime(best):
                best = p
    return exact or best


_SUB_CODEC = {"mp4": "mov_text", "m4v": "mov_text", "mov": "mov_text",
              "mkv": "srt", "webm": "webvtt"}
_LANG3 = {"vi": "vie", "en": "eng", "ja": "jpn", "ko": "kor", "zh": "chi",
          "fr": "fra", "de": "deu", "th": "tha", "es": "spa", "id": "ind"}


def mux_subtitles_into_video(video_path, srt_path, ffmpeg_exe, lang_code="vi"):
    """Nhúng phụ đề mềm (chọn/bật tắt được) vào MP4/MKV. Trả (path|None, lỗi|None)."""
    ext = os.path.splitext(video_path)[1].lower().lstrip(".")
    codec = _SUB_CODEC.get(ext)
    if not codec:
        return None, f"định dạng .{ext} chưa hỗ trợ nhúng phụ đề"
    tmp = os.path.splitext(video_path)[0] + ".subtmp." + ext
    cmd = [ffmpeg_exe, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
           "-i", video_path, "-i", srt_path,
           # chỉ lấy hình+tiếng của video gốc để không nhân đôi phụ đề khi chạy lại
           "-map", "0:v?", "-map", "0:a?", "-map", "1:0",
           "-c", "copy", "-c:s", codec]
    if codec in ("mov_text", "webvtt"):
        iso = _LANG3.get(str(lang_code).split("-")[0].lower(), "und")
        cmd += ["-metadata:s:s:0", f"language={iso}"]
    cmd.append(tmp)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except Exception as e:
        return None, str(e)
    if r.returncode != 0 or not os.path.exists(tmp):
        msg = (r.stderr or "").strip().splitlines()
        return None, (msg[-1] if msg else "ffmpeg báo lỗi")
    try:
        os.replace(tmp, video_path)
    except Exception as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None, str(e)
    return video_path, None


# ---------- dùng chung cho nhận diện ----------
def ensure_av_patched():
    """Vá tương thích faster-whisper 1.2.1 + PyAV>=15 (bỏ tham số metadata_errors)."""
    try:
        import av as _av
        if not getattr(_av.open, "_patched_no_metadata_errors", False):
            _orig_open = _av.open

            def _patched_open(*args, **kwargs):
                kwargs.pop("metadata_errors", None)
                return _orig_open(*args, **kwargs)

            _patched_open._patched_no_metadata_errors = True
            _av.open = _patched_open
    except Exception:
        pass


_MODEL_CACHE = {}               # model_size -> WhisperModel, cũ nhất đứng đầu
_MODEL_CACHE_MAX = 2            # vd base cho bài Anh + small cho bài Việt (D-37)
_MODEL_LOCK = threading.Lock()


def load_model(model_size):
    """WhisperModel dùng lại giữa các lần chấm/nhận dạng; nạp lần đầu cho mỗi cỡ.

    Giữ tối đa 2 cỡ trong RAM (small/medium nặng hàng trăm MB), bỏ cỡ dùng lâu nhất.
    CTranslate2 cho phép gọi transcribe từ nhiều thread trên cùng một model.
    """
    with _MODEL_LOCK:
        m = _MODEL_CACHE.pop(model_size, None)
        if m is None:
            ensure_av_patched()
            from faster_whisper import WhisperModel
            m = WhisperModel(model_size, device="cpu", compute_type="int8")
        _MODEL_CACHE[model_size] = m          # đưa xuống cuối = vừa dùng
        while len(_MODEL_CACHE) > _MODEL_CACHE_MAX:
            _MODEL_CACHE.pop(next(iter(_MODEL_CACHE)))
        return m


PRAC_VI_MODEL = "small"   # base nghe sai cả câu mẫu sạch tiếng Việt; small đúng (D-37)


def whisper_model_on_disk(model_size):
    """Model đã tải về máy chưa (không dùng mạng)."""
    try:
        from faster_whisper.utils import download_model
        download_model(model_size, local_files_only=True)
        return True
    except Exception:
        return False


def practice_model(selected, lang, on_disk=whisper_model_on_disk):
    """Cỡ model để chấm bài luyện: bài tiếng Việt dùng tối thiểu `small` nếu đã có trên
    máy (không tự tải 480 MB — I9). -> (cỡ, đã_nâng_cấp)."""
    if lang != "vi" or selected not in MODELS or \
            MODELS.index(selected) >= MODELS.index(PRAC_VI_MODEL):
        return selected, False
    if on_disk(PRAC_VI_MODEL):
        return PRAC_VI_MODEL, True
    return selected, False


# Tham số Whisper cho bản ghi luyện phát âm (một câu ngắn). Dùng chung với tools/asr_bench.py.
# - Không có initial_prompt: gợi câu mẫu cho Whisper sẽ che lỗi của người học (I2).
# - temperature 0, không lấy mẫu dự phòng ở nhiệt độ cao: trên bản thu yếu, nhánh dự
#   phòng là nơi Whisper "bịa" câu; kết quả độ tin thấp để cổng D-29 xử lý.
# - Không VAD cho bản thu ngắn: Recorder đã cắt im lặng; Silero (ngưỡng 0,5) bỏ mất
#   giọng nhỏ — asr_bench: mic yếu + tiếng click WER 0,185 → 0,157 khi tắt.
PRAC_ASR_OPTS = {"beam_size": 5, "word_timestamps": True,
                 "condition_on_previous_text": False, "temperature": 0.0}
PRAC_VAD_MAX_SEC = 30.0   # file dài hơn một cửa sổ Whisper (Chấm file…) vẫn dùng VAD


def _wav_seconds(path):
    """Độ dài file WAV (giây); None nếu không phải WAV đọc được."""
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:
        return None


_VI_CHARS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")


def guess_lang(text):
    """Ngôn ngữ của câu mẫu: 'vi' nếu có chữ tiếng Việt, 'en' nếu toàn chữ Latin
    không dấu, None nếu không đoán được. Câu ngắn giọng Việt đọc tiếng Anh làm Whisper
    dò nhầm ngôn ngữ → ra chữ rác; câu mẫu cho biết chắc hơn."""
    letters = [c for c in (text or "").lower() if c.isalpha()]
    if not letters:
        return None
    if any(c in _VI_CHARS for c in letters):
        return "vi"
    if all("a" <= c <= "z" for c in letters):
        return "en"
    return None


def transcribe_practice(model, wav_path, lang, **overrides):
    """Nhận dạng bản ghi luyện -> {hyp, words, probs, words_t, info}."""
    secs = _wav_seconds(wav_path)
    opts = dict(PRAC_ASR_OPTS, vad_filter=secs is None or secs > PRAC_VAD_MAX_SEC)
    opts.update(overrides)
    segs, info = model.transcribe(wav_path, language=None if lang == "auto" else lang,
                                  **opts)
    # segs là generator: chỉ duyệt được MỘT lần → gom luôn text dự phòng ở đây
    words, probs, texts, words_t = [], [], [], []
    for s in segs:
        texts.append(getattr(s, "text", "") or "")
        for w in (getattr(s, "words", None) or []):
            t = (getattr(w, "word", "") or "").strip()
            if t:
                p = float(getattr(w, "probability", 1.0) or 0.0)
                words.append(t)
                probs.append(p)
                # mốc thời gian từng từ: để vẽ nhãn từ dưới biểu đồ ngữ điệu (S-5)
                st, en = getattr(w, "start", None), getattr(w, "end", None)
                if st is not None and en is not None:
                    words_t.append({"w": t, "s": round(float(st), 3),
                                    "e": round(float(en), 3), "p": round(p, 3)})
    hyp = " ".join(words).strip() or " ".join("".join(texts).split())
    return {"hyp": hyp, "words": words, "probs": probs, "words_t": words_t, "info": info}


# ---------- tải video YouTube (yt-dlp + ffmpeg) ----------
class _YtCancelled(Exception):
    pass


def yt_ffmpeg_location():
    """Đường dẫn file ffmpeg (dùng gói imageio-ffmpeg kèm sẵn). None nếu chưa có."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def yt_build_opts(out_dir, fmt_key, quality, ffmpeg_loc, hook, sub_lang=None):
    """Dựng tùy chọn cho yt-dlp: chất lượng + merge ra mp4 (hoặc chỉ audio mp3)."""
    if fmt_key == "audio":
        fmt = "ba/b"
    elif quality == "best":
        fmt = "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b"
    else:
        h = quality
        fmt = (f"bv*[ext=mp4][height<={h}]+ba[ext=m4a]/"
               f"bv*[height<={h}]+ba/b[height<={h}]")
    opts = {
        "format": fmt,
        "outtmpl": os.path.join(out_dir, "%(title).80s [%(id)s].%(ext)s"),
        "noplaylist": True,
        "windowsfilenames": True,
        "continuedl": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "merge_output_format": None if fmt_key == "audio" else "mp4",
        "ffmpeg_location": ffmpeg_loc,
    }
    if sub_lang:
        opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [sub_lang],
            "subtitlesformat": "srt/vtt/best",
        })
    if fmt_key == "audio":
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                   "preferredcodec": "mp3",
                                   "preferredquality": "192"}]
    return {k: v for k, v in opts.items() if v is not None}


def yt_progress_fraction(d):
    """Tiến độ 0..1 từ progress hook của yt-dlp; None nếu chưa biết tổng dung lượng."""
    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
    if not total:
        return None
    done = d.get("downloaded_bytes") or 0
    return max(0.0, min(1.0, float(done) / float(total)))


# ---------- đọc to transcript YouTube (D-39, docs/YT-READING-PLAN.md) ----------
def documents_dir():
    """Thư mục Documents thật của người dùng (kể cả khi OneDrive chuyển hướng)."""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
            return buf.value                        # CSIDL_PERSONAL
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def recordings_dir():
    """Nơi "Lưu bản thu" ghi file: Documents\\Oriole (tạo nếu chưa có)."""
    d = os.path.join(documents_dir(), "Oriole")
    os.makedirs(d, exist_ok=True)
    return d


YTREAD_PAD_SEC = 0.4   # nới hai đầu đoạn khi nghe audio gốc: mốc phụ đề lệch, đừng cắt mất từ
YT_SILENCE_SEC = 3.5   # đọc cả đoạn hay ngừng để dò dòng → tự dừng muộn hơn câu ngắn (1,8 s)
YT_MAX_SEC = 150       # đoạn ≤ 45 s; người học đọc chậm gấp 2–3 lần vẫn đủ
YT_REC_HINT = "Đọc hết đoạn — ngừng khoảng 4 giây là app tự dừng và chấm"


def pick_en_subtitle(info, prefer="manual"):
    """Phụ đề TIẾNG ANH gốc: (mã, 'manual'|'auto') hoặc (None, None).

    Không nhận bản dịch máy (video gốc không phải tiếng Anh) — dịch máy không phải lời
    người nói nên không dùng làm bài đọc. prefer="auto" để đo phụ đề tự động (bench).
    """
    info = _yt_first_info(info)
    orig = (info.get("language") or "").lower()
    if orig and not orig.startswith("en"):
        return None, None
    kinds = (("manual", info.get("subtitles")), ("auto", info.get("automatic_captions")))
    if prefer == "auto":
        kinds = kinds[::-1]
    for kind, subs in kinds:
        codes = [c for c in (subs or {}) if c.lower() == "en" or c.lower().startswith("en-")]
        # "en-orig" của YouTube là bản tự động gốc; các mã en-xx khác có thể là dịch
        for c in sorted(codes, key=lambda c: (c.lower() not in ("en", "en-orig"), c)):
            return c, kind
    return None, None


class YtReadSession:
    """Một phiên đọc to: đoạn phụ đề + audio gốc 16 kHz trong thư mục tạm của phiên.

    Phiên dùng một lần (D-39): `close()` xóa toàn bộ thư mục (I10) — gọi khi đổi video,
    rời màn hình hoặc đóng app.
    """

    def __init__(self, work_dir):
        self.work_dir = work_dir
        self.url = self.title = self.vid = ""
        self.sub_kind = None       # "manual" | "auto" | "whisper"
        self.paragraphs = []       # yt_read.build_paragraphs
        self.wav = None            # audio gốc, mono 16 kHz
        self._orig = {}            # chỉ số đoạn → lời Whisper nghe trên audio gốc
        self.orig_words = {}       # chỉ số đoạn → [{w, s, e, p}] của audio gốc
        self.all_words = []        # transcript do Whisper tạo: mốc từ của cả video
        self.lock = threading.Lock()   # ytread_orig_hyp: nghe trước ở nền + lúc chấm
        self.pitch = {}            # chỉ số đoạn → prosody.pitch_track của audio gốc (D-44)

    def close(self):
        if self.work_dir:
            shutil.rmtree(self.work_dir, ignore_errors=True)
        self.work_dir, self.wav = None, None


def ytread_prepare(url, model_size, cancel=lambda: False, status=lambda msg: None,
                   prefer="manual"):
    """Link → YtReadSession (chạy trong worker). Ném _YtCancelled khi cancel() (I11),
    ValueError khi video không dùng được (lời nhắn tiếng Việt cho người học)."""
    import yt_dlp
    import yt_read
    ff = yt_ffmpeg_location()
    if not ff:
        raise ValueError("Chưa có ffmpeg (imageio-ffmpeg). Chạy: pip install -r requirements.txt")
    s = YtReadSession(tempfile.mkdtemp(prefix="oriole_ytread_"))
    try:
        def check():
            if cancel():
                raise _YtCancelled()

        def hook(d):
            check()
            frac = yt_progress_fraction(d) if d.get("status") == "downloading" else None
            if frac is not None:
                status("Đang tải âm thanh gốc… %d%%" % round(frac * 100))

        status("Đang đọc thông tin video…")
        base = {"quiet": True, "no_warnings": True, "noplaylist": True, "noprogress": True}
        with yt_dlp.YoutubeDL(base) as ydl:
            info = _yt_first_info(ydl.extract_info(url, download=False) or {})
        check()
        s.url, s.title, s.vid = url, info.get("title") or "", info.get("id") or ""
        lang = (info.get("language") or "").lower()
        if lang and not lang.startswith("en"):
            raise ValueError("Video này không phải tiếng Anh (%s) — hãy chọn video nói tiếng Anh."
                             % lang)
        code, kind = pick_en_subtitle(info, prefer)

        status("Đang tải âm thanh gốc…")
        opts = dict(base, format="ba/b", progress_hooks=[hook],
                    outtmpl=os.path.join(s.work_dir, "orig.%(ext)s"))
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        check()
        media = [os.path.join(s.work_dir, n) for n in os.listdir(s.work_dir)
                 if n.startswith("orig.")]
        if not media:
            raise ValueError("Không tải được âm thanh của video.")
        s.wav = os.path.join(s.work_dir, "orig16k.wav")
        r = subprocess.run([ff, "-y", "-nostdin", "-v", "error", "-i", max(media, key=os.path.getsize),
                            "-ac", "1", "-ar", str(REC_RATE), "-c:a", "pcm_s16le", s.wav],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not os.path.exists(s.wav):
            raise ValueError("Không đọc được âm thanh của video: %s"
                             % ((r.stderr or "").strip().splitlines() or ["ffmpeg"])[-1])
        for m in media:
            remove_temp(m)
        check()

        cues = []
        if code:
            status("Đang tải phụ đề tiếng Anh…")
            sub_opts = dict(base, skip_download=True, writesubtitles=kind == "manual",
                            writeautomaticsub=kind == "auto", subtitleslangs=[code],
                            subtitlesformat="vtt/srt/best",
                            outtmpl=os.path.join(s.work_dir, "sub.%(ext)s"))
            for attempt in (1, 2):   # YouTube hay trả HTTP 429 cho phụ đề → thử lại một lần
                try:
                    with yt_dlp.YoutubeDL(sub_opts) as ydl:
                        ydl.download([url])
                    break
                except Exception as e:
                    check()
                    if attempt == 2 or "429" not in str(e):
                        break
                    for _ in range(40):
                        check()
                        time.sleep(0.1)
            for n in os.listdir(s.work_dir):
                if n.startswith("sub.") and n.lower().endswith((".vtt", ".srt", ".json3")):
                    cues = read_subtitle_file(os.path.join(s.work_dir, n))
                    remove_temp(os.path.join(s.work_dir, n))
        s.sub_kind = kind if cues else "whisper"
        if not cues:
            status("Video không có phụ đề tiếng Anh → Whisper tạo transcript…")
            segs, _info = load_model(model_size).transcribe(s.wav, language="en", beam_size=5,
                                                            vad_filter=True, word_timestamps=True)
            for seg in segs:
                check()
                tx = " ".join(seg.text.split())
                if tx:
                    cues.append((float(seg.start), float(seg.end), tx))
                # giữ mốc từ của người nói: không đo được "phụ đề sai" (chính Whisper tạo chữ)
                # nhưng vẫn có ▶ Mẫu từng từ/câu và so tốc độ, chỗ ngừng (R1)
                for w in (getattr(seg, "words", None) or []):
                    t = (w.word or "").strip()
                    if t and w.start is not None and w.end is not None:
                        s.all_words.append({"w": t, "s": round(float(w.start), 3),
                                            "e": round(float(w.end), 3),
                                            "p": round(float(w.probability), 3)})
                status("Whisper: %s" % clock_time(seg.end))
        s.paragraphs = yt_read.build_paragraphs(cues)
        if not s.paragraphs:
            raise ValueError("Video không có lời nói tiếng Anh để đọc.")
        return s
    except BaseException:
        s.close()
        raise


YT_LEARNER_MODEL = "medium"   # bản đọc người học (D-41): small nghe nhầm ~1/5 từ đỏ


def ytread_model(selected, on_disk=whisper_model_on_disk):
    """Cỡ model nghe BẢN ĐỌC người học ở chế độ Từ YouTube: `medium` nếu đã có trên máy
    (không tự tải ~1,5 GB — I9) và model đang chọn nhỏ hơn. → (cỡ, đã_nâng_cấp).

    Đo trên 4 đoạn thật (2026-10-24): small 151/250 từ đúng, medium 164/250; medium chậm ~3×
    (6–10 s mỗi đoạn 25–35 s). Audio GỐC vẫn dùng model đang chọn (giọng chuẩn, rõ — medium
    không đổi số "phụ đề có thể sai" mà thêm ~10 s)."""
    if selected not in MODELS or MODELS.index(selected) >= MODELS.index(YT_LEARNER_MODEL):
        return selected, False
    if on_disk(YT_LEARNER_MODEL):
        return YT_LEARNER_MODEL, True
    return selected, False


def ytread_orig_hyp(session, i, model):
    """Whisper nghe ĐOẠN GỐC thứ i → chữ (cache). None khi transcript do chính Whisper
    tạo (so với chính nó thì vô nghĩa) — khi đó không có "phụ đề có thể sai"."""
    if session.sub_kind == "whisper" or not session.wav:
        if session.all_words and i not in session.orig_words:
            p = session.paragraphs[i]
            session.orig_words[i] = [w for w in session.all_words
                                     if p["start"] - YTREAD_PAD_SEC <= (w["s"] + w["e"]) / 2
                                     <= p["end"] + YTREAD_PAD_SEC]
        return None
    with session.lock:
        return _ytread_orig_locked(session, i, model)


def ytread_orig_pitch(session, i):
    """Cao độ đoạn gốc thứ i (mốc tuyệt đối trong session.wav), cache. None nếu không đo được."""
    if not session.wav:
        return None
    if i not in session.pitch:
        p = session.paragraphs[i]
        try:
            session.pitch[i] = prosody.pitch_track(session.wav, p["start"] - YTREAD_PAD_SEC,
                                                   p["end"] + YTREAD_PAD_SEC)
        except Exception:
            session.pitch[i] = None
    return session.pitch[i]


def _ytread_orig_locked(session, i, model):
    if i not in session._orig and session.wav:
        import numpy as np
        p = session.paragraphs[i]
        with wave.open(session.wav, "rb") as w:
            a, b = wav_segment_bounds(w.getnframes(), w.getframerate(),
                                      p["start"], p["end"], pad=YTREAD_PAD_SEC)
            w.setpos(a)
            x = np.frombuffer(w.readframes(b - a), dtype=np.int16).astype(np.float32) / 32768.0
        segs, _info = model.transcribe(x, language="en",
                                       **dict(PRAC_ASR_OPTS, vad_filter=True))
        off, texts, words = a / float(REC_RATE), [], []
        for seg in segs:
            texts.append(" ".join(seg.text.split()))
            for w in (getattr(seg, "words", None) or []):
                t = (w.word or "").strip()
                if t and w.start is not None and w.end is not None:
                    words.append({"w": t, "s": round(off + float(w.start), 3),
                                  "e": round(off + float(w.end), 3),
                                  "p": round(float(w.probability), 3)})
        session._orig[i] = " ".join(texts).strip()
        session.orig_words[i] = words      # mốc tuyệt đối trong session.wav (▶ Mẫu từng từ)
    return session._orig.get(i)


# ---------- chấm phát âm (hàm thuần, dễ test) ----------
def norm_words(s):
    return re.sub(r"[^\w']", " ", s.lower(), flags=re.UNICODE).split()


def _rest_sim(a, b):
    if not a or not b:
        return 1.0 if a == b else 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


_TONE_MARKS = {"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"}  # huyền sắc ngã hỏi nặng


def strip_tone_vi(w):
    """Bỏ DẤU THANH nhưng giữ nguyên chữ cái (â/ă/ê/ô/ơ/ư vẫn khác a/e/o/u)."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", w) if c not in _TONE_MARKS)


def vi_north_key(w):
    """Khóa so sánh chấp nhận giọng Bắc (D-38): r/d/gi → z, x → s, tr → ch ở phụ âm đầu.

    "rừng"/"dừng" → "zừng", "giữ"/"dữ" → "zữ", "gì"/"dì" → "zì", "xinh"/"sinh" → "sinh",
    "trong"/"chong" → "chong". Thanh và vần giữ nguyên. Chỉ dùng cho bài tiếng Việt.
    """
    import unicodedata
    w = unicodedata.normalize("NFC", (w or "").lower())
    if len(w) > 1 and w[0] == "g" and strip_marks_vi(w[1]) == "i":
        # "gi" + nguyên âm ("giữ") → bỏ cả "gi"; "gì"/"gìn" (i là vần) → chỉ đổi g
        vowel = len(w) > 2 and strip_marks_vi(w[2]) in "aeiouy"
        return "z" + (w[2:] if vowel and w[1] == "i" else w[1:])
    if w[:2] == "tr":
        return "ch" + w[2:]
    if w[:1] in ("r", "d"):
        return "z" + w[1:]
    if w[:1] == "x":
        return "s" + w[1:]
    return w


def strip_marks_vi(w):
    """Bỏ MỌI dấu (thanh + mũ/trăng/móc, đ→d) — chỉ còn chữ cái gốc: "lắm" → "lam"."""
    import unicodedata
    base = "".join(c for c in unicodedata.normalize("NFD", w)
                   if not unicodedata.combining(c))
    return base.replace("đ", "d").replace("Đ", "D")


# ---------- mic + nâng chất lượng bản thu ----------
def list_input_mics():
    """Liệt kê micro khả dụng: [(index, tên, hostapi, samplerate)]. Lỗi -> []."""
    try:
        import sounddevice as sd
        apis = sd.query_hostapis()
        out = []
        for i, d in enumerate(sd.query_devices()):
            if d.get("max_input_channels", 0) > 0:
                try:
                    api = apis[d["hostapi"]]["name"]
                except Exception:
                    api = "?"
                try:
                    sr = int(d.get("default_samplerate", 44100) or 44100)
                except Exception:
                    sr = 44100
                out.append((i, d["name"], api, sr))
        return out
    except Exception:
        return []


def list_usable_mics(mics=None):
    """Micro có thể thu liên tục: loại host API WDM-KS.

    PortAudio không hỗ trợ blocking read trên WDM-KS nên Recorder (InputStream +
    stream.read) luôn lỗi 'Blocking API not supported'. Vì vậy WDM-KS không được
    đưa vào ô chọn micro — nếu không người dùng sẽ chọn đúng thiết bị luôn hỏng.
    Máy chỉ có WDM-KS: trả lại danh sách gốc để không bỏ trắng ô chọn.
    """
    mics = list_input_mics() if mics is None else mics
    ok = [m for m in mics if "WDM-KS" not in str(m[2] or "").upper()]
    return ok or list(mics)


def rescan_audio_devices():
    """Nạp lại danh sách thiết bị của PortAudio (thấy mic vừa cắm/kết nối).

    PortAudio chỉ liệt kê thiết bị tại thời điểm khởi tạo; sounddevice không tự
    cập nhật khi người dùng bật tai nghe Bluetooth, AirPods hay cắm mic USB **sau**
    khi mở app. Gọi `_terminate` + `_initialize` để đọc lại. Chỉ gọi khi không có
    stream nào đang chạy (thu âm/phát mẫu), nếu không sẽ làm đứt stream.
    """
    try:
        import sounddevice as sd
        sd._terminate()
        sd._initialize()
        return True
    except Exception:
        return False


# Từ khoá nhận ra thiết bị NGHE là tai nghe/loa bluetooth (không tính loa máy).
_HEADPHONE_HINTS = ("airpod", "headset", "hands-free", "handsfree", "bluetooth",
                    "buds", "jabra", "logitech", "beats", "soundcore", "wh-1000",
                    "galaxy buds", "freebuds")
# Từ chung chung không dùng làm khoá nhận dạng thiết bị.
_GENERIC_WORDS = {
    "headphones", "headset", "speakers", "speaker", "primary", "sound", "mapper",
    "driver", "output", "input", "audio", "realtek", "digital", "stereo", "hands",
    "free", "microphone", "microphones", "array", "find", "wireless", "bluetooth",
}


def _device_brand_key(name):
    """Từ khoá nhận dạng thiết bị: nội dung trong ngoặc, bỏ từ chung chung."""
    import re
    m = re.search(r"\(([^)]*)\)", name or "")
    text = (m.group(1) if m else (name or "")).lower()
    text = text.replace("-", " ").replace("®", " ").replace("(r)", " ")
    words = [w for w in re.split(r"[^a-z0-9]+", text)
             if len(w) >= 4 and w not in _GENERIC_WORDS]
    if not words:
        return None
    return max(words, key=len)


def headset_mic_missing(devices=None):
    """Tai nghe đang chỉ có chiều NGHE (Windows chưa mở micro) -> trả tên, không thì None.

    AirPods/headset Bluetooth thường hiện 2 mục: "Headphones (X)" chỉ để nghe và
    "Headset (X Hands-Free AG Audio)" có micro. Nếu chỉ thấy mục nghe, micro chưa
    được bật (profile Hands-Free/Telephony tắt) và app không thể chọn được.
    """
    try:
        import sounddevice as sd
        devs = sd.query_devices() if devices is None else devices
    except Exception:
        return None
    ins, outs = [], []
    for d in devs:
        n = str(d.get("name") or "")
        if d.get("max_input_channels", 0) > 0:
            ins.append(n.lower())
        if d.get("max_output_channels", 0) > 0:
            outs.append(n)
    for out in outs:
        low = out.lower()
        if not any(h in low for h in _HEADPHONE_HINTS):
            continue
        key = _device_brand_key(out)
        if key and not any(key in i for i in ins):
            return out
    return None


def pick_default_mic(mics):
    """Ưu tiên: micro thật > thiết bị alias; DirectSound > WASAPI > MME > khác.

    Vì sao DirectSound trên WASAPI: đo trên máy hiện tại (Microphone Array
    Intel SST, người dùng đọc cùng câu) cho thấy DirectSound ~2,0% còn WASAPI
    ~0,3% đỉnh tín hiệu cho CÙNG một mic vật lý — WASAPI rơi vào nhánh xử lý
    của driver làm tín hiệu nhỏ đi, dễ bị cổng "mic im lặng" chặn oan.
    """
    if not mics:
        return None
    best, best_score = mics[0][0], -999
    for item in mics:
        idx, name, api = item[0], item[1], item[2]
        n = name.lower()
        s = 0
        if "stereo mix" in n or "loopback" in n or "what u hear" in n:
            s -= 10
        if "sound mapper" in n or "primary sound" in n:
            s -= 3          # thiết bị alias, không phải micro thật
        if "micro" in n or "mic" in n:
            s += 2
        au = api.upper()
        if "DIRECT" in au:
            s += 2
        elif "WASAPI" in au:
            s += 1
        elif "MME" in au:
            s += 0
        else:  # WDM-KS thường liệt kê nhiều sub-device gây nhiễu
            s -= 1
        if s > best_score:
            best, best_score = idx, s
    return best


def query_mic_rate(device_idx, fallback=44100):
    """Tần số gốc của mic. Thu đúng tần số gốc rồi resample mềm về 16k
    sẽ sạch hơn nhiều so với ép InputStream chạy 16k (PortAudio resample thô)."""
    try:
        import sounddevice as sd
        sr = sd.query_devices(device_idx).get("default_samplerate", fallback)
        sr = int(sr or fallback)
        return sr if 8000 <= sr <= 192000 else fallback
    except Exception:
        return fallback


def probe_input_levels(dur=0.5, limit=12):
    """Thu thử từng micro thật (bỏ loopback), trả về [(idx, tên, hostapi, đỉnh)]
    giảm dần theo đỉnh. Dùng để phát hiện micro đang tắt tiếng trên máy."""
    try:
        import numpy as np
        import sounddevice as sd
    except Exception:
        return []
    rows = []
    for idx, name, api, sr in list_input_mics()[:limit]:
        n = name.lower()
        if ("stereo mix" in n or "loopback" in n or "what u hear" in n
                or "sound mapper" in n):
            continue
        if "WDM-KS" in api.upper():
            # WDM-KS không hỗ trợ blocking read -> Recorder không thu được.
            continue
        try:
            sr = int(sr or 44100)
            data = sd.rec(int(sr * dur), samplerate=sr, channels=1,
                          dtype="int16", device=idx)
            sd.wait()
            x = data.astype(np.float32).flatten() / 32768.0
            peak = float(np.max(np.abs(x))) if len(x) else 0.0
            rows.append((idx, name, api, peak))
        except Exception:
            continue
    rows.sort(key=lambda t: -t[3])
    return rows


def best_input_mic(dur=1.0):
    rows = probe_input_levels(dur)
    return rows[0] if rows else None


def fft_convolve(x, h):
    """Tích chập đầy đủ (len x + len h - 1) bằng FFT overlap-add, numpy thuần, float32."""
    import numpy as np
    x = np.asarray(x, dtype=np.float32)
    h = np.asarray(h, dtype=np.float64)
    n, m = len(x), len(h)
    out = np.zeros(n + m - 1, dtype=np.float32)
    if n == 0 or m == 0:
        return out
    # FFT ~8× độ dài kernel: ít phần chồng lấn phí mà vẫn ít vòng lặp
    nfft = max(4096, 1 << int(np.ceil(np.log2(8 * m))))
    block = nfft - m + 1
    H = np.fft.rfft(h, nfft)
    for s in range(0, n, block):
        seg = x[s:s + block]
        k = len(seg) + m - 1
        out[s:s + k] += np.fft.irfft(np.fft.rfft(seg, nfft) * H, nfft)[:k].astype(np.float32)
    return out


# Biên lọc khi về 16 kHz: giữ tới 7,9 kHz (s/sh/th nằm ở 4–8 kHz; Whisper dùng tới 8 kHz),
# chặn ≥ 80 dB từ 8,6 kHz. Chỉ dải 8–8,6 kHz gập nhẹ vào 7,4–8 kHz. Đo bằng
# tools/asr_bench.py: cắt sớm ở 7,4–8 kHz làm Whisper nghe "sells" thành "fell".
RESAMPLE_PASS_HZ = 7900
RESAMPLE_STOP_HZ = 8600
RESAMPLE_ATTEN_DB = 80


def lowpass_kernel(rate, pass_hz, stop_hz, atten_db=RESAMPLE_ATTEN_DB):
    """FIR low-pass pha tuyến tính (sinc cửa sổ Kaiser), số tap lẻ."""
    import numpy as np
    width = 2.0 * np.pi * (stop_hz - pass_hz) / float(rate)
    taps = int(np.ceil((atten_db - 8.0) / (2.285 * width))) | 1
    beta = 0.1102 * (atten_db - 8.7)
    fc = (pass_hz + stop_hz) / 2.0 / float(rate)
    n = np.arange(taps) - (taps - 1) / 2.0
    h = 2.0 * fc * np.sinc(2.0 * fc * n) * np.kaiser(taps, beta)
    return h / np.sum(h)


def resample_to_16k(samples, src_rate, dst_rate=16000):
    """Đổi tần số lấy mẫu bằng numpy (không cần scipy).

    Hạ tần số: lọc chống gập (FIR Kaiser, ≥ 80 dB) rồi mới nội suy. Không lọc thì
    ồn/rít 8–24 kHz của mic 48 kHz gập xuống 0–8 kHz, đè lên dải s/sh/th.
    """
    import numpy as np
    x = np.asarray(samples).flatten().astype(np.float32)
    if len(x) == 0 or src_rate == dst_rate:
        return x
    if dst_rate < src_rate:
        k = dst_rate / 16000.0
        stop = min(RESAMPLE_STOP_HZ * k, 0.49 * src_rate)
        h = lowpass_kernel(src_rate, min(RESAMPLE_PASS_HZ * k, 0.92 * stop), stop)
        d = (len(h) - 1) // 2   # bù trễ của bộ lọc pha tuyến tính
        x = fft_convolve(x, h)[d:d + len(x)]
    ratio = dst_rate / float(src_rate)
    n_out = max(1, int(round(len(x) * ratio)))
    old_idx = np.linspace(0, len(x) - 1, len(x))
    new_idx = np.linspace(0, len(x) - 1, n_out)
    return np.interp(new_idx, old_idx, x).astype(np.float32)


def highpass_1pole_kernel(rate, fc=75.0, tol=1e-7):
    """Đáp ứng xung của high-pass 1 cực y[n] = x[n]-x[n-1] + a*y[n-1]: h0=1, hn=a^n-a^(n-1)."""
    import math
    import numpy as np
    rc = 1.0 / (2.0 * math.pi * fc)
    dt = 1.0 / float(rate)
    a = rc / (rc + dt)
    n = int(math.ceil(math.log(tol) / math.log(a))) + 1
    g = a ** np.arange(n, dtype=np.float64)
    h = g.copy()
    h[1:] -= g[:-1]
    return h


GAIN_FRAME_MS = 10     # khung đo đỉnh khi tính gain
GAIN_SKIP_FRAC = 0.02  # bỏ 2 % khung to nhất (click, gõ bàn, bật hơi) khi tính đỉnh giọng


def speech_peak(x, rate):
    """Đỉnh đại diện cho giọng: đỉnh khung 10 ms ở vị trí top 2 % (bỏ ít nhất 2 khung)."""
    import numpy as np
    x = np.asarray(x, dtype=np.float32)
    f = max(1, int(rate * GAIN_FRAME_MS / 1000.0))
    n = len(x) // f
    if n < 4:
        return float(np.max(np.abs(x))) if len(x) else 0.0
    pk = np.sort(np.max(np.abs(x[:n * f].reshape(n, f)), axis=1))[::-1]
    return float(pk[min(n - 1, max(2, int(GAIN_SKIP_FRAC * n)))])


SNR_FRAME_MS = 20
SNR_LOW_DB = 15.0     # giọng hơn nền < 15 dB → ghi chú "phòng hơi ồn" (chỉ ghi chú, chưa thành cổng)
SNR_MAX_DB = 60.0


def estimate_snr_db(x, rate):
    """Ước lượng giọng/nền (dB): RMS khung 20 ms ở phân vị 90 so với phân vị 10.

    Bản thu luyện luôn có đoạn lặng trước/sau giọng (0,5 s đo nền đầu, ~1,8 s im lặng
    cuối) nên phân vị 10 là nền nhiễu. None nếu bản thu quá ngắn.
    """
    import numpy as np
    x = np.asarray(x, dtype=np.float32)
    f = max(1, int(rate * SNR_FRAME_MS / 1000.0))
    n = len(x) // f
    if n < 10:
        return None
    rms = np.sqrt(np.mean(x[:n * f].reshape(n, f) ** 2, axis=1))
    speech, noise = float(np.percentile(rms, 90)), float(np.percentile(rms, 10))
    if speech <= 1e-7:
        return None
    return round(min(SNR_MAX_DB, 20.0 * math.log10(speech / max(noise, 1e-7))), 1)


def enhance_audio(samples, rate=16000):
    """Lọc DC + high-pass mềm (~75Hz) + giới hạn mềm + chuẩn hóa về -3dB
    + fade + cắt im lặng đầu/cuối. Trả về (int16, info). Hàm thuần, dễ test."""
    import numpy as np
    x = np.asarray(samples).flatten().astype(np.float32) / 32768.0
    if len(x) == 0:
        return np.asarray(samples).flatten().astype(np.int16), {
            "peak0": 0.0, "peak1": 0.0, "quiet": True,
            "clipped": False, "trimmed": 0.0, "snr_db": None}
    peak_raw = float(np.max(np.abs(x))) if len(x) else 0.0
    clipped = peak_raw >= 0.99
    x = x - float(np.mean(x))  # bỏ DC (ù, lệch mic)
    # High-pass 1 cực ~75Hz: y[n] = x[n]-x[n-1] + a*y[n-1], mềm, không ringing
    # như FFT brick-wall cũ (nguyên nhân gây "rè kim loại"). Tính bằng tích chập với
    # đáp ứng xung của chính bộ lọc đó (cắt khi a^n < 1e-7) — cùng kết quả, không lặp Python.
    if len(x) > 1 and rate > 0:
        x = fft_convolve(x, highpass_1pole_kernel(rate))[:len(x)]
    snr_db = estimate_snr_db(x, rate)
    peak0 = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak0 > 1e-6:
        # Chuẩn hóa về -3dB; nếu đầu vào đã vỡ thì HẠ xuống chứ không khuếch đại thêm.
        target = REC_TARGET_PEAK
        if clipped and peak0 > 0:
            gain = min(1.0, target / peak0)
        else:
            # Gain theo mức GIỌNG (đỉnh "thường gặp" của các khung 10 ms), không theo một
            # mẫu cao nhất: một tiếng gõ bàn/bật hơi "p" không được quyết định âm lượng cả
            # bản thu. Giới hạn +24dB (REC_GAIN_MAX) cho micro array laptop đỉnh 1–3%.
            gain = min(REC_GAIN_MAX, target / max(speech_peak(x, rate), 1e-4))
        x = x * gain
    # Soft-clip nhẹ chống vỡ đầu ra
    x = np.tanh(x * 1.0)
    x = np.clip(x, -1.0, 1.0)
    peak1 = float(np.max(np.abs(x))) if len(x) else 0.0
    # Cắt im lặng đầu/cuối có hysteresis + fade chống "tách"
    trimmed = 0.0
    mag = np.abs(x)
    thr = max(0.015, peak1 * 0.04)
    idx = np.where(mag > thr)[0]
    if len(idx):
        pad = max(1, int(rate * 0.08))  # giữ 80ms ngữ cảnh
        s = max(0, int(idx[0]) - pad)
        e = min(len(x), int(idx[-1]) + pad)
        trimmed = ((int(idx[0]) - s) + (e - int(idx[-1]))) / rate
        x = x[s:e]
    f = max(1, int(rate * REC_FADE_MS / 1000.0))
    if len(x) > 2 * f:
        ramp = np.linspace(0.0, 1.0, f, dtype=np.float32)
        x[:f] = x[:f] * ramp
        x[-f:] = x[-f:] * ramp[::-1]
    out = (x * 32767).astype(np.int16)
    return out, {"peak0": peak_raw, "peak1": peak1, "quiet": peak_raw < 0.05,
                 "clipped": clipped, "trimmed": trimmed, "snr_db": snr_db}


def flag_pair(t, h, lang):
    """Trả về (mã, gợi ý) nếu nghi phát âm sai mẫu quen thuộc, else None."""
    if not t or not h or t == h:
        return None
    # Lời nhắc viết như người nói (S-4): "“lan” nghe thành “nan” — âm L bị đọc thành N"
    if lang in ("vi", "auto"):
        if len(t) > 1 and len(h) > 1 and {t[0], h[0]} == {"n", "l"} \
                and _rest_sim(t[1:], h[1:]) >= 0.5:
            return ("nl", "“%s” nghe thành “%s” — âm %s bị đọc thành %s"
                    % (t, h, t[0].upper(), h[0].upper()))
    if lang in ("en", "auto"):
        if t.startswith("th") and h[:1] in "tdsz" and not h.startswith("th") \
                and _rest_sim(t[2:], h[1:]) >= 0.5:
            return ("th", "“%s” nghe thành “%s” — âm th bị đọc thành %s" % (t, h, h[0]))
        for p1, p2 in (("sh", "s"), ("s", "sh")):
            if t.startswith(p1) and h.startswith(p2) \
                    and _rest_sim(t[len(p1):], h[len(p2):]) >= 0.5:
                return ("sh", "“%s” nghe thành “%s” — lẫn s và sh" % (t, h))
        if len(t) > 2 and t[-1] in "tdkpgbs" and h == t[:-1]:
            return ("final", "“%s” nghe thành “%s” — nuốt âm cuối %s" % (t, h, t[-1]))
        if len(t) > 3 and t.endswith("e") and h == t[:-2] + "e" and t[-2] in "tdkpgbsxz":
            return ("final", "“%s” nghe thành “%s” — nuốt âm cuối %s" % (t, h, t[-2]))
    return None


def score_pronunciation(target, hyp, lang):
    """Căn chỉnh từng từ mục tiêu vs máy nghe được. Trả về dict kết quả."""
    tw, hw = norm_words(target), norm_words(hyp)
    # Lượt 1 (theo vị trí đọc): cùng vị trí i thì từ i của bài vs từ i bạn đọc
    # là cặp so sánh đúng nhất (vd: mục tiêu "nam lam", đọc "lam lam" -> nam/lam).
    pos_flag = {}
    for i, t in enumerate(tw):
        h = hw[i] if i < len(hw) else None
        fl = flag_pair(t, h, lang)
        if fl:
            pos_flag[i] = fl[1]
    # Bài Việt so theo khóa giọng Bắc (D-38): "rừng" đọc thành "dừng" vẫn là đúng
    key = vi_north_key if lang == "vi" else (lambda w: w)
    tk, hk = [key(w) for w in tw], [key(w) for w in hw]
    sm = difflib.SequenceMatcher(None, tk, hk)
    # Gộp cặp delete+insert kề nhau thành replace: cùng vị trí đọc thì
    # "thiếu chữ A + thừa chữ B" thực chất là "đọc A thành B" (vd: nam->lam).
    ops, i = [], 0
    raw = sm.get_opcodes()
    while i < len(raw):
        tag, i1, i2, j1, j2 = raw[i]
        if i + 1 < len(raw):
            nt, ni1, ni2, nj1, nj2 = raw[i + 1]
            if tag == "delete" and nt == "insert":
                ops.append(("replace", i1, i2, nj1, nj2))
                i += 2
                continue
            if tag == "insert" and nt == "delete":
                ops.append(("replace", ni1, ni2, j1, j2))
                i += 2
                continue
        ops.append((tag, i1, i2, j1, j2))
        i += 1
    items = []  # (từ_mục_tiêu|None, trạng_thái, từ_bạn_đọc|None, gợi_ý|None)
    ti = 0  # chỉ số từ mục tiêu (để tra gợi ý theo vị trí đọc ở lượt 1)
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            for t, h in zip(tw[i1:i2], hw[j1:j2]):
                items.append((t, "ok", h, None))
                ti += 1
        else:
            ts, hs = tw[i1:i2], hw[j1:j2]
            for k in range(max(len(ts), len(hs))):
                t = ts[k] if k < len(ts) else None
                h = hs[k] if k < len(hs) else None
                if t and h:
                    fl = flag_pair(t, h, lang)
                    if fl:
                        items.append((t, "warn", h, fl[1]))
                    elif lang in ("vi", "auto") and \
                            strip_tone_vi(key(t)) == strip_tone_vi(key(h)):
                        items.append((t, "tone", h,
                                      "“%s” nghe thành “%s” — sai dấu thanh" % (t, h)))
                    elif lang in ("vi", "auto") and \
                            strip_marks_vi(key(t)) == strip_marks_vi(key(h)):
                        # cùng chữ cái gốc, khác dấu phụ (ă/â/ê/ô/ơ/ư/đ) ± dấu thanh:
                        # "lắm" → "lám". Vẫn là từ sai (không tính đúng), chỉ đặt tên rõ (S-4).
                        items.append((t, "rhyme", h,
                                      "“%s” nghe thành “%s” — sai vần/dấu" % (t, h)))
                    elif ti in pos_flag:
                        items.append((t, "warn", h, pos_flag[ti]))
                    else:
                        items.append((t, "bad", h, None))
                    ti += 1
                elif t:
                    if ti in pos_flag:
                        items.append((t, "warn", h, pos_flag[ti]))
                    else:
                        items.append((t, "bad", None, "Thiếu từ “%s”" % t))
                    ti += 1
                else:
                    items.append((None, "extra", h, None))
    total = len(tw)
    correct = sum(1 for it in items if it[1] == "ok")
    warns = sum(1 for it in items if it[1] == "warn")
    tones = sum(1 for it in items if it[1] == "tone")
    rhymes = sum(1 for it in items if it[1] == "rhyme")
    score = round(100.0 * correct / total, 1) if total else 0.0
    return {"items": items, "score": score, "correct": correct,
            "total": total, "warns": warns, "tones": tones, "rhymes": rhymes,
            "hyp": " ".join(hw)}


def read_aloud_diff(sub_text, learner_hyp, orig_hyp=None):
    """Đọc to đoạn transcript YouTube (D-39): phụ đề vs lời người học, tiếng Anh.

    So sau `yt_read.en_tokens` (rút gọn, số, từ đệm). orig_hyp = Whisper trên audio GỐC
    của đoạn: từ phụ đề mà ở đó cũng không khớp → `doubt` "phụ đề có thể sai"; chữ số đọc
    khác → `doubt` "số". `doubt` không tính vào đúng lẫn tổng. Hàm thuần.
    Trả như `score_pronunciation` + doubts, src_idx (từ mẫu thứ k → chỉ số từ trong
    sub_text.split(), để tô màu chữ gốc).
    """
    import yt_read
    tt = yt_read.en_tokens(sub_text)
    target = " ".join(t for t, _i, _n in tt)

    def hyp(s):
        return " ".join(t for t, _i, _n in yt_read.en_tokens(s))

    res = score_pronunciation(target, hyp(learner_hyp), "en")
    orig = None
    if orig_hyp is not None:
        orig = [it for it in score_pronunciation(target, hyp(orig_hyp), "en")["items"]
                if it[0] is not None]
    items, src, ti = [], [], 0
    for tok, kind, heard, note in res["items"]:
        if tok is None:
            items.append((tok, kind, heard, note))
            continue
        _t, si, is_num = tt[ti] if ti < len(tt) else (tok, None, False)
        if kind != "ok":
            if orig and ti < len(orig) and orig[ti][1] != "ok":
                said = orig[ti][2]
                kind, note = "doubt", ("phụ đề có thể sai — trong video nghe như “%s”" % said
                                       if said else
                                       "phụ đề có thể sai — trong video không nghe rõ từ này")
            elif is_num:
                kind, note = "doubt", "số — có thể đọc khác cách viết"
        items.append((tok, kind, heard, note))
        src.append(si)
        ti += 1
    doubts = sum(1 for it in items if it[1] == "doubt")
    correct = sum(1 for it in items if it[1] == "ok")
    total = len(tt) - doubts
    return {"items": items, "correct": correct, "total": total, "doubts": doubts,
            "score": round(100.0 * correct / total, 1) if total else 0.0,
            "warns": sum(1 for it in items if it[1] == "warn"), "tones": 0, "rhymes": 0,
            "hyp": res["hyp"], "src_idx": src, "target": target}


def token_spans(words_t, target):
    """Từ Whisper có mốc [{w, s, e, p}] → {chỉ số token mẫu: (s, e, p)} sau `en_tokens`.

    target = chuỗi token (res["target"] của read_aloud_diff). Dùng cho ▶ Bạn đọc / ▶ Mẫu
    từng từ và dấu "máy chưa chắc" của đoạn đọc to. Hàm thuần.
    """
    import yt_read
    toks = [(t, w) for w in (words_t or []) for t, _i, _n in yt_read.en_tokens(w.get("w", ""))]
    out = {}
    for (t, w), ti in zip(toks, map_to_target(target, [t for t, _w in toks])):
        if ti is not None and ti not in out:
            out[ti] = (w.get("s"), w.get("e"), w.get("p"))
    return out


PAUSE_MIN = 0.30      # khoảng lặng giữa hai từ ≥ mức này = một chỗ ngừng (mốc Whisper ±0,05 s)
PAUSE_LINKED = 0.12   # người nói ngừng < mức này = đọc liền hai từ
PAUSE_REF_MIN = 0.40  # người nói ngừng ≥ mức này mà bạn đọc liền → "người nói ngừng, bạn đọc liền"
PAUSE_HESIT = 1.0     # ngừng ≥ 1 giây giữa vế câu = ngập ngừng
FLU_LIST_MAX = 4      # số ví dụ tối đa mỗi loại trong panel


def _wpm(spans, src):
    """Từ/phút từ mốc token đầu → cuối (bỏ im lặng hai đầu). Chỉ đếm từ gốc ĐÃ có mốc (người
    học dừng giữa đoạn thì không chia cả đoạn cho phần đã đọc). None nếu quá ít dữ liệu."""
    ts = {k: v for k, v in spans.items() if v[0] is not None and v[1] is not None}
    n_words = len({src[k] for k in ts if k < len(src) and src[k] is not None})
    if len(ts) < 3 or n_words < 3:
        return None
    span = max(e for _s, e, _p in ts.values()) - min(s for s, _e, _p in ts.values())
    return round(60.0 * n_words / span) if span > 0.5 else None


def fluency_view(text, res, mine, orig=None):
    """Trôi chảy + từng câu của một đoạn đọc to (R1, D-39). Hàm thuần, chỉ MÔ TẢ (D-34).

    mine / orig: token_spans của bản thu người học / audio gốc ({token: (s, e, p)}).
    Chỗ ngừng tính ở ranh giới TỪ GỐC (một từ gốc như "I'm" có thể là 2 token).
    Trả {wpm_usr, wpm_ref, runs_usr, runs_ref, extra, missed, hesit, lines, sentences,
    pause_after} — pause_after: {chỉ số từ gốc: "extra"} để vẽ "/" trong đoạn văn.
    """
    import yt_read
    words = (text or "").split()
    src = res.get("src_idx") or []
    orig = orig or {}
    first, last = {}, {}                 # từ gốc → token đầu/cuối của nó
    for k, wi in enumerate(src):
        if wi is not None:
            first.setdefault(wi, k)
            last[wi] = k

    def gap(sp, wi):
        """Khoảng lặng sau từ gốc wi (tới từ gốc kế tiếp có mốc)."""
        a = sp.get(last.get(wi))
        b = sp.get(first.get(wi + 1))
        if not a or not b or a[1] is None or b[0] is None:
            return None
        return b[0] - a[1]

    def pair(wi):
        return "%s / %s" % (words[wi].strip(".,;:?!\"'"), words[wi + 1].strip(".,;:?!\"'"))

    extra, missed, hesit, pause_after = [], [], 0, {}
    pauses_usr = pauses_ref = 0
    breaks = set()
    for wi in range(len(words) - 1):
        gu, gr = gap(mine, wi), gap(orig, wi)
        if gr is not None and gr >= PAUSE_MIN:
            pauses_ref += 1
            breaks.add(wi)
        if gu is None:
            continue
        if gu >= PAUSE_MIN:
            pauses_usr += 1
        natural = yt_read.is_clause_end(words[wi]) or (gr is not None and gr >= PAUSE_MIN)
        if gu >= PAUSE_MIN and not natural and (gr is None or gr < PAUSE_LINKED):
            extra.append({"wi": wi, "text": pair(wi), "gap": round(gu, 2)})
            pause_after[wi] = "extra"
            if gu >= PAUSE_HESIT:
                hesit += 1
        elif gr is not None and gr >= PAUSE_REF_MIN and gu < PAUSE_LINKED:
            missed.append({"wi": wi, "text": words[wi].strip(".,;:?!\"'"), "gap": round(gr, 2)})
    n = len(words)
    wpm_u, wpm_r = _wpm(mine, src), _wpm(orig, src)
    runs_u = round(n / float(pauses_usr + 1), 1) if mine else None
    runs_r = round(n / float(pauses_ref + 1), 1) if orig else None

    lines = []
    if wpm_u:
        ln = "Tốc độ: bạn %d từ/phút" % wpm_u
        if wpm_r:
            ln += " · người nói %d từ/phút" % wpm_r
            if wpm_u < 0.7 * wpm_r:
                ln += " — chậm hơn nhiều; nghe rồi đọc theo từng câu để bắt nhịp"
            elif wpm_u > 1.15 * wpm_r:
                ln += " — nhanh hơn người nói; chậm lại cho rõ từ"
        lines.append(ln)
    if runs_u:
        lines.append("Mỗi hơi bạn đọc ~%s từ" % _vn_num(runs_u).replace(",0", "") + (
            " (người nói ~%s từ)" % _vn_num(runs_r).replace(",0", "") if runs_r else ""))
    if extra:
        lines.append("Ngừng giữa cụm từ (dấu / đỏ trong đoạn): %s — đọc liền cả cụm, chỉ "
                     "ngừng ở dấu câu" % ", ".join("“%s”" % e["text"]
                                                    for e in extra[:FLU_LIST_MAX])
                     + (" … +%d" % (len(extra) - FLU_LIST_MAX)
                        if len(extra) > FLU_LIST_MAX else ""))
    if missed:
        lines.append("Người nói ngừng mà bạn đọc liền: sau %s" % ", ".join(
            "“%s”" % m["text"] for m in missed[:FLU_LIST_MAX]))
    if hesit:
        lines.append("Ngập ngừng (ngừng ≥ 1 giây giữa câu): %d lần" % hesit)

    fix_words = {}
    ti = 0
    for tok, kind, _h, _n in res.get("items") or []:
        if tok is None:
            continue
        wi = src[ti] if ti < len(src) else None
        if wi is not None and kind not in ("ok", "doubt"):
            fix_words[wi] = True
        ti += 1
    sentences = []
    for w0, w1 in yt_read.sentence_ranges(text, breaks):
        toks = [k for k, wi in enumerate(src) if wi is not None and w0 <= wi <= w1]

        def span(sp):
            ts = [sp[k] for k in toks if sp.get(k) and sp[k][0] is not None]
            return (min(t[0] for t in ts), max(t[1] for t in ts)) if len(ts) >= 2 else None
        su, sr = span(mine), span(orig)
        ws = words[w0:w1 + 1]
        heard = sum(1 for k in toks if mine.get(k) and mine[k][0] is not None)
        sentences.append({
            "w0": w0, "w1": w1, "n": len(ws),
            "short": " ".join(ws) if len(ws) <= 8 else " ".join(ws[:7]) + " …",
            "fixes": sum(1 for wi in range(w0, w1 + 1) if wi in fix_words),
            "extra": [e["text"] for e in extra if w0 <= e["wi"] < w1],
            "usr": su, "ref": sr,
            "cov_usr": round(heard / float(len(toks)), 2) if toks else 0.0,
            "dur_usr": round(su[1] - su[0], 1) if su else None,
            "dur_ref": round(sr[1] - sr[0], 1) if sr else None})
    return {"wpm_usr": wpm_u, "wpm_ref": wpm_r, "runs_usr": runs_u, "runs_ref": runs_r,
            "extra": extra, "missed": missed, "hesit": hesit, "lines": lines,
            "sentences": sentences, "pause_after": pause_after}


FLAT_RATIO = 0.6     # dải cao độ của bạn < 60 % người nói → "giọng đều hơn nhiều" (D-44)
INTON_MIN_COVER = 0.6  # câu có < 60 % từ máy nghe được (dừng giữa chừng) → không so cao độ


def intonation_view(sentences, pitch_usr, pitch_ref):
    """Ngữ điệu từng câu của đoạn đọc to (D-44). Hàm thuần, chỉ MÔ TẢ (D-34, I5).

    sentences: fluency_view(...)["sentences"] (có mốc "usr"/"ref"); pitch_*: prosody.pitch_track.
    Chỉ so DẢI cao độ (bền) và trả đường cao độ thu nhỏ để vẽ — không kết luận lên/xuống cuối câu
    (đo thấy không ổn định). → {"sentences": [{range_usr, range_ref, curve_usr, curve_ref}],
    "range_usr", "range_ref", "flat", "lines"}."""
    import numpy as np
    rows, pairs = [], []
    for st in sentences or []:
        # câu bạn đọc chưa tới / máy nghe được < 60 % số từ → mốc câu không tin được, bỏ qua
        u = prosody.segment_pitch(pitch_usr, *(st.get("usr") or (None, None))) \
            if st.get("cov_usr", 1.0) >= INTON_MIN_COVER else None
        r = prosody.segment_pitch(pitch_ref, *(st.get("ref") or (None, None)))
        rows.append({"range_usr": u and u["range"], "range_ref": r and r["range"],
                     "curve_usr": u and u["curve"], "curve_ref": r and r["curve"]})
        if u and r:
            pairs.append((u["range"], r["range"]))
    ru = round(float(np.median([a for a, _b in pairs])), 1) if pairs else None
    rr = round(float(np.median([b for _a, b in pairs])), 1) if pairs else None
    flat = bool(ru is not None and rr and ru < FLAT_RATIO * rr)
    lines = []
    if ru is not None:
        lines.append("Dao động cao độ mỗi câu: bạn ~%s bán cung · người nói ~%s%s" % (
            _vn_num(ru).replace(",0", ""), _vn_num(rr).replace(",0", ""),
            " — giọng bạn đều hơn nhiều" if flat else ""))
        if flat:
            lines.append("Tiếng Anh dùng cao độ để nhấn từ khóa: lên giọng ở từ quan trọng, "
                         "hạ rõ ở cuối câu kể. Nghe đường cao độ của người nói ở từng câu bên "
                         "dưới, bắt chước — lúc đầu cứ phóng đại.")
    return {"sentences": rows, "range_usr": ru, "range_ref": rr, "flat": flat, "lines": lines}


UNREAD_MIN = 3       # ≥ ngần này từ cuối đoạn không nghe thấy → "chưa đọc tới" (người học dừng)
PATTERN_SHOW = 4     # số mẫu lỗi tối đa trong mục ÂM HAY SAI
PATTERN_EXAMPLES = 4


def error_pattern_view(fixes):
    """Từ cần sửa (ytread_view["fixes"]) → mẫu lỗi hay gặp (D-42). Hàm thuần.

    → {"groups": [{code, title, tip, n, examples [(từ, nghe)], ti [token]}] (nhiều từ trước),
       "grouped": số từ thuộc ít nhất một mẫu, "total": số từ cần sửa}. Một từ có thể thuộc
    nhiều mẫu (nose → "low": n→l + âm cuối)."""
    groups, grouped = {}, 0
    fixes = [f for f in fixes or [] if not f.get("unread")]
    for f in fixes:
        codes = pron_en.error_patterns(f.get("word"), f.get("heard"))
        grouped += bool(codes)
        for c in codes:
            title, tip = pron_en.PATTERNS[c]
            g = groups.setdefault(c, {"code": c, "title": title, "tip": tip, "n": 0,
                                      "examples": [], "ex_ti": [], "ti": []})
            g["n"] += 1
            g["ti"].append(f.get("ti"))
            ex = (f.get("word"), f.get("heard"))
            if ex not in g["examples"]:
                g["examples"].append(ex)
                g["ex_ti"].append(f.get("ti"))      # token của ví dụ (▶ Mẫu / ▶ Bạn đọc)
    order = list(pron_en.PATTERNS)
    out = sorted(groups.values(), key=lambda g: (-g["n"], order.index(g["code"])))
    return {"groups": out, "grouped": grouped, "total": len(fixes)}


def pattern_example_text(examples, k=PATTERN_EXAMPLES):
    """[(từ, nghe)] → "molecules → “molecule”, is → (thiếu), …"."""
    parts = ["%s → %s" % (w, "“%s”" % h if h else "(thiếu)") for w, h in examples[:k]]
    more = len(examples) - k
    return ", ".join(parts) + (" … +%d" % more if more > 0 else "")


YT_ROWS_MAX = 24   # số dòng tối đa mỗi nhóm trong panel kết quả (đoạn dài)
_YT_RANK = {"ok": 0, "unsure": 1, "doubt": 2, "warn": 3, "bad": 4}


def ytread_view(res, gate=None):
    """Kết quả đọc to một đoạn → nội dung hiển thị (D-39). Hàm thuần, không Tk.

    marks: {chỉ số từ trong đoạn gốc (text.split()): kind} — kind ok|unsure|doubt|warn|bad;
    fixes / doubts: dòng cho panel phải; ring/headline/summary như bài luyện câu.
    """
    if gate:
        return {"state": "unsure", "gate": gate, "marks": {}, "fixes": [], "doubts": [],
                "extras": [], "ring": {"frac": 0.0, "text": "?", "tone": "muted"},
                "headline": "Máy chưa nghe rõ",
                "summary": "Chưa chấm đoạn này — thử lại theo gợi ý bên dưới.",
                "tips": list(UNSURE_TIPS[:2]), "correct": 0, "total": res.get("total", 0)}
    spans = token_spans(res.get("words_t"), res.get("target", ""))
    marks, fixes, doubts, extras, ti, last_heard = {}, [], [], [], 0, -1
    src = res.get("src_idx") or []
    for tok, kind, heard, note in res.get("items") or []:
        if tok is None:
            extras.append(heard)
            continue
        si = src[ti] if ti < len(src) else None
        k = {"tone": "warn", "rhyme": "bad"}.get(kind, kind)
        if k == "ok":
            p = (spans.get(ti) or (None, None, None))[2]
            if p is not None and p < WORD_UNSURE_P:
                k = "unsure"
        elif k == "doubt":
            # dòng nằm dưới tiêu đề "PHỤ ĐỀ CÓ THỂ SAI" → bỏ phần lặp lại tiêu đề
            doubts.append({"ti": ti, "word": tok, "text": "“%s” — %s" % (
                tok, (note or "").replace("phụ đề có thể sai — ", ""))})
        else:
            # ghi chú của luật lỗi (flag_pair) đã nêu cả hai từ: “thing” nghe thành “ting”…
            fixes.append({"ti": ti, "word": tok, "heard": heard, "kind": k,
                          "text": note if (note or "").startswith("“") else "“%s” — %s" % (
                              tok, note or ("nghe “%s”" % heard if heard
                                            else "chưa đọc từ này"))})
        if si is not None and _YT_RANK[k] > _YT_RANK[marks.get(si, "ok")]:
            marks[si] = k
        elif si is not None:
            marks.setdefault(si, k)
        if heard is not None:
            last_heard = ti
        ti += 1
    # người học dừng giữa đoạn: các từ sau từ cuối cùng máy nghe được là "chưa đọc tới",
    # không phải nuốt âm — vẫn tính thiếu trong điểm (I4) nhưng không xếp vào mẫu lỗi (D-42)
    unread = [f for f in fixes if f["heard"] is None and f["ti"] > last_heard]
    if len(unread) < UNREAD_MIN:
        unread = []
    for f in unread:
        f["unread"] = True
        f["text"] = "“%s” — chưa đọc tới" % f["word"]
    correct, total = res.get("correct", 0), res.get("total", 0)
    frac = correct / float(total) if total else 0.0
    perfect = bool(total) and not fixes and correct == total
    parts = []
    if len(fixes) > len(unread):
        parts.append("%d từ cần sửa" % (len(fixes) - len(unread)))
    if unread:
        parts.append("dừng trước %d từ cuối" % len(unread))
    if doubts:
        parts.append("%d từ không tính (phụ đề có thể sai)" % len(doubts))
    return {"state": "result", "gate": None, "marks": marks,
            "fixes": fixes, "doubts": doubts, "extras": extras,
            "ring": {"frac": frac, "text": "✓" if perfect else "%d/%d" % (correct, total),
                     "tone": "ok" if perfect else ("warn" if frac >= 0.5 else "bad")},
            "headline": ("Hoàn hảo — đúng cả %d từ" % total) if perfect
            else "Đúng %d/%d từ" % (correct, total),
            "summary": " · ".join(parts), "tips": [], "correct": correct, "total": total}


# ---------- báo cáo cuối phiên đọc to (D-43) ----------
REPORT_EXAMPLES = 8    # ví dụ tối đa mỗi mẫu lỗi trong báo cáo
REPORT_WORDS = 20      # số "từ cần luyện" tối đa
REPORT_SLOW = 0.75     # tốc độ < 75 % người nói → ưu tiên "đọc nhanh hơn"


def session_report(info, done):
    """Gom MỌI đoạn đã đọc thành báo cáo cuối (D-43). Hàm thuần, không Tk.

    info: {"title", "url", "sub_kind", "n_paras", "date"}; done: [{"idx", "text", "res",
    "gate", "orig_words", "pitch_ref"}] theo thứ tự đoạn (res["pitch"] = cao độ bản đọc). Đoạn "máy chưa nghe rõ" (gate) liệt kê riêng,
    không tính vào tổng. Mọi nhận xét chỉ mô tả (I4, D-34); điểm = tổng từ đúng / tổng từ.
    """
    paras, pats, words = [], {}, {}
    corr = tot = doubts = unread = 0
    extra, missed, hesit, rng = [], [], 0, []
    w_usr = w_ref = n_usr = n_ref = 0.0
    for d in done:
        res, idx = d["res"], d["idx"]
        v = ytread_view(res, d.get("gate"))
        row = {"idx": idx, "state": v["state"], "headline": v["headline"],
               "correct": v.get("correct", 0), "total": v.get("total", 0),
               "fixes": 0, "wpm_usr": None, "wpm_ref": None, "top": None}
        paras.append(row)
        if v["state"] != "result":
            continue
        tgt = res.get("target", "")
        mine = token_spans(res.get("words_t"), tgt)
        orig = token_spans(d.get("orig_words"), tgt)
        flu = fluency_view(d["text"], res, mine, orig)
        iv = intonation_view(flu["sentences"], res.get("pitch"), d.get("pitch_ref"))
        for it in iv["sentences"]:
            if it["range_usr"] is not None and it["range_ref"] is not None:
                rng.append((it["range_usr"], it["range_ref"]))
        pv = error_pattern_view(v["fixes"])
        fixes = [f for f in v["fixes"] if not f.get("unread")]
        corr, tot = corr + v["correct"], tot + v["total"]
        doubts += len(v["doubts"])
        unread += len(v["fixes"]) - len(fixes)
        row.update(fixes=len(fixes), wpm_usr=flu["wpm_usr"], wpm_ref=flu["wpm_ref"],
                   top=pv["groups"][0]["title"] if pv["groups"] else None,
                   unread=len(v["fixes"]) - len(fixes))
        n = len(d["text"].split())
        if flu["wpm_usr"]:
            w_usr, n_usr = w_usr + flu["wpm_usr"] * n, n_usr + n
        if flu["wpm_ref"]:
            w_ref, n_ref = w_ref + flu["wpm_ref"] * n, n_ref + n
        extra += [dict(e, idx=idx) for e in flu["extra"]]
        missed += [dict(m, idx=idx) for m in flu["missed"]]
        hesit += flu["hesit"]
        for g in pv["groups"]:
            a = pats.setdefault(g["code"], {"code": g["code"], "title": g["title"],
                                            "tip": g["tip"], "n": 0, "examples": [],
                                            "where": []})
            a["n"] += g["n"]
            for ex, ti in zip(g["examples"], g["ex_ti"]):
                if ex not in a["examples"]:
                    a["examples"].append(ex)
                    a["where"].append((idx, ti))
        for f in fixes:
            w = f["word"].lower()
            e = words.setdefault(w, {"word": w, "n": 0, "heard": []})
            e["n"] += 1
            if f["heard"] and f["heard"] not in e["heard"]:
                e["heard"].append(f["heard"])
    order = list(pron_en.PATTERNS)
    groups = sorted(pats.values(), key=lambda g: (-g["n"], order.index(g["code"])))
    wpm_u = round(w_usr / n_usr) if n_usr else None
    wpm_r = round(w_ref / n_ref) if n_ref else None
    scored = [p for p in paras if p["state"] == "result"]

    # 3 điều nên tập trung: thói quen nhiều từ nhất → tốc độ / ngắt nghỉ → thói quen thứ hai
    focus = []
    if groups and groups[0]["n"] >= 2:
        g = groups[0]
        focus.append({"title": "%s (%d từ)" % (g["title"], g["n"]), "detail": g["tip"]})
    if wpm_u and wpm_r and wpm_u < REPORT_SLOW * wpm_r:
        focus.append({"title": "Tốc độ: %d từ/phút, người nói %d" % (wpm_u, wpm_r),
                      "detail": "Chọn “Nghe rồi đọc”, đọc theo từng câu cho tới khi theo kịp "
                                "nhịp người nói; đừng cố đọc nhanh khi chưa rõ âm."})
    import numpy as np
    ru = round(float(np.median([a for a, _b in rng])), 1) if rng else None
    rr = round(float(np.median([b for _a, b in rng])), 1) if rng else None
    flat = bool(ru is not None and rr and ru < FLAT_RATIO * rr)
    if flat:
        focus.append({"title": "Giọng đều: cao độ dao động ~%s bán cung, người nói ~%s" % (
            _vn_num(ru).replace(",0", ""), _vn_num(rr).replace(",0", "")),
            "detail": "Lên giọng ở từ khóa, hạ rõ ở cuối câu kể. Nghe đường cao độ của "
                      "người nói từng câu rồi bắt chước, lúc đầu cứ phóng đại."})
    if len(extra) >= 3:
        focus.append({"title": "Ngừng giữa cụm từ: %d chỗ" % len(extra),
                      "detail": "Đọc liền cả cụm (vd “%s”), chỉ ngừng ở dấu phẩy, dấu chấm."
                                % extra[0]["text"]})
    for g in groups[1:]:
        if len(focus) >= 3:
            break
        if g["n"] >= 2:
            focus.append({"title": "%s (%d từ)" % (g["title"], g["n"]), "detail": g["tip"]})
    fluency = []
    if wpm_u:
        fluency.append("Tốc độ trung bình: bạn %d từ/phút%s" % (
            wpm_u, " · người nói %d từ/phút" % wpm_r if wpm_r else ""))
    if extra:
        fluency.append("Ngừng giữa cụm từ: %d chỗ — %s" % (len(extra), ", ".join(
            "“%s”" % e["text"] for e in extra[:FLU_LIST_MAX])))
    if missed:
        fluency.append("Người nói ngừng mà bạn đọc liền: %d chỗ — sau %s" % (len(missed), ", ".join(
            "“%s”" % m["text"] for m in missed[:FLU_LIST_MAX])))
    if hesit:
        fluency.append("Ngập ngừng (≥ 1 giây giữa câu): %d lần" % hesit)
    intonation = []
    if ru is not None:
        intonation.append("Dao động cao độ mỗi câu: bạn ~%s bán cung · người nói ~%s%s" % (
            _vn_num(ru).replace(",0", ""), _vn_num(rr).replace(",0", ""),
            " — giọng bạn đều hơn nhiều" if flat else ""))
    practise = sorted(words.values(), key=lambda e: (-e["n"], e["word"]))[:REPORT_WORDS]
    return {"title": info.get("title", ""), "url": info.get("url", ""),
            "sub_kind": info.get("sub_kind"), "date": info.get("date", ""),
            "n_paras": info.get("n_paras", 0), "n_read": len(paras), "n_scored": len(scored),
            "correct": corr, "total": tot, "pct": round(100.0 * corr / tot) if tot else 0,
            "doubts": doubts, "unread": unread, "wpm_usr": wpm_u, "wpm_ref": wpm_r,
            "focus": focus[:3], "patterns": groups, "fluency": fluency, "paras": paras,
            "intonation": intonation, "range_usr": ru, "range_ref": rr, "flat": flat,
            "words": practise}


def report_html(rep, audio=None):
    """Báo cáo → trang HTML tự chứa (UTF-8, CSS nội tuyến) để lưu/gửi giáo viên. Hàm thuần.

    audio: {chỉ số đoạn: (file bản đọc, file đoạn gốc)} tên tương đối → thẻ <audio> nghe lại."""
    import html as _h

    def e(s):
        return _h.escape(str(s if s is not None else ""))
    audio = audio or {}
    out = ["<!doctype html><html lang='vi'><head><meta charset='utf-8'>",
           "<meta name='viewport' content='width=device-width,initial-scale=1'>",
           "<title>Báo cáo luyện đọc — %s</title>" % e(rep["title"]),
           "<style>body{font-family:'Segoe UI',system-ui,sans-serif;max-width:880px;margin:24px "
           "auto;padding:0 16px;color:#1f2328;line-height:1.5}h1{font-size:24px;margin:0}"
           "h2{font-size:14px;letter-spacing:.06em;text-transform:uppercase;color:#59636e;"
           "margin:28px 0 8px;border-bottom:1px solid #d1d9e0;padding-bottom:4px}"
           ".muted{color:#59636e}.big{font-size:28px;font-weight:700}.card{background:#f6f8fa;"
           "border-radius:8px;padding:10px 14px;margin:8px 0}.ex{color:#59636e;font-size:14px}"
           "table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:6px 8px;"
           "border-bottom:1px solid #d1d9e0;font-size:14px;vertical-align:top}"
           "audio{height:30px;vertical-align:middle}</style></head><body>",
           "<h1>Báo cáo luyện đọc to</h1>",
           "<p class='muted'>%s<br>%s · đã đọc %d/%d đoạn</p>" % (
               e(rep["title"]), e(rep["date"]), rep["n_read"], rep["n_paras"]),
           "<p><span class='big'>%d/%d từ đúng (%d%%)</span>" % (
               rep["correct"], rep["total"], rep["pct"])]
    if rep["wpm_usr"]:
        out.append("<br><span class='muted'>Tốc độ %d từ/phút%s</span>" % (
            rep["wpm_usr"], " · người nói %d" % rep["wpm_ref"] if rep["wpm_ref"] else ""))
    if rep["doubts"]:
        out.append("<br><span class='muted'>%d từ không tính (phụ đề có thể sai)</span>"
                   % rep["doubts"])
    out.append("</p>")
    if rep["focus"]:
        out.append("<h2>3 điều nên tập trung</h2><ol>")
        out += ["<li><b>%s</b><br><span class='ex'>%s</span></li>" % (e(f["title"]),
                                                                   e(f["detail"]))
                for f in rep["focus"]]
        out.append("</ol>")
    if rep["patterns"]:
        out.append("<h2>Âm hay sai — cả bài</h2>")
        for g in rep["patterns"]:
            out.append("<div class='card'><b>%s</b> · %d từ<br><span class='ex'>Ví dụ: %s"
                       "</span><br>%s</div>" % (
                           e(g["title"]), g["n"],
                           e(pattern_example_text(g["examples"], REPORT_EXAMPLES)), e(g["tip"])))
    if rep.get("intonation"):
        out.append("<h2>Ngữ điệu</h2><ul>")
        out += ["<li>%s</li>" % e(x) for x in rep["intonation"]]
        out.append("</ul>")
    if rep["fluency"]:
        out.append("<h2>Trôi chảy</h2><ul>")
        out += ["<li>%s</li>" % e(x) for x in rep["fluency"]]
        out.append("</ul>")
    out.append("<h2>Từng đoạn</h2><table><tr><th>Đoạn</th><th>Kết quả</th>"
               "<th>Tốc độ</th><th>Nghe lại</th></tr>")
    for p in rep["paras"]:
        sp = ("%s từ/phút" % p["wpm_usr"] + (" (người nói %s)" % p["wpm_ref"]
                                             if p["wpm_ref"] else "")) if p["wpm_usr"] else ""
        res_txt = p["headline"] + (" · %d từ cần sửa" % p["fixes"] if p["fixes"] else "") + (
            " · chưa đọc hết %d từ" % p["unread"] if p.get("unread") else "") + (
            " · hay sai: %s" % p["top"] if p["top"] else "")
        a = audio.get(p["idx"])
        au = ("Bạn: <audio controls src='%s'></audio><br>Người nói: <audio controls src='%s'>"
              "</audio>" % (e(a[0]), e(a[1]))) if a else ""
        out.append("<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            p["idx"] + 1, e(res_txt), e(sp), au))
    out.append("</table>")
    if rep["words"]:
        out.append("<h2>Từ cần luyện</h2><p>%s</p>" % ", ".join(
            "<b>%s</b>%s%s" % (e(w["word"]), " ×%d" % w["n"] if w["n"] > 1 else "",
                               " <span class='ex'>(nghe “%s”)</span>" % e(w["heard"][0])
                               if w["heard"] else "") for w in rep["words"]))
    out.append("<p class='muted' style='margin-top:32px'>Oriole %s · %s · Nhận xét chỉ mô tả, so "
               "với người nói trong video; điểm = số từ máy nghe đúng.</p></body></html>"
               % (e(VERSION), e(rep["url"])))
    return "\n".join(out)


GOP_LEVEL_STRONG = 25 # điểm GOP dưới mức này → "lệch rõ"; còn lại trong issues → "hơi lệch"
VI_SOUND_CODES = {"nl": "N/L", "tone": "dấu thanh", "rhyme": "vần/dấu"}  # "âm hay sai" bài Việt

# ---------- cổng bằng chứng (D-29): không hiện điểm khi máy không chắc ----------
UNSURE_RATIO = 0.5        # low_conf + đúng < 50 % số từ → chưa chấm
GARBAGE_RATIO = 1.6       # nghe ≥ 1,6 × số từ mẫu + điểm < GARBAGE_SCORE → chuỗi bịa
GARBAGE_SCORE = 35
# Câu Whisper hay tự sinh trên bản thu nhỏ/nhiễu (học từ video YouTube). Chỉ tính khi
# câu mẫu KHÔNG chứa cụm đó.
HALLUCINATION_PHRASES = ("cảm ơn các bạn đã theo dõi", "hẹn gặp lại các bạn",
                         "đăng ký kênh", "ghiền mì gõ", "subscribe",
                         "thanks for watching", "thank you for watching")
UNSURE_TIPS = ("Để micro cách miệng 10–20 cm, đọc to và chậm.",
               "Tránh chỗ ồn; tắt quạt hoặc nhạc nền.",
               "Đọc tiếng Việt: chọn Model “small”.")


def evidence_gate(res):
    """None nếu đủ bằng chứng để chấm; ngược lại lý do: hallucination | garbage | low_conf."""
    hyp = " ".join(norm_words(res.get("hyp", "")))
    tgt = " ".join(norm_words(res.get("target", "")))
    for ph in HALLUCINATION_PHRASES:
        p = " %s " % " ".join(norm_words(ph))   # khớp nguyên từ: "subscribe" ≠ "subscribers"
        if p in " %s " % hyp and p not in " %s " % tgt:
            return "hallucination"
    hw_n, tw_n = len(hyp.split()), len(tgt.split())
    if tw_n and hw_n >= GARBAGE_RATIO * tw_n and res.get("score", 0) < GARBAGE_SCORE:
        return "garbage"
    total = res.get("total") or 0
    ratio = (res.get("correct", 0) / float(total)) if total else 0.0
    if res.get("low_conf") and ratio < UNSURE_RATIO:
        return "low_conf"
    return None


# ---------- lời khuyên tiếng Việt (S-4) ----------
_VI_TIPS = {
    "L": ("Lưỡi chỉ chạm nhẹ lợi trên, để hơi thoát hai bên miệng. "
          "Bịt mũi: tiếng vẫn ra là đúng L.", "vi_la.wav"),
    "N": ("Đầu lưỡi bít kín lợi trên, đẩy hơi lên mũi. "
          "Bịt mũi: tiếng nghẹt hẳn là đúng N.", "vi_na.wav"),
}
_VI_INITIALS = ("ngh", "ng", "nh", "ch", "gh", "gi", "kh", "ph", "qu", "th", "tr",
                "b", "c", "d", "đ", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v", "x")
_TONE_NAMES = {"̀": "huyền", "́": "sắc", "̉": "hỏi", "̃": "ngã",
               "̣": "nặng"}


def vi_spell(word):
    """Tách âm tiết tiếng Việt: "lắm" → "l + ăm + thanh sắc". Hàm thuần."""
    import unicodedata
    w = (word or "").lower()
    tone = "ngang"
    for c in unicodedata.normalize("NFD", w):
        if c in _TONE_NAMES:
            tone = _TONE_NAMES[c]
    base = unicodedata.normalize("NFC", strip_tone_vi(w))
    init = next((i for i in _VI_INITIALS if base.startswith(i) and len(base) > len(i)), "")
    rhyme = base[len(init):]
    return (init + " + " if init else "") + rhyme + " + thanh " + tone


def _vi_cards(chips):
    """Thẻ lỗi bài Việt: gom N/L theo chiều, mỗi lỗi thanh/vần một thẻ."""
    cards, groups = [], {}
    for c in chips:
        if c["code"] == "nl":
            key = c["target"][:1].upper()            # L→N hay N→L
            groups.setdefault(key, []).append(c)
    for key, cs in groups.items():
        other = "N" if key == "L" else "L"
        tip, sample = _VI_TIPS.get(key, ("", None))
        cards.append({
            "title": "%s đọc thành %s — %s" % (key, other, ", ".join("“%s”" % c["target"] for c in cs)),
            "level": "%d lần" % len(cs), "tip": tip, "kind": "warn", "ipa": False,
            "word": cs[0]["target"], "sample": sample, "heard": cs[0]["heard"]})
    for c in chips:
        if c["code"] in ("tone", "rhyme"):
            what = "sai dấu thanh" if c["code"] == "tone" else "sai vần/dấu"
            cards.append({
                "title": "“%s” nghe thành “%s”" % (c["target"], c["heard"]),
                "level": what, "kind": "bad" if c["code"] == "rhyme" else "warn", "ipa": False,
                "tip": "Đọc tách: %s, rồi ghép lại liền một hơi." % vi_spell(c["target"]),
                "word": c["target"], "sample": None, "heard": c["heard"]})
    return cards


HIST_TRIES_MAX = 30   # D-30: giữ 30 lần luyện gần nhất mỗi bài


def hist_add_try(hist, sid, view, ts):
    """Ghi một lần luyện vào dict lịch sử (D-30). Hàm thuần — không ghi file.

    Lần "chưa nghe rõ" (view state "unsure", D-29) không được lưu. File cũ thiếu
    "tries" vẫn đọc được (coi như danh sách rỗng).
    """
    if view.get("state") == "unsure":
        return hist
    h = hist.setdefault(sid, {"n": 0, "best": 0.0, "last": None, "ph": {}})
    h["n"] = int(h.get("n", 0)) + 1
    h["last"] = round(float(view.get("score", 0)), 1)
    h["best"] = max(float(h.get("best") or 0), h["last"])
    h["ts"] = ts
    ph = h.get("ph") if isinstance(h.get("ph"), dict) else {}
    for k, n in (view.get("sounds") or {}).items():
        ph[k] = ph.get(k, 0) + int(n)
    h["ph"] = ph
    tries = h.get("tries") if isinstance(h.get("tries"), list) else []
    tries.append({"ts": ts, "c": view.get("correct", 0), "t": view.get("total", 0),
                  "ph": dict(view.get("sounds") or {})})
    h["tries"] = tries[-HIST_TRIES_MAX:]
    return hist


def hist_weakest(hist, lang):
    """Âm hay sai nhất, CHỈ trong các bài cùng ngôn ngữ (D-30) → (nhãn, số lần) | None.

    EN: mã ARPAbet → "/θ/". VI: mã VI_SOUND_CODES → "N/L". Bỏ qua dữ liệu cũ lẫn
    ngôn ngữ (vd âm vị tiếng Anh ghi vào bài Việt khi Whisper nhận nhầm ngôn ngữ).
    """
    tot = {}
    for sid, h in hist.items():
        if not isinstance(h, dict) or PRACTICE_SETS.get(sid, {}).get("lang") != lang:
            continue
        for ph, n in (h.get("ph") or {}).items():
            if (ph in VI_SOUND_CODES) != (lang == "vi"):
                continue
            tot[ph] = tot.get(ph, 0) + int(n)
    if not tot:
        return None
    ph = max(tot, key=tot.get)
    label = VI_SOUND_CODES[ph] if lang == "vi" else "/%s/" % pron_en.ARPABET_IPA.get(ph, ph.lower())
    return label, tot[ph]


STT_STATES = ("idle", "recording", "processing", "result", "error")
PRAC_STATES = ("idle", "recording", "scoring", "result", "unsure", "error", "loading")
# loading: đang lấy transcript + audio gốc của video (đọc to YouTube, D-39)


def stt_controls(state, idle_label):
    """Nút/thanh tiến trình của tab Chuyển văn bản theo trạng thái (D-31). Hàm thuần."""
    return {
        "run_enabled": state != "processing",
        "run_text": {"processing": "Đang xử lý…",
                     "recording": "■  Dừng & chuyển thành văn bản"}.get(state, idle_label),
        "cancel_enabled": state in ("processing", "recording"),
        "show_pbar": state == "processing",
    }


def stt_view(state, has_result):
    """Màn Văn bản (S-8): (vùng chữ, panel phải) theo trạng thái + đã có kết quả. Hàm thuần.

    Kết quả cũ vẫn hiện khi lỗi/hủy lần sau; chỉ "đang thu"/"đang xử lý" thay chỗ nó.
    """
    if state in ("processing", "recording"):
        return state, state
    doc = "result" if has_result else "empty"
    return doc, ("error" if state == "error" else doc)


def prac_controls(state, has_replay):
    """Nút/thanh tiến trình của tab Luyện theo trạng thái (D-31). Hàm thuần.

    Nút thu tròn (B4a): rec_icon "mic" | "stop"; nhãn dưới nút "Thu âm" lần đầu,
    "Thu lại" sau một lần chấm, "Dừng & chấm" khi đang thu.
    """
    return {
        "rec_enabled": state not in ("scoring", "loading"),
        "rec_icon": "stop" if state == "recording" else "mic",
        "rec_label": {"recording": "Dừng & chấm", "scoring": "Đang chấm…",
                      "loading": "Đang tải…",
                      "result": "Thu lại", "unsure": "Thu lại",
                      "error": "Thu lại"}.get(state, "Thu âm"),
        "replay_enabled": has_replay and state not in ("recording", "scoring", "loading"),
        "show_pbar": state in ("scoring", "loading"),
    }


NAV_COMPACT_W = 1240   # cửa sổ hẹp hơn (px ở 100 %) → thanh điều hướng chỉ còn biểu tượng


def nav_compact(width, scale):
    """Thanh điều hướng 60 px chỉ biểu tượng khi cửa sổ hẹp (canvas: 980×640)."""
    return width < NAV_COMPACT_W * scale


SIDE_FRAC, SIDE_MIN, SIDE_MAX = 0.48, 340, 640   # panel kết quả ≈ nửa vùng nội dung


YT_SIDE_FRAC = 0.34   # Từ YouTube: đoạn văn + cột thu âm cạnh nhau cần chỗ hơn câu ngắn
YT_REC_COL = 250      # bề rộng chữ trong cột thu âm cạnh đoạn văn (px ở 100 %)


def side_width(content_w, scale, frac=SIDE_FRAC):
    """Bề rộng panel kết quả: rộng ra theo cửa sổ để cả kết quả nằm trong một trang."""
    return int(max(SIDE_MIN * scale, min(SIDE_MAX * scale, frac * content_w)))


def short_mic_name(name, limit=28):
    """"Microphone Array (Intel® …) [Windows DirectSound]" → "Microphone Array (Intel®…"."""
    base = (name or "").split(" [")[0].strip()
    return base if len(base) <= limit else base[:limit - 1].rstrip() + "…"


def meter_cells(level, n=20):
    """Số ô sáng của thanh mức âm (cùng thang dB với Recorder.level_bar)."""
    db = 20 * math.log10(max(float(level or 0.0), 1e-6))
    return int(round(n * min(1.0, max(0.0, (db + 50) / 44.0))))


def stage_words(target, view=None):
    """Câu mẫu trên sân khấu: mỗi từ GỐC (giữ hoa/dấu câu) + kiểu gạch chân + ghi chú.

    view None (chưa chấm / đang thu) hoặc "unsure" → không tô màu (D-29). Chip của view
    theo thứ tự từ mẫu đã chuẩn hóa; một từ gốc có thể ứng với 0 hoặc nhiều từ chuẩn hóa.
    Từ máy nghe ĐÚNG nhưng GOP thấy âm "lệch rõ" (view["gop_marks"]) → warn "âm /θ/ lệch"
    (D-35; điểm vẫn là số từ đúng, I4). Từ đúng mà Whisper nghe với xác suất thấp
    (view["unsure_words"]) → "unsure" "máy chưa chắc" (D-37).
    kind: plain | ok | unsure | warn | bad. Hàm thuần.
    """
    tokens = (target or "").split()
    chips = list((view or {}).get("chips") or [])
    shown = bool(view) and view.get("state") == "result"
    marks = (view or {}).get("gop_marks") or {}
    unsure = (view or {}).get("unsure_words") or {}
    rank = {"plain": 0, "ok": 1, "warn": 2, "bad": 3}
    out, ci = [], 0
    for ti, tok in enumerate(tokens):
        n = len(norm_words(tok))
        c0 = ci
        mine, ci = chips[ci:ci + n], ci + n
        if not shown or not mine:
            out.append({"text": tok, "kind": "plain", "note": ""})
            continue
        kind, note = "ok", "✓"
        for c in mine:
            k = c["kind"]
            k = "ok" if k == "ok" else ("warn" if k in ("warn", "tone") else "bad")
            if rank[k] > rank[kind]:
                kind = k
                note = ("(thiếu)" if c["kind"] == "missing" or not c.get("heard")
                        else "nghe “%s”" % c["heard"])
        if kind == "ok" and marks.get(ti):
            # chữ đúng nhưng âm lệch rõ (GOP): cảnh báo, KHÔNG trừ điểm (I4)
            kind, note = "warn", "âm %s lệch" % ", ".join("/%s/" % x for x in marks[ti][:2])
        elif kind == "ok" and any(k in unsure for k in range(c0, ci)):
            kind, note = "unsure", "máy chưa chắc"
        out.append({"text": tok, "kind": kind, "note": note})
    return out


# ---------- ngữ điệu, trọng âm, tốc độ: chỉ mô tả, không chấm (S-5 / S-5b, D-10 / D-34) ----------
SAMPLE_TIMES_PATH = os.path.join(MAU_DIR, "en", "word_times.json")
INTON_FLAT = 0.35         # |độ dốc cuối câu| (bán cung / 10 % câu) nhỏ hơn → "đi ngang"
INTON_FLAT_RANGE = 0.5    # khoảng cao độ của bạn < 50 % của mẫu → "giọng hơi đều"
SPEED_SAME = 0.15         # chênh tốc độ ≤ 15 % → "gần giống mẫu"


def load_sample_word_times(path=SAMPLE_TIMES_PATH):
    """Mốc từng từ của audio mẫu (sinh sẵn bằng tools/build_lessons.py) → {id: [{w,s,e}]}."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        les = data.get("lessons") if isinstance(data, dict) else None
        return les if isinstance(les, dict) else {}
    except Exception:
        return {}


def map_to_target(target, heard):
    """Từ máy nghe (theo thứ tự) → chỉ số từ mẫu đã chuẩn hóa (None nếu là từ thừa)."""
    tw = norm_words(target or "")
    hw = [(norm_words(w) or [""])[0] for w in heard]
    out = [None] * len(hw)
    sm = difflib.SequenceMatcher(None, tw, hw, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("equal", "replace"):
            for k in range(min(i2 - i1, j2 - j1)):
                out[j1 + k] = i1 + k
    return out


def _slope_dir(v):
    if v is None:
        return None
    return "flat" if abs(v) < INTON_FLAT else ("down" if v < 0 else "up")


def inton_caption(d):
    """MỘT câu nhận xét ngữ điệu (S-5), không điểm → (câu, tone "ok" | "warn" | None)."""
    say = {"down": "xuống giọng", "up": "lên giọng", "flat": "đi ngang"}
    fr, fu = _slope_dir(d.get("final_ref")), _slope_dir(d.get("final_usr"))
    rr, ru = d.get("range_ref"), d.get("range_usr")
    if fr and fu and fr != fu:
        mine = "giữ giọng ngang" if fu == "flat" else say[fu]
        return "Cuối câu mẫu %s, bạn lại %s" % (say[fr], mine), "warn"
    if rr and ru is not None and ru < INTON_FLAT_RANGE * rr:
        return "Giọng bạn hơi đều — thử nhấn mạnh từ khoá hơn", "warn"
    if fr and fu:
        return "Cuối câu bạn %s giống mẫu ✓" % say[fu], "ok"
    return "Chưa đủ dữ liệu cao độ để nhận xét", None


def _vn_num(v):
    return ("%.1f" % v).replace(".", ",")


def speed_note(span_ref, span_usr):
    """Một dòng về tốc độ đọc (S-5b) — đọc chậm khi luyện là bình thường, không phải lỗi."""
    if not span_ref or not span_usr or span_ref <= 0 or span_usr <= 0:
        return None
    r = span_usr / float(span_ref)
    if abs(r - 1.0) <= SPEED_SAME:
        return "Tốc độ gần giống mẫu (%s s / %s s)" % (_vn_num(span_usr), _vn_num(span_ref))
    pct = int(round(abs(r - 1.0) * 100 / 5.0) * 5)
    return "Bạn đọc %s hơn mẫu ~%d %% (%s s / %s s)" % (
        "chậm" if r > 1 else "nhanh", pct, _vn_num(span_usr), _vn_num(span_ref))


def stress_note(ref_top, usr_top, words):
    """Câu về từ được nhấn (S-5b). ref_top None = bài không có mốc mẫu → chỉ nói về bạn."""
    if not usr_top:
        return None
    q = lambda idx: "“%s”" % words[idx]
    if ref_top is None:
        return "Bạn nhấn mạnh nhất: " + ", ".join(q(i) for i in usr_top)
    if not ref_top:
        return None
    if set(ref_top) & set(usr_top):
        return "Bạn nhấn đúng từ như mẫu ✓ (%s)" % q(ref_top[0])
    return "Mẫu nhấn %s, bạn nhấn %s" % (q(ref_top[0]), q(usr_top[0]))


def inton_view(res, view):
    """Dữ liệu vẽ + chữ cho mục NGỮ ĐIỆU. Hàm thuần; None nếu không có so sánh cao độ.

    labels: nhãn từ đặt theo mốc của BẠN trên trục thời gian chuẩn hóa (gần đúng với
    đường mẫu vì mẫu được kéo cùng 0..100 %); err = từ đó cần sửa (dải màu nhạt);
    su / sr = bạn / mẫu nhấn từ này (chấm đặc / vòng nét đứt).
    """
    d = res.get("inton")
    if not d or (view or {}).get("state") != "result":
        return None
    target = res.get("target", "")
    tw = norm_words(target)
    chips = (view or {}).get("chips") or []
    words_t = res.get("words_t") or []
    dur = float(d.get("dur_usr") or 0.0)
    idx = map_to_target(target, [w["w"] for w in words_t])
    st = res.get("stress") or {}
    usr_top = None
    if st.get("usr") and len(st["usr"].get("prom") or []) == len(words_t):
        usr_top = sorted({idx[i] for i in st["usr"]["top"] if idx[i] is not None})
    ref_top = None
    ref_words = st.get("ref_words") or []
    if st.get("ref") and len(st["ref"].get("prom") or []) == len(ref_words):
        ridx = map_to_target(target, [w["w"] for w in ref_words])
        ref_top = sorted({ridx[i] for i in st["ref"]["top"] if ridx[i] is not None})
    labels = []
    if dur > 0:
        for w, ti in zip(words_t, idx):
            if ti is None:
                continue
            kind = chips[ti]["kind"] if ti < len(chips) else "ok"
            labels.append({"x0": max(0.0, w["s"] / dur), "x1": min(1.0, w["e"] / dur),
                           "text": tw[ti], "err": kind != "ok",
                           "su": bool(usr_top and ti in usr_top),
                           "sr": bool(ref_top and ti in ref_top)})
    enough = len(labels) >= prosody.STRESS_MIN_WORDS
    cap, tone = inton_caption(d)
    span_usr = ((words_t[-1]["e"] - words_t[0]["s"]) if len(words_t) >= 2
                else d.get("span_usr"))
    span_ref = ((ref_words[-1]["e"] - ref_words[0]["s"]) if len(ref_words) >= 2
                else d.get("span_ref"))
    return {"labels": labels if enough else [], "caption": cap, "tone": tone,
            "stress": stress_note(ref_top, usr_top, tw) if enough else None,
            "speed": speed_note(span_ref, span_usr)}


def progress_summary(h, weak=None, lang=None, n=10):
    """Tiến bộ một bài (S-7): đường xu hướng c/t của n lần gần nhất + hai dòng chữ."""
    if not h:
        return {"spark": [], "line1": "Chưa luyện bài này.", "line2": ""}
    tries = [t for t in (h.get("tries") or []) if t.get("t")]
    if tries:
        best = max(tries, key=lambda t: t["c"] / float(t["t"]))
        last = tries[-1]
        line1 = "%d lần · tốt nhất %d/%d · lần trước %d/%d" % (
            h.get("n", len(tries)), best["c"], best["t"], last["c"], last["t"])
    else:
        line1 = "%d lần · tốt nhất %.0f%%" % (h.get("n", 0), h.get("best") or 0)
        if h.get("last") is not None:
            line1 += " · lần trước %.0f%%" % h["last"]
    line2 = ""
    if weak:
        name = {"en": "tiếng Anh", "vi": "tiếng Việt"}.get(lang)
        line2 = "Âm hay sai%s: %s, %d lần" % (" (%s)" % name if name else "", weak[0], weak[1])
    return {"spark": [t["c"] / float(t["t"]) for t in tries[-n:]],
            "line1": line1, "line2": line2}


def gop_level(score):
    """Mức chữ cho điểm GOP (I7: không hiện như % đúng)."""
    return "lệch rõ" if float(score) < GOP_LEVEL_STRONG else "hơi lệch"


# Xác suất Whisper của một từ "đúng" dưới mức này → "máy chưa chắc". asr_bench (từ TTS đọc
# đúng): p<0,5 báo oan ~1/5 câu sạch, p<0,25 không báo oan câu sạch/ồn, 1–2 từ ở mic yếu.
WORD_UNSURE_P = 0.25


def word_unsure_marks(res, chips):
    """{chỉ số từ mẫu chuẩn hóa: p} cho từ chấm ĐÚNG mà Whisper nghe với xác suất thấp.

    Không trừ điểm (I4) — chỉ bỏ dấu ✓ chắc chắn. Giới hạn đã đo (D-37): Whisper vẫn hay
    "sửa" từ đọc sai thành từ đúng với xác suất cao (TTS "tink" → "Think" p 0,80, trong khi
    từ đọc đúng có thể chỉ 0,72), nên dấu này không thay được GOP.
    """
    wt = res.get("words_t") or []
    if not wt:
        return {}
    idx = map_to_target(res.get("target", ""), [w.get("w", "") for w in wt])
    out = {}
    for w, ti in zip(wt, idx):
        p = w.get("p")
        if ti is None or p is None or not (0 <= ti < len(chips)):
            continue
        if chips[ti]["kind"] == "ok" and p < WORD_UNSURE_P:
            out[ti] = min(p, out.get(ti, 1.0))
    return out


def build_result_view(res, lesson=None):
    """Kết quả chấm → nội dung hiển thị (D-31, spec S-2). Hàm thuần, không Tk.

    `_prac_done` chỉ VẼ những gì hàm này trả; mọi quyết định "nói gì" nằm ở đây để
    test được. lesson: {"lang": ...} của bài (None với Học âm / Tùy chỉnh).
    Khóa ổn định: state, target, words, chips, extras_total, notes, mismatches,
    is_en, gop, phon_cards, phon_more, perfect, headline, summary, score_line,
    status_line, flags (low_conf, garbage), sounds (đếm âm cho lịch sử).
    """
    items = res.get("items") or []
    is_en = res.get("det_lang") == "en"
    lang = res.get("det_lang") or (lesson or {}).get("lang") or "auto"
    g = res.get("gop")
    phon = res.get("phon") or {}
    issues = phon.get("issues") or []

    words, chips = [], []
    for tw, st, hw, note in items:
        kind = "missing" if (st == "bad" and not hw) else st
        code = None
        if st == "warn" and tw and hw:
            fl = flag_pair(tw, hw, lang if lang in ("vi", "en") else "auto")
            code = fl[0] if fl else None
        elif st in ("tone", "rhyme"):
            code = st
        w = {"target": tw, "heard": hw, "kind": kind, "note": note, "code": code}
        words.append(w)
        if tw is not None:
            chips.append(w)
    extras = [w["heard"] for w in words if w["kind"] == "extra"]
    extras_total = len(extras)

    n_iss = 0
    if is_en:
        n_iss = len(g.get("issues") or []) if g else len(issues)

    # ---- thẻ "Cần sửa" (S-2/S-4): tối đa 4, phụ âm trước nguyên âm ----
    cards, covered = [], set()
    if is_en and g:
        for it in g.get("issues") or []:
            wi = it.get("wi")
            covered.add(wi)
            heard = chips[wi]["heard"] if isinstance(wi, int) and 0 <= wi < len(chips) else None
            lv = gop_level(it["score"])
            cards.append({"title": "/%s/ trong “%s”" % (it.get("ipa_exp") or it.get("ph", ""), it["word"]),
                          "level": lv, "kind": "bad" if lv == "lệch rõ" else "warn",
                          "tip": it["tip"], "ipa": True, "word": it["word"],
                          "sample": "en/w_%s.wav" % it["word"].lower(), "heard": heard,
                          "detail": "%d%%%s" % (round(it["score"]), (" · mẫu %d%%" % round(it["ref_score"]))
                                               if it.get("ref_score") is not None else "")})
    elif is_en and issues:
        seen = set()
        for it in issues:
            covered.add(it.get("i"))
            key = (it["exp"], it["got"], it["word"])
            if key in seen:
                continue
            seen.add(key)
            got = it.get("ipa_got")
            level = ("nghe thành [%s]" % got) if got else "bị mất"
            if it.get("approx"):
                level += " · đoán theo chữ"
            cards.append({"title": "/%s/ trong “%s”" % (it.get("ipa_exp") or it["exp"], it["word"]),
                          "level": level, "kind": "warn", "tip": it["tip"], "ipa": True,
                          "word": it["word"], "sample": "en/w_%s.wav" % it["word"].lower(),
                          "heard": it.get("heard_word"), "detail": None,
                          "vowel": it.get("kind") == "vowel"})
    elif not is_en:
        cards = _vi_cards(chips)
        covered = {i for i, w in enumerate(chips) if w["code"] in ("nl", "tone", "rhyme")}
    cards_more = max(0, len(cards) - 4)
    cards = cards[:4]

    # âm GOP "lệch rõ" theo từ gốc (wi = chỉ số từ tách khoảng trắng, như gop.score nhận) —
    # để câu trên sân khấu không ghi ✓ cho từ mà mô hình âm học thấy lệch rõ. Không đổi điểm (I4).
    gop_marks = {}
    if is_en and g:
        for it in g.get("issues") or []:
            wi = it.get("wi")
            if isinstance(wi, int) and gop_level(it["score"]) == "lệch rõ":
                ipa = it.get("ipa_exp") or pron_en.ARPABET_IPA.get(it.get("ph"), it.get("ph"))
                if ipa and ipa not in gop_marks.setdefault(wi, []):
                    gop_marks[wi].append(ipa)

    unsure_words = word_unsure_marks(res, chips)

    # ghi chú mức từ chưa có thẻ nào giải thích (vd "Thiếu từ …")
    notes = [w["note"] for i, w in enumerate(chips)
             if w["kind"] in ("warn", "tone", "rhyme", "bad", "missing") and w["note"]
             and i not in covered]

    score, correct, total = res.get("score", 0), res.get("correct", 0), res.get("total", 0)
    # "Hoàn hảo — đúng cả N từ" chỉ khi đúng thật mọi từ (câu dài sai 1 từ vẫn ≥ 95 %)
    perfect = (bool(total) and correct == total and not extras_total and not notes
               and not n_iss and not cards and not res.get("warns") and not res.get("tones")
               and not unsure_words)
    gate = evidence_gate(res)
    state = "unsure" if gate else "result"

    if state == "unsure":
        headline = "Máy chưa nghe rõ bài đọc"
        summary = ("Lần này chưa chấm điểm và không lưu vào tiến bộ — thường do micro nhỏ "
                   "hoặc phòng ồn.")
    elif perfect:
        headline = f"Hoàn hảo — đúng cả {total} từ"
        summary = "Đọc rõ từng từ. Thử bài tiếp theo hoặc đọc nhanh hơn một chút."
    else:
        headline = f"Đúng {correct}/{total} từ"
        first = cards[0]["title"] if cards else (notes[0] if notes else "")
        summary = ("Lỗi chính: " + first) if first else ""
    heard_note = ""
    if gate == "hallucination":
        heard_note = ("Câu này thường do máy tự sinh khi bản thu quá nhỏ hoặc nhiễu, "
                      "không phải lời bạn đọc.")
    elif gate == "garbage":
        heard_note = "Máy nghe ra chuỗi dài bất thường so với câu mẫu — có thể là tiếng ồn."
    hyp_show = res.get("hyp", "")
    if len(hyp_show) > 160:
        hyp_show = hyp_show[:160].rstrip() + " …"
    status_line = "" if state == "unsure" else (
        f"Máy nghe bạn đọc là: “{hyp_show}”"
        + ("  (máy nghe chưa chắc)" if res.get("low_conf") else ""))

    # đếm "âm hay sai" theo NGÔN NGỮ CỦA BÀI (D-30): EN = âm vị ARPAbet, VI = mã n/l/thanh/vần
    sounds = {}
    lesson_lang = (lesson or {}).get("lang")
    if state == "result" and lesson_lang == "en" and is_en:
        if g:
            for it in g.get("issues") or []:
                if it.get("ph"):
                    sounds[it["ph"]] = sounds.get(it["ph"], 0) + 1
        else:
            for ph, n in (phon.get("counts") or {}).items():
                sounds[ph] = sounds.get(ph, 0) + int(n)
    elif state == "result" and lesson_lang == "vi" and not is_en:
        for w in chips:
            if w["code"] in VI_SOUND_CODES:
                sounds[w["code"]] = sounds.get(w["code"], 0) + 1

    if state == "unsure":
        ring = {"frac": 0.0, "text": "?", "tone": "muted"}
    else:
        frac = (correct / float(total)) if total else 0.0
        ring = {"frac": frac, "text": "✓" if perfect else f"{correct}/{total}",
                "tone": "ok" if perfect or frac >= 1 else ("warn" if frac >= 0.5 else "bad")}

    return {
        "state": state, "gate": gate,
        "target": res.get("target", ""), "words": words, "chips": chips,
        "extras": extras, "extras_total": extras_total, "notes": notes,
        "is_en": is_en, "cards": cards, "cards_more": cards_more, "has_gop": bool(is_en and g),
        "gop_has_ref": bool(g and g.get("has_ref")),
        "n_issues": n_iss, "perfect": perfect, "correct": correct, "total": total,
        "gop_marks": gop_marks, "unsure_words": unsure_words, "model": res.get("model"),
        "score": score, "ring": ring, "headline": headline, "summary": summary,
        "score_line": "" if state == "unsure" else f"{correct}/{total} từ",
        "status_line": status_line,
        "heard_text": res.get("hyp", ""), "heard_note": heard_note,
        "tips": list(UNSURE_TIPS) if state == "unsure" else [],
        "low_conf": bool(res.get("low_conf")), "garbage": bool(res.get("garbage")),
        "sounds": sounds,
    }

# ======================================================================
#  GIAO DIỆN v2.0
#  3 tab: Chuyển thành văn bản (File / YouTube / Ghi âm) · Luyện phát âm · Cài đặt
# ======================================================================

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DEFAULT_CFG = {
    "model": "base",
    "lang": "auto",
    "out_dir": "",
    "theme": "light",
    "yt_kind": "video",
    "yt_quality": "best",
    "subs": True,
    "embed": True,
    "sub_lang": "auto",
    "mic": "",
    "geometry": "1200x830",
}

THEMES = {
    # D-32 (canvas thiết kế GATE B): bg = khung cửa sổ + thanh điều hướng, card = vùng nội
    # dung, side = panel chi tiết bên phải, nav_sel = mục đang chọn (+ vạch accent 3 px)
    "light": {
        "bg": "#F1F3F6", "card": "#FFFFFF", "card2": "#F5F7FA", "side": "#FAFBFC",
        "nav_sel": "#FFFFFF", "border": "#E1E6EC",
        "fg": "#17212B", "muted": "#56636F", "accent": "#0B6BCB", "accent2": "#0958A8",
        "field": "#FFFFFF", "sel": "#CFE3F7",
        "ok_bg": "#DFF3E3", "bad_bg": "#FDE2E2", "warn_bg": "#FFF0D1",
        "ok_fg": "#1B5E20", "bad_fg": "#A8001B", "log_bg": "#F7F9FB",
        "btn": "#F2F5F8", "btn_hover": "#E3E9F0", "disabled": "#EEF1F5",
        "disabled_fg": "#9AA5B1",
        "warn_fg": "#7A4B00", "accent_fg": "#0A5DB0", "info_bg": "#E7F0FB",
        "track": "#E3E8EE", "ring_ok": "#2E7D32", "ring_warn": "#C77700",
        "ring_bad": "#C62828",
        # nút thu (cùng đỏ hai theme: chữ trắng 5,5 : 1), gạch chân từ, dải lỗi trên biểu đồ
        "rec": "#C8282E", "rec_ring": "#FBE3E4", "warn_line": "#C77700",
        "bad_line": "#C62828", "band": "#FFF6E3",
    },
    "dark": {
        "bg": "#141619", "card": "#1D2024", "card2": "#262A30", "side": "#202328",
        "nav_sel": "#262A30", "border": "#33383F",
        "fg": "#E8EBEF", "muted": "#A3ADB8", "accent": "#2F6FD0", "accent2": "#2A5FB5",
        "field": "#1A1D21", "sel": "#2F4A6B",
        "ok_bg": "#1D3A25", "bad_bg": "#4A2026", "warn_bg": "#45391A",
        "ok_fg": "#9BE3A5", "bad_fg": "#FF9AA2", "log_bg": "#1A1D21",
        "btn": "#2A2E34", "btn_hover": "#33383F", "disabled": "#262A30",
        "disabled_fg": "#6B747E",
        "warn_fg": "#F5C76B", "accent_fg": "#8AB6FF", "info_bg": "#1E2F48",
        "track": "#33383F", "ring_ok": "#4CAF50", "ring_warn": "#E0A030",
        "ring_bad": "#E57373",
        "rec": "#C8282E", "rec_ring": "#4A2026", "warn_line": "#E0A030",
        "bad_line": "#E57373", "band": "#3A3220",
    },
}

YT_KINDS = [("subs", "Chỉ transcript (.srt/.txt)"),
            ("video", "Video MP4 (+ phụ đề)"),
            ("audio", "Audio MP3 (+ phụ đề)")]
YT_KIND_NAMES = [n for _, n in YT_KINDS]
YT_KIND_BY_NAME = {n: c for c, n in YT_KINDS}
YT_KIND_NAME = {c: n for c, n in YT_KINDS}

# Bài luyện: chờ 1,8 s im lặng mới tự dừng (1,3 s cũ cắt ngang người học dừng giữa câu để
# nhớ từ). Tab Văn bản không tự dừng theo im lặng.
PRAC_SILENCE_SEC = 1.8
REC_LONG_SEC = 900          # giới hạn ghi âm ở tab chuyển văn bản (15 phút)


def load_config():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k, v in data.items():
                if k in cfg:
                    cfg[k] = v
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def safe_stem(title, vid=""):
    """Tên file an toàn trên Windows từ tiêu đề video."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(title or "")).strip().strip(".")
    s = re.sub(r"\s+", " ", s)[:80].strip()
    if not s:
        s = "transcript"
    return f"{s} [{vid}]" if vid else s


def quality_note(info):
    # peak1 là đỉnh SAU khi chuẩn hóa (luôn ~70%) -> phải dùng peak0 (đỉnh gốc).
    p0 = float(info.get("peak0", 0.0) or 0.0)
    parts = ["đỉnh vào %.0f%%" % (min(p0, 1.0) * 100)]
    if info.get("trimmed", 0) > 0.2:
        parts.append("cắt %.1fs im lặng" % info["trimmed"])
    if info.get("clipped"):
        parts.append("đầu vào bị VỠ — lần sau để mic xa hơn / giảm volume")
    elif p0 < 0.03:
        parts.append("đầu vào hơi NHỎ — để mic gần hơn (10–20cm)")
    elif p0 < 0.05:
        parts.append("đầu vào hơi nhỏ — đọc to hơn một chút")
    snr = info.get("snr_db")
    if snr is not None and snr < SNR_LOW_DB:
        parts.append("phòng hơi ồn (giọng chỉ to hơn nền ~%d dB) — tắt quạt/nhạc, "
                     "nói gần mic hơn" % round(snr))
    if info.get("dropped"):
        parts.append("mất %d đoạn âm khi thu (máy đang bận)" % info["dropped"])
    return "Đã xử lý: " + ", ".join(parts) + "."


def wav_peak(path):
    """Đỉnh biên độ (0..1) của file wav — để phát hiện file gần như im lặng."""
    try:
        import wave
        import numpy as np
        with wave.open(path, "rb") as w:
            sw = w.getsampwidth()
            raw = w.readframes(w.getnframes())
        if sw == 2:
            x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif sw == 1:
            x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sw == 4:
            x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
        else:
            return 1.0
        return float(np.max(np.abs(x))) if len(x) else 0.0
    except Exception:
        return 1.0


def register_ui_fonts(font_dir=FONTS_DIR):
    """Đăng ký font đóng gói cho riêng tiến trình (FR_PRIVATE, không cài vào Windows).

    Gọi TRƯỚC khi tạo cửa sổ Tk. Trả số file đăng ký được (0 nếu thiếu file / không
    phải Windows) — khi đó pick_ui_font tự lùi về font hệ thống.
    """
    try:
        import ctypes
        add = ctypes.windll.gdi32.AddFontResourceExW
    except Exception:
        return 0
    n = 0
    for name in UI_FONT_FILES:
        p = os.path.join(font_dir, name)
        if not os.path.isfile(p):
            continue
        try:
            if add(p, 0x10, 0) > 0:  # 0x10 = FR_PRIVATE
                n += 1
        except Exception:
            pass
    return n


def pick_ui_font(families, prefs=UI_FONT_PREFS):
    """Font đầu tiên trong prefs mà Tk thấy; không có thì 'Segoe UI'."""
    have = set(families)
    for f in prefs:
        if f in have:
            return f
    return "Segoe UI"


def _hex_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _mix(fg, bg, a):
    f, b = _hex_rgb(fg), _hex_rgb(bg)
    return "#%02x%02x%02x" % tuple(int(round(b[i] + (f[i] - b[i]) * a)) for i in range(3))


def _seg_dist(px_, py_, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / float(dx * dx + dy * dy)))
    return math.hypot(px_ - (ax + t * dx), py_ - (ay + t * dy))


def _raster(size, layers, bg, ss=3):
    """Vẽ các lớp hình (màu, hàm inside(x,y) trên toạ độ 0..1) có khử răng cưa.

    Trả list hàng, mỗi hàng là list '#rrggbb' hoặc None (trong suốt). Hàm thuần.
    """
    rows = []
    step = 1.0 / (size * ss)
    for y in range(size):
        row = []
        for x in range(size):
            col, cov_any = None, 0.0
            for color, inside in layers:
                hit = 0
                for sy in range(ss):
                    for sx in range(ss):
                        if inside((x * ss + sx + 0.5) * step, (y * ss + sy + 0.5) * step):
                            hit += 1
                a = hit / float(ss * ss)
                if a > 0:
                    col = _mix(color, col or bg, a) if col or a < 1 else color
                    cov_any = max(cov_any, a)
            row.append(col if cov_any > 0 else None)
        rows.append(row)
    return rows


def indicator_rows(kind, on, size, colors):
    """Ảnh chỉ báo radio/checkbox theo theme (V-01, V-02). Hàm thuần, dễ test.

    kind: "radio" | "check"; colors: {"box","fill","accent","mark","bg"}.
    Checkbox chọn = nền accent + dấu ✓ trắng (không còn dấu "✕" của theme clam).
    """
    edge = colors["accent"] if on else colors["box"]
    if kind == "radio":
        layers = [(edge, lambda x, y: (x - .5) ** 2 + (y - .5) ** 2 <= .45 ** 2),
                  (colors["fill"], lambda x, y: (x - .5) ** 2 + (y - .5) ** 2 <= .33 ** 2)]
        if on:
            layers.append((colors["accent"],
                           lambda x, y: (x - .5) ** 2 + (y - .5) ** 2 <= .2 ** 2))
    else:
        def rbox(r, pad):
            def inside(x, y):
                qx = max(abs(x - .5) - (.5 - pad - r), 0)
                qy = max(abs(y - .5) - (.5 - pad - r), 0)
                return qx * qx + qy * qy <= r * r
            return inside
        layers = [(edge, rbox(.16, .06))]
        if on:
            layers.append((colors["mark"], lambda x, y: min(
                _seg_dist(x, y, .26, .52, .43, .69), _seg_dist(x, y, .43, .69, .75, .33)) <= .075))
        else:
            layers.append((colors["fill"], rbox(.1, .14)))
    return _raster(size, layers, colors["bg"])


def logo_rows(size, accent="#0B6BCB"):
    """Biểu tượng cửa sổ Oriole (V-08): vòng tròn xanh + chim vàng. Hàm thuần."""
    bird = [(9, 19), (11, 15.5), (14, 13), (18, 11.4), (23, 12), (21, 13.2), (20, 15),
            (20, 17.2), (18.6, 19.8), (16, 21.6), (13, 22), (10.8, 21.2)]
    bird = [(x / 32.0, y / 32.0) for x, y in bird]

    def in_poly(x, y):
        hit, j = False, len(bird) - 1
        for i in range(len(bird)):
            xi, yi = bird[i]
            xj, yj = bird[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                hit = not hit
            j = i
        return hit
    return _raster(size, [
        (accent, lambda x, y: (x - .5) ** 2 + (y - .5) ** 2 <= (15 / 32.0) ** 2),
        ("#F5B82E", in_poly),
        ("#17212B", lambda x, y: (x - 19 / 32.0) ** 2 + (y - 13.5 / 32.0) ** 2 <= (1.4 / 32.0) ** 2),
    ], "#FFFFFF")


def rows_to_photo(img, rows):
    """Đổ kết quả _raster vào tk.PhotoImage (pixel None = trong suốt)."""
    img.blank()
    img.put(" ".join("{" + " ".join(c or "#000000" for c in r) + "}" for r in rows))
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c is None:
                img.transparency_set(x, y, True)
    return img


def remove_temp(path):
    """Xóa file tạm, bỏ qua lỗi (đã xóa / đang bị khóa). True nếu file không còn."""
    if not path:
        return True
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return True


def save_frames_wav(frames, prefix, src_rate):
    """Ghép frame int16 -> lọc ù/chuẩn hóa/cắt im lặng -> file wav 16k mono."""
    import numpy as np
    raw = np.concatenate(frames, axis=0).flatten().astype(np.float32) / 32768.0
    y16 = resample_to_16k(raw, src_rate, REC_RATE)
    audio_i16 = (np.clip(y16, -1.0, 1.0) * 32767).astype(np.int16)
    audio, info = enhance_audio(audio_i16, REC_RATE)
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".wav")
    os.close(fd)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(REC_RATE)
        w.writeframes(audio.tobytes())
    return path, len(audio) / REC_RATE, info


_IPA_RANGES = ((0x0250, 0x02AF), (0x02B0, 0x02FF), (0x03B8, 0x03B8), (0x014B, 0x014B),
               (0x00F0, 0x00F0))


def has_ipa(text):
    """Chuỗi có ký tự IPA (θ ð ŋ ɪ ˈ…) → phải vẽ bằng FONT_IPA (D-28)."""
    return any(lo <= ord(ch) <= hi for ch in (text or "") for lo, hi in _IPA_RANGES)


def wav_segment_bounds(n_frames, rate, start, end, pad=0.12):
    """Khung [a, b) cho đoạn start..end giây, nới pad giây hai đầu, kẹp trong file."""
    a = max(0, int((float(start) - pad) * rate))
    b = min(int(n_frames), int(round((float(end) + pad) * rate)))
    return a, max(a, b)


def play_wav_segment(path, start, end):
    """Phát một đoạn của file wav (vd một từ trong bản thu — nút "▶ Bạn đọc")."""
    import numpy as np
    import sounddevice as sd
    with wave.open(path, "rb") as w:
        n, fr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
        a, b = wav_segment_bounds(n, fr, start, end)
        w.setpos(a)
        data = np.frombuffer(w.readframes(b - a), dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            data = data.reshape(-1, ch).mean(axis=1)
    peak = float(np.max(np.abs(data))) if len(data) else 0.0
    if peak > 1e-6:
        data = data * min(1.0, 0.7 / peak)
    sd.play(data, fr)
    sd.wait()


def play_wav_file(path):
    """Phát file wav (chuẩn hóa -3dB cho đều tai). Ném lỗi nếu không phát được."""
    import numpy as np
    import sounddevice as sd
    with wave.open(path, "rb") as w:
        n, fr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            data = data.reshape(-1, ch).mean(axis=1)
    peak = float(np.max(np.abs(data))) if len(data) else 0.0
    if peak > 1e-6:
        data = data * min(1.0, 0.7 / peak)
    sd.play(data, fr)
    sd.wait()


class Recorder:
    """Thu âm dùng chung: tab chuyển văn bản + tab luyện phát âm."""

    def __init__(self):
        self.frames = []
        self.level = 0.0
        self.rate = REC_RATE
        self.t0 = 0.0
        self.active = False
        self.speech_seen = False
        self.voice_t = 0.0
        self.stop_reason = None
        self.dropped = 0        # số block báo input overflow (máy bận, mất âm)
        self._blocks = queue.Queue()

    def start(self, device, rate, max_sec, on_autostop, on_error,
              auto_stop=None):
        """Thu âm.

        auto_stop={"silence": 1.3, "min_speech": 0.4, "start_timeout": 7.0}
        -> tự dừng khi đọc xong (im lặng sau khi đã nói) hoặc khi không nghe
        thấy giọng. on_autostop(reason) với reason = "max" | "silence" | "nospeech".
        """
        import numpy as np
        import sounddevice as sd

        self.frames = []
        self.level = 0.0
        self.rate = rate
        self.t0 = time.time()
        self.active = True
        self.speech_seen = False
        self.voice_t = 0.0
        self.stop_reason = None
        self.dropped = 0
        cap = int(max_sec * rate)
        step = max(1, int(rate * 0.1))
        cfg = dict(auto_stop or {})
        silence = float(cfg.get("silence", 0.0) or 0.0)
        min_speech = float(cfg.get("min_speech", 0.35) or 0.0)
        start_timeout = float(cfg.get("start_timeout", 0.0) or 0.0)
        calib = []      # 0,5 s đầu: đo nền nhiễu
        noise = 0.003

        def finish(reason):
            self.stop_reason = reason
            self.active = False
            on_autostop(reason)

        blocks = self._blocks
        while not blocks.empty():      # bỏ block cũ của lần thu trước
            try:
                blocks.get_nowait()
            except queue.Empty:
                break

        def _on_block(indata, frames_n, t_info, status):
            if status and getattr(status, "input_overflow", False):
                self.dropped += 1
            if self.active:
                blocks.put(indata.copy())

        def run():
            nonlocal noise
            got = 0
            try:
                # Callback mode, KHÔNG dùng stream.read: trên máy này DirectSound
                # trả toàn số 0 với blocking read (lỗi driver/PortAudio) trong khi
                # callback vẫn thu bình thường -> trước đây app báo "mic im lặng".
                with sd.InputStream(device=device, samplerate=rate, channels=1,
                                    dtype="int16", blocksize=step,
                                    callback=_on_block) as stream:
                    while self.active:
                        try:
                            data = blocks.get(timeout=0.25)
                        except queue.Empty:
                            continue
                        if data is None or len(data) == 0:
                            continue
                        self.frames.append(np.asarray(data, dtype=np.int16).copy())
                        got += len(data)
                        blk = np.asarray(data, dtype=np.float32) / 32768.0
                        rms = float(np.sqrt(np.mean(blk * blk)))
                        self.level = rms
                        now = time.time()

                        # 0,5 s đầu đo nền nhiễu; sau đó ngưỡng bật/tắt có hysteresis
                        # để người nói nhỏ vẫn không bị cắt giữa chừng.
                        # Phân vị 20 thay cho trung vị: người đọc ngay khi bấm thì nửa
                        # sau của 0,5 s đã là giọng, trung vị sẽ coi giọng là nền nhiễu.
                        if now - self.t0 < 0.5:
                            calib.append(rms)
                            noise = float(np.percentile(calib, 20))
                        elif not self.speech_seen:
                            # Sàn thấp (0,4% RMS): micro array laptop cho đỉnh ~2%
                            # (RMS ~0,5%) vẫn phải bật được, nếu không app báo oan
                            # "không nghe thấy giọng". Trần 2,4% chặn phòng ồn.
                            thr = max(0.004, min(0.024, noise * 2.2))
                            if rms > thr:
                                self.speech_seen = True
                                self.voice_t = now
                            else:
                                noise = 0.9 * noise + 0.1 * rms
                        else:
                            thr = max(0.0025, min(0.022, noise * 1.2))
                            if rms > thr:
                                self.voice_t = now
                            elif rms < thr * 0.7:
                                noise = 0.98 * noise + 0.02 * rms

                        if now - self.t0 > max_sec or got >= cap:
                            finish("max")
                            break
                        if auto_stop:
                            if (not self.speech_seen and start_timeout > 0
                                    and now - self.t0 > start_timeout):
                                finish("nospeech")
                                break
                            if (self.speech_seen and silence > 0
                                    and now - self.voice_t > silence
                                    and now - self.t0 > min_speech):
                                finish("silence")
                                break
            except Exception as e:
                self.active = False
                msg = str(e)
                if "Blocking API not supported" in msg:
                    msg = ("Micro WDM-KS không hỗ trợ thu liên tục trong app. "
                           "Hãy chọn micro cùng tên ở [Windows WASAPI] hoặc [MME].")
                elif "WdmSyncIoctl" in msg or "Unanticipated host error" in msg:
                    msg = ("Không mở được micro — thiết bị đang bận hoặc driver lỗi. "
                           "Đóng ứng dụng khác đang dùng micro (Zoom/Teams/trình duyệt), "
                           "rút ra cắm lại tai nghe, rồi bấm Quét lại và thử lại.")
                on_error(f"Lỗi thu âm: {msg}\nThử chọn micro khác hoặc bấm Quét lại.")

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self.active = False
        time.sleep(0.15)
        # Vớt nốt các block còn trong hàng đợi (callback có thể nhanh hơn vòng xử lý).
        while True:
            try:
                d = self._blocks.get_nowait()
            except queue.Empty:
                break
            if d is not None and len(d):
                self.frames.append(d.copy())
        return list(self.frames), self.rate

    def level_bar(self):
        import math
        peak = max(self.level, 1e-6)
        db = 20 * math.log10(peak)
        n = int(round(10 * min(1.0, max(0.0, (db + 50) / 44))))
        state = "TỐT" if -30 <= db <= -6 else ("NHỎ" if db < -30 else "TO/VỠ")
        return "[" + "#" * n + "·" * (10 - n) + f"]  {db:.0f} dB  ({state})"

class App(tk.Tk):
    def __init__(self):
        register_ui_fonts()  # phải trước khi tạo cửa sổ để Tk thấy Be Vietnam Pro (D-28)
        super().__init__()
        import tkinter.font as tkfont
        self.F = pick_ui_font(tkfont.families(self))
        self.cfg = load_config()
        self.title(f"{APP_TITLE} v{VERSION}")
        # Tỉ lệ DPI: 100% -> 1.0, 150% -> 1.5, 250% -> 2.5. Mọi số đo pixel đều nhân tỉ lệ này
        # để giao diện không bị bóp nhỏ / chữ quá to trên màn hình HiDPI.
        try:
            self.S = max(1.0, min(3.0, self.winfo_fpixels("1i") / 96.0))
        except Exception:
            self.S = 1.0
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(int(1480 * self.S), int(sw * 0.94))
        h = min(int(940 * self.S), int(sh * 0.92))
        ge = str(self.cfg.get("geometry") or "")
        m = re.match(r"^(\d+)x(\d+)", ge)
        if m:
            gw, gh = int(m.group(1)), int(m.group(2))
            if gw >= int(900 * self.S) and gh >= int(600 * self.S):
                w, h = min(gw, int(sw * 0.96)), min(gh, int(sh * 0.94))
        self.geometry(f"{w}x{h}")
        self.minsize(int(980 * self.S), int(640 * self.S))

        # ----- biến dùng chung -----
        self.model_name = tk.StringVar(value=self.cfg.get("model", "base"))
        self.lang = tk.StringVar(value=self.cfg.get("lang", "auto"))
        # ô Ngôn ngữ hiển thị tên tiếng Việt; hai biến tự đồng bộ (V-13)
        self.lang_label = tk.StringVar(value=LANG_NAME.get(self.lang.get(), LANG_NAMES[0]))
        self.lang_label.trace_add("write", lambda *_: self._lang_from_label())
        self.lang.trace_add("write", lambda *_: self._lang_to_label())
        self.out_dir = tk.StringVar(value=self.cfg.get("out_dir") or YT_DIR_DEFAULT)
        self.theme_name = tk.StringVar(value=self.cfg.get("theme", "light"))
        self.status = tk.StringVar(value="Sẵn sàng — chọn nguồn rồi bấm Bắt đầu.")
        self.mic_test_msg = tk.StringVar(value="Nói “a…” trong 2 giây để đo mức tín hiệu.")

        # ----- nguồn -----
        self.src = tk.StringVar(value="file")
        self.file_path = tk.StringVar()
        self.yt_url = tk.StringVar()
        self.yt_kind = tk.StringVar(
            value=YT_KIND_NAME.get(self.cfg.get("yt_kind"), YT_KIND_NAMES[1]))
        self.yt_quality = tk.StringVar(
            value={c: n for c, n in YT_QUALITIES}.get(self.cfg.get("yt_quality"),
                                                      YT_QUALITIES[0][1]))
        self.y_subs = tk.BooleanVar(value=bool(self.cfg.get("subs", True)))
        self.y_embed = tk.BooleanVar(value=bool(self.cfg.get("embed", True)))
        self.yt_sub_lang = tk.StringVar(
            value={c: n for c, n in YT_SUB_LANGS}.get(self.cfg.get("sub_lang"),
                                                       YT_SUB_LANG_NAMES[0]))

        self.show_time = tk.BooleanVar(value=False)
        self.busy = False          # = stt_state == "processing" (đặt trong _set_stt_state)
        self.stt_state = "idle"    # D-31
        self.cancel_flag = False
        self._queue = queue.Queue()
        self._texts = []          # (widget, role) để đổi màu khi đổi theme
        self.last_cues = []
        self.last_payload = {}
        self.last_media = None
        self.last_srt = None
        self.last_txt = None

        # ----- thu âm -----
        self.recorder = Recorder()
        self.recording = False
        self.rec_owner = None     # "stt" (tab 1) | "prac" (tab 2): ai đang dùng recorder
        self.last_wav = None      # bản ghi luyện gần nhất (Nghe lại) — xóa khi thay/đóng app
        self.playing = False

        # ----- luyện phát âm -----
        self.prac_mode = tk.StringVar(value="set")
        self.prac_pick = tk.StringVar(value=SET_NAMES[0])
        self.set_id = tk.StringVar(value="vi1")
        self.guide_id = tk.StringVar(value="n")
        self.custom_text = tk.StringVar(value="")
        self.p_status = tk.StringVar(value="Chọn bài (hoặc âm), bấm Thu âm rồi đọc to, rõ.")
        self.p_working = False     # = prac_state == "scoring" (đặt trong _set_prac_state)
        self.prac_state = "idle"   # D-31
        self.mic_var = tk.StringVar()
        self.mic_ids = []
        self._mic_probing = False
        self._mic_names = []
        self._mic_combos = []
        self._mic_hints = []
        self.hist = self._load_hist()
        self.sample_times = load_sample_word_times()   # mốc từ của audio mẫu (S-5b)
        self._inton = None

        self._apply_theme()
        self._build_ui()
        self.yt_kind.trace_add("write", lambda *_: self._yt_subs_changed())
        self._yt_subs_changed()
        self._refresh_mics()
        self._src_changed()
        self._refresh_practice()
        self._poll()  # vòng lặp nhận cập nhật từ worker (tự lặp lại mỗi 80ms)
        self._log("Sẵn sàng. Chọn file, dán link YouTube hoặc thu âm rồi bấm Bắt đầu.")
        self._render_preview()
        self._set_icon()
        self.update_idletasks()
        self._stt_view()
        # Cài đặt lưu ngay khi đổi (B5) — bật sau khi dựng xong để không ghi lúc khởi động
        for v in (self.out_dir, self.y_subs, self.y_embed, self.yt_sub_lang, self.yt_kind,
                  self.yt_quality, self.mic_var, self.model_name, self.lang):
            v.trace_add("write", self._autosave)
        self._autosave_on = True

        self.bind("<Control-o>", lambda e: self._pick_file())
        self.bind("<Control-s>", lambda e: self._save_txt())
        self.bind("<Control-Return>", lambda e: self._primary())
        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================= giao diện chung =================
    def px(self, v):
        """Đổi số đo thiết kế (px ở 100%) sang pixel thật theo DPI."""
        return int(round(float(v) * self.S))

    def _set_icon(self):
        """Biểu tượng cửa sổ/taskbar vẽ bằng code, không cần file ảnh (V-08)."""
        try:
            self._icons = [rows_to_photo(tk.PhotoImage(master=self, width=n, height=n),
                                         logo_rows(n)) for n in (64, 32)]
            self.iconphoto(True, *self._icons)
        except Exception:
            pass

    def _lang_from_label(self):
        code = LANG_BY_NAME.get(self.lang_label.get())
        if code and code != self.lang.get():
            self.lang.set(code)

    def _lang_to_label(self):
        name = LANG_NAME.get(self.lang.get())
        if name and name != self.lang_label.get():
            self.lang_label.set(name)

    def _apply_theme(self):
        P = THEMES.get(self.theme_name.get(), THEMES["light"])
        self.P = P
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        F = self.F
        st.configure(".", font=(F, 10), background=P["bg"], foreground=P["fg"],
                     fieldbackground=P["field"], bordercolor=P["border"],
                     lightcolor=P["card"], darkcolor=P["card"], insertcolor=P["fg"])
        st.configure("App.TFrame", background=P["bg"])
        st.configure("Card.TFrame", background=P["card"], bordercolor=P["border"],
                     relief="solid", borderwidth=1)
        st.configure("CardInner.TFrame", background=P["card"], borderwidth=0, relief="flat")
        st.configure("Card2.TFrame", background=P["card2"])
        st.configure("Header.TFrame", background=P["card"])

        st.configure("TLabel", background=P["bg"], foreground=P["fg"])
        st.configure("Card.TLabel", background=P["card"], foreground=P["fg"])
        st.configure("Card2.TLabel", background=P["card2"], foreground=P["fg"])
        st.configure("H1.TLabel", background=P["card"], foreground=P["fg"],
                     font=(F, 17, "bold"))
        st.configure("Sub.TLabel", background=P["card"], foreground=P["muted"], font=(F, 9))
        st.configure("Card.Title.TLabel", background=P["card"], foreground=P["accent"],
                     font=(F, 11, "bold"))
        st.configure("Card.Hint.TLabel", background=P["card"], foreground=P["muted"],
                     font=(F, 9))
        st.configure("Card.Mono.TLabel", background=P["card"], foreground=P["fg"],
                     font=("Consolas", 10))
        st.configure("Card.Big.TLabel", background=P["card"], foreground=P["fg"],
                     font=(F, 13, "bold"))
        st.configure("Card.Headline.TLabel", background=P["card"], foreground=P["fg"],
                     font=(F, 16, "bold"))
        st.configure("Muted.TLabel", background=P["bg"], foreground=P["muted"], font=(F, 9))
        st.configure("Rec.TLabel", background=P["card"], foreground="#E5484D",
                     font=(F, 10, "bold"))

        st.configure("TButton", background=P["btn"], foreground=P["fg"],
                     bordercolor=P["border"], focuscolor=P["btn"], padding=(self.px(12), self.px(6)),
                     relief="flat")
        st.map("TButton",
               background=[("active", P["btn_hover"]), ("disabled", P["disabled"])],
               foreground=[("disabled", P["muted"])])
        st.configure("Accent.TButton", background=P["accent"], foreground="#FFFFFF",
                     bordercolor=P["accent2"], padding=(self.px(16), self.px(8)), font=(F, 10, "bold"))
        st.map("Accent.TButton",
               background=[("active", P["accent2"]), ("disabled", P["disabled"])],
               foreground=[("disabled", P["muted"])])
        st.configure("Ghost.TButton", background=P["btn"], foreground=P["fg"],
                     bordercolor=P["border"], padding=(self.px(10), self.px(5)))
        st.map("Ghost.TButton",
               background=[("active", P["btn_hover"]), ("disabled", P["disabled"])],
               foreground=[("disabled", P["muted"])])

        st.configure("TEntry", fieldbackground=P["field"], foreground=P["fg"],
                     bordercolor=P["border"], insertcolor=P["fg"], padding=6)
        st.map("TEntry", bordercolor=[("focus", P["accent"])],
               fieldbackground=[("disabled", P["disabled"])],
               foreground=[("disabled", P["muted"])])
        st.configure("TCombobox", fieldbackground=P["field"], background=P["btn"],
                     foreground=P["fg"], arrowcolor=P["muted"], padding=5,
                     arrowsize=self.px(13))
        # "disabled" phải đứng trước "readonly": ô readonly bị tắt trước đây trông như đang bật (V-03)
        st.map("TCombobox",
               fieldbackground=[("disabled", P["disabled"]), ("readonly", P["field"])],
               foreground=[("disabled", P["muted"])],
               arrowcolor=[("disabled", P["border"])],
               bordercolor=[("focus", P["accent"])])
        st.configure("Toolbar.TCombobox", fieldbackground=P["card"], background=P["card"],
                     foreground=P["fg"], bordercolor=P["card"], lightcolor=P["card"],
                     darkcolor=P["card"], arrowcolor=P["muted"], arrowsize=self.px(13),
                     selectbackground=P["card"], selectforeground=P["fg"],
                     padding=(self.px(6), self.px(4)))
        st.map("Toolbar.TCombobox",
               fieldbackground=[("disabled", P["card"]), ("readonly", P["card"])],
               foreground=[("disabled", P["disabled_fg"])],
               arrowcolor=[("disabled", P["border"])],
               bordercolor=[("hover", P["border"]), ("focus", P["border"])],
               selectbackground=[("readonly", P["card"])],
               selectforeground=[("readonly", P["fg"])])
        self.option_add("*TCombobox*Listbox.font", (self.F, 10))
        self.option_add("*TCombobox*Listbox.background", P["field"])
        self.option_add("*TCombobox*Listbox.foreground", P["fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", P["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")

        # Radio/checkbox: chỉ báo vẽ bằng ảnh theo theme (V-01: radio tối bị ngược,
        # V-02: checkbox clam vẽ dấu "✕"). Ảnh được vẽ lại mỗi lần đổi theme.
        self._theme_indicators(P, st)
        for name, bg in (("TCheckbutton", P["bg"]), ("Card.TCheckbutton", P["card"]),
                         ("Card2.TCheckbutton", P["card2"]),
                         ("TRadiobutton", P["bg"]), ("Card.TRadiobutton", P["card"]),
                         ("Card2.TRadiobutton", P["card2"])):
            st.configure(name, background=bg, foreground=P["fg"], borderwidth=0,
                         relief="flat", padding=(0, self.px(2)))
            st.map(name, background=[("active", bg)], foreground=[("disabled", P["muted"])])

        # Tab: clam đặt padding riêng cho tab đang chọn nên chữ bị tụt xuống và tab
        # không chọn trông như nút nổi (V-04). Cùng padding, viền phẳng theo nền.
        tab_pad = (self.px(18), self.px(9))
        st.configure("TNotebook", background=P["bg"], borderwidth=0, tabmargins=(0, 4, 0, 0))
        st.configure("TNotebook.Tab", background=P["bg"], foreground=P["muted"],
                     padding=tab_pad, borderwidth=0, font=(F, 10),
                     bordercolor=P["bg"], lightcolor=P["bg"], darkcolor=P["bg"])
        st.map("TNotebook.Tab",
               background=[("selected", P["card"])],
               foreground=[("selected", P["accent2"] if self.theme_name.get() != "dark"
                            else P["accent"])],
               lightcolor=[("selected", P["accent"])],
               bordercolor=[("selected", P["border"])],
               darkcolor=[("selected", P["card"])],
               padding=[("selected", tab_pad)],
               expand=[("selected", (0, 0, 0, 0))])
        st.configure("TProgressbar", background=P["accent"], troughcolor=P["card2"],
                     bordercolor=P["card2"], lightcolor=P["accent"], darkcolor=P["accent"],
                     thickness=self.px(8))
        st.configure("Card.TNotebook", background=P["card"], borderwidth=0,
                     tabmargins=(0, self.px(3), 0, 0))
        ctab_pad = (self.px(14), self.px(7))
        st.configure("Card.TNotebook.Tab", background=P["card2"], foreground=P["muted"],
                     padding=ctab_pad, borderwidth=0, font=(F, 10),
                     bordercolor=P["card2"], lightcolor=P["card2"], darkcolor=P["card2"])
        st.map("Card.TNotebook.Tab",
               background=[("selected", P["card"])],
               foreground=[("selected", P["accent"])],
               lightcolor=[("selected", P["accent"])],
               bordercolor=[("selected", P["border"])],
               darkcolor=[("selected", P["card"])],
               padding=[("selected", ctab_pad)],
               expand=[("selected", (0, 0, 0, 0))])
        st.configure("TSeparator", background=P["border"])
        st.configure("TPanedwindow", background=P["bg"], sashwidth=self.px(8))
        # thanh cuộn mảnh theo theme cho mọi tk.Text (V-07)
        st.configure("Vertical.TScrollbar", background=P["border"], troughcolor=P["card"],
                     bordercolor=P["card"], lightcolor=P["border"], darkcolor=P["border"],
                     arrowcolor=P["muted"], gripcount=0, arrowsize=self.px(11))
        st.map("Vertical.TScrollbar", background=[("active", P["muted"])])
        st.configure("Card.Ipa.TLabel", background=P["card"], foreground=P["fg"],
                     font=(FONT_IPA, 12))
        st.configure("Card.HintIpa.TLabel", background=P["card"], foreground=P["muted"],
                     font=(FONT_IPA, 9))

        # tk.Text và tk.Frame thuần
        for w, role in list(self._texts):
            try:
                self._style_text(w, role)
            except tk.TclError:
                pass
        # widget tk thuần (thanh điều hướng, sân khấu, panel) + phần vẽ Canvas theo theme mới
        if hasattr(self, "_themed"):
            self._retheme_tk()
        if getattr(self, "_last_view", None):
            self._render_result(self._last_view)
        self.after(200, self._set_titlebar)
        self.bind("<Map>", lambda e: self.after(120, self._set_titlebar), add="+")

    def _set_titlebar(self):
        """Tô thanh tiêu đề Windows theo theme (DWM attribute 20/19)."""
        try:
            import ctypes
            try:
                fid = self.wm_frame()
                hwnd = int(fid, 16) if isinstance(fid, str) else int(fid)
            except Exception:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                return
            v = ctypes.c_int(1 if self.theme_name.get() == "dark" else 0)
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)
        except Exception:
            pass

    def _style_text(self, w, role):
        P = self.P
        bg = P["card"] if role == "out" else (P["log_bg"] if role == "log" else P["card"])
        w.configure(background=bg, foreground=P["fg"], insertbackground=P["fg"],
                    selectbackground=P["sel"], highlightbackground=P["border"],
                    highlightcolor=P["accent"],
                    highlightthickness=0 if role == "doc" else self.px(1), borderwidth=0,
                    relief="flat")
        w.tag_configure("time", foreground=P["muted"])
        w.tag_configure("ok", background=P["ok_bg"], foreground=P["ok_fg"])
        w.tag_configure("bad", background=P["bad_bg"], foreground=P["bad_fg"])
        w.tag_configure("warn", background=P["warn_bg"])
        w.tag_configure("note", foreground=P["muted"])
        w.tag_configure("err", foreground="#E5484D")
        w.tag_configure("big", font=(self.F, 12, "bold"))
        w.tag_configure("ipa", font=(FONT_IPA, 10))

    def _mk_text(self, parent, role="out", scroll=False, **kw):
        """tk.Text theo theme. scroll=True: đặt trong khung có thanh cuộn (V-07) —
        khi đó nơi gọi pack/grid `w.holder` thay vì chính `w`."""
        kw.setdefault("wrap", "word")
        kw.setdefault("width", 1)
        kw.setdefault("font", (self.F, 10))
        kw.setdefault("padx", 10)
        kw.setdefault("pady", 8)
        if scroll:
            holder = ttk.Frame(parent, style="CardInner.TFrame")
            w = tk.Text(holder, **kw)
            sb = ttk.Scrollbar(holder, orient="vertical", command=w.yview)
            w.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            w.pack(side="left", fill="both", expand=True)
            w.holder = holder
        else:
            w = tk.Text(parent, **kw)
            w.holder = w
        self._texts.append((w, role))
        self._style_text(w, role)
        return w

    def _theme_indicators(self, P, st):
        """Vẽ (lại) ảnh chỉ báo radio/checkbox theo theme; lần đầu tạo element + layout."""
        size = max(12, self.px(15))
        norm = {"box": P["muted"], "fill": P["field"], "accent": P["accent"],
                "mark": "#FFFFFF", "bg": P["card"]}
        dis = {"box": P["border"], "fill": P["disabled"], "accent": P["border"],
               "mark": P["muted"], "bg": P["card"]}
        specs = {
            "chk_off": ("check", False, norm), "chk_on": ("check", True, norm),
            "chk_doff": ("check", False, dis), "chk_don": ("check", True, dis),
            "rad_off": ("radio", False, norm), "rad_on": ("radio", True, norm),
            "rad_doff": ("radio", False, dis), "rad_don": ("radio", True, dis),
        }
        # khoảng cách tới chữ nằm luôn trong ảnh (cột trong suốt bên phải): element ảnh
        # của ttk bỏ qua -padding nên chỉ báo dính sát nhãn
        gap = self.px(7)
        first = not hasattr(self, "_ind")
        if first:
            self._ind = {k: tk.PhotoImage(master=self, width=size + gap, height=size)
                         for k in specs}
        for k, (kind, on, colors) in specs.items():
            rows = [r + [None] * gap for r in indicator_rows(kind, on, size, colors)]
            rows_to_photo(self._ind[k], rows)
        if not first:
            return
        I = self._ind
        for el, off, on, doff, don in (("Oriole.Check.indicator", "chk_off", "chk_on",
                                        "chk_doff", "chk_don"),
                                       ("Oriole.Radio.indicator", "rad_off", "rad_on",
                                        "rad_doff", "rad_don")):
            st.element_create(el, "image", I[off],
                              ("disabled", "selected", I[don]), ("disabled", I[doff]),
                              ("selected", I[on]), sticky="")
        for cls, el in (("Checkbutton", "Oriole.Check.indicator"),
                        ("Radiobutton", "Oriole.Radio.indicator")):
            st.layout("T" + cls, [(cls + ".padding", {"sticky": "nswe", "children": [
                (el, {"side": "left", "sticky": ""}),
                (cls + ".focus", {"side": "left", "sticky": "w", "children": [
                    (cls + ".label", {"sticky": "nswe"})]})]})])

    def _card(self, parent, title=None, expand=False, pady=None, style="Card.TFrame"):
        if pady is None:
            pady = (0, self.px(12))
        outer = ttk.Frame(parent, style=style, padding=(self.px(16), self.px(14)))
        outer.pack(fill="both" if expand else "x", expand=expand, pady=pady)
        if title:
            ttk.Label(outer, text=title, style="Card.Title.TLabel").pack(
                anchor="w", pady=(self.px(0), self.px(8)))
        return outer

    def _tw(self, w, **tokens):
        """Gán màu token (vd bg="side", fg="muted") cho widget tk thuần và nhớ để đổi theme."""
        self._themed.append((w, tokens))
        self._tw_apply(w, tokens)
        return w

    def _tw_apply(self, w, tokens):
        opts = {k: self.P[v] for k, v in tokens.items()}
        if "bg" in opts and isinstance(w, tk.Label):
            opts.setdefault("activebackground", opts["bg"])
        w.configure(**opts)

    def _retheme_tk(self):
        alive = []
        for w, tokens in self._themed:
            try:
                self._tw_apply(w, tokens)
                alive.append((w, tokens))
            except tk.TclError:
                pass          # widget đã hủy
        self._themed = alive
        for fn in list(self._redraws):
            try:
                fn()
            except tk.TclError:
                pass

    def _lbl(self, parent, text="", bg="card", fg="fg", size=10, weight="normal",
             font=None, **kw):
        lb = tk.Label(parent, text=text, font=font or (self.F, size, weight), bd=0,
                      padx=0, pady=0, **kw)
        return self._tw(lb, bg=bg, fg=fg)

    def _frame(self, parent, bg="card", **kw):
        return self._tw(tk.Frame(parent, bd=0, highlightthickness=0, **kw), bg=bg)

    def _hline(self, parent, side=None, **pack):
        """Đường kẻ mảnh 1 px (màu border)."""
        ln = self._frame(parent, bg="border", height=1, width=1)
        ln.pack(fill="x" if side in (None, "top", "bottom") else "y", side=side or "top", **pack)
        return ln

    def _link_lbl(self, parent, text, command, bg="card", size=10):
        lb = self._lbl(parent, text, bg=bg, fg="accent_fg", size=size, cursor="hand2")
        lb.bind("<Button-1>", lambda e: command())
        return lb

    def _draw_icon(self, c, name, color, s, bg=None, ox=0, oy=0, clear=True):
        """Biểu tượng nét mảnh vẽ bằng Canvas (không file ảnh): doc, mic, gear, moon, sun, stop."""
        if clear:
            c.delete("all")
        w = max(1, int(round(s / 11.0)))
        u = s / 24.0

        def P(*xy):
            return [v * u + (oy if i % 2 else ox) for i, v in enumerate(xy)]
        if name == "doc":
            c.create_line(*P(14, 3, 6, 3, 5, 4, 5, 20, 6, 21, 18, 21, 19, 20, 19, 8, 14, 3, 14, 8,
                             19, 8), fill=color, width=w, joinstyle="round")
            c.create_line(*P(9, 13, 15, 13), fill=color, width=w)
            c.create_line(*P(9, 17, 13, 17), fill=color, width=w)
        elif name == "mic":
            c.create_line(*P(12, 6, 12, 11), fill=color, width=6 * u, capstyle="round")
            c.create_arc(*P(5, 4, 19, 18), start=180, extent=180, style="arc", outline=color,
                         width=w)
            c.create_line(*P(12, 18, 12, 21), fill=color, width=w)
        elif name == "gear":
            c.create_oval(*P(9, 9, 15, 15), outline=color, width=w)
            for x0, y0, x1, y1 in ((12, 2, 12, 5), (12, 19, 12, 22), (2, 12, 5, 12),
                                   (19, 12, 22, 12), (4.9, 4.9, 7, 7), (17, 17, 19.1, 19.1),
                                   (4.9, 19.1, 7, 17), (17, 7, 19.1, 4.9)):
                c.create_line(*P(x0, y0, x1, y1), fill=color, width=w, capstyle="round")
        elif name == "moon":
            c.create_oval(*P(4, 4, 20, 20), fill=color, outline="")
            c.create_oval(*P(9, 1, 24, 16), fill=bg or "", outline="")
        elif name == "sun":
            c.create_oval(*P(8, 8, 16, 16), outline=color, width=w)
            for x0, y0, x1, y1 in ((12, 2, 12, 4.5), (12, 19.5, 12, 22), (2, 12, 4.5, 12),
                                   (19.5, 12, 22, 12), (5, 5, 6.7, 6.7), (17.3, 17.3, 19, 19),
                                   (5, 19, 6.7, 17.3), (17.3, 6.7, 19, 5)):
                c.create_line(*P(x0, y0, x1, y1), fill=color, width=w, capstyle="round")
        elif name == "stop":
            c.create_rectangle(*P(6, 6, 18, 18), fill=color, outline="")

    def _tooltip(self, w, text_fn, when=lambda: True):
        """Chú thích khi rê chuột (tên mic đầy đủ, tên mục ở thanh điều hướng gọn)."""
        tip = {"win": None, "job": None}

        def show():
            tip["job"] = None
            text = text_fn()
            if not text or not when() or tip["win"] is not None:
                return
            tw = tk.Toplevel(self)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)
            tk.Label(tw, text=text, font=(self.F, 9), bg=self.P["fg"], fg=self.P["card"],
                     padx=self.px(8), pady=self.px(4), wraplength=self.px(420),
                     justify="left").pack()
            tw.wm_geometry("+%d+%d" % (w.winfo_rootx() + self.px(12),
                                       w.winfo_rooty() + w.winfo_height() + self.px(4)))
            tip["win"] = tw

        def hide(_e=None):
            if tip["job"]:
                self.after_cancel(tip["job"])
                tip["job"] = None
            if tip["win"] is not None:
                tip["win"].destroy()
                tip["win"] = None

        w.bind("<Enter>", lambda e: tip.update(job=self.after(450, show)), add="+")
        w.bind("<Leave>", hide, add="+")
        w.bind("<ButtonPress>", hide, add="+")

    # ---------- khung app: thanh điều hướng + màn hình (D-28, B4a) ----------
    def _build_ui(self):
        self._themed, self._redraws = [], []
        self.screen = None
        self._compact = None
        root = self._frame(self, bg="bg")
        root.pack(fill="both", expand=True)
        self._root_frame = root
        self.rail = self._frame(root, bg="bg")
        self.rail.configure(width=self.px(232))
        self.rail.pack(side="left", fill="y")
        self.rail.pack_propagate(False)
        self._tw(tk.Frame(root, width=1, bd=0, highlightthickness=0), bg="border").pack(
            side="left", fill="y")
        self.content = self._frame(root, bg="card")
        self.content.pack(side="left", fill="both", expand=True)

        self.screens = {}
        for key in ("stt", "prac", "set"):
            self.screens[key] = self._frame(self.content, bg="card")
        # tên cũ (tab_*) giữ cho công cụ/hàm khác: mỗi "tab" giờ là một màn hình
        self.tab_stt, self.tab_prac, self.tab_set = (self.screens[k] for k in ("stt", "prac", "set"))
        self._build_rail()
        self._build_text_screen(self.tab_stt)
        self._build_practice_tab(self.tab_prac)
        self._build_settings_screen(self.tab_set)
        self._show_screen("stt")
        root.bind("<Configure>", self._on_root_resize)

    def _build_rail(self):
        r = self.rail
        top = self._frame(r, bg="bg")
        top.pack(fill="x", pady=(self.px(18), self.px(14)))
        n = max(16, self.px(30))
        self._rail_logo_img = rows_to_photo(tk.PhotoImage(master=self, width=n, height=n),
                                            logo_rows(n))
        self._rail_logo = self._tw(tk.Label(top, image=self._rail_logo_img, bd=0), bg="bg")
        self._rail_logo.pack(side="left", padx=(self.px(22), self.px(10)))
        self._rail_title = self._lbl(top, "Oriole", bg="bg", size=16, weight="bold")
        self._rail_title.pack(side="left")
        self.nav = {}
        for key, icon, text in (("stt", "doc", "Chuyển thành văn bản"),
                                ("prac", "mic", "Luyện phát âm")):
            self.nav[key] = self._rail_item(r, key, icon, text, lambda k=key: self._show_screen(k))
        # chân thanh: model/ngôn ngữ (một chỗ duy nhất trên màn hình chính), theme, cài đặt
        foot = self._frame(r, bg="bg")
        foot.pack(side="bottom", fill="x", pady=(0, self.px(14)))
        self.nav["set"] = self._rail_item(foot, "set", "gear", "Cài đặt",
                                          lambda: self._show_screen("set"), side="bottom")
        self.nav["theme"] = self._rail_item(foot, "theme", "moon", "", self._flip_theme,
                                            side="bottom")
        self._rail_model = self._frame(foot, bg="bg", cursor="hand2")
        self._rail_model.pack(side="bottom", fill="x", padx=(self.px(12), self.px(12)),
                              pady=(0, self.px(4)))
        self._rail_model_a = self._lbl(self._rail_model, "Nhận dạng giọng nói", bg="bg",
                                       fg="muted", size=9)
        self._rail_model_a.pack(anchor="w", padx=(self.px(12), 0), pady=(self.px(6), 0))
        self._rail_model_b = self._lbl(self._rail_model, "", bg="bg", size=10)
        self._rail_model_b.pack(anchor="w", padx=(self.px(12), 0), pady=(0, self.px(6)))
        for w in (self._rail_model, self._rail_model_a, self._rail_model_b):
            w.bind("<Button-1>", self._model_menu)
        self.model_name.trace_add("write", lambda *_: self._update_rail_model())
        self.lang.trace_add("write", lambda *_: self._update_rail_model())
        self._update_rail_model()
        self._redraws.append(self._draw_rail)

    def _rail_item(self, parent, key, icon, text, command, side="top"):
        f = self._frame(parent, bg="bg", cursor="hand2")
        f.pack(side=side, fill="x", padx=(self.px(12), self.px(12)), pady=(self.px(2), 0))
        bar = tk.Frame(f, width=self.px(3), bd=0, highlightthickness=0)
        bar.pack(side="left", fill="y")
        s = self.px(18)
        cv = tk.Canvas(f, width=s, height=s, bd=0, highlightthickness=0)
        cv.pack(side="left", padx=(self.px(12), self.px(12)), pady=(self.px(10), self.px(10)))
        lb = tk.Label(f, text=text, font=(self.F, 10), bd=0, anchor="w")
        lb.pack(side="left", fill="x", expand=True)
        item = {"frame": f, "bar": bar, "icon": cv, "label": lb, "name": icon}
        for w in (f, bar, cv, lb):
            w.bind("<Button-1>", lambda e: command())
        self._tooltip(f, lambda: lb.cget("text"), when=lambda: bool(self._compact))
        return item

    def _draw_rail(self):
        P = self.P
        dark = self.theme_name.get() == "dark"
        self.nav["theme"]["name"] = "sun" if dark else "moon"
        self.nav["theme"]["label"].configure(
            text="Giao diện sáng" if dark else "Giao diện tối")
        compact = bool(self._compact)
        for key, it in self.nav.items():
            sel = key == self.screen
            bg = P["nav_sel"] if sel else P["bg"]
            for w in (it["frame"], it["icon"], it["label"]):
                w.configure(bg=bg)
            it["bar"].configure(bg=P["accent"] if sel else bg)
            it["label"].configure(fg=P["fg"], font=(self.F, 10, "bold" if sel else "normal"))
            self._draw_icon(it["icon"], it["name"], P["fg"], self.px(18), bg=bg)
            if compact and it["label"].winfo_manager():
                it["label"].pack_forget()
            elif not compact and not it["label"].winfo_manager():
                it["label"].pack(side="left", fill="x", expand=True)

    def _update_rail_model(self):
        self._rail_model_b.configure(
            text="Model %s · %s ▾" % (self.model_name.get(),
                                      LANG_NAME.get(self.lang.get(), "Tự động")))

    def _model_menu(self, _e=None):
        """Model + ngôn ngữ nhận dạng: menu bật từ chân thanh điều hướng (Q-04/D-28)."""
        m = tk.Menu(self, tearoff=0, font=(self.F, 10))
        m.add_command(label="Model nhận dạng", state="disabled")
        for name in MODELS:
            m.add_radiobutton(label="%s — %s" % (name, MODEL_DESC[name]), value=name,
                              variable=self.model_name, command=self._save_cfg)
        m.add_separator()
        m.add_command(label="Ngôn ngữ", state="disabled")
        for name in LANG_NAMES:
            m.add_radiobutton(label=name, value=name, variable=self.lang_label,
                              command=self._save_cfg)
        w = self._rail_model
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() - self.px(8) - m.winfo_reqheight())

    def _show_screen(self, key):
        if key == self.screen:
            return
        for k, fr in self.screens.items():
            if k != key and fr.winfo_manager():
                fr.pack_forget()
        self.screens[key].pack(fill="both", expand=True)
        self.screen = key
        self._draw_rail()
        if key == "set":
            self._on_tab_changed()

    def _on_root_resize(self, e):
        if e.widget is not self._root_frame:
            return
        compact = nav_compact(e.width, self.S)
        if compact == self._compact:
            return
        self._compact = compact
        self.rail.configure(width=self.px(60 if compact else 232))
        for w in (self._rail_title, self._rail_model):
            if compact and w.winfo_manager():
                w.pack_forget()
        if not compact:
            if not self._rail_title.winfo_manager():
                self._rail_title.pack(side="left")
            if not self._rail_model.winfo_manager():
                self._rail_model.pack(side="bottom", fill="x", padx=(self.px(12), self.px(12)),
                                      pady=(0, self.px(4)), after=self.nav["theme"]["frame"])
        self._rail_logo.pack_configure(padx=(self.px(15 if compact else 22),
                                             self.px(0 if compact else 10)))
        pad = self.px(4 if compact else 12)
        for it in self.nav.values():
            it["frame"].pack_configure(padx=(pad, pad))
        self._draw_rail()
        self._prac_compact(compact)

    def _toolbar(self, parent, title=None):
        """Thanh công cụ 60 px đầu mỗi màn hình (tiêu đề trái, nút phải) + đường kẻ dưới."""
        bar = self._frame(parent, bg="card", height=self.px(60))
        bar.pack(fill="x")
        bar.pack_propagate(False)
        if title:
            self._lbl(bar, title, size=12, weight="bold").pack(side="left", padx=(self.px(28), 0))
        self._hline(parent)
        return bar

    def _status_bar(self, parent):
        bar = self._frame(parent, bg="card")
        bar.pack(side="bottom", fill="x")
        self._hline(bar)
        lb = tk.Label(bar, textvariable=self.status, font=(self.F, 9), bd=0, anchor="w")
        self._tw(lb, bg="card", fg="muted").pack(fill="x", padx=self.px(28), pady=self.px(6))
        return bar

    # ---------- thành phần dùng chung: nút ghép, công tắc ----------
    def _mk_seg(self, parent, items, var, command, locked=lambda: False):
        """Nút ghép (segmented control) gắn StringVar; khóa được khi đang bận."""
        box = self._frame(parent, bg="card2")
        labels = {}

        def click(code):
            if locked() or code == var.get():
                return
            var.set(code)
            command()

        for code, text in items:
            lb = tk.Label(box, text=text, font=(self.F, 10), bd=0, cursor="hand2",
                          padx=self.px(12), pady=self.px(4), highlightthickness=1)
            lb.pack(side="left", padx=self.px(3), pady=self.px(3))
            lb.bind("<Button-1>", lambda e, c=code: click(c))
            labels[code] = lb

        def draw():
            P, cur, lk = self.P, var.get(), locked()
            for code, lb in labels.items():
                sel = code == cur
                lb.configure(bg=P["card"] if sel else P["card2"],
                             fg=P["fg"] if sel else (P["disabled_fg"] if lk else P["muted"]),
                             font=(self.F, 10, "bold" if sel else "normal"),
                             highlightbackground=P["border"] if sel else P["card2"],
                             highlightcolor=P["border"] if sel else P["card2"],
                             cursor="" if lk else "hand2")
            box.configure(bg=P["card2"])

        box._draw = draw
        var.trace_add("write", lambda *_: draw())
        self._redraws.append(draw)
        draw()
        return box

    def _mk_switch(self, parent, var, command=None, bg="card"):
        """Công tắc bật/tắt (Canvas) gắn BooleanVar — thay checkbox ở màn mới (D-28)."""
        w, h = self.px(34), self.px(18)
        cv = self._tw(tk.Canvas(parent, width=w, height=h, bd=0, highlightthickness=0,
                                cursor="hand2"), bg=bg)
        cv._enabled = True

        def draw():
            P, on = self.P, bool(var.get())
            cv.delete("all")
            fill = (P["accent"] if cv._enabled else P["disabled_fg"]) if on else P["track"]
            self._round_rect(cv, 1, 1, w - 1, h - 1, h // 2, fill=fill,
                             outline=fill if on else P["border"])
            r = h // 2 - self.px(3)
            cx = w - h // 2 if on else h // 2
            cv.create_oval(cx - r, h / 2.0 - r, cx + r, h / 2.0 + r,
                           fill="#FFFFFF" if (on or cv._enabled) else P["card2"],
                           outline="" if on else P["border"])
            cv.configure(cursor="hand2" if cv._enabled else "")

        def click(_e):
            if cv._enabled:
                var.set(not bool(var.get()))
                if command:
                    command()

        cv.bind("<Button-1>", click)
        var.trace_add("write", lambda *_: draw())
        cv._draw = draw
        self._redraws.append(draw)
        draw()
        return cv

    def _switch_state(self, sw, enabled):
        sw._enabled = bool(enabled)
        sw._draw()

    def _link_state(self, lb, enabled):
        """Link chữ: bật = màu accent + bấm được; tắt = chữ mờ, không con trỏ tay."""
        lb._enabled = bool(enabled)
        lb.configure(fg=self.P["accent_fg"] if enabled else self.P["disabled_fg"],
                     cursor="hand2" if enabled else "")

    # ================= màn Chuyển thành văn bản (S-8, B5) =================
    def _build_text_screen(self, parent):
        bar = self._toolbar(parent, "Chuyển thành văn bản")
        self._stt_seg = self._mk_seg(bar, (("file", "File máy tính"), ("yt", "Link YouTube"),
                                           ("rec", "Ghi âm")), self.src, self._src_changed,
                                     locked=lambda: self.busy or self.recording)
        self._stt_seg.pack(side="left", padx=(self.px(20), 0))

        # thanh nguồn: ô nhập theo nguồn (trái) + nút chạy/hủy (phải) + tiến trình
        src = self._frame(parent, bg="card")
        src.pack(fill="x")
        inner = self._frame(src, bg="card")
        inner.pack(fill="x", padx=self.px(28), pady=self.px(14))
        self._hline(parent)
        top = self._frame(inner, bg="card")
        top.pack(fill="x")
        acts = self._frame(top, bg="card")
        acts.pack(side="right", anchor="n")
        self.btn_run = ttk.Button(acts, text="▶  Bắt đầu", style="Accent.TButton",
                                  command=self._primary)
        self.btn_run.pack(side="right", padx=(self.px(10), 0))
        self.btn_cancel = ttk.Button(acts, text="Hủy (Esc)", style="Ghost.TButton",
                                     command=self._cancel)
        self.src_box = self._frame(top, bg="card")
        self.src_box.pack(side="left", fill="x", expand=True)
        self._build_src_file(self.src_box)
        self._build_src_yt(self.src_box)
        self._build_src_rec(self.src_box)
        # tiến trình: chỉ hiện khi đang xử lý (V-11, D-31)
        self.stt_prog = self._frame(inner, bg="card")
        self.pbar = ttk.Progressbar(self.stt_prog, mode="determinate", maximum=100)
        self.pbar.pack(fill="x", pady=(self.px(12), self.px(4)))
        self._tw(tk.Label(self.stt_prog, textvariable=self.status, font=(self.F, 9), bd=0,
                          anchor="w"), bg="card", fg="muted").pack(fill="x")

        body = self._frame(parent, bg="card")
        body.pack(fill="both", expand=True)
        side = self._frame(body, bg="side", width=self.px(320))
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        self._tw(tk.Frame(body, width=1, bd=0, highlightthickness=0), bg="border").pack(
            side="right", fill="y")
        doc = self._frame(body, bg="card")
        doc.pack(side="left", fill="both", expand=True)
        self._build_stt_doc(doc)
        self._build_stt_side(side)

    def _build_src_file(self, box):
        f = self._frame(box, bg="card")
        row = self._frame(f, bg="card")
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.file_path, font=(self.F, 11)).pack(
            side="left", fill="x", expand=True)
        ttk.Button(row, text="Chọn file…", style="Ghost.TButton",
                   command=self._pick_file).pack(side="left", padx=(self.px(10), 0))
        self._lbl(f, "mp3 · wav · m4a · flac · ogg · mp4 · mov · mkv · webm — hoặc dán đường "
                     "dẫn vào ô trên", fg="muted", size=9, anchor="w").pack(
            fill="x", pady=(self.px(6), 0))
        self.f_src_file = f

    def _build_src_yt(self, box):
        f = self._frame(box, bg="card")
        row = self._frame(f, bg="card")
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.yt_url, font=(self.F, 11)).pack(
            side="left", fill="x", expand=True)
        ttk.Button(row, text="Dán", style="Ghost.TButton",
                   command=self._paste_url).pack(side="left", padx=(self.px(10), 0))
        g = self._frame(f, bg="card")
        g.pack(fill="x", pady=(self.px(10), 0))
        self._lbl(g, "Lấy", fg="muted", size=9).pack(side="left")
        ttk.Combobox(g, textvariable=self.yt_kind, values=YT_KIND_NAMES, width=24,
                     state="readonly").pack(side="left", padx=(self.px(6), self.px(16)))
        self._lbl(g, "Chất lượng", fg="muted", size=9).pack(side="left")
        self.cb_quality = ttk.Combobox(g, textvariable=self.yt_quality,
                                       values=[n for _, n in YT_QUALITIES], width=13,
                                       state="readonly")
        self.cb_quality.pack(side="left", padx=(self.px(6), 0))
        s = self._frame(f, bg="card")
        s.pack(fill="x", pady=(self.px(8), 0))
        self._mk_switch(s, self.y_subs, self._yt_subs_changed).pack(side="left")
        self._lbl(s, "Kèm phụ đề", size=9).pack(side="left", padx=(self.px(6), self.px(10)))
        self.cb_sublang = ttk.Combobox(s, textvariable=self.yt_sub_lang,
                                       values=YT_SUB_LANG_NAMES, width=24, state="readonly")
        self.cb_sublang.pack(side="left", padx=(0, self.px(16)))
        self.cb_embed = self._mk_switch(s, self.y_embed)
        self.cb_embed.pack(side="left")
        self._lbl(s, "Nhúng phụ đề vào video", size=9).pack(side="left", padx=(self.px(6), 0))
        d = self._frame(f, bg="card")
        d.pack(fill="x", pady=(self.px(8), 0))
        self._lbl(d, "Lưu vào", fg="muted", size=9).pack(side="left")
        tk.Label(d, textvariable=self.out_dir, font=(self.F, 9), bd=0).pack(
            side="left", padx=(self.px(6), self.px(6)))
        self._tw(d.winfo_children()[-1], bg="card", fg="muted")
        self._link_lbl(d, "Đổi", self._pick_out_dir, size=9).pack(side="left")
        self.f_src_yt = f

    def _build_src_rec(self, box):
        f = self._frame(box, bg="card")
        self._lbl(f, "Bấm “Bắt đầu thu âm” rồi nói, tối đa 15 phút; xong thì bấm "
                     "“Dừng & chuyển thành văn bản”.", size=10, anchor="w",
                  justify="left").pack(fill="x")
        mic = self._frame(f, bg="card")
        mic.pack(fill="x", pady=(self.px(6), 0))
        self.stt_mic_lbl = self._lbl(mic, "", fg="muted", size=9)
        self.stt_mic_lbl.pack(side="left")
        self._link_lbl(mic, "Đổi", lambda: self._show_screen("set"), size=9).pack(
            side="left", padx=(self.px(6), 0))
        # T-04: thanh mức âm vẽ bằng Canvas thay chuỗi "[####····]"
        self.stt_meter_row = self._frame(f, bg="card")
        self.stt_meter = self._tw(tk.Canvas(self.stt_meter_row, width=self.px(260),
                                            height=self.px(10), bd=0, highlightthickness=0),
                                  bg="card")
        self.stt_meter.pack(side="left")
        self.lbl_rec_level = self._lbl(self.stt_meter_row, "", fg="rec", size=9, weight="bold")
        self.lbl_rec_level.pack(side="left", padx=(self.px(12), 0))
        self.mic_var.trace_add("write", lambda *_: self.stt_mic_lbl.configure(
            text="Micro: %s  ·" % short_mic_name(self.mic_var.get())))
        self.f_src_rec = f

    # ----- vùng chữ: trống / đang thu / đang xử lý / kết quả -----
    def _build_stt_doc(self, doc):
        pad = (self.px(28), self.px(20))
        self.sd_empty = self._frame(doc, bg="card")
        mid = self._frame(self.sd_empty, bg="card")
        mid.place(relx=0.5, rely=0.45, anchor="center")
        self.sd_icon = self._tw(tk.Canvas(mid, width=self.px(56), height=self.px(56), bd=0,
                                          highlightthickness=0), bg="card")
        self.sd_icon.pack()
        self.sd_title = self._lbl(mid, "", size=17, weight="bold")
        self.sd_title.pack(pady=(self.px(12), self.px(6)))
        self.sd_body = self._lbl(mid, "", fg="muted", size=10, justify="center",
                                 wraplength=self.px(520))
        self.sd_body.pack()
        self._redraws.append(self._draw_sd_icon)

        self.sd_proc = self._frame(doc, bg="card")
        self._lbl(self.sd_proc, "Văn bản sẽ hiện ở đây khi nhận dạng xong.", fg="muted",
                  size=10, anchor="w").pack(fill="x", padx=pad[0], pady=(pad[1], self.px(8)))
        for frac in (0.92, 0.84, 0.88, 0.60, 0.90, 0.72):
            holder = self._frame(self.sd_proc, bg="card", height=self.px(12))
            holder.pack(fill="x", padx=pad[0], pady=(self.px(8), 0))
            self._frame(holder, bg="card2").place(x=0, y=0, relwidth=frac * 0.7,
                                                  relheight=1.0)

        self.sd_res = self._frame(doc, bg="card")
        head = self._frame(self.sd_res, bg="card")
        head.pack(fill="x", padx=pad[0], pady=(self.px(16), self.px(10)))
        self.res_view = tk.StringVar(value="text")
        self._mk_seg(head, (("text", "Văn bản"), ("srt", "Phụ đề SRT")), self.res_view,
                     self._stt_res_view).pack(side="left")
        self.sd_time = self._frame(head, bg="card")
        self._lbl(self.sd_time, "Kèm mốc thời gian", size=9).pack(side="right")
        self._mk_switch(self.sd_time, self.show_time, self._render_preview).pack(
            side="right", padx=(0, self.px(8)))
        self.sd_time.pack(side="right")
        self.txt_out = self._mk_text(self.sd_res, role="doc", scroll=True,
                                     font=(self.F, 12), padx=self.px(4), pady=self.px(4),
                                     spacing1=self.px(3), spacing2=self.px(3),
                                     spacing3=self.px(5))
        self.txt_out.bind("<Configure>", self._doc_margin, add="+")
        self.txt_srt = self._mk_text(self.sd_res, role="doc", scroll=True,
                                     font=("Consolas", 10), state="disabled")
        self._stt_res_view()

    def _doc_margin(self, e):
        # S-8 / T-03: dòng chữ ≤ ~720 px (≈ 90 ký tự) cho dễ đọc
        self.txt_out.tag_configure("doc", rmargin=max(0, e.width - self.px(760)))

    def _stt_res_view(self):
        srt = self.res_view.get() == "srt"
        for w, on in ((self.txt_out.holder, not srt), (self.txt_srt.holder, srt)):
            if on and not w.winfo_manager():
                w.pack(fill="both", expand=True, padx=(self.px(24), self.px(8)),
                       pady=(0, self.px(12)))
            elif not on and w.winfo_manager():
                w.pack_forget()
        if srt and self.sd_time.winfo_manager():
            self.sd_time.pack_forget()
        elif not srt and not self.sd_time.winfo_manager():
            self.sd_time.pack(side="right")

    def _draw_sd_icon(self):
        c, P = self.sd_icon, self.P
        c.configure(bg=P["card"])
        rec = getattr(self, "_sd_mode", "empty") == "recording"
        self._draw_icon(c, "mic" if rec else "doc", P["rec"] if rec else P["muted"],
                        self.px(56), bg=P["card"])

    # ----- panel phải: mẹo / đang xử lý / kết quả + xuất file / lỗi; nhật ký thu gọn -----
    def _build_stt_side(self, side):
        pad = self.px(22)
        # đáy: nhật ký thu gọn (T-02) — bấm để mở
        self.log_box = self._frame(side, bg="side", height=self.px(240))
        self.log_box.pack_propagate(False)
        self.log_txt = self._mk_text(self.log_box, role="log", scroll=True, state="disabled",
                                     font=(self.F, 9))
        self.log_txt.holder.pack(fill="both", expand=True)
        logbar = self._frame(side, bg="card2", cursor="hand2")
        logbar.pack(side="bottom", fill="x", padx=pad, pady=(self.px(6), pad))
        self.log_toggle = self._lbl(logbar, "Nhật ký ▸", bg="card2", fg="accent_fg", size=9,
                                    cursor="hand2")
        self.log_toggle.pack(side="left", padx=(self.px(10), self.px(8)), pady=self.px(6))
        self.log_last = self._lbl(logbar, "", bg="card2", size=9, anchor="w", cursor="hand2")
        self.log_last.pack(side="left", fill="x", expand=True, padx=(0, self.px(8)))
        for w in (logbar, self.log_toggle, self.log_last):
            w.bind("<Button-1>", lambda e: self._toggle_log())
        self._log_logbar = logbar
        self._log_open = False
        self.stt_status = self._wrap_stt(self._lbl(side, "", bg="side", fg="muted", size=9,
                                                   justify="left", anchor="w"))
        self.stt_status.configure(textvariable=self.status)
        self.stt_status.pack(side="bottom", fill="x", padx=pad)

        body = self._frame(side, bg="side")
        body.pack(fill="both", expand=True, padx=pad, pady=(pad, 0))
        self._stt_body = body
        # mẹo khi chưa có kết quả
        self.ss_empty = self._frame(body, bg="side")
        self._caps(self.ss_empty, "MẸO").pack(fill="x", pady=(0, self.px(8)))
        self.ss_tips = self._frame(self.ss_empty, bg="side")
        self.ss_tips.pack(fill="x")
        self._lbl(self.ss_empty, "Ctrl+O chọn file · Ctrl+Enter bắt đầu · Esc hủy", bg="side",
                  fg="muted", size=9, anchor="w").pack(fill="x", pady=(self.px(14), 0))
        # đang xử lý / đang thu / lỗi
        self.ss_busy = self._frame(body, bg="side")
        self.ss_busy_t = self._lbl(self.ss_busy, "", bg="side", size=15, weight="bold",
                                   anchor="w")
        self.ss_busy_t.pack(fill="x")
        self.ss_busy_s = self._wrap_stt(self._lbl(self.ss_busy, "", bg="side", fg="muted",
                                                  size=10, justify="left", anchor="w"))
        self.ss_busy_s.pack(fill="x", pady=(self.px(6), 0))
        # kết quả: thống kê + xuất file
        self.ss_res = self._frame(body, bg="side")
        self._lbl(self.ss_res, "Xong", bg="side", size=15, weight="bold", anchor="w").pack(
            fill="x")
        self.ss_note = self._wrap_stt(self._lbl(self.ss_res, "", bg="side", fg="muted", size=9,
                                                justify="left", anchor="w"))
        self.ss_note.pack(fill="x", pady=(self.px(2), self.px(12)))
        grid = self._frame(self.ss_res, bg="side")
        grid.pack(fill="x")
        self.st_vals = {}
        for i, (key, cap) in enumerate((("lines", "dòng"), ("words", "từ"),
                                        ("dur", "thời lượng"))):
            cell = self._frame(grid, bg="side")
            cell.grid(row=0, column=i, sticky="w")
            grid.grid_columnconfigure(i, weight=1)
            self.st_vals[key] = self._lbl(cell, "", bg="side", size=15, weight="bold",
                                          anchor="w")
            self.st_vals[key].pack(anchor="w")
            self._lbl(cell, cap, bg="side", fg="muted", size=9, anchor="w").pack(anchor="w")
        self.btn_copy = ttk.Button(self.ss_res, text="Sao chép văn bản", style="Accent.TButton",
                                   command=self._copy)
        self.btn_copy.pack(fill="x", pady=(self.px(16), self.px(8)))
        two = self._frame(self.ss_res, bg="side")
        two.pack(fill="x")
        two.grid_columnconfigure(0, weight=1, uniform="x")
        two.grid_columnconfigure(1, weight=1, uniform="x")
        self.btn_txt = ttk.Button(two, text="Lưu .txt", style="Ghost.TButton",
                                  command=self._save_txt)
        self.btn_txt.grid(row=0, column=0, sticky="ew", padx=(0, self.px(4)))
        self.btn_srt = ttk.Button(two, text="Lưu .srt", style="Ghost.TButton",
                                  command=self._save_srt)
        self.btn_srt.grid(row=0, column=1, sticky="ew", padx=(self.px(4), 0))
        links = self._frame(self.ss_res, bg="side")
        links.pack(fill="x", pady=(self.px(10), 0))
        self.btn_folder = self._link_lbl(links, "Mở thư mục",
                                         lambda: self.btn_folder._enabled and self._open_folder(),
                                         bg="side", size=10)
        self.btn_folder.pack(side="left")
        self.btn_open = self._link_lbl(links, "Mở file gốc",
                                       lambda: self.btn_open._enabled and self._open_file(),
                                       bg="side", size=10)
        self.btn_open.pack(side="left", padx=(self.px(16), 0))
        self._link_state(self.btn_folder, False)
        self._link_state(self.btn_open, False)
        body.bind("<Configure>", lambda e: self._stt_wrap_all(e.width))

    def _wrap_stt(self, lb):
        self._stt_side_wraps = getattr(self, "_stt_side_wraps", [])
        self._stt_side_wraps.append(lb)
        return lb

    def _stt_wrap_all(self, width):
        if width <= 1:
            return
        alive = []
        for lb in getattr(self, "_stt_side_wraps", []):
            try:
                lb.configure(wraplength=max(self.px(80), width))
                alive.append(lb)
            except tk.TclError:
                pass          # nhãn mẹo đã hủy khi đổi trạng thái
        self._stt_side_wraps = alive

    def _toggle_log(self):
        self._log_open = not self._log_open
        self.log_toggle.configure(text="Nhật ký ▾" if self._log_open else "Nhật ký ▸")
        if self._log_open:
            self.log_box.pack(side="bottom", fill="x", padx=self.px(22),
                              before=self._log_logbar)
            self.log_txt.see("end")
        else:
            self.log_box.pack_forget()

    def _stt_view(self):
        """Vẽ màn Văn bản theo trạng thái (D-31) + có kết quả hay chưa (S-8)."""
        has = bool(self.last_cues or (self.last_payload or {}).get("text"))
        doc, side = stt_view(getattr(self, "stt_state", "idle"), has)
        self._sd_mode = doc
        yt = self.src.get() == "yt"
        for name, w in (("empty", self.sd_empty), ("recording", self.sd_empty),
                        ("processing", self.sd_proc), ("result", self.sd_res)):
            if name != doc and w.winfo_manager() and not (w is self.sd_empty and
                                                           doc in ("empty", "recording")):
                w.pack_forget()
        target = {"empty": self.sd_empty, "recording": self.sd_empty,
                  "processing": self.sd_proc, "result": self.sd_res}[doc]
        if not target.winfo_manager():
            target.pack(fill="both", expand=True)
        if doc == "recording":
            self.sd_title.configure(text="Đang thu âm…")
            self.sd_body.configure(text="Nói tự nhiên, rõ ràng. Bấm “Dừng & chuyển thành văn "
                                        "bản” khi xong — tối đa 15 phút.")
        elif yt:
            self.sd_title.configure(text="Tải video, audio hoặc chỉ lấy phụ đề")
            self.sd_body.configure(text="Dán link ở trên rồi bấm nút tải. Oriole dùng phụ đề có "
                                        "sẵn của video; nếu không có, sẽ tự tạo bằng Whisper "
                                        "ngay trên máy bạn.")
        else:
            self.sd_title.configure(text="Biến âm thanh thành chữ và phụ đề")
            self.sd_body.configure(text="Chọn một file ở trên, dán link YouTube hoặc ghi âm trực "
                                        "tiếp. Mọi thứ chạy ngay trên máy bạn, không cần mạng.")
        self._draw_sd_icon()
        for w in (self.ss_empty, self.ss_busy, self.ss_res):
            if w.winfo_manager():
                w.pack_forget()
        if side == "empty":
            for ch in self.ss_tips.winfo_children():
                ch.destroy()
            tips = (("Chọn “Chỉ transcript” nếu chỉ cần chữ — không tải video.",
                     "Phụ đề dịch máy của YouTube sẽ được ghi rõ trong Nhật ký.",
                     "Model “small” cho tiếng Việt chính xác hơn “base”.") if yt else
                    ("Tiếng Việt: chọn Model “small” ở góc dưới bên trái.",
                     "File dài 1 giờ mất vài phút với model small.",
                     "Ghi âm tối đa 15 phút; bấm Dừng khi nói xong."))
            for t in tips:
                self._wrap_stt(self._lbl(self.ss_tips, t, bg="side", size=10, justify="left",
                                         anchor="w")).pack(fill="x", pady=(0, self.px(8)))
            self.ss_empty.pack(fill="x")
        elif side == "result":
            self.ss_res.pack(fill="x")
        else:
            t, s = {"processing": ("Đang xử lý…", "Có thể bấm Hủy (Esc) bất cứ lúc nào. "
                                   "Tiến trình hiện ngay dưới ô nguồn."),
                    "recording": ("Đang thu âm…", "Thời gian và mức âm hiện dưới ô nguồn."),
                    "error": ("Chưa xong — có lỗi", "Xem chi tiết trong Nhật ký bên dưới, sửa "
                              "rồi thử lại.")}[side]
            self.ss_busy_t.configure(text=t)
            self.ss_busy_s.configure(text=s)
            self.ss_busy.pack(fill="x")
        self._stt_wrap_all(self._stt_body.winfo_width())

    # ----- đổi nguồn / tham số -----
    def _src_changed(self):
        src = self.src.get()
        for w in (getattr(self, "f_src_file", None), getattr(self, "f_src_yt", None),
                  getattr(self, "f_src_rec", None)):
            if w is not None:
                w.pack_forget()
        target = {"file": self.f_src_file, "yt": self.f_src_yt, "rec": self.f_src_rec}[src]
        target.pack(fill="x")
        self._update_primary()
        if hasattr(self, "sd_empty"):
            self._stt_view()

    def _src_label(self):
        """Nhãn nút chính khi rảnh, theo nguồn đang chọn."""
        if self.src.get() == "rec":
            return "●  Bắt đầu thu âm"
        if self.src.get() == "yt":
            kind = YT_KIND_BY_NAME.get(self.yt_kind.get(), "video")
            return {"video": "Tải video", "audio": "Tải audio"}.get(
                kind, "▶  Lấy transcript")
        return "▶  Bắt đầu"

    def _update_primary(self):
        self.btn_run.configure(
            text=stt_controls(getattr(self, "stt_state", "idle"), self._src_label())["run_text"])

    def _yt_subs_changed(self):
        on = bool(self.y_subs.get())
        kind = YT_KIND_BY_NAME.get(self.yt_kind.get(), "video")
        if hasattr(self, "btn_run"):
            self._update_primary()
        try:
            self.cb_sublang.state(["!disabled"] if on else ["disabled"])
            self._switch_state(self.cb_embed, on and kind == "video")
            self.cb_quality.state(["disabled"] if kind == "subs" else ["!disabled"])
        except Exception:
            pass

    def _paste_url(self):
        try:
            txt = self.clipboard_get().strip()
        except Exception:
            txt = ""
        if txt:
            self.yt_url.set(txt)
            self.status.set("Đã dán link từ clipboard.")

    def _pick_file(self):
        p = filedialog.askopenfilename(title="Chọn file audio/video", filetypes=SUPPORTED)
        if p:
            self.src.set("file")
            self._src_changed()
            self.file_path.set(p)
            self.status.set(f"Đã chọn: {os.path.basename(p)}")

    def _pick_out_dir(self):
        d = filedialog.askdirectory(title="Chọn thư mục lưu",
                                    initialdir=self.out_dir.get() or BASE_DIR)
        if d:
            self.out_dir.set(d)
            self._save_cfg()

    # ----- nhật ký & tiến trình -----
    def _log(self, msg, level="info"):
        t = self.log_txt
        stamp = time.strftime("%H:%M:%S")
        t.configure(state="normal")
        t.insert("end", f"[{stamp}] ", "note")
        t.insert("end", str(msg).strip() + "\n", {"err": "err"}.get(level, ""))
        t.see("end")
        t.configure(state="disabled")
        last = "%s · %s" % (stamp, " ".join(str(msg).split()))
        self.log_last.configure(text=last if len(last) <= 46 else last[:45] + "…",
                                fg=self.P["bad_fg"] if level == "err" else self.P["fg"])

    def _pbar(self, value):
        if value is None:
            if str(self.pbar.cget("mode")) != "indeterminate":
                self.pbar.stop()
                self.pbar.configure(mode="indeterminate")
                self.pbar.start(14)
        else:
            self.pbar.stop()
            if str(self.pbar.cget("mode")) != "determinate":
                self.pbar.configure(mode="determinate")
            self.pbar["value"] = max(0.0, min(100.0, float(value) * 100))

    # ----- trạng thái màn hình (D-31): nơi DUY NHẤT bật/tắt nút & thanh tiến trình -----
    def _set_stt_state(self, state):
        """Tab Chuyển văn bản: idle | recording | processing | result | error."""
        assert state in STT_STATES, state
        prev = getattr(self, "stt_state", "idle")
        self.stt_state = state
        self.busy = state == "processing"
        if state == "recording":
            self.recording, self.rec_owner = True, "stt"
        elif prev == "recording" and self.rec_owner == "stt":
            self.recording, self.rec_owner = False, None
        c = stt_controls(state, self._src_label())
        self.btn_run.state(["!disabled"] if c["run_enabled"] else ["disabled"])
        self.btn_run.configure(text=c["run_text"])
        # "Hủy (Esc)" chỉ hiện khi có việc để hủy (thiết kế S-8)
        if c["cancel_enabled"] and not self.btn_cancel.winfo_manager():
            self.btn_cancel.pack(side="right")
        elif not c["cancel_enabled"] and self.btn_cancel.winfo_manager():
            self.btn_cancel.pack_forget()
        if c["show_pbar"] and not self.stt_prog.winfo_manager():
            self.stt_prog.pack(fill="x")
        elif not c["show_pbar"] and self.stt_prog.winfo_manager():
            self.pbar.stop()
            self.stt_prog.pack_forget()
        rec = state == "recording"
        if rec and not self.stt_meter_row.winfo_manager():
            self.stt_meter_row.pack(fill="x", pady=(self.px(10), 0))
            self._draw_meter(0.0, self.stt_meter)
        elif not rec and self.stt_meter_row.winfo_manager():
            self.stt_meter_row.pack_forget()
        if not rec:
            self.lbl_rec_level.configure(text="")
        self._stt_seg._draw()
        self._stt_view()

    def _set_prac_state(self, state):
        """Màn hình Luyện: idle | recording | scoring | result | unsure | error."""
        assert state in PRAC_STATES, state
        prev = getattr(self, "prac_state", "idle")
        self.prac_state = state
        self.p_working = state in ("scoring", "loading")
        if state == "recording":
            self.recording, self.rec_owner = True, "prac"
        elif prev == "recording" and self.rec_owner == "prac":
            self.recording, self.rec_owner = False, None
        c = prac_controls(state, bool(self.last_wav))
        self._rec_ctl = c
        self._draw_rec_btn()
        self.p_rec_label.configure(text=c["rec_label"])
        self._sync_rec_pills()
        # đang thu: thanh mức âm + dòng đồng hồ thay cho dòng micro
        rec = state == "recording"
        for w in (self.p_meter, self.lbl_plevel):
            if rec and not w.winfo_manager():
                w.pack(pady=(self.px(8), 0), before=self.p_rec_hint)
            elif not rec and w.winfo_manager():
                w.pack_forget()
        if rec:
            self._draw_meter(0.0)
        else:
            self.lbl_plevel.configure(text="")
        # đổi bài/chế độ bị khóa khi đang thu hoặc đang chấm (câu chấm = câu đang đọc)
        locked = state in ("recording", "scoring", "loading")
        for w in (self.cb_prac, self.btn_pprev, self.btn_pnext, self.btn_yt_get):
            w.state(["disabled"] if locked else ["!disabled"])
        self._seg._draw()
        if state in ("idle", "recording", "scoring", "error", "loading"):
            self._panel_state(state)

    # ----- chạy / hủy -----
    def _primary(self):
        if self.recording:
            if self.rec_owner == "stt":
                self._rec_stop_and_transcribe()
            else:
                self.status.set("Đang thu ở tab Luyện phát âm — dừng ở đó trước (hoặc Esc).")
            return
        src = self.src.get()
        if src == "rec":
            self._rec_start()
        else:
            self._run()

    def _run(self):
        if self.busy:
            return
        src = self.src.get()
        model_size = self.model_name.get()
        lang_opt = self.lang.get()
        lang = None if lang_opt == "auto" else lang_opt

        if src == "file":
            fp = self.file_path.get().strip().strip('"')
            if not fp or not os.path.exists(fp):
                messagebox.showwarning("Chưa có file", "Hãy chọn file audio/video trước (Ctrl+O).")
                return
            self.cancel_flag = False
            self._set_stt_state("processing")
            self._log(f"File: {os.path.basename(fp)}  ·  model {model_size}")
            self._pbar(None)
            self.status.set("Đang tải model & nhận dạng…")
            threading.Thread(target=self._w_file, args=(fp, model_size, lang),
                             daemon=True).start()
            return

        url = self.yt_url.get().strip()
        if not re.match(r"https?://", url) or "youtu" not in url.lower():
            messagebox.showwarning("Link không hợp lệ",
                                   "Chỉ hỗ trợ link YouTube (youtu.be/… hoặc watch?v=…).")
            return
        out = self.out_dir.get().strip() or YT_DIR_DEFAULT
        if not os.path.isdir(out):
            try:
                os.makedirs(out, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Không tạo được thư mục", str(e))
                return
        self.out_dir.set(out)
        kind = YT_KIND_BY_NAME.get(self.yt_kind.get(), "video")
        quality = "best" if kind in ("audio", "subs") else \
            YT_QUAL_BY_NAME.get(self.yt_quality.get(), "best")
        subs = bool(self.y_subs.get())
        embed = bool(self.y_embed.get())
        sub_pref = YT_SUB_LANG_BY_NAME.get(self.yt_sub_lang.get(), "auto")
        self.cancel_flag = False
        self._set_stt_state("processing")
        self._log(f"YouTube: {url}")
        self._log(f"Chế độ: {self.yt_kind.get()}" + (
            "  ·  phụ đề " + self.yt_sub_lang.get() if subs else "  ·  không phụ đề"))
        self._pbar(0)
        self.status.set("Đang lấy thông tin video…")
        threading.Thread(target=self._w_yt,
                         args=(url, kind, quality, out, subs, sub_pref, embed,
                               model_size, lang), daemon=True).start()

    def _stop_recorder(self):
        """Dừng recorder dùng chung; tab đang thu về trạng thái idle (D-26, D-31).
        Trả (frames, rate)."""
        owner = self.rec_owner
        frames, rate = self.recorder.stop()
        if owner == "prac":
            self._set_prac_state("idle")
        else:
            self._set_stt_state("idle")
        return frames, rate

    def _cancel(self):
        if self.recording:
            owner = self.rec_owner
            self._stop_recorder()
            if owner == "prac":
                self.p_status.set("Đã dừng thu âm, không chấm điểm.")
            else:
                self.status.set("Đã dừng thu âm, không chuyển văn bản.")
            return
        if self.busy and not self.cancel_flag:
            self.cancel_flag = True
            self.status.set("Đang hủy…")
            self._log("Người dùng bấm hủy.", "err")
            return
        if getattr(self, "prac_state", "") == "loading" and not self._yt_cancel:
            self._yt_cancel = True
            self.p_status.set("Đang hủy…")
        elif self._yt_listening:
            self._stop_play()
            self.p_status.set("Đã dừng nghe — bấm Thu âm khi sẵn sàng.")

    def _poll(self):
        """Vòng lặp duy nhất: nhận cập nhật từ worker thread (chạy trên luồng UI)."""
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    if isinstance(payload, tuple):
                        self._log(*payload)
                    else:
                        self._log(payload)
                elif kind == "status":
                    self.status.set(payload)
                elif kind == "progress":
                    self._pbar(payload)
                elif kind == "result":
                    self._on_result(payload)
                elif kind == "error":
                    self._on_error(payload)
                elif kind == "rec_autostop":
                    self._rec_stop_and_transcribe()
                elif kind == "rec_error":
                    if self.rec_owner == "stt":
                        self._stop_recorder()
                    self.status.set("Lỗi thu âm.")
                    messagebox.showerror("Lỗi thu âm", payload)
                elif kind == "prac_status":
                    self.p_status.set(payload)
                elif kind == "mic_test":
                    self.mic_test_msg.set(payload)
                elif kind == "prac_autostop":
                    self._prac_stop_and_score(payload)
                elif kind == "prac_done":
                    self._prac_done(payload)
                elif kind == "yt_ready":
                    self._yt_ready(payload)
                elif kind == "yt_fail":
                    self._yt_fail(payload)
                elif kind == "yt_done":
                    self._yt_done(*payload)
                elif kind == "yt_listen_done":
                    self._yt_listen_done(payload)
                elif kind == "prac_error":
                    self._prac_error(payload)
                elif kind == "mic_found":
                    self._mic_probing = False
                    if payload and payload[3] >= MIC_MIN_PEAK:
                        idx, name, api, peak = payload
                        try:
                            self.mic_var.set(
                                self._mic_names[self.mic_ids.index(idx)])
                            self.p_status.set(
                                f"Đã chọn micro có tín hiệu: {name} [{api}] "
                                f"(đỉnh {peak * 100:.0f}%). "
                                f"Bấm Thu âm & chấm để đọc lại.")
                        except ValueError:
                            self.p_status.set(
                                "Tìm thấy micro có tín hiệu nhưng danh sách vừa đổi — "
                                "bấm Quét lại rồi chọn lại micro.")
                    else:
                        self.p_status.set(
                            "Không tìm thấy micro nào có tín hiệu. Kiểm tra âm lượng "
                            "trong Windows: Settings → System → Sound → Input.")
        except queue.Empty:
            pass
        self.after(80, self._poll)

    # ================= worker: nhận dạng file / bản ghi =================
    def _w_file(self, fp, model_size, lang, delete_after=False, base=None):
        try:
            self._queue.put(("status", f"Bước 1/2: tải model '{model_size}' "
                                       f"(lần đầu hơi lâu)…"))
            model = load_model(model_size)
            self._queue.put(("status", "Bước 2/2: đang nhận dạng giọng nói…"))
            segs, info = model.transcribe(fp, language=lang, beam_size=5)
            dur = float(getattr(info, "duration", 0) or 0)
            cues = []
            for s in segs:
                if self.cancel_flag:
                    raise _YtCancelled()
                tx = " ".join(s.text.split())
                if tx:
                    cues.append((float(s.start), float(s.end), tx))
                if dur > 0:
                    self._queue.put(("progress", min(0.99, float(s.end) / dur)))
            cues = _fix_cues(split_long_cues(cues))
            det = getattr(info, "language", "?")
            prob = float(getattr(info, "language_probability", 0) or 0)
            self._queue.put(("log", (f"Nhận dạng xong: {len(cues)} dòng · "
                                     f"ngôn ngữ {det} ({prob:.0%})", "info")))
            media = None if delete_after else fp
            if not base:
                base = os.path.splitext(os.path.basename(fp))[0]
            payload = {"cues": cues, "media": media, "base": base,
                       "note": f"Xong: {len(cues)} dòng · {det} ({prob:.0%})"}
            self._queue.put(("result", payload))
        except _YtCancelled:
            self._queue.put(("error", "__cancelled__"))
        except Exception as e:
            self._queue.put(("error", str(e)))
        finally:
            # bản ghi tạm: xóa cả khi xong, hủy hay lỗi (I10)
            if delete_after:
                remove_temp(fp)

    def _w_whisper_cues(self, media, model_size, lang):
        self._queue.put(("status", f"Đang tạo phụ đề bằng Whisper (model '{model_size}')…"))
        self._queue.put(("progress", None))
        model = load_model(model_size)
        segs, info = model.transcribe(media, language=lang, beam_size=5, vad_filter=True)
        cues = []
        det = getattr(info, "language", "?")
        for s in segs:
            if self.cancel_flag:
                raise _YtCancelled()
            tx = " ".join(s.text.split())
            if tx:
                cues.append((float(s.start), float(s.end), tx))
            if cues and len(cues) % 15 == 0:
                self._queue.put(("status",
                                 f"Whisper: {clock_time(s.end)} · {len(cues)} câu"))
        self._queue.put(("log", (f"Whisper xong: {len(cues)} câu ({det})", "info")))
        return _fix_cues(split_long_cues(cues))

    # ================= worker: YouTube =================
    def _w_yt(self, url, kind, quality, out_dir, subs, sub_pref, embed,
              model_size, lang):
        """Điểm vào thread: luôn gửi 'result' hoặc 'error' để UI thoát trạng thái bận.

        Thiếu lớp bọc này thì Hủy (_YtCancelled) hay lỗi bất ngờ làm thread chết
        im lặng → nút Bắt đầu bị khóa mãi, thanh trạng thái treo "Đang hủy…".
        """
        try:
            self._w_yt_body(url, kind, quality, out_dir, subs, sub_pref, embed,
                            model_size, lang)
        except _YtCancelled:
            self._queue.put(("error", "__cancelled__"))
        except Exception as e:
            # yt-dlp có thể bọc ngoại lệ từ hook thành DownloadError
            if self.cancel_flag:
                self._queue.put(("error", "__cancelled__"))
            else:
                self._queue.put(("error", f"Lỗi YouTube: {e}"))

    def _yt_fetch_sub_cues(self, yt_dlp, url, stem, sub_lang, since):
        """Tải phụ đề có sẵn về <stem>.<lang>.<ext>, đọc thành cue, xóa file thô.

        Không bao giờ ném lỗi tải (trừ Hủy): trả [] để nơi gọi chuyển sang Whisper.
        YouTube hay trả HTTP 429 cho phụ đề (nhất là bản dịch máy) → thử lại 1 lần.
        """
        out_dir = os.path.dirname(stem) or "."
        opts = {"skip_download": True, "writesubtitles": True,
                "writeautomaticsub": True, "subtitleslangs": [sub_lang],
                "subtitlesformat": "srt/vtt/best",
                "outtmpl": stem + ".%(ext)s",
                "quiet": True, "no_warnings": True, "noplaylist": True}
        for attempt in (1, 2):
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                break
            except _YtCancelled:
                raise
            except Exception as e:
                if self.cancel_flag:
                    raise _YtCancelled()
                busy = "429" in str(e)
                if busy and attempt == 1:
                    self._queue.put(("status", "YouTube đang giới hạn tải phụ đề, thử lại…"))
                    for _ in range(40):  # ~4 s, vẫn phản hồi nút Hủy
                        if self.cancel_flag:
                            raise _YtCancelled()
                        time.sleep(0.1)
                    continue
                why = ("YouTube tạm chặn vì tải quá nhiều (HTTP 429)" if busy
                       else str(e).replace("ERROR: ", ""))
                self._queue.put(("log", (f"Không tải được phụ đề '{sub_lang}': {why} "
                                         "→ chuyển sang Whisper.", "err")))
                break
        raw = find_subtitle_file(out_dir, stem + ".mp4", sub_lang, since)
        if not raw:
            return []
        try:
            cues = read_subtitle_file(raw)
        except Exception:
            cues = []
        if cues and os.path.normcase(raw) != os.path.normcase(stem + ".srt"):
            try:
                os.remove(raw)
            except OSError:
                pass
        return cues

    def _w_yt_body(self, url, kind, quality, out_dir, subs, sub_pref, embed,
                   model_size, lang):
        try:
            import yt_dlp
        except ImportError:
            self._queue.put(("error", "Chưa có thư viện yt-dlp. "
                                      "Chạy: pip install -r requirements.txt"))
            return
        ffmpeg_loc = yt_ffmpeg_location()
        if not ffmpeg_loc:
            self._queue.put(("error", "Chưa có ffmpeg (imageio-ffmpeg). "
                                      "Chạy: pip install -r requirements.txt"))
            return
        t0 = time.time()

        def hook(d):
            if self.cancel_flag:
                raise _YtCancelled()
            st = d.get("status")
            if st == "downloading":
                frac = yt_progress_fraction(d)  # 0..1 — _pbar tự nhân 100
                if frac is not None:
                    self._queue.put(("progress", frac))
                self._queue.put(("status",
                                 f"Đang tải… {os.path.basename(d.get('filename') or '')}"))
            elif st == "finished":
                self._queue.put(("progress", None))
                self._queue.put(("status", "Đã tải xong, đang ghép bằng ffmpeg…"))

        self._queue.put(("status", "Đang đọc thông tin video…"))
        info = {}
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                   "noplaylist": True}) as ydl:
                info = ydl.extract_info(url, download=False) or {}
            info = _yt_first_info(info)
        except Exception as e:
            self._queue.put(("error", f"Không lấy được thông tin video: {e}"))
            return
        if self.cancel_flag:
            raise _YtCancelled()

        title, vid = info.get("title") or "", info.get("id") or ""
        base = safe_stem(title, vid)
        self._queue.put(("log", (f"Video: {title or vid}", "info")))
        sub_lang, sub_kind = (pick_subtitle_source(info, sub_pref) if subs
                              else (None, None))
        sub_label = ""
        if subs:
            if sub_lang:
                tracks = ((info.get("subtitles") or {}).get(sub_lang)
                          or (info.get("automatic_captions") or {}).get(sub_lang) or [])
                name = (tracks[0] or {}).get("name") if tracks else ""
                available = sorted(set((info.get("subtitles") or {}).keys()) |
                                   set((info.get("automatic_captions") or {}).keys()))
                orig = (info.get("language") or "").lower()
                sub_label = f"{sub_lang}" + (f" ({name})" if name else "")
                hint = ""
                sub_base = sub_lang.lower().split("-")[0]
                if (sub_kind == "auto" and orig and sub_base != orig) or                         sub_base not in ("en", orig):
                    hint = ("  → đây là bản dịch máy của YouTube, không phải bản gốc"
                            + (f"; muốn bản gốc hãy chọn Ngôn ngữ = Tự động ({orig})"
                               if orig else ""))
                self._queue.put(("log", (
                    f"Phụ đề chọn: {sub_label} "
                    f"({'tự động' if sub_kind == 'auto' else 'thủ công'})"
                    f"{hint}", "info")))
                if available:
                    self._queue.put(("log", (
                        "Video có phụ đề: " + ", ".join(available[:12]), "info")))
            else:
                self._queue.put(("log", ("Video không có phụ đề sẵn → dùng Whisper.",
                                         "info")))

        cues = []
        from_video = False  # phụ đề lấy từ YouTube (True) hay do Whisper tạo
        media_path = None

        # ---- chế độ chỉ transcript: không tải video ----
        if kind == "subs":
            if sub_lang:
                self._queue.put(("status", "Đang tải phụ đề có sẵn (không tải video)…"))
                cues = self._yt_fetch_sub_cues(yt_dlp, url, os.path.join(out_dir, base),
                                               sub_lang, t0)
                from_video = bool(cues)
            if not cues:
                self._queue.put(("status",
                                 "Chưa có phụ đề → tải âm thanh tạm để Whisper tạo…"))
                tmp_dir = tempfile.mkdtemp(prefix="stt_yt_")
                opts = {"format": "ba/b",
                        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
                        "quiet": True, "no_warnings": True, "noplaylist": True,
                        "progress_hooks": [hook]}
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    files = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir)]
                    tmp_media = max(files, key=os.path.getsize) if files else None
                    if not tmp_media:
                        self._queue.put(("error", "Không tải được âm thanh của video."))
                        return
                    cues = self._w_whisper_cues(tmp_media, model_size, lang)
                finally:
                    # dọn cả file .part khi hủy/lỗi giữa chừng (I10)
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            base = os.path.join(out_dir, base)

        # ---- tải video/audio ----
        else:
            self._queue.put(("status", "Đang tải video…"))
            # không kèm phụ đề: yt-dlp coi lỗi tải phụ đề (vd HTTP 429) là lỗi chết
            # → mất luôn video. Phụ đề tải riêng ở dưới, lỗi thì dùng Whisper (D-25).
            opts = yt_build_opts(out_dir, "audio" if kind == "audio" else "video",
                                 quality, ffmpeg_loc, hook, None)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    dl_info = _yt_first_info(ydl.extract_info(url, download=True) or {})
            except _YtCancelled:
                raise
            except Exception as e:
                self._queue.put(("error", f"Tải video lỗi: {e}"))
                return
            media_path = pick_downloaded_file(dl_info, out_dir, vid, t0)
            if not media_path:
                self._queue.put(("error",
                                 "Đã tải nhưng không tìm thấy file trong thư mục:\n"
                                 + out_dir + "\n\n"
                                 "Kiểm tra quyền ghi thư mục, hoặc thử đổi thư mục lưu."))
                return
            base = os.path.splitext(media_path)[0]
            if subs:
                if sub_lang:
                    self._queue.put(("status", "Đang tải phụ đề có sẵn…"))
                    cues = self._yt_fetch_sub_cues(yt_dlp, url, base, sub_lang, t0)
                    from_video = bool(cues)
                if not cues:
                    cues = self._w_whisper_cues(media_path, model_size, lang)

        if self.cancel_flag:
            raise _YtCancelled()

        # ---- ghi .srt/.txt ----
        srt_path = txt_path = None
        if cues:
            srt_path = base + ".srt"
            txt_path = base + ".txt"
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(cues_to_srt(cues))
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(cues_to_txt(cues))

        # ---- nhúng phụ đề mềm vào video ----
        if cues and embed and kind == "video" and media_path and srt_path:
            if self.cancel_flag:
                raise _YtCancelled()
            self._queue.put(("status", "Đang nhúng phụ đề vào video…"))
            muxed, err = mux_subtitles_into_video(media_path, srt_path, ffmpeg_loc,
                                                  sub_lang or "vi")
            if muxed:
                media_path = muxed
            else:
                self._queue.put(("log", (f"Không nhúng được phụ đề: {err}", "err")))

        bits = []
        if cues:
            bits.append(f"{len(cues)} dòng phụ đề")
            bits.append(("từ video: " + sub_label) if from_video else "do Whisper tạo")
        if media_path:
            bits.append(os.path.basename(media_path))
        self._queue.put(("result", {
            "cues": cues, "media": media_path, "srt": srt_path, "txt": txt_path,
            "base": os.path.basename(base), "note": "Xong" + (
                ": " + "  ·  ".join(bits) if bits else "."),
        }))

    # ================= kết quả & xuất file =================
    def _render_preview(self):
        cues = self.last_cues
        if cues:
            text = cues_to_txt(cues, with_time=True) if self.show_time.get() \
                else "\n".join(c[2] for c in cues)
        else:
            text = (self.last_payload or {}).get("text", "")
        w = self.txt_out
        w.configure(state="normal")
        w.delete("1.0", "end")
        # chữ giống hệt cues_to_txt (để Lưu .txt / Sao chép không đổi); mốc thời gian tô mờ
        for line in (text or "").splitlines():
            m = re.match(r"(\[\d{2}:\d{2}:\d{2}\] )(.*)", line)
            if m:
                w.insert("end", m.group(1), ("doc", "time"))
                w.insert("end", m.group(2) + "\n", "doc")
            else:
                w.insert("end", line + "\n", "doc")

    def _on_result(self, p):
        self._set_stt_state("result")
        self.pbar.configure(mode="determinate", value=0)
        cues = p.get("cues") or []
        self.last_cues = cues
        self.last_payload = p
        self.last_media = p.get("media")
        self.last_srt = p.get("srt")
        self.last_txt = p.get("txt")
        self._render_preview()
        srt = cues_to_srt(cues)
        self.txt_srt.configure(state="normal")
        self.txt_srt.delete("1.0", "end")
        self.txt_srt.insert("1.0", srt or "Chưa có phụ đề.")
        self.txt_srt.configure(state="disabled")
        words = sum(len(c[2].split()) for c in cues)
        dur = cues[-1][1] if cues else 0
        self.st_vals["lines"].configure(text=str(len(cues)))
        self.st_vals["words"].configure(text=f"{words:,}".replace(",", "."))
        self.st_vals["dur"].configure(text=short_duration(dur))
        on = bool(cues)
        for b in (self.btn_copy, self.btn_txt):
            b.state(["!disabled"] if on else ["disabled"])
        self.btn_srt.state(["!disabled"] if cues else ["disabled"])
        self._link_state(self.btn_folder, bool(self.last_srt or self.last_media))
        self._link_state(self.btn_open, bool(self.last_media and os.path.exists(self.last_media)))
        note = p.get("note") or "Xong."
        src = os.path.basename(self.last_media) if self.last_media else (p.get("base") or "")
        self.ss_note.configure(text=" · ".join(x for x in (src, note) if x))
        self.status.set(note)
        self._log(note)
        self._stt_view()

    def _on_error(self, err):
        self._set_stt_state("idle" if err == "__cancelled__" else "error")
        self.pbar.configure(mode="determinate", value=0)
        self._stt_view()
        if err == "__cancelled__":
            self.status.set("Đã hủy.")
            self._log("Đã hủy tác vụ.", "err")
            return
        self.status.set("Lỗi — xem chi tiết trong hộp thoại.")
        self._log(f"Lỗi: {err}", "err")
        messagebox.showerror("Lỗi", str(err))

    def _default_base(self):
        p = self.last_payload or {}
        if p.get("base"):
            return p["base"]
        if self.last_media:
            return os.path.splitext(os.path.basename(self.last_media))[0]
        return "ket-qua"

    def _copy(self):
        if not (self.last_cues or (self.last_payload or {}).get("text")):
            return
        text = self.txt_out.get("1.0", "end").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("Đã copy vào clipboard.")

    def _save_txt(self):
        text = self.txt_out.get("1.0", "end").strip()
        if not text or not self.last_cues:
            messagebox.showinfo("Trống", "Chưa có nội dung để lưu.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                         initialfile=self._default_base() + ".txt",
                                         filetypes=[("Text", "*.txt"), ("Tất cả file", "*.*")])
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        self.last_txt = p
        self.status.set(f"Đã lưu: {p}")
        self._log(f"Lưu .txt → {p}")

    def _save_srt(self):
        cues = self.last_cues
        if not cues:
            messagebox.showinfo("Chưa có phụ đề", "Chưa có mốc thời gian để xuất .srt.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".srt",
                                         initialfile=self._default_base() + ".srt",
                                         filetypes=[("SubRip", "*.srt"), ("Tất cả file", "*.*")])
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            f.write(cues_to_srt(cues))
        self.last_srt = p
        self.status.set(f"Đã lưu phụ đề: {p}  ({len(cues)} dòng)")
        self._log(f"Lưu .srt → {p}")

    def _open_folder(self):
        target = self.last_srt or self.last_txt or self.last_media
        folder = os.path.dirname(target) if target else (self.out_dir.get() or BASE_DIR)
        try:
            os.startfile(folder)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không mở được thư mục: {e}")

    def _open_file(self):
        p = self.last_media
        if not p or not os.path.exists(p):
            return
        try:
            os.startfile(p)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không mở được file: {e}")

    # ================= ghi âm ở tab 1 =================
    def _rec_start(self):
        if self.busy or self.recording:
            return
        dev, name, rate = self._resolve_mic()
        if dev is None:
            return
        self._set_stt_state("recording")
        self.recorder.start(dev, rate, REC_LONG_SEC,
                            lambda reason: self._queue.put(("rec_autostop", reason)),
                            lambda m: self._queue.put(("rec_error", m)))
        self._log(f"Thu âm bằng {name} ({rate} Hz)")
        self.status.set(f"Đang thu bằng {name} — đọc to, rõ.")
        self._rec_tick()

    def _rec_tick(self):
        if not self.recording:
            return
        el = int(time.time() - self.recorder.t0)
        self.lbl_rec_level.configure(text="● Đang thu · %d:%02d / %d:00"
                                     % (el // 60, el % 60, REC_LONG_SEC // 60))
        self._draw_meter(self.recorder.level, self.stt_meter)
        self.after(120, self._rec_tick)

    def _rec_stop_and_transcribe(self):
        if not self.recording or self.rec_owner != "stt":
            return
        frames, rate = self._stop_recorder()
        if not frames:
            self.status.set("Chưa thu được gì — thử lại.")
            return
        # file tạm thuộc về _w_file (delete_after=True); không gán last_wav — đó là
        # bản ghi để Nghe lại của tab Luyện phát âm.
        path, secs, info = save_frames_wav(frames, "stt_", rate)
        info["dropped"] = self.recorder.dropped
        self._log(quality_note(info))
        if secs < 0.4:
            remove_temp(path)
            self.status.set("Bản thu quá ngắn (<0.4s) — thử lại, đọc to hơn.")
            return
        self.cancel_flag = False
        self._set_stt_state("processing")
        self._pbar(None)
        self.status.set("Đang chuyển bản thu thành văn bản…")
        base = "ghi-am-" + time.strftime("%Y%m%d-%H%M%S")
        threading.Thread(target=self._w_file,
                         args=(path, self.model_name.get(),
                               None if self.lang.get() == "auto" else self.lang.get(),
                               True, base), daemon=True).start()

    # ================= tab 2: luyện phát âm =================
    # ================= màn hình Luyện phát âm (app-style, D-28 / B4a) =================
    def _build_practice_tab(self, parent):
        self._p_target = ""
        self._embeds = []          # widget động trong panel (thẻ lỗi, ghi chú) — hủy khi vẽ lại
        self._pills = []
        self._last_view = None
        self._last_words_t = []
        self._show_details = False
        self._show_heard = False
        self._rec_ctl = prac_controls("idle", False)
        self._stage_data = []
        self._words_key = None

        # ---- thanh công cụ: chế độ · bài · vị trí · bài trước/sau ----
        bar = self._toolbar(parent)
        self.yt_read_url = tk.StringVar()
        self.yt_listen = tk.StringVar(value="listen")
        self._yt_sess, self._yt_idx, self._yt_cancel = None, 0, False
        self._yt_listening, self._yt_res, self._yt_view = False, None, None
        self._yt_keep = {}   # đoạn → {"wav", "res", "gate"}: bản thu + kết quả gần nhất (R1)
        self._saved = {}     # bản thu tạm (đường dẫn) → nơi đã lưu: nút "Đã lưu ✓"
        self._seg = self._mk_seg(bar, (("set", "Luyện câu"), ("guide", "Học âm"),
                                       ("yt", "Từ YouTube")),
                                 self.prac_mode, self._prac_mode_changed,
                                 locked=lambda: self.p_working or self.recording)
        self._seg.pack(side="left", padx=(self.px(28), self.px(16)))
        self.cb_prac = ttk.Combobox(bar, textvariable=self.prac_pick, width=30,
                                    state="readonly", style="Toolbar.TCombobox",
                                    font=(self.F, 12, "bold"))
        self.cb_prac["values"] = SET_NAMES
        self.cb_prac.current(0)
        self.cb_prac.pack(side="left")
        self.cb_prac.bind("<<ComboboxSelected>>", lambda e: self._refresh_practice())
        # đọc to YouTube (D-39): ô link + nút thay cho combobox bài
        self.yt_bar = self._frame(bar, bg="card")
        self.yt_entry = ttk.Entry(self.yt_bar, textvariable=self.yt_read_url, width=34,
                                  font=(self.F, 11))
        self.yt_entry.pack(side="left")
        self.yt_entry.bind("<Return>", lambda e: self._yt_load())
        self.btn_yt_get = ttk.Button(self.yt_bar, text="Lấy transcript", style="Accent.TButton",
                                     command=self._yt_load)
        self.btn_yt_get.pack(side="left", padx=(self.px(8), 0))
        self.p_pos = self._lbl(bar, "", fg="muted", size=10)
        self.p_pos.pack(side="left", padx=(self.px(10), 0))
        self.btn_pnext = ttk.Button(bar, text="Bài sau ▶", style="Ghost.TButton",
                                    command=lambda: self._step_lesson(1))
        self.btn_pnext.pack(side="right", padx=(0, self.px(28)))
        self.btn_pprev = ttk.Button(bar, text="◀ Bài trước", style="Ghost.TButton",
                                    command=lambda: self._step_lesson(-1))
        self.btn_pprev.pack(side="right", padx=(0, self.px(8)))

        # ---- thân: sân khấu (giữa) + panel chi tiết (phải) ----
        body = self._frame(parent, bg="card")
        body.pack(fill="both", expand=True)
        self._prac_body = body
        self.yt_report = self._frame(parent, bg="card")   # báo cáo cuối phiên (D-43)
        self.p_side = self._frame(body, bg="side", width=self.px(400))
        self.p_side.pack(side="right", fill="y")
        self.p_side.pack_propagate(False)
        self._tw(tk.Frame(body, width=1, bd=0, highlightthickness=0), bg="border").pack(
            side="right", fill="y")
        stage = self._frame(body, bg="card")
        stage.pack(side="left", fill="both", expand=True)
        body.bind("<Configure>", self._prac_body_resized)
        self._build_stage(stage)
        self._build_side(self.p_side)
        self._clear_prac_result()

    # ---------- sân khấu: câu đọc, nghe mẫu, mẹo, nút thu ----------
    def _build_stage(self, st):
        inner = self._frame(st, bg="card")
        inner.pack(fill="both", expand=True, padx=self.px(32), pady=(self.px(28), self.px(18)))
        self._stage_in = inner
        self.entry_custom = ttk.Entry(inner, textvariable=self.custom_text, font=(self.F, 11))
        self.entry_custom.bind("<KeyRelease>", lambda e: self._refresh_practice())
        self.p_lead = self._lbl(inner, "Đọc to câu này", fg="muted", size=10)
        self.p_words = self._frame(inner, bg="card", height=self.px(60))
        self.p_words.bind("<Configure>", lambda e: self._layout_words())
        self.p_ipa = self._lbl(inner, "", fg="muted", font=(FONT_IPA, 12))
        self.p_hint = self._lbl(inner, "", fg="muted", font=(FONT_IPA, 9), justify="center")
        self.p_samples = self._frame(inner, bg="card", height=1)
        self.p_samples.bind("<Configure>", lambda e: self._layout_pills())
        # đọc to YouTube (D-39): tiêu đề video · đoạn · chế độ · cả đoạn văn (cuộn được)
        self.yt_head = self._frame(inner, bg="card")
        # ba dòng xếp chồng (không một hàng ngang): cột đoạn văn hẹp vì cột thu âm nằm cạnh
        self.yt_title = self._lbl(self.yt_head, "", fg="muted", size=10, justify="center")
        self.yt_title.pack(fill="x")
        self.yt_meta = self._lbl(self.yt_head, "", size=10, weight="bold")
        self.yt_meta.pack(pady=(self.px(6), 0))
        self._yt_seg = self._mk_seg(self.yt_head, (("listen", "Nghe rồi đọc"),
                                                   ("read", "Đọc thẳng")),
                                    self.yt_listen, self._yt_mode_hint,
                                    locked=lambda: self.p_working or self.recording)
        self._yt_seg.pack(pady=(self.px(8), 0))
        self.yt_head.bind("<Configure>", lambda e: self.yt_title.configure(
            wraplength=max(self.px(120), e.width)))
        self.yt_text = self._mk_text(inner, role="doc", scroll=True, height=6,
                                     font=(self.F, 15), padx=self.px(14), pady=self.px(10),
                                     spacing1=self.px(3), spacing3=self.px(3), cursor="arrow")
        self.yt_text.configure(state="disabled")
        self._redraws.append(self._yt_tags)
        self._yt_tags()
        self.p_tip = self._frame(inner, bg="card2")
        ic = self._tw(tk.Canvas(self.p_tip, width=self.px(16), height=self.px(16), bd=0,
                                highlightthickness=0), bg="card2")
        ic.pack(side="left", anchor="n", padx=(self.px(14), self.px(10)), pady=(self.px(12), 0))
        self._p_tip_icon = ic
        self.p_how = self._lbl(self.p_tip, "", bg="card2", size=10, justify="left", anchor="w")
        self.p_how.pack(side="left", fill="x", expand=True, padx=(0, self.px(14)),
                        pady=self.px(10))
        self._redraws.append(self._draw_tip_icon)
        self._draw_tip_icon()

        # khối thu âm ở đáy sân khấu
        rb = self._frame(inner, bg="card")
        rb.pack(side="bottom", fill="x")
        self.p_recbox = rb
        self.btn_prec = self._tw(tk.Canvas(rb, bd=0, highlightthickness=0, cursor="hand2"),
                                 bg="card")
        self.btn_prec.pack()
        self.btn_prec.bind("<Button-1>", lambda e: self._rec_btn_click())
        self.p_rec_label = self._lbl(rb, "Thu âm", size=12, weight="bold")
        self.p_rec_label.pack(pady=(self.px(6), 0))
        self.p_meter = self._tw(tk.Canvas(rb, width=self.px(260), height=self.px(10), bd=0,
                                          highlightthickness=0), bg="card")
        self.lbl_plevel = self._lbl(rb, "", fg="rec", size=9, weight="bold")
        # hai dòng ngắn thay một dòng dài: sân khấu hẹp vẫn thấy "Đổi"
        self.p_rec_hint = self._lbl(rb, "Đọc xong, app tự dừng và chấm", fg="muted", size=9)
        self.p_rec_hint.pack(pady=(self.px(8), 0))
        self.p_micline = self._frame(rb, bg="card")
        self.p_micline.pack(pady=(self.px(2), 0))
        self.p_mic_lbl = self._lbl(self.p_micline, "", fg="muted", size=9)
        self.p_mic_lbl.pack(side="left")
        self._link_lbl(self.p_micline, "Đổi", lambda: self._show_screen("set"), size=9).pack(
            side="left", padx=(self.px(6), 0))
        self.p_status_lbl = tk.Label(rb, textvariable=self.p_status, font=(self.F, 9), bd=0,
                                     justify="center")
        self._tw(self.p_status_lbl, bg="card", fg="muted")
        links = self._frame(rb, bg="card")
        links.pack(pady=(self.px(4), 0))
        self._p_links = links
        # dòng trạng thái chỉ chiếm chỗ khi có nội dung
        self.p_status.trace_add("write", lambda *_: self._sync_status_line())
        self._link_lbl(links, "Chấm file có sẵn…", self._prac_from_file, size=9).pack(side="left")
        self._lbl(links, "  ·  ", fg="muted", size=9).pack(side="left")
        self._link_lbl(links, "Dừng phát", self._stop_play, size=9).pack(side="left")
        st.bind("<Configure>", self._stage_resized)
        self.mic_var.trace_add("write", lambda *_: self._update_mic_line())
        self._update_mic_line()
        self._redraws.append(self._draw_rec_btn)
        self._redraws.append(self._redraw_words)
        self._redraws.append(self._redraw_pills)
        self._draw_rec_btn()

    def _sync_status_line(self):
        on = bool(self.p_status.get().strip())
        if on and not self.p_status_lbl.winfo_manager():
            self.p_status_lbl.pack(pady=(self.px(4), 0), before=self._p_links)
        elif not on and self.p_status_lbl.winfo_manager():
            self.p_status_lbl.pack_forget()

    def _stage_resized(self, e=None):
        if e is not None:
            self._stage_w = e.width
        w = max(self.px(200), getattr(self, "_stage_w", 0) - 2 * self.px(32))
        self.p_how.configure(wraplength=min(self.px(640), w - self.px(60)))
        self.p_hint.configure(wraplength=w)
        # Từ YouTube: khối thu âm là cột hẹp cạnh đoạn văn → chữ trong cột tự xuống dòng
        col = self._yt_col() if self.prac_mode.get() == "yt" else w
        for lb in (self.p_status_lbl, self.p_rec_hint, self.lbl_plevel, self.p_mic_lbl):
            lb.configure(wraplength=col)

    def _yt_col(self):
        """Bề rộng cột thu âm cạnh đoạn văn (cửa sổ hẹp: hẹp hơn để đoạn văn còn chỗ)."""
        return self.px(YT_REC_COL * (0.72 if self._compact else 1.0))

    def _meter_w(self):
        return min(self.px(260), self._yt_col()) if self.prac_mode.get() == "yt" \
            else self.px(260)

    def _stage_repack(self, custom, ipa, hint, tip):
        """Xếp lại phần trên sân khấu theo thứ tự cố định, bỏ phần trống."""
        for w in (self.p_recbox, self.entry_custom, self.p_lead, self.p_words, self.p_ipa,
                  self.p_hint, self.p_samples, self.p_tip, self.yt_head, self.yt_text.holder):
            if w.winfo_manager():
                w.pack_forget()
        self._stage_resized()
        if custom == "yt":
            # đoạn văn và nút thu cạnh nhau: người học nhìn cả đoạn trong lúc đọc (D-39)
            self.p_recbox.pack(side="right", anchor="n", padx=(self.px(24), 0),
                               pady=(self.px(56), 0))
            self.yt_head.pack(fill="x")
            self.p_samples.pack(fill="x", pady=(self.px(10), 0))
            self.yt_text.holder.pack(fill="both", expand=True, pady=(self.px(10), 0))
            self._prac_body_resized()
            return
        self.p_recbox.pack(side="bottom", fill="x")
        self._prac_body_resized()
        if custom:
            self.entry_custom.pack(fill="x", pady=(0, self.px(14)))
        self.p_lead.pack()
        self.p_words.pack(fill="x", pady=(self.px(8), 0))
        if ipa:
            self.p_ipa.pack(pady=(self.px(6), 0))
        if hint:
            self.p_hint.pack(pady=(self.px(4), 0))
        self.p_samples.pack(fill="x", pady=(self.px(14), 0))
        if tip:
            self.p_tip.pack(pady=(self.px(14), 0))

    def _draw_tip_icon(self):
        c, P, s = self._p_tip_icon, self.P, self.px(16)
        c.delete("all")
        w = max(1, self.px(1.6))
        c.create_oval(w, w, s - w, s - w, outline=P["accent_fg"], width=w)
        c.create_line(s / 2, s * 0.45, s / 2, s * 0.75, fill=P["accent_fg"], width=w)
        c.create_oval(s / 2 - w, s * 0.27 - w, s / 2 + w, s * 0.27 + w, fill=P["accent_fg"],
                      outline="")

    # ----- câu trên sân khấu: từng từ + gạch chân + "nghe ‘…’" (S-2 / D-28) -----
    def _words_font_size(self, text):
        n = len(text or "")
        size = 30 if n <= 36 else (24 if n <= 64 else 20)
        return max(16, size - 6) if self._compact else size

    def _set_stage_words(self, words):
        self._stage_data = list(words)
        self._redraw_words()

    def _redraw_words(self):
        for ch in self.p_words.winfo_children():
            ch.destroy()
        P = self.P
        words = self._stage_data or [{"text": "…gõ câu của bạn ở ô trên…", "kind": "plain",
                                      "note": ""}]
        size = self._words_font_size(" ".join(w["text"] for w in words))
        for w in words:
            fg, line, nfg = {"ok": (P["fg"], P["card"], P["ok_fg"]),
                             "unsure": (P["fg"], P["border"], P["muted"]),
                             "warn": (P["warn_fg"], P["warn_line"], P["warn_fg"]),
                             "bad": (P["bad_fg"], P["bad_line"], P["bad_fg"])}.get(
                w["kind"], (P["fg"], P["card"], P["muted"]))
            f = tk.Frame(self.p_words, bg=P["card"], bd=0, highlightthickness=0)
            tk.Label(f, text=w["text"], font=(self.F, size, "bold"), bg=P["card"], fg=fg,
                     bd=0, padx=0, pady=0).pack()
            tk.Frame(f, bg=line, height=max(2, self.px(4)), bd=0,
                     highlightthickness=0).pack(fill="x", pady=(self.px(2), self.px(2)))
            tk.Label(f, text=w["note"] or " ", font=(self.F, 10), bg=P["card"], fg=nfg,
                     bd=0, padx=0, pady=0).pack()
        self._words_key = None
        # đo kích thước khi Tk đã tính hình học (sau idle) — đo ngay thì mọi từ rộng 1 px
        self.after_idle(self._layout_words)

    def _layout_words(self):
        self._words_key = self._flow(self.p_words, self.px(16), self.px(6), self._words_key)

    def _layout_pills(self):
        self._pills_key = self._flow(self.p_samples, self.px(10), self.px(8),
                                     getattr(self, "_pills_key", None))

    def _flow(self, box, gx, gy, last_key):
        """Xếp con của box thành hàng, căn giữa, tự xuống dòng (place). Con có
        `_hidden = True` bị ẩn. Trả khóa bố cục để bỏ qua lần xếp lại giống hệt."""
        kids = [k for k in box.winfo_children() if not getattr(k, "_hidden", False)]
        for k in box.winfo_children():
            if getattr(k, "_hidden", False):
                k.place_forget()
        W = box.winfo_width()
        if W <= 1 or not kids or any(k.winfo_reqwidth() <= 1 for k in kids):
            if not kids:
                box.configure(height=1)
            return last_key
        key = (W, tuple(str(k) for k in kids))
        if key == last_key:
            return last_key
        rows, row, rw = [], [], 0
        for k in kids:
            kw = k.winfo_reqwidth()
            if row and rw + gx + kw > W:
                rows.append((row, rw))
                row, rw = [], 0
            rw += (gx if row else 0) + kw
            row.append(k)
        if row:
            rows.append((row, rw))
        y = 0
        for row, rw in rows:
            x = max(0, (W - rw) // 2)
            h = max(k.winfo_reqheight() for k in row)
            for k in row:
                k.place(x=x, y=y)
                x += k.winfo_reqwidth() + gx
            y += h + gy
        box.configure(height=max(1, y - gy))
        return key

    # ----- nút nghe dạng viên thuốc (Canvas, góc bo) -----
    def _round_rect(self, c, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
               x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return c.create_polygon(pts, smooth=True, **kw)

    def _mk_pill(self, parent, text, command, enabled=True, icon=True):
        """Nút viên thuốc; icon=True vẽ ▶ (nghe), False chỉ có chữ (vd Lưu bản thu)."""
        import tkinter.font as tkfont
        f = tkfont.Font(family=self.F, size=10)
        h = f.metrics("linespace") + self.px(14)
        cv = tk.Canvas(parent, width=1, height=h, bd=0, highlightthickness=0, cursor="hand2")
        cv._pill = {"text": text, "cmd": command, "enabled": enabled, "font": f, "icon": icon}
        self._pill_size(cv)
        cv.bind("<Button-1>", lambda e: cv._pill["enabled"] and cv._pill["cmd"]())
        self._pills.append(cv)
        self._draw_pill(cv)
        return cv

    def _pill_size(self, cv):
        d = cv._pill
        cv.configure(width=d["font"].measure(d["text"]) + self.px(32)
                     + (self.px(12) if d["icon"] else 0))

    def _pill_set_text(self, cv, text):
        if cv._pill["text"] != text:
            cv._pill["text"] = text
            self._pill_size(cv)
            self._draw_pill(cv)
            self._pills_key = None
            self.after_idle(self._layout_pills)

    def _draw_pill(self, cv):
        P, d = self.P, cv._pill
        w, h = int(cv.cget("width")), int(cv.cget("height"))
        cv.configure(bg=P["card"], cursor="hand2" if d["enabled"] else "")
        cv.delete("all")
        self._round_rect(cv, 1, 1, w - 1, h - 1, h // 2, fill=P["card2"], outline=P["border"])
        fg = P["fg"] if d["enabled"] else P["disabled_fg"]
        x, y, t = self.px(16), h / 2.0, self.px(5)
        if d["icon"]:
            cv.create_polygon(x, y - t, x, y + t, x + t * 1.6, y, fill=fg, outline="")
            x += self.px(16)
        cv.create_text(x, y, text=d["text"], anchor="w", fill=fg, font=d["font"])

    def _redraw_pills(self):
        alive = []
        for cv in self._pills:
            try:
                self._draw_pill(cv)
                alive.append(cv)
            except tk.TclError:
                pass
        self._pills = alive

    def _pill_show(self, cv, on):
        if getattr(cv, "_hidden", None) is (not on):
            return
        cv._hidden = not on
        self._pills_key = None
        self.after_idle(self._layout_pills)

    # ----- nút thu tròn + thanh mức âm -----
    def _rec_btn_click(self):
        if self._rec_ctl.get("rec_enabled"):
            self._prac_record()

    def _draw_rec_btn(self):
        c, P = self.btn_prec, self.P
        d = self.px(72 if self._compact else 96)
        ring = self.px(6 if self._compact else 8)
        c.configure(width=d, height=d, bg=P["card"])
        c.delete("all")
        on = self._rec_ctl.get("rec_enabled", True)
        c.create_oval(0, 0, d - 1, d - 1, fill=P["rec_ring"] if on else P["track"], outline="")
        c.create_oval(ring, ring, d - 1 - ring, d - 1 - ring,
                      fill=P["rec"] if on else P["disabled"], outline="")
        s = int(d * 0.36)
        self._draw_icon(c, self._rec_ctl.get("rec_icon", "mic"),
                        "#FFFFFF" if on else P["disabled_fg"], s,
                        ox=(d - s) // 2, oy=(d - s) // 2, clear=False)
        c.configure(cursor="hand2" if on else "")

    def _draw_meter(self, level=0.0, c=None):
        c, P = c or self.p_meter, self.P
        c.delete("all")
        W, H, n = (self._meter_w() if c is self.p_meter else self.px(260)), self.px(10), 20
        if int(c.cget("width")) != W:
            c.configure(width=W)
        gap = max(1, self.px(3))
        cw = (W - gap * (n - 1)) / float(n)
        lit = meter_cells(level, n)
        for i in range(n):
            x = i * (cw + gap)
            c.create_rectangle(x, 0, x + cw, H, outline="",
                               fill=P["accent"] if i < lit else P["track"])

    def _update_mic_line(self):
        name = self.mic_var.get()
        if not name or name.startswith("("):
            self.p_mic_lbl.configure(text="Chưa có micro —")
        else:
            self.p_mic_lbl.configure(text="Micro: %s  ·" % short_mic_name(name))

    # ----- thanh công cụ: chế độ, bài trước/sau -----
    def _set_prac_mode(self, code):
        if self.p_working or self.recording or code == self.prac_mode.get():
            return
        self.prac_mode.set(code)
        self._prac_mode_changed()

    def _nav_labels(self):
        """Nút bài/đoạn trước–sau; cửa sổ hẹp chỉ còn mũi tên (thanh có 3 chế độ + ô bài/link)."""
        if self._compact:
            prev, nxt = "◀", "▶"
        elif self.prac_mode.get() != "yt":
            prev, nxt = "◀ Bài trước", "Bài sau ▶"
        else:
            prev, nxt = "◀ Đoạn trước", "Đoạn sau ▶"
        self.btn_pprev.configure(text=prev)
        self.btn_pnext.configure(text=nxt)

    def _step_lesson(self, d):
        if self.p_working or self.recording:
            return
        if self.prac_mode.get() == "yt":
            self._yt_step(d)
            return
        n = len(self.cb_prac["values"])
        if n:
            self.cb_prac.current((max(0, self.cb_prac.current()) + d) % n)
            self._refresh_practice()

    def _prac_body_resized(self, e=None):
        if e is not None:
            self._prac_body_w = e.width
        bw = getattr(self, "_prac_body_w", 0)
        if not bw:
            return
        yt = self.prac_mode.get() == "yt"
        w = side_width(bw, self.S, YT_SIDE_FRAC if yt else SIDE_FRAC)
        if abs(w - int(self.p_side.cget("width"))) > 2:
            self.p_side.configure(width=w)

    def _prac_compact(self, compact):
        self.cb_prac.configure(width=22 if compact else 30)
        self.yt_entry.configure(width=16 if compact else 34)
        self.yt_text.configure(font=(self.F, 13 if compact else 15))
        self._nav_labels()
        self._stage_resized()
        pad = self.px(20 if compact else 32)
        self._stage_in.pack_configure(padx=pad, pady=(self.px(16 if compact else 28),
                                                      self.px(12 if compact else 18)))
        self._draw_rec_btn()
        self._redraw_words()

    # ---------- panel chi tiết (phải): cuộn được, nút chính ghim ở đáy ----------
    def _scroll_area(self, parent, bg):
        outer = self._frame(parent, bg=bg)
        cv = self._tw(tk.Canvas(outer, bd=0, highlightthickness=0), bg=bg)
        sb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
        inner = self._frame(cv, bg=bg)
        win = cv.create_window(0, 0, window=inner, anchor="nw")

        def sync(_e=None):
            cv.configure(scrollregion=(0, 0, inner.winfo_reqwidth(), inner.winfo_reqheight()))
            need = inner.winfo_reqheight() > cv.winfo_height() + 1
            if need and not sb.winfo_manager():
                sb.pack(side="right", fill="y", before=cv)   # trước canvas: canvas đã chiếm hết bề ngang
            elif not need and sb.winfo_manager():
                sb.pack_forget()
                cv.yview_moveto(0)

        inner.bind("<Configure>", sync)
        cv.bind("<Configure>", lambda e: (cv.itemconfigure(win, width=e.width), sync()))
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        cv._scroll_sb = sb
        self._scrollers.append(cv)
        return outer, inner

    def _on_wheel(self, e):
        """Cuộn panel nằm dưới con trỏ (Text tự cuộn bằng binding riêng của nó)."""
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            if w in self._scrollers:
                if w._scroll_sb.winfo_manager():
                    w.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")
                return
            w = w.master

    def _build_side(self, side):
        self._scrollers = getattr(self, "_scrollers", [])
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        pad = self.px(24)
        # đáy ghim: tiến bộ + nút chính
        foot = self._frame(side, bg="side")
        foot.pack(side="bottom", fill="x", padx=pad, pady=(self.px(8), self.px(20)))
        prow = self._frame(foot, bg="side")
        prow.pack(fill="x", pady=(0, self.px(10)))
        self.p_spark = self._tw(tk.Canvas(prow, width=self.px(96), height=self.px(28), bd=0,
                                          highlightthickness=0), bg="side")
        self.p_prog = self._lbl(prow, "", bg="side", fg="muted", size=9, justify="left",
                                anchor="w")
        self.p_prog.pack(side="right", fill="x", expand=True)
        self._spark = []
        self._side_wraps = [(self.p_prog, self.px(110))]   # chừa chỗ cho đường xu hướng
        self._redraws.append(self._draw_spark)
        self.p_actions = self._frame(foot, bg="side")
        self.btn_pmain = ttk.Button(self.p_actions, text="Thử lại", style="Accent.TButton")
        self.btn_pmain.pack(side="left", fill="x", expand=True)
        self.p_sec = self._link_lbl(self.p_actions, "", lambda: None, bg="side", size=10)
        outer, inner = self._scroll_area(side, "side")
        outer.pack(fill="both", expand=True)
        body = self._frame(inner, bg="side")
        body.pack(fill="both", expand=True, padx=pad, pady=(pad, 0))
        self._side_body = body
        inner.bind("<Configure>", lambda e: self._side_wrap(e.width - 2 * pad), add="+")

        # chờ / hướng dẫn (idle, đang thu, đang chấm, lỗi)
        self.pp_wait = self._frame(body, bg="side")
        self.pp_wait_t = self._lbl(self.pp_wait, "", bg="side", size=15, weight="bold",
                                   justify="left", anchor="w")
        self.pp_wait_t.pack(fill="x", pady=(self.px(40), self.px(6)))
        self._wrap(self.pp_wait_t)
        self.pp_wait_s = self._lbl(self.pp_wait, "", bg="side", fg="muted", size=10,
                                   justify="left", anchor="w")
        self.pp_wait_s.pack(fill="x")
        self._wrap(self.pp_wait_s)
        self.pp_steps = self._frame(self.pp_wait, bg="side")
        for i, txt in enumerate(("Bấm “Nghe mẫu” để nghe câu chuẩn",
                                 "Bấm nút đỏ và đọc to câu",
                                 "Xem từ nào đúng, từ nào cần sửa"), 1):
            row = self._frame(self.pp_steps, bg="side")
            row.pack(fill="x", pady=(self.px(6), 0))
            self._lbl(row, str(i), bg="side", fg="accent_fg", size=10, weight="bold").pack(
                side="left", padx=(0, self.px(10)))
            self._wrap(self._lbl(row, txt, bg="side", size=10, justify="left", anchor="w"),
                       self.px(24)).pack(side="left", fill="x")
        self.pbar_p = ttk.Progressbar(self.pp_wait, mode="indeterminate", maximum=100)

        # đầu kết quả: vòng điểm + câu chính + tóm tắt
        self.pp_head = self._frame(body, bg="side")
        self.p_ring = self._tw(tk.Canvas(self.pp_head, width=self.px(64), height=self.px(64),
                                         bd=0, highlightthickness=0), bg="side")
        self.p_ring.pack(side="left", anchor="n", padx=(0, self.px(14)))
        info = self._frame(self.pp_head, bg="side")
        info.pack(side="left", fill="x", expand=True)
        self.p_headline = self._lbl(info, "", bg="side", size=15, weight="bold",
                                    justify="left", anchor="w")
        self.p_headline.pack(fill="x")
        self._wrap(self.p_headline, self.px(78))
        self.p_summary = self._lbl(info, "", bg="side", fg="muted", size=10, justify="left",
                                   anchor="w")
        self.p_summary.pack(fill="x", pady=(self.px(2), 0))
        self._wrap(self.p_summary, self.px(78))
        self.pp_heard = self._lbl(body, "", bg="side", fg="muted", size=9, justify="left",
                                  anchor="w")
        self._wrap(self.pp_heard)
        self.pp_fix = self._frame(body, bg="side")
        self._caps(self.pp_fix, "CẦN SỬA").pack(fill="x", pady=(0, self.px(4)))
        self.pp_fix_rows = self._frame(self.pp_fix, bg="side")
        self.pp_fix_rows.pack(fill="x")
        self.pp_notes = self._frame(body, bg="side")
        self.pp_unsure = self._frame(body, bg="side")
        self.pp_detail = self._frame(body, bg="side")
        self.pp_yt = self._frame(body, bg="side")      # danh sách khác biệt của đoạn đọc to

        # NGỮ ĐIỆU (S-5 / S-5b): một câu nhận xét · biểu đồ có nhãn từ · trọng âm · tốc độ
        self.p_int_card = self._frame(body, bg="side")
        self._caps(self.p_int_card, "NGỮ ĐIỆU").pack(fill="x")
        self.p_int_cap = self._wrap(self._lbl(self.p_int_card, "", bg="side", size=10,
                                              weight="bold", justify="left", anchor="w"))
        self.p_int_cap.pack(fill="x", pady=(self.px(4), self.px(6)))
        self.p_int = self._tw(tk.Canvas(self.p_int_card, height=self.px(118), bd=0,
                                        highlightthickness=0), bg="side")
        self.p_int.pack(fill="x")
        self.p_int.bind("<Configure>", lambda e: self._draw_intonation())
        self.p_int_stress = self._wrap(self._lbl(self.p_int_card, "", bg="side", size=9,
                                                 justify="left", anchor="w"))
        self.p_int_speed = self._wrap(self._lbl(self.p_int_card, "", bg="side", fg="muted",
                                                size=9, justify="left", anchor="w"))
        self._iv = None
        self._last_res = None
        self._redraws.append(self._draw_intonation)
        self._redraws.append(lambda: self._last_view is None or self._draw_ring(
            self._last_view["ring"]))
        self._panel_sections = []

    def _caps(self, parent, text):
        return self._lbl(parent, text, bg="side", fg="muted", size=8, weight="bold",
                         anchor="w")

    def _wrap(self, lb, margin=0):
        self._side_wraps.append((lb, margin))
        return lb

    def _side_wrap(self, width):
        alive = []
        for lb, m in self._side_wraps:
            try:
                lb.configure(wraplength=max(self.px(80), width - m))
                alive.append((lb, m))
            except tk.TclError:
                pass
        self._side_wraps = alive

    def _panel_show(self, names):
        order = (("wait", self.pp_wait), ("head", self.pp_head), ("heard", self.pp_heard),
                 ("unsure", self.pp_unsure), ("fix", self.pp_fix), ("notes", self.pp_notes),
                 ("inton", self.p_int_card), ("detail", self.pp_detail), ("yt", self.pp_yt))
        for _n, w in order:
            if w.winfo_manager():
                w.pack_forget()
        first = True
        for n, w in order:
            if n in names:
                w.pack(fill="x", pady=(0 if first else self.px(14), 0))
                first = False
        self._panel_sections = list(names)

    def _show_actions(self, primary=None, primary_cmd=None, secondary=None, secondary_cmd=None):
        if not primary:
            if self.p_actions.winfo_manager():
                self.p_actions.pack_forget()
            return
        self.btn_pmain.configure(text=primary, command=primary_cmd)
        if secondary:
            self.p_sec.configure(text=secondary)
            self.p_sec.bind("<Button-1>", lambda e: secondary_cmd())
            if not self.p_sec.winfo_manager():
                self.p_sec.pack(side="left", padx=(self.px(14), self.px(4)))
        elif self.p_sec.winfo_manager():
            self.p_sec.pack_forget()
        if not self.p_actions.winfo_manager():
            self.p_actions.pack(fill="x")

    def _panel_state(self, state):
        """Panel khi chưa có kết quả: hướng dẫn / đang nghe / đang chấm / lỗi."""
        if state in ("result", "unsure"):
            return
        t, s = {"idle": ("Kết quả sẽ hiện ở đây", ""),
                "recording": ("Đang nghe bạn đọc…", "Kết quả hiện ngay khi bạn đọc xong."),
                "scoring": ("Đang chấm…", "Máy đang nghe lại bản thu của bạn — vài giây."),
                "error": ("Chưa chấm được",
                          "Xem thông báo dưới nút thu âm, sửa rồi bấm Thu lại."),
                "loading": ("Đang lấy transcript…",
                            "Tải phụ đề và âm thanh gốc của video — vài giây đến nửa phút. "
                            "Esc để hủy.")}[state]
        self.pp_wait_t.configure(text=t)
        self.pp_wait_s.configure(text=s)
        if s and not self.pp_wait_s.winfo_manager():
            self.pp_wait_s.pack(fill="x", after=self.pp_wait_t)
        elif not s and self.pp_wait_s.winfo_manager():
            self.pp_wait_s.pack_forget()
        if state == "idle" and not self.pp_steps.winfo_manager():
            self.pp_steps.pack(fill="x", pady=(self.px(6), 0))
        elif state != "idle" and self.pp_steps.winfo_manager():
            self.pp_steps.pack_forget()
        if state in ("scoring", "loading"):
            if not self.pbar_p.winfo_manager():
                self.pbar_p.pack(fill="x", pady=(self.px(16), 0))
            self.pbar_p.start(12)
        elif self.pbar_p.winfo_manager():
            self.pbar_p.stop()
            self.pbar_p.pack_forget()
        self._panel_show(["wait"])
        self._show_actions(None)

    def _clear_prac_result(self, note=True):
        """Xóa kết quả/ngữ điệu của lần chấm trước — đổi bài (P-01), thu/chấm lại."""
        self.p_status.set("Chọn bài (hoặc âm), bấm Thu âm rồi đọc to, rõ.")
        self._destroy_embeds()
        self._last_view = None
        self._show_details = self._show_heard = False
        self._inton = None
        self._iv = None
        self._set_stage_words(stage_words(self._p_target, None))
        if self.prac_mode.get() == "yt":
            self._yt_fill_text(None)
        self._panel_state(getattr(self, "prac_state", "idle")
                          if getattr(self, "prac_state", "idle") not in ("result", "unsure")
                          else "idle")

    def _destroy_embeds(self):
        for w in getattr(self, "_embeds", []):
            try:
                w.destroy()
            except tk.TclError:
                pass
        self._embeds = []

    def _prac_mode_changed(self):
        yt = self.prac_mode.get() == "yt"
        self._yt_report_hide()
        if yt != bool(self.yt_bar.winfo_manager()):
            if yt:
                self.cb_prac.pack_forget()
                self.yt_bar.pack(side="left", before=self.p_pos)
            else:
                self.yt_bar.pack_forget()
                self.cb_prac.pack(side="left", before=self.p_pos)
        self.p_rec_hint.configure(text=YT_REC_HINT if yt else "Đọc xong, app tự dừng và chấm")
        self._nav_labels()
        if yt:
            if self.last_wav and not self._yt_kept_wav(self.last_wav):
                self._set_last_wav(None)        # bản thu bài câu không thuộc đoạn nào
            self._yt_refresh()
            return
        if self._yt_kept_wav(self.last_wav):
            self.last_wav = None                # giữ file cho đoạn YouTube, chỉ bỏ liên kết
        guide = self.prac_mode.get() == "guide"
        self.cb_prac.configure(values=GUIDE_NAMES if guide else SET_NAMES)
        try:
            self.cb_prac.current(0)
        except Exception:
            pass
        self._refresh_practice()

    def _refresh_practice(self):
        # đổi bài / chế độ -> kết quả cũ không còn đúng với câu mới (P-01, D-31: về idle)
        guide = self.prac_mode.get() == "guide"
        idx = self.cb_prac.current()
        ids = GUIDE_IDS if guide else SET_IDS
        idx = idx if 0 <= idx < len(ids) else 0
        sid = None
        if guide:
            g = GUIDES[GUIDE_IDS[idx]]
            target, hint, ipa = g["target"], "Đọc đúng câu trên, so khẩu hình với hướng dẫn.", ""
            tip, samples, custom = g["instruction"], g["samples"], False
        else:
            sid = SET_IDS[idx]
            s = PRACTICE_SETS[sid]
            target, hint, ipa = s["target"], s["hint"], s.get("ipa") or ""
            custom = sid == "custom"
            if custom:
                target = self.custom_text.get().strip()
                hint = "Gõ câu của bạn ở ô trên (Việt hoặc Anh)."
            tip = "\n".join("•  " + x for x in (s.get("tips") or []))
            samples = s.get("samples") or []
        self._p_target = target
        if not self.p_working:
            self._clear_prac_result()
            if getattr(self, "prac_state", "idle") in ("result", "unsure", "error"):
                self._set_prac_state("idle")
        self.p_pos.configure(text="Bài %d / %d" % (idx + 1, len(ids)))
        self.p_ipa.configure(text=ipa)
        self.p_hint.configure(text=hint)
        self.p_how.configure(text=tip)
        self._stage_repack(custom, ipa, hint, tip)
        self._fill_samples(samples)
        self._seg._draw()
        self._update_prog(sid)

    def _fill_samples(self, samples):
        for ch in self.p_samples.winfo_children():
            ch.destroy()
        for label, fname in samples:
            p = os.path.join(MAU_DIR, fname)
            pill = self._mk_pill(self.p_samples, "Nghe mẫu" if label == "Cả câu" else label,
                                 lambda p=p: self._play_sample(p), os.path.exists(p))
            self._pill_show(pill, True)
        self._mk_rec_pills()

    def _mk_rec_pills(self):
        """▶ Bản thu của bạn · Lưu bản thu · (Từ YouTube) Lưu cả N đoạn — hiện khi có bản thu."""
        self.btn_preplay = self._mk_pill(self.p_samples, "Bản thu của bạn", self._prac_replay)
        self.btn_psave = self._mk_pill(self.p_samples, "Lưu bản thu", self._save_recording,
                                       icon=False)
        self.btn_psaveall = self._mk_pill(self.p_samples, "Lưu cả các đoạn đã đọc",
                                          self._save_all, icon=False)
        self.btn_preport = self._mk_pill(self.p_samples, "Kết thúc · xem báo cáo",
                                         self._yt_finish, icon=False)
        self._sync_rec_pills()

    def _sync_rec_pills(self):
        """Hiện/ẩn + đổi chữ các nút bản thu theo trạng thái (đã lưu chưa — R1)."""
        if getattr(self, "btn_psave", None) is None:
            return
        busy = getattr(self, "prac_state", "idle") in ("recording", "scoring", "loading")
        has = bool(self.last_wav and os.path.exists(self.last_wav))
        self._pill_show(self.btn_preplay, has and not busy)
        self._pill_set_text(self.btn_psave, "Đã lưu ✓" if self.last_wav in self._saved
                            else "Lưu bản thu")
        self._pill_show(self.btn_psave, has and not busy)
        kept = [k["wav"] for k in self._yt_keep.values()
                if k.get("wav") and os.path.exists(k["wav"])] \
            if self.prac_mode.get() == "yt" else []
        self._pill_set_text(self.btn_psaveall, ("Đã lưu cả %d đoạn ✓" if all(
            w in self._saved for w in kept) else "Lưu cả %d đoạn đã đọc") % len(kept))
        self._pill_show(self.btn_psaveall, len(kept) >= 2 and not busy)
        s = self._yt_sess if self.prac_mode.get() == "yt" else None
        scored = [k for k in self._yt_keep.values() if k.get("res")] if s else []
        self._pill_set_text(self.btn_preport, "Kết thúc · xem báo cáo (%d/%d đoạn)" % (
            len(scored), len(s.paragraphs)) if s else "Kết thúc · xem báo cáo")
        self._pill_show(self.btn_preport, bool(scored) and not busy)

    def _play_sample(self, path):
        if self.playing:
            return
        self.playing = True

        def job():
            try:
                play_wav_file(path)
            except Exception as e:
                self._queue.put(("prac_status", f"Không phát được âm mẫu: {e}"))
            finally:
                self.playing = False

        threading.Thread(target=job, daemon=True).start()

    # ---------- ngữ điệu (cao độ) ----------
    def _show_intonation(self, d):
        """Ngữ điệu nằm trong panel kết quả; chỉ hiện khi có kết quả chắc chắn (D-29)."""
        self._inton = d or None
        if self._last_view:
            self._render_result(self._last_view)

    def _inton_text(self, d):
        def slope(v):
            if v is None:
                return "không đủ dữ liệu"
            if abs(v) < 0.35:
                return "gần như đi ngang"
            return ("xuống %.1f st" if v < 0 else "lên %.1f st") % abs(v)

        parts = ["Nét đứt = mẫu (%.2fs) · nét liền = bạn (%.2fs)."
                 % (d.get("dur_ref", 0), d.get("dur_usr", 0)),
                 "Cuối câu: mẫu %s · bạn %s."
                 % (slope(d.get("final_ref")), slope(d.get("final_usr")))]
        if d.get("range_ref") is not None and d.get("range_usr") is not None:
            parts.append("Khoảng cao độ: mẫu %.1f st · bạn %.1f st."
                         % (d["range_ref"], d["range_usr"]))
        if d.get("diff") is not None:
            parts.append("Độ lệch đường cong: %.1f st (căn thời gian tự động — "
                         "chỉ để tham khảo)." % d["diff"])
        return "  ".join(parts)

    def _fill_inton(self, v):
        """Chữ quanh biểu đồ: câu nhận xét (màu theo ✓/!), trọng âm, tốc độ, chi tiết số."""
        P = self.P
        iv = self._iv = inton_view(self._last_res or {"inton": self._inton}, v)
        if not iv:
            return
        self.p_int_cap.configure(text=iv["caption"],
                                 fg={"ok": P["ok_fg"], "warn": P["warn_fg"]}.get(
                                     iv["tone"], P["muted"]))
        for w in (self.p_int_stress, self.p_int_speed):
            w.pack_forget()
        pad = (self.px(6), 0)
        if iv["stress"]:
            self.p_int_stress.configure(text=iv["stress"])
            self.p_int_stress.pack(fill="x", pady=pad)
        if iv["speed"]:
            self.p_int_speed.configure(text=iv["speed"])
            self.p_int_speed.pack(fill="x", pady=pad)
        self.after(60, self._draw_intonation)

    def _draw_intonation(self):
        """Hai đường cao độ (bán cung so trung vị mỗi người, I5) trên trục thời gian 0..100 %.

        Không trục số (C-03): chỉ vạch giữa + "cao"/"thấp"; chú thích trong biểu đồ (C-04);
        nhãn từ theo mốc của bạn, dải nhạt ở từ cần sửa (C-01); chấm trên nhãn = từ được
        nhấn (đặc = bạn, vòng nét đứt = mẫu, S-5b). Chỉ mô tả, không chấm (D-10, D-34).
        """
        c = self.p_int
        c.delete("all")
        d = self._inton
        if not d:
            return
        W, H = c.winfo_width(), c.winfo_height()
        if W < self.px(160) or H < self.px(60):
            return
        P = self.P
        c.configure(bg=P["side"])
        iv = self._iv or {"labels": []}
        labels = iv.get("labels") or []
        f8 = (self.F, 8)
        ml, mr = self.px(28), self.px(4)
        mt = self.px(16)                            # dải chú thích phía trên
        mb = self.px(34) if labels else self.px(8)  # chấm trọng âm + nhãn từ phía dưới
        x0, x1, y0, y1 = ml, W - mr, mt, H - mb
        if x1 - x0 < 10 or y1 - y0 < 10:
            return
        vals = [v for k in ("ref", "usr") for v in (d.get(k) or {}).get("st", [])
                if v is not None]
        if not vals:
            return
        lim = max(6, min(18, int(math.ceil(max(abs(v) for v in vals) / 3.0)) * 3))

        def X(t):
            return x0 + max(0.0, min(1.0, t)) * (x1 - x0)

        def Y(v):
            return y0 + (lim - v) / (2.0 * lim) * (y1 - y0)

        for lb in labels:                           # dải nhạt ở từ cần sửa
            if lb["err"]:
                c.create_rectangle(X(lb["x0"]), y0, X(lb["x1"]), y1, fill=P["band"],
                                   outline="")
        c.create_line(x0, Y(0), x1, Y(0), fill=P["border"])
        c.create_text(x0 - self.px(4), y0, text="cao", anchor="ne", fill=P["muted"], font=f8)
        c.create_text(x0 - self.px(4), y1, text="thấp", anchor="se", fill=P["muted"], font=f8)
        for key, color, width, dash in (("ref", P["muted"], 2, (self.px(5), self.px(4))),
                                        ("usr", P["accent"], 3, ())):
            data = d.get(key) or {}
            pts = []
            for t, st in zip(data.get("t") or [], data.get("st") or []):
                if st is None:
                    if len(pts) >= 4:
                        c.create_line(*pts, fill=color, width=self.px(width), dash=dash)
                    pts = []
                else:
                    pts.extend((X(t), Y(st)))
            if len(pts) >= 4:
                c.create_line(*pts, fill=color, width=self.px(width), dash=dash)
        # chú thích trong biểu đồ: nét đứt = Mẫu, nét liền = Bạn
        ly, xr = self.px(6), x1
        for text, color, width, dash in (("Bạn", P["accent"], 3, ()),
                                         ("Mẫu", P["muted"], 2, (self.px(4), self.px(3)))):
            tid = c.create_text(xr, ly, text=text, anchor="e", fill=P["muted"], font=f8)
            bx = c.bbox(tid)[0] - self.px(4)
            c.create_line(bx - self.px(18), ly, bx, ly, fill=color, width=self.px(width),
                          dash=dash)
            xr = bx - self.px(28)
        # nhãn từ + chấm trọng âm
        r = self.px(3)
        for lb in labels:
            xm = (X(lb["x0"]) + X(lb["x1"])) / 2.0
            c.create_text(xm, H - self.px(2), text=lb["text"], anchor="s",
                          fill=P["fg"] if lb["err"] else P["muted"], font=f8)
            dy = y1 + self.px(10)
            if lb["sr"]:
                c.create_oval(xm - r - self.px(2), dy - r - self.px(2), xm + r + self.px(2),
                              dy + r + self.px(2), outline=P["muted"], dash=(2, 2))
            if lb["su"]:
                c.create_oval(xm - r, dy - r, xm + r, dy + r, fill=P["accent"], outline="")

    # ---------- lịch sử luyện (tiến bộ) ----------
    def _load_hist(self):
        try:
            with open(HISTORY_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_hist(self):
        try:
            tmp = HISTORY_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.hist, f, ensure_ascii=False, indent=1)
            os.replace(tmp, HISTORY_PATH)
        except Exception:
            pass

    def _update_prog(self, sid):
        if not sid or sid == "custom":
            self.p_prog.configure(text="")
            self._spark = []
            self._draw_spark()
            return
        lang = PRACTICE_SETS.get(sid, {}).get("lang")
        ps = progress_summary(self.hist.get(sid), hist_weakest(self.hist, lang), lang)
        self.p_prog.configure(text=ps["line1"] + ("\n" + ps["line2"] if ps["line2"] else ""))
        self._spark = ps["spark"]
        self._draw_spark()

    def _draw_spark(self):
        """Đường xu hướng đúng/tổng của ≤ 10 lần gần nhất (S-7); ẩn khi < 2 lần."""
        c, P = self.p_spark, self.P
        pts = self._spark
        if len(pts) < 2:
            if c.winfo_manager():
                c.pack_forget()
            return
        if not c.winfo_manager():
            c.pack(side="left", padx=(0, self.px(12)), before=self.p_prog)
        c.delete("all")
        W, H, m = self.px(96), self.px(28), self.px(4)
        xs = [m + i * (W - 2 * m) / float(len(pts) - 1) for i in range(len(pts))]
        ys = [H - m - v * (H - 2 * m) for v in pts]
        c.create_line(*[v for xy in zip(xs, ys) for v in xy], fill=P["accent"],
                      width=self.px(2.5), joinstyle="round")
        c.create_oval(xs[-1] - m, ys[-1] - m, xs[-1] + m, ys[-1] + m, fill=P["accent"],
                      outline="")

    def _record_hist(self, sid, res, view=None):
        if not sid or sid == "custom":
            return
        if view is None:
            view = build_result_view(res, PRACTICE_SETS.get(sid))
        hist_add_try(self.hist, sid, view, time.strftime("%Y-%m-%d %H:%M"))
        self._save_hist()

    def _current_set_id(self):
        if self.prac_mode.get() != "set":
            return None
        idx = self.cb_prac.current()
        return SET_IDS[idx] if 0 <= idx < len(SET_IDS) else None

    def _current_practice(self):
        guide = self.prac_mode.get() == "guide"
        idx = self.cb_prac.current()
        if guide:
            idx = idx if 0 <= idx < len(GUIDE_IDS) else 0
            g = GUIDES[GUIDE_IDS[idx]]
            return g["target"], g["lang"]
        idx = idx if 0 <= idx < len(SET_IDS) else 0
        sid = SET_IDS[idx]
        if sid == "custom":
            return self.custom_text.get().strip(), "auto"
        s = PRACTICE_SETS[sid]
        return s["target"], s["lang"]

    def _prac_record(self):
        if self.p_working or self.busy:
            return
        if self.recording:
            if self.rec_owner == "prac":
                self._prac_stop_and_score()
            else:
                self.p_status.set("Đang ghi âm ở tab Chuyển thành văn bản — dừng ở đó "
                                  "trước (hoặc Esc) rồi mới thu bài luyện.")
        else:
            self._prac_start()

    def _prac_start(self):
        if self.prac_mode.get() == "yt":
            self._yt_start()
            return
        target, _lang = self._current_practice()
        if not target:
            messagebox.showwarning("Chưa có câu",
                                   "Hãy chọn bài hoặc gõ câu cần đọc vào ô Tùy chỉnh.")
            return
        if self._mic_probing:
            self.p_status.set("Đang dò micro — chờ vài giây rồi bấm Thu âm & chấm.")
            return
        dev, name, rate = self._resolve_mic()
        if dev is None:
            return
        self._set_prac_state("recording")
        self._clear_prac_result(note=False)
        self.recorder.start(dev, rate, REC_MAX_SEC,
                            lambda reason: self._queue.put(("prac_autostop", reason)),
                            lambda m: self._queue.put(("prac_error", m)),
                            auto_stop={"silence": PRAC_SILENCE_SEC, "min_speech": 0.4,
                                       "start_timeout": 7.0})
        self.p_status.set(
            f"● ĐANG THU bằng {name}. Đọc câu trên — đọc xong app tự dừng, "
            f"hoặc bấm ■ Dừng & chấm.")
        self.lbl_plevel.configure(text="● Đang thu · 00:00 · mời bạn đọc…")
        self._prac_tick()

    def _prac_tick(self):
        if not self.recording:
            return
        el = int(time.time() - self.recorder.t0)
        if self.recorder.speech_seen:
            hint = "đã nghe giọng · đọc xong app tự dừng"
        elif el >= 3:
            hint = "chưa nghe thấy giọng — nói to / gần mic hơn"
        else:
            hint = "mời bạn đọc…"
        self.lbl_plevel.configure(text=f"● Đang thu · {el // 60:02d}:{el % 60:02d} · {hint}")
        self._draw_meter(self.recorder.level)
        self.after(120, self._prac_tick)

    def _set_last_wav(self, path):
        """Đổi bản ghi để Nghe lại; xóa bản cũ (file tạm luyen_*) để không rò rỉ (I10)."""
        old = self.last_wav
        if old and old != path:
            remove_temp(old)
        self.last_wav = path

    def _prac_stop_and_score(self, reason=None):
        if not self.recording or self.rec_owner != "prac":
            return
        frames, rate = self._stop_recorder()
        if reason == "nospeech":
            self.p_status.set("Không nghe thấy giọng nói — mic gần như im lặng "
                              "(có thể đang bị tắt tiếng). Chưa chấm điểm.")
            self._find_mic_auto(show_dialog=True)
            return
        if not frames:
            self.p_status.set("Chưa thu được gì — thử lại.")
            return
        path, secs, info = save_frames_wav(frames, "luyen_", rate)
        self._set_last_wav(path)
        self._sync_rec_pills()
        peak0 = float(info.get("peak0", 0.0) or 0.0)
        if peak0 < MIC_MIN_PEAK:
            # Gần như im lặng: KHÔNG đưa cho Whisper (dễ bịa ra câu lặp vô nghĩa).
            self.p_status.set(
                "Bản thu gần như im lặng (đỉnh vào %.2f%%) — chưa chấm điểm. "
                "Tăng Microphone Level trong Windows hoặc để mic gần hơn."
                % (peak0 * 100))
            self._find_mic_auto(show_dialog=True)
            return
        info["dropped"] = self.recorder.dropped
        self.p_status.set(quality_note(info))
        if secs < 0.5:
            self.p_status.set("Bản thu quá ngắn (<0.5s) — thử lại, đọc to hơn.")
            return
        self._prac_score(path)

    def _mic_help_text(self):
        return ("Mic gần như chỉ thu được im lặng (mức tín hiệu ~0).\n\n"
                "Cách sửa:\n"
                "• Bỏ tắt tiếng micro: nhấn phím tắt mute trên bàn phím/tai nghe "
                "(nếu có).\n"
                "• Windows: Settings → System → Sound → Input — chọn đúng micro, "
                "kéo Volume lên 100%, bật Microphone Boost nếu có, bỏ Mute.\n"
                "• Hoặc chọn micro khác ở ô Micro rồi bấm Kiểm tra. Mic ngoài (USB, "
                "tai nghe bluetooth) phải được Windows nhận trước: bấm “Quét lại”, "
                "và với tai nghe bluetooth hãy bật profile Hands-Free (xem gợi ý "
                "dưới ô Micro).\n\n"
                "Lưu ý: micro loại [Windows WDM-KS] không thu được trong app — "
                "hãy chọn bản cùng tên ở [Windows WASAPI], [Windows DirectSound] "
                "hoặc [MME].\n\n"
                "App đang tự dò các micro khác trên máy để tìm cái có tín hiệu.")

    def _find_mic_auto(self, show_dialog=False):
        """Dò các micro, chọn cái có tín hiệu nhất (chạy nền)."""
        if show_dialog:
            messagebox.showwarning("Mic im lặng", self._mic_help_text())
        if self._mic_probing:
            return
        self._mic_probing = True
        self.p_status.set("Đang dò các micro để tìm cái có tín hiệu…")

        def job():
            try:
                best = best_input_mic(1.0)
            except Exception:
                best = None
            self._queue.put(("mic_found", best))

        threading.Thread(target=job, daemon=True).start()
        self.after(20000, self._mic_probe_timeout)

    def _mic_probe_timeout(self):
        self._mic_probing = False

    def _prac_replay(self):
        if not self.last_wav or not os.path.exists(self.last_wav) or self.playing:
            return
        self.playing = True

        def job():
            try:
                play_wav_file(self.last_wav)
            except Exception as e:
                self._queue.put(("prac_status", f"Không phát lại được: {e}"))
            finally:
                self.playing = False

        threading.Thread(target=job, daemon=True).start()

    def _stop_play(self):
        self._yt_listening = False
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self.playing = False

    def _prac_from_file(self):
        if self.p_working or self.recording:
            return
        p = filedialog.askopenfilename(title="Chọn file bài đọc", filetypes=SUPPORTED)
        if not p:
            return
        self._set_last_wav(None)  # bỏ bản ghi tạm cũ; file người dùng chọn không gán vào last_wav
        self._prac_score(p)

    def _prac_score(self, wav_path):
        if self.prac_mode.get() == "yt":
            self._yt_score(wav_path)
            return
        target, lang = self._current_practice()
        if not target:
            messagebox.showwarning("Chưa có câu", "Bài đọc đang trống.")
            return
        self._set_prac_state("scoring")
        self._clear_prac_result(note=False)
        ref_wav, ref_words = None, None
        sid = self._current_set_id()
        if sid and sid != "custom":
            samples = PRACTICE_SETS.get(sid, {}).get("samples") or []
            if samples:
                cand = os.path.join(MAU_DIR, samples[0][1])
                if os.path.exists(cand):
                    ref_wav = cand
                    ref_words = self.sample_times.get(sid)
        threading.Thread(target=self._w_prac,
                         args=(wav_path, self.model_name.get(), lang, target, ref_wav,
                               ref_words),
                         daemon=True).start()

    def _w_prac(self, wav_path, model_size, lang, target, ref_wav=None, ref_words=None):
        try:
            pk = wav_peak(wav_path)
            if pk < MIC_MIN_PEAK:
                self._queue.put(("prac_error",
                                 "File gần như im lặng (đỉnh %.2f%%) — không chấm điểm. "
                                 "Hãy chọn file khác." % (pk * 100)))
                return
            # câu tự gõ (lang "auto"): lấy ngôn ngữ từ chữ của câu mẫu thay vì để Whisper dò
            asr_lang = lang if lang != "auto" else (guess_lang(target) or "auto")
            model_size, upgraded = practice_model(model_size, asr_lang)
            self._queue.put(("prac_status",
                             "Đang nghe lại bài đọc của bạn (bài tiếng Việt: model small "
                             "nghe tiếng Việt rõ hơn)…" if upgraded
                             else "Đang nghe lại bài đọc của bạn…"))
            model = load_model(model_size)
            asr = transcribe_practice(model, wav_path, asr_lang)
            _info, probs, words_t = asr["info"], asr["probs"], asr["words_t"]
            hyp = asr["hyp"]
            if not hyp:
                self._queue.put(("prac_error",
                                 "Không nghe được chữ nào — thử đọc to, gần mic hơn."))
                return
            res = score_pronunciation(target, hyp, lang)
            res["target"] = target
            res["words_t"] = words_t
            res["model"] = model_size
            res["det_lang"] = (getattr(_info, "language", None) or lang or "auto")
            res["conf"] = (sum(probs) / len(probs)) if probs else 1.0
            res["low_conf"] = bool(probs) and res["conf"] < 0.35
            # Dấu hiệu Whisper "bịa" (câu lặp rất dài so với câu mẫu):
            hw_n = len(res.get("hyp", "").split())
            tw_n = len(target.split())
            res["garbage"] = bool(hw_n >= 8 and hw_n >= 2 * tw_n
                                  and res["score"] < 35)
            pairs = [(i, tw, hw) for i, (tw, st, hw, _n) in enumerate(res["items"])
                     if st != "ok" and tw and hw]
            if res.get("det_lang") == "en" and pairs:
                res["phon"] = pron_en.analyze_pairs(pairs)
            else:
                res["phon"] = {"issues": [], "counts": {}, "top": [],
                               "by_phoneme": {}, "unknown": []}
            res["inton"] = None
            res["stress"] = None
            if ref_wav:
                try:
                    res["inton"] = prosody.compare(ref_wav, wav_path)
                except Exception:
                    res["inton"] = None
                # trọng âm từng từ của bạn và của mẫu — chỉ mô tả (S-5b, D-34)
                try:
                    res["stress"] = {
                        "usr": prosody.word_stress(wav_path, words_t),
                        "ref": prosody.word_stress(ref_wav, ref_words) if ref_words else None,
                        "ref_words": ref_words or []}
                except Exception:
                    res["stress"] = None
            res["gop"] = None
            if (lang == "en" or res.get("det_lang") == "en") and gop.available():
                try:
                    self._queue.put(("prac_status",
                                     "Đang chấm âm vị (GOP)… lần đầu sẽ lâu hơn "
                                     "(nạp model)."))
                    tw = [w for w in re.split(r"\s+", target.strip()) if w]
                    res["gop"] = gop.score(wav_path, tw, ref_wav=ref_wav)
                except Exception:
                    res["gop"] = None
            self._queue.put(("prac_done", res))
        except Exception as e:
            self._queue.put(("prac_error", str(e)))

    def _prac_done(self, res):
        sid = self._current_set_id()
        lesson = PRACTICE_SETS.get(sid) if sid and sid != "custom" else None
        v = build_result_view(res, lesson)
        self._set_prac_state(v["state"])
        self.p_status.set("")
        self._last_words_t = res.get("words_t") or []
        self._last_res = res
        self._show_details = self._show_heard = False
        self._inton = res.get("inton") if v["state"] == "result" else None
        self._render_result(v)

        self._record_hist(sid, res, v)
        self._update_prog(sid)

    # ---------- kết quả luyện (S-2, B3/B4a): chỉ VẼ view của build_result_view ----------
    def _render_result(self, v):
        """Câu trên sân khấu tô theo từng từ; panel phải: vòng điểm, CẦN SỬA, ngữ điệu."""
        self._last_view = v
        self._destroy_embeds()
        self._set_stage_words(stage_words(v["target"], v))
        self._draw_ring(v["ring"])
        self.p_headline.configure(text=v["headline"])
        self.p_summary.configure(text=v["summary"],
                                 font=(FONT_IPA if has_ipa(v["summary"]) else self.F, 10))
        sections = ["head"]
        heard = v["status_line"]
        if v["extras"] and v["state"] == "result":   # D-29: chữ "nghe thêm" khi không chắc là chữ bịa
            more = v["extras_total"] - 3
            heard += ("\n" if heard else "") + "Đọc thêm: " + ", ".join(
                "“%s”" % w for w in v["extras"][:3]) + (" … +%d từ" % more if more > 0 else "")
        if heard:
            self.pp_heard.configure(text=heard)
            sections.append("heard")

        if v["state"] == "unsure":
            # D-29: không số, không tô màu câu, không đổ lỗi cho người học
            box = self._frame(self.pp_unsure, bg="info_bg")
            box.pack(fill="x")
            self._embeds.append(box)
            self._lbl(box, "Thử lại như sau", bg="info_bg", fg="accent_fg", size=10,
                      weight="bold").pack(anchor="w", padx=self.px(14), pady=(self.px(10), 0))
            for tip in v["tips"]:
                self._wrap(self._lbl(box, "•  " + tip, bg="info_bg", size=10, justify="left",
                                     anchor="w"), self.px(28)).pack(
                    fill="x", padx=self.px(14), pady=(self.px(3), 0))
            tk.Frame(box, height=self.px(10), bd=0, highlightthickness=0,
                     bg=self.P["info_bg"]).pack()
            tog = self._link_lbl(self.pp_unsure, "Máy nghe được gì? " +
                                 ("▾" if self._show_heard else "▸"), self._toggle_heard,
                                 bg="side", size=9)
            tog.pack(anchor="w", pady=(self.px(10), 0))
            self._embeds.append(tog)
            if self._show_heard:
                txt = "“%s”" % v["heard_text"] + ("\n" + v["heard_note"] if v["heard_note"]
                                                   else "")
                lb = self._wrap(self._lbl(self.pp_unsure, txt, bg="side", fg="muted", size=9,
                                          justify="left", anchor="w"))
                lb.pack(fill="x", pady=(self.px(4), 0))
                self._embeds.append(lb)
            sections.append("unsure")
            self._show_actions("Thử lại", self._prac_record, "Kiểm tra micro",
                               lambda: self._show_screen("set"))
        else:
            if v["cards"]:
                for card in v["cards"]:
                    self._mk_fix(self.pp_fix_rows, card)
                if v["cards_more"]:
                    lb = self._lbl(self.pp_fix_rows, "… và %d lỗi khác" % v["cards_more"],
                                   bg="side", fg="muted", size=9, anchor="w")
                    lb.pack(fill="x", pady=(self.px(8), 0))
                    self._embeds.append(lb)
                sections.append("fix")
            notes = ["•  " + n for n in v["notes"][:6]]
            if v["is_en"] and not v["cards"] and not v["perfect"] and v["score"] < 95:
                notes.append("Chưa đủ dữ liệu để kết luận âm vị — đọc to và rõ hơn.")
            if not v["is_en"] and v["correct"] == 0 and not v["cards"]:
                notes.append("Nghe lại câu mẫu rồi đọc chậm, rõ hơn" + (
                    "." if v.get("model") in ("small", "medium") else
                    "; nếu bản ghi nghe rõ mà vẫn sai, thử model “small”."))
            if v["low_conf"]:
                notes.append("Máy nghe chưa chắc (tín hiệu yếu/nhiễu) — phần âm vị chỉ để "
                             "tham khảo.")
            sid = self._current_set_id()
            if not self._inton and PRACTICE_SETS.get(sid or "", {}).get("lang") == "vi":
                notes.append("Biểu đồ ngữ điệu sẽ có cho bài tiếng Việt khi có bản ghi mẫu "
                             "người thật.")
            for n in notes:
                lb = self._wrap(self._lbl(self.pp_notes, n, bg="side", size=9, justify="left",
                                          anchor="w", fg="fg" if n.startswith("•") else "muted"))
                lb.pack(fill="x", pady=(0, self.px(4)))
                self._embeds.append(lb)
            if notes:
                sections.append("notes")
            if self._inton:
                sections.append("inton")
            if v["has_gop"] or self._inton:
                # Q-03: mọi con số (GOP, bán cung, độ lệch) chỉ nằm trong MỘT mục "Chi tiết số
                # đo"; mặc định là chữ (I7, S-5)
                tog = self._link_lbl(self.pp_detail, "Chi tiết số đo " +
                                     ("▾" if self._show_details else "▸"), self._toggle_details,
                                     bg="side", size=9)
                tog.pack(anchor="w")
                self._embeds.append(tog)
                if self._show_details:
                    lines = []
                    if v["has_gop"]:
                        lines = ["%s:  %s" % (c["title"], c["detail"]) for c in v["cards"]
                                 if c.get("detail")]
                        lines.append(
                            "Điểm GOP 0–100 do mô hình âm học chấm, so với bản mẫu cùng câu"
                            " — không phải phần trăm phát âm đúng." if v["gop_has_ref"] else
                            "Điểm GOP 0–100 do mô hình âm học chấm (ngưỡng tuyệt đối vì "
                            "không có bản mẫu) — không phải phần trăm phát âm đúng.")
                    if self._inton:
                        lines.append("Ngữ điệu — " + self._inton_text(self._inton))
                    for ln in lines:
                        lb = self._wrap(self._lbl(self.pp_detail, ln, bg="side", fg="muted",
                                                  font=(FONT_IPA, 9), justify="left",
                                                  anchor="w"))
                        lb.pack(fill="x", pady=(self.px(4), 0))
                        self._embeds.append(lb)
                sections.append("detail")
            if v["perfect"]:
                self._show_actions("Bài tiếp theo →", lambda: self._step_lesson(1),
                                   "Thử lại", self._prac_record)
            else:
                self._show_actions("Thử lại", self._prac_record)
        self._panel_show(sections)
        if self._inton:
            self._fill_inton(v)
        self._side_wrap(self._side_body.winfo_width())

    def _mk_fix(self, parent, card):
        """Một mục CẦN SỬA: chấm màu · tiêu đề · mức · ▶ Mẫu / ▶ Bạn đọc (cùng hàng) · mẹo."""
        P = self.P
        row = self._frame(parent, bg="side")
        row.pack(fill="x", pady=(self.px(8), 0))
        self._embeds.append(row)
        s = self.px(10)
        dot = self._tw(tk.Canvas(row, width=s, height=s, bd=0, highlightthickness=0), bg="side")
        dot.create_oval(0, 0, s, s, outline="",
                        fill=P["bad_line"] if card["kind"] == "bad" else P["warn_line"])
        dot.pack(side="left", anchor="n", padx=(0, self.px(12)), pady=(self.px(5), 0))
        col = self._frame(row, bg="side")
        col.pack(side="left", fill="x", expand=True)
        # hàng đầu: tiêu đề · mức (trái) — ▶ Mẫu / ▶ Bạn đọc (phải): gọn một dòng mỗi lỗi
        top = self._frame(col, bg="side")
        top.pack(fill="x")
        links = self._frame(top, bg="side")
        sample = os.path.join(MAU_DIR, card["sample"]) if card.get("sample") else None
        if card.get("heard") and self._heard_span(card["heard"]):
            self._link_lbl(links, "▶ Bạn đọc", lambda h=card["heard"]: self._play_heard(h),
                           bg="side", size=9).pack(side="right", padx=(self.px(12), 0))
        if sample and os.path.exists(sample):
            self._link_lbl(links, "▶ Mẫu", lambda p=sample: self._play_sample(p),
                           bg="side", size=9).pack(side="right", padx=(self.px(12), 0))
        links.pack(side="right", anchor="n", pady=(self.px(1), 0))
        title = self._lbl(top, card["title"], bg="side", size=10, weight="bold",
                          font=(FONT_IPA, 10, "bold") if card.get("ipa") else None,
                          justify="left", anchor="w")
        title.pack(side="left", anchor="n")
        self._wrap(title, self.px(150))
        self._lbl(top, "· " + card["level"], bg="side", fg="muted", size=9,
                  font=(FONT_IPA, 9) if has_ipa(card["level"]) else None).pack(
            side="left", anchor="n", padx=(self.px(6), 0), pady=(self.px(1), 0))
        if card.get("tip"):
            self._wrap(self._lbl(col, card["tip"], bg="side", size=10, justify="left", anchor="w",
                                 font=(FONT_IPA, 10) if has_ipa(card["tip"]) else None),
                       self.px(22)).pack(fill="x", pady=(self.px(2), 0))
        return row

    def _toggle_details(self):
        self._show_details = not self._show_details
        if self._last_view:
            self._render_result(self._last_view)

    def _toggle_heard(self):
        self._show_heard = not self._show_heard
        if self._last_view:
            self._render_result(self._last_view)

    def _draw_ring(self, ring):
        c, P, s = self.p_ring, self.P, self.px(64)
        c.configure(bg=P["side"])
        c.delete("all")
        w = self.px(7)
        pad = w / 2.0 + 1
        c.create_oval(pad, pad, s - pad, s - pad, outline=P["track"], width=w)
        color = {"ok": P["ring_ok"], "warn": P["ring_warn"], "bad": P["ring_bad"]}.get(
            ring["tone"], P["muted"])
        if ring["frac"] > 0:
            c.create_arc(pad, pad, s - pad, s - pad, start=90,
                         extent=-359.9 * min(1.0, ring["frac"]), style="arc",
                         outline=color, width=w)
        c.create_text(s / 2.0, s / 2.0, text=ring["text"], fill=P["fg"],
                      font=(self.F, 12 if len(ring["text"]) <= 4 else 10, "bold"))

    def _heard_span(self, word):
        """Mốc (bắt đầu, kết thúc) của từ máy nghe trong bản thu luyện — None nếu không có."""
        if not self.last_wav or not os.path.exists(self.last_wav):
            return None
        key = " ".join(norm_words(word))
        for w in self._last_words_t:
            if " ".join(norm_words(w["w"])) == key:
                return w["s"], w["e"]
        return None

    def _play_heard(self, word):
        span = self._heard_span(word)
        if not span or self.playing:
            return
        self.playing = True
        path = self.last_wav

        def job():
            try:
                play_wav_segment(path, *span)
            except Exception as e:
                self._queue.put(("prac_status", f"Không phát được: {e}"))
            finally:
                self.playing = False

        threading.Thread(target=job, daemon=True).start()

    def _prac_error(self, err):
        if self.rec_owner == "prac":
            # lỗi mở micro khi đang thu bài luyện; lỗi chấm điểm thì không đụng
            # tới bản thu đang chạy ở tab 1
            self._stop_recorder()
        self._set_prac_state("error")
        msg = str(err)
        self.p_status.set(msg if len(msg) < 300
                          else "Lỗi — xem chi tiết trong hộp thoại.")
        messagebox.showerror("Lỗi", msg)

    def _save_bundle(self, stem, wav, target, res, yt_idx=None):
        """Ghi một bộ bản thu: stem.wav + stem.txt (dòng 1 = câu/đoạn mẫu, định dạng
        `asr_bench --dir`) + stem.json (lời máy nghe, mốc từ) [+ stem_goc.wav: đoạn gốc YouTube].
        Trả danh sách tên file đã ghi."""
        shutil.copyfile(wav, stem + ".wav")
        with open(stem + ".txt", "w", encoding="utf-8") as f:
            f.write(target.strip() + "\n")
        files = [stem + ".wav", stem + ".txt"]
        info = {"app": "Oriole %s" % VERSION, "saved": time.strftime("%Y-%m-%d %H:%M"),
                "target": target, "hyp": (res or {}).get("hyp"),
                "items": (res or {}).get("items"), "words_t": (res or {}).get("words_t"),
                "model": (res or {}).get("model")}
        s = self._yt_sess
        if yt_idx is not None and s and s.wav:
            p = s.paragraphs[yt_idx]
            a = max(0.0, p["start"] - YTREAD_PAD_SEC)
            with wave.open(s.wav, "rb") as r, wave.open(stem + "_goc.wav", "wb") as w:
                i0, i1 = wav_segment_bounds(r.getnframes(), r.getframerate(),
                                            p["start"], p["end"], pad=YTREAD_PAD_SEC)
                r.setpos(i0)
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(r.getframerate())
                w.writeframes(r.readframes(i1 - i0))
            files.append(stem + "_goc.wav")
            info.update(url=s.url, title=s.title, sub_kind=s.sub_kind, paragraph=yt_idx + 1,
                        start=p["start"], end=p["end"], orig_hyp=s._orig.get(yt_idx),
                        # mốc từ của audio gốc tính theo file stem_goc.wav
                        orig_words=[dict(w, s=round(w["s"] - a, 3), e=round(w["e"] - a, 3))
                                    for w in s.orig_words.get(yt_idx) or []])
        with open(stem + ".json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=1, default=str)
        files.append(stem + ".json")
        self._saved[wav] = stem
        return [os.path.basename(x) for x in files]

    def _open_folder_of(self, stem):
        folder = os.path.dirname(stem)
        self.p_status.set("Bản thu này đã lưu ở %s" % folder)
        try:
            os.startfile(folder)
        except Exception as e:
            self.p_status.set("Không mở được thư mục: %s" % e)

    def _saved_dialog(self, folder, files, n):
        self._sync_rec_pills()
        self.p_status.set("Đã lưu %d bản thu vào %s" % (n, folder))
        self._log("Đã lưu %d bản thu vào %s" % (n, folder))
        shown = "\n".join("•  " + f for f in files[:8]) + (
            "\n…  và %d file khác" % (len(files) - 8) if len(files) > 8 else "")
        if messagebox.askyesno("Đã lưu bản thu",
                               "Đã lưu %d bản thu vào thư mục:\n%s\n\n%s\n\nMở thư mục này?"
                               % (n, folder, shown)):
            try:
                os.startfile(folder)
            except Exception as e:
                self.p_status.set("Không mở được thư mục: %s" % e)

    def _save_recording(self):
        """Lưu bản thu đang xem vào Documents\\Oriole (không hỏi thư mục) rồi báo nơi lưu.
        Dữ liệu chỉ nằm trên máy người dùng (R1)."""
        if self.recording or self.p_working:
            return
        if not self.last_wav or not os.path.exists(self.last_wav):
            self.p_status.set("Chưa có bản thu để lưu — thu âm trước đã.")
            return
        if self.last_wav in self._saved:          # nút "Đã lưu ✓": mở chỗ đã lưu, không lưu trùng
            self._open_folder_of(self._saved[self.last_wav])
            return
        yt = self.prac_mode.get() == "yt" and self._yt_sess
        stamp = time.strftime("%Y%m%d-%H%M%S")
        if yt:
            s, idx = self._yt_sess, self._yt_idx
            name = "oriole_%s_doan%d_%s" % (safe_stem(s.vid or "video"), idx + 1, stamp)
            target, res = s.paragraphs[idx]["text"], self._yt_res
        else:
            sid = self._current_set_id() or self.prac_mode.get()
            name = "oriole_%s_%s" % (sid, stamp)
            target, res, idx = self._current_practice()[0], self._last_res, None
        try:
            folder = recordings_dir()
            files = self._save_bundle(os.path.join(folder, name), self.last_wav, target, res,
                                      idx if yt else None)
        except Exception as e:
            messagebox.showerror("Không lưu được", str(e))
            return
        self._saved_dialog(folder, files, 1)

    def _save_all(self):
        """Từ YouTube: lưu MỌI đoạn đã đọc của video vào một thư mục con của Documents\\Oriole."""
        s = self._yt_sess
        if not s or self.recording or self.p_working:
            return
        kept = sorted((i, k) for i, k in self._yt_keep.items()
                      if k.get("wav") and os.path.exists(k["wav"]))
        if not kept:
            self.p_status.set("Chưa có đoạn nào đã đọc để lưu.")
            return
        if all(k["wav"] in self._saved for _i, k in kept):
            self._open_folder_of(self._saved[kept[0][1]["wav"]])
            return
        try:
            folder = os.path.join(recordings_dir(), "oriole_%s_%s" % (
                safe_stem(s.vid or "video"), time.strftime("%Y%m%d-%H%M%S")))
            os.makedirs(folder, exist_ok=True)
            files = []
            for i, k in kept:
                files += self._save_bundle(os.path.join(folder, "doan%02d" % (i + 1)), k["wav"],
                                           s.paragraphs[i]["text"], k["res"], i)
        except Exception as e:
            messagebox.showerror("Không lưu được", str(e))
            return
        self._saved_dialog(folder, files, len(kept))

    # ================= đọc to transcript YouTube (D-39, YT-READING-PLAN Y3) =================
    def _yt_tags(self):
        P, t = self.P, self.yt_text
        t.tag_configure("yk_ok", foreground=P["fg"], background="")
        t.tag_configure("yk_unsure", foreground=P["fg"], background=P["card2"])
        t.tag_configure("yk_doubt", foreground=P["muted"], background=P["card2"])
        t.tag_configure("yk_warn", foreground=P["warn_fg"], background=P["warn_bg"])
        t.tag_configure("yk_bad", foreground=P["bad_fg"], background=P["bad_bg"])
        t.tag_configure("yk_plain", foreground=P["fg"], background="")
        t.tag_configure("yk_hint", foreground=P["muted"], font=(self.F, 12))
        t.tag_configure("yk_pause", foreground=P["bad_fg"], font=(self.F, 15, "bold"))

    def _yt_fill_text(self, marks, pauses=None):
        """Cả đoạn trong ô chữ; marks {chỉ số từ: kind} tô màu sau khi chấm; pauses {chỉ số
        từ: "extra"} → dấu "/" đỏ sau từ đó (bạn ngừng giữa cụm từ, R1)."""
        t = self.yt_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        s = self._yt_sess
        if not s:
            t.insert("end", "Dán link video YouTube tiếng Anh ở ô trên rồi bấm “Lấy transcript”.\n\n"
                     "Oriole chia lời nói thành từng đoạn ~20–45 giây. Bạn nghe đoạn gốc, đọc to "
                     "cả đoạn, rồi xem từ nào khác với phụ đề.", "yk_hint")
        else:
            for i, w in enumerate(s.paragraphs[self._yt_idx]["text"].split()):
                t.insert("end", w, "yk_" + ((marks or {}).get(i) or "plain"))
                t.insert("end", " ")
                if (pauses or {}).get(i):
                    t.insert("end", "/ ", "yk_pause")
        t.configure(state="disabled")
        t.yview_moveto(0)

    def _yt_mode_hint(self):
        if self.prac_mode.get() != "yt" or self.p_working or self.recording:
            return
        self.p_status.set("Bấm Thu âm: app phát đoạn gốc trước, nghe xong tự bắt đầu thu."
                          if self.yt_listen.get() == "listen" else
                          "Bấm Thu âm rồi đọc to cả đoạn — không nghe mẫu trước.")

    def _yt_refresh(self):
        """Vẽ lại màn đọc to theo phiên + đoạn hiện tại; kết quả cũ bị xóa (P-01)."""
        s = self._yt_sess
        self._p_target = ""
        self._stage_repack("yt", False, False, False)
        if s:
            p = s.paragraphs[self._yt_idx]
            kind = {"manual": "phụ đề thủ công", "auto": "phụ đề tự động",
                    "whisper": "transcript do Whisper tạo"}.get(s.sub_kind, "")
            self.yt_title.configure(text="%s  ·  %s" % (s.title or s.vid, kind))
            self.yt_meta.configure(text="%s–%s  ·  %d từ  ·  %d từ/phút" % (
                short_duration(p["start"]), short_duration(p["end"]), p["words"], p["wpm"]))
            self.p_pos.configure(text="Đoạn %d / %d" % (self._yt_idx + 1, len(s.paragraphs)))
        else:
            self.yt_title.configure(text="Luyện đọc to theo video YouTube tiếng Anh")
            self.yt_meta.configure(text="")
            self.p_pos.configure(text="")
        for ch in self.p_samples.winfo_children():
            ch.destroy()
        pill = self._mk_pill(self.p_samples, "Nghe đoạn gốc", self._yt_play_para, bool(s))
        self._pill_show(pill, True)
        self._mk_rec_pills()
        self._yt_res = self._yt_view = None
        if not self.p_working:
            self._clear_prac_result()
            if getattr(self, "prac_state", "idle") in ("result", "unsure", "error"):
                self._set_prac_state("idle")
        self.p_status.set("" if s else "Dán link YouTube, bấm “Lấy transcript”.")
        if s:
            self._yt_mode_hint()
        self._seg._draw()
        self._update_prog(None)
        if s and s.sub_kind != "whisper" and self._yt_idx not in s._orig:
            threading.Thread(target=self._w_ytprefetch,
                             args=(s, self._yt_idx, self.model_name.get()), daemon=True).start()
        k = self._yt_keep.get(self._yt_idx) if s else None
        if not self.p_working and not self.recording:
            ok = bool(k and k.get("wav") and os.path.exists(k["wav"]))
            if self.last_wav and not self._yt_kept_wav(self.last_wav):
                remove_temp(self.last_wav)      # bản thu chưa chấm được (lỗi) — không giữ
            self.last_wav = k["wav"] if ok else None
            self._sync_rec_pills()
            if ok:
                self._yt_show(k["res"], k["gate"])

    def _yt_step(self, d):
        s = self._yt_sess
        if not s or self.p_working or self.recording:
            return
        self._stop_play()
        self._yt_report_hide()
        self._yt_idx = (self._yt_idx + d) % len(s.paragraphs)
        self._yt_refresh()           # bản thu + kết quả của đoạn mới (nếu đã đọc) hiện lại

    def _yt_load(self):
        if self.p_working or self.recording:
            return
        url = self.yt_read_url.get().strip()
        if not re.match(r"https?://", url) or "youtu" not in url.lower():
            messagebox.showwarning("Link không hợp lệ",
                                   "Dán link video YouTube (youtu.be/… hoặc watch?v=…).")
            return
        self._stop_play()
        if self._yt_sess:
            self._yt_sess.close()           # phiên dùng một lần (D-39)
            self._yt_sess = None
        self._yt_drop_keep()
        self._yt_report_hide()
        self._yt_cancel = False
        self._yt_refresh()
        self._set_prac_state("loading")
        self.p_status.set("Đang đọc thông tin video…")
        self._log(f"Đọc to YouTube: {url}")
        threading.Thread(target=self._w_ytload, args=(url, self.model_name.get()),
                         daemon=True).start()

    def _w_ytload(self, url, model_size):
        try:
            s = ytread_prepare(url, model_size, cancel=lambda: self._yt_cancel,
                               status=lambda m: self._queue.put(("prac_status", m)))
            self._queue.put(("yt_ready", s))
        except _YtCancelled:
            self._queue.put(("yt_fail", "__cancelled__"))
        except ValueError as e:
            self._queue.put(("yt_fail", str(e)))
        except Exception as e:
            self._queue.put(("yt_fail", "__cancelled__" if self._yt_cancel
                             else f"Lỗi YouTube: {e}"))

    def _yt_ready(self, s):
        if self._yt_cancel:              # Hủy đến sau khi worker vừa xong
            s.close()
            self._yt_fail("__cancelled__")
            return
        self._yt_sess, self._yt_idx = s, 0
        self._log("Đọc to: %s · %d đoạn (%s)" % (s.title, len(s.paragraphs), s.sub_kind))
        self._set_prac_state("idle")
        self._yt_refresh()

    def _yt_fail(self, msg):
        cancelled = msg == "__cancelled__"
        self._set_prac_state("idle" if cancelled else "error")
        self._yt_refresh()
        self.p_status.set("Đã hủy lấy transcript." if cancelled else msg)
        if not cancelled:
            self._log(msg, "err")

    def _yt_play_para(self):
        s = self._yt_sess
        if not s or self.playing or self.recording or self.p_working:
            return
        p = s.paragraphs[self._yt_idx]
        self._play_span(s.wav, p["start"], p["end"])

    def _play_span(self, path, start, end, then=None):
        """Phát start..end của file wav trong thread; then: thông điệp queue khi phát xong."""
        if self.playing or not path:
            return
        self.playing = True

        def job():
            try:
                play_wav_segment(path, start, end)
            except Exception as e:
                self._queue.put(("prac_status", f"Không phát được: {e}"))
            finally:
                self.playing = False
                if then:
                    self._queue.put(then)

        threading.Thread(target=job, daemon=True).start()

    def _yt_start(self):
        s = self._yt_sess
        if not s:
            self.p_status.set("Chưa có đoạn để đọc — dán link YouTube, bấm “Lấy transcript”.")
            return
        if self._yt_listening:            # bấm Thu khi đang nghe → bỏ phần còn lại, thu ngay
            self._stop_play()
            self._yt_rec_start()
            return
        if self.yt_listen.get() == "listen" and not self.playing:
            p = s.paragraphs[self._yt_idx]
            self._yt_listening = True
            self._clear_prac_result(note=False)
            self.p_status.set("▶ Đang phát đoạn gốc — nghe kỹ; xong app tự bắt đầu thu. "
                              "(Bấm nút đỏ để thu ngay, Esc để dừng)")
            self._play_span(s.wav, p["start"], p["end"],
                            then=("yt_listen_done", (id(s), self._yt_idx)))
            return
        self._yt_rec_start()

    def _yt_listen_done(self, token):
        s = self._yt_sess
        if not self._yt_listening or not s or token != (id(s), self._yt_idx):
            return
        self._yt_listening = False
        self._yt_rec_start()

    def _yt_rec_start(self):
        if self._mic_probing or self.recording or self.p_working:
            return
        dev, name, rate = self._resolve_mic()
        if dev is None:
            return
        self._set_prac_state("recording")
        self._clear_prac_result(note=False)
        self.recorder.start(dev, rate, YT_MAX_SEC,
                            lambda reason: self._queue.put(("prac_autostop", reason)),
                            lambda m: self._queue.put(("prac_error", m)),
                            auto_stop={"silence": YT_SILENCE_SEC, "min_speech": 0.4,
                                       "start_timeout": 10.0})
        self.p_status.set(f"● ĐANG THU bằng {name}. Đọc to cả đoạn — xong ngừng khoảng "
                          f"4 giây, hoặc bấm ■ Dừng & chấm.")
        self.lbl_plevel.configure(text="● Đang thu · 00:00 · mời bạn đọc…")
        self._prac_tick()

    def _yt_score(self, wav_path):
        s = self._yt_sess
        if not s:
            return
        self._set_prac_state("scoring")
        self._clear_prac_result(note=False)
        self.p_status.set("Đang nghe lại bài đọc của bạn và đoạn gốc…")
        threading.Thread(target=self._w_ytscore,
                         args=(wav_path, s, self._yt_idx, self.model_name.get()),
                         daemon=True).start()

    def _w_ytscore(self, wav_path, s, idx, model_size):
        try:
            learner, up = ytread_model(model_size)
            if up:
                self._queue.put(("prac_status", "Đang nghe lại bài đọc của bạn bằng model "
                                                "medium (chính xác hơn, ~10 giây)…"))
            asr = transcribe_practice(load_model(learner), wav_path, "en")
            if not asr["hyp"]:
                self._queue.put(("prac_error", "Không nghe được chữ nào — thử đọc to, gần mic hơn."))
                return
            orig = ytread_orig_hyp(s, idx, load_model(model_size))
            res = read_aloud_diff(s.paragraphs[idx]["text"], asr["hyp"], orig)
            probs = asr["probs"]
            res["words_t"], res["model"] = asr["words_t"], learner
            try:
                res["pitch"] = prosody.pitch_track(wav_path)        # ngữ điệu (D-44)
            except Exception:
                res["pitch"] = None
            ytread_orig_pitch(s, idx)
            res["conf"] = (sum(probs) / len(probs)) if probs else 1.0
            res["low_conf"] = bool(probs) and res["conf"] < 0.35
            self._queue.put(("yt_done", (idx, res, evidence_gate(res))))
        except Exception as e:
            self._queue.put(("prac_error", f"Lỗi chấm đoạn đọc: {e}"))

    def _yt_session_patterns(self):
        """Một dòng gom mẫu lỗi của MỌI đoạn đã đọc trong video ("" nếu < 2 đoạn)."""
        done = [k for k in self._yt_keep.values() if k.get("res") and not k.get("gate")]
        if len(done) < 2:
            return ""
        tot = {}
        for k in done:
            for g in error_pattern_view(ytread_view(k["res"])["fixes"])["groups"]:
                tot[g["title"]] = tot.get(g["title"], 0) + g["n"]
        if not tot:
            return ""
        top = sorted(tot.items(), key=lambda kv: -kv[1])[:3]
        return "Cả video (%d đoạn đã đọc): %s" % (
            len(done), " · ".join("%s %d từ" % (t, n) for t, n in top))

    # ----- báo cáo cuối phiên (D-43) -----
    def _yt_report_input(self):
        s = self._yt_sess
        info = {"title": s.title or s.vid, "url": s.url, "sub_kind": s.sub_kind,
                "n_paras": len(s.paragraphs), "date": time.strftime("%d/%m/%Y %H:%M")}
        done = [{"idx": i, "text": s.paragraphs[i]["text"], "res": k["res"],
                 "gate": k.get("gate"), "orig_words": s.orig_words.get(i),
                 "pitch_ref": s.pitch.get(i)}
                for i, k in sorted(self._yt_keep.items()) if k.get("res")]
        return info, done

    def _yt_finish(self):
        """Kết thúc phiên (có thể trước khi đọc hết) → báo cáo các đoạn đã đọc."""
        s = self._yt_sess
        if not s or self.recording or self.p_working:
            return
        info, done = self._yt_report_input()
        if not done:
            self.p_status.set("Chưa có đoạn nào được chấm — đọc ít nhất một đoạn trước.")
            return
        self._stop_play()
        self._yt_rep = session_report(info, done)
        self._yt_report_render(self._yt_rep)
        if self._prac_body.winfo_manager():
            self._prac_body.pack_forget()
        if not self.yt_report.winfo_manager():
            self.yt_report.pack(fill="both", expand=True)

    def _yt_report_hide(self):
        if getattr(self, "yt_report", None) is not None and self.yt_report.winfo_manager():
            self._stop_play()
            self.yt_report.pack_forget()
            self._prac_body.pack(fill="both", expand=True)

    def _yt_goto(self, idx):
        self._yt_report_hide()
        if self._yt_sess and 0 <= idx < len(self._yt_sess.paragraphs):
            self._yt_idx = idx
            self._yt_refresh()

    def _yt_report_render(self, rep):
        """Màn báo cáo toàn bề ngang: tóm tắt, 3 điều tập trung, âm hay sai cả bài, trôi chảy,
        từng đoạn (▶ cả đoạn, mở lại đoạn), từ cần luyện; nút Lưu báo cáo / Quay lại."""
        for ch in self.yt_report.winfo_children():
            ch.destroy()
        s, P = self._yt_sess, self.P
        outer, inner = self._scroll_area(self.yt_report, "card")
        outer.pack(fill="both", expand=True)
        box = self._frame(inner, bg="card")
        box.pack(fill="x", padx=self.px(48), pady=(self.px(28), self.px(36)))
        wraps = []

        def lbl(parent, text, size=10, weight="normal", fg="fg", margin=0, font=None):
            lb = self._lbl(parent, text, size=size, weight=weight, fg=fg, justify="left",
                           anchor="w", font=font)
            wraps.append((lb, margin))
            return lb

        def caps(text):
            self._lbl(box, text, fg="muted", size=9, weight="bold", anchor="w").pack(
                fill="x", pady=(self.px(26), self.px(6)))
            self._hline(box, pady=(0, self.px(6)))

        def links(parent, items):
            fr = self._frame(parent, bg="card")
            for text, cmd in items:
                self._link_lbl(fr, text, cmd, size=9).pack(side="left", padx=(0, self.px(14)))
            return fr

        def kept(idx):
            k = self._yt_keep.get(idx) or {}
            return k.get("wav") if k.get("wav") and os.path.exists(k["wav"]) else None

        def word_links(idx, ti):
            k = self._yt_keep.get(idx) or {}
            res = k.get("res") or {}
            tgt = res.get("target", "")
            mine = token_spans(res.get("words_t"), tgt).get(ti)
            orig = token_spans(s.orig_words.get(idx), tgt).get(ti)
            out, wav = [], kept(idx)
            if orig and s.wav:
                out.append(("▶ Mẫu", lambda a=orig: self._play_span(s.wav, a[0], a[1])))
            if mine and wav:
                out.append(("▶ Bạn đọc", lambda a=mine, w=wav: self._play_span(w, a[0], a[1])))
            return out

        # đầu báo cáo + nút
        top = self._frame(box, bg="card")
        top.pack(fill="x")
        acts = self._frame(top, bg="card")
        acts.pack(side="right", anchor="n")
        ttk.Button(acts, text="Lưu báo cáo", style="Accent.TButton",
                   command=self._yt_save_report).pack(side="left")
        ttk.Button(acts, text="Quay lại luyện", style="Ghost.TButton",
                   command=self._yt_report_hide).pack(side="left", padx=(self.px(10), 0))
        lbl(top, "Báo cáo luyện đọc to", size=20, weight="bold", margin=self.px(320)).pack(
            fill="x")
        lbl(top, "%s · đã đọc %d/%d đoạn · %s" % (rep["title"], rep["n_read"], rep["n_paras"],
                                                 rep["date"]), fg="muted",
            margin=self.px(320)).pack(fill="x", pady=(self.px(2), 0))
        lbl(box, "%d/%d từ đúng (%d%%)" % (rep["correct"], rep["total"], rep["pct"]), size=18,
            weight="bold").pack(fill="x", pady=(self.px(18), 0))
        bits = []
        if rep["wpm_usr"]:
            bits.append("tốc độ %d từ/phút" % rep["wpm_usr"] + (
                " (người nói %d)" % rep["wpm_ref"] if rep["wpm_ref"] else ""))
        if rep["doubts"]:
            bits.append("%d từ không tính (phụ đề có thể sai)" % rep["doubts"])
        if rep["unread"]:
            bits.append("%d từ chưa đọc tới" % rep["unread"])
        if rep["n_read"] < rep["n_paras"]:
            bits.append("còn %d đoạn chưa đọc" % (rep["n_paras"] - rep["n_read"]))
        if bits:
            lbl(box, " · ".join(bits), fg="muted").pack(fill="x")

        if rep["focus"]:
            caps("3 ĐIỀU NÊN TẬP TRUNG")
            for i, f in enumerate(rep["focus"], 1):
                lbl(box, "%d.  %s" % (i, f["title"]), size=11, weight="bold").pack(
                    fill="x", pady=(self.px(6), 0))
                lbl(box, f["detail"], margin=self.px(22)).pack(fill="x", padx=(self.px(22), 0))
        if rep["patterns"]:
            caps("ÂM HAY SAI — CẢ BÀI")
            for g in rep["patterns"]:
                row = self._frame(box, bg="card")
                row.pack(fill="x", pady=(self.px(8), 0))
                idx, ti = g["where"][0]
                links(row, word_links(idx, ti)).pack(side="right", anchor="n")
                lbl(row, "%s · %d từ" % (g["title"], g["n"]), size=11, weight="bold",
                    margin=self.px(200)).pack(fill="x")
                lbl(box, "Ví dụ: " + pattern_example_text(g["examples"], REPORT_EXAMPLES),
                    fg="muted", margin=self.px(22)).pack(fill="x", padx=(self.px(22), 0))
                lbl(box, g["tip"], margin=self.px(22)).pack(fill="x", padx=(self.px(22), 0))
        if rep.get("intonation"):
            caps("NGỮ ĐIỆU")
            for x in rep["intonation"]:
                lbl(box, "•  " + x).pack(fill="x", pady=(self.px(2), 0))
        if rep["fluency"]:
            caps("TRÔI CHẢY")
            for x in rep["fluency"]:
                lbl(box, "•  " + x).pack(fill="x", pady=(self.px(2), 0))
        caps("TỪNG ĐOẠN — nghe lại cả đoạn hoặc mở lại để đọc tiếp")
        for p in rep["paras"]:
            row = self._frame(box, bg="card")
            row.pack(fill="x", pady=(self.px(6), 0))
            idx, para = p["idx"], s.paragraphs[p["idx"]]
            items = []
            if s.wav:
                items.append(("▶ Người nói", lambda a=para: self._play_span(
                    s.wav, a["start"], a["end"])))
            wav = kept(idx)
            if wav:
                items.append(("▶ Bạn đọc", lambda w=wav: self._play_span(w, 0, 10 ** 6)))
            items.append(("Mở đoạn", lambda i=idx: self._yt_goto(i)))
            links(row, items).pack(side="right", anchor="n")
            txt = "Đoạn %d · %s" % (idx + 1, p["headline"])
            sub_ = []
            if p["fixes"]:
                sub_.append("%d từ cần sửa" % p["fixes"])
            if p.get("unread"):
                sub_.append("chưa đọc hết %d từ" % p["unread"])
            if p["wpm_usr"]:
                sub_.append("%d từ/phút" % p["wpm_usr"] + (
                    " (người nói %d)" % p["wpm_ref"] if p["wpm_ref"] else ""))
            if p["top"]:
                sub_.append("hay sai: " + p["top"])
            col = self._frame(row, bg="card")
            col.pack(side="left", fill="x", expand=True)
            lbl(col, txt, weight="bold", margin=self.px(300)).pack(fill="x")
            if sub_:
                lbl(col, " · ".join(sub_), fg="muted", margin=self.px(300)).pack(fill="x")
        if rep["words"]:
            caps("TỪ CẦN LUYỆN")
            lbl(box, ",  ".join(w["word"] + (" ×%d" % w["n"] if w["n"] > 1 else "")
                                for w in rep["words"])).pack(fill="x")
        lbl(box, "Nhận xét chỉ mô tả, so với người nói trong video; điểm = số từ máy nghe đúng.",
            fg="muted", size=9).pack(fill="x", pady=(self.px(28), 0))

        def rewrap(e):
            for lb, m in wraps:
                try:
                    lb.configure(wraplength=max(self.px(200), e.width - m))
                except tk.TclError:
                    pass
        box.bind("<Configure>", rewrap)

    def _yt_save_report(self):
        """Lưu báo cáo: thư mục con của Documents\\Oriole gồm bao-cao.html (mở bằng trình duyệt,
        có nút nghe lại) + bản thu/đoạn gốc từng đoạn đã đọc."""
        s, rep = self._yt_sess, getattr(self, "_yt_rep", None)
        if not s or not rep:
            return
        try:
            folder = os.path.join(recordings_dir(), "oriole_%s_%s_baocao" % (
                safe_stem(s.vid or "video"), time.strftime("%Y%m%d-%H%M%S")))
            os.makedirs(folder, exist_ok=True)
            audio = {}
            for i, k in sorted(self._yt_keep.items()):
                if k.get("wav") and os.path.exists(k["wav"]) and k.get("res"):
                    stem = "doan%02d" % (i + 1)
                    self._save_bundle(os.path.join(folder, stem), k["wav"],
                                      s.paragraphs[i]["text"], k["res"], i)
                    audio[i] = (stem + ".wav", stem + "_goc.wav")
            page = os.path.join(folder, "bao-cao.html")
            with open(page, "w", encoding="utf-8") as f:
                f.write(report_html(rep, audio))
        except Exception as e:
            messagebox.showerror("Không lưu được báo cáo", str(e))
            return
        self._sync_rec_pills()
        self._log("Đã lưu báo cáo: %s" % page)
        if messagebox.askyesno("Đã lưu báo cáo",
                               "Đã lưu báo cáo và %d bản thu vào thư mục:\n%s\n\n"
                               "Mở báo cáo (bao-cao.html) bằng trình duyệt?" % (len(audio), folder)):
            try:
                os.startfile(page)
            except Exception as e:
                messagebox.showerror("Không mở được", str(e))

    def _w_ytprefetch(self, s, idx, model_size):
        """Nghe trước đoạn gốc trong lúc người học nghe/đọc → chấm xong nhanh hơn ~3–10 s.
        Lỗi bỏ qua: lúc chấm sẽ thử lại (cùng khóa của phiên)."""
        try:
            ytread_orig_hyp(s, idx, load_model(model_size))
            ytread_orig_pitch(s, idx)
        except Exception:
            pass

    def _yt_done(self, idx, res, gate):
        if idx != self._yt_idx or not self._yt_sess:
            self._set_prac_state("idle")
            return
        self._yt_keep[idx] = {"wav": self.last_wav, "res": res, "gate": gate}
        self._yt_show(res, gate)
        self.p_status.set("")

    def _yt_show(self, res, gate):
        v = ytread_view(res, gate)
        self._yt_res, self._yt_view = res, v
        self._set_prac_state(v["state"])
        self._yt_render(v)

    def _yt_drop_keep(self):
        """Xóa mọi bản thu đã giữ của phiên (lấy video khác / đóng app — I10)."""
        for k in self._yt_keep.values():
            if k.get("wav") and k["wav"] != self.last_wav:
                remove_temp(k["wav"])
        self._yt_keep = {}
        self._saved = {}
        self._set_last_wav(None)

    def _yt_kept_wav(self, path):
        return bool(path) and any(k.get("wav") == path for k in self._yt_keep.values())

    def _yt_render(self, v):
        """Đoạn văn tô màu theo từ + dấu "/" chỗ ngừng sai; panel phải: vòng điểm, TRÔI CHẢY,
        TỪNG CÂU (▶ Mẫu / ▶ Bạn đọc cả câu), CẦN SỬA, PHỤ ĐỀ CÓ THỂ SAI."""
        self._destroy_embeds()
        self._last_view = None
        s, res = self._yt_sess, self._yt_res
        tgt = res.get("target", "")
        mine = token_spans(res.get("words_t"), tgt)
        orig = token_spans(s.orig_words.get(self._yt_idx), tgt) if s else {}
        text = s.paragraphs[self._yt_idx]["text"] if s else ""
        flu = fluency_view(text, res, mine, orig) if v["state"] == "result" else None
        self._yt_flu = flu
        self._yt_fill_text(v["marks"], flu and flu["pause_after"])
        self._draw_ring(v["ring"])
        self.p_headline.configure(text=v["headline"])
        self.p_summary.configure(text=v["summary"], font=(self.F, 10))

        def caps(text):
            lb = self._caps(self.pp_yt, text)
            lb.pack(fill="x", pady=(self.px(14) if self.pp_yt.winfo_children()[:-1] else 0,
                                    self.px(2)))
            self._embeds.append(lb)

        def mini_curve(parent, ref, usr):
            """Đường cao độ thu nhỏ: người nói (nét chấm) và bạn (nét liền), cùng thang."""
            W, H = self.px(150), self.px(30)
            cv = self._tw(tk.Canvas(parent, width=W, height=H, bd=0, highlightthickness=0),
                          bg="side")
            lim = 9.0

            def draw(vals, color, dash):
                pts = []
                for i, v in enumerate(vals or []):
                    if v is None:
                        if len(pts) >= 4:
                            cv.create_line(*pts, fill=color, width=max(1, self.px(1.6)),
                                           dash=dash, smooth=True)
                        pts = []
                        continue
                    x = 2 + i * (W - 4) / float(max(1, len(vals) - 1))
                    y = H / 2.0 - max(-lim, min(lim, v)) / lim * (H / 2.0 - 2)
                    pts += [x, y]
                if len(pts) >= 4:
                    cv.create_line(*pts, fill=color, width=max(1, self.px(1.6)), dash=dash,
                                   smooth=True)
            cv.create_line(0, H / 2.0, W, H / 2.0, fill=P["border"])
            draw(ref, P["muted"], (2, 2))
            draw(usr, P["accent"], None)
            return cv

        def row(color, text, mine_sp=None, orig_sp=None, muted=False, sub=None, curve=None):
            r = self._frame(self.pp_yt, bg="side")
            r.pack(fill="x", pady=(self.px(5), 0))
            self._embeds.append(r)
            d = self.px(8)
            dot = self._tw(tk.Canvas(r, width=d, height=d, bd=0, highlightthickness=0),
                           bg="side")
            dot.create_oval(0, 0, d, d, outline="", fill=color)
            dot.pack(side="left", anchor="n", padx=(0, self.px(10)), pady=(self.px(5), 0))
            links = self._frame(r, bg="side")
            links.pack(side="right", anchor="n")
            if mine_sp and self.last_wav:
                self._link_lbl(links, "▶ Bạn đọc",
                               lambda a=mine_sp: self._play_span(self.last_wav, a[0], a[1]),
                               bg="side", size=9).pack(side="right", padx=(self.px(10), 0))
            if orig_sp and s and s.wav:
                self._link_lbl(links, "▶ Mẫu",
                               lambda a=orig_sp: self._play_span(s.wav, a[0], a[1]),
                               bg="side", size=9).pack(side="right", padx=(self.px(10), 0))
            col = self._frame(r, bg="side")
            col.pack(side="left", fill="x", expand=True)
            self._wrap(self._lbl(col, text, bg="side", fg="muted" if muted else "fg", size=10,
                                 justify="left", anchor="w"), self.px(150)).pack(fill="x")
            if sub:
                self._wrap(self._lbl(col, sub, bg="side", fg="muted", size=9, justify="left",
                                     anchor="w"), self.px(150)).pack(fill="x")
            if curve and (curve[0] or curve[1]):
                mini_curve(col, *curve).pack(anchor="w", pady=(self.px(3), 0))

        def note(text):
            lb = self._wrap(self._lbl(self.pp_yt, "•  " + text, bg="side", size=10,
                                      justify="left", anchor="w"), self.px(10))
            lb.pack(fill="x", pady=(self.px(3), 0))
            self._embeds.append(lb)

        P = self.P
        sections = ["head"]
        pats = error_pattern_view(v["fixes"]) if v["state"] == "result" else None
        if pats and pats["groups"]:
            caps("ÂM HAY SAI — sửa thói quen, không chỉ từng từ")
            for g in pats["groups"][:PATTERN_SHOW]:
                ti = next((t for t in g["ti"] if orig.get(t)), g["ti"][0])
                row(P["warn_line"], "%s · %d từ" % (g["title"], g["n"]), mine.get(ti),
                    orig.get(ti), sub="Ví dụ: " + pattern_example_text(g["examples"]))
                tip = self._wrap(self._lbl(self.pp_yt, g["tip"], bg="side", size=9,
                                           justify="left", anchor="w"), self.px(28))
                tip.pack(fill="x", padx=(self.px(18), 0), pady=(self.px(2), self.px(2)))
                self._embeds.append(tip)
            rest = pats["groups"][PATTERN_SHOW:]
            if rest:
                note("Còn: " + ", ".join("%s (%d)" % (g["title"], g["n"]) for g in rest))
            whole = self._yt_session_patterns()
            if whole:
                note(whole)
        if flu and flu["lines"]:
            caps("TRÔI CHẢY")
            for ln in flu["lines"]:
                note(ln)
        inton = intonation_view(flu["sentences"], res.get("pitch"),
                                ytread_orig_pitch(s, self._yt_idx) if s else None) \
            if flu else None
        if inton and inton["lines"]:
            caps("NGỮ ĐIỆU")
            for ln in inton["lines"]:
                note(ln)
        if flu and flu["sentences"]:
            caps("TỪNG CÂU — cao độ: chấm = người nói, liền = bạn")
            for i, st in enumerate(flu["sentences"], 1):
                it = inton["sentences"][i - 1] if inton else {}
                bits = []
                if st["dur_usr"] and st["dur_ref"]:
                    bits.append("bạn %s s · người nói %s s" % (_vn_num(st["dur_usr"]),
                                                             _vn_num(st["dur_ref"])))
                if st["fixes"]:
                    bits.append("%d từ cần sửa" % st["fixes"])
                if st["extra"]:
                    bits.append("ngừng: " + ", ".join(st["extra"][:2]))
                if it.get("range_usr") is not None and it.get("range_ref") is not None:
                    bits.append("cao độ: bạn %s · người nói %s bán cung" % (
                        _vn_num(it["range_usr"]).replace(",0", ""),
                        _vn_num(it["range_ref"]).replace(",0", "")))
                row(P["warn_line"] if (st["fixes"] or st["extra"]) else P["ring_ok"],
                    "Câu %d · “%s”" % (i, st["short"]), st["usr"], st["ref"],
                    sub=" · ".join(bits) or None,
                    curve=(it.get("curve_ref"), it.get("curve_usr")))
        if v["state"] == "unsure":
            for tip in v["tips"]:
                lb = self._wrap(self._lbl(self.pp_yt, "•  " + tip, bg="side", size=10,
                                          justify="left", anchor="w"))
                lb.pack(fill="x", pady=(0, self.px(4)))
                self._embeds.append(lb)
            sections.append("yt")
            self._show_actions("Đọc lại đoạn này", self._prac_record)
            self._panel_show(sections)
            return
        if v["fixes"]:
            caps("CẦN SỬA (%d)" % len(v["fixes"]))
            for f in v["fixes"][:YT_ROWS_MAX]:
                row(P["bad_line"] if f["kind"] == "bad" else P["warn_line"], f["text"],
                    mine.get(f["ti"]), orig.get(f["ti"]))
            if len(v["fixes"]) > YT_ROWS_MAX:
                caps("… và %d từ khác (tô màu trong đoạn)" % (len(v["fixes"]) - YT_ROWS_MAX))
        if v["doubts"]:
            caps("PHỤ ĐỀ CÓ THỂ SAI — KHÔNG TÍNH (%d)" % len(v["doubts"]))
            for d in v["doubts"][:YT_ROWS_MAX]:
                row(P["border"], d["text"], mine.get(d["ti"]), orig.get(d["ti"]), muted=True)
        if v["extras"]:
            more = len(v["extras"]) - 6
            caps("ĐỌC THÊM")
            lb = self._wrap(self._lbl(self.pp_yt, ", ".join("“%s”" % w for w in v["extras"][:6])
                                      + (" … +%d từ" % more if more > 0 else ""),
                                      bg="side", fg="muted", size=9, justify="left", anchor="w"))
            lb.pack(fill="x")
            self._embeds.append(lb)
        if self.pp_yt.winfo_children():
            sections.append("yt")
        last = bool(s) and self._yt_idx == len(s.paragraphs) - 1
        self._show_actions("Đọc lại đoạn này", self._prac_record,
                           "Xem báo cáo →" if last else "Đoạn sau →",
                           self._yt_finish if last else (lambda: self._step_lesson(1)))
        self._panel_show(sections)
        self._side_wrap(self._side_body.winfo_width())

    # ================= micro =================
    def _refresh_mics(self, rescan=False):
        if rescan and not (self.recording or self.p_working
                           or getattr(self, "playing", False)
                           or self._mic_probing):
            rescan_audio_devices()
        mics = list_usable_mics()
        self.mic_ids = [i for (i, n, a, *_) in mics]
        self._mic_names = [f"{n} [{a}]" for (i, n, a, *_) in mics] or ["(không tìm thấy micro)"]
        for cb in self._mic_combos:
            cb["values"] = self._mic_names
        self._update_mic_hint()
        if not mics:
            return
        saved = self.cfg.get("mic") or ""
        dflt = None
        if saved in self._mic_names:
            dflt = self.mic_ids[self._mic_names.index(saved)]
        if dflt is None:
            dflt = pick_default_mic(mics)
        try:
            self.mic_var.set(self._mic_names[self.mic_ids.index(dflt)])
        except Exception:
            self.mic_var.set(self._mic_names[0])

    def _on_tab_changed(self, _evt=None):
        """Vào màn hình Cài đặt -> quét lại thiết bị (thấy mic ngoài vừa kết nối)."""
        if self.screen == "set":
            self._refresh_mics(rescan=True)

    def _mic_hint_text(self):
        """Gợi ý dưới ô Micro: thiết bị bị ẩn và tai nghe bluetooth thiếu micro."""
        parts = []
        missing = headset_mic_missing()
        if missing:
            parts.append(
                f"Tai nghe “{missing}” mới chỉ có chiều NGHE — Windows chưa mở micro "
                "của nó (headset bluetooth chỉ thu khi bật profile Hands-Free). "
                "Cách bật: Control Panel → Sound → tab Recording → chuột phải → "
                "“Show Disabled Devices” → Enable “Headset (… Hands-Free AG Audio)”; "
                "hoặc Control Panel → Devices and Printers → chuột phải tai nghe → "
                "Properties → Services → tích “Hands-Free Telephony”. Xong bấm "
                "“Quét lại”.")
        try:
            hidden = len(list_input_mics()) - len(self.mic_ids)
        except Exception:
            hidden = 0
        if hidden > 0:
            parts.append(f"Đã ẩn {hidden} thiết bị [Windows WDM-KS] "
                         "(PortAudio không thu liên tục được).")
        return "  ".join(parts)

    def _update_mic_hint(self):
        text = self._mic_hint_text()
        for lbl in getattr(self, "_mic_hints", []):
            try:
                lbl.configure(text=text)
            except Exception:
                pass

    def _open_sound_settings(self):
        """Mở trang âm thanh của Windows để chọn/tăng micro ngoài."""
        try:
            os.startfile("ms-settings:sound")
        except Exception:
            messagebox.showinfo(
                "Âm thanh Windows",
                "Mở thủ công: Settings → System → Sound → Input (hoặc Control Panel → "
                "Sound → Recording).")

    def _resolve_mic(self):
        try:
            import sounddevice  # noqa: F401
        except ImportError:
            messagebox.showerror("Thiếu thư viện",
                                 "Chưa có sounddevice. Chạy: pip install -r requirements.txt")
            return None, None, None
        try:
            i = self._mic_names.index(self.mic_var.get())
            dev = self.mic_ids[i]
            return dev, self._mic_names[i], query_mic_rate(dev)
        except Exception:
            pass
        self._refresh_mics()
        if not self.mic_ids:
            messagebox.showerror("Không có micro", "Không tìm thấy thiết bị thu âm nào.")
            return None, None, None
        try:
            dev = self.mic_ids[0]
            return dev, self._mic_names[0], query_mic_rate(dev)
        except Exception:
            return None, None, None

    def _test_mic(self):
        if self.recording or self.p_working or self._mic_probing:
            return
        dev, mic, sr = self._resolve_mic()
        if dev is None:
            return
        self.status.set(f"Đang kiểm tra mic ({mic}) — nói “a…” to trong 2 giây…")
        self.mic_test_msg.set("Đang nghe… nói “a…” to trong 2 giây.")

        def job():
            try:
                import math
                import numpy as np
                import sounddevice as sd
                data = sd.rec(int(sr * 2.0), samplerate=sr, channels=1,
                              dtype="int16", device=dev)
                sd.wait()
                x = data.astype(np.float32).flatten() / 32768.0
                peak = float(np.max(np.abs(x))) if len(x) else 0.0
                rms = float(np.sqrt(np.mean(x * x))) if len(x) else 0.0
                db = 20 * math.log10(peak + 1e-9)
                meas = (f"đỉnh {peak*100:.2f}% ({db:.0f} dB), "
                        f"RMS {rms*100:.2f}%")
                if peak < MIC_MIN_PEAK:
                    msg = (f"Mic gần như IM LẶNG ({meas}). "
                           "Bật micro trong Windows (Privacy → Microphone), bỏ Mute, "
                           "tăng Microphone Level lên 100%.")
                    best = best_input_mic()
                    if best and best[3] >= max(MIC_MIN_PEAK, peak * 3):
                        self._queue.put(("mic_found", best))
                        msg += (f" Đã tìm thấy '{best[1]}' [{best[2]}] có tín hiệu "
                                f"(đỉnh {best[3]*100:.0f}%) — đã chọn giúp bạn. "
                                f"Bấm Thu âm & chấm để đọc lại.")
                    else:
                        msg += (" Không thấy micro nào khác có tín hiệu — kiểm tra "
                                "âm lượng micro trong Windows (Settings → System → "
                                "Sound → Input).")
                elif peak < MIC_GOOD_PEAK:
                    msg = (f"Mic hơi NHỎ ({meas}). App vẫn thu và khuếch đại được, "
                           "nhưng nên tăng Microphone Level lên 100% và để mic "
                           "gần hơn (10–20cm) để nhận dạng chính xác hơn.")
                    best = best_input_mic()
                    if best and best[3] >= max(MIC_GOOD_PEAK, peak * 3):
                        self._queue.put(("mic_found", best))
                        msg += (f" Có micro khác khá hơn: '{best[1]}' [{best[2]}] "
                                f"(đỉnh {best[3]*100:.0f}%) — đã chọn giúp bạn.")
                elif peak >= 0.95:
                    msg = (f"Mic quá TO/VỠ ({meas}). "
                           "Để mic xa hơn hoặc giảm Microphone Level.")
                else:
                    msg = f"Mic tốt ({meas})."
                self._queue.put(("status", "Kiểm tra mic: " + msg))
                self._queue.put(("mic_test", msg))
                self._queue.put(("prac_status", "Kiểm tra mic: " + msg))
            except Exception as e:
                self._queue.put(("error", f"Lỗi kiểm tra mic: {e}"))

        threading.Thread(target=job, daemon=True).start()

    # ================= màn Cài đặt (B5): nhóm hàng kiểu Windows 11, lưu ngay khi đổi =================
    def _build_settings_screen(self, parent):
        bar = self._toolbar(parent, "Cài đặt")
        right = self._frame(bar, bg="card")
        right.pack(side="right", padx=(0, self.px(28)))
        self.set_saved = self._lbl(right, "Thay đổi được lưu ngay", fg="muted", size=9)
        self.set_saved.pack(side="left")
        self._lbl(right, "  ·  ", fg="muted", size=9).pack(side="left")
        self._link_lbl(right, "Khôi phục mặc định", self._reset_cfg, size=9).pack(side="left")
        outer, inner = self._scroll_area(parent, "card")
        outer.pack(fill="both", expand=True)
        wrap = self._frame(inner, bg="card")
        wrap.pack(fill="x", padx=self.px(28), pady=self.px(24))
        cols = self._frame(wrap, bg="card")
        cols.pack(fill="x")
        cols.grid_columnconfigure(0, weight=1, uniform="c")
        cols.grid_columnconfigure(1, weight=1, uniform="c")
        left = self._frame(cols, bg="card")
        left.grid(row=0, column=0, sticky="new", padx=(0, self.px(12)))
        right = self._frame(cols, bg="card")
        right.grid(row=0, column=1, sticky="new", padx=(self.px(12), 0))
        self._set_wraps = []
        inner.bind("<Configure>", lambda e: self._set_wrap_all(
            (e.width - 2 * self.px(28)) // 2 - self.px(60)), add="+")

        # --- Micro ---
        g = self._set_group(left, "Micro")
        row = self._set_row(g, "Thiết bị thu âm", vertical=True)
        cb = ttk.Combobox(row, textvariable=self.mic_var, width=1, state="readonly")
        cb.pack(fill="x", pady=(self.px(6), 0))
        self._mic_combos.append(cb)
        self._tooltip(cb, self.mic_var.get)   # tên mic dài bị cắt trong ô (V-15)
        row, r = self._set_row(g, "Kiểm tra micro", sub_var=self.mic_test_msg)
        ttk.Button(r, text="Thử 2 giây", style="Accent.TButton",
                   command=self._test_mic).pack(side="right")
        # hai nút xếp DƯỚI chữ: cột hẹp (cửa sổ tối thiểu) không cắt mất nhãn
        row = self._set_row(g, "Không thấy micro mới cắm?", vertical=True, last=True)
        sub = self._lbl(row, "Tai nghe bluetooth cần bật chế độ Hands-Free", fg="muted",
                        size=9, anchor="w", justify="left")
        sub.pack(fill="x", pady=(self.px(2), 0))
        self._set_wraps.append(sub)
        r = self._frame(row, bg="card")
        r.pack(fill="x", pady=(self.px(8), 0))
        ttk.Button(r, text="Quét lại", style="Ghost.TButton",
                   command=lambda: self._refresh_mics(rescan=True)).pack(side="left")
        self._link_lbl(r, "Âm thanh Windows", self._open_sound_settings, size=10).pack(
            side="left", padx=(self.px(14), 0))
        hint = self._lbl(left, "", fg="muted", size=9, justify="left", anchor="w")
        hint.pack(fill="x", pady=(self.px(6), 0))
        self._set_wraps.append(hint)
        self._mic_hints.append(hint)

        # --- Giao diện và lưu file ---
        g = self._set_group(left, "Giao diện và lưu file")
        row, r = self._set_row(g, "Giao diện")
        self._mk_seg(r, (("light", "Sáng"), ("dark", "Tối")), self.theme_name,
                     self._toggle_theme).pack(side="right")
        row = self._set_row(g, "Thư mục lưu video và phụ đề", vertical=True, last=True)
        d = self._frame(row, bg="card")
        d.pack(fill="x", pady=(self.px(6), 0))
        ttk.Entry(d, textvariable=self.out_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(d, text="Đổi…", style="Ghost.TButton",
                   command=self._pick_out_dir).pack(side="left", padx=(self.px(8), 0))

        # --- Phụ đề YouTube mặc định ---
        g = self._set_group(right, "Phụ đề YouTube mặc định")
        row, r = self._set_row(g, "Kèm phụ đề", "Lưu .srt và .txt cạnh video")
        self._mk_switch(r, self.y_subs, self._yt_subs_changed).pack(side="right")
        row, r = self._set_row(g, "Ngôn ngữ phụ đề")
        ttk.Combobox(r, textvariable=self.yt_sub_lang, values=YT_SUB_LANG_NAMES, width=24,
                     state="readonly").pack(side="right")
        row, r = self._set_row(g, "Nhúng phụ đề vào video",
                               "Bật/tắt được trong trình xem video", last=True)
        self._mk_switch(r, self.y_embed).pack(side="right")

        # --- Phím tắt ---
        g = self._set_group(right, "Phím tắt")
        for i, (key, desc) in enumerate((("Ctrl+O", "Chọn file âm thanh / video"),
                                         ("Ctrl+Enter", "Bắt đầu, hoặc bắt đầu / dừng thu"),
                                         ("Ctrl+S", "Lưu văn bản (.txt)"),
                                         ("Esc", "Hủy việc đang chạy hoặc dừng thu"))):
            row, r = self._set_row(g, desc, last=i == 3, compact=True)
            self._lbl(r, " %s " % key, bg="card2", size=9).pack(side="right")

        # --- Giới thiệu ---
        g = self._set_group(right, "Giới thiệu")
        box = self._frame(g, bg="card")
        box.pack(fill="x", padx=self.px(16), pady=self.px(12))
        self.info_lines = []
        for _ in range(3):
            lb = self._lbl(box, "", size=10, justify="left", anchor="w")
            lb.pack(fill="x", pady=(0, self.px(4)))
            self._set_wraps.append(lb)
            self.info_lines.append(lb)
        links = self._frame(box, bg="card")
        links.pack(fill="x", pady=(self.px(4), 0))
        self._link_lbl(links, "Mở thư mục app", lambda: os.startfile(BASE_DIR)).pack(side="left")
        self._link_lbl(links, "Mở hướng dẫn (README)", self._open_readme).pack(
            side="left", padx=(self.px(16), 0))
        self._fill_info()
        self._redraws.append(self._fill_info)   # màu ✓/✗ theo theme

    def _set_group(self, parent, title):
        self._lbl(parent, title, size=11, weight="bold", anchor="w").pack(
            fill="x", pady=(self.px(4) if not parent.winfo_children() else self.px(22),
                            self.px(8)))
        g = self._tw(tk.Frame(parent, bd=0, highlightthickness=1), bg="card",
                     highlightbackground="border", highlightcolor="border")
        g.pack(fill="x")
        return g

    def _set_row(self, g, label, sub=None, sub_var=None, last=False, vertical=False,
                 compact=False):
        """Một hàng cài đặt: nhãn (+ dòng phụ) bên trái, điều khiển bên phải."""
        row = self._frame(g, bg="card")
        row.pack(fill="x")
        body = self._frame(row, bg="card")
        body.pack(fill="x", padx=self.px(16), pady=self.px(8 if compact else 12))
        if not last:
            self._hline(row)
        if vertical:
            self._lbl(body, label, size=10, anchor="w").pack(fill="x")
            return body
        r = self._frame(body, bg="card")
        r.pack(side="right", anchor="center")
        txt = self._frame(body, bg="card")
        txt.pack(side="left", fill="x", expand=True)
        self._lbl(txt, label, size=10, anchor="w", justify="left").pack(fill="x")
        if sub or sub_var is not None:
            lb = self._lbl(txt, sub or "", fg="muted", size=9, anchor="w", justify="left")
            if sub_var is not None:
                lb.configure(textvariable=sub_var)
            lb.pack(fill="x", pady=(self.px(2), 0))
            self._set_wraps.append(lb)
        return row, r

    def _set_wrap_all(self, width):
        alive = []
        for lb in getattr(self, "_set_wraps", []):
            try:
                lb.configure(wraplength=max(self.px(120), width))
                alive.append(lb)
            except tk.TclError:
                pass
        self._set_wraps = alive

    def _fill_info(self):
        import importlib.util
        ok = {}
        for mod in ("faster_whisper", "yt_dlp", "imageio_ffmpeg", "sounddevice", "numpy"):
            try:
                ok[mod] = importlib.util.find_spec(mod) is not None
            except Exception:
                ok[mod] = False
        core = all(ok.values())
        gop_ok = gop.available()
        self.info_lines[0].configure(text="%s %s · chạy hoàn toàn trên máy · Python %s"
                                     % (APP_TITLE, VERSION, sys.version.split()[0]))
        self.info_lines[1].configure(
            text="Nhận dạng, tải YouTube, phụ đề, thu âm: %s · Chấm âm vị chuyên sâu: %s"
            % ("✓ sẵn sàng" if core else "✗ thiếu " + ", ".join(m for m, v in ok.items()
                                                                if not v),
               "✓" if gop_ok else "chưa cài (tùy chọn)"),
            fg=self.P["ok_fg"] if core else self.P["bad_fg"])
        self.info_lines[2].configure(text="ffmpeg: %s" % (yt_ffmpeg_location() or "(chưa có)"),
                                     fg=self.P["muted"])

    # ----- lưu ngay khi đổi (thay nút "Lưu cài đặt") -----
    def _autosave(self, *_):
        if not getattr(self, "_autosave_on", False):
            return
        if getattr(self, "_autosave_job", None):
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(400, self._do_autosave)

    def _do_autosave(self):
        self._autosave_job = None
        self._save_cfg()
        self.set_saved.configure(text="✓ Đã lưu")
        self.after(1600, lambda: self.set_saved.configure(text="Thay đổi được lưu ngay"))

    def _open_readme(self):
        p = os.path.join(BASE_DIR, "README.md")
        if os.path.exists(p):
            os.startfile(p)

    # ================= cấu hình & đóng app =================
    def _cfg_from_vars(self):
        return {
            "model": self.model_name.get(),
            "lang": self.lang.get(),
            "out_dir": self.out_dir.get(),
            "theme": self.theme_name.get(),
            "yt_kind": YT_KIND_BY_NAME.get(self.yt_kind.get(), "video"),
            "yt_quality": YT_QUAL_BY_NAME.get(self.yt_quality.get(), "best"),
            "subs": bool(self.y_subs.get()),
            "embed": bool(self.y_embed.get()),
            "sub_lang": YT_SUB_LANG_BY_NAME.get(self.yt_sub_lang.get(), "auto"),
            "mic": self.mic_var.get(),
            "geometry": self.cfg.get("geometry") or "1200x830",
        }

    def _save_cfg(self):
        self.cfg = self._cfg_from_vars()
        save_config(self.cfg)

    def _toggle_theme(self):
        self._apply_theme()
        self._save_cfg()

    def _flip_theme(self):
        """Nút ở header: đảo theme rồi áp dụng. Radio trong Cài đặt tự set biến
        trước khi gọi _toggle_theme, nên không đảo ở đó."""
        self.theme_name.set("light" if self.theme_name.get() == "dark" else "dark")
        self._toggle_theme()

    def _reset_cfg(self):
        self.cfg = dict(DEFAULT_CFG)
        self.model_name.set(self.cfg["model"])
        self.lang.set(self.cfg["lang"])
        self.out_dir.set(self.cfg["out_dir"] or YT_DIR_DEFAULT)
        self.theme_name.set(self.cfg["theme"])
        self.yt_kind.set(YT_KIND_NAME.get(self.cfg["yt_kind"], YT_KIND_NAMES[1]))
        self.yt_quality.set({c: n for c, n in YT_QUALITIES}.get(self.cfg["yt_quality"],
                                                               YT_QUALITIES[0][1]))
        self.y_subs.set(bool(self.cfg["subs"]))
        self.y_embed.set(bool(self.cfg["embed"]))
        self.yt_sub_lang.set({c: n for c, n in YT_SUB_LANGS}.get(self.cfg["sub_lang"],
                                                                YT_SUB_LANG_NAMES[0]))
        self._apply_theme()
        self._fill_info()
        self._save_cfg()
        self.status.set("Đã khôi phục cài đặt mặc định.")
        self.set_saved.configure(text="✓ Đã khôi phục mặc định")
        self.after(1600, lambda: self.set_saved.configure(text="Thay đổi được lưu ngay"))

    def _on_close(self):
        try:
            self.cfg["geometry"] = self.geometry()
        except Exception:
            pass
        self._save_cfg()
        self.cancel_flag = True       # worker đang chạy tự dừng ở lần kiểm tra kế tiếp
        if self.recording:
            self.recorder.stop()
        self._stop_play()
        self._set_last_wav(None)      # xóa bản ghi luyện tạm (I10)
        self._yt_cancel = True
        self._yt_drop_keep()          # bản thu từng đoạn (I10)
        if self._yt_sess:
            self._yt_sess.close()     # audio gốc của phiên đọc to (I10, D-39)
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
