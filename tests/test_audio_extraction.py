"""Tests for audio extraction functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from meeting_transcriber.transcription.audio_extraction import extract_audio


def test_extract_audio_success(tmp_path: Path) -> None:
    """Test successful audio extraction."""
    # Setup
    video_file = tmp_path / "test_video.mp4"
    video_file.touch()  # Create empty file
    audio_name = "test_audio.mp3"

    # Mock ffmpeg
    with patch(
        "meeting_transcriber.transcription.audio_extraction.ffmpeg"
    ) as mock_ffmpeg:
        mock_input = MagicMock()
        mock_output = MagicMock()
        mock_run = MagicMock()

        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        mock_output.overwrite_output.return_value = mock_run

        # Execute
        result = extract_audio(video_file=video_file, audio_name=audio_name)

        # Assert
        assert result == video_file.parent / audio_name
        mock_ffmpeg.input.assert_called_once_with(str(video_file))
        mock_input.output.assert_called_once_with(
            str(video_file.parent / audio_name), acodec="mp3", ab="192k", vn=None
        )
        mock_output.overwrite_output.assert_called_once()
        mock_run.run.assert_called_once_with(quiet=True)


def test_extract_audio_default_name(tmp_path: Path) -> None:
    """Test audio extraction with default filename."""
    # Setup
    video_file = tmp_path / "test_video.mp4"
    video_file.touch()

    # Mock ffmpeg
    with patch("meeting_transcriber.transcription.audio_extraction.ffmpeg"):
        # Execute
        result = extract_audio(video_file=video_file)

        # Assert
        assert result == video_file.parent / "audio.mp3"
