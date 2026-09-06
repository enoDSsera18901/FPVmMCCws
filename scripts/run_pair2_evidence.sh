#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
evidence_dir="$repo_root/evidence/pair2-software-sim"
events_tmp="$evidence_dir/events.csv.tmp"
tests_tmp="$evidence_dir/test-results.txt.tmp"

mkdir -p "$evidence_dir"
"$repo_root/build/test_coordinator" >"$tests_tmp"
"$repo_root/build/pair2_sim" "$events_tmp"
mv "$tests_tmp" "$evidence_dir/test-results.txt"
mv "$events_tmp" "$evidence_dir/events.csv"

expected='1270,task_101_reconfigured_to_node_1,active,active,1,enabled,enabled'
if ! grep -Fxq "$expected" "$evidence_dir/events.csv"; then
  printf 'evidence contract failed: final controlled reconfiguration not observed\n' >&2
  exit 1
fi
if ! grep -Fq 'node_1_lost_task_reassigned,lost,active,2,suppressed,enabled' "$evidence_dir/events.csv"; then
  printf 'evidence contract failed: loss/reassignment not observed\n' >&2
  exit 1
fi
if ! grep -Fq 'node_1_recovered_unassigned,active,active,2,suppressed,enabled' "$evidence_dir/events.csv"; then
  printf 'evidence contract failed: recovered node emitted without an assignment\n' >&2
  exit 1
fi

printf 'PASS: deterministic pair-2 software simulation evidence generated\n'
