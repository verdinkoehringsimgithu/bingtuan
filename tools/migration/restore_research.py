"""Verify and safely restore all archived evidence; never overwrite edits."""
import hashlib,json,shutil,tempfile,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2]
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 data=ROOT/'TransferData';m=json.loads((data/'manifest.json').read_text(encoding='utf-8'));restored=0
 for part in m['parts']:
  p=data/part['name'];assert p.stat().st_size==part['bytes'] and digest(p)==part['sha256'],p
 with tempfile.TemporaryDirectory(prefix='bingtuan-restore-') as temp:
  archive=Path(temp)/'research.zip'
  with archive.open('wb') as output:
   for part in m['parts']:
    with (data/part['name']).open('rb') as source:shutil.copyfileobj(source,output)
  assert digest(archive)==m['archive_sha256'],'Archive checksum mismatch'
  with zipfile.ZipFile(archive) as z:
   for row in m['files']:
    rel=PurePosixPath(row['path']);assert not rel.is_absolute() and '..' not in rel.parts
    target=(ROOT/Path(*rel.parts)).resolve();assert target.is_relative_to(ROOT.resolve())
    if target.exists():
     assert digest(target)==row['sha256'],'Local edits preserved; resolve conflict: '+str(target)
     continue
    target.parent.mkdir(parents=True,exist_ok=True)
    temp_file=target.with_name(target.name+'.restore-tmp')
    with z.open(row['path']) as source,temp_file.open('wb') as dest:shutil.copyfileobj(source,dest)
    assert digest(temp_file)==row['sha256'],target
    temp_file.replace(target);restored+=1
 print('Verified',len(m['files']),'files; restored',restored)
if __name__=='__main__':main()
