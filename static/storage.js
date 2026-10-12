(function(){
'use strict';
const serverMode=new URLSearchParams(location.search).get('storage')==='server';
let dbPromise,referencePromise;
function database(){
 if(!dbPromise)dbPromise=new Promise((resolve,reject)=>{
  if(!window.indexedDB)return reject(Error('เบราว์เซอร์นี้ไม่รองรับการเก็บประวัติ กรุณาใช้ Chrome, Edge หรือ Firefox'));
  const request=indexedDB.open('sap-replacement-dashboard-v1',1);
  request.onupgradeneeded=()=>request.result.createObjectStore('snapshots',{keyPath:'day'});
  request.onsuccess=()=>resolve(request.result);
  request.onerror=()=>reject(Error('เปิดที่เก็บประวัติไม่ได้ กรุณาตรวจการตั้งค่าเบราว์เซอร์'));
 });
 return dbPromise;
}
async function readAll(){
 const db=await database();
 return new Promise((resolve,reject)=>{
  const tx=db.transaction('snapshots','readonly'),request=tx.objectStore('snapshots').getAll();
  request.onsuccess=()=>resolve(request.result.sort((a,b)=>a.day.localeCompare(b.day)));request.onerror=()=>reject(request.error);
 });
}
async function jsonAsset(path){const r=await fetch(path);if(!r.ok)throw Error('โหลดข้อมูลตั้งต้นไม่สำเร็จ');return r.json();}
async function reference(){return referencePromise||(referencePromise=jsonAsset('data/reference.json'));}
async function merge(snapshots,duplicateError=false){
 const db=await database();
 return new Promise((resolve,reject)=>{
  const tx=db.transaction('snapshots','readwrite'),store=tx.objectStore('snapshots');let count=0,failure;
  tx.oncomplete=()=>resolve({count});
  tx.onabort=()=>reject(failure||Error('บันทึกประวัติไม่ได้ พื้นที่เก็บข้อมูลอาจเต็ม'));
  tx.onerror=()=>{};
  for(const s of snapshots){
   const request=store.get(s.day);
   request.onsuccess=()=>{
    if(request.result){
     if(duplicateError||!SAPParser.sameSnapshot(request.result,s)){
      failure=Error(duplicateError?'มีข้อมูลวันที่นี้แล้ว กรุณาเลือกวันที่อื่น เพื่อรักษาประวัติเดิม':`วันที่ ${s.day} มีข้อมูลขัดแย้ง ระบบไม่เขียนทับประวัติ`);tx.abort();
     }
    }else{store.add(s);count++;}
   };
  }
 });
}
async function load(){
 if(serverMode){const r=await fetch('/api/data');if(!r.ok)throw Error('โหลดข้อมูลไม่สำเร็จ');return r.json();}
 let snapshots=await readAll();
 if(!snapshots.length){const seed=SAPParser.validateSnapshot(await jsonAsset('data/seed.json'));await merge([seed]);snapshots=await readAll();}
 return {snapshots,reference:await reference()};
}
async function parse(file){
 if(file.size>20*1024*1024)throw Error('ไฟล์ใหญ่เกิน 20 MB');
 const buffer=await file.arrayBuffer();
 return new Promise((resolve,reject)=>{
  const worker=new Worker('sap-worker.js');
  const timer=setTimeout(()=>{worker.terminate();reject(Error('อ่านไฟล์ใช้เวลานานเกินไป กรุณาตรวจไฟล์ SAP หรือลองไฟล์ขนาดเล็กลง'));},60000);
  const finish=()=>{clearTimeout(timer);worker.terminate();};
  worker.onmessage=e=>{finish();if(e.data.error)reject(Error(e.data.error));else resolve(e.data.result);};
  worker.onerror=()=>{finish();reject(Error('อ่าน Excel ไม่สำเร็จ กรุณาตรวจรูปแบบไฟล์ SAP'));};
  worker.postMessage({name:file.name,buffer},[buffer]);
 });
}
async function importFile(file,day){
 SAPParser.validDay(day);
 if(serverMode){
  const content=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(file);});
  const r=await fetch('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:file.name,day,content})});const result=await r.json();if(!r.ok)throw Error(result.error);return result;
 }
 const result=await parse(file);const snapshot=SAPParser.validateSnapshot({day,source:file.name,...result});
 await merge([snapshot],true);
 return {count:Object.keys(snapshot.jobs).length,buckets:snapshot.buckets,warnings:result.warnings};
}
async function restore(payload){
 if(serverMode){const r=await fetch('/api/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const result=await r.json();if(!r.ok)throw Error(result.error);return result;}
 return merge(SAPParser.validateBackup(payload));
}
window.SAPStore={load,importFile,restore,serverMode};
})();
