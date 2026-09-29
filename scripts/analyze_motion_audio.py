from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np


FRAME_RE = re.compile(r"^Frame\s+(\d+)\s+\(List\s+\d+\s+\[(.*)\]\)$")
LM_RE = re.compile(r"\(LM\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+\d+\s+[0-9.]+\s+[0-9.]+\)")


def run(command: list[str], *, binary: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=not binary,
        encoding=None if binary else "utf-8",
        errors=None if binary else "replace",
    )


def probe(ffprobe: Path, video: Path) -> dict:
    result = run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=avg_frame_rate,width,height:format=duration",
            "-of",
            "json",
            str(video),
        ]
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    numerator, denominator = stream["avg_frame_rate"].split("/")
    return {
        "duration": float(data["format"]["duration"]),
        "fps": float(numerator) / float(denominator),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
    }


def create_motion_file(ffmpeg: Path, video: Path, target: Path) -> None:
    escaped = str(target).replace("\\", "/").replace(":", "\\:")
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            f"scale=270:-2,vidstabdetect=shakiness=5:accuracy=9:fileformat=ascii:result='{escaped}'",
            "-an",
            "-f",
            "null",
            "NUL",
        ]
    )


def robust_affine(points: np.ndarray, vectors: np.ndarray) -> tuple[np.ndarray, float, float]:
    design = np.column_stack([points[:, 0], points[:, 1], np.ones(len(points))])
    coeff_x = np.linalg.lstsq(design, vectors[:, 0], rcond=None)[0]
    coeff_y = np.linalg.lstsq(design, vectors[:, 1], rcond=None)[0]
    predicted = np.column_stack([design @ coeff_x, design @ coeff_y])
    residual = np.linalg.norm(vectors - predicted, axis=1)
    median = float(np.median(residual))
    mad = float(np.median(np.abs(residual - median)))
    limit = max(1.25, median + 2.5 * max(mad, 0.1))
    inliers = residual <= limit
    if int(inliers.sum()) >= 8:
        design = design[inliers]
        vectors = vectors[inliers]
        coeff_x = np.linalg.lstsq(design, vectors[:, 0], rcond=None)[0]
        coeff_y = np.linalg.lstsq(design, vectors[:, 1], rcond=None)[0]
    coefficients = np.vstack([coeff_x, coeff_y])
    return coefficients, float(inliers.mean()), median


