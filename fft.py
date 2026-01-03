import pyaudio
import numpy as np
import time

# --- Ayarlar ---
RATE = 44100          # Örnekleme hızı (Hz)
CHUNK = 4096          # Her FFT için örnek sayısı
CHANNELS = 1          # Mono ses
REFRESH = 0.2         # Kaç saniyede bir terminale yazılsın

# --- PyAudio başlat ---
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("Canlı dinleniyor... (Ctrl+C ile durdurabilirsin)")

# --- Ana döngü ---
try:
    while True:
        # Mikrofondan ses oku (overflow hatalarını yut)
        data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)

        # FFT hesapla
        fft_data = np.fft.rfft(data)
        magnitudes = np.abs(fft_data)
        freqs = np.fft.rfftfreq(CHUNK, d=1.0/RATE)

        # En güçlü frekansı bul
        peak_index = np.argmax(magnitudes)
        peak_freq = freqs[peak_index]

        # Terminale bas
        print(f"🔊 En baskın frekans: {peak_freq:7.1f} Hz")

        # Biraz bekle ki CPU yanmasın :)
        time.sleep(REFRESH)

except KeyboardInterrupt:
    print("\nDurduruldu.")

# --- Temizlik ---
stream.stop_stream()
stream.close()
p.terminate()
