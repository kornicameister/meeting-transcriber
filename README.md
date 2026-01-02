# Meeting Transcriber 🎙️

Professional audio/video transcription toolkit with AWS Transcribe integration and **MCP Server support**. Extract audio from video files, identify speakers, and generate markdown transcripts with timestamps. Perfect for meeting documentation and content creation workflows.

## Features

- **MCP Server**: Local Model Context Protocol server for LLM integration
- **Cloud Transcription**: AWS Transcribe with speaker identification
- **Audio Extraction**: Extract audio from video files (MP4, etc.)
- **Speaker Detection**: Automatic speaker labeling and timestamps
- **Markdown Output**: Clean, readable transcript format
- **Rich CLI Interface**: Beautiful progress bars and formatted output

## Quick Start

```bash
# Install dependencies
uv sync

# Start MCP server (for LLM integration)
uv run mcp-server

# Or use CLI directly
uv run python -m meeting_transcriber.aws_transcribe meeting.mp4 --bucket your-s3-bucket
```

## Requirements

- Python 3.10-3.12
- FFmpeg (for audio extraction)
- AWS credentials configured
- S3 bucket for temporary file storage

## Installation

```bash
git clone https://github.com/kornicameister/meeting-transcriber.git
cd meeting-transcriber
uv sync
```

## MCP Server (for LLM integration)

Local MCP (Model Context Protocol) server providing transcription tools via STDIO.

### Start Server
```bash
# Start MCP server (STDIO mode)
uv run mcp-server

# Or using entry point
uv run python -m meeting_transcriber.mcp_server
```

### Available Tools

#### 1. `extract_audio`
Extract audio from video file using FFmpeg.

**Parameters:**
- `video_path` (str): Path to video file
- `audio_name` (str, optional): Output audio filename (default: "audio.mp3")

**Returns:**
```json
{
  "audio_path": "/path/to/audio.mp3",
  "video_path": "/path/to/video.mp4", 
  "status": "success"
}
```

#### 2. `transcribe_audio`
Transcribe audio file using AWS Transcribe with speaker identification.

**Parameters:**
- `audio_path` (str): Path to audio file
- `bucket` (str): S3 bucket name
- `max_speakers` (int, optional): Maximum speakers (default: 10)
- `job_name` (str, optional): Custom job name (auto-generated if not provided)

**Returns:**
```json
{
  "transcript_data": {...},
  "speakers_count": 3,
  "transcript_length": 1250,
  "job_name": "transcribe-audio-1234567890",
  "status": "success"
}
```

#### 3. `transcribe_video`
Complete video transcription pipeline: extract audio → transcribe → convert to markdown.

**Parameters:**
- `video_path` (str): Path to video file
- `bucket` (str): S3 bucket name
- `max_speakers` (int, optional): Maximum speakers (default: 10)
- `audio_name` (str, optional): Temporary audio filename (default: "audio.mp3")
- `job_name` (str, optional): Custom job name (auto-generated if not provided)
- `cleanup_audio` (bool, optional): Remove audio file after transcription (default: true)

**Returns:**
```json
{
  "markdown_path": "/path/to/transcript.md",
  "video_path": "/path/to/video.mp4",
  "speakers_count": 3,
  "transcript_length": 1250,
  "job_name": "transcribe-video-1234567890",
  "status": "success"
}
```

### MCP Features

- **Progress Tracking**: Real-time progress updates for long-running operations
- **Error Handling**: Detailed error messages and logging
- **AWS Integration**: Uses existing AWS Transcribe service
- **Local Operation**: Runs entirely locally via STDIO
- **Speaker Detection**: Automatic speaker identification and labeling

### Architecture

```
MCP Client (LLM) ←→ STDIO ←→ FastMCP Server ←→ TranscriptionService ←→ AWS Transcribe
```

## Usage Examples

### AWS Transcribe CLI
```bash
# Basic transcription with speaker identification
uv run python -m meeting_transcriber.aws_transcribe meeting.mp4 --bucket my-bucket

# Specify maximum number of speakers
uv run python -m meeting_transcriber.aws_transcribe meeting.mp4 --bucket my-bucket --max-speakers 5

# Custom job name and region
uv run python -m meeting_transcriber.aws_transcribe meeting.mp4 \
  --bucket my-bucket \
  --job-name "team-standup-2024" \
  --region us-west-2

# Keep intermediate files for debugging
uv run python -m meeting_transcriber.aws_transcribe meeting.mp4 \
  --bucket my-bucket \
  --keep-audio \
  --keep-json
```

## Output Format

Transcripts are generated in markdown format with speaker labels and timestamps:

```markdown
# Meeting Transcript

[speaker: spk_0][00:15-00:32]: Welcome everyone to today's meeting. Let's start with the project updates.

[speaker: spk_1][00:33-00:45]: Thanks for having me. I wanted to discuss the latest developments in our API integration.
```

## AWS Setup

### Prerequisites
1. **AWS Account** with Transcribe service access
2. **S3 Bucket** for temporary file storage
3. **AWS Credentials** configured via:
   - AWS CLI: `aws configure`
   - Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - IAM roles (for EC2/Lambda deployment)

### Required Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob",
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "*"
        }
    ]
}
```

## License

MIT License - see LICENSE file for details.