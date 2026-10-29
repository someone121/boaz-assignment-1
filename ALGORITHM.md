# Projection Algorithm — Detailed Specification

## 1. Coordinate System and Volume Representation

- **Volume layout:** The 3D NRRD volume is loaded with Fortran axis ordering (`index_order='F'`) so that array indexing matches `volume[x, y, z]`.
- **Supported data types:** `uint8`, `uint16`, `uint32` (and non-negative `int16`, which is cast to `uint16` on load). All dimensions must be in `[1, 1023]`.
- **Coordinate space:** Plane vertices are represented as `Point3D(x, y, z)` in floating-point voxel index coordinates (`float64`).

---

## 2. Row-Wise Segment Sampling (`_sample_row`)

Both triangle and trapezoid projections sample one horizontal row `row` at a time between a 3D `start` point and a 3D `end` point into an output array `out` of fixed `width`:

1. Compute segment length `distance = norm(end - start)`.
2. Determine sample count: `count = min(width, floor(distance) + 1)`.
3. Compute unit direction vector:
   - `direction = (end - start) / distance` if `distance > 1e-12`, else `[0, 0, 0]`.
4. Generate `count` sample positions along the segment:
   - `positions[k] = start + k * direction` for `k = 0, 1, ..., count - 1`.
5. Round to nearest-neighbor integer voxel coordinates:
   - `coords = floor(positions + 0.5)` as 64-bit integers.
6. Check bounds for each coordinate `(cx, cy, cz)`:
   - Valid if `0 <= cx < shape[0]`, `0 <= cy < shape[1]`, and `0 <= cz < shape[2]`.
   - In-bounds coordinates read `volume[cx, cy, cz]`; out-of-bounds coordinates evaluate to `0`.
7. Center the `count` samples horizontally in row `row` of `out`:
   - `offset = (width - count) // 2`
   - `out[row, offset : offset + count] = values`

All steps within a row are vectorized in NumPy without per-pixel Python loops.

---

## 3. Three-Point Plane: Isosceles Triangle (`project_triangle`)

Given 3D points `a` (apex), `b` (left endpoint), and `c` (right endpoint) from CSV columns `(x1,y1,z1)`, `(x2,y2,z2)`, `(x3,y3,z3)`:

1. Compute edge lengths:
   - `Dab = norm(b - a)`
   - `Dac = norm(c - a)`
   - `Dbc = norm(c - b)`
2. Validate geometry:
   - Reject degenerate triangles if `min(Dab, Dac, Dbc) <= 1e-12`.
   - Require isosceles sides: `isclose(Dab, Dac, rtol=1e-5, atol=1e-5)`.
   - Reject collinear points if `norm(cross(b - a, c - a)) <= 1e-10 * Dab * Dac`.
3. Compute output dimensions and allocate image:
   - `height = max(1, ceil(Dab))`
   - `width = max(1, ceil(Dbc) + 1)`
   - `output = zeros((height, width), dtype=volume.dtype)`
4. Compute unit side vectors:
   - `vab = (b - a) / Dab`
   - `vac = (c - a) / Dac`
5. Sample rows for `y = 0, ..., height - 1`:
   - `step = min(y + 1, Dab)` (reproduces the assignment pseudocode's advance-before-sampling order, omitting the apex at `step = 0`).
   - `start = a + step * vab`
   - `end = a + step * vac`
   - Call `_sample_row(volume, start, end, width, y, output)`.

---

## 4. Four-Point Plane: Coplanar Trapezoid (`project_trapezoid`)

Given 3D points `a_left`, `a_right`, `b_left`, `b_right` from CSV columns `(x1,y1,z1)` through `(x4,y4,z4)`:

1. Define side vectors and lengths:
   - `left = b_left - a_left`, `dl = norm(left)`
   - `right = b_right - a_right`, `dr = norm(right)`
2. Validate geometry:
   - Require equal non-zero side lengths: `min(dl, dr) > 1e-12` and `isclose(dl, dr, rtol=1e-5, atol=1e-5)`.
   - Compute plane normal `normal = cross(a_right - a_left, left)` and `norm = norm(normal)`.
   - Reject zero-area shapes if `norm <= 1e-12`.
   - Require coplanarity: `abs(dot(b_right - a_left, normal)) <= 1e-5 * norm * max(1.0, norm(b_right - a_left))`.
3. Compute output dimensions and allocate image:
   - `height = max(1, ceil(dl))`
   - `max_width = max(norm(a_right - a_left), norm(b_right - b_left))`
   - `width = max(1, ceil(max_width) + 1)`
   - `output = zeros((height, width), dtype=volume.dtype)`
4. Sample rows for `y = 0, ..., height - 1`:
   - `t = min((y + 1) / dl, 1.0)`
   - `start = a_left + t * left`
   - `end = a_right + t * right`
   - Call `_sample_row(volume, start, end, width, y, output)`.

---

## 5. Normalization, Padding, and Video Encoding (`projection/cli.py`)

1. **Plane filtering:** Each plane from the CSV is projected in sequence. If `project_triangle` or `project_trapezoid` raises a `ValueError` due to the isosceles or equal side-length check, the CLI logs a warning with the CSV line number and skips that plane.
2. **Global intensity scaling (`grayscale_uint8`):**
   - Let `low = volume.min()` and `high = volume.max()`.
   - If `high <= low`, all output pixels are `0`.
   - Otherwise, each projected frame is linearly mapped via `clip((image - low) * (255.0 / (high - low)), 0, 255)` and cast to `uint8`.
3. **Uniform canvas padding (`pad_frame`):**
   - Compute the maximum height `H` and maximum width `W` across all valid projected frames.
   - Round both `H` and `W` up to the next even integer (`H += H % 2`, `W += W % 2`) for H.264 macroblock/chroma compatibility.
   - Center each `h × w` frame at `(y, x) = ((H - h) // 2, (W - w) // 2)` on a zero-filled `H × W` canvas.
4. **MP4 encoding:** Frames are written sequentially using `imageio` with `codec='libx264'`, `macro_block_size=1`, and `-pix_fmt yuv420p`.

---

## 6. Complexity Analysis

- **Time complexity per plane:** For a projected image of height $H$ and width $W$, the outer loop runs $H$ times and each vectorized row step processes at most $W$ points, yielding $\mathcal{O}(H \cdot W)$ time per plane.
- **Space complexity:**
  - Input volume: $\mathcal{O}(S_x \cdot S_y \cdot S_z)$.
  - Temporary per-row buffers: $\mathcal{O}(W)$.
  - Output image per plane: $\mathcal{O}(H \cdot W)$. All valid projected frames are held in memory prior to encoding.

---

## 7. Known Differences from Literal Assignment Pseudocode

- **Array indexing:** Output images use standard NumPy `[row, column]` (`[y, x]`) layout rather than `E[x][y]`.
- **Integer dimensions and clamping:** The assignment pseudocode uses floating-point distances directly as array dimensions and loop bounds; the implementation uses `ceil` for array dimensions and clamps the final step (`min(y + 1, Dab)` and `min((y + 1) / dl, 1.0)`) so sampling never overshoots the endpoints.
- **Distinct variable names:** The assignment reuses `p` for both the plane and the sample point; the code separates plane vertices (`a, b, c`) from sample coordinates (`positions, coords`).
