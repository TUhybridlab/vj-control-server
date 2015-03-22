#!/bin/sh

IP=192.168.1.50

if [ -z $PI_IP ]
then
	IP=$PI_IP
fi

ssh pi@$PI_IP "mkdir -p vj-control-server"
scp -r * pi@${PI_IP}:~/vj-control-server
ssh pi@$PI_IP "chmod +x vj-control-server/launch.sh"
