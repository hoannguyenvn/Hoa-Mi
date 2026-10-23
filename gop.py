"""GOP — chấm âm vị bằng mô hình acoustic (wav2vec2 CTC, phoneme tiếng Anh).

Khác với phần so từ của Whisper (chỉ là "máy nghe ra chữ gì"), ở đây:
  - Nạp model wav2vec2 đa ngữ huấn luyện trên âm vị IPA (espeak).
  - Ép buộc căn (CTC Viterbi) chuỗi âm vị MONG ĐỢI của câu mẫu vào các khung audio.
  - Với từng âm vị: so log xác suất của âm đó với âm cạnh tranh mạnh nhất
    trên đúng các khung đã căn -> GOP (log posterior ratio).
  - GOP > 0: model chắc chắn đó là âm mong đợi; GOP < 0: model nghiêng về âm khác.

Điểm 0-100 của từng âm là quy đổi logistic từ GOP, KHÔNG phải % phát âm đúng.

Để tránh báo oan do model yếu ở một số âm/giọng, khi có audio mẫu (câu mẫu do
máy đọc) app chấm cả bản mẫu rồi so: chỉ coi là "yếu" khi bản đọc của bạn kém
rõ rệt so với chính bản mẫu ở cùng vị trí. Không có bản mẫu -> dùng ngưỡng tuyệt đối.

Cần: torch + transformers + model đã tải (xem README). Thiếu -> available() = False.
"""

import json
import os

import numpy as np

import pron_en
import prosody

MODEL_ID = "facebook/wav2vec2-lv-60-espeak-cv-ft"

# Bảng âm vị IPA (chuẩn espeak) của model -> tên ARPAbet dùng trong app.
# Nhiều biến thể được gộp vào một âm vị (ví dụ T gồm cả flap ɾ) để không
# báo oan cách phát âm hợp lệ. Vài nguyên âm gộp cả biến thể ghép (eə, ɪə).
SYMS = {
    "AA": ["ɑː", "ɑ", "aː"],
    "AE": ["æ"],
    "AH": ["ʌ", "ə", "ɐ"],
    "AO": ["ɔː", "ɔ"],
    "AW": ["aʊ"],
    "AY": ["aɪ"],
    "EH": ["ɛ", "e", "eə"],
    "ER": ["ɜː", "ɜ", "ɚ"],
    "ER0": ["ɜː", "ɜ", "ɚ", "ɹ", "r", "ə"],  # "every", "winter": r thành âm tiết
    "EY": ["eɪ"],
    "IH": ["ɪ", "ɪə"],
    "IY": ["iː", "i"],
    "OW": ["oʊ", "əʊ"],
    "OY": ["ɔɪ"],
    "UH": ["ʊ", "ʊə"],
    "UW": ["uː", "u"],
    "B": ["b"],
    "CH": ["tʃ"],
    "D": ["d"],
    "DH": ["ð"],
    "F": ["f"],
    "G": ["ɡ", "g"],
    "HH": ["h"],
    "JH": ["dʒ"],
    "K": ["k"],
    "L": ["l"],
    "M": ["m"],
    "N": ["n"],
    "NG": ["ŋ"],
    "P": ["p"],
    "R": ["ɹ", "r"],
    "S": ["s"],
    "SH": ["ʃ"],
    "T": ["t", "ɾ", "ʔ"],
    "TH": ["θ"],
    "V": ["v"],
    "W": ["w"],
    "Y": ["j"],
    "Z": ["z"],
    "ZH": ["ʒ"],
}
_CLASS_LABEL = {"ER0": "ER"}

_MODEL = None
_VOCAB = None
_PHONES = None
_PH_IDS = None
_PH_COL = None
_BLANK = None
_REF_CACHE = {}
_BROKEN = False


# ------------------------------------------------------------------ sẵn sàng?
def _cached_file(name):
    try:
        from huggingface_hub import try_to_load_from_cache
        p = try_to_load_from_cache(MODEL_ID, name)
        return p if isinstance(p, str) and os.path.exists(p) else None
    except Exception:
        return None


def available():
    """Có torch + transformers? (model sẽ tự tải lần chấm đầu nếu chưa có)."""
    global _BROKEN
    if _MODEL is not None:
        return True
    if _BROKEN:
        return False
    try:
        import importlib.util as u
        return bool(u.find_spec("torch") and u.find_spec("transformers"))
    except Exception:
        return False


def _load_vocab():
    p = _cached_file("vocab.json")
    if p:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    from huggingface_hub import hf_hub_download
    with open(hf_hub_download(MODEL_ID, "vocab.json"), encoding="utf-8") as f:
        return json.load(f)


