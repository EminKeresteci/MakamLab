import pyaudio
import numpy as np
import math
import time

# --- Ayarlar ---
RATE = 44100          # Örnekleme hızı (Hz)
CHUNK = 2048          # FFT örnek sayısı
CHANNELS = 1          # Mono ses
REFRESH = 0.2         # Terminal güncelleme aralığı (saniye)
A4_REF = 440.0        # A4 referans frekansı

# --- TSM nota tablosu (basit) ---
TSM_MAP = {
    'G': 'Rast',
    'A': 'Dügâh',
    'B': 'Segâh',
    'C': 'Çargâh',
    'D': 'Neva',
    'E': 'Hüseynî',
    'F': 'Eviç'
}

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

# --- Yardımcı fonksiyonlar ---
def freq_to_midi(freq, a4=A4_REF):
    """Frekansı float MIDI numarasına çevirir. freq <= 0 ise None döner."""
    if freq <= 0:
        return None
    return 69 + 12 * math.log2(freq / a4)


def midi_to_note_name(midi):
    """MIDI numarasını nota adı ile döndürür (C, C#, D...)"""
    m = int(round(midi))
    return NOTE_NAMES[m % 12]

def midi_to_tsm(midi):
    """MIDI numarasını en yakın TSM notasına çevirir."""
    note = midi_to_note_name(midi)
    # basit map: yalnızca doğal notalar
    tsm = TSM_MAP.get(note, note)
    return tsm

# --- PyAudio başlat ---
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("Canlı TSM nota tespiti başlıyor... (Ctrl+C ile durdur)")

# --- Ana döngü ---
try:
    while True:
        # Ses bloğunu al (overflow engellemek için exception_on_overflow=False)
        data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)

        # FFT hesapla
        fft_data = np.fft.rfft(data)
        magnitudes = np.abs(fft_data)
        freqs = np.fft.rfftfreq(CHUNK, d=1.0/RATE)

        # En güçlü frekansı bul
        peak_index = np.argmax(magnitudes)
        peak_freq = freqs[peak_index]

        # En yakın MIDI ve TSM notası
        midi = freq_to_midi(peak_freq)
        if midi is None:
            tsm_note = "---"
        else:
            tsm_note = midi_to_tsm(midi)

        print(f"🔊 {peak_freq:7.1f} Hz -> TSM Nota: {tsm_note}")



        time.sleep(REFRESH)

except KeyboardInterrupt:
    print("\nDurduruldu.")

# --- Temizlik ---
stream.stop_stream()
stream.close()
p.terminate()
