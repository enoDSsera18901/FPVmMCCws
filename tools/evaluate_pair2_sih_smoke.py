#!/usr/bin/env python3
"""Fail-closed evaluator for the pair-2 PX4 SIH-as-SITL smoke evidence."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
DISARMED = 1

def _vehicle_by_node(observation: dict[str, Any], node_id: int):
    for vehicle in observation.get("vehicles", []):
        if vehicle.get("node_id") == node_id:
            return vehicle
    return None

def evaluate(manifest: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    if manifest.get("gate") != "pair-2": reasons.append("manifest gate is not pair-2")
    expected = manifest.get("vehicles", [])
    if len(expected) != 2: reasons.append("manifest must define exactly two vehicles")
    safety = manifest.get("safety_boundary", {})
    if safety.get("arming_authority") is not False: reasons.append("arming authority must remain false")
    if safety.get("flight_mode_authority") is not False: reasons.append("flight-mode authority must remain false")
    if safety.get("trajectory_output_requires_supervisor_gate") is not True: reasons.append("trajectory output must require supervisor gate")
    if observation.get("probe_complete") is not True: reasons.append("probe did not complete its observation window")
    for item in expected:
        node_id = item.get("node_id")
        obs = _vehicle_by_node(observation, node_id)
        if obs is None:
            reasons.append(f"node {node_id}: no observation record"); continue
        for field in ("px4_instance", "dds_namespace"):
            if obs.get(field) != item.get(field): reasons.append(f"node {node_id}: {field} mismatch")
        expected_sys_id = item.get("mav_sys_id")
        sys_ids = set(obs.get("raw_system_ids", []))
        if obs.get("raw_vehicle_status_count", 0) <= 0: reasons.append(f"node {node_id}: no raw VehicleStatus")
        elif sys_ids != {expected_sys_id}: reasons.append(f"node {node_id}: raw system_id mismatch {sorted(sys_ids)} != [{expected_sys_id}]")
        if obs.get("raw_local_position_count", 0) <= 0: reasons.append(f"node {node_id}: no raw VehicleLocalPosition")
        raw_arming = set(obs.get("raw_arming_states", []))
        if not raw_arming: reasons.append(f"node {node_id}: no raw arming state")
        elif raw_arming != {DISARMED}: reasons.append(f"node {node_id}: raw vehicle not continuously disarmed: {sorted(raw_arming)}")
        if obs.get("normalized_state_count", 0) <= 0: reasons.append(f"node {node_id}: no normalized VehicleState")
        normalized_nodes = set(obs.get("normalized_node_ids", []))
        if normalized_nodes and normalized_nodes != {node_id}: reasons.append(f"node {node_id}: normalized node identity mismatch: {sorted(normalized_nodes)}")
        normalized_arming = set(obs.get("normalized_arming_states", []))
        if not normalized_arming: reasons.append(f"node {node_id}: no normalized arming state")
        elif normalized_arming != {DISARMED}: reasons.append(f"node {node_id}: normalized vehicle not continuously disarmed: {sorted(normalized_arming)}")
        if obs.get("offboard_control_mode_count", 0) != 0: reasons.append(f"node {node_id}: bridge emitted OffboardControlMode without supervisor gate")
        if obs.get("trajectory_setpoint_count", 0) != 0: reasons.append(f"node {node_id}: bridge emitted TrajectorySetpoint without supervisor gate")
    return {"schema_version": 1, "gate": "pair-2-sih-no-gate-smoke", "status": "PASS" if not reasons else "FAIL", "reasons": reasons}

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--manifest", required=True, type=Path); p.add_argument("--observation", required=True, type=Path); p.add_argument("--result", required=True, type=Path)
    a=p.parse_args(); result=evaluate(json.loads(a.manifest.read_text()), json.loads(a.observation.read_text()))
    a.result.parent.mkdir(parents=True, exist_ok=True); a.result.write_text(json.dumps(result, indent=2)+"\n"); print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1
if __name__ == "__main__": raise SystemExit(main())