def _ensure_loaded():
    global _MODEL, _VOCAB, _PHONES, _PH_IDS, _PH_COL, _BLANK
    if _MODEL is not None:
        return
    from transformers import AutoModelForCTC

    mdl = AutoModelForCTC.from_pretrained(MODEL_ID)
    mdl.eval()
    vocab = _load_vocab()

    phones, ph_ids = [], []
    for ph, syms in SYMS.items():
        ids = [vocab[s] for s in syms if s in vocab]
        if not ids:
            continue
        phones.append(ph)
        ph_ids.append(ids)

    _MODEL = mdl
    _VOCAB = vocab
    _PHONES = phones
    _PH_IDS = ph_ids
    _PH_COL = {p: i for i, p in enumerate(phones)}
    _BLANK = int(getattr(mdl.config, "pad_token_id", 1))


def forget():
    """Giải phóng model (dùng khi test)."""
    global _MODEL, _VOCAB, _PHONES, _PH_IDS, _PH_COL, _BROKEN
    _MODEL = _VOCAB = _PHONES = _PH_IDS = _PH_COL = None
    _BROKEN = False
    _REF_CACHE.clear()


# ------------------------------------------------------------------ tiện ích
def _lse(a, axis):
    m = np.max(a, axis=axis, keepdims=True)
    m = np.where(np.isfinite(m), m, 0.0)
    return (m + np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True))).squeeze(axis)


def _class_logp(logp):
    """(T, V) -> (T, P): log xác suất cộng dồn theo từng âm vị."""
    return np.stack([_lse(logp[:, ids], axis=1) for ids in _PH_IDS], axis=1)


def _viterbi(emit, seq):
    """Căn chuỗi âm vị vào khung. emit: (T, S) log prob từng state.

    Trả (labels, score) — labels[t] = state tại khung t (chẵn = blank).
    Không cho bỏ qua khi hai âm liền nhau giống nhau (CTC).
    """
    T, S = emit.shape
    n_ph = len(seq)
    if T < n_ph:
        return None, None
    neg = -1e18
    dp = np.full(S, neg)
    dp[0] = emit[0, 0]
    if S > 1:
        dp[1] = emit[0, 1]
    skip_ok = np.zeros(S, dtype=bool)
    for k in range(1, n_ph):
        if seq[k][0] != seq[k - 1][0]:
            skip_ok[2 * k + 1] = True
    bp = np.zeros((T, S), dtype=np.uint8)
    for t in range(1, T):
        stay = dp
        step1 = np.concatenate(([neg], dp[:-1]))
        step2 = np.concatenate(([neg, neg], dp[:-2]))
        step2 = np.where(skip_ok, step2, neg)
        cand = np.stack((stay, step1, step2), axis=0)  # 3 x S
        arg = np.argmax(cand, axis=0).astype(np.uint8)
        best = cand[arg, np.arange(S)]
        dp = best + emit[t]
        bp[t] = arg
    end = int(np.argmax(dp[S - 2:])) + S - 2
    labels = np.empty(T, dtype=np.int32)
    s = end
    for t in range(T - 1, -1, -1):
        labels[t] = s
        a = bp[t, s]
        s = s - (1 if a == 1 else 2 if a == 2 else 0)
    return labels, float(dp[end])


def _score(gop):
    """GOP (log ratio, ~[-20..+6]) -> 0..100. Logistic, chỉ để so sánh tương đối."""
    return 100.0 / (1.0 + np.exp(-(gop - 0.2) / 2.2))


# ------------------------------------------------------------------ chấm
def _seq(words):
    seq, skipped = [], []
    for wi, w in enumerate(words):
        ph = pron_en.phonemes(w, raw=True)
        if not ph:
            skipped.append(w)
            continue
        show = w.strip(".,!?;:\"'()[]")
        for pi, p in enumerate(ph):
            base = p.rstrip("012")
            cls = "ER0" if (base == "ER" and p.endswith("0")) else base
            if cls not in _PH_COL:
                continue
            seq.append((cls, base, show, wi, pi, len(ph),
                        not (base == "AH" and p.endswith("0"))))
    return seq, skipped


