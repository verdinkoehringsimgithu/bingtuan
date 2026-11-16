from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'retune_2026_10_27'))
import confirm_policies as previous
from audit_research import check_manifest,equivalent
from state_contract import ExpeditionState
from supply_adapter import restore_missing_caps
from run_bonds import atomic_json

old=previous.old
OUT=HERE/'results'
