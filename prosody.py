"""Phân tích ngữ điệu (cao độ) — chỉ dùng numpy, không cần librosa/praat.

Nguyên tắc: chỉ hiển thị cái đo được, không cho "điểm ngữ điệu" giả.
  - Tách cao độ F0 bằng autocorrelation trên từng khung 40 ms (bước 10 ms).
  - Bỏ khung câm / vô thanh (không có cao độ).
  - Quy đổi sang BÁN CUNG so với trung vị của chính người nói
    (12*log2(f/median)) -> so được hình dáng câu giữa hai người khác giọng.
  - Trục thời gian chuẩn hoá 0..100% vì độ dài hai bản thu khác nhau.

Hàm chính:
    compare(ref_path, usr_path) -> dict | None
"""

import wave

import numpy as np

_REF_CACHE = {}  # (path, mtime, size) -> contour


# ------------------------------------------------------------------ đọc WAV
def read_wav(path):
    """Đọc WAV PCM -> (float32 mono [-1..1], sample_rate)."""
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v & 0x800000, v - 0x1000000, v)
        x = v.astype(np.float32) / 8388608.0
    elif sw == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError("định dạng WAV không hỗ trợ")
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)
    if sr != 16000:  # nội suy tuyến tính — đủ tốt cho việc đo F0
        t_old = np.arange(len(x), dtype=np.float64) / sr
        n_new = int(round(len(x) * 16000.0 / sr))
        t_new = np.arange(n_new, dtype=np.float64) / 16000.0
        x = np.interp(t_new, t_old, x).astype(np.float32)
        sr = 16000
    return x, sr


# ------------------------------------------------------------------ F0
def _clean(f0):
    """Lọc trung vị 5 khung + sửa lỗi nhảy quãng tám so với lân cận."""
    bad = np.isnan(f0)
    idx = np.where(~bad)[0]
    if len(idx) < 3:
        return f0
    vals = f0[idx].astype(np.float64)
    sm = vals.copy()
    for k in range(len(vals)):
        lo, hi = max(0, k - 2), min(len(vals), k + 3)
        sm[k] = np.median(vals[lo:hi])
    for k in range(1, len(sm) - 1):
        nb = np.median(sm[max(0, k - 2):k + 3])
        if nb <= 0:
            continue
        if sm[k] > 1.8 * nb:
            sm[k] /= 2.0
        elif sm[k] < 0.55 * nb:
            sm[k] *= 2.0
    f0[idx] = sm
    return f0


def f0_track(x, sr, fmin=60.0, fmax=420.0, frame_ms=40, hop_ms=10):
    """Trả (times, f0) — f0 = nan ở khung câm/vô thanh."""
    frame = int(sr * frame_ms / 1000)
    hop = int(sr * hop_ms / 1000)
    if len(x) < frame:
        return np.array([]), np.array([])
    n = 1 + (len(x) - frame) // hop
    win = np.hanning(frame).astype(np.float32)
    nfft = 1
    while nfft < 2 * frame:
        nfft *= 2
    lag_min = max(2, int(sr / fmax))
    lag_max = min(frame - 2, int(sr / fmin))
    if lag_max <= lag_min:
        return np.array([]), np.array([])

    rms = np.empty(n, dtype=np.float64)
    f0 = np.full(n, np.nan, dtype=np.float64)
    for i in range(n):
        seg = x[i * hop:i * hop + frame]
        rms[i] = float(np.sqrt(np.mean(seg * seg)))
        w = (seg - seg.mean()) * win
        if rms[i] <= 0:
            continue
        spec = np.fft.rfft(w, nfft)
        ac = np.fft.irfft(spec * np.conj(spec), nfft)[:frame]
        if ac[0] <= 1e-12:
            continue
        ac = ac / ac[0]
        seg_ac = ac[lag_min:lag_max]
        k = int(np.argmax(seg_ac)) + lag_min
        peak = float(ac[k])
        if peak < 0.32:
            continue
        # nội suy parabol để mịn hơn
        if 0 < k < frame - 1:
            a, b, c = ac[k - 1], ac[k], ac[k + 1]
            den = a - 2 * b + c
            delta = 0.5 * (a - c) / den if abs(den) > 1e-9 else 0.0
        else:
            delta = 0.0
        lag = k + delta
        if lag <= 0:
            continue
        hz = sr / lag
        if fmin <= hz <= fmax:
            f0[i] = hz

    thr = max(0.004, 0.10 * float(np.percentile(rms, 95)))
    f0[rms < thr] = np.nan
    f0 = _clean(f0)
    times = (np.arange(n) * hop + frame / 2.0) / sr
    return times, f0


