"""Additional sensitivity split: remove only unnamed footways/services."""
from pathlib import Path
s=Path(__file__).with_name('reproduce.py').read_text()
start=s.index("variants={")
end=s.index('\nsummary=',start)
s=s[:start]+"variants={'no_unnamed_footway_service':{'footway','service'}}"+s[end:]
s=s.replace("if classes(d)&drop]", "if classes(d)&drop and not d.get('name')]")
s=s.replace("save('summary.json',summary)","save('unnamed_summary.json',summary)")
exec(compile(s,str(Path(__file__).with_name('reproduce.py')),'exec'))
