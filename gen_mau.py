# Tạo thư viện âm mẫu giọng bản ngữ trong thư mục mau/ (chạy 1 lần).
# Cần mạng + edge-tts (chỉ dùng lúc TẠO, app chạy offline hoàn toàn):
#   C:\Users\ADMIN\miniforge3\python.exe -m pip install edge-tts
#   C:\Users\ADMIN\miniforge3\python.exe gen_mau.py [--force]
import asyncio
import os
import sys
import wave

BASE = os.path.dirname(os.path.abspath(__file__))
MAU = os.path.join(BASE, "mau")
os.makedirs(MAU, exist_ok=True)

VI = "vi-VN-HoaiMyNeural"
EN = "en-US-AriaNeural"

# rate 0% = giọng tự nhiên nhất; -10% cũ làm méo, rè, giống robot.
# Thêm dấu chấm để TTS ngắt nhịp tự nhiên, sau đó cắt im lặng thừa.
CLIPS = [
    ("na.", VI, "vi_na.wav"),
    ("la.", VI, "vi_la.wav"),
    ("năm.", VI, "vi_nam.wav"),
    ("lăm.", VI, "vi_lam.wav"),
    ("nên.", VI, "vi_nen.wav"),
    ("lên.", VI, "vi_len.wav"),
    ("Lan năm nay lên lớp.", VI, "vi_cau.wav"),
    ("think.", EN, "en_think.wav"),
    ("this.", EN, "en_this.wav"),
    ("she.", EN, "en_she.wav"),
    ("sea.", EN, "en_sea.wav"),
    ("She sells seashells.", EN, "en_cau.wav"),
]


async def gen_one(text, voice, mp3, tries=4):
    import edge_tts
    import asyncio as _aio
    last = None
    for i in range(tries):
        try:
            # rate tự nhiên, volume chuẩn; pitch giữ nguyên để không "chipmunk"
            await edge_tts.Communicate(text, voice, rate="+0%", volume="+0%").save(mp3)
            return
        except Exception as e:
            last = e
            await _aio.sleep(2 * (i + 1))
    raise last


def mp3_to_wav16k(mp3, wav):
    """mp3 -> wav 16k mono + làm sạch: bỏ DC, cắt im lặng, chuẩn hóa -3dB, fade."""
    import av
    import numpy as np
    from av.audio.resampler import AudioResampler
    src = av.open(mp3)
    astream = next(s for s in src.streams if s.type == "audio")
    res = AudioResampler(format="s16", layout="mono", rate=16000)
    chunks = []
    for frame in src.decode(astream):
        for f in res.resample(frame):
            arr = np.frombuffer(bytes(f.planes[0]), dtype=np.int16).copy()
            # Cắt padding thừa nếu frame cuối lẻ (planes có thể dài hơn nb_samples)
            expect = f.samples * (1 if "mono" in str(f.layout.name).lower() else 1)
            if len(arr) > expect:
                arr = arr[:expect]
            chunks.append(arr.astype(np.float32) / 32768.0)
    for f in res.resample(None):  # flush
        if f is not None:
            arr = np.frombuffer(bytes(f.planes[0]), dtype=np.int16).copy()
            expect = f.samples
            if len(arr) > expect:
                arr = arr[:expect]
            chunks.append(arr.astype(np.float32) / 32768.0)
    src.close()
    if not chunks:
        raise RuntimeError(f"không decode được {mp3}")
    import math
    x = np.concatenate(chunks).astype(np.float32)
    x = x - float(np.mean(x))  # bỏ DC
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    # Cắt im lặng đầu/cuối (ngưỡng thấp để giữ hơi đầu từ)
    mag = np.abs(x)
    thr = max(0.008, peak * 0.03)
    idx = np.where(mag > thr)[0]
    if len(idx):
        pad = int(16000 * 0.12)  # giữ 120ms
        s = max(0, int(idx[0]) - pad)
        e = min(len(x), int(idx[-1]) + pad)
        x = x[s:e]
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak > 1e-6:
        x = x * (0.70 / peak)  # chuẩn hóa -3dB: to, đều, không vỡ
    x = np.tanh(x)  # soft-clip chống rè đỉnh
    f = int(16000 * 0.008)
    if len(x) > 2 * f:
        ramp = np.linspace(0.0, 1.0, f, dtype=np.float32)
        x[:f] *= ramp
        x[-f:] *= ramp[::-1]
    out = (np.clip(x, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(out.tobytes())
    return len(out) / 16000


def main():
    force = "--force" in sys.argv
    for text, voice, name in CLIPS:
        mp3 = os.path.join(MAU, name + ".mp3")
        wav = os.path.join(MAU, name)
        if os.path.exists(wav) and not force:
            print("skip:", name)
            continue
        print("gen:", name)
        asyncio.run(gen_one(text, voice, mp3))
        secs = mp3_to_wav16k(mp3, wav)
        try:
            os.remove(mp3)
        except OSError:
            pass
        print(f"  -> {name}: {secs:.2f}s")
    print("DONE:")
    for _, _, name in CLIPS:
        p = os.path.join(MAU, name)
        w = wave.open(p, "rb")
        print(f"  {name}: {w.getnframes() / w.getframerate():.2f}s")


if __name__ == "__main__":
    main()
