"""Archive bulky evidence losslessly, keeping sources/docs directly browsable."""
import hashlib,json,os,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'TransferData'
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 files=[]
 for base,dirs,names in os.walk(ROOT/'combat_numerical_paradigms'):
  dirs[:]=[d for d in dirs if d not in {'.venv','venv','__pycache__','.git'}]
  for name in names:
   p=Path(base)/name;r=p.relative_to(ROOT)
   if p.suffix in {'.pyc'}:continue
   if 'results' in r.parts or p.stat().st_size>2*1024*1024:files.append(p)
 OUT.mkdir(exist_ok=True);zpath=OUT/'research-evidence.zip';manifest=[]
 with zipfile.ZipFile(zpath,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
  for i,p in enumerate(sorted(files)):
   rel=p.relative_to(ROOT).as_posix();manifest.append(dict(path=rel,bytes=p.stat().st_size,sha256=digest(p)));z.write(p,rel)
   if i%10000==0:print('Archived',i,'of',len(files),flush=True)
 parts=[]
 with zpath.open('rb') as f:
  i=1
  while True:
   b=f.read(40*1024*1024)
   if not b:break
   p=OUT/('research-evidence.zip.part%03d'%i);p.write_bytes(b);parts.append(dict(name=p.name,bytes=len(b),sha256=digest(p)));i+=1
 (OUT/'manifest.json').write_text(json.dumps(dict(version=1,archive_sha256=digest(zpath),parts=parts,files=manifest),ensure_ascii=False,indent=2),encoding='utf-8')
 ignore=ROOT/'.gitignore'
 with ignore.open('a',encoding='utf-8') as f:
  f.write('\n# Lossless evidence moved into TransferData; run restore_research.py.\n')
  f.write('/combat_numerical_paradigms/**/results/\n')
  for row in manifest:
   if 'results' not in Path(row['path']).parts:
    f.write('/'+''.join('[[]' if c=='[' else '[]]' if c==']' else c for c in row['path'])+'\n')
 print(json.dumps(dict(files=len(files),original_bytes=sum(x['bytes'] for x in manifest),archive_bytes=zpath.stat().st_size,parts=len(parts))),flush=True)
if __name__=='__main__':main()
