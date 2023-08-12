#!/bin/bash

if [ ! -f .env ]
then
  export $(cat .env | xargs)
fi

sudo -E python3 mqtt-control.py > led-rainbown.log &