"""Bundle runnable sources and evidence without the machine-specific virtualenv."""
import hashlib
import json
import zipfile
from pathlib import Path
root=Path(__file__).parent
project=root.parents[1]
dest=root/"delivery";dest.mkdir(exist_ok=True)
archive=dest/"V11_RESEARCH_DELIVERY.zip"
with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in (project/'test_30man_combat_simulator.py',project/'AGENT.md',project/'combat_numerical_paradigms/01_COMBAT_CORE_MATHEMATICAL_MODEL.md',project/'combat_numerical_paradigms/02_PROGRESSION_STAGES_AND_BUDGETS.md'):
        z.write(p,p.relative_to(project))
    for p in sorted(root.rglob("*")):
        rel=p.relative_to(root)
        if p.is_file() and not any(x in (".venv","__pycache__","delivery") for x in rel.parts):z.write(p,Path("combat_numerical_paradigms/v11_research")/rel)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert hashlib.sha256(z.read('test_30man_combat_simulator.py')).hexdigest()==hashlib.sha256((project/'test_30man_combat_simulator.py').read_bytes()).hexdigest()
info=dict(path=str(archive.resolve()),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(dest/"archive_manifest.json").write_text(json.dumps(info,indent=2),encoding="utf-8")
print(json.dumps(info,indent=2))
