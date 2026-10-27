# Software Requirements Specification (draft)

## Scope
Convert 3D unsigned voxel volumes stored in NRRD into an MP4 sequence of 2D samples at planes specified in a CSV file. No interactive GUI is required.

## Functional requirements

- FR-1: Accept exactly three positional CLI arguments: input NRRD, input CSV, output MP4.
- FR-2: Read a 3D NRRD with unsigned 8-, 16-, or 32-bit voxel values.
- FR-3: Read ordered plane definitions consisting of 3 or 4 XYZ points.
- FR-4: Validate isosceles triangular planes; support the documented four-point trapezoid convention.
- FR-5: Sample the 3D volume at nearest-neighbor coordinates; out-of-volume samples produce zero.
- FR-6: Produce one 2D image per CSV row, in original order.
- FR-7: Write all frames to a playable MP4 with a fixed frame size.
- FR-8: Report invalid inputs with actionable errors.
- FR-9: Optionally print projection-only FPS.

## Non-functional requirements

- NFR-1: Stable and deterministic output for a given input.
- NFR-2: Clear separation between geometry, input parsing, and video generation.
- NFR-3: Automated tests for geometry, boundary conditions, parsing, and frame formatting.
- NFR-4: Performance goal: >=30 projection frames/second for the assignment's benchmark; 100 FPS expected. Must be validated empirically.

## Input and output contracts

- Volume array: `volume[x,y,z]`, voxel-index coordinates, unsigned integer.
- CSV: 9 or 12 comma-separated numeric fields per row; see README.
- MP4: 8-bit grayscale frames encoded with H.264, padded to uniform even dimensions.

## Open questions for instructor

1. Are external NRRD and MP4 libraries allowed?
2. Is FPS measured for projection only, or end-to-end video generation?
3. What exact four-point ordering and CSV schema are expected?
4. Must plane coordinates be physical-world coordinates or voxel indices?
5. Is the assignment pseudocode's omission of the apex intentional?


CSV input: The lecturer-provided CSV begins with `Number of Point`, then x1,y1,z1 through x4,y4,z4. Each row contains 3 or 4 points; unused final fields may be empty.
