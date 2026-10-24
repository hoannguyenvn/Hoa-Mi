"""Đọc to transcript YouTube (D-39) — phần xử lý chữ, hàm thuần, chỉ dùng stdlib.

  - `clean_caption`: bỏ nhãn phụ đề ([Music], (applause), ♪, >>, "JOHN:").
  - `build_paragraphs`: gộp cue phụ đề thành ĐOẠN để đọc (~20–45 s), cắt ở khoảng lặng
    hoặc cuối câu; phụ đề tự động không có dấu câu nên khoảng lặng là mốc chính.
  - `en_tokens`: chuẩn hóa tiếng Anh để so phụ đề với lời người học: viết thường, bỏ dấu
    câu, bung rút gọn (don't → do not), gonna/wanna, bỏ từ đệm (um, uh), số → chữ.
    Mỗi token nhớ chỉ số từ gốc trong đoạn để tô màu đúng chữ người học nhìn thấy.

Chấm (căn từ, kind `doubt`) nằm ở `app.read_aloud_diff` cạnh `score_pronunciation`.
"""

import re

PARA_MIN_SEC = 20.0   # đoạn ngắn hơn thì gộp tiếp (trừ đoạn cuối)
PARA_MAX_SEC = 45.0   # dài hơn thì cắt — Whisper trên bản thu dài dễ bịa/trôi căn chỉnh
PARA_GAP_SEC = 1.5    # khoảng lặng giữa hai cue ≥ mức này là chỗ cắt tự nhiên

_NOISE_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|[♪♫]+|>>+|^\s*-\s+")
_SPEAKER_RE = re.compile(r"^\s*[A-Z][A-Z .'\-]{1,24}:\s+")
_END_RE = re.compile(r"[.?!][\"')\]]*$")


def clean_caption(text):
    """Bỏ nhãn không phải lời nói khỏi một dòng phụ đề."""
    s = _NOISE_RE.sub(" ", text or "")
    s = _SPEAKER_RE.sub("", s)
    return " ".join(s.split())


def build_paragraphs(cues, min_sec=PARA_MIN_SEC, max_sec=PARA_MAX_SEC, gap_sec=PARA_GAP_SEC):
    """[(start, end, text)] → [{"start", "end", "text", "words", "wpm"}].

    Cắt khi đoạn đang gom đã ≥ min_sec và (cue trước kết thúc câu hoặc có khoảng lặng
    ≥ gap_sec); cắt bắt buộc khi thêm cue sẽ vượt max_sec. Cue chỉ có [Music]… bị bỏ.
    """
    paras, cur = [], []

    def flush():
        if cur:
            text = " ".join(t for _s, _e, t in cur)
            st, en = cur[0][0], cur[-1][1]
            n = len(text.split())
            paras.append({"start": st, "end": en, "text": text, "words": n,
                          "wpm": round(60.0 * n / max(en - st, 0.1))})
            del cur[:]

    for st, en, tx in cues:
        tx = clean_caption(tx)
        if not tx:
            continue
        if cur:
            span = cur[-1][1] - cur[0][0]
            natural = _END_RE.search(cur[-1][2]) or st - cur[-1][1] >= gap_sec
            if (span >= min_sec and natural) or en - cur[0][0] > max_sec:
                flush()
        cur.append((float(st), float(en), tx))
    flush()
    return paras


# ------------------------------------------------------------ chuẩn hóa tiếng Anh
_FILLERS = {"um", "uh", "erm", "er", "ah", "hmm", "mm", "mhm", "uhm"}
_WHOLE = {  # thay cả từ (sau khi viết thường)
    "gonna": "going to", "wanna": "want to", "gotta": "got to", "gimme": "give me",
    "kinda": "kind of", "sorta": "sort of", "lemme": "let me", "dunno": "do not know",
    "'cause": "because", "cuz": "because", "ok": "okay", "y'all": "you all",
    "can't": "can not", "cannot": "can not", "won't": "will not", "shan't": "shall not",
    "ain't": "is not", "let's": "let us",
    "it's": "it is", "that's": "that is", "what's": "what is", "there's": "there is",
    "here's": "here is", "he's": "he is", "she's": "she is", "who's": "who is",
    "where's": "where is", "how's": "how is",
    "mr": "mister", "mrs": "missus", "dr": "doctor", "vs": "versus",
}
_SUFFIX = (("n't", " not"), ("'re", " are"), ("'ll", " will"), ("'ve", " have"),
           ("'d", " would"), ("'m", " am"))
_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(n):
    """Số nguyên ≥ 0 → chữ tiếng Anh: 42 → "forty two"; năm 1100–1999 → "nineteen ninety"."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])
    if 1100 <= n <= 1999 and n % 100:
        return number_words(n // 100) + " " + (
            "oh " + _ONES[n % 100] if n % 100 < 10 else number_words(n % 100))
    for size, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand"),
                       (100, "hundred")):
        if n >= size:
            head, rest = divmod(n, size)
            return number_words(head) + " " + name + ("" if not rest
                                                      else " " + number_words(rest))
    return str(n)


def _expand(word):
    if word in _WHOLE:
        return _WHOLE[word]
    for suf, rep in _SUFFIX:
        if word.endswith(suf) and len(word) > len(suf):
            return word[:-len(suf)] + rep
    return word


def en_tokens(text):
    """Chữ → [(token, chỉ số từ gốc, là_số)]. Từ gốc = phần tử của text.split()."""
    out = []
    for i, raw in enumerate((text or "").split()):
        w = raw.lower().replace("’", "'").replace("‘", "'")
        w = w.replace(",", "") if re.fullmatch(r"[\d,]+\.?", w.strip(".,!?;:\"")) else w
        for part in re.findall(r"[a-z0-9']+|%", w):
            part = part.strip("'") if part not in _WHOLE else part
            if not part:
                continue
            if part == "%":
                out.append(("percent", i, False))
                continue
            if part.isdigit():
                for t in number_words(int(part)).split():
                    out.append((t, i, True))
                continue
            for t in _expand(part).split():
                if t not in _FILLERS:
                    out.append((t, i, False))
    return out
