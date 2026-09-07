import subprocess,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from check_sitl_host import assess
from verify_px4_contract import REQUIRED_FIELDS
def init_repo(root):
 subprocess.run(["git","init","-q",str(root)],check=True); subprocess.run(["git","-C",str(root),"config","user.email","test@example.invalid"],check=True); subprocess.run(["git","-C",str(root),"config","user.name","Test"],check=True); subprocess.run(["git","-C",str(root),"add","."],check=True); subprocess.run(["git","-C",str(root),"commit","-qm","fixture"],check=True)
def text(fields):return "\n".join(f"float32 {x}" for x in fields)+"\n"
def tree(base,name):
 root=base/name;(root/"msg").mkdir(parents=True)
 for fn,fields in REQUIRED_FIELDS.items():(root/"msg"/fn).write_text(text(fields))
 init_repo(root);return root
def osrel(base,v="24.04"):
 p=base/"os-release";p.write_text(f'ID=ubuntu\nVERSION_ID="{v}"\n');return p
def cmds(_):return "/fake/bin/tool"
class Tests(unittest.TestCase):
 def test_clean_matching_host_passes(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);a=tree(b,"px4");m=tree(b,"msgs");self.assertEqual(assess(a,m,os_release=osrel(b),environ={"ROS_DISTRO":"jazzy"},which=cmds,agent_version="2.4.3")["status"],"PASS")
 def test_message_drift_fails(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);a=tree(b,"px4");m=tree(b,"msgs");p=m/"msg"/"TrajectorySetpoint.msg";p.write_text(p.read_text()+"float32 extra\n");subprocess.run(["git","-C",str(m),"add","."],check=True);subprocess.run(["git","-C",str(m),"commit","-qm","drift"],check=True);self.assertEqual(assess(a,m,os_release=osrel(b),environ={"ROS_DISTRO":"jazzy"},which=cmds,agent_version="2.4.3")["status"],"FAIL")
 def test_dirty_tree_fails(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);a=tree(b,"px4");m=tree(b,"msgs");(m/"dirty").write_text("x");self.assertEqual(assess(a,m,os_release=osrel(b),environ={"ROS_DISTRO":"jazzy"},which=cmds,agent_version="2.4.3")["status"],"FAIL")
 def test_missing_runtime_is_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);a=tree(b,"px4");m=tree(b,"msgs");self.assertEqual(assess(a,m,os_release=osrel(b),environ={},which=lambda _:None)["status"],"BLOCKED")
 def test_wrong_ros_or_os_fails(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);a=tree(b,"px4");m=tree(b,"msgs");self.assertEqual(assess(a,m,os_release=osrel(b,"22.04"),environ={"ROS_DISTRO":"humble"},which=cmds,agent_version="2.4.3")["status"],"FAIL")
if __name__=="__main__":unittest.main()
