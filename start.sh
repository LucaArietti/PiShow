#!/bin/bash
X -nolisten tcp > /dev/null 2>&1 &
DISPLAY=:0.0 /usr/bin/python2 -u pishow.py /home/pi/pishow/Images Photos/Sample\ Album >> log.txt 2>&1 &
