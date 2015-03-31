#!/bin/bash

if [ -z $PI_IP ]
then
	IP=192.168.1.50
else
	IP=$PI_IP
fi

ssh pi@$IP "mkdir -p vj-control-server"
scp -r * pi@${IP}:~/vj-control-server
ssh pi@$IP "chmod +x vj-control-server/launch.sh"
