import {parentPort,workerData} from 'node:worker_threads';
import {extract} from './extract.mjs';
try{parentPort.postMessage({rows:extract(workerData.html,workerData.url,workerData.source)});}catch(e){parentPort.postMessage({error:String(e)});}
