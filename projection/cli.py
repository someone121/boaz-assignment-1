"""Command-line demo and video generation."""
import argparse
from pathlib import Path
import time
import numpy as np
from .core import project_triangle, project_trapezoid
from .io import load_nrrd, load_planes


def grayscale_uint8(image, low, high):
    if high <= low:
        return np.zeros(image.shape, dtype=np.uint8)
    scaled = (image.astype(np.float64) - low) * (255.0 / (high - low))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def pad_frame(image, target_height, target_width):
    """Pad to fixed even dimensions (required by common MP4 codecs)."""
    frame = np.zeros((target_height, target_width), dtype=np.uint8)
    h, w = image.shape
    y, x = (target_height-h)//2, (target_width-w)//2
    frame[y:y+h, x:x+w] = image
    return frame


def main(argv=None):
    parser = argparse.ArgumentParser(description='Create a video of arbitrary plane slices through a 3D NRRD volume')
    parser.add_argument('nrrd_file')
    parser.add_argument('csv_file')
    parser.add_argument('mp4_file')
    parser.add_argument('--video-fps', type=float, default=None)
    parser.add_argument('--benchmark', action='store_true', help='Benchmark projection throughput')
    parser.add_argument('--benchmark-seconds', type=float, default=3.0,
                        help='Minimum benchmark duration in seconds (default: 3)')
    args = parser.parse_args(argv)
    if args.video_fps is not None and args.video_fps <= 0:
        parser.error('--video-fps must be positive')
    if args.benchmark_seconds <= 0:
        parser.error('--benchmark-seconds must be positive')

    nrrd_name = Path(args.nrrd_file).stem
    volume, _ = load_nrrd(args.nrrd_file)
    planes = load_planes(args.csv_file, with_line_numbers=True)
    # Fixed global contrast: preserves comparability between frames.
    low, high = float(volume.min()), float(volume.max())
    images = []
    skipped = 0
    valid_planes = []
    projection_elapsed = 0.0
    for lineno, points in planes:
        kind = 'triangle' if len(points) == 3 else 'trapezoid'
        try:
            t0 = time.perf_counter()
            image = project_triangle(volume, *points) if len(points) == 3 else project_trapezoid(volume, *points)
            projection_elapsed += time.perf_counter() - t0
        except ValueError as exc:
            # Only skip violations of the isosceles/equal-edge requirement.
            message = str(exc)
            if ('must be isosceles' not in message and
                    'side vectors must have equal nonzero length' not in message):
                raise
            print(f'Warning: CSV line {lineno} describes a {kind} that is not isosceles '
                  f'and was therefore skipped. ({message})')
            skipped += 1
            continue
        images.append(image)
        valid_planes.append(points)
        if len(images) % 25 == 0:
            print(f'Projected {len(images)}/{len(planes)} {nrrd_name}')
    print(f'Processed: {len(images)} {nrrd_name}; Skipped: {skipped} {nrrd_name}')
    if not images:
        print('No valid planes to encode; no MP4 was created.')
        return 1
    measured_fps = len(images) / projection_elapsed if projection_elapsed > 0 else float(len(images))
    if args.benchmark:
        # Warm up projection functions outside the timed region.
        for points in valid_planes:
            if len(points) == 3:
                project_triangle(volume, *points)
            else:
                project_trapezoid(volume, *points)

        iterations = 0
        started = time.perf_counter()
        elapsed = 0.0
        while elapsed < args.benchmark_seconds:
            for points in valid_planes:
                if len(points) == 3:
                    project_triangle(volume, *points)
                else:
                    project_trapezoid(volume, *points)
                iterations += 1
            elapsed = time.perf_counter() - started
        measured_fps = iterations / elapsed
        print(f'Projection benchmark: {measured_fps:.2f} FPS '
              f'({iterations} projections in {elapsed:.3f}s)')
    video_fps = args.video_fps if args.video_fps is not None else round(measured_fps, 2)
    height = max(im.shape[0] for im in images)
    width = max(im.shape[1] for im in images)
    height += height % 2
    width += width % 2
    try:
        import imageio.v2 as imageio
    except ImportError as exc:
        raise RuntimeError('Install video dependencies: pip install -r requirements.txt') from exc
    with imageio.get_writer(args.mp4_file, fps=video_fps, codec='libx264', macro_block_size=1,
                            output_params=['-pix_fmt', 'yuv420p']) as writer:
        for im in images:
            writer.append_data(pad_frame(grayscale_uint8(im, low, high), height, width))
    fps_label = f'{video_fps:g}' if args.video_fps is not None else f'{video_fps:.2f}'
    print(f'Wrote {args.mp4_file}: {len(images)} frames, {width}x{height}, {fps_label} video FPS')
    return 0
