#!/bin/sh
nice -n 20 screenrecord  --bit-rate 4000000 $1 &
limit_free=4194304

size=$(df -k /data|tail -n1|awk '{print $(NF-2)}')
if [ $size -lt $limit_free ];then
  cw=$(basename $1)
  ls -1 /sdcard/realdata |head -n2|while read d;do
    rm -rf /sdcard/realdata/$d 
  done
  ls -1 /sdcard/dashcam |head -n2|grep -v $cw|while read d;do
    rm -rf /sdcard/dashcam/$d 
  done
fi
