/* Shared validation for SAP imports and portable history. No network access. */
(function(root){
'use strict';
const WBS=/\.([A-Z0-9]+)\.([23]\d{3})$/;
const GROUPS=['HB','JA','M4'];
function cents(value){
 if(value===null||value===undefined||value===''||value==='-')return 0;
 const n=Number(String(value).replace(/,/g,'').trim());
 const c=Math.round(n*100);
 if(!Number.isFinite(n)||!Number.isSafeInteger(c))throw Error('จำนวนเงินไม่ถูกต้อง');
 return c;
}
function validDay(day){
 if(typeof day!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(day)||Number.isNaN(Date.parse(day+'T00:00:00Z'))||new Date(day+'T00:00:00Z').toISOString().slice(0,10)!==day)throw Error('วันที่ข้อมูลไม่ถูกต้อง');
 return day;
}
function csvRows(text){
 text=text.replace(/^\ufeff/,'');
 const first=text.split(/\r?\n/)[0]||'';
 const delimiter=first.includes('\t')?'\t':first.includes(';')?';':',';
 const rows=[];let row=[],cell='',quoted=false;
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(c==='"'){
   if(quoted&&text[i+1]==='"'){cell+='"';i++;}
   else if(quoted){quoted=false;}
   else if(cell===''){quoted=true;}
   else cell+=c;
  }else if(!quoted&&c===delimiter){row.push(cell);cell='';}
  else if(!quoted&&(c==='\n'||c==='\r')){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);rows.push(row);row=[];cell='';}
  else cell+=c;
 }
 if(quoted)throw Error('CSV มีเครื่องหมายคำพูดไม่ครบ');
 if(cell!==''||row.length){row.push(cell);rows.push(row);}
 return rows;
}
function parseTables(tables){
 const jobs=Object.create(null),seen=new Map(),buckets=new Set(),warnings=[];
 for(const table of tables){
  const rows=table.rows;
  const hi=rows.slice(0,25).findIndex(r=>String(r?.[0]??'').trim()==='Lv'&&r.some(h=>String(h??'').trim()==='งบประมาณปัจจุบัน'));
  if(hi<0)continue;
  const headers=rows[hi].map(h=>String(h??'').trim());
  for(const field of ['ข้อกำหนดโครงการ /WBS','งบประมาณปัจจุบัน','รวม Act.ทั้งหมดที่ควบคุม งปม.','งบประมาณคงเหลือ']){
   if(!headers.includes(field))throw Error('ขาดคอลัมน์ SAP: '+field);
  }
  const index=Object.fromEntries(headers.filter(Boolean).map(h=>[h,headers.indexOf(h)]));
  const get=(r,k)=>index[k]===undefined?null:(r[index[k]]??null);
  for(let i=hi+1;i<rows.length;i++){
   const row=rows[i],wbs=String(get(row,'ข้อกำหนดโครงการ /WBS')??'').trim(),match=WBS.exec(wbs);
   if(!match||!GROUPS.includes(match[1]))continue;
   const bucket=match[2][0]+'xxx';buckets.add(bucket);
   if(Number(get(row,'Lv'))!==5)continue;
   const textFields=['ข้อกำหนดโครงการ /WBS','คำอธิบายภาษาไทย','Status','สถานะ'];
   const signature=JSON.stringify(headers.slice(0,24).map(k=>textFields.includes(k)?String(get(row,k)??'').trim():cents(get(row,k))));
   if(seen.has(wbs)){
    if(seen.get(wbs)===signature){warnings.push('ตัดแถวซ้ำที่เหมือนกัน: '+wbs);continue;}
    throw Error('WBS ซ้ำและข้อมูลขัดแย้ง: '+wbs+' แถว '+(i+1));
   }
   seen.set(wbs,signature);
   const sap=String(get(row,'Status')??'').trim();
   const status=String(get(row,'สถานะ')??'').trim()||(sap.includes('//')?sap.split('//').at(-1).trim():'ไม่ระบุ');
   jobs[wbs]={wbs,name:String(get(row,'คำอธิบายภาษาไทย')??''),group:match[1],bucket,year:/^I-(\d{2})-/.exec(wbs)?.[1]||'',status,sap,
    budget:cents(get(row,'งบประมาณปัจจุบัน')),actual:cents(get(row,'รวม Act.ทั้งหมดที่ควบคุม งปม.')),remaining:cents(get(row,'งบประมาณคงเหลือ')),
    material:cents(get(row,'Plan ค่าวัสดุ')),expense:cents(get(row,'Plan คชจ.หน้างาน'))};
  }
 }
 if(!Object.keys(jobs).length)throw Error('ไม่พบงาน Lv 5 ในชีต SAP ดิบที่มีงบประมาณปัจจุบัน กรุณาเลือกไฟล์ Export ดิบ ไม่ใช่ชีตสรุป');
 return {jobs,buckets:[...buckets].sort(),warnings};
}
function validateSnapshot(s){
 if(!s||typeof s!=='object')throw Error('ไฟล์สำรองไม่ถูกต้อง');
 validDay(s.day);
 if(typeof s.source!=='string'||!s.jobs||typeof s.jobs!=='object'||Array.isArray(s.jobs)||!Array.isArray(s.buckets)||s.buckets.some(b=>!['2xxx','3xxx'].includes(b)))throw Error('โครงสร้างประวัติไม่ถูกต้อง');
 const jobs=Object.create(null);
 for(const [wbs,j] of Object.entries(s.jobs)){
  const m=WBS.exec(wbs);
  if(!m||!j||j.wbs!==wbs||!GROUPS.includes(j.group)||j.group!==m[1]||j.bucket!==m[2][0]+'xxx'||!s.buckets.includes(j.bucket))throw Error('WBS หรือกลุ่มงบในไฟล์สำรองไม่ถูกต้อง');
  const job={wbs,group:j.group,bucket:j.bucket};
  for(const k of ['name','year','status','sap']){if(typeof j[k]!=='string')throw Error('ข้อมูลข้อความในไฟล์สำรองไม่ถูกต้อง');job[k]=j[k];}
  for(const k of ['budget','actual','remaining','material','expense']){if(!Number.isSafeInteger(j[k]))throw Error('จำนวนเงินในไฟล์สำรองไม่ถูกต้อง');job[k]=j[k];}
  jobs[wbs]=job;
 }
 return {day:s.day,source:s.source,jobs,buckets:[...new Set(s.buckets)].sort(),warnings:Array.isArray(s.warnings)?s.warnings.filter(w=>typeof w==='string'):[]};
}
function validateBackup(payload){
 if(!payload||payload.version!==1||!Array.isArray(payload.snapshots))throw Error('ไฟล์สำรองไม่ถูกต้อง');
 const snapshots=payload.snapshots.map(validateSnapshot),days=new Set();
 for(const s of snapshots){if(days.has(s.day))throw Error('วันที่ซ้ำในไฟล์สำรอง');days.add(s.day);}
 return snapshots;
}
function sameSnapshot(a,b){
 const canonical=s=>JSON.stringify({buckets:[...s.buckets].sort(),jobs:Object.keys(s.jobs).sort().map(w=>Object.keys(s.jobs[w]).sort().map(k=>[k,s.jobs[w][k]]))});
 return canonical(a)===canonical(b);
}
const api={cents,validDay,csvRows,parseTables,validateSnapshot,validateBackup,sameSnapshot};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.SAPParser=api;
})(typeof self!=='undefined'?self:globalThis);
