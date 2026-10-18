#!/usr/bin/env python3
"""Bounded concurrent range download from Xiaomi; validate each Content-Range."""
from pathlib import Path
import concurrent.futures,urllib.request,time,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
URL='https://cdnorg.d.miui.com/V11.0.2.0.OAHMIXM/lithium_global_images_V11.0.2.0.OAHMIXM_20191023.0000.00_8.0_global_3454b31c75.tgz'
SIZE=1803158296
CHUNK=4*1024*1024

def main():
 folder=ROOT/'artifacts/stock/ranges';folder.mkdir(parents=True,exist_ok=True)
 def fetch(start):
  end=min(start+CHUNK,SIZE)-1
  target=folder/str(start)
  if target.exists() and target.stat().st_size==end-start+1:return target
  for attempt in range(3):
   try:
    req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'})
    with urllib.request.urlopen(req,timeout=30) as response:
     if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{SIZE}':raise ValueError('Range not honored')
     data=response.read(end-start+2)
    if len(data)!=end-start+1:raise ValueError('Wrong response length')
    partial=target.with_suffix('.partial');partial.write_bytes(data);partial.rename(target)
    return target
   except Exception:
    if attempt==2:raise
    time.sleep(1+attempt)
 starts=list(range(0,SIZE,CHUNK));start_time=time.monotonic()
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  futures=[pool.submit(fetch,start) for start in starts]
  for i,future in enumerate(concurrent.futures.as_completed(futures),1):
   future.result()
   if i%20==0 or i==len(starts):print(f'{i}/{len(starts)} ranges complete ({time.monotonic()-start_time:.0f}s)',flush=True)
 final=ROOT/'artifacts/stock/lithium-global-V11.0.2.0.tgz'
 if final.exists():raise SystemExit('Final already exists; do not overwrite')
 partial=final.with_suffix('.assembled.partial');h=hashlib.sha256()
 with partial.open('wb') as output:
  for start in starts:
   data=(folder/str(start)).read_bytes();h.update(data);output.write(data)
 if partial.stat().st_size!=SIZE:raise ValueError('Wrong final length')
 partial.rename(final)
 (final.with_suffix('.manifest.json')).write_text(json.dumps({'url':URL,'bytes':SIZE,'sha256':h.hexdigest(),'transport':'HTTPS validated byte ranges','status':'complete_pending_gzip_and_tar_audit'},indent=2)+'\n')
 print('Complete: '+h.hexdigest(),flush=True)
if __name__=='__main__':main()
