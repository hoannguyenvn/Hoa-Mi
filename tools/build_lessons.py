"""Tạo lessons_en.json + audio mẫu cho tab Luyện phát âm (tiếng Anh).

Chạy 1 lần (cần mạng cho edge-tts):
    C:\\Users\\ADMIN\\miniforge3\\python.exe tools\\build_lessons.py [--force]
Khi chạy lại: bỏ qua file đã có, trừ khi --force.
"""
import asyncio
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import pron_en  # noqa: E402

VOICE = "en-US-AriaNeural"
OUT_DIR = os.path.join(BASE, "mau", "en")
JSON_PATH = os.path.join(BASE, "lessons_en.json")

# ------------------------------------------------------------------ nội dung
LESSONS = [
    {
        "id": "en_th", "group": "Phụ âm",
        "title": "Anh — Âm /θ/ và /ð/ (think, this)",
        "focus": ["TH", "DH"],
        "target": "Think about this thing.",
        "words": ["think", "about", "this", "thing"],
        "tips": [
            "Đặt ĐẦU LƯỠI GIỮA hai răng cửa rồi thổi hơi ra — không chạm lợi như /t/.",
            "/ð/ (this) giữ nguyên khẩu hình đó nhưng RUNG dây thanh; /θ/ (think) thì không rung.",
        ],
        "pairs": [["think", "tink"], ["this", "dis"], ["thing", "ting"]],
    },
    {
        "id": "en_th2", "group": "Phụ âm",
        "title": "Anh — /θ/ trong cụm (three, thousand)",
        "focus": ["TH"],
        "target": "Three thousand thanks.",
        "words": ["three", "thousand", "thanks"],
        "tips": [
            "Trong 'three' và 'thousand', lưỡi vẫn phải thò ra rồi mới chuyển sang /r/ hoặc /aʊ/.",
            "Lỗi hay gặp: rụt lưỡi vào → 'tree', 'tousand', 'tanks'.",
        ],
        "pairs": [["three", "tree"], ["thousand", "tousand"], ["thanks", "tanks"]],
    },
    {
        "id": "en_sh", "group": "Phụ âm",
        "title": "Anh — /ʃ/ và /s/ (she, seashells)",
        "focus": ["SH", "S"],
        "target": "She sells seashells.",
        "words": ["she", "sells", "seashells"],
        "tips": [
            "/ʃ/: CHU MÔI tròn, lưỡi lùi ra sau, hơi xát mạnh.",
            "/s/: môi bẹt, đầu lưỡi gần lợi trên, hơi xì nhẹ.",
        ],
        "pairs": [["she", "see"], ["sells", "sells"], ["ship", "sip"]],
    },
    {
        "id": "en_plural", "group": "Âm cuối",
        "title": "Anh — /s/ và /z/ cuối (cats, dogs)",
        "focus": ["S", "Z"],
        "target": "Cats love dogs and books.",
        "words": ["cats", "love", "dogs", "books"],
        "tips": [
            "Sau âm vô thanh (t, k, p) → /s/: cats, books.",
            "Sau âm hữu thanh (g, d, m, n) → /z/: dogs. Sờ cổ phải thấy rung.",
        ],
        "pairs": [["cats", "cat"], ["dogs", "dog"], ["books", "book"]],
    },
    {
        "id": "en_final", "group": "Âm cuối",
        "title": "Anh — Bật âm cuối /p t k/ (stop, cat)",
        "focus": ["P", "T", "K"],
        "target": "Stop that big cat.",
        "words": ["stop", "that", "big", "cat"],
        "tips": [
            "Âm cuối phải BẬT ra rồi mới kết thúc từ: stoP, caT, biG.",
            "Đừng nuốt âm cuối — đó là lỗi phổ biến nhất của người Việt.",
        ],
        "pairs": [["cat", "ca"], ["stop", "sto"], ["big", "bi"]],
    },
    {
        "id": "en_cluster", "group": "Âm cuối",
        "title": "Anh — Cụm phụ âm cuối (-sks, -xts, -fts)",
        "focus": ["S", "K", "T"],
        "target": "He asks for texts and gifts.",
        "words": ["asks", "texts", "gifts"],
        "tips": [
            "Giữ đủ từng âm: a-sk-s, te-xt-s, gi-ft-s.",
            "Đọc chậm trước, sau đó nhanh dần nhưng không bỏ âm.",
        ],
        "pairs": [["asks", "ask"], ["texts", "text"], ["gifts", "gift"]],
    },
    {
        "id": "en_vw", "group": "Phụ âm",
        "title": "Anh — /v/ và /w/ (visit, winter)",
        "focus": ["V", "W"],
        "target": "Every winter we visit a village.",
        "words": ["every", "winter", "visit", "village"],
        "tips": [
            "/v/: RĂNG TRÊN chạm nhẹ MÔI DƯỚI, có rung.",
            "/w/: chỉ tròn môi rồi mở, KHÔNG chạm răng.",
        ],
        "pairs": [["very", "wery"], ["visit", "wisit"], ["village", "willage"]],
    },
    {
        "id": "en_rl", "group": "Phụ âm",
        "title": "Anh — /r/ và /l/ (red, lorry)",
        "focus": ["R", "L"],
        "target": "Red lorry, yellow lorry.",
        "words": ["red", "lorry", "yellow"],
        "tips": [
            "/r/: cong đầu lưỡi lên nhưng KHÔNG chạm vòm.",
            "/l/: đầu lưỡi CHẠM lợi trên rồi bật ra.",
        ],
        "pairs": [["red", "led"], ["light", "right"], ["lorry", "lolly"]],
    },
    {
        "id": "en_ae", "group": "Nguyên âm",
        "title": "Anh — /æ/ (cat, bad)",
        "focus": ["AE"],
        "target": "That cat sat on a bad mat.",
        "words": ["that", "cat", "sat", "bad", "mat"],
        "tips": [
            "/æ/: MỞ MIỆNG RỘNG, hạ hàm, kéo môi sang hai bên (như đang cười).",
            "Đừng đọc thành /e/ (bed) — miệng phải rộng hơn.",
        ],
        "pairs": [["bad", "bed"], ["sat", "set"], ["man", "men"]],
    },
    {
        "id": "en_ih", "group": "Nguyên âm",
        "title": "Anh — /ɪ/ và /iː/ (ship, sheep)",
        "focus": ["IH", "IY"],
        "target": "This ship is cheap.",
        "words": ["this", "ship", "is", "cheap"],
        "tips": [
            "/ɪ/: NGẮN, lơi, môi không căng.",
            "/iː/: DÀI, môi kéo rộng, lưỡi cao hơn.",
        ],
        "pairs": [["ship", "sheep"], ["sit", "seat"], ["it", "eat"]],
    },
    {
        "id": "en_uh", "group": "Nguyên âm",
        "title": "Anh — /ʊ/ và /uː/ (book, moon)",
        "focus": ["UH", "UW"],
        "target": "A good book and a cool moon.",
        "words": ["good", "book", "cool", "moon"],
        "tips": [
            "/ʊ/: ngắn, môi hơi tròn và lơi.",
            "/uː/: dài, môi tròn rõ và đẩy ra trước.",
        ],
        "pairs": [["full", "fool"], ["pull", "pool"], ["good", "gooed"]],
    },
    {
        "id": "en_ng", "group": "Âm cuối",
        "title": "Anh — /ŋ/ và /n/ cuối (sing, sin)",
        "focus": ["NG", "N"],
        "target": "The king is singing.",
        "words": ["king", "singing"],
        "tips": [
            "/ŋ/: GỐC lưỡi chạm vòm mềm (phía sau), hơi qua mũi.",
            "/n/: ĐẦU lưỡi chạm lợi trên.",
        ],
        "pairs": [["sing", "sin"], ["thing", "thin"], ["king", "kin"]],
    },
    {
        "id": "en_ch", "group": "Phụ âm",
        "title": "Anh — /tʃ/ /dʒ/ /ʃ/ (chair, John)",
        "focus": ["CH", "JH", "SH"],
        "target": "John chose a cheap chair.",
        "words": ["john", "chose", "cheap", "chair"],
        "tips": [
            "/tʃ/ (cheap, chair): bật + xát, môi hơi chu.",
            "/dʒ/ (John): như /tʃ/ nhưng có rung.",
            "/ʃ/ (share): chỉ xát, không bật.",
        ],
        "pairs": [["cheap", "jeep"], ["chair", "share"], ["chose", "shows"]],
    },
    {
        "id": "en_schwa", "group": "Nâng cao",
        "title": "Anh — Âm lướt /ə/ (banana, potato)",
        "focus": ["AH", "ER"],
        "target": "A banana and a potato for breakfast.",
        "words": ["banana", "potato", "breakfast"],
        "tips": [
            "Âm tiết KHÔNG nhấn đọc rất nhẹ, gần như /ə/: b'NAna, p'TATo.",
            "Đừng đọc rõ đủ mọi âm tiết — nghe sẽ rất 'máy móc'.",
        ],
        "pairs": [],
    },
]


