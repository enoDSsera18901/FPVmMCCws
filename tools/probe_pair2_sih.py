#!/usr/bin/env python3
"""Observe two live PX4 SIH instances and record the no-supervisor-gate safety boundary."""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from px4_msgs.msg import VehicleStatus, VehicleLocalPosition, OffboardControlMode, TrajectorySetpoint
from coordination_msgs.msg import VehicleState

class Pair2Probe(Node):
    def __init__(self, manifest):
        super().__init__("pair2_sih_probe")
        self.obs = {}
        px4_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE, history=HistoryPolicy.KEEP_LAST, depth=10)
        for v in manifest["vehicles"]:
            n=v["node_id"]; ns=v["dds_namespace"]
            self.obs[n]={"node_id":n,"px4_instance":v["px4_instance"],"dds_namespace":ns,"raw_vehicle_status_count":0,"raw_local_position_count":0,"raw_system_ids":set(),"raw_arming_states":set(),"normalized_state_count":0,"normalized_node_ids":set(),"normalized_arming_states":set(),"offboard_control_mode_count":0,"trajectory_setpoint_count":0}
            self.create_subscription(VehicleStatus, f"/{ns}/fmu/out/vehicle_status", lambda m,n=n:self.status_cb(n,m), px4_qos)
            self.create_subscription(VehicleLocalPosition, f"/{ns}/fmu/out/vehicle_local_position", lambda m,n=n:self.pos_cb(n,m), px4_qos)
            self.create_subscription(OffboardControlMode, f"/{ns}/fmu/in/offboard_control_mode", lambda m,n=n:self.offboard_cb(n,m), 10)
            self.create_subscription(TrajectorySetpoint, f"/{ns}/fmu/in/trajectory_setpoint", lambda m,n=n:self.trajectory_cb(n,m), 10)
        self.create_subscription(VehicleState, "/vehicle_state", self.state_cb, 10)
    def status_cb(self,n,m):
        o=self.obs[n]; o["raw_vehicle_status_count"]+=1; o["raw_system_ids"].add(int(m.system_id)); o["raw_arming_states"].add(int(m.arming_state))
    def pos_cb(self,n,m): self.obs[n]["raw_local_position_count"]+=1
    def state_cb(self,m):
        n=int(m.node_id)
        if n in self.obs:
            o=self.obs[n]; o["normalized_state_count"]+=1; o["normalized_node_ids"].add(n); o["normalized_arming_states"].add(int(m.arming_state))
    def offboard_cb(self,n,m): self.obs[n]["offboard_control_mode_count"]+=1
    def trajectory_cb(self,n,m): self.obs[n]["trajectory_setpoint_count"]+=1
    def serializable(self, complete):
        vehicles=[]
        for n in sorted(self.obs):
            o=dict(self.obs[n])
            for k in ("raw_system_ids","raw_arming_states","normalized_node_ids","normalized_arming_states"): o[k]=sorted(o[k])
            vehicles.append(o)
        return {"schema_version":1,"probe_complete":complete,"vehicles":vehicles}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",required=True,type=Path); p.add_argument("--output",required=True,type=Path); p.add_argument("--duration",type=float,default=12.0)
    a=p.parse_args(); manifest=json.loads(a.manifest.read_text())
    if manifest.get("gate")!="pair-2" or len(manifest.get("vehicles",[]))!=2: raise SystemExit("invalid pair-2 manifest")
    rclpy.init(); node=Pair2Probe(manifest); complete=False
    try:
        deadline=time.monotonic()+a.duration
        while time.monotonic()<deadline: rclpy.spin_once(node, timeout_sec=0.2)
        complete=True
    finally:
        result=node.serializable(complete); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2)+"\n")
        node.destroy_node(); rclpy.shutdown()
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
