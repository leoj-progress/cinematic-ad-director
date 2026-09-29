from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np


def fit_frame(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    scale = min(width / frame.shape[1], height / frame.shape[0])
    resized = cv2.resize(
        frame,
        (max(1, round(frame.shape[1] * scale)), max(1, round(frame.shape[0] * scale))),
        interpolation=cv2.INTER_AREA,
    )
    y = (height - resized.shape[0]) // 2
    x = (width - resized.shape[1]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def main() -> None:
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    records = []

    for index, video in enumerate(sorted(source.glob("*.mp4")), start=1):
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps else 0
        sample_count = 12
        times = np.linspace(0, max(0, duration - 0.05), sample_count)
        tiles = []

        for time_sec in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(time_sec * 1000))
            ok, frame = cap.read()
            if not ok:
                frame = np.zeros((height or 360, width or 640, 3), dtype=np.uint8)
            tile = fit_frame(frame, 300, 360)
            cv2.rectangle(tile, (0, 324), (300, 360), (0, 0, 0), -1)
            cv2.putText(
                tile,
                f"{time_sec:.1f}s",
                (10, 348),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            tiles.append(tile)

        cap.release()
        rows = [np.hstack(tiles[i : i + 4]) for i in range(0, sample_count, 4)]
        sheet = np.vstack(rows)
        output_name = f"video-{index:02d}-contact.jpg"
        cv2.imwrite(str(output / output_name), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
        records.append(
            {
                "id": index,
                "name": video.name,
                "duration": round(duration, 3),
                "fps": round(fps, 3),
                "width": width,
                "height": height,
                "contact_sheet": output_name,
            }
        )

    (output / "metadata.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
