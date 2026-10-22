# 3D Volume Oblique Slicing & Plane Projection Engine

Project implementation for Software Engineering (OOP, OOD)[cite: 1]. This system computes fast 2D plane projections (oblique slicing) from 3D raster volume data (NRRD format) based on continuous coordinate definitions, producing a smooth MP4 video sequence[cite: 1, 3].

---

## 1. Problem Definition & Scope
The goal of this project is to design and implement a robust, high-performance projection engine[cite: 1]. Given a 3D volumetric matrix $M$ of size $s_x \times s_y \times s_z$ (8, 16, or 32-bit unsigned integers, where $1 \le s_x, s_y, s_z < 2^{10}$)[cite: 1] and a sequence of planes defined in a CSV file[cite: 3], the software projects the intersected 3D voxels onto 2D image matrices ($E$) and encodes them into a real-time output video (`.mp4`)[cite: 1, 2, 3].

---

## 2. Software Requirements Specification (SRS)

### Functional Requirements
* **FR1: 3D Volume Input (`Volume3D`):** Loads `.nrrd` files into a memory-efficient structure. Out-of-bounds coordinate lookups safely return a default value of `0` (black pixel) without throwing memory errors[cite: 1, 2].
* **FR2: Plane Parsing & Validation (`SlicingPlane`):** Reads CSV rows containing 3 points (isosceles triangle) or 4 points (isosceles trapezoid)[cite: 2, 3]. Validates geometric constraints against an error margin $\text{EPS} = 0.001$ (including distance equality, base ratios, and coplanarity)[cite: 2, 3].
* **FR3: Projection Engine (`ProjectionEngine`):** Computes the 2D projection matrix $E$ of size $\lceil D_{bc} \rceil \times \lceil D_{ab} \rceil$ using vectorized NumPy operations[cite: 2]. Employs Nearest-Neighbor sampling and centers the scanned profile using the horizontal offset formula $x = (D_{bc}/2) - (d_{12}/2) + x_1$[cite: 2].
* **FR4: Video Encoding (`Mp4VideoWriter`):** Normalizes bit-depths (16/32-bit to 8-bit grayscale [0-255]) and streams frames safely into an MP4 file with guaranteed resource cleanup (`try...finally`)[cite: 1, 3].

### Non-Functional Requirements
* **Performance:** Targets **100+ FPS** (with a mandatory minimum threshold of **30 FPS**) on a $500^3$ voxel matrix, leveraging NumPy vectorization and optimized baseline step calculations[cite: 1, 2].
* **Architecture:** Strict adherence to Object-Oriented Design (OOD) and Separation of Concerns (I/O, Models, Engine)[cite: 1, 3].

---

## 3. Algorithm Details & Optimizations
* **Vectorized Scanning:** Replaces slow Python nested loops with optimized array structures to achieve real-time rendering speeds[cite: 1, 2].
* **Geometric Pre-calculation:** The horizontal step direction vector ($\vec{dp}$) is computed once per plane directly from the base vector ($\vec{bc}$), avoiding redundant square-root and division operations inside inner loops[cite: 2].
* **Safety Handling:** Prevents division-by-zero errors on degenerate triangle apexes and safely clips indices to avoid `IndexError` at boundary conditions[cite: 2].

---

## 4. Dataset Definition
1. **Clinical Real-World Data:** `MRHead.nrrd` from the open-source **3D Slicer** project, used for visual demonstrations and final experiment rendering[cite: 1, 3].
2. **Synthetic Validation Volume:** A custom $100^3$ synthetic volume featuring known geometric shapes to rigorously test spatial correctness and coordinate mapping[cite: 1].
3. **Benchmark Volume:** A full $500 \times 500 \times 500$ matrix across 8, 16, and 32-bit depths dedicated to strict FPS and performance profiling[cite: 1].

---

## 5. Testing Strategy
* **Unit Tests (`tests/test_geometry.py`):** Validates $\text{EPS} = 0.001$ constraints, isosceles triangle/trapezoid side equality, base ratios, and coplanarity checks[cite: 2, 3].
* **Algorithm & Boundary Tests (`tests/test_engine.py`):** Verifies orthogonal slicing correctness against direct volume slices, out-of-bounds safety (clipping to black pixels), and horizontal centering[cite: 1, 2].
* **Performance Benchmarks:** Measures raw projection time on a $500^3$ grid to ensure the 30–100+ FPS requirement is met[cite: 1].
* **End-to-End Demo CLI Test (`tests/test_integration.py`):** Tests complete execution via command line (`python Ex0.py`) and asserts proper MP4 creation and frame count matching[cite: 3].

---

## 6. Usage & Demo (CLI)
Run the script from the root directory using the following format[cite: 3]:
```bash
python Ex0.py data/MRHead.nrrd data/planes_path.csv output/output_video.mp4