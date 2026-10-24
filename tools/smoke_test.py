#!/usr/bin/env python3
"""Test khói cho các hàm thuần của Oriole.

Không cần mic, không cần model Whisper, không mở cửa sổ Tk. Mục đích là bắt
regression nhanh trước khi sửa app.py. Chạy:

    C:\\Users\\ADMIN\\miniforge3\\python.exe tools\\smoke_test.py

Quy ước: mỗi test in PASS/FAIL; exit code 1 nếu có FAIL.
"""

from __future__ import annotations

import math
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402  (import sau khi thêm ROOT vào sys.path)
import numpy as np  # noqa: E402
import pron_en  # noqa: E402
import prosody  # noqa: E402

CASES: list[tuple[str, callable]] = []


def case(fn):
    CASES.append((fn.__name__, fn))
    return fn


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol


# ---------------------------------------------------------------- bài học
@case
def lessons_loaded():
    assert len(app.SET_IDS) == 18, f"SET_IDS={len(app.SET_IDS)}"
    assert len(app.SET_IDS) == len(set(app.SET_IDS)), "SET_IDS trùng"
    assert "en_th" in app.PRACTICE_SETS
    for sid in app.SET_IDS:
        s = app.PRACTICE_SETS[sid]
        if sid != "custom":
            assert s.get("target"), f"{sid} thiếu target"
            assert s.get("lang") in ("vi", "en", "auto"), f"{sid} lang lạ"


@case
def lessons_have_samples():
    for sid in app.SET_IDS:
        if sid in ("custom",) or not sid.startswith("en_"):
            continue
        for _label, rel in app.PRACTICE_SETS[sid]["samples"]:
            assert (ROOT / "mau" / rel).exists(), f"thiếu mau/{rel}"


# ---------------------------------------------------------------- L1 scoring
@case
def exact_read_is_100():
    r = app.score_pronunciation("Think about this thing.",
                                "Think about this thing.", "en")
    assert r["score"] == 100.0, r
    assert r["warns"] == 0 and r["tones"] == 0, r
    assert all(it[1] == "ok" for it in r["items"]), r["items"]


@case
def th_confusion_flagged():
    r = app.score_pronunciation("Think about this thing.",
                                "Tink about this thing.", "en")
    assert r["warns"] >= 1, r
    assert any("âm th" in (it[3] or "").lower() for it in r["items"]), r["items"]
    assert r["score"] < 100, r


@case
def nl_confusion_flagged():
    r = app.score_pronunciation("na la", "la la", "vi")
    assert r["warns"] >= 1, r
    assert any(it[1] == "warn" for it in r["items"]), r["items"]
    assert approx(r["score"], 50.0), r


@case
def vietnamese_tone_flagged():
    r = app.score_pronunciation("má", "ma", "vi")
    assert r["tones"] == 1, r
    assert r["items"][0][1] == "tone", r["items"]
    assert r["score"] == 0.0, r


@case
def northern_accent_is_correct():
    # D-38: r/d/gi, s/x, tr/ch giọng Bắc tính là đúng ở bài Việt; thanh vẫn phải đúng
    r = app.score_pronunciation("rừng xinh trong giữ gì", "dừng sinh chong dữ dì", "vi")
    assert r["correct"] == 5, r["items"]
    assert r["items"][0] == ("rừng", "ok", "dừng", None), r["items"]
    r = app.score_pronunciation("rủ", "dù", "vi")
    assert r["items"][0][1] == "tone", r["items"]
    r = app.score_pronunciation("nai", "lai", "vi")      # n/l KHÔNG phải giọng Bắc
    assert r["items"][0][1] == "warn", r["items"]
    r = app.score_pronunciation("red", "dead", "en")     # chỉ áp cho tiếng Việt
    assert r["correct"] == 0, r["items"]
    assert app.vi_north_key("gìn") == app.vi_north_key("dìn") == "zìn"


@case
def yt_caption_clean_and_paragraphs():
    import yt_read
    assert yt_read.clean_caption(">> JOHN: [Music] hello (laughs) world ♪") == "hello world"
    cues = [(0, 3, "[Music]"), (3, 6, "so today we are"), (6, 9, "going to talk."),
            (9, 25, "about cats"), (27, 30, "and dogs"), (30, 50, "and birds"),
            (50, 52, "end.")]
    ps = yt_read.build_paragraphs(cues)
    assert [(p["start"], p["end"]) for p in ps] == [(3.0, 25.0), (27.0, 52.0)], ps
    assert ps[0]["text"].startswith("so today"), ps    # cue chỉ có [Music] bị bỏ
    # không cue nào làm đoạn vượt PARA_MAX_SEC
    long = [(i * 5.0, i * 5.0 + 5, "word word") for i in range(30)]
    assert all(p["end"] - p["start"] <= yt_read.PARA_MAX_SEC
               for p in yt_read.build_paragraphs(long))


@case
def en_tokens_normalise():
    import yt_read
    toks = [t for t, _i, _n in yt_read.en_tokens("I'm gonna, um, say it's 1990! Don't")]
    assert toks == "i am going to say it is nineteen ninety do not".split(), toks
    assert yt_read.number_words(2024) == "two thousand twenty four"
    assert yt_read.number_words(1905) == "nineteen oh five"
    assert yt_read.en_tokens("1,000 50%")[-1][0] == "percent"


@case
def read_aloud_diff_doubts():
    sub = "So today I'm gonna show you 3 tricks to cook rice."
    # người học sai "rice"; video thật nói "trick" mà người học đọc "tricks" như phụ đề → vẫn đúng
    r = app.read_aloud_diff(sub, "so today I am going to show you three tricks to cook lice",
                            "so today i am going to show you three trick to cook rice")
    assert (r["correct"], r["total"], r["doubts"]) == (12, 13, 0), r
    assert r["src_idx"][-1] == 10, r["src_idx"]    # "rice." là từ thứ 10 của phụ đề
    # người học và video đều không có "really" → phụ đề có thể sai, không tính
    r = app.read_aloud_diff("It is really good", "it is good", "it is good")
    kinds = [it[1] for it in r["items"] if it[0]]
    assert kinds == ["ok", "ok", "doubt", "ok"], r["items"]
    assert (r["correct"], r["total"]) == (3, 3), r
    # chữ số đọc khác cách viết → doubt "số"
    r = app.read_aloud_diff("Room 12", "room one two")
    assert r["doubts"] >= 1 and r["total"] == 1, r


@case
def ytread_view_marks_and_rows():
    para = "So today I'm gonna show you 3 tricks, really."
    res = app.read_aloud_diff(para, "so today I am going to show you three trick",
                              "so today I am going to show you three tricks")
    res["words_t"] = [{"w": w, "s": i, "e": i + 0.5, "p": 0.9 if w != "today" else 0.1}
                      for i, w in enumerate("so today I am going to show you three trick".split())]
    v = app.ytread_view(res)
    words = para.split()
    # "tricks," (từ 7) nuốt âm cuối → warn; "really." (từ 8) người học và video đều không đọc
    # → phụ đề có thể sai
    assert v["marks"][7] == "warn" and v["marks"][8] == "doubt", v["marks"]
    assert v["marks"][1] == "unsure", v["marks"]           # "today" p 0,1 → máy chưa chắc
    assert words[7].startswith("tricks") and len(v["fixes"]) == 1, v["fixes"]
    assert v["fixes"][0]["text"].startswith("“tricks”"), v["fixes"]
    assert "phụ đề có thể sai" not in v["doubts"][0]["text"], v["doubts"]   # tiêu đề đã nói
    assert v["headline"] == "Đúng %d/%d từ" % (res["correct"], res["total"])
    assert app.token_spans(res["words_t"], res["target"])[1][:2] == (1, 1.5)
    u = app.ytread_view(res, "garbage")
    assert u["state"] == "unsure" and not u["marks"] and u["ring"]["text"] == "?"
    c = app.prac_controls("loading", True)
    assert not c["rec_enabled"] and not c["replay_enabled"] and c["show_pbar"]


@case
def fluency_pauses_and_sentences():
    import yt_read
    assert yt_read.sentence_ranges("One two. Three four five? Six") == [(0, 1), (2, 4), (5, 5)]
    long = " ".join("w%d" % i for i in range(30))
    assert yt_read.sentence_ranges(long, breaks={14}) == [(0, 14), (15, 29)]
    text = ("When I was in college I had to write a ninety page thesis. "
            "I planned to start early, but I watched videos instead.")
    plain = text.lower().replace(".", "").replace(",", "")
    res = app.read_aloud_diff(text, plain, plain)
    toks = res["target"].split()

    def times(gaps):
        t, out = 0.0, []
        for i, w in enumerate(toks):
            out.append({"w": w, "s": round(t, 2), "e": round(t + 0.3, 2), "p": 0.9})
            t += 0.3 + gaps.get(i, 0.02)
        return out
    # token 8 = "write", 10 = "ninety": người học ngừng giữa cụm (1,2 s = ngập ngừng);
    # token 13 = "thesis." (cuối câu) — ngừng ở đó là tự nhiên, không bị báo
    mine = app.token_spans(times({8: 0.6, 10: 1.2, 13: 0.5}), res["target"])
    ref = app.token_spans(times({4: 0.5, 13: 0.6}), res["target"])   # người nói ngừng sau "college"
    v = app.fluency_view(text, res, mine, ref)
    assert [e["text"] for e in v["extra"]] == ["write / a", "ninety / page"], v["extra"]
    assert [m["text"] for m in v["missed"]] == ["college"], v["missed"]
    assert v["hesit"] == 1 and set(v["pause_after"]) == {8, 10}, v
    assert len(v["sentences"]) == 2 and v["sentences"][0]["extra"] == ["write / a", "ninety / page"]
    assert v["sentences"][0]["usr"] and v["sentences"][0]["ref"]
    assert v["wpm_usr"] < v["wpm_ref"] and any("Tốc độ" in ln for ln in v["lines"])
    # không có audio gốc (transcript do Whisper tạo) → vẫn có tốc độ của bạn, không so
    v2 = app.fluency_view(text, res, mine, None)
    assert v2["wpm_ref"] is None and v2["missed"] == []