# ------------------------------------------------------------------ contour
def contour(path):
    """-> {"t": [...0..1], "st": [...], "dur": giây, "median": Hz, "voiced": 0..1}."""
    x, sr = read_wav(path)
    times, f0 = f0_track(x, sr)
    if len(f0) == 0:
        return None
    ok = ~np.isnan(f0)
    if ok.sum() < 6:
        return None
    med = float(np.median(f0[ok]))
    if med <= 0:
        return None
    st = 12.0 * np.log2(f0 / med)  # giữ nan
    dur = len(x) / float(sr)
    t = times / max(times[-1], 1e-6)
    vt = times[ok]
    return {
        "t": [round(float(v), 4) for v in t],
        "st": [None if np.isnan(v) else round(float(v), 2) for v in st],
        "dur": round(dur, 2),
        # khoảng có giọng (bỏ im lặng đầu/cuối) — dùng cho câu "tốc độ đọc" (S-5b)
        "span": round(float(vt[-1] - vt[0]), 2),
        "median": round(med, 1),
        "voiced": round(float(ok.mean()), 3),
    }


def contour_cached(path):
    try:
        st = __import__("os").stat(path)
        key = (path, st.st_mtime_ns, st.st_size)
    except OSError:
        return None
    if key in _REF_CACHE:
        return _REF_CACHE[key]
    try:
        c = contour(path)
    except Exception:
        c = None
    if len(_REF_CACHE) > 40:
        _REF_CACHE.clear()
    _REF_CACHE[key] = c
    return c


# ------------------------------------------------------------------ so sánh
def _grid(c, n=101):
    pts = [(t, s) for t, s in zip(c["t"], c["st"]) if s is not None]
    if len(pts) < 8:
        return None
    pts.sort()
    xs = np.linspace(0.0, 1.0, n)
    ys = np.interp(xs, [p[0] for p in pts], [p[1] for p in pts])
    return ys


