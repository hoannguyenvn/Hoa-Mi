"""Phân tích âm vị tiếng Anh cho tab "Luyện phát âm".

Nguyên tắc: chỉ kết luận điều có bằng chứng.
  - Từ mục tiêu -> chuỗi âm vị (CMUdict).
  - Từ máy NGHE ĐƯỢC -> chuỗi âm vị (CMUdict).
  - Căn chỉnh 2 chuỗi (Needleman-Wunsch) -> biết cụ thể âm nào bị thay / bị nuốt.
Không so phổ, không so formant, không cho điểm "timbre" giả.

Dùng:
    import pron_en
    rep = pron_en.analyze_pairs([(0, "think", "tink"), (2, "this", "dis")])
    rep["issues"]  -> [{i, exp, got, ipa_exp, ipa_got, word, pos, tip, label, approx}, ...]
    rep["counts"]  -> {"TH": 1, "DH": 1}
    rep["top"]     -> [{"ph": "TH", "ipa": "θ", "n": 1, "heard": ["t"], "tip": ...}, ...]
"""

import difflib
import re

# ---------------------------------------------------------------- ARPAbet -> IPA
ARPABET_IPA = {
    "AA": "ɑː", "AE": "æ", "AH": "ʌ", "AO": "ɔː", "AW": "aʊ", "AY": "aɪ",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "EH": "e", "ER": "ɜː",
    "EY": "eɪ", "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "iː",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ",
    "OW": "əʊ", "OY": "ɔɪ", "P": "p", "R": "ɹ", "S": "s", "SH": "ʃ",
    "T": "t", "TH": "θ", "UH": "ʊ", "UW": "uː", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH",
          "IY", "OW", "OY", "UH", "UW"}

# ---------------------------------------------------------------- từ điển
_DICT = None
_DICT_TRIED = False


def _load_dict():
    """Nạp CMUdict một lần. Không có thư viện -> tra bảng tay nhỏ."""
    global _DICT, _DICT_TRIED
    if _DICT_TRIED:
        return _DICT
    _DICT_TRIED = True
    try:
        import cmudict
        _DICT = cmudict.dict()
    except Exception:
        _DICT = {}
    return _DICT


# Vài từ hay gặp khi máy nghe sai mà CMUdict không có (bổ sung tay).
_EXTRA = {
    "tink": "T IH NG K", "ticker": "T IH K ER", "tank": "T AE NG K",
    "dis": "D IH S", "dat": "D AE T", "sink": "S IH NG K",
    "sip": "S IH P", "seep": "S IY P", "wery": "W EH R IY",
    "tree": "T R IY", "trees": "T R IY Z", "free": "F R IY",
    "sree": "S R IY", "shree": "SH R IY", "tousand": "T AW Z AH N D",
    "tanks": "T AE NG K S",
}


def phonemes(word, raw=False):
    """Trả về list âm vị ARPAbet hoặc None.

    raw=False: đã bỏ số trọng âm (để so sánh).
    raw=True:  giữ số 0/1/2 (để hiển thị IPA có dấu nhấn).
    """
    w = re.sub(r"[^a-z']", "", (word or "").lower())
    if not w:
        return None
    d = _load_dict()
    cand = d.get(w) if d else None
    if cand:
        return list(cand[0]) if raw else [p.rstrip("012") for p in cand[0]]
    ex = _EXTRA.get(w)
    if ex:
        return ex.split()
    return None


def ipa(phs, stress=False):
    """Chuỗi âm vị -> IPA để hiển thị."""
    out = []
    for p in phs or []:
        base = p.rstrip("012")
        s = ARPABET_IPA.get(base, base.lower())
        if stress and p[-1:] == "1":
            s = "ˈ" + s
        out.append(s)
    return "".join(out)


def _render(p, stressed=False):
    base = p.rstrip("012")
    digit = p[-1:] if p[-1:].isdigit() else ""
    if base == "AH" and digit == "0":
        return "ə"
    if base == "ER" and digit == "0":
        return "ə"
    s = ARPABET_IPA.get(base, base.lower())
    return ("ˈ" + s) if stressed else s