def parse_motion(path: Path, width: int, height: int) -> dict[int, dict]:
    frames: dict[int, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = FRAME_RE.match(line)
        if not match:
            continue
        frame_number = int(match.group(1))
        fields = LM_RE.findall(match.group(2))
        if len(fields) < 8:
            continue
        values = np.asarray([[int(value) for value in field] for field in fields], dtype=float)
        vectors = values[:, :2]
        points = values[:, 2:4]
        coefficients, coherence, residual = robust_affine(points, vectors)
        center = np.asarray([width / 2, height / 2, 1.0])
        center_motion = coefficients @ center
        scale = float((coefficients[0, 0] + coefficients[1, 1]) / 2)
        rotation = float((coefficients[1, 0] - coefficients[0, 1]) / 2)
        frames[frame_number] = {
            "tx": float(center_motion[0]),
            "ty": float(center_motion[1]),
            "scale": scale,
            "rotation": rotation,
            "coherence": coherence,
            "residual": residual,
        }
    return frames


def classify_motion(values: list[dict], frame_width: int, frame_height: int) -> dict:
    if not values:
        return {"label": "insufficient-motion-data", "confidence": 0.0}
    tx = np.asarray([value["tx"] for value in values])
    ty = np.asarray([value["ty"] for value in values])
    scale = np.asarray([value["scale"] for value in values])
    rotation = np.asarray([value["rotation"] for value in values])
    coherence = float(np.median([value["coherence"] for value in values]))
    magnitude = np.hypot(tx, ty)
    motion_energy = float(np.median(magnitude))
    direction_consistency = float(np.hypot(tx.sum(), ty.sum()) / max(magnitude.sum(), 1e-6))
    median_tx = float(np.median(tx))
    median_ty = float(np.median(ty))
    median_scale = float(np.median(scale))
    median_rotation = float(np.median(rotation))
    zoom_edge_motion = abs(median_scale) * math.hypot(frame_width / 2, frame_height / 2)
    rotation_edge_motion = abs(median_rotation) * math.hypot(frame_width / 2, frame_height / 2)

    if motion_energy < 0.35 and zoom_edge_motion < 0.35 and rotation_edge_motion < 0.35:
        label = "stable-or-very-subtle"
    elif coherence < 0.55 or direction_consistency < 0.35:
        label = "mixed-subject-motion-or-complex-parallax"
    elif zoom_edge_motion > max(0.7, motion_energy * 0.8):
        label = "push-pull-or-optical-scale-change"
    elif rotation_edge_motion > max(0.7, motion_energy * 0.8):
        label = "roll-or-orbit-like-motion"
    elif abs(median_tx) > abs(median_ty) * 1.35:
        label = "lateral-pan-or-track"
    elif abs(median_ty) > abs(median_tx) * 1.35:
        label = "vertical-tilt-or-rise"
    else:
        label = "diagonal-or-combined-translation"

    confidence = min(1.0, coherence * (0.55 + 0.45 * direction_consistency))
    return {
        "label": label,
        "confidence": round(confidence, 3),
        "motion_px_per_frame": round(motion_energy, 3),
        "median_image_dx": round(median_tx, 3),
        "median_image_dy": round(median_ty, 3),
        "scale_per_frame": round(median_scale, 6),
        "rotation_per_frame": round(median_rotation, 6),
        "coherence": round(coherence, 3),
        "direction_consistency": round(direction_consistency, 3),
    }


def decode_audio(ffmpeg: Path, video: Path, sample_rate: int = 11025) -> np.ndarray:
    result = run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "f32le",
            "pipe:1",
        ],
        binary=True,
    )
    return np.frombuffer(result.stdout, dtype=np.float32)


def audio_features(audio: np.ndarray, sample_rate: int = 11025) -> dict:
    frame_size = 1024
    hop = 256
    if len(audio) < frame_size:
        return {"estimated_bpm": None, "transient_times": [], "rms_times": [], "rms": []}
    frame_count = 1 + (len(audio) - frame_size) // hop
    window = np.hanning(frame_size).astype(np.float32)
    flux = np.zeros(frame_count, dtype=float)
    rms = np.zeros(frame_count, dtype=float)
    previous = None
    for index in range(frame_count):
        frame = audio[index * hop : index * hop + frame_size]
        rms[index] = float(np.sqrt(np.mean(frame * frame) + 1e-12))
        spectrum = np.log1p(np.abs(np.fft.rfft(frame * window)))
        if previous is not None:
            flux[index] = float(np.mean(np.maximum(spectrum - previous, 0.0)))
        previous = spectrum
    envelope = np.convolve(flux, np.ones(3) / 3, mode="same")
    local_window = max(3, int(round(0.35 * sample_rate / hop)))
    peaks: list[int] = []
    last_peak = -local_window
    threshold = float(np.percentile(envelope, 67) + 0.25 * np.std(envelope))
    for index in range(1, len(envelope) - 1):
        if envelope[index] <= threshold or envelope[index] < envelope[index - 1] or envelope[index] < envelope[index + 1]:
            continue
        if index - last_peak < local_window:
            if peaks and envelope[index] > envelope[peaks[-1]]:
                peaks[-1] = index
                last_peak = index
            continue
        peaks.append(index)
        last_peak = index

    normalized = envelope - envelope.mean()
    minimum_lag = max(1, int(round(60 / 180 * sample_rate / hop)))
    maximum_lag = min(len(normalized) - 1, int(round(60 / 60 * sample_rate / hop)))
    bpm = None
    if maximum_lag > minimum_lag:
        correlations = [float(np.dot(normalized[:-lag], normalized[lag:])) for lag in range(minimum_lag, maximum_lag + 1)]
        best_lag = minimum_lag + int(np.argmax(correlations))
        bpm = 60 * sample_rate / (hop * best_lag)

    times = np.arange(frame_count) * hop / sample_rate
    stride = max(1, int(round(0.1 * sample_rate / hop)))
    return {
        "estimated_bpm": round(float(bpm), 1) if bpm else None,
        "transient_times": [round(float(index * hop / sample_rate), 3) for index in peaks],
        "rms_times": [round(float(value), 3) for value in times[::stride]],
        "rms": [round(float(value), 6) for value in rms[::stride]],
    }


