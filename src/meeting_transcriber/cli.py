#!/usr/bin/env python3
"""
AWS Transcribe Job Manager
Uploads audio, starts transcription job, waits for completion, downloads result
"""

import json
import time
from pathlib import Path

import boto3  # type: ignore[import-untyped]
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .transcription.audio_extraction import extract_audio
from .transcription.aws_transcribe import transcribe_audio
from .transcription.markdown_converter import convert_to_markdown

console = Console()


def extract_audio_cli(video_file: Path, audio_name: str) -> Path:
    """Extract audio from MP4 video using ffmpeg with CLI progress."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting audio from video...", total=None)

        try:
            audio_file = extract_audio(video_file=video_file, audio_name=audio_name)
            progress.update(task, description="✅ Audio extraction complete")
            return audio_file
        except Exception as e:
            console.print(f"\n❌ [bold red]FFmpeg error:[/bold red] {str(e)}")
            raise click.Abort() from e


def transcribe_audio_cli(
    audio_file: Path, bucket: str, job_name: str, max_speakers: int, region: str
) -> Path:
    """Upload audio to S3, transcribe with AWS Transcribe, download result with CLI progress."""
    # Initialize AWS clients
    s3_client = boto3.client("s3", region_name=region)
    transcribe_client = boto3.client("transcribe", region_name=region)

    try:
        # Upload to S3
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Uploading to S3...", total=None)
            s3_client.upload_file(
                str(audio_file), bucket, f"audio/{job_name}/{audio_file.name}"
            )
            progress.update(task, description="✅ Upload complete")

        # Start transcription job
        console.print("\n🚀 Starting transcription job...")

        # Wait for completion with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Waiting for transcription...", total=None)

            transcript_data = transcribe_audio(
                s3_client,
                transcribe_client,
                audio_file=audio_file,
                bucket=bucket,
                job_name=job_name,
                max_speakers=max_speakers,
            )
            progress.update(task, description="✅ Transcription complete")

        # Save transcript data
        output_file = audio_file.parent / "transcript.json"
        with open(output_file, "w") as f:
            json.dump(transcript_data, f)

        return output_file

    except Exception as e:
        console.print(f"\n❌ [bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() from e


@click.command()
@click.argument("video_file", type=click.Path(exists=True, path_type=Path))
@click.option("--bucket", "-b", required=True, help="S3 bucket name")
@click.option(
    "--job-name", "-j", help="Transcription job name (auto-generated if not provided)"
)
@click.option(
    "--max-speakers", "-s", default=10, help="Maximum number of speakers to identify"
)
@click.option("--region", "-r", default="us-east-1", help="AWS region")
@click.option(
    "--audio-name",
    "-a",
    default="audio.mp3",
    help="Audio filename (default: meeting_audio.mp3)",
)
@click.option(
    "--cleanup-audio/--keep-audio",
    default=True,
    help="Remove audio file after transcription (default: keep)",
)
@click.option(
    "--cleanup-json/--keep-json",
    default=True,
    help="Remove JSON file after creating markdown (default: keep)",
)
def main(
    video_file: Path,
    bucket: str,
    job_name: str | None,
    max_speakers: int,
    region: str,
    audio_name: str,
    cleanup_audio: bool,
    cleanup_json: bool,
) -> None:
    """
    🎯 AWS Transcribe Job Manager

    Extracts audio from MP4 video, uploads to S3, starts transcription job with speaker identification,
    waits for completion, and downloads the result to the same folder.

    Example: python aws_transcribe.py meeting.mp4
    """

    console.print(
        Panel.fit(
            "[bold blue]🎯 AWS Transcribe Job Manager[/bold blue]\n"
            "[green]🔊 Speaker identification enabled[/green]",
            border_style="blue",
        )
    )

    # Generate job name if not provided
    if not job_name:
        timestamp = int(time.time())
        job_name = f"transcribe-{video_file.stem}-{timestamp}"

    console.print(f"\n🎥 Video file: [bold]{video_file.name}[/bold]")
    console.print(f"🪣 S3 bucket: [bold]{bucket}[/bold]")
    console.print(f"🏷️  Job name: [bold]{job_name}[/bold]")
    console.print(f"👥 Max speakers: [bold]{max_speakers}[/bold]")
    console.print(f"🎵 Audio filename: [bold]{audio_name}[/bold]")
    console.print(f"🧹 Cleanup audio: [bold]{'Yes' if cleanup_audio else 'No'}[/bold]")
    console.print(f"📄 Cleanup JSON: [bold]{'Yes' if cleanup_json else 'No'}[/bold]")

    try:
        # Extract audio from video
        audio_file = extract_audio_cli(video_file, audio_name)
        console.print(f"🎵 Audio extracted: [bold]{audio_file.name}[/bold]")

        # Transcribe audio
        output_file = transcribe_audio_cli(
            audio_file, bucket, job_name, max_speakers, region
        )

        # Load and process results
        with open(output_file) as f:
            transcript_data = json.load(f)

        # Convert to markdown
        console.print("\n📝 Converting to markdown format...")
        markdown_file = convert_to_markdown(
            transcript_data=transcript_data, output_file=output_file
        )

        transcript_text = transcript_data["results"]["transcripts"][0]["transcript"]
        speaker_labels = transcript_data["results"].get("speaker_labels", {})
        speakers_count = len(
            {
                segment.get("speaker_label", "")
                for segment in speaker_labels.get("segments", [])
            }
        )

        console.print("\n✅ [bold green]Transcription Complete![/bold green]")
        console.print(f"📄 JSON saved: [bold]{output_file}[/bold]")
        console.print(f"📝 Markdown saved: [bold]{markdown_file}[/bold]")
        console.print(f"👥 Speakers identified: [bold]{speakers_count}[/bold]")
        console.print(
            f"📊 Transcript length: [bold]{len(transcript_text)} characters[/bold]"
        )

        # Show markdown preview
        with open(markdown_file) as f:
            markdown_content = f.read()
        preview_lines = markdown_content.split("\n")[
            2:4
        ]  # Skip title, show first 2 speaker lines
        preview = "\n".join(preview_lines)
        console.print(f"\n📝 [bold]Markdown Preview:[/bold]\n{preview}")

        # Cleanup files if requested
        audio_status = "preserved"
        if cleanup_audio and audio_file.exists():
            audio_file.unlink()
            audio_status = "removed"
            console.print(f"🧹 Removed audio file: [bold]{audio_file.name}[/bold]")

        json_status = "preserved"
        if cleanup_json and output_file.exists():
            output_file.unlink()
            json_status = "removed"
            console.print(f"🧹 Removed JSON file: [bold]{output_file.name}[/bold]")

        console.print(
            Panel(
                "[green]🎉 Success![/green]\n"
                f"Markdown transcript saved to: [bold]{markdown_file}[/bold]\n"
                f"JSON file {json_status}: [bold]{output_file.name}[/bold]\n"
                f"Audio file {audio_status}: [bold]{audio_file.name}[/bold]",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"\n❌ [bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() from e


if __name__ == "__main__":
    main()