def word_ipa(word):
    """IPA của 1 từ; dấu nhấn đặt ở đầu âm tiết, chỉ khi từ có ≥2 nguyên âm."""
    ph = phonemes(word, raw=True)
    if not ph:
        return ""
    vowels = [i for i, p in enumerate(ph) if p.rstrip("012") in VOWELS]
    if len(vowels) < 2:
        return "".join(_render(p) for p in ph)
    # âm tiết mang trọng âm chính (digit 1), không có thì lấy nguyên âm đầu
    stress_i = next((i for i in vowels if ph[i][-1:] == "1"), vowels[0])
    onset = stress_i
    while onset > 0 and ph[onset - 1].rstrip("012") not in VOWELS:
        onset -= 1
    out = []
    for i, p in enumerate(ph):
        if i == onset:
            out.append("ˈ" + _render(p))
        else:
            out.append(_render(p))
    return "".join(out)


# ---------------------------------------------------------------- căn chỉnh
def align(a, b):
    """Needleman-Wunsch: trả [(a_i|None, b_j|None, 'same'|'sub'|'del'|'ins')]."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j - 1] + cost,
                           dp[i - 1][j] + 1,
                           dp[i][j - 1] + 1)
    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (
                0 if a[i - 1] == b[j - 1] else 1):
            ops.append((a[i - 1], b[j - 1],
                        "same" if a[i - 1] == b[j - 1] else "sub"))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append((a[i - 1], None, "del"))
            i -= 1
        else:
            ops.append((None, b[j - 1], "ins"))
            j -= 1
    return list(reversed(ops))


# ---------------------------------------------------------------- gợi ý sửa
# (âm mục tiêu, âm nghe được) -> gợi ý. None = mất hẳn âm đó.
TIPS = {
    ("TH", "T"): "/θ/ → /t/: đặt ĐẦU LƯỠI GIỮA hai răng cửa rồi thổi hơi, "
                 "đừng chạm lợi như /t/.",
    ("TH", "S"): "/θ/ → /s/: phải THÒ đầu lưỡi ra giữa hai răng; /s/ thì lưỡi "
                 "ở trong miệng.",
    ("TH", "F"): "/θ/ → /f/: đừng chạm môi vào răng; đầu lưỡi giữa hai răng.",
    ("TH", "D"): "/θ/ → /d/: âm này KHÔNG rung dây thanh, và lưỡi phải thò ra.",
    ("TH", None): "Mất /θ/ ở cuối: vẫn phải đưa lưỡi ra giữa răng rồi thổi hơi.",
    ("DH", "D"): "/ð/ → /d/: đặt lưỡi giữa hai răng và RUNG dây thanh "
                 "(đặt tay lên cổ để cảm nhận).",
    ("DH", "Z"): "/ð/ → /z/: lưỡi phải thò ra giữa răng, không rụt vào trong.",
    ("DH", None): "Mất /ð/: giữ lưỡi giữa răng và rung đến hết âm.",
    ("SH", "S"): "/ʃ/ → /s/: CHU MÔI tròn, lưỡi lùi ra sau; /s/ thì môi bẹt, "
                 "lưỡi gần lợi trên.",
    ("SH", "CH"): "/ʃ/ → /tʃ/: bỏ phần 'bật' đầu lưỡi, chỉ giữ luồng hơi xát.",
    ("SH", None): "Mất /ʃ/: chu môi và giữ hơi xát đến cuối từ.",
    ("S", "SH"): "/s/ → /ʃ/: môi bẹt (không chu), đầu lưỡi gần lợi trên.",
    ("S", "Z"): "/s/ → /z/: âm /s/ KHÔNG rung dây thanh.",
    ("Z", "S"): "/z/ → /s/: phải RUNG dây thanh — sờ cổ thấy rung mới đúng.",
    ("Z", "D"): "/z/ → /d/: đây là âm xát, giữ luồng hơi, không bật thành /d/.",
    ("V", "W"): "/v/ → /w/: RĂNG TRÊN chạm nhẹ MÔI DƯỚI rồi rung; /w/ chỉ "
                "tròn môi.",
    ("V", "B"): "/v/ → /b/: đừng bặm hai môi; răng trên chạm môi dưới.",
    ("V", "F"): "/v/ → /f/: giữ rung dây thanh (sờ cổ) khi đọc /v/.",
    ("W", "V"): "/w/ → /v/: không chạm răng vào môi, chỉ tròn môi rồi mở.",
    ("R", "L"): "/r/ → /l/: lưỡi CONG LÊN nhưng KHÔNG chạm vòm; /l/ thì chạm lợi.",
    ("R", "W"): "/r/ → /w/: cong đầu lưỡi lên, đừng chỉ tròn môi.",
    ("L", "R"): "/l/ → /r/: đầu lưỡi phải CHẠM lợi trên rồi bật ra.",
    ("L", "N"): "/l/ → /n/: hơi thoát ra HAI BÊN lưỡi, không qua mũi.",
    ("N", "L"): "/n/ → /l/: bít kín đường miệng, hơi thoát qua MŨI.",
    ("N", "NG"): "/n/ → /ŋ/: âm cuối -n thì đầu lưỡi chạm lợi; -ng (ŋ) thì "
                 "gốc lưỡi chạm vòm mềm.",
    ("NG", "N"): "/ŋ/ → /n/: gốc lưỡi phải chạm vòm mềm, không phải đầu lưỡi.",
    ("AE", "E"): "/æ/ → /e/: MỞ MIỆNG RỘNG, hạ hàm, kéo môi sang hai bên.",
    ("AE", "A"): "/æ/ → /ɑː/: miệng mở ngang (không mở tròn), lưỡi đưa ra trước.",
    ("IH", "IY"): "/ɪ/ → /iː/: /ɪ/ NGẮN và lơi, không kéo dài, môi không căng.",
    ("IH", "E"): "/ɪ/ → /e/: lưỡi cao hơn, miệng hẹp hơn /e/.",
    ("IY", "IH"): "/iː/ → /ɪ/: kéo DÀI và căng môi rộng hơn.",
    ("UH", "UW"): "/ʊ/ → /uː/: /ʊ/ ngắn, môi hơi tròn; /uː/ dài, môi tròn rõ.",
    ("UW", "UH"): "/uː/ → /ʊ/: kéo dài và tròn môi hơn.",
    ("AH", "A"): "/ʌ/ → /ɑː/: /ʌ/ ngắn, miệng mở vừa, lưỡi giữa.",
    ("ER", "A"): "/ɜː/ → /ə/: cong lưỡi nhẹ và giữ âm dài hơn.",
    ("CH", "SH"): "/tʃ/ → /ʃ/: phải có phần BẬT đầu lưỡi (như 'ch').",
    ("CH", "T"): "/tʃ/ → /t/: thêm luồng hơi xát sau khi bật.",
    ("JH", "Z"): "/dʒ/ → /z/: bắt đầu bằng phần bật như /d/ rồi mới xát.",
    ("JH", "Y"): "/dʒ/ → /j/: phải có tiếng bật + xát, không chỉ lướt.",
    ("P", None): "/p/ cuối bị nuốt: BẬT môi rõ rồi mới kết thúc từ.",
    ("T", None): "/t/ cuối bị nuốt: bật đầu lưỡi rõ ở cuối từ.",
    ("K", None): "/k/ cuối bị nuốt: bật gốc lưỡi rõ ở cuối từ.",
    ("B", "P"): "/b/ cuối mất rung: giữ dây thanh rung đến hết.",
    ("D", "T"): "/d/ cuối mất rung: giữ rung dây thanh đến hết.",
    ("G", "K"): "/ɡ/ cuối mất rung: giữ rung dây thanh đến hết.",
    ("F", "P"): "/f/ → /p/: răng trên chạm môi dưới, giữ hơi xát.",
    ("M", None): "Mất /m/ cuối: ngậm môi và giữ âm mũi.",
    ("Z", None): "Mất /z/ cuối: giữ âm xát và rung (quan trọng với số nhiều).",
    ("S", None): "Mất /s/ cuối: giữ hơi xát (quan trọng với số nhiều).",
    ("D", None): "Mất /d/ cuối: bật đầu lưỡi và rung.",
}

# Chữ cái (đoạn bị đổi) -> âm vị ARPAbet tương ứng, để vẫn báo được dạng /θ/ → [t]
# khi từ máy nghe được không có trong từ điển.
_LETTER_PH = {
    "t": "T", "d": "D", "s": "S", "z": "Z", "f": "F", "v": "V", "p": "P",
    "b": "B", "k": "K", "c": "K", "g": "G", "l": "L", "r": "R", "n": "N",
    "m": "M", "w": "W", "j": "JH", "ch": "CH", "sh": "SH", "th": "TH",
    "ng": "NG", "y": "Y", "h": "HH",
}

# Gợi ý khi máy nghe ra một từ lạ (không có trong từ điển) — chỉ đoán theo chữ.
LETTER_TIPS = {
    ("th", "t"): "Nghe thành 't…' — nghi mất /θ/ (lưỡi phải thò ra giữa răng).",
    ("th", "s"): "Nghe thành 's…' — nghi /θ/ bị đọc thành /s/ (lưỡi phải thò ra).",
    ("th", "d"): "Nghe thành 'd…' — nghi /ð/ bị đọc thành /d/ (phải rung).",
    ("th", "z"): "Nghe thành 'z…' — nghi /ð/ bị đọc thành /z/ (lưỡi thò ra).",
    ("th", "f"): "Nghe thành 'f…' — nghi /θ/ bị đọc thành /f/.",
    ("sh", "s"): "Nghe thành 's…' — nghi /ʃ/ bị đọc thành /s/ (phải chu môi).",
    ("ch", "s"): "Nghe thành 's…' — nghi /tʃ/ mất phần bật.",
    ("v", "w"): "Nghe thành 'w…' — nghi /v/ bị đọc thành /w/ (răng trên chạm môi dưới).",
    ("v", "b"): "Nghe thành 'b…' — nghi /v/ bị đọc thành /b/.",
    ("z", "s"): "Nghe thành 's…' — nghi /z/ mất rung.",
    ("g", "k"): "Nghe thành '…k' — nghi /ɡ/ cuối mất rung (giữ dây thanh rung đến hết từ).",
    ("d", "t"): "Nghe thành '…t' — nghi /d/ cuối mất rung (giữ dây thanh rung đến hết từ).",
    ("b", "p"): "Nghe thành '…p' — nghi /b/ cuối mất rung (giữ dây thanh rung đến hết từ).",
    ("r", "l"): "Nghe thành 'l…' — nghi /r/ bị đọc thành /l/.",
    ("l", "r"): "Nghe thành 'r…' — nghi /l/ bị đọc thành /r/.",
    ("n", "l"): "Nghe thành 'l…' — nghi /n/ bị đọc thành /l/.",
    ("l", "n"): "Nghe thành 'n…' — nghi /l/ bị đọc thành /n/.",
}


def _pos_label(idx, n):
    if n <= 1:
        return "âm"
    if idx == 0:
        return "đầu từ"
    if idx >= n - 1:
        return "cuối từ"
    return "giữa từ"


def _issue(exp, got, word, idx, n, approx=False):
    label = "/%s/" % ARPABET_IPA.get(exp, exp.lower())
    if got:
        label += " → [%s]" % ARPABET_IPA.get(got, got.lower())
    else:
        label += " bị mất"
    tip = TIPS.get((exp, got))
    if not tip:
        if got:
            tip = ("/X/ đọc thành /Y/: nghe lại âm mẫu và đọc chậm từng âm."
                   .replace("/X/", "/%s/" % ARPABET_IPA.get(exp, exp.lower()))
                   .replace("/Y/", "[%s]" % ARPABET_IPA.get(got, got.lower())))
        else:
            tip = ("Mất âm /%s/ — đọc chậm và giữ âm đó đến hết từ."
                   % ARPABET_IPA.get(exp, exp.lower()))
    return {
        "exp": exp, "got": got, "word": word, "pos": _pos_label(idx, n),
        "ipa_exp": ARPABET_IPA.get(exp, ""), "ipa_got": ARPABET_IPA.get(got, ""),
        "label": label, "tip": tip, "approx": approx,
        "kind": "vowel" if exp in VOWELS else "cons",
    }


def _letter_issues(exp_w, got_w, exp_ph):
    """Từ nghe được không có trong từ điển: chỉ suy theo chữ, đánh dấu approx."""
    e, g = exp_w.lower(), got_w.lower()
    if not e or not g or e == g:
        return []
    # tìm đoạn khác nhau đầu tiên
    i = 0
    while i < min(len(e), len(g)) and e[i] == g[i]:
        i += 1
    if i == len(e) or i == len(g):
        # một từ là tiền tố của từ kia -> mất âm cuối
        short, long_ = (e, g) if len(e) < len(g) else (g, e)
        if exp_ph:
            return [_issue(exp_ph[-1], None, exp_w, len(exp_ph) - 1, len(exp_ph),
                           approx=True)]
        return []
    a, b = e[i:i + 2], g[i:i + 2]
    for (pa, pb), tip in LETTER_TIPS.items():
        if a.startswith(pa) and b.startswith(pb):
            idx = 0 if i == 0 else max(0, len(exp_ph) - 1)
            ph = exp_ph[idx] if exp_ph else None
            got_ph = _LETTER_PH.get(pb)
            if ph and got_ph and (ph, got_ph) in TIPS:
                return [_issue(ph, got_ph, exp_w, idx, len(exp_ph), approx=True)]
            it = _issue(ph or "?", None, exp_w, idx, len(exp_ph or [1]), approx=True)
            it["label"] = "%s → [%s]" % (pa, pb)
            it["tip"] = tip
            it["ipa_exp"], it["ipa_got"] = pa, pb
            return [it]
    return []


def _letters(w):
    return re.sub(r"[^a-z]", "", (w or "").lower())


def compare_words(exp_word, got_word):
    """So 1 cặp từ. Trả list issue (rỗng nếu không thấy khác biệt âm vị)."""
    e = phonemes(exp_word)
    g = phonemes(got_word)
    if not e:
        return []
    if not g:
        return _letter_issues(exp_word, got_word, e)

    # Máy nghe ra đúng phần ĐẦU của từ (vd "cat" -> "ca", "cats" -> "cat"):
    # đây là mất âm cuối, không phải đổi nguyên âm. Báo đúng cái bị mất.
    ew, gw = _letters(exp_word), _letters(got_word)
    if gw and ew.startswith(gw) and len(ew) > len(gw) and len(e) > len(g):
        k = min(2, len(e) - len(g))
        return [_issue(ph, None, exp_word, len(e) - k + j, len(e))
                for j, ph in enumerate(e[-k:])]
    ops = align(e, g)
    out = []
    n = len(e)
    for k, (a, b, tag) in enumerate(ops):
        if tag == "same":
            continue
        if tag == "sub":
            out.append(_issue(a, b, exp_word, k, n))
        elif tag == "del":
            # bỏ âm cuối / phụ âm cuối là lỗi nặng; bỏ âm giữa cũng báo
            out.append(_issue(a, None, exp_word, k, n))
        # insertion: máy nghe thêm âm -> thường do ASR, bỏ qua để khỏi nhiễu
    return out


def analyze_pairs(pairs):
    """pairs: [(chỉ_số_item, từ_mục_tiêu, từ_nghe_được), ...].

    Trả về dict: issues (kèm 'i'), counts, top, by_phoneme, unknown.
    """
    issues = []
    unknown = []
    for idx, exp_w, got_w in pairs:
        if not exp_w:
            continue
        if not got_w:
            continue
        got = compare_words(exp_w, got_w)
        if not got:
            if phonemes(got_w) is None:
                unknown.append(got_w)
            continue
        for it in got:
            it["i"] = idx
            it["heard_word"] = got_w
            issues.append(it)

    # Phụ âm trước, nguyên âm sau: phụ âm là bằng chứng chắc hơn (ASR dễ nhầm
    # nguyên âm), nên cho người học thấy lỗi chắc chắn trước.
    issues.sort(key=lambda it: it.get("kind") == "vowel")

    counts = {}
    for it in issues:
        counts[it["exp"]] = counts.get(it["exp"], 0) + 1

    groups = {}
    for it in issues:
        g = groups.setdefault(it["exp"], {"ph": it["exp"],
                                          "ipa": it["ipa_exp"],
                                          "n": 0, "heard": [], "tip": it["tip"],
                                          "words": []})
        g["n"] += 1
        if it["ipa_got"] and it["ipa_got"] not in g["heard"]:
            g["heard"].append(it["ipa_got"])
        if it["word"] not in g["words"]:
            g["words"].append(it["word"])
    top = sorted(groups.values(), key=lambda x: (-x["n"], x["ph"]))
    return {"issues": issues, "counts": counts, "top": top,
            "by_phoneme": groups, "unknown": unknown}


# ---------------------------------------------------------------- mẫu lỗi hay gặp (người Việt)
# Gom lỗi từng từ thành MẪU để người học sửa một thói quen thay vì từng từ (D-42).
# Thứ tự = thứ tự ưu tiên hiển thị khi số từ bằng nhau.
PATTERNS = {
    "final": ("Âm cuối & -s số nhiều",
              "Tiếng Việt không bật phụ âm cuối nên ta hay nuốt /s z t d k/. Đọc rõ âm cuối "
              "như có thêm chút hơi: molecule-s, contain-s, ask-ed. Số nhiều và -s của động "
              "từ làm đổi nghĩa câu."),
    "th": ("Âm th — /θ/ /ð/",
           "Thò đầu lưỡi ra giữa hai răng rồi thổi hơi: /θ/ (think) không rung, /ð/ (the, "
           "these, that) rung dây thanh. Đừng thay bằng t, d hay z."),
    "nl": ("N đọc thành L",
           "/n/ đầu từ: đầu lưỡi bít kín lợi trên, hơi ra MŨI — bịt mũi thấy nghẹt là đúng. "
           "nose ≠ lows, night ≠ light."),
    "diph": ("Nguyên âm đôi /eɪ/ /oʊ/ /aɪ/",
             "Nguyên âm đôi phải TRƯỢT từ âm đầu sang âm sau: bacon = BAY-kən (e→i), odor = "
             "OH-dər (ô→u). Đừng dừng ở một âm (back, odd)."),
    "cluster": ("Cụm phụ âm đầu (sm-, st-, sn-…)",
                "Đọc liền hai phụ âm, không bỏ âm nào và không chèn nguyên âm: s-mell, "
                "s-niff, s-tinky. Bắt đầu bằng /s/ xì nhẹ rồi nối ngay âm sau."),
    "short": ("Từ ngắn bị nuốt",
              "Từ ngắn (is, an, of, the…) đọc nhẹ và nhanh nhưng vẫn phải có: “which IS AN "
              "energy source”. Nghe lại câu mẫu để bắt cách nối các từ này."),
}
SHORT_WORDS = {"a", "an", "the", "of", "to", "in", "on", "at", "is", "are", "am", "be",
               "was", "were", "up", "and", "or", "for", "as", "it", "its", "by", "with",
               "from", "that", "this", "but", "so", "if", "we", "you", "he", "she", "they",
               "i", "me", "my", "our", "your", "can", "do", "has", "have", "had", "not"}
# Từ chức năng: tiếng Anh đọc lướt, nhẹ (dạng yếu /tə/ /əv/ /ðə/) — dùng cho nhịp (D-45)
FUNCTION_WORDS = SHORT_WORDS | {"than", "their", "them", "there", "which", "who", "about",
                                "into", "will", "would", "could", "should", "been", "does",
                                "did", "his", "her", "its", "us", "some", "such", "then"}
_DIPH = {"EY", "OW", "AY", "AW", "OY"}
PATTERN_MIN_SIM = 0.3   # giống nhau (âm vị) dưới mức này → coi là máy nghe nhầm, không xếp mẫu
# (much→"two" 0, trash→"just" 0,25 bị loại; nose→"lobe" 0,33 vẫn là n→l)


def error_patterns(exp_word, got_word):
    """Từ mẫu vs từ máy nghe → [mã mẫu lỗi] (có thể nhiều, có thể rỗng). Hàm thuần.

    got_word None/"" = bỏ sót từ: chỉ tính "short" khi là từ ngắn. Từ nghe được không có
    trong CMUdict → chỉ đoán theo chữ cái (âm cuối, n→l, th, cụm đầu)."""
    ew = _letters(exp_word or "")
    if not ew:
        return []
    if not got_word:
        return ["short"] if ew in SHORT_WORDS else []
    gw = _letters(got_word)
    e, g = phonemes(exp_word), phonemes(got_word)
    out = []
    # máy nghe ra một từ khác hẳn (much → "two") là nghe nhầm, không phải thói quen phát âm
    sim = difflib.SequenceMatcher(None, e, g).ratio() if (e and g) else \
        difflib.SequenceMatcher(None, ew, gw).ratio()
    if sim < PATTERN_MIN_SIM:
        return []
    if e and g:
        ops = align(e, g)

        def tail(ph):      # số phụ âm ở cuối từ; /r/ cuối không tính (giọng Anh-Anh bỏ /r/)
            ph = ph[:-1] if ph and ph[-1] == "R" else ph
            n = 0
            while n < len(ph) and ph[-1 - n] not in VOWELS:
                n += 1
            return n

        def onset(ph):     # các phụ âm ở đầu từ
            out_ = []
            for p in ph:
                if p in VOWELS:
                    break
                out_.append(p)
            return out_
        # âm cuối: ít phụ âm cuối hơn (salt→so, molecules→molecule), mất cả âm tiết -es/-ed
        # (senses→cents), hoặc máy nghe đúng phần đầu của từ (contains→contain)
        lost_syll = len(e) >= 3 and e[-1] in ("S", "Z", "D", "T") and e[-2] in ("IH", "AH") \
            and ew.endswith(("es", "ed")) and \
            sum(p in VOWELS for p in g) < sum(p in VOWELS for p in e)
        if tail(e) > tail(g) or lost_syll:
            out.append("final")
        if any(a in ("TH", "DH") and b != a for a, b, tag in ops if tag in ("sub", "del")):
            out.append("th")
        if e[0] == "N" and g[0] == "L":
            out.append("nl")
        if any(a in _DIPH and b not in _DIPH for a, b, tag in ops if tag in ("sub", "del")):
            out.append("diph")
        if len(onset(e)) >= 2 and onset(e) != onset(g):
            out.append("cluster")
    else:
        if gw and ew.startswith(gw) and len(ew) > len(gw):
            out.append("final")
        if ew.startswith("th") and not gw.startswith("th"):
            out.append("th")
        if ew[:1] == "n" and gw[:1] == "l":
            out.append("nl")
        if len(ew) > 1 and ew[0] == "s" and ew[1] not in "aeiouy" and gw[:2] != ew[:2]:
            out.append("cluster")
    return out


def syllables(word):
    """Số âm tiết (số nguyên âm CMUdict); từ ngoài từ điển: ước theo cụm nguyên âm chữ."""
    ph = phonemes(word)
    if ph:
        return max(1, sum(p in VOWELS for p in ph))
    return max(1, len(re.findall(r"[aeiouy]+", _letters(word or ""))))


# ---------------------------------------------------------------- nối âm (D-46)
# Chỉ để DẠY: đo trên bản thu thật (mốc Whisper, năng lượng) không phân biệt được ngắt/nối → không chấm.
def link_points(words):
    """[từ gốc của đoạn] → [(chỉ số từ đầu, "cv" | "cc")]: chỗ nên đọc nối với từ sau.

    cv = phụ âm cuối + nguyên âm đầu (talk‿about, think‿of); cc = cùng một phụ âm (big‿game,
    this‿side). Không nối qua dấu câu (, . ? ! ; :). Từ ngoài CMUdict bỏ qua. Hàm thuần."""
    out = []
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        if re.search(r"[,.;:?!\"')\]]$", a or ""):
            continue
        pa, pb = phonemes(a), phonemes(b)
        if not pa or not pb:
            continue
        if pa[-1] not in VOWELS and pb[0] in VOWELS:
            out.append((i, "cv"))
        elif pa[-1] not in VOWELS and pa[-1] == pb[0]:
            out.append((i, "cc"))
    return out


# ---------------------------------------------------------------- từ nên nhấn (D-47)
_NEG = {"not", "no", "never", "nothing", "nobody", "none", "cannot"}


def stress_word(word):
    """Từ NÊN nhấn trong câu tiếng Anh (gợi ý để dạy, không đo): từ nội dung — danh từ, động
    từ chính, tính từ, trạng từ — và từ phủ định (not, never, can't…); từ chức năng đọc lướt."""
    raw = (word or "").lower().replace("’", "'").strip(".,;:?!\"()“”")
    if re.search(r"\d", raw):
        return True                     # con số là nội dung (90 page, 400 receptors)
    if raw in _NEG or raw.endswith("n't"):
        return True
    # I'm, it's, you're, we'll, let's… và gonna/wanna/gotta là dạng rút gọn của từ chức năng
    if "'" in raw or raw in ("gonna", "wanna", "gotta"):
        return False
    w = _letters(raw)
    return bool(w) and w not in FUNCTION_WORDS
