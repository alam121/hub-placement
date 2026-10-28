#!/bin/bash
# record.sh <k> <hold_seconds_before> <max_seconds>
K=$1; PRE=${2:-4}; MAX=${3:-120}
cd /home/claude/gz/video
source /home/claude/gz/env.sh
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe
rm -rf frames_ep$K
gz sim -s -r --headless-rendering ep$K.sdf > rec_ep$K.log 2>&1 &
sleep 5
gz topic -e -t /overview > /dev/null 2>&1 &
SUB=$!
sleep $PRE
timeout $MAX python3 drive.py $K > drive_ep$K.log 2>&1
sleep 3
kill $SUB; pkill -f "gz sim"; sleep 2
echo "frames: $(ls frames_ep$K | wc -l)"
