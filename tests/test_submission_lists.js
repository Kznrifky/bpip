'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../web/js/app.js'), 'utf8');
const context = vm.createContext({state: {documents: []}});
for (const name of ['needsChecker', 'finalStatus', 'activeDocuments', 'historyOutcome', 'kpiReviewStatus', 'dashboardCounts', 'renderSolDecision', 'renderDocumentProgress', 'renderDualDocumentProgress', 'renderDualCustomerData', 'customerReviewText', 'bindDocumentRows', 'bindCustomerRows', 'renderCustomerTable', 'renderCustomerDetail', 'positionDateRange']) {
  const start = source.indexOf('function ' + name + '(');
  assert.ok(start >= 0, 'Missing ' + name);
  let cursor = source.indexOf('{', start), depth = 0, end;
  do {
    if (source[cursor] === '{') depth++;
    if (source[cursor] === '}') depth--;
    if (!depth) end = cursor + 1;
    cursor++;
  } while (depth);
  vm.runInContext(source.slice(start, end), context);
}
vm.runInContext(source.match(/^const kpiLabels=.*$/m)[0], context);
vm.runInContext(source.match(/^const kpiDocuments=.*$/m)[0], context);
vm.runInContext(source.match(/^const labels =.*$/m)[0], context);
vm.runInContext(source.match(/^const solLabels =.*$/m)[0], context);
context.esc = value => value;

const doc = (id, customer_status, sol_status, kind='Standing Instruction') => ({id, customer_status, sol_status, kind});
const rows = [
  doc('waiting-customer', 'pending', 'pending'),
  doc('waiting-sol', 'confirmed', 'pending'),
  doc('revision', 'confirmed', 'revision_requested'),
  doc('complete-si', 'confirmed', 'approved'),
  doc('complete-warkat', 'confirmed', 'approved', 'Warkat'),
  doc('customer-rejected', 'rejected', 'pending'),
  doc('sol-rejected', 'confirmed', 'rejected'),
  doc('cancelled', 'pending', 'cancelled'),
];

test('Only unfinished submissions stay active; both document kinds enter history', () => {
  assert.deepEqual(Array.from(context.activeDocuments(rows), d => d.id), ['waiting-customer', 'waiting-sol', 'revision']);
  assert.deepEqual(rows.filter(d => context.historyOutcome(d)).map(d => d.id), ['complete-si', 'complete-warkat', 'customer-rejected', 'sol-rejected', 'cancelled']);
});

test('Success requires both approvals; a customer rejection ends the active queue immediately', () => {
  assert.equal(context.historyOutcome(doc('incomplete', 'pending', 'approved')), null);
  assert.equal(context.historyOutcome(doc('complete', 'confirmed', 'approved')).result, 'success');
  assert.equal(context.historyOutcome(doc('rejected', 'rejected', 'pending')).label, 'Ditolak');
  assert.equal(context.finalStatus(doc('rejected', 'rejected', 'pending')), 'rejected');
});

test('History result filters distinguish successful and rejected submissions', () => {
  const filtered = result => rows.filter(d => context.historyOutcome(d)?.result === result).map(d => d.id);
  assert.deepEqual(filtered('success'), ['complete-si', 'complete-warkat']);
  assert.deepEqual(filtered('failure'), ['customer-rejected', 'sol-rejected', 'cancelled']);
  assert.deepEqual(filtered('cancelled'), []);
});

test('Dashboard KPIs and their detail lists exclude all terminal submissions', () => {
  const counts = context.dashboardCounts(rows);
  assert.equal(counts.total, 3);
  assert.equal(counts.pending, 1);
  assert.equal(counts.review, 2);
  context.state.documents = rows;
  assert.equal(vm.runInContext("kpiDocuments('total').length", context), 3);
  assert.equal(vm.runInContext("kpiDocuments('review',state.documents,'all').length", context), 2);
});

test('Refreshing a customer or AMOL decision moves a record to history without deleting it', () => {
  const pending = doc('same-id', 'confirmed', 'pending');
  const approved = {...pending, sol_status: 'approved'};
  context.state.documents = [pending];
  assert.equal(context.activeDocuments().length, 1);
  context.state.documents = [approved];
  assert.equal(context.activeDocuments().length, 0);
  assert.equal(context.state.documents[0].id, 'same-id');
  assert.equal(context.historyOutcome(context.state.documents[0]).result, 'success');
});

test('AMOL has only approve/reject actions, including unfinished legacy revision requests', () => {
  context.icon = () => '';
  context.notice = message => message;
  for (const sol of ['pending', 'revision_requested']) {
    const html = context.renderSolDecision(doc('ready', 'confirmed', sol));
    assert.equal((html.match(/<button/g) || []).length, 2);
    assert.ok(html.includes('data-decision="approved"'));
    assert.ok(html.includes('data-decision="rejected"'));
    assert.ok(!html.includes('Minta revisi'));
  }
  for (const record of [doc('rejected','rejected','pending'), doc('done','confirmed','approved')]) {
    assert.ok(!context.renderSolDecision(record).includes('<button'));
  }
});

