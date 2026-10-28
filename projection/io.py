"""NRRD and CSV input."""
import csv
from pathlib import Path
import numpy as np
from .core import Point3D


def load_nrrd(path):
    try:
        import nrrd
    except ImportError as exc:
        raise RuntimeError('Install the pynrrd dependency: pip install -r requirements.txt') from exc
    volume, header = nrrd.read(str(path), index_order='F')
    # Convert non-negative signed 16-bit MRI data to unsigned 16-bit.
    if volume.dtype == np.int16:
        if np.any(volume < 0):
            raise ValueError(
                "Cannot convert MRI: negative voxel values detected"
            )
        volume = volume.astype(np.uint16)
    # pynrrd's F index order gives volume[x,y,z] for NRRD axis order x,y,z.
    if volume.ndim != 3:
        raise ValueError('Expected a 3D NRRD volume')
    if volume.dtype.kind != 'u' or volume.dtype.itemsize not in (1, 2, 4):
        raise ValueError('Only unsigned 8-, 16-, or 32-bit NRRD data is supported')
    if any(s >= 1024 for s in volume.shape):
        raise ValueError('All volume dimensions must be smaller than 1024')
    return volume, header


def load_planes(path, *, with_line_numbers=False):
    """Read assignment CSV: count,x1,y1,z1,...,x4,y4,z4.

    Each data row has 3 or 4 points. The header is optional, and empty
    trailing cells for three-point rows are permitted.
    """
    planes = []
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        for lineno, row in enumerate(csv.reader(handle), start=1):
            cells = [cell.strip() for cell in row]
            if not any(cells):
                continue
            if cells[0].startswith('#') or cells[0].lower().startswith('number of point'):
                continue
            try:
                count = int(cells[0])
            except ValueError as exc:
                raise ValueError(f'CSV line {lineno}: first column must be 3 or 4') from exc
            if count not in (3, 4):
                raise ValueError(f'CSV line {lineno}: point count must be 3 or 4')
            required = 1 + count * 3
            if len(cells) < required or any(not cell for cell in cells[1:required]):
                raise ValueError(f'CSV line {lineno}: expected {count} complete points')
            if any(cell for cell in cells[required:]):
                raise ValueError(f'CSV line {lineno}: unexpected extra coordinates')
            try:
                values = [float(cell) for cell in cells[1:required]]
            except ValueError as exc:
                raise ValueError(f'CSV line {lineno}: invalid coordinate') from exc
            if not np.all(np.isfinite(values)):
                raise ValueError(f'CSV line {lineno}: coordinates must be finite')
            points = tuple(Point3D(*values[i:i+3]) for i in range(0, len(values), 3))
            planes.append((lineno, points) if with_line_numbers else points)
    if not planes:
        raise ValueError('CSV contains no planes')
    return planes