def _run(wav_path, seq):
    """Chạy model + căn chỉnh. -> (labels, cls, all_lse) | None."""
    try:
        x, _sr = prosody.read_wav(wav_path)
        if len(x) < 1600:
            return None
        import torch
        xv = torch.from_numpy(np.asarray(x, dtype=np.float32)).float()[None]
        xv = (xv - xv.mean()) / (xv.std() + 1e-7)
        with torch.no_grad():
            logits = _MODEL(xv).logits[0]
        logp = torch.log_softmax(logits, dim=-1).numpy()
    except Exception:
        return None

    T = logp.shape[0]
    N = len(seq)
    if T < N:
        return None
    cls = _class_logp(logp)
    all_lse = _lse(logp, axis=1)
    col = np.array([_PH_COL[x[0]] for x in seq], dtype=np.int32)
    emit = np.empty((T, 2 * N + 1), dtype=np.float32)
    emit[:, 0::2] = logp[:, _BLANK][:, None]
    emit[:, 1::2] = cls[:, col]
    labels, _ = _viterbi(emit, seq)
    if labels is None:
        return None
    return labels, cls, all_lse


def _rows(seq, labels, cls, all_lse):
    other = all_lse[:, None] + np.log1p(
        -np.exp(np.clip(cls - all_lse[:, None], -60, -1e-9)))
    out = []
    for k, (ckey, ph, w, wi, pi, n, scored) in enumerate(seq):
        fr = np.where(labels == 2 * k + 1)[0]
        if len(fr) == 0:
            out.append({"ph": ph, "word": w, "wi": wi, "pi": pi, "n": n,
                        "frames": 0, "gop": None, "score": 0.0,
                        "heard": None, "deleted": True, "scored": scored})
            continue
        c = _PH_COL[ckey]
        gop = float(np.mean(cls[fr, c] - other[fr, c]))
        comp = cls[fr].mean(axis=0)
        comp[c] = -1e9
        heard = _PHONES[int(np.argmax(comp))]
        heard = _CLASS_LABEL.get(heard, heard)
        out.append({"ph": ph, "word": w, "wi": wi, "pi": pi, "n": n,
                    "frames": int(len(fr)), "gop": round(gop, 2),
                    "score": round(float(_score(gop)), 1),
                    "heard": heard, "deleted": False, "scored": scored})
    return out


def _run_cached(wav_path, seq):
    try:
        st = os.stat(wav_path)
        key = (os.path.abspath(wav_path), st.st_mtime_ns, st.st_size,
               tuple(x[0] for x in seq))
    except OSError:
        return None
    if key in _REF_CACHE:
        return _REF_CACHE[key]
    got = _run(wav_path, seq)
    rows = _rows(seq, *got) if got else None
    if len(_REF_CACHE) > 24:
        _REF_CACHE.clear()
    _REF_CACHE[key] = rows
    return rows


def score(wav_path, words, ref_wav=None):
    """words: list từ mục tiêu. ref_wav: câu mẫu (tùy chọn).

    -> dict | None: {rows, issues, ok, total, skipped, ...}
    """
    global _BROKEN
    if not available():
        return None
    try:
        _ensure_loaded()
    except Exception:
        _BROKEN = True  # thiếu model / lỗi tải: đừng thử lại mỗi lần chấm
        return None

    seq, skipped = _seq(words)
    if len(seq) < 2:
        return None
    got = _run(wav_path, seq)
    if not got:
        return None
    rows = _rows(seq, *got)

    ref_rows = _run_cached(ref_wav, seq) if ref_wav else None
    if ref_rows and len(ref_rows) == len(rows):
        for r, rr in zip(rows, ref_rows):
            r["ref_score"] = rr["score"]
            r["ref_gop"] = rr["gop"]
    else:
        ref_rows = None

    # chọn các âm "yếu": kém rõ rệt so với bản mẫu, hoặc tuyệt đối thấp
    issues = []
    for r in rows:
        if not r["scored"] or r["frames"] == 0:
            continue
        weak = False
        if ref_rows is not None and r.get("ref_gop") is not None:
            if r["score"] < 55 and r["gop"] < r["ref_gop"] - 1.5:
                weak = True
            elif r["score"] < 25 and r["gop"] < r["ref_gop"] - 0.5:
                weak = True
        else:
            if r["score"] < 50 and r["gop"] < -1.0:
                weak = True
        if weak:
            it = pron_en._issue(r["ph"], r["heard"], r["word"], r["pi"], r["n"])
            it.update({"gop": r["gop"], "score": r["score"],
                       "ref_score": r.get("ref_score"),
                       "heard": r["heard"], "frames": r["frames"],
                       "wi": r["wi"], "ph": r["ph"]})
            issues.append(it)
    issues.sort(key=lambda d: (d["score"], -d["frames"]))

    scored = [r for r in rows if r["scored"] and r["frames"] > 0]
    return {
        "rows": rows,
        "issues": issues,
        "ok": sum(1 for r in scored if r["score"] >= 55),
        "total": len(scored),
        "skipped": skipped,
        "has_ref": ref_rows is not None,
    }