@case
def ytread_learner_uses_medium_when_on_disk():
    # D-41: bản đọc Từ YouTube chấm bằng medium nếu đã có trên máy (không tự tải — I9)
    on, off = (lambda m: True), (lambda m: False)
    assert app.ytread_model("small", on) == ("medium", True)
    assert app.ytread_model("base", off) == ("base", False)
    assert app.ytread_model("medium", on) == ("medium", False)
    s = app.YtReadSession(None)
    assert hasattr(s.lock, "acquire")       # nghe trước ở nền + lúc chấm dùng chung khóa
    s.close()


@case
def english_error_patterns_from_real_reading():
    # D-42: ví dụ lấy từ 4 đoạn đọc thật của người dùng (2026-10-24)
    ep = app.pron_en.error_patterns
    assert ep("molecules", "molecule") == ["final"]
    assert ep("senses", "scents") == ["final"]            # mất âm tiết -es
    assert ep("nose", "lowes") == ["nl"] and "nl" in ep("nose", "lobe")
    assert ep("the", "some") == ["th"]
    assert ep("bacon", "back") == ["diph"]
    assert ep("smell", "mail") == ["cluster"] and ep("sniff", "sit") == ["cluster"]
    assert ep("is", None) == ["short"]
    assert ep("much", "two") == [] and ep("trash", "just") == []   # nghe nhầm hẳn → không xếp
    assert ep("your", "you") == [] and ep("their", "the") == []    # bỏ /r/ cuối không phải lỗi
    fixes = [{"ti": 0, "word": "molecules", "heard": "molecule"},
             {"ti": 3, "word": "emotions", "heard": "motion"},
             {"ti": 5, "word": "nose", "heard": "lowes"},
             {"ti": 7, "word": "much", "heard": "two"},
             {"ti": 9, "word": "is", "heard": None, "unread": True}]
    pv = app.error_pattern_view(fixes)
    assert [g["code"] for g in pv["groups"]] == ["final", "nl"], pv
    assert pv["groups"][0]["n"] == 2 and pv["grouped"] == 3 and pv["total"] == 4
    assert "molecules → “molecule”" in app.pattern_example_text(pv["groups"][0]["examples"])
    # dừng giữa đoạn: ≥3 từ cuối không nghe thấy → "chưa đọc tới", không thành "từ ngắn bị nuốt"
    res = app.read_aloud_diff("I like it and there are many more of them here",
                              "I like it and there", None)
    v = app.ytread_view(res)
    assert sum(1 for f in v["fixes"] if f.get("unread")) == 6, v["fixes"]
    assert "dừng trước 6 từ cuối" in v["summary"], v["summary"]
    assert not app.error_pattern_view(v["fixes"])["groups"]


@case
def session_report_and_html():
    # D-43: báo cáo cuối gom các đoạn đã đọc (dừng sớm được), lưu HTML có nút nghe lại
    def para(text, heard, step=0.4):
        res = app.read_aloud_diff(text, heard, None)
        res["words_t"] = [{"w": w, "s": i * step, "e": i * step + 0.3, "p": 0.9}
                          for i, w in enumerate(heard.split())]
        orig = [{"w": w, "s": i * 0.25, "e": i * 0.25 + 0.2, "p": 0.9}
                for i, w in enumerate(text.split())]
        return {"text": text, "res": res, "orig_words": orig}
    d1 = dict(para("The molecules reach the nose and the brain loves it.",
                   "the molecule reach the nose and the brain loves it"), idx=0)
    d2 = dict(para("Odor receptors send molecules to the brain right now and here today.",
                   "odor receptors send molecule to the brain"), idx=2)
    d3 = dict(para("Bad audio.", "garbage words"), idx=3, gate="garbage")
    rep = app.session_report({"title": "Smell <TED>", "url": "u", "n_paras": 6,
                              "date": "24/10/2026"}, [d1, d2, d3])
    assert rep["n_read"] == 3 and rep["n_scored"] == 2 and rep["n_paras"] == 6
    assert rep["paras"][2]["state"] == "unsure"
    assert rep["patterns"][0]["code"] == "final" and rep["patterns"][0]["n"] == 2, rep["patterns"]
    assert rep["unread"] == 5 and rep["paras"][1]["unread"] == 5        # "right now and here today."
    assert rep["focus"] and rep["focus"][0]["title"].startswith("Âm cuối")
    assert rep["wpm_usr"] and rep["wpm_ref"] and rep["wpm_usr"] < rep["wpm_ref"]
    assert any(w["word"] == "molecules" and w["n"] == 2 for w in rep["words"])
    html = app.report_html(rep, {0: ("doan01.wav", "doan01_goc.wav")})
    assert "<audio controls src='doan01.wav'>" in html and "doan01_goc.wav" in html
    assert "Smell &lt;TED&gt;" in html and "<TED>" not in html           # thoát ký tự HTML
    assert "3 điều nên tập trung" in html and "đã đọc 3/6 đoạn" in html


@case
def intonation_range_not_direction():
    # D-44: so DẢI cao độ từng câu (bền), không kết luận lên/xuống cuối câu
    import math
    import prosody

    def track(amp, t0=0.0, dur=4.0):
        ts = [t0 + i * 0.01 for i in range(int(dur * 100))]
        return {"t": ts, "st": [None if i % 9 == 0 else round(amp * math.sin(i / 30.0), 2)
                                for i in range(len(ts))]}
    flat, lively = track(2.5), track(7.0, t0=10.0)
    s1 = prosody.segment_pitch(flat, 0.5, 3.5)
    assert s1 and 3 < s1["range"] < 6 and len(s1["curve"]) == prosody.CURVE_POINTS
    assert prosody.segment_pitch(flat, 0.5, 0.7) is None            # < 30 khung có giọng
    sents = [{"usr": (0.5, 3.5), "ref": (10.5, 13.5), "cov_usr": 1.0},
             {"usr": (0.2, 1.8), "ref": (10.2, 11.8), "cov_usr": 0.3}]   # câu chưa đọc tới
    v = app.intonation_view(sents, flat, lively)
    assert v["flat"] and v["range_usr"] < app.FLAT_RATIO * v["range_ref"], v
    assert v["sentences"][1]["range_usr"] is None and v["sentences"][1]["range_ref"]
    assert v["lines"] and "giọng bạn đều" in v["lines"][0]
    assert not any("cuối câu" in ln and ("lên" in ln or "xuống" in ln) for ln in v["lines"][:1])
    v2 = app.intonation_view(sents, track(7.0), lively)      # người học dao động như người nói
    assert not v2["flat"] and len(v2["lines"]) == 1, v2


@case
def rhythm_function_words_not_stress():
    # D-45: nhịp = từ chức năng dài so với người nói; không so từ được nhấn (R-16)
    text = ("The cat sat on the mat and the dog ran to the park with a ball of string "
            "for the kids in the yard.")
    plain = text.lower().replace(".", "")
    res = app.read_aloud_diff(text, plain, plain)
    toks = res["target"].split()

    def times(func_d, cont_d):
        t, out = 0.0, []
        for w in toks:
            d = func_d if w in app.pron_en.FUNCTION_WORDS else cont_d * app.pron_en.syllables(w)
            out.append({"w": w, "s": round(t, 3), "e": round(t + d, 3), "p": 0.9})
            t += d + 0.03
        return out
    mine = app.token_spans(times(0.40, 0.26), res["target"])     # từ ngắn 400 ms
    ref = app.token_spans(times(0.18, 0.25), res["target"])      # người nói 180 ms
    smp = app.rhythm_samples(res, mine, ref)
    v = app.rhythm_view(smp)
    assert v["even"] and v["lines"] and "dài gấp" in v["lines"][0], v
    assert v["ex"] and all(w in app.pron_en.FUNCTION_WORDS for w, *_ in v["ex"])
    same = app.rhythm_view(app.rhythm_samples(res, ref, ref))
    assert not same["even"] and len(same["lines"]) == 1
    assert app.rhythm_view({"fu": [0.3], "fr": [0.2], "cu": [0.2], "cr": [0.2]})["lines"] == []
    assert app.pron_en.syllables("olfactory") == 4 and app.pron_en.syllables("the") == 1


