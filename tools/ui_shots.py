#!/usr/bin/env python3
"""Chụp màn hình Oriole ở các trạng thái cố định — để so sánh trước/sau khi sửa giao diện.

Không cần mic/model/mạng. KHÔNG ghi gì vào config.json hay practice_history.json
(chặn save_config, _save_hist, _record_hist). Ảnh ghi ra %TEMP%\\oriole_shots\\<nhãn>\\
(ngoài repo, I10). Chạy:

    C:\\Users\\ADMIN\\miniforge3\\python.exe tools\\ui_shots.py before
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import struct
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import app  # noqa: E402
import pron_en  # noqa: E402
import prosody  # noqa: E402

# ---- an toàn: không đụng file của người dùng ----
app.save_config = lambda cfg: None
app.App._save_hist = lambda self: None
app.App._record_hist = lambda self, *a, **k: None


class _BMI(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD),
                ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


def grab_png(x, y, w, h, path):
    """Chụp vùng màn hình (toạ độ vật lý) ra PNG — chỉ ctypes + zlib, không cần PIL."""
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    sdc = user32.GetDC(0)
    mdc = gdi32.CreateCompatibleDC(sdc)
    bmp = gdi32.CreateCompatibleBitmap(sdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    gdi32.BitBlt(mdc, 0, 0, w, h, sdc, x, y, 0x00CC0020)
    bi = _BMI()
    bi.biSize = ctypes.sizeof(bi)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount = w, -h, 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(0, sdc)
    data = buf.raw
    raw = bytearray()
    for r in range(h):
        row = data[r * w * 4:(r + 1) * w * 4]
        rgb = bytearray(w * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = row[2::4], row[1::4], row[0::4]
        raw.append(0)
        raw += rgb

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "shots"
    out = Path(tempfile.gettempdir()) / "oriole_shots" / label
    out.mkdir(parents=True, exist_ok=True)

    A = app.App()
    A.attributes("-topmost", True)

    def shot(name):
        for _ in range(3):
            A.update_idletasks()
            A.update()
            A.after(120)
        grab_png(A.winfo_rootx(), A.winfo_rooty(), A.winfo_width(), A.winfo_height(),
                 out / (name + ".png"))
        print("shot", name)

    def theme(name):
        A.theme_name.set(name)
        A._apply_theme()

    def pick(sid):
        A.prac_mode.set("set")
        A._prac_mode_changed()
        A.cb_prac.current(app.SET_IDS.index(sid))
        A._refresh_practice()

    def result(target, hyp, lang, conf=0.85, inton=None):
        res = app.score_pronunciation(target, hyp, lang)
        res.update(target=target, det_lang=lang, conf=conf, low_conf=conf < 0.35, gop=None)
        hw_n, tw_n = len(res["hyp"].split()), len(target.split())
        res["garbage"] = bool(hw_n >= 8 and hw_n >= 2 * tw_n and res["score"] < 35)
        pairs = [(i, tw, hw) for i, (tw, st, hw, _n) in enumerate(res["items"])
                 if st != "ok" and tw and hw]
        res["phon"] = (pron_en.analyze_pairs(pairs) if lang == "en" and pairs else
                       {"issues": [], "counts": {}, "top": [], "by_phoneme": {}, "unknown": []})
        res["inton"] = inton
        if inton and lang == "en":
            # "bản thu" = câu mẫu chậm; mốc từ = mốc mẫu kéo theo độ dài (đủ để xem bố cục)
            k = inton["dur_usr"] / max(inton["dur_ref"], 1e-6)
            heard = res["hyp"].split()
            res["words_t"] = [{"w": h, "s": w["s"] * k, "e": w["e"] * k}
                              for h, w in zip(heard, ref_words)]
            usr_wav = slow if k > 1.05 else ref
            res["stress"] = {"usr": prosody.word_stress(usr_wav, res["words_t"]),
                             "ref": prosody.word_stress(ref, ref_words),
                             "ref_words": ref_words}
        return res

    en_t = app.PRACTICE_SETS["en_th"]["target"]
    vi1 = app.PRACTICE_SETS["vi1"]["target"]
    vi2 = app.PRACTICE_SETS["vi2"]["target"]
    ref = str(Path(app.MAU_DIR) / "en" / "en_th.wav")
    slow = str(Path(app.MAU_DIR) / "en" / "en_th_slow.wav")
    ref_words = app.load_sample_word_times()["en_th"]
    en_bad = en_t.lower().replace("think", "tink").replace("this", "dis").rstrip(".")
    # lịch sử giả CHỈ trong bộ nhớ (ghi file đã bị chặn ở trên) để thấy đường xu hướng
    A.hist["en_th"] = {"n": 6, "best": 75.0, "last": 50.0, "ph": {"TH": 4},
                       "tries": [{"ts": "x", "c": c, "t": 4, "ph": {}}
                                 for c in (1, 2, 3, 2, 3, 2)]}

    # ---- Chuyển văn bản ----
    theme("light")
    A._show_screen("stt")
    A.src.set("file")
    A._src_changed()
    shot("00_stt_empty_light")
    A.file_path.set(r"D:\Bai giang\bai-giang-n-l.mp3")
    A._log("File: bai-giang-n-l.mp3  ·  model small")
    A._set_stt_state("processing")
    A._pbar(0.62)
    A.status.set("Bước 2/2 · đang nhận dạng giọng nói… 62 %")
    shot("00b_stt_processing_light")
    A._on_result({"cues": [
        (0.0, 3.2, "Xin chào các bạn, hôm nay chúng ta sẽ học cách phát âm âm N và L."),
        (3.2, 7.9, "Đầu tiên, hãy đặt đầu lưỡi chạm vào lợi trên, ngay sau răng cửa."),
        (7.9, 12.4, "Với âm N, hơi thoát ra bằng mũi; với âm L, hơi thoát ra hai bên lưỡi."),
        (12.4, 18.0, "Bây giờ hãy đọc theo tôi: na, la, năm, lăm, nên, lên.")],
        "media": None, "base": "bai-giang-n-l", "note": "Xong: 4 dòng · vi (99%)"})
    shot("01_stt_result_light")
    A._toggle_log()
    shot("01b_stt_log_open_light")
    A._toggle_log()
    A.src.set("yt")
    A._src_changed()
    A.yt_url.set("https://www.youtube.com/watch?v=2UIqadUjQf8")
    A.y_subs.set(False)
    A._yt_subs_changed()
    shot("02_stt_youtube_subs_off_light")
    A.y_subs.set(True)
    A._yt_subs_changed()
    A.src.set("rec")
    A._src_changed()
    A._set_stt_state("recording")
    A.lbl_rec_level.configure(text="● Đang thu · 0:12 / 15:00")
    A._draw_meter(0.08, A.stt_meter)
    shot("02b_stt_recording_light")
    A._set_stt_state("idle")
    A.src.set("file")
    A._src_changed()

    # ---- Luyện phát âm ----
    A._show_screen("prac")
    pick("en_th")
    shot("03a_prac_idle_light")
    A._set_prac_state("recording")
    A.lbl_plevel.configure(text="● Đang thu · 00:04 · đã nghe giọng · đọc xong app tự dừng")
    A._draw_meter(0.08)
    shot("03b_prac_recording_light")
    A._set_prac_state("idle")
    A._prac_done(result(en_t, en_bad, "en", inton=prosody.compare(ref, slow)))
    shot("03_prac_en_result_light")
    # trường hợp dài nhất: 6 lỗi GOP (4 dòng CẦN SỬA + "… và 2 lỗi khác") + ngữ điệu
    worst = result(en_t, "think about the siege stim", "en", inton=prosody.compare(ref, slow))
    issues = []
    for exp, got, word, wi, sc in (("TH", "L", "think", 0, 12), ("K", "T", "think", 0, 18),
                                   ("TH", "ER", "thing", 3, 15), ("DH", "Z", "this", 2, 20),
                                   ("NG", "N", "thing", 3, 30), ("AW", "AA", "about", 1, 40)):
        it = pron_en._issue(exp, got, word, 0, 3)
        it.update(score=sc, ref_score=70.0, wi=wi, ph=exp)
        issues.append(it)
    worst["gop"] = {"issues": issues, "has_ref": True}
    A._prac_done(worst)
    shot("03c_prac_en_gop_full_light")
    A.prac_mode.set("guide")
    A._prac_mode_changed()
    shot("04_prac_switch_to_guide_light")
    pick("en_th")
    A._prac_done(result(en_t, en_t.lower().rstrip("."), "en", inton=prosody.compare(ref, ref)))
    shot("05_prac_en_perfect_light")
    pick("vi1")
    A._prac_done(result(vi1, "nan lăm nay nên lớp nói năng lưu loát lám", "vi"))
    shot("06_prac_vi_result_light")
    pick("vi2")
    A._prac_done(result(vi2, "cảm ơn các bạn đã theo dõi hẹn gặp lại các bạn trong video "
                             "tiếp theo nhé cảm ơn các bạn", "vi", conf=0.22))
    shot("07_prac_noisy_light")
    theme("dark")
    pick("en_th")
    A._prac_done(result(en_t, en_bad, "en", inton=prosody.compare(ref, slow)))
    shot("08_prac_en_result_dark")

    # ---- Cài đặt ----
    A._show_screen("set")
    shot("09_settings_dark")
    theme("light")
    shot("10_settings_light")

    # ---- cửa sổ tối thiểu ----
    A.geometry("%dx%d" % (int(980 * A.S), int(640 * A.S)))
    A._show_screen("prac")
    pick("en_th")
    A._prac_done(result(en_t, en_bad, "en", inton=prosody.compare(ref, slow)))
    shot("11_prac_min_light")
    pick("vi1")
    A._prac_done(result(vi1, "nan lăm nay nên lớp nói năng lưu loát lám", "vi"))
    shot("12_prac_vi_min_light")
    theme("dark")
    shot("13_prac_vi_min_dark")
    theme("light")
    A._show_screen("stt")
    A.src.set("yt")
    A._src_changed()
    shot("14_stt_youtube_min_light")
    A._show_screen("set")
    shot("15_settings_min_light")
    A.destroy()
    print("saved to", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
