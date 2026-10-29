# Software Requirements Specification (SRS)

## Scope

Convert 3D voxel volumes stored in NRRD format into an H.264 MP4 video sequence of 2D cross-sectional slices defined by 3-point (triangle) and 4-point (trapezoid) planes in a CSV file.

## Functional Requirements

- **FR-1:** Accept three positional CLI arguments (`nrrd_file`, `csv_file`, `mp4_file`) and optional flags (`--video-fps`, `--benchmark`, `--benchmark-seconds`) via `Ex0.py`.
- **FR-2:** Read a 3D NRRD volume with dimensions `< 1024` containing unsigned 8-, 16-, or 32-bit voxel values (`uint8`, `uint16`, `uint32`), or non-negative signed 16-bit (`int16`) values converted to `uint16`.
- **FR-3:** Read ordered plane definitions from a CSV file where each row begins with a point count (`3` or `4`) followed by 3 or 4 3D coordinates (`x, y, z`).
- **FR-4:** Validate isosceles triangular planes (`dist(a, b) == dist(a, c)`) and coplanar four-point trapezoids with equal-length side vectors (`dist(a_left, b_left) == dist(a_right, b_right)`). Skip planes that violate the equal-edge requirement with a warning; raise an error on malformed or degenerate inputs.
- **FR-5:** Sample the 3D volume at nearest-neighbor voxel coordinates (`floor(coord + 0.5)`); return `0` for out-of-volume coordinates.
- **FR-6:** Produce one 2D image per valid CSV row, preserving the original CSV order.
- **FR-7:** Scale intensities using the global volume minimum/maximum to 8-bit grayscale, center frames on a uniform even-dimension black canvas, and encode to an H.264 (`yuv420p`) MP4 file.
- **FR-8:** Optionally benchmark and report projection-only throughput in frames per second (FPS).

## Non-Functional Requirements

- **NFR-1:** Deterministic output for any given NRRD and CSV input.
- **NFR-2:** Modular separation between geometry/sampling (`projection/core.py`), file I/O (`projection/io.py`), and CLI/video generation (`projection/cli.py`).
- **NFR-3:** Automated `pytest` suite (`tests/test_projection.py`) covering triangle and trapezoid sampling, out-of-bounds handling, geometry validation, CSV parsing, and frame padding.
- **NFR-4:** Performance target of at least 30 projection FPS (100 FPS expected target), measurable via `--benchmark`.

## Input and Output Contracts

- **Volume array:** `volume[x, y, z]` loaded in Fortran index order, voxel-index coordinates, `uint8` / `uint16` / `uint32`.
- **CSV schema:** Optional header starting with `Number of Point`, followed by rows of `3,x1,y1,z1,x2,y2,z2,x3,y3,z3` (with optional trailing empty cells) or `4,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4`.
- **MP4 output:** 8-bit grayscale frames encoded with `libx264` (`yuv420p`), padded to uniform even dimensions matching the largest projected frame.