def nearest_distance(time_sec: float, events: list[float]) -> float | None:
    if not events:
        return None
    return min(abs(time_sec - event) for event in events)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("shots_json", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--ffprobe", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    shot_records = json.loads(args.shots_json.read_text(encoding="utf-8"))
    videos = sorted(args.source.glob("*.mp4"))
    output_records = []
    for index, (video, shot_record) in enumerate(zip(videos, shot_records), start=1):
        metadata = probe(args.ffprobe, video)
        motion_path = args.output / f"video-{index:02d}-motion.trf"
        create_motion_file(args.ffmpeg, video, motion_path)
        scaled_height = round(metadata["height"] * 270 / metadata["width"])
        motion_frames = parse_motion(motion_path, 270, scaled_height)
        audio = audio_features(decode_audio(args.ffmpeg, video))
        cuts = [float(value) for value in shot_record["candidate_cuts"]]
        boundaries = cuts + [metadata["duration"]]
        shots = []
        for shot_index, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:]), start=1):
            trim = min(0.12, max(0.0, (end - start) * 0.15))
            first_frame = int(math.ceil((start + trim) * metadata["fps"])) + 1
            last_frame = int(math.floor((end - trim) * metadata["fps"])) + 1
            values = [motion_frames[frame] for frame in range(first_frame, last_frame + 1) if frame in motion_frames]
            motion = classify_motion(values, 270, scaled_height)
            distance = nearest_distance(start, audio["transient_times"]) if start > 0 else None
            shots.append(
                {
                    "shot": shot_index,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "duration": round(end - start, 3),
                    "motion": motion,
                    "cut_to_nearest_audio_transient_ms": round(distance * 1000) if distance is not None else None,
                }
            )

        cut_distances = [
            nearest_distance(cut, audio["transient_times"])
            for cut in cuts[1:]
        ]
        valid_distances = [distance for distance in cut_distances if distance is not None]
        output_records.append(
            {
                "id": index,
                "name": video.name,
                "duration": round(metadata["duration"], 3),
                "fps": round(metadata["fps"], 3),
                "estimated_bpm": audio["estimated_bpm"],
                "audio_transient_count": len(audio["transient_times"]),
                "cuts_within_80ms_of_transient_pct": round(100 * sum(distance <= 0.08 for distance in valid_distances) / max(1, len(valid_distances)), 1),
                "cuts_within_120ms_of_transient_pct": round(100 * sum(distance <= 0.12 for distance in valid_distances) / max(1, len(valid_distances)), 1),
                "audio": audio,
                "shots": shots,
            }
        )

    target = args.output / "motion-audio.json"
    target.write_text(json.dumps(output_records, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = [
        {
            "id": record["id"],
            "duration": record["duration"],
            "estimated_bpm": record["estimated_bpm"],
            "audio_transient_count": record["audio_transient_count"],
            "cuts_within_80ms_pct": record["cuts_within_80ms_of_transient_pct"],
            "cuts_within_120ms_pct": record["cuts_within_120ms_of_transient_pct"],
        }
        for record in output_records
    ]
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
