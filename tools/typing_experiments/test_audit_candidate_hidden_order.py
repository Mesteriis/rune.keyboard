import unittest
from audit_candidate_hidden_order import measure
from test_audit_candidate_strip_utility import fixture


class HiddenOrderTest(unittest.TestCase):
    def test_hidden_target_and_existing_visible_prefix(self):
        row,obs,identity=fixture()
        first={'id':'a','text':'готово'}
        obs['candidateView']={'candidates':[dict(first,role='CORRECTION')]}
        obs['fullCandidateOrder']=[first,{'id':'b','text':'где'},{'id':'c','text':'готовы'}]
        result=measure([row],[obs],[obs],[identity])['languages']['ru']
        self.assertEqual(1,result['hidden3to7_on']);self.assertEqual(1,result['hidden3to7_off'])
        changed=obs|{'fullCandidateOrder':[{'id':'z','text':'другой'}]+obs['fullCandidateOrder']}
        with self.assertRaisesRegex(ValueError,'HIDDEN_ORDER_VISIBLE_MISMATCH'):measure([row],[changed],[obs],[identity])

    def test_duplicate_id_and_missing_row_fail(self):
        row,obs,identity=fixture();item={'id':'a','text':'готово'}
        obs['candidateView']={'candidates':[dict(item,role='CORRECTION')]};obs['fullCandidateOrder']=[item,item]
        with self.assertRaisesRegex(ValueError,'HIDDEN_ORDER_DUPLICATE'):measure([row],[obs],[obs],[identity])
        with self.assertRaises(ValueError):measure([row],[],[obs],[identity])


if __name__=='__main__':unittest.main()
