#!/usr/bin/env python3
import json, sys
from pathlib import Path

def verify(path: Path):
    data=json.loads(path.read_text())
    errors=[]
    vehicles=data.get('vehicles',[])
    if len(vehicles)!=2: errors.append('pair-2 requires exactly 2 vehicles')
    seen_nodes=set(); seen_instances=set(); seen_sys=set(); seen_keys=set(); seen_ns=set()
    for v in vehicles:
        nid=v.get('node_id'); inst=v.get('px4_instance'); sysid=v.get('mav_sys_id'); key=v.get('uxrce_dds_key'); ns=v.get('dds_namespace')
        if not all(isinstance(x,int) for x in (nid,inst,sysid,key)): errors.append(f'invalid integer identity fields: {v}'); continue
        if nid != inst + 1: errors.append(f'node_id {nid} != px4_instance+1 ({inst+1})')
        if sysid != nid: errors.append(f'MAV_SYS_ID {sysid} != node_id {nid}')
        if key != nid: errors.append(f'UXRCE_DDS_KEY {key} != node_id {nid}')
        if ns != f'coord_{nid:03d}': errors.append(f'namespace {ns!r} != coord_{nid:03d}')
        for value,seen,label in ((nid,seen_nodes,'node_id'),(inst,seen_instances,'px4_instance'),(sysid,seen_sys,'mav_sys_id'),(key,seen_keys,'uxrce_dds_key'),(ns,seen_ns,'dds_namespace')):
            if value in seen: errors.append(f'duplicate {label}: {value}')
            seen.add(value)
    safety=data.get('safety_boundary',{})
    if safety.get('arming_authority') is not False: errors.append('arming authority must remain false')
    if safety.get('flight_mode_authority') is not False: errors.append('flight-mode authority must remain false')
    if safety.get('trajectory_output_requires_supervisor_gate') is not True: errors.append('trajectory output must require supervisor gate')
    return errors

def main():
    path=Path(sys.argv[1] if len(sys.argv)>1 else 'integration/sitl/pair2_identity.json')
    errors=verify(path)
    if errors:
        for e in errors: print('ERROR:',e)
        return 1
    print('PASS: pair-2 identity and safety contract is internally consistent')
    return 0

if __name__=='__main__': raise SystemExit(main())
