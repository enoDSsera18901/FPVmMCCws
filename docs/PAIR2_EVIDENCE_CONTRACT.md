# Pair-2 live SITL evidence contract

A host-readiness `PASS` is only permission to start simulation. **Gate #1 closes only when a real run directory passes `tools/validate_pair2_evidence.py`.**

Required retained files are `host_readiness.json`, environment/process/topic snapshots, node-state and transport-health CSVs, supervisor transitions, a fault timeline, PX4 event log, resource measurements and `result.json`, plus non-empty DDS, PX4-001/002 and bridge-001/002 logs.

`result.json` must carry the exact PX4 and `px4_msgs` SHAs from the passing host-readiness report, node IDs `[1,2]`, ROS 2 Jazzy, ordered start/end timestamps, measured state-age/jitter/loss/detection/recovery metrics, non-empty process CPU/RAM measurements, and explicit `true` dispositions for every mission, identity, namespace, safety, injected-fault, node-loss, quarantine, reassignment/reconfiguration, recovery-window and operator-authority criterion.

The validator intentionally contains **no synthetic latency or packet-loss pass thresholds**. Those are measured outputs to retain and review; the safety/fault behaviours themselves must be proven true. Empty logs, null metrics, wrong SHAs or manually skipping a criterion are failures.

Example result structure: `evidence/pair2/result.example.json`. Do not convert the example into a PASS fixture.
