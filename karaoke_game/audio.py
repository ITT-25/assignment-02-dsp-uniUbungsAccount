import threading
from collections import deque

import numpy as np
import pyaudio

from utils import (
    band_pass_filter,
    apply_window_function,
    smooth_signal_with_sg,
    detect_frequency_from_fft, #guter watch über FFT von Veritasium btw: https://www.youtube.com/watch?v=nmgFG7PUHfo
    frequency_to_midi_number,
)

class MicPitch:
    def __init__(
        self,
        sample_rate=2048,
        buffer_size=128,
        history_size=1,
        low_cut_frequency=80.0,
        high_cut_frequency=1000.0,
        amplitude_threshold=60,
        smoothing_alpha=1,
        octave_offset=1,
        device_index=None,
    ):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.low_cut_frequency = low_cut_frequency
        self.high_cut_frequency = high_cut_frequency
        self.amplitude_threshold = amplitude_threshold
        self.smoothing_alpha = smoothing_alpha
        self.octave_offset = octave_offset

        self.note = -1
        self._frequency_history = deque(maxlen=history_size)
        self._smoothed_midi_estimate = None
        self._run = True

        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=buffer_size,
            input_device_index=device_index,
        )

        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        while self._run:
            raw_bytes = self._stream.read(self.buffer_size, exception_on_overflow=False)
            samples = np.frombuffer(raw_bytes, np.int16)

            if np.mean(np.abs(samples)) < self.amplitude_threshold:
                self.note = -1
                continue

            samples = band_pass_filter(samples, self.low_cut_frequency, self.high_cut_frequency, self.sample_rate)
            samples = smooth_signal_with_sg(samples)
            samples = apply_window_function(samples)

            freq_hz = detect_frequency_from_fft(samples, self.sample_rate)
            if freq_hz <= 0:
                self.note = -1
                continue

            self._frequency_history.append(freq_hz)
            median_freq = float(np.median(self._frequency_history))

            midi_val = frequency_to_midi_number(median_freq) + 12 * self.octave_offset

            if self._smoothed_midi_estimate is None:
                self._smoothed_midi_estimate = midi_val
            else:
                self._smoothed_midi_estimate = (
                    (1 - self.smoothing_alpha) * self._smoothed_midi_estimate
                    + self.smoothing_alpha * midi_val
                )

            self.note = int(round(self._smoothed_midi_estimate))

    def close(self):
        self._run = False
        self._stream.stop_stream()
        self._stream.close()
        self._pa.terminate()
