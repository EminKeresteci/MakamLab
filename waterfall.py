import pyaudio
import numpy as np
import matplotlib.pyplot as plt
import time

# --- Ayarlar ---
RATE = 44100              # Örnekleme hızı (Hz)
CHUNK = 2048              # FFT yapılacak örnek sayısı (frame)
CHANNELS = 1              # Mono ses
MAX_FRAMES = 100          # Grafikte tutulacak satır sayısı (ne kadar “aşağı” aksın)
SLEEP = 0.05              # Grafiğin yenileme aralığı (sn)

# --- PyAudio başlat ---
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,    # 16-bit PCM
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

# --- FFT frekans ekseni (sadece pozitif frekanslar) ---
freqs = np.fft.rfftfreq(CHUNK, d=1.0/RATE)

# --- Waterfall matrisini başlat ---
waterfall = np.zeros((MAX_FRAMES, len(freqs)))

# --- Matplotlib ayarları ---
plt.ion()  # etkileşimli mod
fig, ax = plt.subplots(figsize=(10, 6))
img = ax.imshow(waterfall, aspect='auto', origin='upper',
                extent=[freqs[0], freqs[-1], 0, MAX_FRAMES],
                cmap='inferno')

ax.set_xlabel("Frekans (Hz)")
ax.set_ylabel("Zaman (yeni -> aşağı)")
ax.set_title("Canlı FFT Waterfall (Türk Sanat Müziği Tını Analizi)")
plt.tight_layout()

# --- Ana döngü ---
print("Canlı dinleniyor... (Ctrl+C ile durdurabilirsin)")
try:
    while True:
        # Mikrofondan ses oku
        data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)

        # FFT al ve genlik hesabı
        fft_data = np.abs(np.fft.rfft(data))
        fft_data = 20 * np.log10(fft_data + 1e-6)  # dB ölçeği

        # Waterfall güncelle: en üste yeni veriyi ekle
        waterfall = np.vstack((fft_data, waterfall[:-1, :]))

        # Görselleştir
        img.set_data(waterfall)
        plt.pause(SLEEP)

except KeyboardInterrupt:
    print("\nDurduruldu.")

# --- Temizlik ---
stream.stop_stream()
stream.close()
p.terminate()
