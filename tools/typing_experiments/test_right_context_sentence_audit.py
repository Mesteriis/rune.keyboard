import copy
import hashlib
import unittest
from right_context_sentence_audit import audit_new_sentences,exclude_prior_contexts

SEED='authored-audit-tests'


def family(part):
    for i in range(100):
        value='семья'+str(i)
        found='calibration' if hashlib.sha256((SEED+':family:'+value).encode()).digest()[0]%2==0 else 'holdout'
        if found==part:return value


def context(part,article,prefix):
    f=family(part);word='готов';suffix=' люди дома ';key=hashlib.sha256((' '.join((prefix+' '+word+suffix).casefold().split())).encode()).hexdigest()
    base=dict(split=part,language='ru',contextHash=key,family=f,families=[f],article=article,prefix=prefix,word=word,rival='готовы',sideGroup='authored')
    return [base|dict(id=part+'-'+kind,group=kind,typed=typed,expectedSpelling=typed if control else word,rightContext=right,noAuto=control,retainBaseline=retain)
        for kind,typed,right,control,retain in [('typo','готв',suffix,False,False),('unfinished','готв',' люди',False,True),
            ('correct',word,suffix,True,False),('correct_rival','готовы',suffix,True,False),('protected','@'+word,suffix,True,False)]]


class SentenceAuditTest(unittest.TestCase):
    def parts(self):return dict(calibration=context('calibration','101','тогда'),holdout=context('holdout','202','потом'))
    def audit(self,parts,prior=()):return audit_new_sentences(parts,list(prior),['обученный'],seed=SEED)

    def test_new_sentences_of_a_previously_evaluated_family_are_allowed_and_reported(self):
        parts=self.parts();before=copy.deepcopy(parts);result=self.audit(parts,[dict(article='999',family=family('holdout'))])
        self.assertTrue(result['passed']);self.assertEqual(1,result['parts']['holdout']['previouslyBoundFamilies']);self.assertEqual(before,parts)

    def test_same_phrase_in_another_article_is_still_a_prior_context_overlap(self):
        parts=self.parts();result=self.audit(parts,[dict(article='999',contextHash=parts['holdout'][0]['contextHash'])])
        self.assertFalse(result['passed']);self.assertTrue(result['parts']['holdout']['priorContextOverlap'])

    def test_legacy_manifest_family_counts_are_not_mistaken_for_declared_families(self):
        result=self.audit(self.parts(),[dict(families=42)])
        self.assertTrue(result['passed']);self.assertEqual(0,result['parts']['holdout']['previouslyBoundFamilies'])

    def test_prior_context_exclusion_is_explicit_whole_group_and_does_not_mutate_inputs(self):
        parts=self.parts();before=copy.deepcopy(parts);prior=[dict(article='999',contextHash=parts['holdout'][0]['contextHash'])]
        kept,report=exclude_prior_contexts(parts,prior)
        self.assertEqual(parts,before);self.assertEqual(parts['calibration'],kept['calibration'])
        self.assertEqual([],kept['holdout']);self.assertEqual(5,report['holdout']['removedRows'])
        self.assertEqual(0,report['calibration']['removedRows'])
        self.assertTrue(self.audit(kept,prior)['passed'])
        with self.assertRaises(ValueError):exclude_prior_contexts(dict(calibration=[{}],holdout=[]),prior)

    def test_supervised_families_and_old_articles_are_not_silently_readmitted(self):
        parts=self.parts();self.assertFalse(self.audit(parts,[dict(article='202')])['passed'])
        result=audit_new_sentences(parts,[],[family('calibration')],seed=SEED)
        self.assertFalse(result['passed']);self.assertEqual([family('calibration')],result['parts']['calibration']['trainingFamilyOverlap'])

    def test_all_variants_labels_and_source_hashes_are_audited(self):
        for key,value in [('expectedSpelling','чужое'),('rightContext',' другие '),('noAuto',False)]:
            parts=self.parts();parts['calibration'][2][key]=value
            with self.assertRaises(ValueError):self.audit(parts)
        parts=self.parts();parts['holdout'].pop()
        with self.assertRaises(ValueError):self.audit(parts)
        parts=self.parts()
        for row in parts['holdout']:row['contextHash']='0'*64
        with self.assertRaises(ValueError):self.audit(parts)

    def test_family_partition_is_fixed_even_when_articles_and_contexts_are_different(self):
        parts=self.parts()
        for row in parts['holdout']:row['family']=family('calibration');row['families']=[row['family']]
        result=self.audit(parts);self.assertFalse(result['passed']);self.assertTrue(result['crossPartOverlap']['families'])
        self.assertTrue(result['parts']['holdout']['familyPartitionMismatch'])


if __name__=='__main__':unittest.main()
