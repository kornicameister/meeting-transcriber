"""AWS Transcribe audio transcription."""

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types_boto3_s3.client import S3Client
    from types_boto3_transcribe.client import TranscribeServiceClient


def transcribe_audio(
    s3_client: "S3Client",
    transcribe_client: "TranscribeServiceClient",
    *,
    audio_file: Path,
    bucket: str,
    job_name: str,
    max_speakers: int = 10,
) -> dict[str, Any]:
    """Transcribe audio file using AWS Transcribe."""
    # S3 paths
    s3_key = f"audio/{job_name}/{audio_file.name}"
    s3_uri = f"s3://{bucket}/{s3_key}"
    output_key = f"transcripts/{job_name}.json"

    # Upload to S3
    s3_client.upload_file(str(audio_file), bucket, s3_key)

    # Start transcription job
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        LanguageCode="en-US",
        Media={"MediaFileUri": s3_uri},
        Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": max_speakers},
        OutputBucketName=bucket,
        OutputKey=output_key,
    )

    # Wait for completion
    while True:
        job_status = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        status = job_status["TranscriptionJob"]["TranscriptionJobStatus"]

        if status == "COMPLETED":
            break
        elif status == "FAILED":
            failure_reason = job_status["TranscriptionJob"].get(
                "FailureReason", "Unknown error"
            )
            raise RuntimeError(f"Transcription failed: {failure_reason}")

        time.sleep(10)

    # Download result
    output_file = audio_file.parent / "transcript.json"
    s3_client.download_file(bucket, output_key, str(output_file))

    # Cleanup S3
    s3_client.delete_object(Bucket=bucket, Key=s3_key)
    s3_client.delete_object(Bucket=bucket, Key=output_key)

    # Load and return transcript data
    with open(output_file) as f:
        return json.load(f)  # type: ignore[no-any-return]
