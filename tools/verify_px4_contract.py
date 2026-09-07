#!/usr/bin/env python3
"""Fail-closed compatibility check for PX4 message contracts used by the ROS 2 bridge."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

REQUIRED_FIELDS={
 "VehicleLocalPosition.msg":("timestamp","x","y","z","vx","vy","vz","xy_valid","z_valid","v_xy_valid","v_z_valid","heading","heading_good_for_control"),
 "VehicleStatus.msg":("timestamp","nav_state","arming_state","accepts_offboard_setpoints","failsafe"),
 "FailsafeFlags.msg":("timestamp","offboard_control_signal_lost","fd_critical_failure","navigator_failure","position_accuracy_low","gnss_lost"),
 "OffboardControlMode.msg":("timestamp","position","velocity","acceleration","attitude","body_rate","thrust_and_torque","direct_actuator"),
 "TrajectorySetpoint.msg":("timestamp","position","velocity","acceleration","jerk","yaw","yawspeed"),
}

def _normalized_bytes(path:Path)->bytes: return path.read_text(encoding="utf-8").replace("\r\n","\n").encode()
def _sha256(path:Path)->str: return hashlib.sha256(_normalized_bytes(path)).hexdigest()
def _field_names(path:Path)->set[str]:
 fields=set()
 for raw in path.read_text(encoding="utf-8").splitlines():
  line=raw.split("#",1)[0].strip()
  if not line: continue
  parts=line.split()
  if len(parts)<2 or (len(parts)>=3 and parts[2]=="="): continue
  fields.add(parts[1])
 return fields

def _tree_report(label:str,msg_dir:Path)->dict:
 messages=[]; ok=True
 for filename,required in REQUIRED_FIELDS.items():
  path=msg_dir/filename
  if not path.is_file(): messages.append({"message":filename,"status":"FAIL","reason":"missing file","missing_fields":list(required)}); ok=False; continue
  fields=_field_names(path); missing=[x for x in required if x not in fields]; good=not missing; ok=ok and good
  messages.append({"message":filename,"status":"PASS" if good else "FAIL","sha256":_sha256(path),"missing_fields":missing})
 return {"label":label,"path":str(msg_dir),"status":"PASS" if ok else "FAIL","messages":messages}

def assess(px4_msg_dir:Path|None,px4_msgs_dir:Path|None)->dict:
 if px4_msg_dir is None and px4_msgs_dir is None: raise ValueError("provide PX4 and/or px4_msgs message directory")
 trees=[]
 if px4_msg_dir is not None: trees.append(_tree_report("PX4-Autopilot",px4_msg_dir))
 if px4_msgs_dir is not None: trees.append(_tree_report("px4_msgs",px4_msgs_dir))
 comparisons=[]; compare_ok=True
 if px4_msg_dir is not None and px4_msgs_dir is not None:
  for filename in REQUIRED_FIELDS:
   a=px4_msg_dir/filename; b=px4_msgs_dir/filename
   if not a.is_file() or not b.is_file(): comparisons.append({"message":filename,"status":"FAIL","reason":"missing file"}); compare_ok=False; continue
   same=_normalized_bytes(a)==_normalized_bytes(b); compare_ok=compare_ok and same
   comparisons.append({"message":filename,"status":"PASS" if same else "FAIL","px4_sha256":_sha256(a),"px4_msgs_sha256":_sha256(b)})
 tree_ok=all(t["status"]=="PASS" for t in trees)
 return {"status":"PASS" if tree_ok and compare_ok else "FAIL","required_messages":sorted(REQUIRED_FIELDS),"trees":trees,"cross_tree_match":comparisons,"rule":"All bridge-used fields must exist. For the first pair-2 gate, used PX4 and px4_msgs definitions must match exactly after newline normalization."}

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument("--px4-msg-dir",type=Path); ap.add_argument("--px4-msgs-dir",type=Path); ap.add_argument("--json",type=Path); a=ap.parse_args()
 try: r=assess(a.px4_msg_dir,a.px4_msgs_dir)
 except (OSError,UnicodeError,ValueError) as e: print(f"verify_px4_contract: ERROR: {e}",file=sys.stderr); return 2
 text=json.dumps(r,sort_keys=True,indent=2)+"\n"
 if a.json: a.json.parent.mkdir(parents=True,exist_ok=True); a.json.write_text(text,encoding="utf-8")
 else: print(text,end="")
 return 0 if r["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
