from pathlib import Path
from typing import Any, Dict, Literal, Optional

import essentia.standard as es
import ffmpeg


class AudioProcessingError(Exception):
    pass


camelot_map = {
    ("C", "major"): "8B",
    ("C#", "major"): "3B",
    ("Db", "major"): "3B",
    ("D", "major"): "10B",
    ("D#", "major"): "5B",
    ("Eb", "major"): "5B",
    ("E", "major"): "12B",
    ("F", "major"): "7B",
    ("F#", "major"): "2B",
    ("Gb", "major"): "2B",
    ("G", "major"): "9B",
    ("G#", "major"): "4B",
    ("Ab", "major"): "4B",
    ("A", "major"): "11B",
    ("A#", "major"): "6B",
    ("Bb", "major"): "6B",
    ("B", "major"): "1B",
    ("C", "minor"): "5A",
    ("C#", "minor"): "12A",
    ("Db", "minor"): "12A",
    ("D", "minor"): "7A",
    ("D#", "minor"): "2A",
    ("Eb", "minor"): "2A",
    ("E", "minor"): "9A",
    ("F", "minor"): "4A",
    ("F#", "minor"): "11A",
    ("Gb", "minor"): "11A",
    ("G", "minor"): "6A",
    ("G#", "minor"): "1A",
    ("Ab", "minor"): "1A",
    ("A", "minor"): "8A",
    ("A#", "minor"): "3A",
    ("Bb", "minor"): "3A",
    ("B", "minor"): "10A",
}


def _camelot_key(key: str, scale: Literal["minor", "major"]) -> Optional[str]:
    key = key.strip()
    key = key.replace("♭", "b")
    scale = scale.lower()

    return camelot_map.get((key, scale), "Unknown")


def process_audio(audio_path: Path) -> Dict[str, Any]:
    try:
        # Load mono audio
        loader = es.MonoLoader(filename=str(audio_path))
        audio = loader()

        length = get_audio_length(audio_path)
        length_str = get_audio_length_str(length)

        # BPM estimation
        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, _, _, _, _ = rhythm_extractor(audio)

        # Key estimation
        key_extractor = es.KeyExtractor()
        key, scale, _ = key_extractor(audio)

        camelot = _camelot_key(key, scale)

        return {
            "bpm": round(float(bpm), 2),
            "key": key,
            "scale": scale,
            "camelot": camelot,
            "length_seconds": length,
            "length": length_str,
        }
    except Exception as e:
        raise AudioProcessingError(f"Essentia analysis failed: {e}")


def get_audio_length(audio_path: Path) -> float:
    probe = ffmpeg.probe(audio_path)
    return float(probe["format"]["duration"])


def get_audio_length_str(duration: float) -> str:
    minutes = int(duration // 60)
    seconds = int(round(duration % 60))
    return f"{minutes:02d}:{seconds:02d}"


def download_audio_from_url(url: str) -> Path:
    import tempfile

    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / f"downloaded_audio_{hash(url)}.mp3"
    ffmpeg.input(url).output(str(temp_file), acodec="copy").run(
        capture_stdout=False, capture_stderr=True
    )
    return temp_file
