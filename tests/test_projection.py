import numpy as np
import pytest
from projection.core import Point3D, project_triangle, project_trapezoid
from projection.cli import grayscale_uint8, pad_frame
from projection.io import load_planes


def test_triangle_samples_expected_voxels():
    vol = np.zeros((8,8,8), dtype=np.uint16)
    for x in range(8):
        for y in range(8):
            for z in range(8):
                vol[x,y,z] = x + 10*y + 100*z
    im = project_triangle(vol, Point3D(2,1,1), Point3D(2,5,1), Point3D(6,1,1))
    assert im.shape == (4, 7)
    assert im[0,2] == 122  # (2,2,1) first sample after advancing
    assert im[3,0] == 152  # (2,5,1) last-row left sample
    assert im[3,5] == 116  # (6,1,1) last-row right sample


def test_outside_is_zero():
    vol = np.ones((3,3,3), dtype=np.uint8)
    im = project_triangle(vol, Point3D(-2,0,0), Point3D(-2,2,0), Point3D(0,0,0))
    assert 0 in im


def test_reject_non_isosceles():
    vol = np.ones((8,8,8), dtype=np.uint8)
    with pytest.raises(ValueError, match='isosceles'):
        project_triangle(vol, Point3D(0,0,0), Point3D(3,0,0), Point3D(0,4,0))


def test_trapezoid():
    vol = np.ones((10,10,10), dtype=np.uint8) * 20
    im = project_trapezoid(vol, Point3D(1,1,2), Point3D(4,1,2), Point3D(1,5,2), Point3D(4,5,2))
    assert im.shape == (4,4)
    assert np.all(im == 20)


def test_csv(tmp_path):
    path = tmp_path / 'planes.csv'
    path.write_text('Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n3,0,0,0,0,2,0,2,0,0,,,\n4,0,0,0,2,0,0,0,2,0,2,2,0\n')
    assert len(load_planes(path)) == 2


def test_frame_dimensions():
    assert pad_frame(grayscale_uint8(np.array([[0, 10]], dtype=np.uint8), 0, 10), 4, 4).shape == (4,4)
