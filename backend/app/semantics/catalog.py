import yaml
from app.core.config import ROOT

with (ROOT / 'config' / 'semantics.yml').open(encoding='utf-8') as file:
    CATALOG = yaml.safe_load(file)
METRICS = CATALOG['metrics']
DIMENSIONS = CATALOG['dimensions']
