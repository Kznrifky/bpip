"""Customer deletion is a maker/checker request, preserving transaction evidence."""
import concurrent.futures
import json
import unittest
import test_app as workflow

app, Client = workflow.app, workflow.Client


class CustomerDeletionTests(unittest.TestCase):
    setUp = workflow.WorkflowTests.setUp
    tearDown = workflow.WorkflowTests.tearDown
    create = workflow.WorkflowTests.create
    token = workflow.WorkflowTests.token
    respond = workflow.WorkflowTests.respond
    customer_edit = workflow.WorkflowTests.customer_edit
    delete_customers = workflow.WorkflowTests.delete_customers
    boh_client = workflow.WorkflowTests.boh_client

    def review(self, request_id, decision='approved', client=None, **extra):
        return (client or self.sol).call('/customer-edit-requests/' + request_id + '/review', {'decision': decision, **extra})

    def test_pending_survives_restart_and_approved_delete_preserves_document_files_links_and_audit(self):
        doc = self.create();token = self.token(doc)
        before = self.maker.call('/documents/' + doc)[1]['document']
        with app.database() as db:
            counts = [db.execute('SELECT COUNT(*) FROM ' + table + ' WHERE doc_id=?', (doc,)).fetchone()[0] for table in ('versions','outbox','audit')]
        status, result, _ = self.delete_customers(['1234567'])
        self.assertEqual(status, 201, result);request_id = result['ids'][0]
        self.assertTrue(any(c['cif']=='1234567' for c in self.maker.call('/customers')[1]['customers']))
        app.initialize()
        self.assertEqual(self.review(request_id)[0], 200)
        self.assertFalse(any(c['cif']=='1234567' for c in self.maker.call('/customers')[1]['customers']))
        self.assertEqual(self.maker.call('/documents/' + doc)[1]['document'], before)
        self.assertEqual(self.maker.call('/documents/' + doc + '/file')[0], 200)
        self.assertEqual(self.respond(token)[0], 200)
        with app.database() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM archived_customers').fetchone()[0], 0)
            for table, count in zip(('versions','outbox','audit'), counts):
                self.assertGreaterEqual(db.execute('SELECT COUNT(*) FROM '+table+' WHERE doc_id=?',(doc,)).fetchone()[0], count)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM management_audit WHERE action LIKE 'AMOL menyetujui penghapusan nasabah:%'").fetchone()[0],1)
        self.assertEqual(self.review(request_id)[0],409)

    def test_rejection_preserves_master_and_requires_reason_then_allows_resubmission(self):
        request_id=self.delete_customers(['1234567'])[1]['ids'][0]
        self.assertEqual(self.review(request_id,'rejected',notes=' ')[0],400)
        self.assertEqual(self.review(request_id,'rejected',notes='Nasabah masih aktif')[0],200)
        self.assertTrue(any(c['cif']=='1234567' for c in self.maker.call('/customers')[1]['customers']))
        self.assertEqual(self.delete_customers(['1234567'])[0],201)

    def test_submit_roles_csrf_and_authoritative_identity(self):
        payload={'customers':[{'cif':'1234567','revision':0}], 'reason':'Tidak digunakan', 'status':'approved','requested_by':'forged'}
        for client in (self.sol,self.maker,self.boh_client()):
            self.assertEqual(client.call('/customer-delete-requests',payload)[0],403)
        self.assertEqual(self.customer.call('/customer-delete-requests',payload)[0],401)
        self.assertEqual(self.checker.call('/customer-delete-requests',payload,csrf=False)[0],403)
        result=self.checker.call('/customer-delete-requests',payload);self.assertEqual(result[0],201)
        request_id=result[1]['ids'][0]
        for client in (self.checker,self.maker):self.assertEqual(self.review(request_id,client=client)[0],403)
        self.assertEqual(self.sol.call('/customer-edit-requests/'+request_id+'/review',{'decision':'approved'},csrf=False)[0],403)
        request=next(r for r in self.sol.call('/customer-edit-requests')[1]['requests'] if r['id']==request_id)
        self.assertEqual(request['status'],'pending');self.assertNotEqual(request['requested_by'],'forged')
        self.assertEqual(request['old_data']['name'],'PT Maju Bersama');self.assertEqual(request['new_data'],{})

    def test_validation_and_multi_customer_submission_are_atomic(self):
        good={'cif':'1234567','revision':0}
        for selected in ([], [good,good], [{'cif':'bad','revision':0}], [{'cif':'1234567','revision':True}], [{'cif':'1234567'}], ['1234567']):
            self.assertEqual(self.checker.call('/customer-delete-requests',{'customers':selected,'reason':'Tidak digunakan'})[0],400)
        self.assertEqual(self.checker.call('/customer-delete-requests',{'customers':[good],'reason':''})[0],400)
        for selected in ([good,{'cif':'9876543','revision':1}], [good,{'cif':'999999','revision':0}]):
            self.assertEqual(self.checker.call('/customer-delete-requests',{'customers':selected,'reason':'Tidak digunakan'})[0],409)
        self.assertEqual(self.sol.call('/customer-edit-requests')[1]['requests'],[])
        ids=self.delete_customers(['1234567','9876543'])[1]['ids']
        self.assertEqual(len(ids),2)
        self.assertEqual(self.review(ids[0])[0],200)
        self.assertEqual(self.review(ids[1],'rejected',notes='Masih dipakai')[0],200)
        self.assertEqual(len(self.maker.call('/customers')[1]['customers']),2)

    def test_pending_delete_blocks_edits_and_duplicates_and_stale_approval_is_rejected(self):
        payload=self.customer_edit()
        request_id=self.delete_customers(['1234567'])[1]['ids'][0]
        self.assertEqual(self.delete_customers(['1234567'])[0],409)
        self.assertEqual(self.checker.call('/customers/1234567/edit-requests',payload)[0],409)
        self.assertEqual(self.checker.call('/customers/1234567/phone',{'phone':'081234567891'})[0],409)
        with app.database(True) as db:db.execute("UPDATE customers SET name='External change',revision=revision+1 WHERE cif='1234567'")
        self.assertEqual(self.review(request_id)[0],409)
        self.assertEqual(self.review(request_id,'rejected',notes='Data berubah')[0],200)

    def test_concurrent_deletion_submissions_and_decisions_only_apply_once(self):
        other=Client(self.url);session=other.call('/login',{'email':'sol@example.test','password':'SolCheckerDemo!2026'})[1];other.csrf=session['csrf']
        payload={'customers':[{'cif':'1234567','revision':0}],'reason':'Tidak digunakan'}
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results=list(pool.map(lambda client:client.call('/customer-delete-requests',payload),[self.checker,other]))
        self.assertEqual(sorted(r[0] for r in results),[201,409])
        request_id=next(r[1]['ids'][0] for r in results if r[0]==201)
        other_amol=Client(self.url);other_amol.login('sol')
        with concurrent.futures.ThreadPoolExecutor() as pool:
            statuses=list(pool.map(lambda client:self.review(request_id,client=client)[0],[self.sol,other_amol]))
        self.assertEqual(sorted(statuses),[200,409])

    def test_requester_cannot_review_own_legacy_deletion(self):
        request_id=self.delete_customers(['1234567'])[1]['ids'][0]
        with app.database(True) as db:
            user=db.execute("SELECT id FROM users WHERE email='sol@bpip.local'").fetchone()[0]
            db.execute('UPDATE customer_edit_requests SET requested_by=? WHERE id=?',(user,request_id))
        self.assertEqual(self.review(request_id)[0],403)
        self.assertEqual(self.review(request_id,'rejected',notes='Own request')[0],403)
