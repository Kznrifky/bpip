'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../web/js/app.js'), 'utf8');
const context = vm.createContext({state: {documents: []}});
for (const name of ['finalStatus', 'activeDocuments', 'historyOutcome', 'kpiReviewStatus', 'dashboardCounts', 'renderSolDecision', 'bindDocumentRows']) {
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

test('Refreshing a customer or SOL decision moves a record to history without deleting it', () => {
  const pending = doc('same-id', 'confirmed', 'pending');
  const approved = {...pending, sol_status: 'approved'};
  context.state.documents = [pending];
  assert.equal(context.activeDocuments().length, 1);
  context.state.documents = [approved];
  assert.equal(context.activeDocuments().length, 0);
  assert.equal(context.state.documents[0].id, 'same-id');
  assert.equal(context.historyOutcome(context.state.documents[0]).result, 'success');
});

test('SOL has only approve/reject actions, including unfinished legacy revision requests', () => {
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
