importScripts('sap-parser.js');
self.onmessage=e=>{
 try{
  const {name,buffer}=e.data;
  let tables;
  if(/\.(csv|txt)$/i.test(name)){
   let text;
   try{text=new TextDecoder('utf-8',{fatal:true}).decode(buffer);}
   catch(_){text=new TextDecoder('windows-874').decode(buffer);}
   tables=[{name,rows:SAPParser.csvRows(text)}];
  }else{
   importScripts('vendor/xlsx.full.min.js');
   const book=XLSX.read(buffer,{type:'array',raw:true,cellDates:false,cellFormula:false,cellHTML:false,codepage:65001});
   tables=book.SheetNames.map(name=>({name,rows:XLSX.utils.sheet_to_json(book.Sheets[name],{header:1,raw:true,defval:null,blankrows:true})}));
  }
  self.postMessage({result:SAPParser.parseTables(tables)});
 }catch(error){self.postMessage({error:error.message||'อ่านไฟล์ไม่สำเร็จ'});}
};
