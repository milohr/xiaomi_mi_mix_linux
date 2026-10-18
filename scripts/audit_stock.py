#!/usr/bin/env python3
"""Audit the complete lithium stock archive; extract only research inputs."""
from pathlib import Path
import gzip,hashlib,json,struct,subprocess,tarfile,datetime,zlib,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'artifacts/stock/lithium-global-V11.0.2.0.tgz'
OUT=ROOT/'artifacts/stock/audit'

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def main():
 if ARCHIVE.stat().st_size!=1803158296:raise SystemExit('Unexpected archive length')
 OUT.mkdir(parents=True,exist_ok=True)
 # Consume the complete gzip stream to verify its CRC and uncompressed length.
 with gzip.open(ARCHIVE,'rb') as f:
  while f.read(1024*1024):pass
 entries=[];extracted=[]
 wanted={'boot.img','recovery.img','misc.txt','android-info.txt','flash_all.sh','flash_all_except_storage.sh','flash_all_lock.sh','emmc_appsboot.mbn'}
 with tarfile.open(ARCHIVE,'r:gz') as t:
  for m in t:
   entries.append({'name':m.name,'bytes':m.size,'type':m.type.decode('ascii',errors='replace')})
   name=Path(m.name).name
   if name not in wanted and not (name.startswith('rawprogram') and name.endswith('.xml')):continue
   if not m.isfile() or m.size>128*1024*1024:raise ValueError('Unexpected member type/size')
   target=OUT/name
   if any(x['name']==name for x in extracted):raise ValueError('Duplicate selected basename')
   with t.extractfile(m) as source,target.open('wb') as dest:
    for b in iter(lambda:source.read(1024*1024),b''):dest.write(b)
   extracted.append({'name':name,'member':m.name,'bytes':target.stat().st_size,'sha256':digest(target)})
 (OUT/'archive-list.json').write_text(json.dumps(entries,indent=2)+'\n')
 images=[]
 for name in ['boot.img','recovery.img']:
  path=OUT/name
  if not path.exists():raise ValueError('Missing '+name)
  header=path.read_bytes()[:1632]
  if header[:8]!=b'ANDROID!':raise ValueError('Bad Android boot magic')
  v=struct.unpack_from('<10I',header,8)
  info=dict(zip(['kernel_size','kernel_addr','ramdisk_size','ramdisk_addr','second_size','second_addr','tags_addr','page_size','header_version','os_version'],v))
  if info['header_version']!=0:raise ValueError('Expected legacy header; audit manually')
  page=info['page_size']
  if page not in [2048,4096,8192,16384]:raise ValueError('Unexpected page size')
  aligned=lambda n:((n+page-1)//page)*page
  info['kernel_file_offset']=page
  info['ramdisk_file_offset']=page+aligned(info['kernel_size'])
  info['second_file_offset']=info['ramdisk_file_offset']+aligned(info['ramdisk_size'])
  info['cmdline']=(header[64:576].split(b'\0')[0]+header[608:1632].split(b'\0')[0]).decode(errors='replace')
  info['name']=name;info['image_bytes']=path.stat().st_size;info['partition_bytes']=67108864
  info['fits_partition']=path.stat().st_size<=67108864
  if info['second_file_offset']+info['second_size']>path.stat().st_size:raise ValueError('Truncated components')
  result=subprocess.run(['unpack_bootimg','--boot_img',str(path),'--out',str(OUT/(name+'.unpacked'))],text=True,capture_output=True,check=True)
  (OUT/(name+'.header.txt')).write_text(result.stdout+result.stderr)
  kernel=(OUT/(name+'.unpacked')/'kernel').read_bytes()
  info['kernel_compression']='gzip' if kernel[:2]==b'\x1f\x8b' else 'unknown'
  if info['kernel_compression']=='gzip':
   stream=zlib.decompressobj(16+zlib.MAX_WBITS)
   decoded=stream.decompress(kernel)
   if not stream.eof:raise ValueError('Incomplete compressed kernel')
   info['compressed_kernel_bytes']=len(kernel)-len(stream.unused_data)
   info['kernel_trailing_bytes']=len(stream.unused_data)
   version=re.search(rb'Linux version [^\x00\n]+',decoded)
   info['kernel_version_string']=version.group().decode(errors='replace') if version else None
  dtbs=[];offset=0
  while True:
   offset=kernel.find(b'\xd0\x0d\xfe\xed',offset)
   if offset<0:break
   if offset+40<=len(kernel):
    fields=struct.unpack_from('>10I',kernel,offset)
    total=fields[1]
    if 40<=total<=len(kernel)-offset and fields[5] in [16,17] and all(x<total for x in fields[2:5]):
     blob=kernel[offset:offset+total]
     dtbs.append({'kernel_offset':offset,'image_offset':page+offset,'bytes':total,'sha256':hashlib.sha256(blob).hexdigest()})
     (OUT/(name+'.dtb-'+str(len(dtbs)-1))).write_bytes(blob)
   offset+=4
  info['appended_dtb_candidates']=dtbs
  images.append(info)
 report={'audited_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(ARCHIVE.relative_to(ROOT)),'archive_bytes':ARCHIVE.stat().st_size,'archive_sha256':digest(ARCHIVE),'gzip_integrity':'passed','archive_members':len(entries),'extracted':extracted,'images':images,'device_writes':False,'vendor_scripts_executed':False,'provenance_note':'Xiaomi HTTPS download and local digest; no independently published signature verified'}
 metadata=dict(line.split('=',1) for line in (OUT/'misc.txt').read_text().splitlines())
 if metadata.get('device')!='lithium' or metadata.get('build_number')!='V11.0.2.0.OAHMIXM':raise ValueError('Stock metadata mismatch')
 live=json.loads((ROOT/'research/partition-inventory.json').read_text())
 sizes={x['name']:x['size_bytes'] for x in live['partitions']}
 layout=[]
 for xml in OUT.glob('rawprogram*.xml'):
  for entry in ET.parse(xml).getroot().iter('program'):
   e=entry.attrib
   if e.get('label') not in ['boot','recovery']:continue
   size=int(e['SECTOR_SIZE_IN_BYTES'])*int(e['num_partition_sectors'])
   if size!=sizes[e['label']]:raise ValueError('Stock/live partition size mismatch')
   layout.append({'name':e['label'],'source':str(xml.relative_to(ROOT)),'physical_partition_number':int(e['physical_partition_number']),'start_sector':int(e['start_sector']),'sector_bytes':int(e['SECTOR_SIZE_IN_BYTES']),'size_bytes':size,'matches_live_size':True})
 if len(layout)!=2:raise ValueError('Missing or duplicate stock partition entries')
 for info in images:
  dtbs=info['appended_dtb_candidates']
  if len(dtbs)!=20 or dtbs[0]['kernel_offset']!=info['compressed_kernel_bytes']:raise ValueError('Unexpected DTB layout')
  if any(x['kernel_offset']+x['bytes']!=y['kernel_offset'] for x,y in zip(dtbs,dtbs[1:])):raise ValueError('DTB gap')
  if dtbs[-1]['kernel_offset']+dtbs[-1]['bytes']!=info['kernel_size']:raise ValueError('Unaccounted kernel tail')
 report.update(stock_metadata=metadata,stock_layout_comparison=layout,dtb_layout_check='20 contiguous DTBs exactly cover gzip trailing bytes in both images')
 (ROOT/'research/stock-image-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
