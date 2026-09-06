# FPV Multi-Node Coordination Controller

Engineering repository for the multi-node FPV coordination/controller architecture.

The controller is intentionally separated from airframe design. It manages configuration identity, node discovery/admission, assignment, supervision, mission coordination, replacement/reconfiguration, bounded intent generation, and simulation/verification evidence while leaving local flight stability and motor control to the aircraft autopilot.

Current engineering gate: validated portable software baseline -> live PX4/Gazebo/ROS 2 two-node SITL evidence -> fault injection -> progressive scale testing.

This repository is **not evidence of flight readiness**. Physical testing remains gated after SITL, simulated fault injection, bench and controlled test stages.
