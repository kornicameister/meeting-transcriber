#!/usr/bin/env python3
"""
AWS Transcribe Job Manager
Uploads audio, starts transcription job, waits for completion, downloads result
"""

import json
import time
from pathlib import Path

import boto3
import click
import ffmpeg
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()

def extract_audio(video_file: Path, audio_name: str) -> Path:
    """Extract audio from MP4 video using ffmpeg"""
    audio_file = video_file.parent / audio_name

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Extracting audio from video...", total=None)

        try:
            (
                ffmpeg
                .input(str(video_file))
                .output(str(audio_file), acodec='mp3', ab='192k', vn=None)
                .overwrite_output()
                .run(quiet=True)
            )
            progress.update(task, description="✅ Audio extraction complete")
            return audio_file
        except ffmpeg.Error as e:
            console.print(f"\n❌ [bold red]FFmpeg error:[/bold red] {str(e)}")
            raise click.Abort() from e

def transcribe_audio(audio_file: Path, bucket: str, job_name: str, max_speakers: int, region: str) -> Path:
    """Upload audio to S3, transcribe with AWS Transcribe, download result"""
    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name=region)
    transcribe_client = boto3.client('transcribe', region_name=region)

    # S3 paths
    s3_key = f"audio/{job_name}/{audio_file.name}"
    s3_uri = f"s3://{bucket}/{s3_key}"
    output_key = f"transcripts/{job_name}.json"
    output_file = audio_file.parent / "transcript.json"

    try:
        # Upload to S3
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Uploading to S3...", total=None)
            s3_client.upload_file(str(audio_file), bucket, s3_key)
            progress.update(task, description="✅ Upload complete")

        # Start transcription job
        console.print("\n🚀 Starting transcription job...")
        job_config = {
            'TranscriptionJobName': job_name,
            'LanguageCode': 'en-US',
            'Media': {'MediaFileUri': s3_uri},
            'Settings': {
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': max_speakers
            },
            'OutputBucketName': bucket,
            'OutputKey': output_key
        }

        response = transcribe_client.start_transcription_job(**job_config)
        console.print(f"✅ Job started: {response['TranscriptionJob']['TranscriptionJobStatus']}")

        # Wait for completion
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Waiting for transcription...", total=None)

            while True:
                job_status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
                status = job_status['TranscriptionJob']['TranscriptionJobStatus']

                if status == 'COMPLETED':
                    progress.update(task, description="✅ Transcription complete")
                    break
                elif status == 'FAILED':
                    failure_reason = job_status['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    console.print(f"\n❌ [bold red]Job failed:[/bold red] {failure_reason}")
                    raise click.Abort()
                else:
                    progress.update(task, description=f"Processing... ({status})")
                    time.sleep(10)

        # Download result
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Downloading transcript...", total=None)
            s3_client.download_file(bucket, output_key, str(output_file))
            progress.update(task, description="✅ Download complete")

        # Cleanup S3 files
        console.print("\n🧹 Cleaning up S3 files...")
        s3_client.delete_object(Bucket=bucket, Key=s3_key)
        s3_client.delete_object(Bucket=bucket, Key=output_key)

        return output_file

    except Exception as e:
        console.print(f"\n❌ [bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() from e

def convert_to_markdown(transcript_data: dict, output_file: Path) -> Path:
    """Convert AWS Transcribe JSON to readable markdown format"""
    markdown_file = output_file.parent / "transcript.md"

    # Get transcript items with speaker labels
    items = transcript_data['results']['items']
    speaker_labels = transcript_data['results'].get('speaker_labels', {})
    segments = speaker_labels.get('segments', [])

    # Create speaker timeline
    speaker_timeline = {}
    for segment in segments:
        start_time = float(segment['start_time'])
        end_time = float(segment['end_time'])
        speaker = segment['speaker_label']
        speaker_timeline[(start_time, end_time)] = speaker

    # Build markdown content
    markdown_lines = []
    current_speaker = None
    current_text = []
    current_start = None
    current_end = None

    for item in items:
        if item['type'] == 'pronunciation':
            item_start = float(item['start_time'])
            item_end = float(item['end_time'])
            word = item['alternatives'][0]['content']

            # Find speaker for this timestamp
            item_speaker = None
            for (seg_start, seg_end), speaker in speaker_timeline.items():
                if seg_start <= item_start <= seg_end:
                    item_speaker = speaker
                    break

            # If speaker changed or first word
            if item_speaker != current_speaker:
                # Write previous speaker's text
                if current_speaker and current_text:
                    text = ' '.join(current_text)
                    start_min = int(current_start // 60)
                    start_sec = int(current_start % 60)
                    end_min = int(current_end // 60)
                    end_sec = int(current_end % 60)
                    markdown_lines.append(
                        f"[speaker: {current_speaker}][{start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d}]: {text}"
                    )

                # Start new speaker section
                current_speaker = item_speaker
                current_text = [word]
                current_start = item_start
                current_end = item_end
            else:
                # Continue with same speaker
                current_text.append(word)
                current_end = item_end

        elif item['type'] == 'punctuation':
            if current_text:
                current_text[-1] += item['alternatives'][0]['content']

    # Write final speaker's text
    if current_speaker and current_text:
        text = ' '.join(current_text)
        start_min = int(current_start // 60)
        start_sec = int(current_start % 60)
        end_min = int(current_end // 60)
        end_sec = int(current_end % 60)
        markdown_lines.append(
            f"[speaker: {current_speaker}][{start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d}]: {text}"
        )

    # Write markdown file
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write("# Meeting Transcript\n\n")
        f.write("\n\n".join(markdown_lines))

    return markdown_file

@click.command()
@click.argument('video_file', type=click.Path(exists=True, path_type=Path))
@click.option('--bucket', '-b', required=True, help='S3 bucket name')
@click.option('--job-name', '-j', help='Transcription job name (auto-generated if not provided)')
@click.option('--max-speakers', '-s', default=10, help='Maximum number of speakers to identify')
@click.option('--region', '-r', default='us-east-1', help='AWS region')
@click.option('--audio-name', '-a', default='audio.mp3', help='Audio filename (default: meeting_audio.mp3)')
@click.option('--cleanup-audio/--keep-audio', default=True, help='Remove audio file after transcription (default: keep)')
@click.option('--cleanup-json/--keep-json', default=True, help='Remove JSON file after creating markdown (default: keep)')
def main(video_file, bucket, job_name, max_speakers, region, audio_name, cleanup_audio, cleanup_json):
    """
    🎯 AWS Transcribe Job Manager

    Extracts audio from MP4 video, uploads to S3, starts transcription job with speaker identification,
    waits for completion, and downloads the result to the same folder.

    Example: python aws_transcribe.py meeting.mp4
    """

    console.print(Panel.fit(
        "[bold blue]🎯 AWS Transcribe Job Manager[/bold blue]\n"
        "[green]🔊 Speaker identification enabled[/green]",
        border_style="blue"
    ))

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
        audio_file = extract_audio(video_file, audio_name)
        console.print(f"🎵 Audio extracted: [bold]{audio_file.name}[/bold]")

        # Transcribe audio
        output_file = transcribe_audio(audio_file, bucket, job_name, max_speakers, region)

        # Load and process results
        with open(output_file) as f:
            transcript_data = json.load(f)

        # Convert to markdown
        console.print("\n📝 Converting to markdown format...")
        markdown_file = convert_to_markdown(transcript_data, output_file)

        transcript_text = transcript_data['results']['transcripts'][0]['transcript']
        speaker_labels = transcript_data['results'].get('speaker_labels', {})
        speakers_count = len({segment.get('speaker_label', '') for segment in speaker_labels.get('segments', [])})

        console.print("\n✅ [bold green]Transcription Complete![/bold green]")
        console.print(f"📄 JSON saved: [bold]{output_file}[/bold]")
        console.print(f"📝 Markdown saved: [bold]{markdown_file}[/bold]")
        console.print(f"👥 Speakers identified: [bold]{speakers_count}[/bold]")
        console.print(f"📊 Transcript length: [bold]{len(transcript_text)} characters[/bold]")

        # Show markdown preview
        with open(markdown_file) as f:
            markdown_content = f.read()
        preview_lines = markdown_content.split('\n')[2:4]  # Skip title, show first 2 speaker lines
        preview = '\n'.join(preview_lines)
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

        console.print(Panel(
            "[green]🎉 Success![/green]\n"
            f"Markdown transcript saved to: [bold]{markdown_file}[/bold]\n"
            f"JSON file {json_status}: [bold]{output_file.name}[/bold]\n"
            f"Audio file {audio_status}: [bold]{audio_file.name}[/bold]",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"\n❌ [bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() from e

if __name__ == "__main__":
    main()
