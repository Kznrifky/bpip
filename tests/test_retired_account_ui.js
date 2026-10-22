'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../web/js/app.js'), 'utf8');
const shell = source.slice(source.indexOf('function renderShell()'), source.indexOf('async function renderRoute()'));
const refresh = source.slice(source.indexOf('async function refreshData()'), source.indexOf('function updateNavCount()'));
for (const role of ['petugas','sol','boh','checker']) {
 test(role+' navigation and refresh do not expose account management', async()=>{
  const requests=[];
  const context=vm.createContext({
   state:{user:{role,name:'Test User'},config:{mail_mode:'console'},customerUpdates:[]},app:{innerHTML:''},
   sidebarBrand:()=>'',icon:()=>'',profileDisplayName:()=> 'Test User',esc:value=>value,
   $:()=>null,updateNavCount:()=>{},
   api:async path=>{requests.push(path);return path==='/documents'?{documents:[]}:path==='/customers'?{customers:[]}:path==='/customer-edit-requests'?{requests:[]}:{user:{role,name:'Test User'},csrf:'test'};}
  });
  vm.runInContext(shell+refresh,context);
  await context.refreshData();context.renderShell();
  assert.match(context.app.innerHTML,/data-route="dashboard"/);
  if(role!=='boh')assert.match(context.app.innerHTML,/data-route="settings"/);
  assert.doesNotMatch(context.app.innerHTML,/data-route="accounts"|Persetujuan Akun|Kelola Akun/);
  assert.ok(!requests.some(path=>/officer|accounts/.test(path)));
  if(role==='checker'){assert.doesNotMatch(context.app.innerHTML,/Pemeriksaan|data-route="documents"/);assert.match(context.app.innerHTML,/data-route="customers"/);assert.match(context.app.innerHTML,/data-route="customer-updates"/);assert.doesNotMatch(context.app.innerHTML,/data-route="initiate"/);assert.ok(requests.includes('/customers'));assert.ok(requests.includes('/customer-edit-requests'));}
  if(role==='boh'){
   assert.match(context.app.innerHTML,/data-route="history"/);
   assert.doesNotMatch(context.app.innerHTML,/data-route="customer-updates"|data-route="customers"|data-route="documents"|data-route="initiate"|data-route="emails"|data-route="settings"/);
   assert.deepEqual(requests,['/documents','/session']);
  }
 });
}
test('BOH cannot reach business actions by entering a hidden route',async()=>{
 const routeCode=source.slice(source.indexOf('async function renderRoute()'),source.indexOf('const kpiLabels='));
 for(const route of ['customer-updates','customers','customer/1234567','documents','initiate','revise/SI-test','archive/documents','emails','settings']){
  const destinations=[];
  const context=vm.createContext({state:{user:{role:'boh'},route:'dashboard'},routeNow:()=>route,$:()=>({}),go:value=>destinations.push(value)});
  vm.runInContext(routeCode,context);
  await context.renderRoute();
  assert.deepEqual(destinations,['dashboard'],route);
 }
});
