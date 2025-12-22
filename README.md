# Meeting Transcriber 🎙️

Professional audio/video transcription toolkit with local Faster-Whisper and AWS Transcribe integration. Extract audio, identify speakers, generate markdown transcripts with timestamps. Perfect for meeting documentation and content creation workflows.

## Features

- **Local Transcription**: 100% private processing with Faster-Whisper
- **Cloud Transcription**: AWS Transcribe with speaker identification
- **Audio Extraction**: Extract audio from video files (MP4, etc.)
- **Speaker Detection**: Automatic speaker labeling and timestamps
- **Markdown Output**: Clean, readable transcript format
- **Multiple Models**: Choose speed vs accuracy trade-offs

## Quick Start

```bash
# Install dependencies
uv sync

# Local transcription (private)
uv run python transcribe.py meeting.mp4

# AWS Transcribe (cloud)
uv run python aws_transcribe.py meeting.mp4 --bucket your-s3-bucket
```

## Local Transcription Models

| Model  | Size   | Speed | Accuracy | Best For |
|--------|--------|-------|----------|----------|
| tiny   | ~39MB  | ~32x  | Basic    | Quick drafts |
| base   | ~74MB  | ~16x  | Good     | Recommended |
| small  | ~244MB | ~6x   | Better   | Higher accuracy |
| medium | ~769MB | ~2x   | High     | Best quality |

## Requirements

- Python 3.9-3.12
- FFmpeg (for audio extraction)
- AWS credentials (for cloud transcription)

## Installation

```bash
git clone https://github.com/kornicameister/meeting-transcriber.git
cd meeting-transcriber
uv sync
```

## Usage Examples

### Local Transcription
```bash
# Basic transcription
uv run python transcribe.py meeting.mp4

# Fast transcription
uv run python transcribe.py meeting.mp4 --model tiny

# High quality
uv run python transcribe.py meeting.mp4 --model medium
```

### AWS Transcribe
```bash
# With speaker identification
uv run python aws_transcribe.py meeting.mp4 --bucket my-bucket --max-speakers 5

# Custom job name
uv run python aws_transcribe.py meeting.mp4 --bucket my-bucket --job-name "team-standup-2024"
```

## Output Format

Transcripts are generated in markdown format with speaker labels and timestamps:

```markdown
# Meeting Transcript

[speaker: spk_0][00:15-00:32]: Welcome everyone to today's meeting. Let's start with the project updates.

[speaker: spk_1][00:33-00:45]: Thanks for having me. I wanted to discuss the latest developments in our API integration.
```

## License

MIT License - see LICENSE file for details.