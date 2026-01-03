import sounddevice as sd
import numpy as np
import librosa
import math
import queue
import time
from collections import deque
# ... existing code ...
TURKISH_SOLFEGE = ['do', 'do#', 're', 're#', 'mi', 'fa', 'fa#', 'sol', 'sol#', 'la', 'la#', 'si']
TSM_MAP = {
    'G': 'Rast',
    'G#': 'Rast♯',
    'A': 'Dügâh',
    'A#': 'Dügâh♯',
    'B': 'Segâh',
    'C': 'Çargâh',
    'C#': 'Nim Hicaz',
    'D': 'Neva',
    'D#': 'Hicaz',
    'E': 'Hüseynî',
    'F': 'Eviç',
    'F#': 'Acem'
}
def freq_to_midi(freq):
    return 69 + 12 * math.log2(freq / 440.0)

def midi_to_names(midi):
    note_index = int(round(midi)) % 12
    octave = (int(round(midi)) // 12) - 1
    note_en = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][note_index]
    solfej = TURKISH_SOLFEGE[note_index]
    tsm = TSM_MAP.get(note_en, note_en)
    return note_en + str(octave), solfej + str(octave), tsm + f" (oktav {octave})"

samplerate = 22050
block_duration = 0.3  # saniye (daha uzun blok, daha kararlı tespit)
blocksize = int(samplerate * block_duration)
buffer_seconds = 0.6  # analiz için birleştirilecek toplam süre
rms_gate = 0.01       # sessizlik/gürültü eşiği (-1..1 arası ölçek)
recent_blocks = deque(maxlen=int(buffer_seconds / block_duration))
q = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print(status)
    q.put(indata.copy())

def analyze_block(y):
    # RMS sessizlik kapısı
    rms = float(np.sqrt(np.mean(y ** 2))) if y.size else 0.0
    if rms < rms_gate:
        return None

    try:
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=65, fmax=1000, sr=samplerate,
            frame_length=4096, hop_length=256,
            center=False
        )
    except Exception:
        return None

    if f0 is None or np.all(np.isnan(f0)):
        return None

    # Sadece sesli (voiced) kareleri kullan
    f0 = np.where(voiced_flag, f0, np.nan)
    if np.all(np.isnan(f0)):
        return None

    # Ortanca ile gürbüzleştir
    freq = float(np.nanmedian(f0))
    if not np.isfinite(freq):
        return None

    midi = freq_to_midi(freq)
    note_en, solfej, tsm = midi_to_names(midi)
    cents = (midi - round(midi)) * 100
    return freq, midi, note_en, solfej, tsm, cents

print("🎶 Canlı TSM nota tespiti başlıyor... (Ctrl+C ile çıkış)")
with sd.InputStream(channels=1, samplerate=samplerate, blocksize=blocksize, callback=callback):
    while True:
        block = q.get()
        recent_blocks.append(block.flatten())
        # Yeterli tampon biriktiğinde analiz et
        if len(recent_blocks) == recent_blocks.maxlen:
            y = np.concatenate(list(recent_blocks))
            result = analyze_block(y)
            if result:
                freq, midi, note_en, solfej, tsm, cents = result
                print(f"{freq:7.1f} Hz → {note_en:<4} | {solfej:<6} | {tsm:<15} | {cents:+.1f} cents")
        time.sleep(block_duration / 2)