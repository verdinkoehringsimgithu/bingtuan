"""Verify stored archive and its per-entry bytes without extracting or edits."""
import hashlib,json,tempfile,zipfile
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
  for row in manifest['files']:
   h=hashlib.sha256()
   with z.open(row['path']) as f:
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
   assert h.hexdigest()==row['sha256'],row['path'];total+=row['bytes']
 print('Archive verified:',len(manifest['files']),'files;',total,'original bytes;',len(manifest['parts']),'parts')
if __name__=='__main__':main()
