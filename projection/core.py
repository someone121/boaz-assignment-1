"""Projection implementation based on the assignment's row-wise sampling.

Coordinates are voxel indices (x, y, z). The volume is indexed [x, y, z].
A row is sampled between two endpoints, with samples centered in a fixed
width output image. Samples outside the volume are zero.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Point3D:
    x: float
    y: float
    z: float

    def array(self):
        return np.array((self.x, self.y, self.z), dtype=np.float64)


def _length(v):
    return float(np.linalg.norm(v))


def _sample_row(volume, start, end, width, row, out):
    """Sample a row using nearest-neighbor values, vectorized in NumPy."""
    distance = _length(end - start)
    count = min(width, int(np.floor(distance)) + 1)
    if count <= 0:
        return
    # Match the pseudocode: start at a1, then step in unit increments.
    direction = (end - start) / distance if distance > 1e-12 else np.zeros(3)
    positions = start + np.arange(count, dtype=np.float64)[:, None] * direction
    coords = np.floor(positions + 0.5).astype(np.int64)
    shape = np.asarray(volume.shape)
    valid = np.all((coords >= 0) & (coords < shape), axis=1)
    values = np.zeros(count, dtype=volume.dtype)
    if np.any(valid):
        c = coords[valid]
        values[valid] = volume[c[:, 0], c[:, 1], c[:, 2]]
    offset = (width - count) // 2
    out[row, offset:offset + count] = values


def _sample_rows(volume, starts, ends, width):
    """Sample all rows of a plane simultaneously using 2D NumPy broadcasting."""
    diffs = ends - starts
    distances = np.linalg.norm(diffs, axis=1)
    counts = np.minimum(width, np.floor(distances).astype(np.int64) + 1)
    directions = np.divide(
        diffs,
        distances[:, None],
        out=np.zeros_like(diffs),
        where=distances[:, None] > 1e-12,
    )
    offsets = (width - counts) // 2
    k = np.arange(width, dtype=np.int64)[None, :] - offsets[:, None]
    active = (k >= 0) & (k < counts[:, None])
    kf = k.astype(np.float64)
    cx = np.floor(starts[:, 0:1] + kf * directions[:, 0:1] + 0.5).astype(np.int64)
    cy = np.floor(starts[:, 1:2] + kf * directions[:, 1:2] + 0.5).astype(np.int64)
    cz = np.floor(starts[:, 2:3] + kf * directions[:, 2:3] + 0.5).astype(np.int64)
    sx, sy, sz = volume.shape
    valid = active & (cx >= 0) & (cx < sx) & (cy >= 0) & (cy < sy) & (cz >= 0) & (cz < sz)
    out = np.zeros((len(starts), width), dtype=volume.dtype)
    out[valid] = volume[cx[valid], cy[valid], cz[valid]]
    return out


def project_triangle(volume, a: Point3D, b: Point3D, c: Point3D, *, tolerance=1e-5):
    """Sample the triangle with equal-length sides a->b and a->c.

    Returns an image in conventional [row, column] layout.
    The apex is omitted (the supplied pseudocode advances before sampling).
    """
    _validate_volume(volume)
    aa, bb, cc = a.array(), b.array(), c.array()
    dab, dac, dbc = _length(bb-aa), _length(cc-aa), _length(cc-bb)
    if min(dab, dac, dbc) <= 1e-12:
        raise ValueError('Triangle points must be distinct and non-degenerate')
    if not np.isclose(dab, dac, rtol=tolerance, atol=tolerance):
        raise ValueError('Triangle must be isosceles: dist(a,b) == dist(a,c)')
    if _length(np.cross(bb-aa, cc-aa)) <= 1e-10 * dab * dac:
        raise ValueError('Triangle points must not be collinear')
    height = max(1, int(np.ceil(dab)))
    width = max(1, int(np.ceil(dbc)) + 1)
    vab, vac = (bb-aa)/dab, (cc-aa)/dac
    # Assignment step 5 advances both edge points before sampling each row.
    steps = np.minimum(np.arange(1, height + 1, dtype=np.float64), dab)[:, None]
    return _sample_rows(volume, aa + steps * vab, aa + steps * vac, width)


def project_trapezoid(volume, a_left: Point3D, a_right: Point3D,
                      b_left: Point3D, b_right: Point3D, *, tolerance=1e-5):
    """Sample a trapezoid using equal-length side vectors a_left->b_left
    and a_right->b_right. Both pairs of endpoints must lie in one plane.
    Rows progress from the a-edge to the b-edge.
    """
    _validate_volume(volume)
    al, ar, bl, br = (p.array() for p in (a_left, a_right, b_left, b_right))
    left, right = bl-al, br-ar
    dl, dr = _length(left), _length(right)
    if min(dl, dr) <= 1e-12 or not np.isclose(dl, dr, rtol=tolerance, atol=tolerance):
        raise ValueError('Trapezoid side vectors must have equal nonzero length')
    normal = np.cross(ar-al, left)
    norm = _length(normal)
    if norm <= 1e-12:
        raise ValueError('Trapezoid must have nonzero area')
    if abs(np.dot(br-al, normal)) > tolerance * norm * max(1.0, _length(br-al)):
        raise ValueError('Trapezoid points must be coplanar')
    height = max(1, int(np.ceil(dl)))
    max_width = max(_length(ar-al), _length(br-bl))
    width = max(1, int(np.ceil(max_width)) + 1)
    ts = np.minimum(np.arange(1, height + 1, dtype=np.float64) / dl, 1.0)[:, None]
    return _sample_rows(volume, al + ts * left, ar + ts * right, width)


def _validate_volume(volume):
    if not isinstance(volume, np.ndarray) or volume.ndim != 3:
        raise ValueError('Volume must be a 3D NumPy array')
    if any(s < 1 for s in volume.shape):
        raise ValueError('Volume dimensions must be positive')
    if volume.dtype.kind != 'u' or volume.dtype.itemsize not in (1, 2, 4):
        raise ValueError('Volume dtype must be uint8, uint16, or uint32')
