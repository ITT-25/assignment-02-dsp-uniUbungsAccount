import numpy as np
from scipy.fft import rfft, rfftfreq
from scipy.signal import butter, sosfilt, get_window, savgol_filter
from mido import MidiFile

def band_pass_filter(signal_data, low_cut_frequency, high_cut_frequency, sample_rate):
    sos = butter(4, [low_cut_frequency, high_cut_frequency], btype="band",
                 fs=sample_rate, output="sos")
    return sosfilt(sos, signal_data)


def apply_window_function(signal_data, window_type="hamming"):
    return signal_data * get_window(window_type, len(signal_data), fftbins=True)


def smooth_signal_with_sg(signal_data, window_size=64):
    window_size = max(5, window_size | 1)
    return savgol_filter(signal_data, window_size, polyorder=2)


def detect_frequency_from_fft(signal_data, sample_rate):
    if signal_data.size == 0:
        return 0.0
    magnitudes = np.abs(rfft(signal_data))
    idx_of_peak = np.argmax(magnitudes)
    freqs = rfftfreq(len(signal_data), 1 / sample_rate)
    return freqs[idx_of_peak]


def frequency_to_midi_number(freq_hz):
    return -1 if freq_hz <= 0 else int(round(12 * np.log2(freq_hz / 440.0) + 69))


def midi_number_to_frequency(midi_note):
    return 440.0 * 2 ** ((midi_note - 69) / 12)

def read_midi(midi_path, track_index=0):
    midi_file = MidiFile(midi_path)
    ticks_per_beat = midi_file.ticks_per_beat
    tempo = 1000_000
    current_time_sec = 0.0
    notes_on = {}
    notes_out = []

    for msg in midi_file.tracks[track_index]:
        current_time_sec += (msg.time * tempo) / 1_000_000 / ticks_per_beat

        if msg.type == "note_on" and msg.velocity > 0:
            notes_on[msg.note] = current_time_sec
        elif msg.type in ("note_off", "note_on") and msg.note in notes_on:
            start_time = notes_on.pop(msg.note)
            notes_out.append((start_time, current_time_sec - start_time, msg.note))

    return sorted(notes_out, key=lambda tup: tup[0])
