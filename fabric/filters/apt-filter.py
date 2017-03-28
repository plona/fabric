#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

mybuf = list()

line = sys.stdin.readline()
while line:
    mybuf.append(line.rstrip())
    line = sys.stdin.readline()

for i, el in enumerate(mybuf):
    words = el.split()
    if len(words) > 0 and words[0] == "Updates" and int(words[2]) > 0:
        print mybuf[i-3], words[0], words[2]