test('Row navigation ignores interactive controls and selected text', () => {
  let clickHandler, navigated = '', closed = false, selection = '';
  const row = {dataset: {documentRow: 'SI-TEST'}, addEventListener: (_, fn) => {clickHandler = fn;}, closest: () => true};
  context.window = {getSelection: () => ({toString: () => selection})};
  context.dialog = {close: () => {closed = true;}};
  context.go = route => {navigated = route;};
  context.bindDocumentRows({querySelectorAll: () => [row]});
  clickHandler({target: {closest: () => true}});
  assert.equal(navigated, ''); // Checkbox, download button, or a name link handles its own action.
  selection = 'Copied document ID';
  clickHandler({target: {closest: () => null}});
  assert.equal(navigated, '');
  selection = '';
  clickHandler({target: {closest: () => null}});
  assert.equal(navigated, 'doc/SI-TEST');
  assert.equal(closed, true); // A row opened from the KPI dialog closes that dialog.
});

test('Rejected reviews use a cross and never a completed approval check', () => {
  context.icon = symbol => `<svg data-icon="${symbol}"></svg>`;
  const customer = context.renderDocumentProgress(doc('rejected', 'rejected', 'pending'));
  const customerStep = customer.match(/<li class="status-step rejected"[\s\S]*?<\/li>/)[0];
  assert.ok(customerStep.includes('data-icon="close"'));
  assert.ok(!customerStep.includes('data-icon="check"'));
  assert.ok(customer.includes('Tidak dilanjutkan'));
  const sol = context.renderDocumentProgress(doc('rejected-sol', 'confirmed', 'rejected'));
  const solStep = sol.match(/<li class="status-step rejected"[\s\S]*?<\/li>/)[0];
  assert.ok(solStep.includes('data-icon="close"'));
  assert.ok(solStep.includes('Review AMOL'));
  const approved = context.renderDocumentProgress(doc('done', 'confirmed', 'approved'));
  assert.equal((approved.match(/data-icon="check"/g) || []).length, 3);
  assert.ok(!approved.includes('status-step rejected'));
});


test('Partial two-verifier approval remains in customer review and cannot open AMOL actions', () => {
  const partial = {...doc('dual-partial', 'pending', 'pending'), verification:{required:2, confirmed:1, verifiers:[{position:1,status:'confirmed'},{position:2,status:'pending'}]}};
  assert.equal(context.customerReviewText(partial, 'Menunggu'), 'Menunggu verifikator lainnya');
  assert.equal(context.kpiReviewStatus('pending', partial), 'pending');
  assert.equal(context.kpiReviewStatus('review', partial), null);
  assert.equal(context.historyOutcome(partial), null);
  assert.ok(!context.renderSolDecision(partial).includes('data-decision="approved"'));
  assert.ok(context.renderDocumentProgress(partial).includes('Verifikator 2'));
  assert.equal((context.renderDocumentProgress(partial).match(/<li /g)||[]).length, 4);
  const complete = {...partial, customer_status:'confirmed', verification:{required:2, confirmed:2}};
  assert.equal(context.kpiReviewStatus('review', complete), 'pending');
  assert.ok(context.renderSolDecision(complete).includes('data-decision="approved"'));
});


test('Four detail steps track each verifier independently and stop after a rejection', () => {
  context.icon = symbol => `<svg data-icon="${symbol}"></svg>`;
  const dual = {...doc('dual', 'pending', 'pending'),verification:{required:2,confirmed:1,verifiers:[{position:1,status:'pending'},{position:2,status:'confirmed'}]}};
  const html=context.renderDocumentProgress(dual);
  const steps=html.match(/<li [\s\S]*?<\/li>/g);
  assert.equal(steps.length,4);
  assert.ok(steps[1].includes('current'));
  assert.ok(steps[1].includes('Verifikator 1'));
  assert.ok(steps[2].includes('complete'));
  assert.ok(steps[2].includes('Verifikator 2'));
  assert.ok(!html.includes('Review nasabah'));
  const rejected={...dual,customer_status:'rejected',verification:{required:2,confirmed:0,verifiers:[{position:1,status:'pending'},{position:2,status:'rejected'}]}};
  const stopped=context.renderDocumentProgress(rejected).match(/<li [\s\S]*?<\/li>/g);
  assert.ok(stopped[2].includes('data-icon="close"'));
  assert.ok(stopped[1].includes('Tidak dilanjutkan'));
  assert.ok(stopped[3].includes('Tidak dilanjutkan'));
  const single=context.renderDocumentProgress(doc('single','pending','pending'));
  assert.equal((single.match(/<li /g)||[]).length,3);
  assert.ok(single.includes('Review nasabah'));
});


