import time
import pyaudio
import numpy as np
import pyglet
from pyglet import shapes
from pynput.keyboard import Controller, Key
from audio_utils import bandpass_filter, smooth_signal, apply_window, get_peak_frequency, SAMPLING_RATE

BUFFER_SIZE = 1024
NOISE_THRESHOLD = 180
FREQ_DIFF_THRESHOLD = 70
NUM_RECTANGLES = 8
RECT_WIDTH = 320
RECT_HEIGHT = 70
RECT_GAP = 12

def get_microphone_frequency(stream):
    data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
    samples = np.frombuffer(data, dtype=np.int16)
    if np.abs(samples).mean() < NOISE_THRESHOLD:
        return None
    filtered = bandpass_filter(samples, 80, 2000)
    smoothed = smooth_signal(filtered)
    windowed = apply_window(smoothed)
    return get_peak_frequency(windowed)

class WhistleVisualizer(pyglet.window.Window):
    def __init__(self):
        super().__init__(width=1200, height=800, caption="Whistle To Control arrow-keys up/down")
        audio = pyaudio.PyAudio()
        self.stream = audio.open(format=pyaudio.paInt16,
                                 channels=1,
                                 rate=SAMPLING_RATE,
                                 input=True,
                                 frames_per_buffer=BUFFER_SIZE)
        self.current_frequency = None
        self.previous_frequency = None
        self.cursor_index = NUM_RECTANGLES // 2
        self.last_shift_time = 0.0
        self.keyboard = Controller()
        start_y = (self.height - (NUM_RECTANGLES * (RECT_HEIGHT + RECT_GAP))) / 2
        self.rectangles = []
        for i in range(NUM_RECTANGLES):
            x = (self.width - RECT_WIDTH) / 2
            y = start_y + i * (RECT_HEIGHT + RECT_GAP)
            rect = shapes.Rectangle(x, y, RECT_WIDTH, RECT_HEIGHT)
            self.rectangles.append(rect)
        self.label = pyglet.text.Label("Frequency: -", x=15, y=self.height - 35, font_size=14)

    def on_draw(self):
        self.clear()
        for idx, rect in enumerate(self.rectangles):
            rect.color = (60, 90, 180) if idx == self.cursor_index else (80, 80, 80)
            rect.draw()
        freq_text = f"{self.current_frequency:.1f} Hz" if self.current_frequency else "-"
        self.label.text = f"Frequency: {freq_text}"
        self.label.draw()

    def update(self, dt):
        freq = get_microphone_frequency(self.stream)
        self.current_frequency = freq
        if self.previous_frequency is not None and freq is not None:
            diff = self.previous_frequency - freq
            now = time.time()
            if abs(diff) > FREQ_DIFF_THRESHOLD and now - self.last_shift_time >= 0.5:
                step = -1 if diff > 0 else 1
                self.cursor_index = (self.cursor_index + step) % NUM_RECTANGLES
                key = Key.down if step == -1 else Key.up
                self.keyboard.press(key)
                self.keyboard.release(key)
                self.last_shift_time = now
                self.previous_frequency = None
            else:
                self.previous_frequency = freq
        else:
            self.previous_frequency = freq

if __name__ == "__main__":
    window = WhistleVisualizer()
    pyglet.clock.schedule_interval(window.update, 1 / 30)
    pyglet.app.run()
