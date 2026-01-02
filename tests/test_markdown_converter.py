"""Tests for markdown conversion functionality."""

from pathlib import Path

from meeting_transcriber.transcription.markdown_converter import convert_to_markdown


def test_convert_to_markdown_with_speakers(tmp_path: Path) -> None:
    """Test markdown conversion with speaker labels."""
    # Setup
    transcript_data = {
        "results": {
            "items": [
                {
                    "type": "pronunciation",
                    "start_time": "0.0",
                    "end_time": "1.0",
                    "alternatives": [{"content": "Hello"}],
                },
                {
                    "type": "pronunciation",
                    "start_time": "1.0",
                    "end_time": "2.0",
                    "alternatives": [{"content": "world"}],
                },
                {"type": "punctuation", "alternatives": [{"content": "."}]},
            ],
            "speaker_labels": {
                "segments": [
                    {"start_time": "0.0", "end_time": "2.0", "speaker_label": "spk_0"}
                ]
            },
        }
    }

    output_file = tmp_path / "transcript.json"

    # Execute
    result = convert_to_markdown(
        transcript_data=transcript_data, output_file=output_file
    )

    # Assert
    assert result == tmp_path / "transcript.md"
    assert result.exists()

    content = result.read_text()
    assert "# Meeting Transcript" in content
    assert "[speaker: spk_0][00:00-00:02]: Hello world." in content


def test_convert_to_markdown_no_speakers(tmp_path: Path) -> None:
    """Test markdown conversion without speaker labels."""
    # Setup
    transcript_data = {
        "results": {
            "items": [
                {
                    "type": "pronunciation",
                    "start_time": "0.0",
                    "end_time": "1.0",
                    "alternatives": [{"content": "Hello"}],
                }
            ],
            "speaker_labels": {"segments": []},
        }
    }

    output_file = tmp_path / "transcript.json"

    # Execute
    result = convert_to_markdown(
        transcript_data=transcript_data, output_file=output_file
    )

    # Assert
    assert result.exists()
    content = result.read_text()
    assert "# Meeting Transcript" in content


def test_convert_to_markdown_multiple_speakers(tmp_path: Path) -> None:
    """Test markdown conversion with multiple speakers."""
    # Setup
    transcript_data = {
        "results": {
            "items": [
                {
                    "type": "pronunciation",
                    "start_time": "0.0",
                    "end_time": "1.0",
                    "alternatives": [{"content": "Hello"}],
                },
                {
                    "type": "pronunciation",
                    "start_time": "2.0",
                    "end_time": "3.0",
                    "alternatives": [{"content": "Hi"}],
                },
            ],
            "speaker_labels": {
                "segments": [
                    {"start_time": "0.0", "end_time": "1.0", "speaker_label": "spk_0"},
                    {"start_time": "2.0", "end_time": "3.0", "speaker_label": "spk_1"},
                ]
            },
        }
    }

    output_file = tmp_path / "transcript.json"

    # Execute
    result = convert_to_markdown(
        transcript_data=transcript_data, output_file=output_file
    )

    # Assert
    content = result.read_text()
    assert "[speaker: spk_0]" in content
    assert "[speaker: spk_1]" in content
