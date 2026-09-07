#!/usr/bin/env python3
"""Fail-closed host/readiness check for the first pair-2 PX4 SITL gate. This does not run SITL."""
from __future__ import annotations
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
from typing import Callable
from verify_px4_contract import assess as assess_message_contract
REQUIRED_OS=("ubuntu","24.04"); REQUIRED_ROS_DISTRO="jazzy"; REQUIRED_AGENT_VERSION="2.4.3"; REQUIRED_COMMANDS=("git","ros2","colcon","gz","MicroXRCEAgent"); SHA40=re.compile(r"^[0-9a-f]{40}$")
def _read_os_release(path):
 out={}
 for raw in path.read_text(encoding="utf-8").splitlines():
  if "=" in raw and not raw.lstrip().startswith("#"):
   k,v=raw.split("=",1); out[k.strip()]=v.strip().strip('"')
 return out
def _git(root,*args): return subprocess.run(["git","-C",str(root),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def _source_tree(label,root):
 if root is None:return {"label":label,"status":"BLOCKED","reason":"path not supplied"}
 if not root.is_dir():return {"label":label,"status":"BLOCKED","path":str(root),"reason":"path not found"}
 try: sha=_git(root,"rev-parse","HEAD"); dirty=bool(_git(root,"status","--porcelain"))
 except (OSError,subprocess.CalledProcessError) as e:return {"label":label,"status":"FAIL","path":str(root),"reason":f"git inspection failed: {e}"}
 if not SHA40.match(sha):return {"label":label,"status":"FAIL","path":str(root),"reason":"HEAD is not an exact 40-character commit SHA","head":sha}
 if dirty:return {"label":label,"status":"FAIL","path":str(root),"reason":"working tree is dirty","head":sha}
 return {"label":label,"status":"PASS","path":str(root),"head":sha,"clean":True}
def assess(px4_root,px4_msgs_root,*,os_release=Path("/etc/os-release"),environ=None,which:Callable[[str],str|None]=shutil.which,agent_version=None):
 env=dict(os.environ if environ is None else environ); gates=[]
 try:
  osv=_read_os_release(os_release); good=(osv.get("ID"),osv.get("VERSION_ID"))==REQUIRED_OS
  gates.append({"gate":"host_os","status":"PASS" if good else "FAIL","observed":{"ID":osv.get("ID"),"VERSION_ID":osv.get("VERSION_ID")},"required":{"ID":"ubuntu","VERSION_ID":"24.04"}})
 except OSError as e:gates.append({"gate":"host_os","status":"BLOCKED","reason":str(e)})
 ros=env.get("ROS_DISTRO"); gates.append({"gate":"ros_distribution","status":"PASS" if ros==REQUIRED_ROS_DISTRO else ("BLOCKED" if not ros else "FAIL"),"observed":ros,"required":REQUIRED_ROS_DISTRO})
 commands={n:which(n) for n in REQUIRED_COMMANDS}; gates.append({"gate":"required_commands","status":"PASS" if all(commands.values()) else "BLOCKED","commands":commands})
 av=agent_version or env.get("MICRO_XRCE_DDS_AGENT_VERSION"); gates.append({"gate":"micro_xrce_dds_agent_version","status":"PASS" if av==REQUIRED_AGENT_VERSION else ("BLOCKED" if not av else "FAIL"),"observed":av,"required":REQUIRED_AGENT_VERSION})
 px4=_source_tree("PX4-Autopilot",px4_root); msgs=_source_tree("px4_msgs",px4_msgs_root); gates += [{"gate":"px4_source_tree",**px4},{"gate":"px4_msgs_source_tree",**msgs}]
 contract=None
 if px4["status"]=="PASS" and msgs["status"]=="PASS":
  try: contract=assess_message_contract(px4_root/"msg",px4_msgs_root/"msg"); gates.append({"gate":"bridge_message_contract","status":contract["status"],"rule":contract["rule"]})
  except (OSError,UnicodeError,ValueError) as e:gates.append({"gate":"bridge_message_contract","status":"FAIL","reason":str(e)})
 else:gates.append({"gate":"bridge_message_contract","status":"BLOCKED","reason":"source trees not ready"})
 states=[g["status"] for g in gates]; state="FAIL" if "FAIL" in states else ("BLOCKED" if "BLOCKED" in states else "PASS")
 return {"status":state,"purpose":"pair-2 live-SITL preflight only; PASS is not SITL evidence","gates":gates,"message_contract":contract,"policy":"First pair-2 requires clean exact PX4/px4_msgs revisions with byte-matching bridge-used message definitions; message translation is not enabled for this gate."}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--px4-root",type=Path); ap.add_argument("--px4-msgs-root",type=Path); ap.add_argument("--os-release",type=Path,default=Path("/etc/os-release")); ap.add_argument("--agent-version"); ap.add_argument("--json",type=Path); a=ap.parse_args(); r=assess(a.px4_root,a.px4_msgs_root,os_release=a.os_release,agent_version=a.agent_version); text=json.dumps(r,sort_keys=True,indent=2)+"\n"
 if a.json:a.json.parent.mkdir(parents=True,exist_ok=True);a.json.write_text(text,encoding="utf-8")
 else:print(text,end="")
 return 0 if r["status"]=="PASS" else (1 if r["status"]=="FAIL" else 2)
if __name__=="__main__":raise SystemExit(main())
