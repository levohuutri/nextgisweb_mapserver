from pathlib import Path
from uuid import uuid4

import pytest
import transaction
from osgeo import ogr

from nextgisweb.env import DBSession

from nextgisweb.auth import User
from nextgisweb.spatial_ref_sys import SRS
from nextgisweb.vector_layer import VectorLayer

from ..model import MapserverStyle

data_path = Path(__file__).parent / 'data'


@pytest.fixture()
def layer(ngw_resource_group):
    with transaction.manager:
        res = VectorLayer(
            parent_id=ngw_resource_group, display_name='test-vlayer',
            owner_user=User.by_keyname('administrator'),
            srs=SRS.filter_by(id=3857).one(),
            tbl_uuid=uuid4().hex
        ).persist()

        ds = ogr.Open(str(data_path / 'multipolygonz-duplicate.geojson'))
        layer = ds.GetLayer(0)

        res.setup_from_ogr(layer)
        res.load_from_ogr(layer)

        DBSession.flush()

    yield res

    with transaction.manager:
        DBSession.delete(res)


color = (200, 0, 0)


@pytest.fixture()
def style(layer):
    with transaction.manager:
        res = MapserverStyle(
            parent_id=layer.id, display_name='test-msstyle',
            owner_user=User.by_keyname('administrator'),
            xml=MapserverStyle.default_style_xml(layer, color=color),
        ).persist()

        DBSession.flush()

        yield res

        DBSession.delete(res)


def test_render(style):
    srs = SRS.filter_by(id=4326).one()

    size = 64
    center = size // 2
    h = center // 2

    req = style.render_request(srs)
    extent = (-5, -5, 5, 5)
    img = req.render_extent(extent, (size, size))

    p = 5  # shade padding
    for x, y in (
        (p, p),
        (p, size - p),
        (size - p, p),
        (size - p, size - p),
        (center, center),
    ):
        assert img.getpixel((x, y)) == color + (255, )

    for dx, dy in (
        (h, 0), (h, -h), (0, -h),
        (-h, -h), (-h, 0), (-h, h),
        (0, h), (h, h),
    ):
        assert img.getpixel((center + dx, center + dy)) == (0, 0, 0, 0)