@case
def linking_points_teaching_only():
    # D-46: chỉ chỉ ra chỗ nên nối + mốc để nghe; không chấm nối/ngắt (R-17)
    lp = app.pron_en.link_points
    w = "let's talk about how smell works, from big games we think of".split()
    pairs = [w[i] + "‿" + w[i + 1] for i, _k in lp(w)]
    assert "talk‿about" in pairs and "think‿of" in pairs, pairs
    assert "works,‿from" not in pairs                     # không nối qua dấu phẩy
    assert dict((w[i], k) for i, k in lp(w))["big"] == "cc"
    text = "We talk about it every day."
    res = app.read_aloud_diff(text, text.lower().rstrip("."), None)
    sp = app.token_spans([{"w": x, "s": i * 0.3, "e": i * 0.3 + 0.25, "p": 0.9}
                          for i, x in enumerate(res["target"].split())], res["target"])
    v = app.linking_view(text, res, sp, sp)
    assert [x["text"] for x in v["links"]] == ["“talk about”", "“about it”", "“it every”"], v
    assert v["links"][0]["usr"] == (0.3, 0.85) and v["lines"]
    assert not any("sai" in ln or "đúng" in ln for ln in v["lines"])   # không phán


@case
def tone_strip_keeps_letters():
    # strip_tone_vi trả chuỗi NFD (giữ dấu chữ như ă/â), nên chuẩn hóa NFC để so.
    import unicodedata

    def nfc(s):
        return unicodedata.normalize("NFC", s)

    assert nfc(app.strip_tone_vi("năm")) == "năm", repr(app.strip_tone_vi("năm"))
    assert nfc(app.strip_tone_vi("má")) == "ma"
    assert nfc(app.strip_tone_vi("mất")) == "mât"


@case
def extra_word_not_penalised():
    # Hành vi có chủ đích: điểm = correct/total, từ thừa chỉ là cảnh báo.
    r = app.score_pronunciation("na la", "na la la", "vi")
    assert r["score"] == 100.0, r
    assert any(it[1] == "extra" for it in r["items"]), r["items"]


@case
def norm_words_strips_punctuation():
    assert app.norm_words("Xin chào, thế giới!") == ["xin", "chào", "thế", "giới"]
    assert app.norm_words("") == []


@case
def flag_pair_direct():
    assert app.flag_pair("think", "tink", "en")[0] == "th"
    assert app.flag_pair("she", "see", "en")[0] == "sh"
    assert app.flag_pair("cat", "ca", "en")[0] == "final"
    assert app.flag_pair("năm", "lăm", "vi")[0] == "nl"
    assert app.flag_pair("na", "na", "vi") is None


# ---------------------------------------------------------------- cue / SRT
@case
def srt_timestamps():
    srt = app.cues_to_srt([(0.0, 1.234, "Xin chào"),
                           (61.5, 63.0, "Dòng hai")])
    assert "1\n00:00:00,000 --> 00:00:01,234\nXin chào" in srt, srt
    assert "2\n00:01:01,500 --> 00:01:03,000\nDòng hai" in srt, srt


@case
def txt_with_time():
    txt = app.cues_to_txt([(0, 1, "a"), (61, 62, "b")])
    assert txt == "[00:00:00] a\n[00:01:01] b\n", repr(txt)


@case
def fix_cues_removes_empty_and_fixes_duration():
    out = app._fix_cues([(0, 1, "  a  "), (2, 2, ""), (3, 2, "b")])
    assert out[0] == (0.0, 1.0, "a"), out
    assert len(out) == 2, out
    assert out[1][1] > out[1][0], out


@case
def split_long_cues_respects_words():
    text = " ".join(["hello"] * 40)
    out = app.split_long_cues([(0, 10, text)], max_chars=40)
    assert len(out) > 1, out
    assert all(len(c[2]) <= 40 for c in out), out
    assert all(" ".join(c[2].split()) == c[2] for c in out), out
    assert out[0][0] == 0.0 and out[-1][1] <= 10.0, out


# ---------------------------------------------------------------- âm thanh
@case
def resample_length():
    x = np.zeros(44100, dtype=np.float32)
    y = app.resample_to_16k(x, 44100, 16000)
    assert len(y) == 16000, len(y)


@case
def enhance_silence_is_quiet():
    x = np.zeros(16000, dtype=np.int16)
    out, info = app.enhance_audio(x, 16000)
    assert out.dtype == np.int16
    assert info["quiet"] is True, info
    assert info["peak0"] == 0.0, info


@case
def enhance_normalises_gain():
    t = np.arange(16000, dtype=np.float32) / 16000.0
    x = (0.2 * np.sin(2 * math.pi * 150 * t) * 32767).astype(np.int16)
    out, info = app.enhance_audio(x, 16000)
    assert info["quiet"] is False, info
    assert info["peak1"] > 0.4, info
    assert np.max(np.abs(out)) <= 32767


@case
def enhance_lifts_weak_mic():
    # Micro array laptop cho đỉnh ~1%: vẫn phải kéo lên mức Whisper nghe được
    # (gain tối đa +24dB), nếu không app sẽ không chấm được gì.
    t = np.arange(16000, dtype=np.float32) / 16000.0
    x = (0.01 * np.sin(2 * math.pi * 150 * t) * 32767).astype(np.int16)
    out, info = app.enhance_audio(x, 16000)
    assert info["peak0"] < app.MIC_GOOD_PEAK, info
    assert info["peak1"] > 0.1, info
    assert np.max(np.abs(out)) <= 32767
    assert app.MIC_MIN_PEAK < app.MIC_GOOD_PEAK, (app.MIC_MIN_PEAK, app.MIC_GOOD_PEAK)


@case
def resample_blocks_aliasing():
    # Mic 48/44,1 kHz: tiếng 10 kHz không được gập xuống 6 kHz (đè dải s/sh/th);
    # dải giọng tới 7,5 kHz phải giữ nguyên. Nội suy tuyến tính cũ để lọt 87 %.
    for sr in (48000, 44100):
        t = np.arange(sr * 2) / sr

        def rms_after(f):
            y = app.resample_to_16k(0.5 * np.sin(2 * math.pi * f * t), sr)[2000:-2000]
            return float(np.sqrt(np.mean(y ** 2)))
        assert rms_after(10000) < 0.002, (sr, rms_after(10000))
        assert rms_after(3000) > 0.33, (sr, rms_after(3000))
        assert rms_after(7500) > 0.30, (sr, rms_after(7500))


@case
def highpass_matches_one_pole_loop():
    # Bộ lọc vector hóa phải đúng là high-pass 1 cực cũ (D-11), chỉ nhanh hơn.
    rate = 16000
    x = np.random.default_rng(0).standard_normal(6000).astype(np.float32) * 0.1
    rc = 1.0 / (2 * math.pi * 75.0)
    a = rc / (rc + 1.0 / rate)
    y = np.empty_like(x)
    y[0] = x[0]
    for n in range(1, len(x)):
        y[n] = (x[n] - x[n - 1]) + a * y[n - 1]
    z = app.fft_convolve(x, app.highpass_1pole_kernel(rate))[:len(x)]
    assert float(np.max(np.abs(y - z))) < 1e-5


@case
def enhance_gain_ignores_click():
    # Một tiếng gõ bàn không được quyết định gain: giọng nhỏ vẫn phải được kéo lên.
    sp = (np.random.default_rng(1).standard_normal(16000 * 3) * 0.005).astype(np.float32)
    outs = []
    for click in (False, True):
        s = sp.copy()
        if click:
            s[20000] = 0.5
        out, _info = app.enhance_audio((s * 32767).astype(np.int16), 16000)
        o = out.astype(np.float32) / 32767
        outs.append(float(np.sqrt(np.mean(o ** 2))))
    assert outs[1] > 0.8 * outs[0], outs


@case
def guess_lang_from_target_text():
    assert app.guess_lang("Lan năm nay lên lớp.") == "vi"
    assert app.guess_lang("đi") == "vi"
    assert app.guess_lang("Think about this: three thanks.") == "en"
    assert app.guess_lang("123 !!") is None
    assert app.guess_lang("Grüß dich") is None


@case
def practice_asr_options():
    # I2: không initial_prompt; temperature 0; VAD chỉ cho file dài/không phải WAV.
    import types
    seen = []

    class FakeModel:
        def transcribe(self, path, **k):
            seen.append(k)
            return iter(()), types.SimpleNamespace(language=k.get("language"))

    short = _tmp_wav()
    with app.wave.open(short, "wb") as w:   # WAV thật 1 s
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * 16000)
    try:
        app.transcribe_practice(FakeModel(), short, "en")
        app.transcribe_practice(FakeModel(), "khong_co.mp3", "auto")
    finally:
        app.remove_temp(short)
    k0, k1 = seen
    assert "initial_prompt" not in k0 and k0["temperature"] == 0.0, k0
    assert k0["vad_filter"] is False and k0["language"] == "en", k0
    assert k1["vad_filter"] is True and k1["language"] is None, k1


@case
def whisper_model_is_cached():
    import types
    made = []

    class FakeWM:
        def __init__(self, size, **k):
            made.append(size)

    real = sys.modules.get("faster_whisper")
    sys.modules["faster_whisper"] = types.SimpleNamespace(WhisperModel=FakeWM)
    saved = dict(app._MODEL_CACHE)
    app._MODEL_CACHE.clear()
    try:
        a = app.load_model("base")
        assert app.load_model("base") is a
        app.load_model("small")
        app.load_model("base")                       # base thành "vừa dùng"
        app.load_model("tiny")                       # vượt 2 → bỏ cỡ dùng lâu nhất (small)
        assert made == ["base", "small", "tiny"], made
        assert list(app._MODEL_CACHE) == ["base", "tiny"], list(app._MODEL_CACHE)
    finally:
        app._MODEL_CACHE.clear()
        app._MODEL_CACHE.update(saved)
        if real is None:
            sys.modules.pop("faster_whisper", None)
        else:
            sys.modules["faster_whisper"] = real


