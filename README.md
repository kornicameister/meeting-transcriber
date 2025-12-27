# Meeting Transcriber 🎙️

Professional audio/video transcription toolkit with AWS Transcribe integration. Extract audio from video files, identify speakers, and generate markdown transcripts with timestamps. Perfect for meeting documentation and content creation workflows.

## Features

- **Cloud Transcription**: AWS Transcribe with speaker identification
- **Audio Extraction**: Extract audio from video files (MP4, etc.)
- **Speaker Detection**: Automatic speaker labeling and timestamps
- **Markdown Output**: Clean, readable transcript format
- **Rich CLI Interface**: Beautiful progress bars and formatted output

## Quick Start

```bash
# Install dependencies
uv sync

# Transcribe with AWS Transcribe
uv run python -m meeting_transcriber.aws_transcribe meeting.mp4 --bucket your-s3-bucket
```

## Requirements

- Python 3.9-3.12
- FFmpeg (for audio extraction)
- AWS credentials configured
- S3 bucket for temporary file storage

## Installation

```bash
git clone https://github.com/kornicameister/meeting-transcriber.git
cd meeting-transcriber
uv sync
```

## Usage Examples

### AWS Transcribe
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