test('Data Nasabah groups both verifier identities with their own phone and email', () => {
  const d={customer_name:'PT Contoh',cif:'777',account:'000123456789012',verification:{required:2,verifiers:[{position:1,name:'Adi',person:'Direktur',phone:'081111111111',email:'adi@example.test'},{position:2,name:'Maya',person:'Komisaris',phone:'082222222222',email:'maya@example.test'}]}};
  const html=context.renderDualCustomerData(d,(label,value)=>`<div>${label}: ${value}</div>`,'');
  assert.ok(html.includes('aria-label="Verifikator 1"'));
  assert.ok(html.includes('aria-label="Verifikator 2"'));
  for(const value of ['Adi','Maya','Direktur','Komisaris','081111111111','082222222222','adi@example.test','maya@example.test'])assert.ok(html.includes(value));
  assert.equal((html.match(/Nama Verifikator/g)||[]).length,2);
  assert.ok(!html.includes('Disetujui'));
  const single=context.renderDualCustomerData({customer_name:'PT Satu',cif:'123',account:'000123456789012',person:'Direktur',email:'satu@example.test',verification:{required:1,verifiers:[]}},(label,value)=>`<div>${label}: ${value||'Belum tercatat'}</div>`,'081234567890','Verifikator');
  assert.ok(single.includes('single-detail-verifiers'));
  assert.ok(single.includes('<h3>Verifikator</h3>'));
  assert.ok(!single.includes('<h3>Verifikator 1</h3>'));
  for(const value of ['Direktur','satu@example.test','081234567890'])assert.ok(single.includes(value));
});


test('Customer directory contains only the four requested columns', () => {
  const target={innerHTML:'',querySelectorAll:()=>[]}, count={};
  context.$=selector=>selector==='#customer-table'?target:selector==='#customer-list-count'?count:null;
  context.labelRecordTables=()=>{};
  Object.assign(context.state,{customerEditMode:false,customerDeleteMode:false,customerSearch:'',customerSelected:[],customerUpdates:[],customers:[{cif:'123',name:'PT Satu',account:'000123456789012',person:'Direktur',email:'private@example.test',phone:'081234567890',verification_count:1},{cif:'456',name:'PT Dua',account:'000987654321012',verification_count:2}]});
  context.renderCustomerTable();
  const html=target.innerHTML;
  assert.equal((html.match(/<th>/g)||[]).length,4);
  for(const label of ['Nama Nasabah','Nomor Rekening','CIF','Jumlah Verifikator'])assert.ok(html.includes('<th>'+label+'</th>'));
  assert.ok(!html.includes('private@example.test'));
  assert.ok(html.includes('href="#customer/123"'));
  assert.ok(html.includes('data-customer-detail="456"'));
  context.state.customerEditMode=true;
  context.document={querySelectorAll:()=>[]};
  context.renderCustomerTable();
  assert.ok(target.innerHTML.includes('data-customer-pick="123"'));
  assert.ok(!target.innerHTML.includes('data-customer-detail='));
  context.state.customerEditMode=false;
});

test('Customer row click and keyboard open details without intercepting controls or selected text', () => {
  let selected='',route='';const handlers={};
  const row={dataset:{customerDetail:'123'},addEventListener:(type,fn)=>{handlers[type]=fn;}};
  context.window={getSelection:()=>({toString:()=>selected})};
  context.go=value=>{route=value;};context.bindCustomerRows({querySelectorAll:()=>[row]});
  handlers.click({target:{closest:()=>true}});assert.equal(route,'');
  selected='PT Satu';handlers.click({target:{closest:()=>null}});assert.equal(route,'');
  selected='';handlers.click({target:{closest:()=>null}});assert.equal(route,'customer/123');
  route='';let prevented=false;handlers.keydown({target:row,key:'Enter',preventDefault:()=>{prevented=true;}});
  assert.equal(route,'customer/123');assert.ok(prevented);
});

