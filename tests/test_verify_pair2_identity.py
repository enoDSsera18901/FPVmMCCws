import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from verify_pair2_identity import verify

BASE={
 'vehicles':[
  {'node_id':1,'px4_instance':0,'mav_sys_id':1,'uxrce_dds_key':1,'dds_namespace':'coord_001'},
  {'node_id':2,'px4_instance':1,'mav_sys_id':2,'uxrce_dds_key':2,'dds_namespace':'coord_002'}],
 'safety_boundary':{'arming_authority':False,'flight_mode_authority':False,'trajectory_output_requires_supervisor_gate':True}}

class Pair2IdentityTests(unittest.TestCase):
 def check(self,data):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.json'; p.write_text(json.dumps(data)); return verify(p)
 def test_good(self): self.assertEqual(self.check(BASE),[])
 def test_identity_drift_rejected(self):
  data=json.loads(json.dumps(BASE)); data['vehicles'][1]['mav_sys_id']=7
  self.assertTrue(any('MAV_SYS_ID' in e for e in self.check(data)))
 def test_safety_authority_rejected(self):
  data=json.loads(json.dumps(BASE)); data['safety_boundary']['arming_authority']=True
  self.assertTrue(any('arming authority' in e for e in self.check(data)))

if __name__=='__main__': unittest.main()
