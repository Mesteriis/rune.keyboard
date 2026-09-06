"""Actual aapt2+zipalign asset-only APK contribution, identical storage policy per format."""
import hashlib,json,os,pathlib,subprocess,zipfile
root=pathlib.Path(__file__).resolve().parents[1];sdk=pathlib.Path(os.environ['RUNE_BENCH_SDK']);tools=sdk/'build-tools/36.0.0';out=root/'packaging';fixtures=root/'fixtures'
manifest=out/'AndroidManifest.xml';manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="io.github.mesteriis.rune.lexiconqualification"><uses-sdk android:minSdkVersion="26" android:targetSdkVersion="26"/><application android:hasCode="false" android:label="Lexicon asset size fixture"/></manifest>\n')
def link(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():os.link(src,dst)
def assemble(lang,kind):
 stage=out/f'{lang}.{kind}.assets';stage.mkdir(exist_ok=True)
 link(fixtures/'frequency'/f'{lang}.tsv',stage/'frequency'/f'{lang}.tsv')
 for p in (fixtures/'notices').iterdir():link(p,stage/'notices'/p.name)
 names=[] if kind=='base' else [f'{lang}.front',f'{lang}.front.lengths'] if kind=='front' else [f'{lang}.trie',f'{lang}.trie.lengths'] if kind=='trie' else [f'{lang}.delete',f'{lang}.front']
 for name in names:link(fixtures/'assets'/name,stage/'lexicon'/name)
 raw=out/f'{lang}.{kind}.unaligned.apk';apk=out/f'{lang}.{kind}.apk'
 subprocess.run([str(tools/'aapt2'),'link','-o',str(raw),'--manifest',str(manifest),'-I',str(sdk/'platforms/android-37.0/android.jar'),'-A',str(stage),'-0','front','-0','trie','-0','delete','-0','lengths'],check=True)
 subprocess.run([str(tools/'zipalign'),'-f','4',str(raw),str(apk)],check=True)
 with zipfile.ZipFile(apk) as z:
  entries=[{'path':i.filename,'uncompressed_bytes':i.file_size,'compressed_bytes':i.compress_size,'compression':i.compress_type} for i in z.infolist()]
  lex=[i for i in z.infolist() if i.filename.startswith('assets/lexicon/')]
  assert len(lex)==len(names) and all(i.compress_type==zipfile.ZIP_STORED for i in lex)
  for i in lex:
   h=hashlib.sha256()
   with z.open(i) as f:
    for b in iter(lambda:f.read(1048576),b''):h.update(b)
   source=fixtures/'assets'/i.filename.rsplit('/',1)[-1]
   original=hashlib.sha256()
   with source.open('rb') as f:
    for b in iter(lambda:f.read(1048576),b''):original.update(b)
   assert h.digest()==original.digest()
 raw.unlink() # only this invocation's intermediate APK; final artifact retained
 return {'language':lang,'format':kind,'apk':str(apk.relative_to(root)),'apk_bytes':apk.stat().st_size,'index_raw_bytes':sum((fixtures/'assets'/x).stat().st_size for x in names),'entries':entries}
rows=[]
for lang in ['en','es','ru']:
 baseline=assemble(lang,'base');rows.append(baseline)
 for kind in ['front','trie','delete']:
  row=assemble(lang,kind);row['apk_index_contribution_bytes']=row['apk_bytes']-baseline['apk_bytes'];rows.append(row)
  print(lang,kind,row['apk_index_contribution_bytes'],flush=True)
(root/'reports/apk-assets.json').write_text(json.dumps({'status':'ACTUAL_AAPT2_APK_MEASURED','policy':'front/trie/delete/lengths ZIP_STORED, shared frequency/notices normal aapt2 compression; zipalign4; same manifest; unsigned asset-only fixture','scope':'not application release APK; no installation or app asset activation claim','artifacts':rows},indent=2)+'\n')
