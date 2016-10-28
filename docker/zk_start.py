#!/usr/bin/env python3
import time
import socket
from tipsi_tools.unix import succ


MYIP = socket.gethostbyname(socket.gethostname())

while 1:
    time.sleep(99999)