test('Customer detail uses the same grouped style with one or two verifier boxes', () => {
  const main={innerHTML:''};context.$=()=>main;
  context.icon=symbol=>`<svg>${symbol}</svg>`;
  context.state.customers=[{cif:'123',name:'PT Satu',account:'000123456789012',person:'Direktur',email:'satu@example.test',phone:'081234567890',verification_count:1},{cif:'456',name:'PT Dua',account:'000987654321012',person:'Direktur',email:'dua@example.test',phone:'081234567890',verification_count:2,verifier_name:'Adi',second_name:'Maya',second_person:'Komisaris',second_email:'maya@example.test',second_phone:'082234567890'}];
  context.renderCustomerDetail('123');
  for(const label of ['Nama nasabah','Nomor rekening','CIF','Nama Verifikator','Jabatan Verifikator','Email Verifikator','Nomor HP'])assert.ok(main.innerHTML.includes('<span>'+label+'</span>'));
  assert.ok(main.innerHTML.includes('single-detail-verifiers'));
  assert.ok(main.innerHTML.includes('aria-label="Verifikator 1"'));
  assert.ok(!main.innerHTML.includes('aria-label="Verifikator 2"'));
  assert.ok(main.innerHTML.includes('Belum tercatat'));
  context.renderCustomerDetail('456');
  assert.ok(main.innerHTML.includes('aria-label="Verifikator 1"'));
  assert.ok(main.innerHTML.includes('aria-label="Verifikator 2"'));
  assert.ok(!main.innerHTML.includes('single-detail-verifiers'));
  assert.ok(main.innerHTML.includes('082234567890'));
  assert.ok(main.innerHTML.includes('data-route="customers"'));
});


test('Date filter stays within the viewport near screen edges and releases desktop coordinates on mobile', () => {
  let mobile=false;let bounds={top:398,bottom:442,right:1219};
  const panel={offsetWidth:320,offsetHeight:414,style:{removeProperty(key){delete this[key];}}};
  const picker={open:true},trigger={getBoundingClientRect:()=>bounds};
  context.$=selector=>({'#date-picker':picker,'#date-range-trigger':trigger,'#date-range-panel':panel}[selector]);
  context.window={innerWidth:1280,innerHeight:720,matchMedia:()=>({matches:mobile})};
  const fits=()=>{const x=parseFloat(panel.style.left),y=parseFloat(panel.style.top);assert.ok(x>=12&&x+panel.offsetWidth<=1268);assert.ok(y>=12&&y+panel.offsetHeight<=708);};
  context.positionDateRange();fits();
  bounds={top:30,bottom:74,right:200};context.positionDateRange();fits();
  assert.ok(parseFloat(panel.style.top)>bounds.bottom);
  mobile=true;context.positionDateRange();
  assert.equal(panel.style.left,undefined);assert.equal(panel.style.top,undefined);
  picker.open=false;context.positionDateRange();assert.equal(panel.style.top,undefined);
});

test('New flow has four single-verifier steps and five two-verifier steps',()=>{
 context.icon=symbol=>`<svg data-icon="${symbol}"></svg>`;
 const single={...doc('new','pending','pending'),review_flow:2,checker_status:'pending'};
 const dual={...single,verification:{required:2,confirmed:0,verifiers:[{position:1,status:'pending'},{position:2,status:'pending'}]}};
 for(const [record,count] of [[single,4],[dual,5]]){
  const html=context.renderDocumentProgress(record);
  assert.equal((html.match(/<li /g)||[]).length,count);
  assert.ok(html.indexOf('Review SOL')<html.indexOf('Review AMOL'));
 }
});
test('AMOL actions open only after SOL; checker rejection ends active processing',()=>{
 const pending={...doc('new','confirmed','pending'),review_flow:2,checker_status:'pending'};
 context.state.user={role:'sol'};
 assert.ok(!context.renderSolDecision(pending).includes('<button'));
 context.state.user={role:'checker'};
 assert.equal((context.renderSolDecision(pending).match(/<button/g)||[]).length,2);
 const approved={...pending,checker_status:'approved'};
 assert.ok(!context.renderSolDecision(approved).includes('<button'));
 context.state.user={role:'sol'};
 assert.equal((context.renderSolDecision(approved).match(/<button/g)||[]).length,2);
 const rejected={...pending,checker_status:'rejected'};
 assert.equal(context.historyOutcome(rejected).reason,'Ditolak SOL');
 assert.equal(context.activeDocuments([rejected]).length,0);
 assert.equal(context.finalStatus(pending),'checker');
 assert.equal(context.finalStatus(approved),'review');
 const checkerStep=context.renderDocumentProgress(rejected).match(/<li [\s\S]*?<\/li>/g);
 assert.ok(checkerStep[2].includes('status-step rejected'));
 assert.ok(checkerStep[3].includes('Tidak dilanjutkan'));
});
test('Checker and approver KPI queues advance independently',()=>{
 const waiting={...doc('wait','confirmed','pending'),review_flow:2,checker_status:'pending'};
 const checked={...waiting,id:'checked',checker_status:'approved'};
 assert.equal(context.kpiReviewStatus('checker',waiting),'pending');
 assert.equal(context.kpiReviewStatus('review',waiting),null);
 assert.equal(context.kpiReviewStatus('review',checked),'pending');
 assert.equal(context.kpiReviewStatus('checker',checked),'approved');
});
