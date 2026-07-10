# API Reference

Detailed documentation for all public classes, methods, and functions.

---

## audio_processor

### Exceptions

#### `UnsupportedFormatError`

Raised when the audio file extension is not in the supported set (`.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aac`, `.wma`).

#### `CorruptedAudioError`

Raised when the audio file exists and has a valid extension but cannot be decoded (e.g., truncated file, invalid header).

#### `EmptyAudioError`

Raised when the audio file decodes successfully but contains no samples or only silence.

### Class: `AudioProcessor`

Processes audio files into spectrograms and detects spectral peaks.

```python
from audio_processor import AudioProcessor

processor = AudioProcessor(sample_rate=22050, fft_size=2048, hop_size=512)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sample_rate` | `int` | `22050` | Target sample rate for loaded audio |
| `fft_size` | `int` | `2048` | FFT window size for spectrogram |
| `hop_size` | `int` | `512` | Hop size between FFT frames |

#### `load_audio(file_path: str) -> np.ndarray`

Load an audio file, convert to mono at the configured sample rate, and normalize to [-1, 1].

**Raises:** `FileNotFoundError`, `UnsupportedFormatError`, `CorruptedAudioError`, `EmptyAudioError`

**Returns:** 1-D numpy array of normalized float32 samples.

#### `compute_spectrogram(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]`

Compute an STFT spectrogram from raw audio samples.

**Returns:** `(frequencies, times, Sxx_db)` — frequency bins, time bins, and power spectrogram in dB.

#### `detect_peaks(Sxx_db, threshold_percentile=95, neighborhood_size=3) -> list[tuple[int, int, float]]`

Find local maxima in the spectrogram above a percentile threshold.

**Returns:** List of `(freq_index, time_index, amplitude)` tuples.

#### `peaks_to_freq_time(peaks, freqs, times) -> list[dict]`

Convert index-based peaks to frequency/time coordinates.

**Returns:** List of dicts with keys: `frequency`, `time`, `amplitude`, `freq_idx`, `time_idx`.

#### `process_file(file_path: str) -> dict[str, Any]`

Full pipeline: load → spectrogram → peaks → coordinate mapping.

**Returns:** Dict with keys: `file_path`, `audio`, `frequencies`, `times`, `spectrogram`, `peaks`.

---

## fingerprint_generator

### Class: `FingerprintGenerator`

Converts spectral peaks into fingerprint hashes using peak-pair constellation.

```python
from fingerprint_generator import FingerprintGenerator

generator = FingerprintGenerator(min_time_delta=0.1, max_time_delta=2.0, freq_tolerance=100)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_time_delta` | `float` | `0.1` | Minimum time (seconds) between paired peaks |
| `max_time_delta` | `float` | `2.0` | Maximum time (seconds) between paired peaks |
| `freq_tolerance` | `int` | `100` | Minimum frequency difference (Hz) between paired peaks |

#### `generate_hashes(peaks: list[dict]) -> list[dict]`

Generate fingerprint hashes from a list of spectral peaks.

**Returns:** List of dicts with keys: `hash`, `freq1`, `freq2`, `time1`, `time2`, `time_delta`.

#### `process_audio_data(audio_data: dict) -> dict`

Convenience wrapper: extract peaks from `audio_data` dict (as returned by `AudioProcessor.process_file`) and generate hashes.

**Returns:** Dict with keys: `file_path`, `hashes`, `peak_count`.

---

## database

### Exceptions

#### `DatabaseCorruptedError`

Raised when the SQLite database file is corrupted and cannot be recovered.

#### `DatabaseLockedError`

Raised when the database is locked by another process and cannot be accessed.

### Class: `FingerprintDatabase`

SQLite-backed storage for fingerprints with connection pooling.

```python
from database import FingerprintDatabase

db = FingerprintDatabase("songs.db")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `str \| None` | `None` | Path to SQLite file. `None` or `":memory:"` for in-memory. |

#### `add_song(song_name: str, fingerprints: dict) -> int`

Insert a song and its fingerprints into the database.

**Returns:** The assigned `song_id`.

#### `lookup_hash(hash_val: int) -> list[dict]`

Find all entries matching a hash value.

**Returns:** List of dicts with keys: `song_id`, `time`.

#### `get_song_info(song_id: int) -> dict | None`

Retrieve song metadata by ID.

**Returns:** Dict with `name` and `hash_count`, or `None` if not found.

#### `get_all_songs() -> dict[int, dict]`

Return all indexed songs.

**Returns:** Dict mapping `song_id` → `{name, hash_count}`.

#### `get_stats() -> dict[str, int]`

Database statistics.

**Returns:** Dict with keys: `total_songs`, `total_hashes`, `total_entries`.

#### `save(path: str | None = None) -> None`

Commit and optionally copy the database to a new path.

#### `load(path: str | None = None) -> None`

Close the current connection and open a different database file.

#### `close() -> None`

Close the database connection and remove it from the connection pool.

### Class: `InMemoryFingerprintDatabase`

In-memory fallback using `defaultdict`. Same interface as `FingerprintDatabase`.

---

## matcher

### Class: `FingerprintMatcher`

Matches query fingerprints against a database and ranks results.

```python
from matcher import FingerprintMatcher

matcher = FingerprintMatcher(max_offset_tolerance=5.0, min_matches=5)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_offset_tolerance` | `float` | `5.0` | Max allowed time offset (seconds) between consistent matches |
| `min_matches` | `int` | `5` | Minimum hash matches to consider a candidate |

#### `match(query_fingerprints: dict, database) -> list[dict]`

Find all matching songs ranked by score.

**Returns:** List of dicts (descending by `score`) with keys: `song_id`, `song_name`, `score`, `confidence`, `offset`, `total_matches`, `consistent_matches`.

#### `get_best_match(query_fingerprints: dict, database) -> dict | None`

Return only the top-scoring match, or `None`.

---

## utils

### Functions

#### `plot_spectrogram(audio_data: dict, save_path: str | None = None) -> None`

Plot a two-panel figure (spectrogram with peaks overlay + waveform). If `save_path` is given, save to file instead of showing.

#### `format_time(seconds: float) -> str`

Format seconds as `MM:SS`.

#### `print_match_results(results: list[dict]) -> None`

Pretty-print up to 5 match results to stdout.

#### `print_index_stats(stats: dict[str, int]) -> None`

Pretty-print database statistics to stdout.
