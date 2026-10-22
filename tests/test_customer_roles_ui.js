'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../web/js/app.js'),'utf8');
const take=(name,next)=>source.slice(source.indexOf('function '+name+'('),source.indexOf('function '+next+'('));
const fixture={cif:'1234567',name:'PT Contoh',account:'000123456789012',person:'Direktur',email:'contoh@example.test',phone:'081234567890',revision:0};

function contextFor(role){
 const elements=new Map();
 const element=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',value:'1',classList:{toggle(){}},addEventListener(){}});return elements.get(id);};
 const dialog={innerHTML:'',opened:false,showModal(){this.opened=true;},querySelectorAll:()=>[]};
 const context=vm.createContext({state:{user:{role,id:'reviewer'},customerSearch:'',customers:[fixture],customerDeleteMode:false,customerEditMode:false,customerUpdates:[]},$:element,dialog,esc:value=>value??'',icon:()=>'',toast:()=>{},renderCustomerTable:()=>{},date:()=>'',customerChanges:()=>['name'],customerFieldLabels:{name:'Nama nasabah'},customerUpdateBadge:()=>''});
 return {context,element,dialog};
}

test('Only SOL can open customer edit and registration forms',()=>{
 for(const role of ['checker','sol','boh','petugas']){
  const {context,dialog}=contextFor(role);vm.runInContext(take('newCustomer','renderEmails'),context);
  context.newCustomer(fixture);
  assert.equal(dialog.opened,role==='checker',role+' edit');
  if(role==='checker'){assert.match(dialog.innerHTML,/Ajukan ke AMOL/);assert.doesNotMatch(dialog.innerHTML,/BOH/);}
  dialog.opened=false;context.newCustomer();assert.equal(dialog.opened,role==='checker',role+' add');
  if(role==='checker')assert.match(dialog.innerHTML,/Ajukan ke AMOL/);
 }
});

test('Only SOL has customer actions, with Add at the far right',()=>{
 for(const role of ['checker','sol','boh','petugas']){
  const {context,element}=contextFor(role);vm.runInContext(take('renderCustomers','renderCustomerTable'),context);context.renderCustomers();
  const html=element('#main').innerHTML;
  for(const action of ['select-customer-edit','select-customers','new-customer'])assert.equal(html.includes('data-action="'+action+'"'),role==='checker');
  if(role==='checker'){
   assert.ok(html.indexOf('data-action="select-customers"')<html.indexOf('data-action="select-customer-edit"'));
   assert.ok(html.indexOf('data-action="select-customer-edit"')<html.indexOf('data-action="new-customer"'));
  }
 }
});

test('Only a distinct AMOL account sees customer-change approval controls',()=>{
 for(const [role,requestedBy,status] of [['checker','requester','pending'],['sol','requester','pending'],['sol','reviewer','pending'],['sol','requester','approved']]){
  const {context,dialog}=contextFor(role);
  context.state.customerUpdates=[{id:'test',old_data:fixture,new_data:{...fixture,name:'PT Baru'},requested_by:requestedBy,requested_name:'SOL',status,reason:'Data terbaru'}];
  vm.runInContext(take('viewCustomerUpdate','renderArchive').replace(/async $/,''),context);
  context.viewCustomerUpdate('test');
  const allowed=role==='sol'&&requestedBy!=='reviewer'&&status==='pending';
  assert.equal(dialog.innerHTML.includes('data-customer-review="approved"'),allowed);
  assert.equal(dialog.innerHTML.includes('data-customer-review="rejected"'),allowed);
  assert.doesNotMatch(dialog.innerHTML,/BOH/);
 }
});

 test('New customer request displays its name and approval action without requiring an old master',()=>{
  const {context,dialog}=contextFor('sol');
  context.state.customerUpdates=[{id:'new',operation:'create',old_data:{},new_data:fixture,requested_by:'requester',requested_name:'SOL',status:'pending',reason:'Nasabah baru'}];
  vm.runInContext(take('viewCustomerUpdate','renderArchive').replace(/async $/,''),context);
  context.viewCustomerUpdate('new');
  assert.match(dialog.innerHTML,/PT Contoh/);
  assert.match(dialog.innerHTML,/Setujui nasabah/);
  assert.doesNotMatch(dialog.innerHTML,/undefined|Data nasabah tetap menggunakan data lama/);
 });

test('Deletion review describes the retained transaction history and uses a deletion decision',()=>{
 const {context,dialog}=contextFor('sol');
 context.state.customerUpdates=[{id:'delete',operation:'delete',old_data:fixture,new_data:{},requested_by:'requester',requested_name:'SOL',status:'pending',reason:'Tidak digunakan'}];
 vm.runInContext(take('viewCustomerUpdate','renderArchive').replace(/async $/,''),context);
 context.viewCustomerUpdate('delete');
 assert.match(dialog.innerHTML,/Setujui penghapusan/);assert.match(dialog.innerHTML,/Riwayat pengajuan tetap tersimpan/);
 assert.doesNotMatch(dialog.innerHTML,/undefined|Setujui perubahan/);
});
