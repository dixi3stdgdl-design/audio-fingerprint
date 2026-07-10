from __future__ import annotations

from typing import Any


class FingerprintGenerator:
    def __init__(
        self,
        min_time_delta: float = 0.1,
        max_time_delta: float = 2.0,
        freq_tolerance: int = 100,
    ) -> None:
        self.min_time_delta = min_time_delta
        self.max_time_delta = max_time_delta
        self.freq_tolerance = freq_tolerance

    def generate_hashes(self, peaks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        hashes: list[dict[str, Any]] = []
        peaks_sorted = sorted(peaks, key=lambda x: x['time'])

        for i, peak1 in enumerate(peaks_sorted):
            target_zone = self._get_target_zone(peak1, peaks_sorted, i)

            for peak2 in target_zone:
                hash_val = self._create_hash(peak1, peak2)
                hashes.append({
                    'hash': hash_val,
                    'freq1': peak1['frequency'],
                    'freq2': peak2['frequency'],
                    'time1': peak1['time'],
                    'time2': peak2['time'],
                    'time_delta': peak2['time'] - peak1['time'],
                })

        return hashes

    def _get_target_zone(
        self,
        peak1: dict[str, Any],
        peaks_sorted: list[dict[str, Any]],
        peak1_idx: int,
    ) -> list[dict[str, Any]]:
        target_peaks: list[dict[str, Any]] = []
        time1 = peak1['time']
        freq1 = peak1['frequency']

        for i in range(peak1_idx + 1, len(peaks_sorted)):
            peak2 = peaks_sorted[i]
            time_delta = peak2['time'] - time1

            if time_delta > self.max_time_delta:
                break

            if time_delta < self.min_time_delta:
                continue

            if abs(peak2['frequency'] - freq1) <= self.freq_tolerance:
                continue

            target_peaks.append(peak2)

        return target_peaks

    def _create_hash(self, peak1: dict[str, Any], peak2: dict[str, Any]) -> int:
        freq1 = int(peak1['frequency'])
        freq2 = int(peak2['frequency'])
        time_delta = int((peak2['time'] - peak1['time']) * 1000)

        freq1 = max(0, min(freq1, 4095))
        freq2 = max(0, min(freq2, 4095))
        time_delta = max(0, min(time_delta, 4095))

        hash_val = (freq1 << 24) | (freq2 << 12) | time_delta
        return hash_val

    def process_audio_data(self, audio_data: dict[str, Any]) -> dict[str, Any]:
        peaks = audio_data['peaks']
        hashes = self.generate_hashes(peaks)
        return {
            'file_path': audio_data['file_path'],
            'hashes': hashes,
            'peak_count': len(peaks),
        }
