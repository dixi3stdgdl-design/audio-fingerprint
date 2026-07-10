# Audio Fingerprint

Python library for generating, storing, and matching audio fingerprints. Identify songs from short audio clips by comparing spectrogram-based fingerprints against an indexed database.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org/)
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen.svg)](#testing)

## Demo

```
$ python fingerprint_app.py index ./music --db songs.db
Indexing: 100%|████████████████████| 247/247 [00:12<00:00]
✓ Indexed 247 songs → songs.db (3.2 MB)

$ python fingerprint_app.py identify clip.wav --db songs.db
Match found: "Daft Punk - Around the World" (confidence: 94.2%)
Match found: "Daft Punk - Da Funk" (confidence: 12.1%)

$ python fingerprint_app.py visualize song.wav
[Displays spectrogram with detected peaks]
```

## Installation

```bash
git clone https://github.com/dixi3stdgdl-design/audio-fingerprint.git
cd audio-fingerprint
pip install -r requirements.txt
```

Requires Python 3.8+. FFmpeg required for mp3/ogg support.

## CLI Usage

### Index a music library

```bash
python fingerprint_app.py index ./music --db songs.db
```

Recursively scans for `.wav`, `.mp3`, `.flac`, `.ogg` files, extracts fingerprints, stores in SQLite.

### Identify an audio clip

```bash
python fingerprint_app.py identify clip.wav --db songs.db
```

Compares query against all indexed songs, reports matches with confidence scores.

### Visualize audio

```bash
python fingerprint_app.py visualize song.wav
```

Displays spectrogram with detected peaks and waveform.

### Database statistics

```bash
python fingerprint_app.py --stats --db songs.db
```

| Flag | Description |
|------|-------------|
| `--version` | Show program version |
| `--db PATH` | SQLite database path (default: `fingerprint_db.sqlite`) |
| `--stats` | Show database statistics |

## Programmatic Usage

```python
from audio_processor import AudioProcessor
from fingerprint_generator import FingerprintGenerator
from database import FingerprintDatabase
from matcher import FingerprintMatcher

processor = AudioProcessor()
generator = FingerprintGenerator()
database = FingerprintDatabase("songs.db")
matcher = FingerprintMatcher()

# Index a file
audio_data = processor.process_file("song.wav")
fingerprints = generator.process_audio_data(audio_data)
database.add_song("Song Name", fingerprints)

# Identify a clip
query_data = processor.process_file("clip.wav")
query_fp = generator.process_audio_data(query_data)
results = matcher.match(query_fp, database)
```

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  AudioProcessor  │────▶│ FingerprintGenerator  │────▶│ FingerprintDB    │
│                  │     │                      │     │  (SQLite)        │
│ - Load audio     │     │ - Peak pairs → hashes│     │                  │
│ - Spectrogram    │     │ - Consellation map   │     │ hash → song_id   │
│ - Peak detection │     │                      │     │                  │
└─────────────────┘     └──────────────────────┘     └──────────────────┘
                                                          │
                    ┌──────────────────────┐               │
                    │  FingerprintMatcher   │◀──────────────┘
                    │                      │
                    │ - Hash matching       │
                    │ - Scoring & ranking   │
                    └──────────────────────┘
```

**Pipeline:** Load audio → compute spectrogram (STFT) → detect spectral peaks → generate fingerprint hashes (peak-pair constellation) → store/query in SQLite → match and rank results.

## Project Structure

```
├── fingerprint_app.py       # CLI entry point (index, identify, visualize)
├── audio_processor.py       # Audio loading, spectrogram, peak detection
├── fingerprint_generator.py # Constellation map and hash generation
├── database.py              # SQLite-backed fingerprint storage
├── matcher.py               # Matching and scoring engine
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container deployment
├── docker-compose.yml       # Docker Compose config
├── docs/                    # Extended documentation
│   └── API.md               # Detailed module API reference
├── demo/                    # Demo scripts and sample data
└── tests/                   # Test suite
```

## Docker

```bash
docker-compose up --build
```

## Testing

```bash
pytest tests/ -v
```

## Dependencies

- **numpy** — numerical computation
- **scipy** — signal processing (STFT, peak filtering)
- **pydub** — audio file loading and format conversion
- **matplotlib** — spectrogram visualization
- **tqdm** — progress bars

## Troubleshooting

### "Could not find ffmpeg or avconv"
```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### Low confidence scores
- Ensure clip is at least 5 seconds long
- Verify clip contains audio from an indexed song
- Check audio quality is reasonable

## License

MIT License - Ver [LICENSE](LICENSE)

## Contact

[@dixi3stdgdl-design](https://github.com/dixi3stdgdl-design)
