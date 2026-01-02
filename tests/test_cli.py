"""Tests for CLI functionality."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from moto import mock_aws

from meeting_transcriber.cli import main


@pytest.fixture
def runner() -> CliRunner:
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def sample_transcript_data() -> dict[str, Any]:
    """Sample AWS Transcribe response data."""
    return {
        "results": {
            "transcripts": [{"transcript": "Hello world test transcript"}],
            "speaker_labels": {
                "segments": [
                    {"speaker_label": "spk_0", "start_time": "0.0", "end_time": "2.0"},
                    {"speaker_label": "spk_1", "start_time": "2.1", "end_time": "4.0"},
                ]
            },
        }
    }


@mock_aws
def test_cli_success(
    runner: CliRunner, tmp_path: Path, sample_transcript_data: dict[str, Any]
) -> None:
    """Test successful CLI execution."""
    # Setup
    video_file = tmp_path / "test.mp4"
    video_file.touch()

    with (
        patch("meeting_transcriber.cli.extract_audio") as mock_extract,
        patch("meeting_transcriber.cli.transcribe_audio") as mock_transcribe,
        patch("meeting_transcriber.cli.convert_to_markdown") as mock_convert,
        patch("meeting_transcriber.cli.boto3") as mock_boto3,
    ):
        # Mock AWS clients
        mock_s3 = MagicMock()
        mock_transcribe_client = MagicMock()
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            "s3": mock_s3,
            "transcribe": mock_transcribe_client,
        }[service]

        # Mock returns
        audio_file = tmp_path / "audio.mp3"
        json_file = tmp_path / "transcript.json"
        markdown_file = tmp_path / "transcript.md"

        mock_extract.return_value = audio_file
        mock_transcribe.return_value = sample_transcript_data
        mock_convert.return_value = markdown_file

        # Create mock files
        audio_file.touch()
        json_file.write_text(json.dumps(sample_transcript_data))
        markdown_file.write_text("# Test\n[speaker: spk_0][00:00-00:02]: Hello world")

        # Execute
        result = runner.invoke(
            main, [str(video_file), "--bucket", "test-bucket", "--job-name", "test-job"]
        )

        # Assert
        assert result.exit_code == 0
        assert "Transcription Complete!" in result.output
        assert "test-job" in result.output


def test_cli_missing_bucket(runner: CliRunner, tmp_path: Path) -> None:
    """Test CLI with missing required bucket parameter."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()

    result = runner.invoke(main, [str(video_file)])

    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_cli_nonexistent_file(runner: CliRunner) -> None:
    """Test CLI with nonexistent video file."""
    result = runner.invoke(main, ["nonexistent.mp4", "--bucket", "test-bucket"])

    assert result.exit_code != 0


@mock_aws
def test_cli_with_cleanup_options(
    runner: CliRunner, tmp_path: Path, sample_transcript_data: dict[str, Any]
) -> None:
    """Test CLI with cleanup options."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()

    with (
        patch("meeting_transcriber.cli.extract_audio") as mock_extract,
        patch("meeting_transcriber.cli.transcribe_audio") as mock_transcribe,
        patch("meeting_transcriber.cli.convert_to_markdown") as mock_convert,
        patch("meeting_transcriber.cli.boto3") as mock_boto3,
    ):
        # Mock AWS clients
        mock_s3 = MagicMock()
        mock_transcribe_client = MagicMock()
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            "s3": mock_s3,
            "transcribe": mock_transcribe_client,
        }[service]

        audio_file = tmp_path / "audio.mp3"
        json_file = tmp_path / "transcript.json"
        markdown_file = tmp_path / "transcript.md"

        mock_extract.return_value = audio_file
        mock_transcribe.return_value = sample_transcript_data
        mock_convert.return_value = markdown_file

        audio_file.touch()
        json_file.write_text(json.dumps(sample_transcript_data))
        markdown_file.touch()

        result = runner.invoke(
            main,
            [
                str(video_file),
                "--bucket",
                "test-bucket",
                "--cleanup-audio",
                "--cleanup-json",
            ],
        )

        assert result.exit_code == 0
        assert "removed" in result.output.lower()


@mock_aws
def test_cli_keep_files(
    runner: CliRunner, tmp_path: Path, sample_transcript_data: dict[str, Any]
) -> None:
    """Test CLI with keep files options."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()

    with (
        patch("meeting_transcriber.cli.extract_audio") as mock_extract,
        patch("meeting_transcriber.cli.transcribe_audio") as mock_transcribe,
        patch("meeting_transcriber.cli.convert_to_markdown") as mock_convert,
        patch("meeting_transcriber.cli.boto3") as mock_boto3,
    ):
        # Mock AWS clients
        mock_s3 = MagicMock()
        mock_transcribe_client = MagicMock()
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            "s3": mock_s3,
            "transcribe": mock_transcribe_client,
        }[service]

        audio_file = tmp_path / "audio.mp3"
        json_file = tmp_path / "transcript.json"
        markdown_file = tmp_path / "transcript.md"

        mock_extract.return_value = audio_file
        mock_transcribe.return_value = sample_transcript_data
        mock_convert.return_value = markdown_file

        audio_file.touch()
        json_file.write_text(json.dumps(sample_transcript_data))
        markdown_file.touch()

        result = runner.invoke(
            main,
            [str(video_file), "--bucket", "test-bucket", "--keep-audio", "--keep-json"],
        )

        assert result.exit_code == 0
        assert "preserved" in result.output.lower()


def test_cli_extract_audio_error(runner: CliRunner, tmp_path: Path) -> None:
    """Test CLI with audio extraction error."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()

    with patch("meeting_transcriber.cli.extract_audio") as mock_extract:
        mock_extract.side_effect = Exception("FFmpeg error")

        result = runner.invoke(main, [str(video_file), "--bucket", "test-bucket"])

        assert result.exit_code != 0


@mock_aws
def test_cli_transcribe_error(runner: CliRunner, tmp_path: Path) -> None:
    """Test CLI with transcription error."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()

    with (
        patch("meeting_transcriber.cli.extract_audio") as mock_extract,
        patch("meeting_transcriber.cli.transcribe_audio") as mock_transcribe,
        patch("meeting_transcriber.cli.boto3") as mock_boto3,
    ):
        # Mock AWS clients
        mock_s3 = MagicMock()
        mock_transcribe_client = MagicMock()
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            "s3": mock_s3,
            "transcribe": mock_transcribe_client,
        }[service]

        audio_file = tmp_path / "audio.mp3"
        mock_extract.return_value = audio_file
        mock_transcribe.side_effect = Exception("Transcribe error")

        result = runner.invoke(main, [str(video_file), "--bucket", "test-bucket"])

        assert result.exit_code != 0