@case
def vietnamese_practice_uses_small_when_on_disk():
    yes, no = (lambda _s: True), (lambda _s: False)
    assert app.practice_model("base", "vi", yes) == ("small", True)
    assert app.practice_model("base", "vi", no) == ("base", False)   # không tự tải (I9)
    assert app.practice_model("medium", "vi", yes) == ("medium", False)
    assert app.practice_model("base", "en", yes) == ("base", False)
    assert app.practice_model("base", "auto", yes) == ("base", False)


@case
def unsure_word_loses_tick_not_points():
    # D-37: từ đúng nhưng Whisper nghe p rất thấp → "máy chưa chắc"; điểm giữ nguyên (I4)
    res = app.score_pronunciation("Think about this", "think about this", "en")
    res.update(target="Think about this", det_lang="en", words_t=[
        {"w": "think", "p": 0.9}, {"w": "about", "p": 0.1}, {"w": "this.", "p": 0.95}])
    v = app.build_result_view(res, {"lang": "en"})
    assert v["unsure_words"] == {1: 0.1}, v["unsure_words"]
    assert v["correct"] == 3 and not v["perfect"], v
    kinds = [w["kind"] for w in app.stage_words("Think about this", v)]
    assert kinds == ["ok", "unsure", "ok"], kinds
    res["words_t"][1]["p"] = 0.6
    v = app.build_result_view(res, {"lang": "en"})
    assert v["unsure_words"] == {} and v["perfect"], v["unsure_words"]


@case
def snr_estimate_and_quality_note():
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(16000 * 3).astype(np.float32) * 0.002
    t = np.arange(16000, dtype=np.float32) / 16000.0
    loud, faint = noise.copy(), noise.copy()
    loud[16000:32000] += 0.2 * np.sin(2 * math.pi * 200 * t)
    faint[16000:32000] += 0.006 * np.sin(2 * math.pi * 200 * t)
    s_loud = app.estimate_snr_db(loud, 16000)
    s_faint = app.estimate_snr_db(faint, 16000)
    assert s_loud > 30 and s_faint < app.SNR_LOW_DB, (s_loud, s_faint)
    assert app.estimate_snr_db(np.zeros(100), 16000) is None
    base = {"peak0": 0.2, "trimmed": 0, "clipped": False}
    assert "ồn" not in app.quality_note(dict(base, snr_db=s_loud))
    assert "phòng hơi ồn" in app.quality_note(dict(base, snr_db=s_faint))
    assert "mất 2 đoạn" in app.quality_note(dict(base, snr_db=None, dropped=2))
    _out, info = app.enhance_audio((loud * 32767).astype(np.int16), 16000)
    assert info["snr_db"] is not None and info["snr_db"] > 30, info


@case
def recorder_noise_floor_and_practice_silence():
    # đọc ngay khi bấm: nền đo theo phân vị thấp, không theo trung vị; bài luyện chờ 1,8 s
    import inspect
    src = inspect.getsource(app.Recorder.start)
    assert "np.percentile(calib, 20)" in src and "np.median(calib)" not in src
    assert "input_overflow" in src
    assert app.PRAC_SILENCE_SEC >= 1.8
    assert "PRAC_SILENCE_SEC" in inspect.getsource(app.App._prac_start)


# ---------------------------------------------------------------- âm vị / F0
@case
def ipa_think_has_theta():
    ipa = pron_en.word_ipa("think")
    assert "θ" in ipa, ipa


@case
def phoneme_issue_think_tink():
    rep = pron_en.analyze_pairs([(0, "think", "tink")])
    assert rep["issues"], rep
    assert any(it["exp"] == "TH" for it in rep["issues"]), rep["issues"]
    assert any("θ" in it["label"] for it in rep["issues"]), rep["issues"]


@case
def f0_track_sine():
    sr = 16000
    t = np.arange(sr, dtype=np.float32) / sr
    x = (0.5 * np.sin(2 * math.pi * 150.0 * t)).astype(np.float32)
    _times, f0 = prosody.f0_track(x, sr)
    vals = f0[~np.isnan(f0)]
    assert len(vals) > 20, f"voiced={len(vals)}"
    med = float(np.median(vals))
    assert 135.0 <= med <= 165.0, med


# ---------------------------------------------------------------- cấu hình
@case
def config_is_whitelisted():
    cfg = app.load_config()
    assert set(cfg) <= set(app.DEFAULT_CFG), set(cfg) - set(app.DEFAULT_CFG)
    for key, val in app.DEFAULT_CFG.items():
        assert key in cfg
        assert isinstance(cfg[key], type(val)), f"{key}: {type(cfg[key])} != {type(val)}"


@case
def usable_mics_drops_wdmks():
    # WDM-KS luôn lỗi blocking read -> không được hiện trong ô chọn micro.
    fake = [(1, "Mic A", "Windows WASAPI", 48000),
            (2, "Mic B", "Windows WDM-KS", 48000)]
    out = app.list_usable_mics(fake)
    assert [m[0] for m in out] == [1], out
    # Máy chỉ có WDM-KS: giữ lại để ô chọn không trắng.
    only = [(2, "Mic B", "Windows WDM-KS", 48000)]
    assert len(app.list_usable_mics(only)) == 1, only
    assert app.list_usable_mics([]) == []


@case
def pick_default_prefers_real_mic():
    mics = [(0, "Microsoft Sound Mapper - Input", "MME", 44100),
            (4, "Primary Sound Capture Driver", "Windows DirectSound", 44100),
            (9, "Microphone Array (Intel)", "Windows WASAPI", 48000),
            (5, "Microphone Array (Intel)", "Windows DirectSound", 44100),
            (11, "Microphone (Realtek)", "Windows WDM-KS", 44100)]
    assert app.pick_default_mic(mics) == 5, app.pick_default_mic(mics)
    assert app.pick_default_mic([]) is None


@case
def headset_without_mic_is_detected():
    # AirPods nối bluetooth chỉ có chiều nghe -> app phải phát hiện & nhắc bật
    # profile Hands-Free, chứ không im lặng để người dùng tưởng app không hỗ trợ.
    base = [
        {"name": "Speakers (Realtek(R) Audio)", "max_input_channels": 0,
         "max_output_channels": 2},
        {"name": "Headphones (AirPods Pro - Find My)", "max_input_channels": 0,
         "max_output_channels": 2},
        {"name": "Microphone Array (Intel)", "max_input_channels": 4,
         "max_output_channels": 0},
    ]
    assert app.headset_mic_missing(base), "phải thấy AirPods thiếu micro"
    with_mic = base + [{"name": "Headset (AirPods Pro Hands-Free AG Audio)",
                        "max_input_channels": 1, "max_output_channels": 2}]
    assert app.headset_mic_missing(with_mic) is None
    # Loa máy thường và tai nghe có dây không bị báo nhầm.
    plain = [{"name": "Speakers (Realtek(R) Audio)", "max_input_channels": 0,
              "max_output_channels": 2},
             {"name": "Microphone (USB Audio Device)", "max_input_channels": 1,
              "max_output_channels": 0}]
    assert app.headset_mic_missing(plain) is None


@case
def recorder_uses_callback_not_blocking_read():
    # DirectSound trên máy này trả 100 % số 0 với InputStream.read (D-23) — phải giữ
    # callback + queue; quay lại blocking read là lỗi "mic im lặng" tái phát.
    import inspect
    src = inspect.getsource(app.Recorder.start)
    assert "callback=" in src, "Recorder phải mở InputStream(callback=...)"
    assert "stream.read(" not in src, "không được dùng stream.read (D-23)"
    assert "get_nowait" in inspect.getsource(app.Recorder.stop), \
        "stop() phải drain queue trước khi trả frames"


@case
def yt_worker_always_reports_back():
    # Thiếu lớp bọc ở _w_yt thì Hủy/lỗi giữa chừng làm thread chết im lặng
    # → UI kẹt trạng thái bận mãi (D-24). Không cần mạng.
    import queue as _q
    import types

    def run(exc, cancel=False):
        fake = types.SimpleNamespace(_queue=_q.Queue(), cancel_flag=cancel)

        def body(*a):
            raise exc
        fake._w_yt_body = body
        app.App._w_yt(fake, "u", "video", "best", ".", False, "auto", False, "base", None)
        return fake._queue.get_nowait()

    assert run(app._YtCancelled()) == ("error", "__cancelled__")
    assert run(RuntimeError("boom"), cancel=True) == ("error", "__cancelled__")
    kind, msg = run(RuntimeError("boom"))
    assert kind == "error" and "boom" in msg


@case
def auto_captions_rolling_overlap_removed():
    # Phụ đề tự động YouTube: mỗi cue lặp đuôi cue trước → transcript gấp đôi (Y2 đo 300+ wpm)
    cues = [(0, 4, "so in college I was a government major which"),
            (4, 6, "college I was a government major which means I had to write"),
            (6, 8, "means I had to write a lot of papers"),
            (8, 9, "a lot of papers")]
    out = app._dedupe_cues(cues)
    text = " ".join(t for _s, _e, t in out)
    assert text == ("so in college I was a government major which means I had to write "
                    "a lot of papers"), out
    # lặp 1–2 từ giữa hai câu thật thì giữ nguyên
    keep = app._dedupe_cues([(0, 1, "I said no"), (1, 2, "no way")])
    assert [t for _s, _e, t in keep] == ["I said no", "no way"], keep


