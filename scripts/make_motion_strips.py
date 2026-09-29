from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True)


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
            "scale=220:-2",
            "-y",
            str(target),
        ]
    )


def choose_shots(shots: list[dict], maximum: int) -> list[dict]:
    eligible = [shot for shot in shots if shot["duration"] >= 0.6]
    if len(eligible) <= maximum:
        return eligible
    indexes = np.linspace(0, len(eligible) - 1, maximum).round().astype(int)
    return [eligible[index] for index in sorted(set(indexes))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("analysis_json", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--maximum", type=int, default=16)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    records = json.loads(args.analysis_json.read_text(encoding="utf-8"))
    videos = sorted(args.source.glob("*.mp4"))
    font = ImageFont.load_default(size=17)
    for video_index, (video, record) in enumerate(zip(videos, records), start=1):
        shots = choose_shots(record["shots"], args.maximum)
        tile_width = 220
        frame_height = 391
        label_height = 48
        canvas = Image.new("RGB", (tile_width * 4, (frame_height + label_height) * len(shots)), "#111111")
        draw = ImageDraw.Draw(canvas)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            for row, shot in enumerate(shots):
                start = float(shot["start"])
                duration = float(shot["duration"])
                times = [start + duration * fraction for fraction in (0.12, 0.38, 0.64, 0.9)]
                for column, time_sec in enumerate(times):
                    frame_path = temp / f"{row:02d}-{column}.jpg"
                    extract_frame(args.ffmpeg, video, time_sec, frame_path)
                    frame = Image.open(frame_path).convert("RGB")
                    frame.thumbnail((tile_width, frame_height))
                    x = column * tile_width + (tile_width - frame.width) // 2
                    y = row * (frame_height + label_height)
                    canvas.paste(frame, (x, y))
                    draw.text((column * tile_width + 6, y + frame_height + 4), f"{time_sec:.2f}s", fill="white", font=font)
                label = f"S{shot['shot']} {start:.2f}-{shot['end']:.2f}s | {shot['motion']['label']}"
                draw.text((6, row * (frame_height + label_height) + frame_height + 24), label, fill="#e6c66a", font=font)
        canvas.save(args.output / f"video-{video_index:02d}-motion-strips.jpg", quality=91)


if __name__ == "__main__":
    main()
