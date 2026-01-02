"""Tests for AWS Transcribe functionality."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import boto3  # type: ignore[import-untyped]
import pytest
from moto import mock_aws

from meeting_transcriber.transcription.aws_transcribe import transcribe_audio


@mock_aws
def test_transcribe_audio_success(tmp_path: Path) -> None:
    """Test successful audio transcription."""
    # Setup AWS clients
    s3_client = boto3.client("s3", region_name="us-east-1")
    transcribe_client = boto3.client("transcribe", region_name="us-east-1")

    # Create bucket
    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Setup files
    audio_file = tmp_path / "test_audio.mp3"
    audio_file.write_text("fake audio content")

    job_name = "test-job"

    # Mock transcribe responses
    transcribe_client.get_transcription_job = MagicMock()
    transcribe_client.get_transcription_job.return_value = {
        "TranscriptionJob": {"TranscriptionJobStatus": "COMPLETED"}
    }

    # Mock transcript data
    transcript_data = {
        "results": {
            "transcripts": [{"transcript": "Hello world"}],
            "items": [],
            "speaker_labels": {"segments": []},
        }
    }

    # Create transcript file that will be downloaded
    transcript_file = tmp_path / "transcript.json"
    transcript_file.write_text(json.dumps(transcript_data))

    # Mock download_file to copy our test file
    def mock_download(bucket: str, key: str, filename: str) -> None:
        Path(filename).write_text(json.dumps(transcript_data))

    s3_client.download_file = mock_download

    # Execute
    result = transcribe_audio(
        s3_client,
        transcribe_client,
        audio_file=audio_file,
        bucket=bucket,
        job_name=job_name,
    )

    # Assert
    assert result == transcript_data
    assert "results" in result
    assert "transcripts" in result["results"]


@mock_aws
def test_transcribe_audio_failed_job(tmp_path: Path) -> None:
    """Test transcription job failure."""
    # Setup
    s3_client = boto3.client("s3", region_name="us-east-1")
    transcribe_client = boto3.client("transcribe", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    audio_file = tmp_path / "test_audio.mp3"
    audio_file.write_text("fake audio")

    # Mock failed transcription
    transcribe_client.get_transcription_job = MagicMock()
    transcribe_client.get_transcription_job.return_value = {
        "TranscriptionJob": {
            "TranscriptionJobStatus": "FAILED",
            "FailureReason": "Test failure",
        }
    }

    # Execute & Assert
    with pytest.raises(RuntimeError, match="Transcription failed: Test failure"):
        transcribe_audio(
            s3_client,
            transcribe_client,
            audio_file=audio_file,
            bucket=bucket,
            job_name="test-job",
        )