@case
def ytread_subtitle_pick_and_session_cleanup():
    import types
    pick = app.pick_en_subtitle
    info = {"language": "en", "subtitles": {"en-GB": [{}], "vi": [{}]},
            "automatic_captions": {"en-orig": [{}], "en": [{}], "fr": [{}]}}
    assert pick(info) == ("en-GB", "manual")
    assert pick(info, "auto") == ("en", "auto")
    assert pick({"language": "fr", "automatic_captions": {"en": [{}]}}) == (None, None)
    # lỗi giữa chừng (ở đây: extract_info) → thư mục tạm của phiên bị xóa (I10)
    made = []
    real_mkdtemp = app.tempfile.mkdtemp

    def mkdtemp(**kw):
        made.append(real_mkdtemp(**kw))
        return made[-1]

    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            raise RuntimeError("offline")

    old = sys.modules.get("yt_dlp"), app.tempfile.mkdtemp
    sys.modules["yt_dlp"] = types.SimpleNamespace(YoutubeDL=FakeYDL)
    app.tempfile.mkdtemp = mkdtemp
    try:
        app.ytread_prepare("u", "base")
        raise AssertionError("phải ném lỗi")
    except RuntimeError:
        pass
    finally:
        app.tempfile.mkdtemp = old[1]
        if old[0] is not None:
            sys.modules["yt_dlp"] = old[0]
        else:
            sys.modules.pop("yt_dlp", None)
    assert made and not app.os.path.exists(made[0]), made
    s = app.YtReadSession(real_mkdtemp())
    s.sub_kind = "whisper"
    assert app.ytread_orig_hyp(s, 0, None) is None   # transcript tự sinh: không đo phụ đề sai
    s.close()
    assert s.work_dir is None


@case
def yt_subtitle_429_falls_back_not_fatal():
    # yt-dlp coi lỗi tải phụ đề là lỗi chết; YouTube hay trả 429 cho phụ đề dịch máy.
    # Lỗi phụ đề phải trả [] (→ Whisper), không được làm hỏng tải video (D-25).
    import inspect
    import queue as _q
    import types

    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def download(self, urls):
            raise RuntimeError("HTTP Error 429: Too Many Requests")

    fake = types.SimpleNamespace(_queue=_q.Queue(), cancel_flag=False)
    app.time.sleep, real_sleep = (lambda s: None), app.time.sleep
    try:
        cues = app.App._yt_fetch_sub_cues(
            fake, types.SimpleNamespace(YoutubeDL=FakeYDL), "u",
            app.os.path.join(app.tempfile.gettempdir(), "stt_none_x"), "en", 0)
    finally:
        app.time.sleep = real_sleep
    assert cues == []
    body = inspect.getsource(app.App._w_yt_body)
    assert "quality, ffmpeg_loc, hook, None)" in body, \
        "tải video không được kèm phụ đề trong cùng lệnh yt-dlp"


def _tmp_wav(prefix="luyen_"):
    fd, path = app.tempfile.mkstemp(prefix=prefix, suffix=".wav")
    app.os.close(fd)
    return path


class _Widget:
    """Widget giả: chỉ ghi lại configure/set để test không cần mở Tk."""

    def __init__(self):
        self.calls = []

    def configure(self, **kw):
        self.calls.append(kw)

    def set(self, v):
        self.calls.append(v)


@case
def remove_temp_is_safe():
    p = _tmp_wav()
    assert app.remove_temp(p) and not app.os.path.exists(p)
    assert app.remove_temp(p), "file đã xóa rồi vẫn phải trả True"
    assert app.remove_temp(None) and app.remove_temp("")


@case
def practice_replay_wav_is_replaced_not_leaked():
    # Trước đây mỗi lần luyện để lại 1 luyen_*.wav trong %TEMP% (I10).
    import types
    a, b = _tmp_wav(), _tmp_wav()
    fake = types.SimpleNamespace(last_wav=a)
    app.App._set_last_wav(fake, b)
    assert not app.os.path.exists(a) and fake.last_wav == b
    app.App._set_last_wav(fake, b)  # cùng file: không được tự xóa
    assert app.os.path.exists(b)
    app.App._set_last_wav(fake, None)  # đóng app / chấm file ngoài
    assert not app.os.path.exists(b) and fake.last_wav is None


@case
def w_file_removes_temp_recording_on_error():
    import queue as _q
    import types
    p = _tmp_wav("stt_")
    fake = types.SimpleNamespace(_queue=_q.Queue(), cancel_flag=False)

    def boom(_size):
        raise RuntimeError("model hỏng")
    real, app.load_model = app.load_model, boom
    try:
        app.App._w_file(fake, p, "base", None, True, "ghi-am")
    finally:
        app.load_model = real
    msgs = []
    while not fake._queue.empty():
        msgs.append(fake._queue.get_nowait())
    assert ("error", "model hỏng") in msgs, msgs
    assert not app.os.path.exists(p), "bản ghi tạm phải bị xóa cả khi lỗi"


@case
def yt_progress_is_a_fraction():
    # _pbar nhân 100: hook gửi 0..100 làm thanh tiến trình đầy ngay từ đầu.
    import inspect
    f = app.yt_progress_fraction
    assert approx(f({"total_bytes": 200, "downloaded_bytes": 50}), 0.25)
    assert approx(f({"total_bytes_estimate": 400, "downloaded_bytes": 100}), 0.25)
    assert f({"downloaded_bytes": 10}) is None
    assert approx(f({"total_bytes": 10, "downloaded_bytes": 30}), 1.0)
    assert "yt_progress_fraction(d)" in inspect.getsource(app.App._w_yt_body)


@case
def practice_hyp_falls_back_to_segment_text():
    # segs là generator: fallback cũ duyệt lại generator đã cạn → luôn rỗng.
    import queue as _q
    import types

    def segs():
        yield types.SimpleNamespace(text=" xin chào", words=None)

    class FakeModel:
        def transcribe(self, *a, **k):
            return segs(), types.SimpleNamespace(language="vi")

    fake = types.SimpleNamespace(_queue=_q.Queue())
    real, app.load_model = app.load_model, (lambda _s: FakeModel())
    try:
        # đường dẫn không phải WAV → wav_peak trả 1.0, gate im lặng bỏ qua
        app.App._w_prac(fake, "khong_co.wav", "base", "vi", "xin chào", None)
    finally:
        app.load_model = real
    msgs = []
    while not fake._queue.empty():
        msgs.append(fake._queue.get_nowait())
    kind, res = msgs[-1]
    assert kind == "prac_done", msgs
    assert res["hyp"] == "xin chào" and res["score"] == 100.0, res["hyp"]


@case
def recording_belongs_to_one_tab():
    # Recorder dùng chung: bấm nút tab Luyện khi tab 1 đang thu không được chấm
    # nhầm bản thu của tab 1; dừng thì reset đúng UI của tab đang thu.
    import types
    stopped = []
    fake = types.SimpleNamespace(
        p_working=False, busy=False, recording=True, rec_owner="stt",
        p_status=_Widget(),
        _prac_stop_and_score=lambda *a: stopped.append("prac"),
        _prac_start=lambda: stopped.append("start"))
    app.App._prac_record(fake)
    assert stopped == [] and fake.p_status.calls, "không được đụng bản thu tab 1"

    # dừng thu → tab ĐANG THU về idle qua state model (D-31), tab kia không bị đụng
    states = []
    fake = types.SimpleNamespace(
        recording=True, rec_owner="prac",
        recorder=types.SimpleNamespace(stop=lambda: ([], 16000)),
        _set_prac_state=lambda s: states.append(("prac", s)),
        _set_stt_state=lambda s: states.append(("stt", s)))
    frames, rate = app.App._stop_recorder(fake)
    assert frames == [] and rate == 16000
    assert states == [("prac", "idle")], states
    # nút thu trở lại "Thu âm" ở idle (trước đây Esc để kẹt "Dừng & chấm"); B4a: nút tròn
    idle, rec = app.prac_controls("idle", False), app.prac_controls("recording", False)
    assert idle["rec_label"] == "Thu âm" and idle["rec_icon"] == "mic"
    assert rec["rec_label"] == "Dừng & chấm" and rec["rec_icon"] == "stop"
    assert app.prac_controls("result", True)["rec_label"] == "Thu lại"


@case
def ui_font_bundled_and_registered():
    # D-28: Be Vietnam Pro đóng gói kèm giấy phép OFL; đăng ký riêng cho tiến trình.
    for name in app.UI_FONT_FILES + ("OFL.txt",):
        assert (Path(app.FONTS_DIR) / name).is_file(), name
    assert app.register_ui_fonts(app.tempfile.gettempdir() + "\\khong_co_font") == 0
    if sys.platform == "win32":
        assert app.register_ui_fonts() == len(app.UI_FONT_FILES)
    assert app.pick_ui_font(["Arial", "Be Vietnam Pro"]) == "Be Vietnam Pro"
    assert app.pick_ui_font(["Arial", "Segoe UI Variable Text"]) == "Segoe UI Variable Text"
    assert app.pick_ui_font(["Arial"]) == "Segoe UI"
    assert app.FONT_IPA == "Segoe UI", "IPA phải dùng font có đủ θ ŋ ə ɪ (D-28)"


