# Exercise 1 — 3D Volume Plane Projection

A Python implementation of the assignment's row-wise triangular plane sampling algorithm, extended to four-point trapezoids. It reads a 3D NRRD volume, samples a 2D slice for each valid plane defined in a CSV file, and encodes the resulting frames into an H.264 MP4 video.

## Installation

Requires Python 3.10+ and FFmpeg (provided automatically via `imageio-ffmpeg`).

```bash
python -m pip install -r requirements.txt
```

## Usage

Run the projection CLI via `Ex0.py`:

```bash
python Ex0.py <nrrd_file> <csv_file> <mp4_file> [--video-fps FPS] [--benchmark] [--benchmark-seconds SECONDS]
```

Examples:

```bash
python Ex0.py scan.nrrd planes.csv output.mp4
python Ex0.py scan.nrrd planes.csv output.mp4 --video-fps 15 --benchmark --benchmark-seconds 3
python -m pytest -q
```

### CLI Arguments

- `nrrd_file`: Path to input 3D NRRD volume file.
- `csv_file`: Path to input CSV file containing 3-point (triangle) or 4-point (trapezoid) plane definitions.
- `mp4_file`: Output path for the encoded `.mp4` video.
- `--video-fps`: Output video frame rate (default: `15`, must be positive).
- `--benchmark`: Run a projection throughput benchmark after processing the CSV planes.
- `--benchmark-seconds`: Minimum duration in seconds for the benchmark loop (default: `3.0`, must be positive).

### CSV Format

Header (optional): `Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4` (rows starting with `#` or `Number of Point` and blank rows are ignored).
Each data row begins with `3` or `4`, followed by the corresponding 3D point coordinates (`x, y, z` per point):

- **Triangle (`3` points):** Requires 9 coordinate values (`x1,y1,z1` through `x3,y3,z3`). Trailing empty cells for the 4th point are permitted.
  - Point 1 is the apex `a`, Point 2 is endpoint `b`, and Point 3 is endpoint `c`.
  - The two side vectors `a -> b` and `a -> c` must have equal non-zero length (`dist(a, b) == dist(a, c)` within tolerance `1e-5`), and the three points must not be collinear.
- **Trapezoid (`4` points):** Requires 12 coordinate values (`x1,y1,z1` through `x4,y4,z4`).
  - Point 1 is `a_left`, Point 2 is `a_right`, Point 3 is `b_left`, and Point 4 is `b_right`.
  - The two side vectors are `a_left -> b_left` (Point 1 → Point 3) and `a_right -> b_right` (Point 2 → Point 4). They must have equal non-zero length, the four points must be coplanar, and the trapezoid must have non-zero area.
  - Rows progress from the `a_left`–`a_right` edge toward the `b_left`–`b_right` edge.

One valid CSV row produces one video frame, preserving the CSV row order. Planes that violate the isosceles (`dist(a, b) == dist(a, c)`) or equal side-length (`dist(a_left, b_left) == dist(a_right, b_right)`) requirement are skipped with a warning printed to stdout; other geometry or formatting errors raise a `ValueError`.

### Algorithm Summary

- **Triangles:** Computes unit vectors from apex `a` to endpoints `b` and `c`. Advances along both sides by 1 voxel per output row (`step = min(y + 1, Dab)`), samples along the connecting segment at 1-voxel steps using NumPy vectorization, and centers each sampled row horizontally in the 2D output matrix.
- **Trapezoids:** Interpolates corresponding endpoints along the two equal-length side vectors `a_left -> b_left` and `a_right -> b_right` at `t = min((y + 1) / dl, 1.0)` for each row `y`, then samples across the connecting segment and centers the row horizontally.

### Assumptions and Implementation Details

- **Volume format:** NRRD must be 3D with dimensions `< 1024`. Unsigned 8-, 16-, and 32-bit integer types (`uint8`, `uint16`, `uint32`) are supported directly; non-negative signed 16-bit (`int16`) volumes are automatically converted to `uint16` (negative values raise a `ValueError`).
- **Indexing:** `pynrrd` reads the array with `index_order='F'` so the volume is addressed as `volume[x, y, z]`.
- **Coordinate space:** Plane coordinates are interpreted directly as **voxel indices**; NRRD physical spacing, origin, and direction headers are not applied.
- **Sampling:** Nearest-neighbor sampling rounds coordinates via `floor(coord + 0.5)`. Coordinates outside the volume bounds return `0`.
- **Advance-before-sampling:** Following the assignment's pseudocode, both side positions advance before sampling row `0` (`step = min(y + 1, ...)`), omitting the exact apex/starting edge at step `0`.
- **Dimensions and rounding:** Non-integer side lengths are rounded **up** (`ceil`) to determine image height (`max(1, ceil(side_length))`), and image width is `max(1, ceil(base_or_max_width) + 1)`. The final side step is clamped to the endpoint.
- **Contrast and framing:** Voxel intensities are linearly scaled to 8-bit grayscale (`uint8`) using the **global minimum and maximum of the entire input volume**. Variable-size frames are centered on a black (`0`) canvas sized to the largest frame's height and width, rounded up to even dimensions for H.264 (`yuv420p`) compatibility.

## Project Structure

```text
├── Ex0.py                      # Command-line entry point
├── projection/
│   ├── __init__.py             # Package docstring
│   ├── cli.py                  # CLI argument parsing, plane processing, benchmarking, and MP4 encoding
│   ├── core.py                 # Point3D model, vector geometry, and vectorized row-wise sampling
│   └── io.py                   # NRRD volume loading and CSV plane parsing
├── tests/
│   └── test_projection.py      # Unit tests for triangle/trapezoid projection, CSV parsing, and frame padding
├── ALGORITHM.md                # Detailed mathematical and algorithmic specification
├── README.md                   # Project overview and usage instructions
├── SRS.md                      # Software Requirements Specification
└── requirements.txt            # Python package dependencies
```

## Performance Benchmarking

The CLI includes an optional benchmark mode (`--benchmark`) that measures pure 3D-to-2D projection throughput (excluding NRRD loading, CSV parsing, and MP4 encoding).

### Running the Benchmark

```bash
python Ex0.py input.nrrd planes.csv output.mp4 --benchmark
```

By default, the benchmark runs for at least 3 seconds after a warm-up pass over all valid planes. To specify a custom duration:

```bash
python Ex0.py input.nrrd planes.csv output.mp4 --benchmark --benchmark-seconds 10
```

### Example Results

Preliminary benchmark using `MRHead_1.nrrd` (`256 × 256 × 130` voxels):

| Metric | Result |
|---|---|
| Benchmark duration | 3.011 seconds |
| Projections completed | 158 |
| Average projection throughput | 52.48 FPS |
| Average time per projection | 19.05 ms |
| Minimum performance requirement | 30 FPS |
| Expected performance target | 100 FPS |
