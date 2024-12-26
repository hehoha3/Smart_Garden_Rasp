#!/bin/bash
python3 main_mqtt.py &
python3 face_recog_door.py &
python3 take_pics.py &
wait
