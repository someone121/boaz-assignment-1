# Projection algorithm — detailed design

## Three-point plane (triangle)

Given 3D points `a,b,c` with `norm(b-a) == norm(c-a)`:

1. Compute `Dab=norm(b-a)`, `Dac=norm(c-a)`, `Dbc=norm(c-b)`.
2. Reject zero-length or collinear triangles and unequal `Dab`, `Dac`.
3. Compute unit side vectors `u=(b-a)/Dab`, `v=(c-a)/Dac`.
4. Create a zero-filled image of height `ceil(Dab)` and width `ceil(Dbc)+1`.
5. For each row `y` from 0 to height-1, let `step=min(y+1,Dab)`. This reproduces the assignment's advance-before-sampling order.
6. Compute `left=a+step*u` and `right=a+step*v`.
7. Let `d=norm(right-left)`; sample `min(width,floor(d)+1)` positions at `left + x*(right-left)/d` for `x=0,1,...`, or the sole `left` point when `d=0`.
8. Round each sample coordinate with `floor(coord+0.5)`. If all three indices are within bounds, read `volume[x,y,z]`; otherwise use 0.
9. Center the samples horizontally within the output row and return the matrix.

This uses NumPy vectorized sampling per row, rather than a Python loop per pixel.

## Four-point plane (trapezoid)

The assignment mentions two equal-length vectors but does not specify CSV ordering. Define `a_left, a_right, b_left, b_right`, with side vectors `a_left->b_left` and `a_right->b_right`. Validate equal nonzero side lengths and coplanarity. For each row interpolate corresponding positions along these sides, then sample across the connecting segment as above.

## Complexity

Let output image dimensions be H by W. Runtime is O(HW) and temporary row memory is O(W); output memory is O(HW). Input volume occupies O(sx*sy*sz). Video generation currently holds all projected images in memory, proportional to their total pixel counts.

## Precision and implementation choices

- Nearest-neighbor sampling rather than trilinear interpolation.
- Use double-precision vectors and integer indices for reads.
- Out-of-bounds voxel values are 0 as specified by the assignment.
- For non-integer side lengths, output size is rounded up and final side steps are clamped.
- A trapezoid's two cross-sections need not have equal widths; center each row in a fixed-width image.

## Known differences from literal pseudocode

- Image array layout is `[row,column]`, not `E[x][y]`.
- The supplied pseudocode uses floating-point distances as array sizes and loop bounds; integer conventions are necessary.
- The assignment says `x1 <= d12`, but fractional endpoints require a rounding policy.
- The assignment's `p` notation is reused for plane and sample point; code uses distinct names.


CSV input: The lecturer-provided CSV begins with `Number of Point`, then x1,y1,z1 through x4,y4,z4. Each row contains 3 or 4 points; unused final fields may be empty.