def _dtw(a, b, band=15):
    n, m = len(a), len(b)
    inf = 1e18
    D = np.full((n + 1, m + 1), inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(max(1, i - band), min(m, i + band) + 1):
            D[i, j] = abs(a[i - 1] - b[j - 1]) + min(
                D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    if not np.isfinite(D[n, m]):
        return None
    return float(D[n, m] / max(n, m))


def _final_slope(c, frac=0.3):
    pts = [(t, s) for t, s in zip(c["t"], c["st"])
           if s is not None and t >= 1.0 - frac]
    if len(pts) < 5:
        return None
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    if np.ptp(xs) < 1e-6:
        return None
    a = float(np.polyfit(xs, ys, 1)[0])
    return a / 10.0  # bán cung trên mỗi 10% độ dài câu


def _range(c):
    v = [s for s in c["st"] if s is not None]
    if len(v) < 4:
        return None
    return float(max(v) - min(v))


def compare(ref_path, usr_path):
    """So đường cao độ bản mẫu với bản người đọc. Lỗi/thiếu dữ liệu -> None."""
    try:
        ref = contour_cached(ref_path)
        usr = contour(usr_path)
    except Exception:
        return None
    if not ref or not usr:
        return None
    ga, gb = _grid(ref), _grid(usr)
    diff = _dtw(ga, gb) if (ga is not None and gb is not None) else None
    return {
        "ref": {"t": ref["t"], "st": ref["st"]},
        "usr": {"t": usr["t"], "st": usr["st"]},
        "dur_ref": ref["dur"], "dur_usr": usr["dur"],
        "span_ref": ref.get("span"), "span_usr": usr.get("span"),
        "med_ref": ref["median"], "med_usr": usr["median"],
        "range_ref": _range(ref), "range_usr": _range(usr),
        "final_ref": _final_slope(ref), "final_usr": _final_slope(usr),
        "diff": None if diff is None else round(diff, 2),
        "voiced_ref": ref["voiced"], "voiced_usr": usr["voiced"],
    }


# ------------------------------------------------------------------ trọng âm từ (S-5b, D-34)
STRESS_MIN_WORDS = 3     # ít hơn số từ có mốc thời gian này → không nhận xét trọng âm
STRESS_TIE = 0.5         # từ thứ hai cũng tính là "nhấn" nếu kém từ đầu < 0,5 (đơn vị z)


def stress_from_features(db, st):
    """Từ được nhấn từ cường độ (dB) + cao độ (bán cung) của từng từ. Hàm thuần.

    Mỗi đại lượng quy về z-score TRONG câu của chính người nói (I5); từ thiếu cao độ chỉ
    tính cường độ. Trả (prominence list, chỉ số từ được nhấn) — tối đa 2 từ.
    """
    db = np.asarray(db, dtype=np.float64)
    if len(db) < STRESS_MIN_WORDS:
        return [], []
    zl = (db - db.mean()) / max(1.0, float(db.std()))
    have = [v for v in st if v is not None]
    if len(have) >= 2:
        mu, sd = float(np.mean(have)), max(0.5, float(np.std(have)))
        zp = np.array([0.0 if v is None else (v - mu) / sd for v in st])
    else:
        zp = np.zeros(len(db))
    prom = zl + zp
    order = [int(i) for i in np.argsort(-prom)]
    top = [order[0]]
    if len(order) > 1 and prom[order[0]] - prom[order[1]] < STRESS_TIE:
        top.append(order[1])
    return [round(float(v), 2) for v in prom], top


def word_stress(path, words):
    """words = [{"s", "e"} giây, ...] (mốc Whisper) → {"prom": [...], "top": [chỉ số]} | None.

    Cường độ = RMS dB trên đoạn từ; cao độ = trung vị bán cung (so trung vị cả câu của
    chính người nói) của các khung có giọng trong đoạn. Chỉ mô tả, không chấm (D-34).
    """
    spans = [(float(w["s"]), float(w["e"])) for w in (words or [])
             if w.get("s") is not None and w.get("e") is not None and w["e"] > w["s"]]
    if len(spans) < STRESS_MIN_WORDS or len(spans) != len(words):
        return None
    x, sr = read_wav(path)
    times, f0 = f0_track(x, sr)
    ok = ~np.isnan(f0) if len(f0) else np.array([], dtype=bool)
    med = float(np.median(f0[ok])) if ok.sum() >= 6 else None
    db, st = [], []
    for s, e in spans:
        seg = x[int(s * sr):max(int(s * sr) + 1, int(e * sr))]
        rms = float(np.sqrt(np.mean(seg * seg))) if len(seg) else 0.0
        db.append(20.0 * np.log10(max(rms, 1e-6)))
        v = None
        if med:
            sel = (times >= s) & (times <= e) & ok
            if sel.sum() >= 2:
                v = float(np.median(12.0 * np.log2(f0[sel] / med)))
        st.append(v)
    prom, top = stress_from_features(db, st)
    if not top:
        return None
    return {"prom": prom, "top": top}


# ------------------------------------------------------------------ ngữ điệu theo câu (D-44)
# Đo 2026-10-24 trên 4 đoạn đọc thật + audio TED: HƯỚNG giọng cuối câu đổi chiều khi đổi cửa sổ
# 0,3 → 0,6 s (giọng khàn cuối câu, nhạc nền) → KHÔNG kết luận lên/xuống cuối câu. DẢI cao độ
# (phân vị 90 − 10, bán cung) ổn định trên hàng trăm khung → dùng để nói "giọng đều".
PITCH_MIN_FRAMES = 30   # < 30 khung có giọng (~0,3 s) trong câu → không nhận xét câu đó
CURVE_POINTS = 48       # số điểm đường cao độ thu nhỏ mỗi câu


def pitch_track(path, start=None, end=None):
    """F0 của file (hoặc đoạn start..end giây) → {"t": [giây tuyệt đối], "st": [bán cung | None]}.

    Bán cung so với trung vị CHÍNH người nói trong đoạn đó (I5). None nếu quá ít khung có giọng."""
    x, sr = read_wav(path)
    a = int(max(0.0, start or 0.0) * sr)
    b = len(x) if end is None else min(len(x), int(end * sr))
    times, f0 = f0_track(x[a:b], sr)
    ok = ~np.isnan(f0) if len(f0) else np.array([], dtype=bool)
    if ok.sum() < PITCH_MIN_FRAMES:
        return None
    st = 12.0 * np.log2(f0 / float(np.median(f0[ok])))
    off = a / float(sr)
    return {"t": [round(float(v) + off, 3) for v in times],
            "st": [None if np.isnan(v) else round(float(v), 2) for v in st]}


def segment_pitch(track, start, end, n=CURVE_POINTS):
    """Một câu (start..end giây) của pitch_track → {"range": bán cung, "curve": [n điểm | None],
    "frames": số khung có giọng} hoặc None. Hàm thuần.

    range = phân vị 90 − 10 (bền với khung lỗi); curve = trung vị theo n ô thời gian đều nhau
    (None = ô không có giọng) để vẽ đường cao độ thu nhỏ, cùng thang cho người nói và người học."""
    if not track or start is None or end is None or end <= start:
        return None
    pts = [(t, s) for t, s in zip(track["t"], track["st"])
           if s is not None and start <= t <= end]
    if len(pts) < PITCH_MIN_FRAMES:
        return None
    v = np.array([s for _t, s in pts])
    curve = []
    edges = np.linspace(start, end, n + 1)
    for i in range(n):
        cell = [s for t, s in pts if edges[i] <= t < edges[i + 1]]
        curve.append(round(float(np.median(cell)), 2) if cell else None)
    return {"range": round(float(np.percentile(v, 90) - np.percentile(v, 10)), 1),
            "curve": curve, "frames": len(pts)}
