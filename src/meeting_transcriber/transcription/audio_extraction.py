"""Audio extraction from video files."""

from pathlib import Path

import ffmpeg  # type: ignore[import-untyped]


def extract_audio(*, video_file: Path, audio_name: str = "audio.mp3") -> Path:
    """Extract audio from video file using FFmpeg."""
    audio_file = video_file.parent / audio_name

    (
        ffmpeg.input(str(video_file))
        .output(str(audio_file), acodec="mp3", ab="192k", vn=None)
        .overwrite_output()
        .run(quiet=True)
    )

    return audio_file
