#!/usr/bin/env python3
"""Validate retained pair-2 live-SITL evidence. Static fixtures cannot satisfy this gate."""
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path
REQUIRED_FILES=("host_readiness.json","environment.txt","process_map.txt","ros2_topics.txt","node_state.csv","transport_health.csv","supervisor_transitions.csv","fault_timeline.md","px4_events.log","resource_usage.csv","result.json")
REQUIRED_LOGS=("dds_agent.log","px4_001.log","px4_002.log","bridge_001.log","bridge_002.log")
NUMERIC=("max_state_age_ms","mean_state_age_ms","max_jitter_ms","mean_jitter_ms","observed_packet_loss_pct","fault_detection_latency_ms","recovery_latency_ms")
CRITERIA=("two_node_mission_completed","identity_unique","no_cross_namespace_state","supervisor_gate_enforced","bridge_does_not_arm_or_change_mode","communications_fault_injected","fault_isolated_to_selected_node","loss_of_node_detected","restart_quarantine_enforced","reassignment_or_reconfiguration_completed","configured_recovery_window_enforced","operator_px4_authority_retained")
def _iso(s):
 try:return datetime.fromisoformat(str(s).replace("Z","+00:00"))
 except (TypeError,ValueError):return None
def _host_sha(host,name):
 for g in host.get("gates",[]):
  if g.get("gate")==name:return g.get("head")
 return None
def validate(gate_dir,identity_path):
 gate_dir=Path(gate_dir);identity_path=Path(identity_path);errors=[];missing=[]
 for name in REQUIRED_FILES:
  p=gate_dir/name
  if not p.is_file():missing.append(name)
  elif p.stat().st_size==0:errors.append(f"empty evidence file:{name}")
 logs=gate_dir/"bridge_logs"
 for name in REQUIRED_LOGS:
  p=logs/name
  if not p.is_file():missing.append(f"bridge_logs/{name}")
  elif p.stat().st_size==0:errors.append(f"empty evidence file:bridge_logs/{name}")
 if missing:return {"status":"FAIL","missing_files":missing,"errors":errors}
 try:host=json.loads((gate_dir/"host_readiness.json").read_text());result=json.loads((gate_dir/"result.json").read_text());identity=json.loads(identity_path.read_text())
 except Exception as e:return {"status":"FAIL","missing_files":[],"errors":errors+[f"invalid JSON:{e}"]}
 if host.get("status")!="PASS":errors.append("host_readiness.json is not PASS")
 ids=[int(v["node_id"]) for v in identity.get("vehicles",[])]
 if result.get("gate")!="pair_2":errors.append("result gate must be pair_2")
 if result.get("node_ids")!=ids:errors.append(f"node_ids must match frozen identity {ids}")
 if result.get("ros2_distribution")!="jazzy":errors.append("ros2_distribution must be jazzy for frozen pair-2 host")
 px4=_host_sha(host,"px4_source_tree");msgs=_host_sha(host,"px4_msgs_source_tree")
 if not px4 or result.get("px4_commit")!=px4:errors.append("result px4_commit does not match host-readiness exact SHA")
 if not msgs or result.get("px4_msgs_commit")!=msgs:errors.append("result px4_msgs_commit does not match host-readiness exact SHA")
 start=_iso(result.get("start_timestamp_utc"));end=_iso(result.get("end_timestamp_utc"))
 if start is None or end is None or end<=start:errors.append("start/end timestamps must be valid ISO-8601 with end > start")
 for key in NUMERIC:
  v=result.get(key)
  if not isinstance(v,(int,float)) or isinstance(v,bool) or v<0:errors.append(f"{key} must be measured non-negative number")
 if isinstance(result.get("observed_packet_loss_pct"),(int,float)) and not 0<=result["observed_packet_loss_pct"]<=100:errors.append("observed_packet_loss_pct must be within 0..100")
 for key in ("peak_cpu_pct_by_process","peak_ram_mb_by_process"):
  d=result.get(key)
  if not isinstance(d,dict) or not d:errors.append(f"{key} must be non-empty object");continue
  if any(not isinstance(v,(int,float)) or isinstance(v,bool) or v<0 for v in d.values()):errors.append(f"{key} values must be non-negative numbers")
 criteria=result.get("criteria")
 if not isinstance(criteria,dict):errors.append("criteria must be object")
 else:
  for c in CRITERIA:
   if criteria.get(c) is not True:errors.append(f"criterion not proven true:{c}")
 sb=identity.get("safety_boundary",{})
 if sb.get("arming_authority") is not False or sb.get("flight_mode_authority") is not False or sb.get("trajectory_output_requires_supervisor_gate") is not True:errors.append("frozen identity safety boundary has drifted")
 return {"status":"PASS" if not errors else "FAIL","missing_files":[],"errors":errors,"node_ids":ids,"px4_commit":result.get("px4_commit"),"px4_msgs_commit":result.get("px4_msgs_commit"),"rule":"PASS requires retained non-empty runtime evidence, exact host/source provenance, measured metrics, and every frozen safety/fault/recovery criterion explicitly proven true. This is simulation evidence only."}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--gate-dir",type=Path,required=True);ap.add_argument("--identity",type=Path,default=Path("integration/sitl/pair2_identity.json"));ap.add_argument("--json",type=Path);a=ap.parse_args();r=validate(a.gate_dir,a.identity);text=json.dumps(r,sort_keys=True,indent=2)+"\n"
 if a.json:a.json.parent.mkdir(parents=True,exist_ok=True);a.json.write_text(text)
 else:print(text,end="")
 return 0 if r["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
