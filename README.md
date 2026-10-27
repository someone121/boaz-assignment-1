# Exercise 1 — 3D volume plane projection

A Python implementation of the assignment's row-wise triangular plane sampling algorithm, extended to a four-point trapezoid. It reads a 3D NRRD file, samples a plane for each CSV row, and writes one MP4 frame per plane.

## Installation

Requires Python 3.10+ and FFmpeg provided by `imageio-ffmpeg`.

```bash
python -m pip install -r requirements.txt
```

## Usage

```bash
python Ex0.py scan.nrrd planes.csv output.mp4 --benchmark
python -m pytest -q
```

### CSV format (provided by the lecturer)

Header: `Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4`.
Each row begins with `3` or `4`, followed by the corresponding 3D point coordinates.
Three-point rows may leave the final three cells blank. See `example_planes.csv`,
which reproduces the four plane definitions from the provided screenshot.

For a triangle, points 1, 2, 3 are apex `a`, endpoint `b`, endpoint `c`.
For a four-point region, points 1→2 and 3→4 are the two equal-length
side vectors. The algorithm requires coplanar points.

One CSV row produces one frame, in the same order.
Coordinates are interpreted as voxel indices rather than physical millimeters.

### Algorithm

For triangles, compute normalized vectors from apex `a` to endpoints `b` and `c`. Advance along both sides by one voxel per output row, sample along the connecting segment at one-voxel steps, and center each row in the 2D image. This closely follows page 2 of the assignment, with necessary integer-size and rounding conventions. For trapezoids, interpolate between corresponding ends of the two equal-length sides.

### Assumptions and limitations

- NRRD must contain 3 dimensions and unsigned 8/16/32-bit data, with each dimension <1024.
- `pynrrd` reads the array with `index_order='F'` so the volume is addressed as `[x,y,z]`.
- Coordinates refer to **voxel indices**; NRRD physical spacing/origin/direction are not applied.
- Nearest-neighbor sampling rounds `floor(coord + 0.5)`; points outside the volume return zero.
- The assignment's pseudocode increments `a1` and `a2` before sampling; this implementation follows that convention, so the exact apex pixel is not included in the first row.
- Non-integer lengths are rounded **up** to determine output dimensions; the last side step is clamped to the endpoint.
- Different-size frames are centered on a black canvas sized to the largest frame, with even dimensions for H.264.
- Unsigned voxel intensities are converted to 8-bit grayscale using the **global min and max of the input volume**; zero is not necessarily black when the volume minimum is nonzero. Padding is black.
- No GUI, interpolation, physical-space orientation, or 4D NRRD support.
- Frames are currently kept in memory before MP4 encoding. For very long CSVs, consider a streaming/two-pass design.
- The project has not been benchmarked on your hardware or on a 500³ NRRD; do not claim it meets the assignment's 30/100 FPS targets without measuring.

## Project structure

- `Ex0.py`: command-line entry point
- `projection/core.py`: vector geometry and row-wise sampling
- `projection/io.py`: NRRD and CSV parsing
- `projection/cli.py`: processing and MP4 encoding
- `tests/`: automated unit tests
- `SRS.md`: requirements and design choices
- `ALGORITHM.md`: detailed algorithm specification
- `EXPERIMENT.md`: experiment template to complete after testing

## Performance

Use `--benchmark` to print **projection-only FPS**. It excludes NRRD loading, CSV reading, image normalization, and video encoding. Test on your actual hardware and dataset. The assignment expects at least 30 FPS and targets 100 FPS for a 500³ volume; this code is a baseline rather than a proven optimized solution.
