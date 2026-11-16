"""Verify stored archive and its per-entry bytes without extracting or edits."""
import hashlib,json,sys,zipfile
from pathlib import Path
from restore_research import ROOT,digest
def main():
 data=ROOT/'TransferData';manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'));total=0
 for part in manifest['parts']:
  p=data/part['name'];assert p.stat().st_size==part['bytes'] and digest(p)==part['sha256'],p
 archive=data/'research-evidence.zip'
 if not archive.exists():
  print('Parts verified. Run restore_research.py for full per-file validation.');return
 assert digest(archive)==manifest['archive_sha256']
 with zipfile.ZipFile(archive) as z:
  assert len(z.infolist())==len(manifest['files'])
  files=manifest['files']
  if '--sample' in sys.argv:
   picked=set(range(0,len(files),max(1,len(files)//64)));picked.add(len(files)-1)
   picked.update(sorted(range(len(files)),key=lambda i:files[i]['bytes'],reverse=True)[:16])
   files=[files[i] for i in sorted(picked)]
  for row in files:
   h=hashlib.sha256()
   with z.open(row['path']) as f:
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
   assert h.hexdigest()==row['sha256'],row['path'];total+=row['bytes']
 result=dict(passed=True,archive_files=len(manifest['files']),content_checked_files=len(files),content_checked_bytes=total,parts=len(manifest['parts']),all_parts_sha256_verified=True,whole_archive_sha256_verified=True)
 if '--sample' in sys.argv:(data/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result))
if __name__=='__main__':main()
