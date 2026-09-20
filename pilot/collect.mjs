// Static public HTML collection; no browser profile, cookies, or JavaScript execution.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import robotsParser from 'robots-parser';
import { hash } from './extract.mjs';
import { Worker } from 'node:worker_threads';
function extractBounded(html,url,source){return new Promise((resolve,reject)=>{const w=new Worker(new URL('./extract-worker.mjs',import.meta.url),{workerData:{html,url,source},resourceLimits:{maxOldGenerationSizeMb:256}});const timer=setTimeout(()=>{w.terminate();reject(Error('extraction timeout'));},15000);w.once('message',v=>{clearTimeout(timer);w.terminate();v.error?reject(Error(v.error)):resolve(v.rows);});w.once('error',e=>{clearTimeout(timer);reject(e);});w.once('exit',code=>{clearTimeout(timer);if(code!==0)reject(Error('extraction worker exited'));});});}
const UA='HandrailQualityPilot/0.1';
function shuffled(a, seed=42) {
  let x=seed;
  for(let i=a.length-1;i>0;i--){x=(1664525*x+1013904223)>>>0;const j=x%(i+1);[a[i],a[j]]=[a[j],a[i]];}
  return a;
}
async function get(url, limit=3000000) {
  const r=await fetch(url,{headers:{'User-Agent':UA},signal:AbortSignal.timeout(12000)});
  if (!r.ok) throw Error(`HTTP ${r.status}`);
  const reader=r.body.getReader();let size=0;const parts=[];
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();throw Error('body limit');}parts.push(value);}
  return {text:Buffer.concat(parts).toString('utf8'),url:r.url};
}
export async function collect() {
  const args=process.argv.slice(2);const value=(k,def)=>args.includes(k)?args[args.indexOf(k)+1]:def;
  const list=value('--list','pilot/data/tranco.csv');const listId=value('--list-id','unspecified');
  const pages=Number(value('--pages-per-stratum','50'));const perPage=Number(value('--items-per-page','10'));
  const out=value('--out','pilot/data');mkdirSync(out,{recursive:true});
  const raw=readFileSync(list,'utf8');const ranks=raw.trim().split('\n').map(l=>{const [r,d]=l.trim().split(',');return {rank:Number(r),domain:d};});
  let log={list_id:listId,list_sha256:hash(raw),seed:42,method:'static-html-explicit-name-masking',started_at:new Date().toISOString(),target_pages_per_stratum:pages,items_per_page:perPage,attempts:[]};
  let records=[];
  try {const prior=JSON.parse(readFileSync(`${out}/collection.json`,'utf8'));if(prior.list_sha256!==log.list_sha256||prior.items_per_page!==perPage||prior.target_pages_per_stratum!==pages)throw Error('collection config mismatch');log=prior;records=readFileSync(`${out}/corpus.jsonl`,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);}catch(e){if(e.code!=='ENOENT')throw e;}
  for(const [stratum,lo,hi] of [['top',1,1000],['long-tail',1001,1000000]]){
    const pool=shuffled(ranks.filter(r=>r.rank>=lo&&r.rank<=hi)).slice(0,600).filter(s=>!log.attempts.some(a=>a.domain===s.domain));
    let accepted=log.attempts.filter(a=>a.stratum===stratum&&a.accepted).length;
    for(let offset=0;offset<pool.length&&accepted<pages;offset+=8){
      const batch=await Promise.all(pool.slice(offset,offset+8).map(async s=>{
        const url=`https://${s.domain}/`;const entry={...s,stratum,url};
        try{
          let robots;
          try{robots=(await get(new URL('/robots.txt',url),300000)).text;}catch(e){if(!String(e).includes('HTTP 404'))throw Error('robots unavailable: '+e);robots='';}
          if(robotsParser(new URL('/robots.txt',url).href,robots).isAllowed(url,UA)===false)throw Error('robots disallow');
          const page=await get(url);
          // Cross-origin redirects require their own robots policy; skip in this pilot.
          if(new URL(page.url).hostname.replace(/^www\./,'')!==s.domain.replace(/^www\./,''))throw Error('cross-domain redirect');
          const items=await extractBounded(page.text,page.url,{stratum,rank:s.rank,list_id:listId,captured_at:new Date().toISOString(),html_sha256:hash(page.text),synthetic:false});
          if(items.length<perPage)throw Error(`only ${items.length} eligible masked controls`);
          return {entry,items:shuffled(items).slice(0,perPage)};
        }catch(e){return {entry:{...entry,error:String(e)}};}
      }));
      for(const b of batch){if(b.items&&accepted<pages){records.push(...b.items);accepted++;b.entry.accepted=true;}else if(b.items){b.entry.error='stratum quota filled';}log.attempts.push(b.entry);}
      writeFileSync(`${out}/corpus.jsonl`,records.map(r=>JSON.stringify(r)).join('\n')+'\n');
      writeFileSync(`${out}/collection.json`,JSON.stringify({...log,records:records.length},null,2));
      console.log(`${stratum}: ${accepted}/${pages} pages, ${records.length} total items (${offset+batch.length} attempted)`);
    }
  }
  log.finished_at=new Date().toISOString();log.records=records.length;
  writeFileSync(`${out}/collection.json`,JSON.stringify(log,null,2));
  console.log(`Collected ${records.length}; target ${pages*perPage*2}. Shortfalls must be reported, not filled with synthetic examples.`);
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)collect().catch(e=>{console.error(e);process.exitCode=1;});
