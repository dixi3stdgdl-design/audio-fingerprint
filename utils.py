from __future__ import annotations

import os
from typing import Any, Optional

import numpy as np
import matplotlib.pyplot as plt


def plot_spectrogram(audio_data: dict[str, Any], save_path: Optional[str] = None) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    times = audio_data['times']
    frequencies = audio_data['frequencies']
    spectrogram = audio_data['spectrogram']

    axes[0].pcolormesh(times, frequencies, spectrogram, shading='gouraud')
    axes[0].set_ylabel('Frequency (Hz)')
    axes[0].set_title('Spectrogram')

    peaks = audio_data['peaks']
    if peaks:
        peak_freqs = [p['frequency'] for p in peaks]
        peak_times = [p['time'] for p in peaks]
        axes[0].scatter(peak_times, peak_freqs, c='red', s=5, alpha=0.5)

    axes[1].plot(audio_data['audio'])
    axes[1].set_xlabel('Sample')
    axes[1].set_ylabel('Amplitude')
    axes[1].set_title('Waveform')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
    else:
        plt.show()

    plt.close()


def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def print_match_results(results: list[dict[str, Any]]) -> None:
    if not results:
        print("No matches found.")
        return

    print("\n" + "=" * 60)
    print("MATCH RESULTS")
    print("=" * 60)

    for i, result in enumerate(results[:5], 1):
        print(f"\n#{i}: {result['song_name']}")
        print(f"    Confidence: {result['confidence']:.1%}")
        print(f"    Score: {result['score']} matches")
        print(f"    Time offset: {format_time(result['offset'])}")

    print("\n" + "=" * 60)


def print_index_stats(stats: dict[str, int]) -> None:
    print("\nIndex Statistics:")
    print(f"  Total songs: {stats['total_songs']}")
    print(f"  Total unique hashes: {stats['total_hashes']}")
    print(f"  Total hash entries: {stats['total_entries']}")
