import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from evaluate_pair2_sih_smoke import evaluate

MANIFEST = {"gate":"pair-2","vehicles":[{"node_id":1,"px4_instance":0,"mav_sys_id":1,"uxrce_dds_key":1,"dds_namespace":"coord_001"},{"node_id":2,"px4_instance":1,"mav_sys_id":2,"uxrce_dds_key":2,"dds_namespace":"coord_002"}],"safety_boundary":{"arming_authority":False,"flight_mode_authority":False,"trajectory_output_requires_supervisor_gate":True}}

def clean_observation():
    return {"probe_complete":True,"vehicles":[{"node_id":1,"px4_instance":0,"dds_namespace":"coord_001","raw_vehicle_status_count":5,"raw_local_position_count":5,"raw_system_ids":[1],"raw_arming_states":[1],"normalized_state_count":5,"normalized_node_ids":[1],"normalized_arming_states":[1],"offboard_control_mode_count":0,"trajectory_setpoint_count":0},{"node_id":2,"px4_instance":1,"dds_namespace":"coord_002","raw_vehicle_status_count":5,"raw_local_position_count":5,"raw_system_ids":[2],"raw_arming_states":[1],"normalized_state_count":5,"normalized_node_ids":[2],"normalized_arming_states":[1],"offboard_control_mode_count":0,"trajectory_setpoint_count":0}]}

class TestPair2SihSmoke(unittest.TestCase):
    def test_clean_pass(self): self.assertEqual(evaluate(MANIFEST, clean_observation())["status"], "PASS")
    def test_control_output_fails(self):
        o=clean_observation(); o["vehicles"][0]["offboard_control_mode_count"]=1
        self.assertEqual(evaluate(MANIFEST,o)["status"],"FAIL")
    def test_wrong_sysid_fails(self):
        o=clean_observation(); o["vehicles"][1]["raw_system_ids"]=[3]
        self.assertEqual(evaluate(MANIFEST,o)["status"],"FAIL")
    def test_armed_normalized_fails(self):
        o=clean_observation(); o["vehicles"][0]["normalized_arming_states"]=[2]
        self.assertEqual(evaluate(MANIFEST,o)["status"],"FAIL")

if __name__=="__main__": unittest.main()
