#!/bin/sh

ssh pi@192.168.1.50 "mkdir -p vj-control-server"
scp -r * pi@192.168.1.50:~/vj-control-server
ssh pi@192.168.1.50 "chmod +x vj-control-server/launch.sh"
