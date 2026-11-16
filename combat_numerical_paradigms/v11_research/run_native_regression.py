"""Reproduce the mandated unmodified 37,500-battle native regression."""
import contextlib
import io
import json
import random
import re
from pathlib import Path
from research_core import engine
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--output",default=str(Path(__file__).parent/"results"));args=parser.parse_args()
    directory=Path(args.output);directory.mkdir(parents=True,exist_ok=True)
    random.seed(20261012)
    buffer=io.StringIO()
    with contextlib.redirect_stdout(buffer):engine.run_full_stress_test(2500)
    log=buffer.getvalue();(directory/"native_37500_regression.log").write_text(log,encoding="utf-8")
    rates=[]
    for line in log.splitlines():
        nums=re.findall(r"(\d+\.\d+)%",line)
        if len(nums)==7:rates.append(float(nums[-1]))
    spread=max(rates)-min(rates)
    assert spread<=15.,spread
    data=dict(seed=20261012,battles=37500,overall_winrates_percent=rates,spread_percentage_points=spread,passed=spread<=15.)
    (directory/"native_regression.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    print(json.dumps(data,indent=2))
