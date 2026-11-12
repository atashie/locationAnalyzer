"""Same record count does not bind an explanation to the measured graph."""
from common import ROOT, script
import json
import numpy as np
import shapely

pilot = script('t0_attachment_pilot')
artifact = json.loads((ROOT / 'docs/experiments/t0-attachment-pilot.json').read_text())
expected = artifact['graph']['design_records']

class RecordsWithCount:
    # Virtual fixtures avoid allocating hundreds of thousands of unused records.
    # The guard under review calls only len(records), so no other method is needed.
    def __init__(self, geometry):
        self.geometry = geometry
    def __len__(self):
        return expected

for offset in (0., 100.):
    records = RecordsWithCount(shapely.LineString([(offset, 0.), (offset + 10., 0.)]))
    assert len(records) == expected  # the exact guard in explain_adoption_diff.main
    geoms = np.empty(1, dtype=object)
    geoms[:] = [records.geometry]
    m = pilot.measure_point(geoms, shapely.STRtree(geoms), 5., 1., 200., arithmetic='exact')
    print('count guard passes:', len(records), '; residual:', m['global_min_m'],
          '; selected XY:', [(p.x, p.y) for p in m['_sets']['C']])
print('The other expected-1 records can be identical in both runs and far away. '
      'Changing a coordinate/weight or reordering records preserves this guard.')
