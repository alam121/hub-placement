#!/bin/bash
# run_batch.sh <mode> <layout dirs...>
M=$1; shift
for L in "$@"; do
  /home/claude/gz/cleanup.sh
  echo "== $L start $(date +%T)"
  /home/claude/gz/multi/run_exact.sh /home/claude/gz/multi/exact/$M/$L > /home/claude/gz/multi/exact/$M/$L.out 2>&1
  grep -c movers /home/claude/gz/multi/exact/$M/$L/logs/runner.log
done
