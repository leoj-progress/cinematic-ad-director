from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PTS_RE = re.compile(r"pts_time:([0-9.]+)")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def detect_cuts(ffmpeg: Path, video: Path, threshold: float) -> list[float]:
    result = run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-i",
            str(video),
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-an",
            "-f",
            "null",
            "NUL",
        ]
    )
    candidates = [float(value) for value in PTS_RE.findall(result.stderr)]
    cuts = [0.0]
    for candidate in candidates:
        if candidate - cuts[-1] >= 0.22:
            cuts.append(candidate)
    return cuts


def duration_seconds(ffprobe: Path, video: Path) -> float:
    result = run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ]
    )
    return float(result.stdout.strip())


def extract_frame(ffmpeg: Path, video: Path, time_sec: float, target: Path) -> None:
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{time_sec:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-vf",
            "scale=300:-2",
            "-y",
            str(target),
        ]
    )


def contact_sheet(frames: list[tuple[float, Path]], target: Path) -> None:
    tile_width = 300
    image_height = 534
    label_height = 34
    columns = 4
    rows = (len(frames) + columns - 1) // columns
    canvas = Image.new("RGB", (tile_width * columns, (image_height + label_height) * rows), "#111111")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)

    for index, (time_sec, frame_path) in enumerate(frames):
        image = Image.open(frame_path).convert("RGB")
        image.thumbnail((tile_width, image_height))
        x = (index % columns) * tile_width + (tile_width - image.width) // 2
        y = (index // columns) * (image_height + label_height)
        canvas.paste(image, (x, y))
        draw.text((x + 8, y + image_height + 7), f"{time_sec:05.2f}s", fill="white", font=font)

    canvas.save(target, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--ffprobe", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.18)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    videos = sorted(args.source.glob("*.mp4"))
    for index, video in enumerate(videos, start=1):
        duration = duration_seconds(args.ffprobe, video)
        cuts = detect_cuts(args.ffmpeg, video, args.threshold)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            frames = []
            for frame_index, cut in enumerate(cuts):
                sample_time = min(cut + 0.08, max(0.0, duration - 0.04))
                frame_path = temp_path / f"{frame_index:03d}.jpg"
                extract_frame(args.ffmpeg, video, sample_time, frame_path)
                frames.append((cut, frame_path))
            output_name = f"video-{index:02d}-shots.jpg"
            contact_sheet(frames, args.output / output_name)

        records.append(
            {
                "id": index,
                "name": video.name,
                "duration": round(duration, 3),
                "candidate_shot_count": len(cuts),
                "candidate_cuts": [round(value, 3) for value in cuts],
                "contact_sheet": output_name,
                "threshold": args.threshold,
            }
        )

    (args.output / "shots.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
