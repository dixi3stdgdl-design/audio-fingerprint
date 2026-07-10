from __future__ import annotations

import os
from typing import Any

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter
from pydub import AudioSegment


class UnsupportedFormatError(Exception):
    """Raised when the audio file format is not supported."""


class CorruptedAudioError(Exception):
    """Raised when the audio file is corrupted or unreadable."""


class EmptyAudioError(Exception):
    """Raised when the audio file contains no audio data."""


SUPPORTED_FORMATS = frozenset({'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma'})


class AudioProcessor:
    def __init__(
        self,
        sample_rate: int = 22050,
        fft_size: int = 2048,
        hop_size: int = 512,
    ) -> None:
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.hop_size = hop_size

    def _validate_file(self, file_path: str) -> None:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_FORMATS:
            raise UnsupportedFormatError(
                f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )

    def load_audio(self, file_path: str) -> np.ndarray:
        self._validate_file(file_path)

        try:
            audio = AudioSegment.from_file(file_path)
        except Exception as exc:
            raise CorruptedAudioError(
                f"Failed to read audio file: {file_path}"
            ) from exc

        audio = audio.set_frame_rate(self.sample_rate).set_channels(1)
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)

        if samples.size == 0:
            raise EmptyAudioError(f"Audio file is empty or has no samples: {file_path}")

        max_val = np.max(np.abs(samples))
        if max_val == 0:
            raise EmptyAudioError(f"Audio file contains only silence: {file_path}")

        samples = samples / max_val
        return samples

    def compute_spectrogram(self, audio: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        f, t, Sxx = signal.spectrogram(
            audio,
            fs=self.sample_rate,
            nperseg=self.fft_size,
            noverlap=self.fft_size - self.hop_size,
            window='hann',
        )
        Sxx_db = 10 * np.log10(Sxx + 1e-10)
        return f, t, Sxx_db

    def detect_peaks(
        self,
        Sxx_db: np.ndarray,
        threshold_percentile: float = 95,
        neighborhood_size: int = 3,
    ) -> list[tuple[int, int, float]]:
        local_max = maximum_filter(Sxx_db, size=neighborhood_size)
        peaks_mask = (Sxx_db == local_max)

        threshold = np.percentile(Sxx_db, threshold_percentile)
        peaks_mask &= (Sxx_db >= threshold)

        freq_indices, time_indices = np.where(peaks_mask)

        peaks: list[tuple[int, int, float]] = []
        for fi, ti in zip(freq_indices, time_indices):
            peaks.append((fi, ti, Sxx_db[fi, ti]))

        return peaks

    def peaks_to_freq_time(
        self,
        peaks: list[tuple[int, int, float]],
        freqs: np.ndarray,
        times: np.ndarray,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for freq_idx, time_idx, amplitude in peaks:
            result.append({
                'frequency': freqs[freq_idx],
                'time': times[time_idx],
                'amplitude': amplitude,
                'freq_idx': freq_idx,
                'time_idx': time_idx,
            })
        return result

    def process_file(self, file_path: str) -> dict[str, Any]:
        audio = self.load_audio(file_path)
        freqs, times, Sxx_db = self.compute_spectrogram(audio)
        raw_peaks = self.detect_peaks(Sxx_db)
        peaks = self.peaks_to_freq_time(raw_peaks, freqs, times)
        return {
            'file_path': file_path,
            'audio': audio,
            'frequencies': freqs,
            'times': times,
            'spectrogram': Sxx_db,
            'peaks': peaks,
        }
