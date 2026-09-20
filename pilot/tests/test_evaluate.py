import importlib.util
import math
import unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('evaluate',Path(__file__).parents[1]/'evaluate.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class EvaluationTests(unittest.TestCase):
    def test_reference_never_enters_prompt(self):
        text=m.prompt({'kind':'button','html':'<button></button>','context':{},'reference':'SECRET'})
        self.assertNotIn('SECRET',text)
    def test_bad_outputs_rejected(self):
        for p in [{'label':'Search','confidence':float('nan')},{'label':'Search','confidence':True},{'label':'button','confidence':.9},{'label':'x'*61,'confidence':1},{'label':23,'confidence':1}]:
            with self.assertRaises(ValueError):m.validate(p)
    def test_rules_use_token_boundaries(self):
        self.assertEqual(m.rule({'html':'<button class="lucide-search"></button>'})['label'],'Search')
        self.assertEqual(m.rule({'html':'<button class="not-fa-searching"></button>'})['label'],'')
    def test_non_latin_normalization(self):
        self.assertEqual(m.normalized('検索！'),'検索')
        self.assertEqual(m.normalized(' SEARCH!  '),'search')
    def test_truncation_is_not_a_label(self):
        with patch.object(m,'api',return_value={'done':True,'done_reason':'length','response':'{"label":"Search","confidence":0.9}'}):
            with self.assertRaises(ValueError):m.infer({'kind':'button','html':'','context':{}},'model')
    def test_abstentions_remain_in_denominator(self):
        rows=[{'accepted':False,'prediction':'','reference':'Search','tier':2,'elapsed_ms':100,'error':''}]
        s=m.summarize(rows)
        self.assertEqual(s['coverage'],0);self.assertEqual(s['normalized_match_all'],0);self.assertIsNone(s['normalized_match_accepted'])
if __name__=='__main__':unittest.main()

class WorkflowTests(unittest.TestCase):
    def test_csv_formula_roundtrip(self):
        for s in ['=HYPERLINK("x")','  +123','@lookup','ordinary',"'literal"]:
            self.assertEqual(m.csv_original(m.csv_safe(s)),s)
        self.assertTrue(m.csv_safe(' =x').startswith("'"))

    def test_review_gate_and_boundary(self):
        import argparse, csv, json, tempfile, random
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            rows=[]
            for i in range(1000):
                rows.append({'id':str(i),'source':{'url':f'https://example{i//10}.org','stratum':'top' if i<500 else 'long-tail','synthetic':False},'kind':'button','html':'<button></button>','context':'{}','reference':'Search','prediction':'Search','accepted':True})
            (out/'predictions.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            m.review_template(rows,out)
            review_path=out/'review.csv'
            records=list(csv.DictReader(review_path.open()))
            args=argparse.Namespace(run=directory,csv=str(review_path))
            m.review(args)
            self.assertEqual(json.loads((out/'human-summary.json').read_text())['decision'],'PENDING')
            for i,r in enumerate(records):r.update(rating='4',misleading='yes' if i<10 else 'no',reviewer='test-only')
            with review_path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
            m.review(args)
            self.assertEqual(json.loads((out/'human-summary.json').read_text())['decision'],'NO-GO')
            records[9]['misleading']='no'
            with review_path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
            m.review(args)
            self.assertTrue(json.loads((out/'human-summary.json').read_text())['decision'].startswith('GO'))
            records[0]['prediction']='Tampered'
            with review_path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
            with self.assertRaises(ValueError):m.review(args)

    def test_run_resume_and_reuse_no_extra_calls(self):
        import argparse, tempfile, json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=root/'data.jsonl'
            row={'id':'a','reference':'Search','source':{'synthetic':True},'input':{'kind':'button','html':'<button class="fa-search"></button>','context':{}}}
            data.write_text(json.dumps(row)+'\n')
            args=argparse.Namespace(dataset=str(data),out=str(root/'first'),mode='rules',model='unused',cpu=False,threshold=.8,reuse=None)
            m.run(args);m.run(args)
            self.assertEqual(len((root/'first/predictions.jsonl').read_text().splitlines()),1)
            row2={**row,'id':'b'};data.write_text(json.dumps(row)+'\n'+json.dumps(row2)+'\n')
            with self.assertRaises(ValueError):m.run(args)
            args.out=str(root/'second');args.reuse=str(root/'first');m.run(args)
            self.assertEqual(len((root/'second/predictions.jsonl').read_text().splitlines()),2)
