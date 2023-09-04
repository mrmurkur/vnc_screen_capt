#!/bin/bash

file_suo="suo_host.txt"
file_stik="stik_host.txt"
for var in $(cat $file_suo)
do
   if ping -c 1 $var &> /dev/null
then
  vnccapture -P $1 -H $var -o /home/milov/vnc_screen_capt/pict/$var.png
else
  echo "$var unavailable"
fi
done
for var in $(cat $file_stik)
do
   if ping -c 1 $var &> /dev/null
then
  sshpass -p $2 scp -o StrictHostKeyChecking=no -P 22349 user@$var:/home/user/Documents/$var.png /home/milov/vnc_screen_capt/pict/
else
  echo "$var unavailable"
fi
done