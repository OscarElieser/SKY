"""Run from SKY repository root: python scripts/audit_ui_locales.py"""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from neural_core.sky_i18n_audit import report
print(json.dumps(report(root/'metaverse'/'static'),ensure_ascii=False,indent=2))