# ------------------------------------------------------------------ IPA
def sentence_ipa(text):
    parts = []
    for w in text.split():
        clean = w.strip(".,:;!?\"'")
        s = pron_en.word_ipa(clean)
        parts.append(s or clean.lower())
    return " ".join(parts)


def focus_text(codes):
    return " ".join("/%s/" % pron_en.ARPABET_IPA.get(c, c.lower()) for c in codes)


# ------------------------------------------------------------------ TTS
async def tts(text, mp3_path, rate="+0%"):
    import edge_tts
    last = None
    for i in range(4):
        try:
            await edge_tts.Communicate(text, VOICE, rate=rate, volume="+0%").save(mp3_path)
            return
        except Exception as e:  # mạng chập chờn
            last = e
            await asyncio.sleep(2 * (i + 1))
    raise last


def make_wav(text, name, rate, force):
    from gen_mau import mp3_to_wav16k
    wav = os.path.join(OUT_DIR, name + ".wav")
    if os.path.exists(wav) and not force:
        return False
    mp3 = os.path.join(OUT_DIR, "_tmp.mp3")
    asyncio.run(tts(text, mp3, rate))
    try:
        mp3_to_wav16k(mp3, wav)
    finally:
        if os.path.exists(mp3):
            os.remove(mp3)
    return True


def main():
    force = "--force" in sys.argv
    os.makedirs(OUT_DIR, exist_ok=True)

    out = {"version": 1, "lessons": []}
    words = {}
    for L in LESSONS:
        L = dict(L)
        L["ipa"] = sentence_ipa(L["target"])
        L["focus_ipa"] = focus_text(L["focus"])
        L["samples"] = {"normal": "%s.wav" % L["id"], "slow": "%s_slow.wav" % L["id"]}
        out["lessons"].append(L)
        for w in L["words"]:
            words[w] = True

    with io.open(JSON_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("ghi:", JSON_PATH, len(out["lessons"]), "bài")

    n_new = 0
    for L in LESSONS:
        print("TTS câu:", L["id"], "—", L["target"])
        n_new += make_wav(L["target"], L["id"], "+0%", force)
        n_new += make_wav(L["target"], L["id"] + "_slow", "-30%", force)
    for w in sorted(words):
        print("TTS từ:", w)
        n_new += make_wav(w + ".", "w_" + w, "+0%", force)

    print("xong. file mới:", n_new)
    print("tổng file trong mau/en:", len(os.listdir(OUT_DIR)))


if __name__ == "__main__":
    main()
