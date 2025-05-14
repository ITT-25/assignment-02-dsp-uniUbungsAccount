import numpy as np
from scipy.signal import butter, sosfilt, savgol_filter, get_window
from scipy.fft import rfft, rfftfreq

SAMPLING_RATE = 4096

def bandpass_filter(signal: np.ndarray, low_cut: float, high_cut: float, fs: int = SAMPLING_RATE) -> np.ndarray:
    sos = butter(4, [low_cut, high_cut], btype="band", fs=fs, output="sos")
    return sosfilt(sos, signal)


def apply_window(signal: np.ndarray) -> np.ndarray:
    window = get_window("hamming", len(signal))
    return signal * window


def smooth_signal(signal: np.ndarray, window_length: int = 57, poly_degree: int = 2) -> np.ndarray:
    return savgol_filter(signal, window_length, poly_degree)



def get_peak_frequency(signal: np.ndarray, fs: int = SAMPLING_RATE) -> float:
    spectrum = np.abs(rfft(signal))
    freqs = rfftfreq(len(signal), d=1 / fs)
    return freqs[np.argmax(spectrum)]