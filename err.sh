#!/bin/bash

# Call this script without arguments, it will call itself again, nohupped and forked
if [ -z $1 ]; then
    nohup ./err.sh start &
elif [[ $1 == "start" ]]; then
    while [ true ]; do
	nohup python err.py
    done
fi
