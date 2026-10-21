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

test('SOL can open the customer edit form; AMOL can add customers but cannot submit edits',()=>{
 for(const role of ['checker','sol','boh','petugas']){
  const {context,dialog}=contextFor(role);vm.runInContext(take('newCustomer','renderEmails'),context);
  context.newCustomer(fixture);
  assert.equal(dialog.opened,role==='checker',role+' edit');
  if(role==='checker'){assert.match(dialog.innerHTML,/Ajukan ke AMOL/);assert.doesNotMatch(dialog.innerHTML,/BOH/);}
  dialog.opened=false;context.newCustomer();assert.equal(dialog.opened,role==='sol',role+' add');
 }
});

test('Customer directory puts editing on SOL and keeps existing add/delete controls on AMOL',()=>{
 for(const role of ['checker','sol']){
  const {context,element}=contextFor(role);vm.runInContext(take('renderCustomers','renderCustomerTable'),context);context.renderCustomers();
  const html=element('#main').innerHTML;
  assert.equal(html.includes('data-action="select-customer-edit"'),role==='checker');
  assert.equal(html.includes('data-action="select-customers"'),role==='sol');
  assert.equal(html.includes('data-action="new-customer"'),role==='sol');
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