@case
def indicator_images_follow_theme():
    # V-01/V-02: radio/checkbox vẽ bằng ảnh theo theme; checkbox chọn có nền accent.
    c = {"box": "#56636F", "fill": "#FFFFFF", "accent": "#0B6BCB", "mark": "#FFFFFF",
         "bg": "#FFFFFF"}
    for kind in ("check", "radio"):
        for on in (False, True):
            rows = app.indicator_rows(kind, on, 16, c)
            assert len(rows) == 16 and all(len(r) == 16 for r in rows)
            assert rows[0][0] is None, "góc ngoài phải trong suốt"
    on_rows = app.indicator_rows("radio", True, 16, c)
    off_rows = app.indicator_rows("radio", False, 16, c)
    assert on_rows[8][8] == "#0b6bcb" or on_rows[8][8] == "#0B6BCB", on_rows[8][8]
    assert off_rows[8][8].lower() == "#ffffff", "radio chưa chọn phải rỗng (lỗi theme tối cũ)"
    chk = app.indicator_rows("check", True, 16, c)
    assert chk[3][3].lower() == "#0b6bcb", chk[3][3]


@case
def window_icon_drawn_in_code():
    rows = app.logo_rows(32)
    assert len(rows) == 32 and rows[0][0] is None
    assert rows[16][4].lower() == "#0b6bcb", rows[16][4]


@case
def language_names_map_to_codes():
    # V-13: ô Ngôn ngữ hiện tên tiếng Việt, cấu hình vẫn lưu mã.
    assert app.LANG_NAMES[0] == "Tự động" and app.LANG_BY_NAME["Tiếng Việt"] == "vi"
    assert [c for c, _ in app.LANG_LABELS] == app.LANGS
    for code in app.LANGS:
        assert app.LANG_BY_NAME[app.LANG_NAME[code]] == code


def _view_of(target, hyp, lang, lesson_lang=None, **extra):
    res = app.score_pronunciation(target, hyp, lang)
    res.update(target=target, det_lang=lang, gop=None, low_conf=False, garbage=False)
    res.update(extra)
    pairs = [(i, tw, hw) for i, (tw, st, hw, _n) in enumerate(res["items"])
             if st != "ok" and tw and hw]
    if "phon" not in extra:
        res["phon"] = (pron_en.analyze_pairs(pairs) if lang == "en" and pairs else
                       {"issues": [], "counts": {}, "top": [], "by_phoneme": {}, "unknown": []})
    return app.build_result_view(res, {"lang": lesson_lang or lang})


@case
def result_view_english_errors():
    # D-31 / A-02: "nói gì" nằm trong hàm thuần, test được không cần Tk.
    v = _view_of("Think about this thing.", "tink about dis thing", "en")
    kinds = [(c["target"], c["kind"], c["heard"]) for c in v["chips"]]
    assert kinds[0] == ("think", "warn", "tink") and kinds[1][1] == "ok", kinds
    assert v["headline"] == "Đúng 2/4 từ" and not v["perfect"]
    assert v["score_line"] == "2/4 từ", v["score_line"]
    assert v["cards"] and v["cards"][0]["title"].startswith("/θ/"), v["cards"]
    assert v["summary"].startswith("Lỗi chính: /θ/"), v["summary"]
    assert v["sounds"].get("TH"), v["sounds"]
    assert v["state"] == "result"


@case
def result_view_perfect_and_extras():
    v = _view_of("Think about this thing.", "think about this thing", "en")
    assert v["perfect"] and v["headline"] == "Hoàn hảo — đúng cả 4 từ" and v["ring"]["text"] == "✓"
    v2 = _view_of("Think about this thing.", "think about this thing um", "en")
    assert not v2["perfect"] and v2["extras_total"] == 1, "từ thừa không được khen hoàn hảo"


@case
def result_view_vietnamese_counts_by_lesson_language():
    v = _view_of("Lan năm nay lên lớp", "nan lăm nay nên lớp", "vi")
    assert [c["code"] for c in v["chips"] if c["kind"] == "warn"] == ["nl", "nl", "nl"]
    assert v["sounds"] == {"nl": 3}, v["sounds"]
    # Whisper nhận nhầm tiếng Anh cho bài Việt → KHÔNG đếm âm vị Anh vào bài Việt (H-03)
    wrong = _view_of("Lan năm nay", "nan lăm nay", "en", lesson_lang="vi")
    assert wrong["sounds"] == {}, wrong["sounds"]
    missing = _view_of("Lan năm nay lên", "lan năm nay", "vi")
    assert missing["chips"][-1]["kind"] == "missing" and missing["chips"][-1]["heard"] is None


@case
def result_view_gop_levels_not_percent():
    # I7: GOP thành mức chữ cho giao diện mới; số vẫn giữ trong view cho "Chi tiết".
    it = pron_en._issue("TH", "T", "think", 0, 3)
    it.update(score=18.0, ref_score=71.0, wi=0, ph="TH")
    it2 = pron_en._issue("DH", "D", "this", 0, 3)
    it2.update(score=31.0, ref_score=66.0, wi=2, ph="DH")
    v = _view_of("Think about this thing.", "tink about dis thing", "en",
                 gop={"issues": [it, it2], "has_ref": True})
    assert [c["level"] for c in v["cards"]] == ["lệch rõ", "hơi lệch"]
    assert v["has_gop"] and "18%" in v["cards"][0]["detail"]
    assert v["sounds"] == {"TH": 1, "DH": 1} and v["n_issues"] == 2


@case
def screen_states_drive_controls():
    # D-31: một chỗ quyết định nút/thanh tiến trình theo trạng thái.
    c = app.stt_controls("processing", "▶  Bắt đầu")
    assert not c["run_enabled"] and c["cancel_enabled"] and c["show_pbar"]
    c = app.stt_controls("result", "▶  Bắt đầu")
    assert c["run_enabled"] and c["run_text"] == "▶  Bắt đầu" and not c["show_pbar"]
    assert not c["cancel_enabled"]
    assert app.stt_controls("recording", "x")["run_text"].startswith("■")
    p = app.prac_controls("scoring", True)
    assert not p["rec_enabled"] and not p["replay_enabled"] and p["show_pbar"]
    p = app.prac_controls("result", True)
    assert p["rec_enabled"] and p["replay_enabled"] and not p["show_pbar"]
    assert not app.prac_controls("idle", False)["replay_enabled"]
    assert set(app.PRAC_STATES) >= {"unsure", "scoring"}


@case
def history_keeps_tries_and_migrates():
    # D-30: lưu từng lần (tối đa 30); file cũ không có "tries" vẫn dùng được.
    old = {"en_th": {"n": 2, "best": 75.0, "last": 50.0, "ph": {"TH": 2}}}
    v = _view_of("Think about this thing.", "tink about dis thing", "en")
    app.hist_add_try(old, "en_th", v, "2026-10-22 10:00")
    h = old["en_th"]
    assert h["n"] == 3 and h["last"] == 50.0 and h["best"] == 75.0
    assert h["tries"] == [{"ts": "2026-10-22 10:00", "c": 2, "t": 4, "ph": v["sounds"]}]
    for i in range(40):
        app.hist_add_try(old, "en_th", v, "t%d" % i)
    assert len(old["en_th"]["tries"]) == app.HIST_TRIES_MAX
    unsure = dict(v, state="unsure")
    before = old["en_th"]["n"]
    app.hist_add_try(old, "en_th", unsure, "x")
    assert old["en_th"]["n"] == before, "lần 'chưa nghe rõ' không được lưu (D-29/D-30)"


@case
def weakest_sound_is_per_language():
    hist = {"vi2": {"ph": {"N": 10, "AA": 4, "nl": 2}},   # dữ liệu cũ lẫn âm vị Anh
            "en_th": {"ph": {"TH": 5, "DH": 4}}}
    assert app.hist_weakest(hist, "vi") == ("N/L", 2)
    assert app.hist_weakest(hist, "en") == ("/θ/", 5)
    assert app.hist_weakest({"vi1": {"ph": {"N": 10}}}, "vi") is None


@case
def practice_keeps_word_timings():
    # S-5: giữ mốc thời gian từng từ để vẽ nhãn dưới biểu đồ ngữ điệu (B4).
    import queue as _q
    import types

    def segs():
        yield types.SimpleNamespace(text=" xin chào", words=[
            types.SimpleNamespace(word=" xin", probability=0.9, start=0.1, end=0.4),
            types.SimpleNamespace(word=" chào", probability=0.8, start=0.5, end=0.9)])

    class FakeModel:
        def transcribe(self, *a, **k):
            return segs(), types.SimpleNamespace(language="vi")

    fake = types.SimpleNamespace(_queue=_q.Queue())
    real, app.load_model = app.load_model, (lambda _s: FakeModel())
    try:
        app.App._w_prac(fake, "khong_co.wav", "base", "vi", "xin chào", None)
    finally:
        app.load_model = real
    msgs = []
    while not fake._queue.empty():
        msgs.append(fake._queue.get_nowait())
    kind, res = msgs[-1]
    assert kind == "prac_done", msgs
    assert [w["w"] for w in res["words_t"]] == ["xin", "chào"]
    assert res["words_t"][1]["s"] == 0.5 and res["words_t"][1]["e"] == 0.9


