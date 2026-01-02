"""Tests for MCP server functionality."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastmcp.client import Client

from meeting_transcriber.mcp import mcp

# Mark all tests as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client() -> AsyncGenerator[Client[Any], None]:
    """FastMCP test client."""
    async with Client(transport=mcp) as client:
        yield client


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


async def test_list_tools(mcp_client: Client[Any]) -> None:
    """Test MCP server lists all tools."""
    tools = await mcp_client.list_tools()

    assert len(tools) == 3
    tool_names = {tool.name for tool in tools}
    assert tool_names == {"extract_audio", "transcribe_audio", "transcribe_video"}


async def test_extract_audio_tool(mcp_client: Client[Any], tmp_path: Path) -> None:
    """Test extract_audio tool."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()

    with patch("meeting_transcriber.mcp.extract_audio") as mock_extract:
        audio_file = tmp_path / "audio.mp3"
        mock_extract.return_value = audio_file

        result = await mcp_client.call_tool(
            name="extract_audio",
            arguments={"video_path": str(video_file), "audio_name": "audio.mp3"},
        )

        assert result.data["status"] == "success"
        assert result.data["audio_path"] == str(audio_file)
        assert result.data["video_path"] == str(video_file)


async def test_extract_audio_file_not_found(mcp_client: Client[Any]) -> None:
    """Test extract_audio with nonexistent file."""
    result = await mcp_client.call_tool(
        name="extract_audio",
        arguments={"video_path": "nonexistent.mp4"},
        raise_on_error=False,
    )

    assert result.is_error
    assert "not found" in result.content[0].text  # type: ignore[union-attr]
