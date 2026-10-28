"""Command-line demo and video generation."""
import argparse
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
    parser.add_argument('--video-fps', type=int, default=15)
    parser.add_argument('--benchmark', action='store_true', help='Benchmark projection throughput')
    parser.add_argument('--benchmark-seconds', type=float, default=3.0,
                        help='Minimum benchmark duration in seconds (default: 3)')
    args = parser.parse_args(argv)
    if args.video_fps <= 0:
        parser.error('--video-fps must be positive')
    if args.benchmark_seconds <= 0:
        parser.error('--benchmark-seconds must be positive')

    volume, _ = load_nrrd(args.nrrd_file)
    planes = load_planes(args.csv_file, with_line_numbers=True)
    # Fixed global contrast: preserves comparability between frames.
    low, high = float(volume.min()), float(volume.max())
    images = []
    skipped = 0
    valid_planes = []
    for lineno, points in planes:
        kind = 'triangle' if len(points) == 3 else 'trapezoid'
        try:
            image = project_triangle(volume, *points) if len(points) == 3 else project_trapezoid(volume, *points)
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
            print(f'Projected {len(images)}/{len(planes)} planes')
    print(f'Processed: {len(images)} planes; Skipped: {skipped} planes')
    if not images:
        print('No valid planes to encode; no MP4 was created.')
        return 1
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
        print(f'Projection benchmark: {iterations / elapsed:.2f} FPS '
              f'({iterations} projections in {elapsed:.3f}s)')
    height = max(im.shape[0] for im in images)
    width = max(im.shape[1] for im in images)
    height += height % 2
    width += width % 2
    try:
        import imageio.v2 as imageio
    except ImportError as exc:
        raise RuntimeError('Install video dependencies: pip install -r requirements.txt') from exc
    with imageio.get_writer(args.mp4_file, fps=args.video_fps, codec='libx264', macro_block_size=1,
                            output_params=['-pix_fmt', 'yuv420p']) as writer:
        for im in images:
            writer.append_data(pad_frame(grayscale_uint8(im, low, high), height, width))
    print(f'Wrote {args.mp4_file}: {len(images)} frames, {width}x{height}, {args.video_fps} video FPS')
    return 0
