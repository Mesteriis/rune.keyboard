import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import ewt_product_replay as subject


def sentence(token, misc):
    return (f'# text = we see {token}\n'
            '1\twe\twe\tPRON\t_\t_\t0\troot\t_\t_\n'
            '2\tsee\tsee\tVERB\t_\t_\t1\tdep\t_\t_\n'
            f'3\t{token}\t_\tX\t_\t_\t1\tdep\t_\t{misc}\n').encode()


class EwtProductReplayTest(unittest.TestCase):
    def test_exact_alignment_separates_labels_and_unannotated_controls(self):
        data={'en_ewt-ud-train.conllu':sentence('teh','CorrectForm=the'),
              'en_ewt-ud-test.conllu':sentence('cot','_')}
        rows,labels,stats=subject.extract(data,{'the':10,'cat':5},set())
        self.assertEqual(2,len(rows))
        self.assertEqual({'test:unannotated-unknown':1,'train:annotated':1},stats)
        self.assertEqual({'id','split','language','prefix','typed'},set(rows[0]))
        self.assertNotIn('expected',rows[0])
        self.assertEqual({'annotated','unannotated-unknown'},{row['kind'] for row in labels})
        self.assertIn('the',{row['expected'] for row in labels})
        rows,_,_=subject.extract(data,{'the':10,'cat':5},{'cot'})
        self.assertEqual(1,len(rows))

    def test_multiword_and_misaligned_sentences_cannot_generate_rows(self):
        a=sentence('teh','CorrectForm=the').decode()
        multi=a.replace('1\twe\t','1-2\twe\t',1)
        wrong=a.replace('# text = we see teh','# text = we missed teh')
        with self.assertRaisesRegex(ValueError,'EWT_REPLAY_EMPTY'):
            subject.extract({'en_ewt-ud-test.conllu':(multi+'\n'+wrong).encode()},{},set())

    def test_summary_requires_exact_replay_input_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();data=root/'data';run=root/'run';data.mkdir();run.mkdir()
            row=dict(id='row-1',split='holdout',language='en',prefix='we see',typed='teh')
            label=dict(id='row-1',kind='annotated',expected='the',part='test')
            obs=dict(split='holdout',language='en',prefix='we see',typed='teh',
                beforeBoundary={'text':'we see teh'},afterBoundary={'text':'we see teh '},afterBackspace={'text':'we see teh'},
                fullTokenGeneration={'completion':'COMPLETE','alternatives':[{'language':'en','text':'the'}]},automaticAdmissionAllowed=False)
            for path,value in ((data/'inputs.jsonl',row),(data/'labels.jsonl',label),(run/'projection.jsonl',obs)):
                path.write_text(json.dumps(value)+'\n')
            sha=lambda path:subject.model.sha(path.read_bytes())
            (data/'manifest.json').write_text(json.dumps(dict(scope='disclosed-ewt-replay-not-qualification',independentQualification=False,
                inputSha256=sha(data/'inputs.jsonl'),labelSha256=sha(data/'labels.jsonl'),analyzerSha256=sha(Path(subject.__file__)))))
            receipt=dict(status='COMPLETE',deterministic=True,modelCalls=0,inputFieldsSent=['id','split','language','prefix','typed'],
                files={'data/inputs.jsonl':sha(data/'inputs.jsonl')},projectionSha256=sha(run/'projection.jsonl'),rows=1)
            (run/'receipt.json').write_text(json.dumps(receipt))
            with mock.patch.object(subject,'ROOT',root):
                result=subject.summarize(data,run)
                self.assertEqual(1,result['counts']['test:annotated']['targetInAlternatives'])
                self.assertFalse(result['independentQualification'])
                receipt['files']={};(run/'receipt.json').write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError,'EWT_REPLAY_BINDING'):
                    subject.summarize(data,run)


if __name__=='__main__':unittest.main()