def _gate_of(target, hyp, lang, **extra):
    res = app.score_pronunciation(target, hyp, lang)
    res.update(target=target, **extra)
    return app.evidence_gate(res)


@case
def evidence_gate_blocks_hallucination_and_noise():
    # D-29 / P-03 / P-04: chuỗi Whisper tự sinh không được chấm thành lỗi của người học.
    vi2 = app.PRACTICE_SETS["vi2"]["target"]
    assert _gate_of(vi2, "cảm ơn các bạn đã theo dõi hẹn gặp lại các bạn", "vi") == "hallucination"
    assert _gate_of("Read this line.", "please subscribe", "en") == "hallucination"
    # câu mẫu chứa đúng cụm đó → đọc đúng thì vẫn chấm
    assert _gate_of("Cảm ơn các bạn đã theo dõi.", "cảm ơn các bạn đã theo dõi", "vi") is None
    # khớp nguyên từ: "subscribers" không phải "subscribe"
    assert _gate_of("Our subscribers read it.", "our subscribers read it", "en") is None
    # quá dài so với câu mẫu + điểm thấp → chuỗi rác
    assert _gate_of("Lan năm nay", "một hai ba bốn năm sáu", "vi") == "garbage"
    # máy không chắc + đúng < 50 % → chưa chấm; đúng ≥ 50 % thì vẫn chấm
    assert _gate_of("Think about this thing.", "tink a dis ting", "en", low_conf=True) == "low_conf"
    assert _gate_of("Think about this thing.", "tink about this thing", "en", low_conf=True) is None
    assert _gate_of("Think about this thing.", "tink about dis thing", "en") is None


@case
def unsure_view_shows_no_score_and_is_not_stored():
    vi2 = app.PRACTICE_SETS["vi2"]["target"]
    v = _view_of(vi2, "cảm ơn các bạn đã theo dõi", "vi")
    assert v["state"] == "unsure" and v["gate"] == "hallucination"
    assert v["score_line"] == "" and v["status_line"] == "" and v["ring"]["text"] == "?"
    assert v["headline"] == "Máy chưa nghe rõ bài đọc" and v["tips"] and v["heard_note"]
    assert v["sounds"] == {}, "lần chưa nghe rõ không đếm âm hay sai"
    hist = {}
    app.hist_add_try(hist, "vi2", v, "t")
    assert hist == {}, "lần chưa nghe rõ không lưu vào lịch sử (D-29/D-30)"


@case
def perfect_needs_every_word():
    # câu dài sai 1 từ: 20/21 = 95,2 % nhưng KHÔNG được khen "đúng cả 21 từ"
    words = ["ba"] * 21
    hyp = list(words)
    hyp[10] = "cá"
    v = _view_of(" ".join(words), " ".join(hyp), "vi")
    assert not v["perfect"] and v["headline"] == "Đúng 20/21 từ", v["headline"]
    assert _view_of(" ".join(words), " ".join(words), "vi")["perfect"]


@case
def vietnamese_rhyme_state_named():
    # S-4: "lắm" → "lám" (khác dấu phụ ± thanh) là "sai vần/dấu", không phải "chưa khớp"
    assert app.strip_marks_vi("lắm") == "lam" and app.strip_marks_vi("Đường") == "Duong"
    r = app.score_pronunciation("Lan nói lắm, mẹ bảo má", "lan nói lám mẹ bảo ma", "vi")
    st = {t: s for t, s, _h, _n in r["items"]}
    assert st["lắm"] == "rhyme" and st["má"] == "tone", r["items"]
    assert r["rhymes"] == 1 and r["tones"] == 1 and r["correct"] == 4
    v = _view_of("Lan nói lắm, mẹ bảo má", "lan nói lám mẹ bảo ma", "vi")
    cards = {c["word"]: c for c in v["cards"]}
    assert cards["lắm"]["kind"] == "bad" and cards["lắm"]["level"] == "sai vần/dấu"
    assert "l + ăm + thanh sắc" in cards["lắm"]["tip"], cards["lắm"]["tip"]
    assert cards["má"]["level"] == "sai dấu thanh"
    assert v["sounds"] == {"rhyme": 1, "tone": 1}, v["sounds"]


@case
def vi_spell_splits_syllable():
    assert app.vi_spell("lắm") == "l + ăm + thanh sắc"
    assert app.vi_spell("nghiêng") == "ngh + iêng + thanh ngang"
    assert app.vi_spell("Ạ") == "a + thanh nặng"
    assert app.vi_spell("gì") == "g + i + thanh huyền"   # "gi" đứng một mình: g + i


@case
def ipa_text_detected_for_font():
    # D-28: chữ IPA vẽ bằng FONT_IPA; chữ Việt thì không.
    assert app.has_ipa("/θ/ trong “think”") and app.has_ipa("ˈθɪŋk") and app.has_ipa("ð")
    assert not app.has_ipa("lắm nghiêng đường Ạ") and not app.has_ipa("") and not app.has_ipa(None)


@case
def wav_segment_bounds_clamped():
    # ▶ Bạn đọc: nới đoạn một từ, kẹp trong file, không bao giờ âm/ngược
    assert app.wav_segment_bounds(16000, 16000, 0.5, 0.5, pad=0.25) == (4000, 12000)
    assert app.wav_segment_bounds(1000, 16000, 0.0, 0.01) == (0, 1000)
    a, b = app.wav_segment_bounds(16000, 16000, 0.9, 0.1, pad=0.25)
    assert a == b and a > 0, (a, b)


@case
def theme_text_contrast_ok():
    # S-9 / D-32: mọi cặp chữ/nền của kết quả ≥ 4,5 : 1 ở cả hai theme
    def lum(h):
        def ch(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)
    pairs = [("ok_fg", "ok_bg"), ("warn_fg", "warn_bg"), ("bad_fg", "bad_bg"),
             ("fg", "info_bg"), ("accent_fg", "info_bg"), ("muted", "card"),
             ("accent_fg", "card"), ("fg", "card"), ("muted", "side"), ("fg", "side"),
             ("accent_fg", "side"), ("muted", "bg"), ("fg", "bg"), ("muted", "card2"),
             ("white", "accent"), ("white", "rec"), ("warn_fg", "card"), ("bad_fg", "card"),
             ("ok_fg", "card")]
    for name, P in app.THEMES.items():
        P = dict(P, white="#FFFFFF")
        for a, b in pairs:
            hi, lo = sorted((lum(P[a]), lum(P[b])), reverse=True)
            ratio = (hi + 0.05) / (lo + 0.05)
            assert ratio >= 4.5, f"{name}: {a}/{b} = {ratio:.1f}"


@case
def stage_words_mark_each_original_word():
    # B4a: câu trên sân khấu giữ chữ hoa/dấu câu gốc, gạch chân theo chip của view
    v = _view_of("Think about this thing.", "tink about dis thing", "en")
    w = app.stage_words("Think about this thing.", v)
    assert [x["text"] for x in w] == ["Think", "about", "this", "thing."]
    assert [x["kind"] for x in w] == ["warn", "ok", "warn", "ok"], w
    assert w[0]["note"] == "nghe “tink”" and w[1]["note"] == "✓"
    miss = _view_of("Lan năm nay lên", "lan năm nay", "vi")
    assert app.stage_words("Lan năm nay lên", miss)[-1] == {
        "text": "lên", "kind": "bad", "note": "(thiếu)"}
    # chưa chấm / "chưa nghe rõ": không tô màu câu (D-29)
    vi2 = app.PRACTICE_SETS["vi2"]["target"]
    unsure = _view_of(vi2, "cảm ơn các bạn đã theo dõi", "vi")
    assert all(x["kind"] == "plain" for x in app.stage_words(vi2, unsure))
    assert all(x["kind"] == "plain" for x in app.stage_words(vi2, None))


@case
def shell_helpers():
    # thanh điều hướng thu về 60 px khi cửa sổ hẹp (canvas: 980×640 là chế độ gọn)
    assert app.nav_compact(980 * 2.5, 2.5) and not app.nav_compact(1480 * 2.5, 2.5)
    assert app.short_mic_name("Microphone Array (Intel® Smart Sound Technology for Digital "
                              "Microphones) [Windows DirectSound]").endswith("…")
    assert app.short_mic_name("USB Mic [MME]") == "USB Mic"
    assert app.meter_cells(0.0) == 0 and app.meter_cells(1.0) == 20
    # panel kết quả ≈ nửa vùng nội dung, kẹp 340–640 px × S (yêu cầu: cả kết quả trên một trang)
    S = 2.5
    assert app.side_width((1480 - 232) * S, S) == int(0.48 * 1248 * S)
    assert app.side_width(3000 * S, S) == int(640 * S)
    assert app.side_width(500 * S, S) == int(340 * S)
    assert 0 < app.meter_cells(0.05) < 20


