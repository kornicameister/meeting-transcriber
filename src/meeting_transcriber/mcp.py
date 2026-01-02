#!/usr/bin/env python3
"""MCP Server for meeting transcription."""

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import boto3  # type: ignore[import-untyped]

if TYPE_CHECKING:
    pass

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext, Progress

from .transcription.audio_extraction import extract_audio
from .transcription.aws_transcribe import transcribe_audio
from .transcription.markdown_converter import convert_to_markdown

mcp = FastMCP(
    "meeting-transcriber",
    instructions="Professional meeting transcription service with AWS Transcribe integration. Extract audio from videos, transcribe with speaker identification, and generate markdown transcripts.",
)


def _get_aws_client(
    service: str,
    region: str,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_session_token: str | None = None,
) -> Any:
    """Create AWS client with custom credentials if provided."""
    if aws_access_key_id and aws_secret_access_key:
        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )
    else:
        return boto3.client(service, region_name=region)


@mcp.tool(
    name="extract_audio",
    description="Extract audio from video file using FFmpeg",
    tags={"audio", "video", "extraction"},
)
async def extract_audio_tool(
    video_path: str,
    audio_name: str = "audio.mp3",
    ctx: Context = CurrentContext(),  # noqa: B008
) -> dict[str, str]:
    """Extract audio from video file."""
    await ctx.info(f"Extracting audio from {video_path}")

    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    try:
        audio_file = extract_audio(video_file=video_file, audio_name=audio_name)
        await ctx.info(f"Audio extracted to {audio_file}")

        return {
            "audio_path": str(audio_file),
            "video_path": video_path,
            "status": "success",
        }
    except Exception as e:
        await ctx.error(f"Audio extraction failed: {str(e)}")
        raise


@mcp.tool(
    name="transcribe_audio",
    description="Transcribe audio file using AWS Transcribe with speaker identification",
    tags={"transcription", "aws", "speakers"},
)
async def transcribe_audio_tool(
    audio_path: str,
    bucket: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    region_name: str = "us-east-1",
    max_speakers: int = 10,
    job_name: str | None = None,
    aws_session_token: str | None = None,
    ctx: Context = CurrentContext(),  # noqa: B008
    progress: Progress = Progress(),  # noqa: B008
) -> dict[str, Any]:
    """Transcribe audio file using AWS Transcribe."""
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Generate job name if not provided
    if not job_name:
        timestamp = int(time.time())
        job_name = f"transcribe-{audio_file.stem}-{timestamp}"

    await ctx.info(f"Starting transcription job: {job_name}")
    await progress.set_total(100)

    try:
        # Create AWS clients with custom credentials
        s3_client: Any = _get_aws_client(
            "s3",
            region_name,
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
        )
        transcribe_client: Any = _get_aws_client(
            "transcribe",
            region_name,
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
        )

        # Upload phase
        await progress.set_message("Uploading to S3...")
        await progress.increment(20)

        # Transcription phase
        await progress.set_message("Starting AWS Transcribe job...")
        await progress.increment(10)

        transcript_data = transcribe_audio(
            s3_client,
            transcribe_client,
            audio_file=audio_file,
            bucket=bucket,
            job_name=job_name,
            max_speakers=max_speakers,
        )

        await progress.set_message("Transcription completed")
        await progress.increment(70)

        # Get speaker count
        speaker_labels = transcript_data["results"].get("speaker_labels", {})
        speakers_count = len(
            {
                segment.get("speaker_label", "")
                for segment in speaker_labels.get("segments", [])
            }
        )

        transcript_text = transcript_data["results"]["transcripts"][0]["transcript"]

        await ctx.info(f"Transcription completed. Speakers: {speakers_count}")

        return {
            "transcript_data": transcript_data,
            "speakers_count": speakers_count,
            "transcript_length": len(transcript_text),
            "job_name": job_name,
            "status": "success",
        }
    except Exception as e:
        await ctx.error(f"Transcription failed: {str(e)}")
        raise


@mcp.tool(
    name="transcribe_video",
    description="Complete video transcription pipeline: extract audio → transcribe → convert to markdown",
    tags={"transcription", "video", "pipeline", "markdown"},
)
async def transcribe_video_tool(
    video_path: str,
    bucket: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    region_name: str = "us-east-1",
    max_speakers: int = 10,
    audio_name: str = "audio.mp3",
    job_name: str | None = None,
    cleanup_audio: bool = True,
    aws_session_token: str | None = None,
    ctx: Context = CurrentContext(),  # noqa: B008
    progress: Progress = Progress(),  # noqa: B008
) -> dict[str, str]:
    """Complete video transcription pipeline: extract audio → transcribe → convert to markdown."""
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Generate job name if not provided
    if not job_name:
        timestamp = int(time.time())
        job_name = f"transcribe-{video_file.stem}-{timestamp}"

    await ctx.info(f"Starting video transcription pipeline: {job_name}")
    await progress.set_total(100)

    try:
        # Create AWS clients with custom credentials
        s3_client: Any = _get_aws_client(
            "s3",
            region_name,
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
        )
        transcribe_client: Any = _get_aws_client(
            "transcribe",
            region_name,
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
        )

        # Step 1: Extract audio
        await progress.set_message("Extracting audio from video...")
        audio_file = extract_audio(video_file=video_file, audio_name=audio_name)
        await progress.increment(20)
        await ctx.info(f"Audio extracted: {audio_file}")

        # Step 2: Transcribe audio
        await progress.set_message("Transcribing audio...")
        transcript_data = transcribe_audio(
            s3_client,
            transcribe_client,
            audio_file=audio_file,
            bucket=bucket,
            job_name=job_name,
            max_speakers=max_speakers,
        )
        await progress.increment(60)

        # Step 3: Convert to markdown
        await progress.set_message("Converting to markdown...")
        output_file = audio_file.parent / "transcript.json"
        markdown_file = convert_to_markdown(
            transcript_data=transcript_data, output_file=output_file
        )
        await progress.increment(15)

        # Step 4: Cleanup
        if cleanup_audio and audio_file.exists():
            audio_file.unlink()
            await ctx.info("Audio file cleaned up")

        if output_file.exists():
            output_file.unlink()

        await progress.increment(5)
        await progress.set_message("Transcription complete")

        # Get stats
        speaker_labels = transcript_data["results"].get("speaker_labels", {})
        speakers_count = len(
            {
                segment.get("speaker_label", "")
                for segment in speaker_labels.get("segments", [])
            }
        )

        transcript_text = transcript_data["results"]["transcripts"][0]["transcript"]

        await ctx.info(
            f"Pipeline completed. Speakers: {speakers_count}, Length: {len(transcript_text)} chars"
        )

        return {
            "markdown_path": str(markdown_file),
            "video_path": video_path,
            "speakers_count": str(speakers_count),
            "transcript_length": str(len(transcript_text)),
            "job_name": job_name,
            "status": "success",
        }
    except Exception as e:
        await ctx.error(f"Video transcription failed: {str(e)}")
        raise


def main() -> None:
    """Entry point for MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
