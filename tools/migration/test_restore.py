"""Exercise lossless restore, edited-file refusal and corrupt-part detection."""
import hashlib,io,json,tempfile,zipfile
from pathlib import Path
import restore_research as restore
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 original=restore.ROOT
 with tempfile.TemporaryDirectory(prefix='bingtuan-restore-test-') as folder:
  root=Path(folder);data=root/'TransferData';data.mkdir();content=b'calibrated configuration\r\n'
  stream=io.BytesIO()
  with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('research/example.json',content)
  archive=stream.getvalue();chunks=[archive[:50],archive[50:]];parts=[]
  for i,b in enumerate(chunks):
   name='test.part%03d'%i;(data/name).write_bytes(b);parts.append(dict(name=name,bytes=len(b),sha256=sha(b)))
  manifest=dict(parts=parts,archive_sha256=sha(archive),files=[dict(path='research/example.json',bytes=len(content),sha256=sha(content))])
  (data/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8');restore.ROOT=root
  try:
   restore.main();assert (root/'research/example.json').read_bytes()==content
   restore.main()
   (root/'research/example.json').write_bytes(b'local edit')
   try:restore.main()
   except AssertionError:pass
   else:raise AssertionError('Edited local file was overwritten')
   assert (root/'research/example.json').read_bytes()==b'local edit'
   (data/parts[0]['name']).write_bytes(b'corrupt')
   try:restore.main()
   except AssertionError:pass
   else:raise AssertionError('Corrupt archive part accepted')
  finally:restore.ROOT=original
 print('Restore tests passed: exact bytes, repeated restore, local edits retained, corrupt parts rejected')
if __name__=='__main__':main()