def _write_bursts(path, specs, sr=16000):
    """Ghi WAV gồm các đoạn sin (hz, biên độ, giây) cách nhau 0,12 s im lặng."""
    import wave
    parts = []
    for hz, amp, sec in specs:
        t = np.arange(int(sr * sec)) / sr
        parts += [amp * np.sin(2 * np.pi * hz * t), np.zeros(int(sr * 0.12))]
    x = (np.concatenate(parts) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(x.tobytes())


@case
def stress_picks_loud_high_word():
    # S-5b / D-34: từ to + cao hơn hẳn trong câu của CHÍNH người nói là từ được nhấn
    prom, top = prosody.stress_from_features([60, 70, 60, 61], [0.0, 3.0, 0.0, None])
    assert top == [1], (prom, top)
    _p, tie = prosody.stress_from_features([60, 66, 66, 60], [0.0, 1.0, 1.0, 0.0])
    assert sorted(tie) == [1, 2], tie            # hai từ gần bằng nhau → cả hai
    assert prosody.stress_from_features([60, 70], [0, 3]) == ([], [])   # < 3 từ
    path = _tmp_wav("stress_")
    try:
        _write_bursts(path, [(140, 0.2, 0.3), (190, 0.6, 0.3), (140, 0.2, 0.3),
                             (130, 0.2, 0.3)])
        words = [{"s": 0.00 + i * 0.42, "e": 0.30 + i * 0.42} for i in range(4)]
        r = prosody.word_stress(path, words)
        assert r and r["top"] == [1], r
        c = prosody.contour(path)
        assert c and 1.3 < c["span"] < 1.7, c and c["span"]   # bỏ im lặng đuôi
    finally:
        app.remove_temp(path)


@case
def heard_words_map_to_target():
    m = app.map_to_target("Think about this thing.", ["Tink", "about", "um", "this", "thing."])
    assert m == [0, 1, None, 2, 3], m
    # mốc từ của 14 câu mẫu (build_lessons.py --word-times) phủ đủ mọi từ của câu
    times = app.load_sample_word_times()
    assert len(times) == 14, len(times)
    for lid, words in times.items():
        target = app.PRACTICE_SETS[lid]["target"]
        idx = app.map_to_target(target, [w["w"] for w in words])
        assert sorted(i for i in idx if i is not None) == list(
            range(len(app.norm_words(target)))), (lid, idx)


@case
def intonation_caption_rules():
    # S-5: MỘT câu, không số, không điểm (D-10)
    cap = app.inton_caption
    assert cap({"final_ref": -1.3, "final_usr": -1.4, "range_ref": 13, "range_usr": 12}) == (
        "Cuối câu bạn xuống giọng giống mẫu ✓", "ok")
    assert cap({"final_ref": -1.0, "final_usr": 0.9, "range_ref": 10, "range_usr": 9})[0] == \
        "Cuối câu mẫu xuống giọng, bạn lại lên giọng"
    assert cap({"final_ref": -1.0, "final_usr": 0.1, "range_ref": 10, "range_usr": 9})[0] == \
        "Cuối câu mẫu xuống giọng, bạn lại giữ giọng ngang"
    assert cap({"final_ref": -1.0, "final_usr": -1.0, "range_ref": 10, "range_usr": 4}) == (
        "Giọng bạn hơi đều — thử nhấn mạnh từ khoá hơn", "warn")
    assert cap({})[1] is None
    for text, _t in (cap({"final_ref": -1, "final_usr": 1}), cap({})):
        assert "st" not in text.split() and "DTW" not in text


@case
def speed_and_stress_sentences():
    assert app.speed_note(1.2, 1.6) == "Bạn đọc chậm hơn mẫu ~35 % (1,6 s / 1,2 s)"
    assert app.speed_note(1.6, 1.2).startswith("Bạn đọc nhanh hơn mẫu ~25 %")
    assert app.speed_note(1.2, 1.3) == "Tốc độ gần giống mẫu (1,3 s / 1,2 s)"
    assert app.speed_note(None, 1.2) is None
    w = ["think", "about", "this", "thing"]
    assert app.stress_note(None, [1], w) == "Bạn nhấn mạnh nhất: “about”"
    assert app.stress_note([0], [0, 2], w) == "Bạn nhấn đúng từ như mẫu ✓ (“think”)"
    assert app.stress_note([0], [1], w) == "Mẫu nhấn “think”, bạn nhấn “about”"
    assert app.stress_note([0], [], w) is None


@case
def intonation_view_labels_and_markers():
    v = _view_of("Think about this thing.", "tink about dis thing", "en")
    words_t = [{"w": "tink", "s": 0.1, "e": 0.4}, {"w": "about", "s": 0.45, "e": 0.8},
               {"w": "dis", "s": 0.85, "e": 1.0}, {"w": "thing", "s": 1.05, "e": 1.4}]
    ref_words = [{"w": "Think", "s": 0.0, "e": 0.3}, {"w": "about", "s": 0.3, "e": 0.6},
                 {"w": "this", "s": 0.6, "e": 0.8}, {"w": "thing.", "s": 0.8, "e": 1.2}]
    res = {"target": "Think about this thing.", "words_t": words_t,
           "inton": {"dur_usr": 1.6, "final_ref": -1.3, "final_usr": -1.4,
                     "range_ref": 13, "range_usr": 12},
           "stress": {"usr": {"prom": [0, 2, 0, 0], "top": [1]},
                      "ref": {"prom": [2, 0, 0, 0], "top": [0]}, "ref_words": ref_words}}
    iv = app.inton_view(res, v)
    assert [l["text"] for l in iv["labels"]] == ["think", "about", "this", "thing"]
    assert [l["err"] for l in iv["labels"]] == [True, False, True, False]
    assert [l["su"] for l in iv["labels"]] == [False, True, False, False]
    assert [l["sr"] for l in iv["labels"]] == [True, False, False, False]
    assert iv["stress"] == "Mẫu nhấn “think”, bạn nhấn “about”"
    # tốc độ theo mốc từ (bỏ im lặng): bạn 0,1→1,4 s, mẫu 0→1,2 s
    assert iv["speed"] == "Tốc độ gần giống mẫu (1,3 s / 1,2 s)", iv["speed"]
    assert iv["caption"].endswith("✓") and iv["tone"] == "ok"
    # bài không có mốc mẫu → chỉ nói về bạn; "chưa nghe rõ" → không có mục ngữ điệu
    res["stress"] = {"usr": {"prom": [0, 2, 0, 0], "top": [1]}, "ref": None, "ref_words": []}
    assert app.inton_view(res, v)["stress"] == "Bạn nhấn mạnh nhất: “about”"
    assert app.inton_view(res, dict(v, state="unsure")) is None


@case
def progress_summary_lines():
    # S-7: phân số theo từ, đường xu hướng ≤ 10 lần; file cũ không có "tries" vẫn hiện được
    h = {"n": 6, "tries": [{"c": c, "t": 4} for c in (1, 2, 3, 2, 3, 2)]}
    ps = app.progress_summary(h, ("/θ/", 4), "en")
    assert ps["line1"] == "6 lần · tốt nhất 3/4 · lần trước 2/4", ps
    assert ps["line2"] == "Âm hay sai (tiếng Anh): /θ/, 4 lần"
    assert ps["spark"] == [0.25, 0.5, 0.75, 0.5, 0.75, 0.5]
    old = app.progress_summary({"n": 2, "best": 75.0, "last": 50.0})
    assert old["line1"] == "2 lần · tốt nhất 75% · lần trước 50%" and old["spark"] == []
    assert app.progress_summary(None)["line1"] == "Chưa luyện bài này."


@case
def transcription_screen_states():
    # S-8: vùng chữ + panel theo trạng thái; kết quả cũ không mất khi lần sau lỗi
    v = app.stt_view
    assert v("idle", False) == ("empty", "empty")
    assert v("processing", True) == ("processing", "processing")
    assert v("recording", False) == ("recording", "recording")
    assert v("result", True) == ("result", "result")
    assert v("error", True) == ("result", "error") and v("error", False) == ("empty", "error")
    assert [app.short_duration(x) for x in (18, 75, 3723, 0)] == ["0:18", "1:15", "1:02:03",
                                                                   "0:00"]


@case
def gop_clearly_off_marks_stage_word():
    # D-35: chữ đúng ("think") nhưng GOP thấy /θ/ lệch rõ → gạch cam trên câu, điểm KHÔNG đổi
    it = pron_en._issue("TH", "T", "think", 0, 3)
    it.update(score=12.0, ref_score=70.0, wi=0, ph="TH")
    it2 = pron_en._issue("DH", "D", "this", 0, 3)
    it2.update(score=40.0, ref_score=70.0, wi=2, ph="DH")      # hơi lệch → không gạch
    v = _view_of("Think about this thing.", "think about this thing", "en",
                 gop={"issues": [it, it2], "has_ref": True})
    assert v["correct"] == 4 and v["headline"] == "Đúng 4/4 từ", v["headline"]
    assert v["gop_marks"] == {0: ["θ"]}, v["gop_marks"]
    w = app.stage_words("Think about this thing.", v)
    assert w[0] == {"text": "Think", "kind": "warn", "note": "âm /θ/ lệch"}, w[0]
    assert [x["kind"] for x in w[1:]] == ["ok", "ok", "ok"]
    # lỗi cấp từ (máy nghe sai chữ) vẫn ưu tiên ghi chú "nghe ‘…’"
    v2 = _view_of("Think about this thing.", "tink about this thing", "en",
                  gop={"issues": [it], "has_ref": True})
    assert app.stage_words("Think about this thing.", v2)[0]["note"] == "nghe “tink”"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    failed = 0
    for name, fn in CASES:
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {name}: {exc}")
            if not isinstance(exc, AssertionError):
                traceback.print_exc(limit=2)

    print()
    print(f"TỔNG: {len(CASES) - failed}/{len(CASES)} PASS · {failed} FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
