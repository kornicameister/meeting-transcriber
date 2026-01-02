"""Convert AWS Transcribe JSON to markdown format."""

from pathlib import Path
from typing import Any


def convert_to_markdown(*, transcript_data: dict[str, Any], output_file: Path) -> Path:
    """Convert AWS Transcribe JSON to markdown format."""
    markdown_file = output_file.parent / "transcript.md"

    items = transcript_data["results"]["items"]
    speaker_labels = transcript_data["results"].get("speaker_labels", {})
    segments = speaker_labels.get("segments", [])

    # Create speaker timeline
    speaker_timeline = {}
    for segment in segments:
        start_time = float(segment["start_time"])
        end_time = float(segment["end_time"])
        speaker = segment["speaker_label"]
        speaker_timeline[(start_time, end_time)] = speaker

    # Build markdown content
    markdown_lines = []
    current_speaker = None
    current_text = []
    current_start = None
    current_end = None

    for item in items:
        if item["type"] == "pronunciation":
            item_start = float(item["start_time"])
            item_end = float(item["end_time"])
            word = item["alternatives"][0]["content"]

            # Find speaker for this timestamp
            item_speaker = None
            for (seg_start, seg_end), speaker in speaker_timeline.items():
                if seg_start <= item_start <= seg_end:
                    item_speaker = speaker
                    break

            # If speaker changed or first word
            if item_speaker != current_speaker:
                # Write previous speaker's text
                if (
                    current_speaker
                    and current_text
                    and current_start is not None
                    and current_end is not None
                ):
                    text = " ".join(current_text)
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

        elif item["type"] == "punctuation":
            if current_text:
                current_text[-1] += item["alternatives"][0]["content"]

    # Write final speaker's text
    if (
        current_speaker
        and current_text
        and current_start is not None
        and current_end is not None
    ):
        text = " ".join(current_text)
        start_min = int(current_start // 60)
        start_sec = int(current_start % 60)
        end_min = int(current_end // 60)
        end_sec = int(current_end % 60)
        markdown_lines.append(
            f"[speaker: {current_speaker}][{start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d}]: {text}"
        )

    # Write markdown file
    with open(markdown_file, "w", encoding="utf-8") as f:
        f.write("# Meeting Transcript\n\n")
        f.write("\n\n".join(markdown_lines))

    return markdown_file
