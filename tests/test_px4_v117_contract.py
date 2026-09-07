import tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from verify_px4_contract import assess, REQUIRED_FIELDS

def definition(fields):
    return "uint32 MESSAGE_VERSION = 1\n" + "\n".join(f"float32 {f}" for f in fields) + "\n"

def make_pair(base, versioned_px4=True):
    px4=base/"px4"/"msg"; msgs=base/"msgs"/"msg"
    (px4/"versioned").mkdir(parents=True); msgs.mkdir(parents=True)
    for name,fields in REQUIRED_FIELDS.items():
        text=definition(fields)
        target=(px4/"versioned"/name) if versioned_px4 and name in {"VehicleLocalPosition.msg","VehicleStatus.msg","TrajectorySetpoint.msg"} else (px4/name)
        target.write_text(text); (msgs/name).write_text(text)
    return px4,msgs

class Tests(unittest.TestCase):
    def test_versioned_px4_layout_matches_flat_px4_msgs(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=make_pair(Path(d)); self.assertEqual(assess(a,b)["status"],"PASS")
    def test_v117_contract_does_not_require_later_fields(self):
        self.assertNotIn("accepts_offboard_setpoints",REQUIRED_FIELDS["VehicleStatus.msg"])
        self.assertNotIn("gnss_lost",REQUIRED_FIELDS["FailsafeFlags.msg"])
        self.assertIn("global_position_invalid",REQUIRED_FIELDS["FailsafeFlags.msg"])
    def test_used_message_byte_drift_fails(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=make_pair(Path(d)); p=b/"TrajectorySetpoint.msg"; p.write_text(p.read_text()+"float32 unexpected\n")
            self.assertEqual(assess(a,b)["status"],"FAIL")

if __name__=="__main__":unittest.main()
