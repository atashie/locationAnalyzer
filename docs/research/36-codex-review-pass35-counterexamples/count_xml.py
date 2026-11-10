import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'data/triangle/triangle-roads.osm'
counts=Counter();vehicles=Counter();examples=[]
for _,el in ET.iterparse(p,events=('end',)):
    if el.tag in ['node','way','relation']:
        for tag in el.findall('tag'):
            k,v=tag.get('k'),tag.get('v')
            if k in ['surface','vehicle']:counts[el.tag,k]+=1
            if k=='vehicle':
                vehicles[el.tag,v]+=1
                if el.tag!='way':examples.append((el.tag,el.get('id'),v))
        el.clear()
print('BY_ELEMENT',counts)
print('VEHICLE_BY_ELEMENT',vehicles)
print('VEHICLE_NON_WAYS',examples)
