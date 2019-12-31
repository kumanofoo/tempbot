#!/usr/bin/env python3

import datetime
import time
import random

filename = '/tmp/w1_slave'
max_temp = 25
min_temp = 12
norm_temp = [0.25396825396825407,
             0.1746031746031747,
             0.12698412698412695,
             0.09523809523809533,
             0.07936507936507936,
             0.0,
             0.07936507936507936,
             0.21428571428571438,
             0.4365079365079367,
             0.6111111111111112,
             0.7936507936507938,
             0.9126984126984129,
             0.9444444444444445,
             1.0,
             0.9761904761904762,
             0.9841269841269842,
             0.9206349206349206,
             0.7936507936507938,
             0.6507936507936509,
             0.5555555555555557,
             0.48412698412698413,
             0.46031746031746024,
             0.4206349206349206,
             0.3333333333333334,
             0.25396825396825407]

w1_slave = "bd 01 4b 46 7f ff 03 10 ff : crc=ff YES\n" \
           "bd 01 4b 46 7f ff 03 10 ff t="

while True:
    now = datetime.datetime.now()
    if now.hour == 5 and now.minute == 0:
        max_temp += random.uniform(-10, 10)
    if now.hour == 13 and now.minute == 0:
        min_temp = max_temp - random.uniform(5, 10)

    t0 = norm_temp[now.hour]
    t1 = norm_temp[now.hour+1]
    t = (t1 - t0)/60*now.minute + t0
    t = (max_temp - min_temp)*t + min_temp

    with open(filename, mode='w') as f:
        f.write("%s%d" % (w1_slave, int(t*1000)))

    time.sleep(60)
