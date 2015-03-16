#!/bin/bash

sleep 10

cd "$( dirname "${BASH_SOURCE[0]}" )"
/usr/bin/python ./vj-control-server.py >> log.txt
