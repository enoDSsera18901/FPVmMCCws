import json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from validate_pair2_evidence import validate,REQUIRED_FILES,REQUIRED_LOGS,CRITERIA
SHA1='1'*40;SHA2='2'*40
def make(base):
 gate=base/'gate';(gate/'bridge_logs').mkdir(parents=True);identity=base/'identity.json';identity.write_text(json.dumps({'vehicles':[{'node_id':1},{'node_id':2}],'safety_boundary':{'arming_authority':False,'flight_mode_authority':False,'trajectory_output_requires_supervisor_gate':True}}));host={'status':'PASS','gates':[{'gate':'px4_source_tree','status':'PASS','head':SHA1},{'gate':'px4_msgs_source_tree','status':'PASS','head':SHA2}]};result={'gate':'pair_2','node_ids':[1,2],'px4_commit':SHA1,'px4_msgs_commit':SHA2,'ros2_distribution':'jazzy','start_timestamp_utc':'2026-09-07T00:00:00Z','end_timestamp_utc':'2026-09-07T00:10:00Z','max_state_age_ms':20,'mean_state_age_ms':10,'max_jitter_ms':4,'mean_jitter_ms':1,'observed_packet_loss_pct':5,'fault_detection_latency_ms':120,'recovery_latency_ms':800,'peak_cpu_pct_by_process':{'bridge_001':20},'peak_ram_mb_by_process':{'bridge_001':50},'criteria':{c:True for c in CRITERIA}}
 for name in REQUIRED_FILES:
  (gate/name).write_text(json.dumps(host) if name=='host_readiness.json' else json.dumps(result) if name=='result.json' else 'evidence\n')
 for name in REQUIRED_LOGS:(gate/'bridge_logs'/name).write_text('log\n')
 return gate,identity,result
class Tests(unittest.TestCase):
 def test_complete_passes(self):
  with tempfile.TemporaryDirectory() as d:g,i,_=make(Path(d));self.assertEqual(validate(g,i)['status'],'PASS')
 def test_false_criterion_fails(self):
  with tempfile.TemporaryDirectory() as d:g,i,r=make(Path(d));r['criteria']['loss_of_node_detected']=False;(g/'result.json').write_text(json.dumps(r));self.assertEqual(validate(g,i)['status'],'FAIL')
 def test_wrong_sha_fails(self):
  with tempfile.TemporaryDirectory() as d:g,i,r=make(Path(d));r['px4_commit']='3'*40;(g/'result.json').write_text(json.dumps(r));self.assertEqual(validate(g,i)['status'],'FAIL')
 def test_empty_log_fails(self):
  with tempfile.TemporaryDirectory() as d:g,i,_=make(Path(d));(g/'bridge_logs'/'bridge_002.log').write_text('');self.assertEqual(validate(g,i)['status'],'FAIL')
 def test_bad_timestamp_fails(self):
  with tempfile.TemporaryDirectory() as d:g,i,r=make(Path(d));r['end_timestamp_utc']=r['start_timestamp_utc'];(g/'result.json').write_text(json.dumps(r));self.assertEqual(validate(g,i)['status'],'FAIL')
 def test_packet_loss_range_fails(self):
  with tempfile.TemporaryDirectory() as d:g,i,r=make(Path(d));r['observed_packet_loss_pct']=101;(g/'result.json').write_text(json.dumps(r));self.assertEqual(validate(g,i)['status'],'FAIL')
if __name__=='__main__':unittest.main()
