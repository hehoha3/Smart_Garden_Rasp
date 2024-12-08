from datetime import datetime

import paho.mqtt.client as mqtt
from firebase_admin import credentials, db, initialize_app


class MQTTController:
    def __init__(self, host, port, keep_alive, firebase_key_path, db_url):
        self.client = mqtt.Client()
        self.client.connect(host, port, keep_alive)

        # Authenticate to Firebase
        cred = credentials.Certificate(firebase_key_path)
        initialize_app(cred, {"databaseURL": db_url})

        # Save last executed for publish MQTT 1 time
        self.last_executed = {
            "pump_LEFT": None,
            "pump_RIGHT": None,
            "lights": None,
            "fans": None,
        }

        # Dictionary to store sensor values
        self.sensor_values = {
            "Water/Quantity": None,
            "Soil/Moisture_LEFT": None,
            "Soil/Moisture_RIGHT": None,
            "DHT11/Temperature": None,
            "DHT11/Humidity": None,
        }

    #! [SAVE] MQTT msg
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        # Save the value based on the topic
        if topic in self.sensor_values:
            self.sensor_values[topic] = float(payload)
            print(f"[SAVE] Topic {topic}: {self.sensor_values[topic]}")

    #! Subscibe TOPIC & [SAVE] MQTT msg
    def subscribe_to_topics(self, topics):
        for topic in topics:
            self.client.subscribe(topic)
        # [SAVE] MQTT msg
        self.client.on_message = self.on_message

    #! Publish MQTT msg to TOPIC
    def publish_to_topics(self, topic, msg):
        self.client.publish(topic, msg)

    #! Logic Control PUMPs
    def control_pumps(self, topic_pump_left, topic_pump_right):
        moisture_left = self.sensor_values["Soil/Moisture_LEFT"]
        moisture_right = self.sensor_values["Soil/Moisture_RIGHT"]

        # Pump LEFT
        if (
            moisture_left is not None
            and moisture_left <= 35
            and self.last_executed["pump_LEFT"] != "ON"
        ):
            print("Soil moisture left is low. Turning ON Pump Left.")
            self.client.publish(topic_pump_left, "ON")
            self.last_executed["pump_LEFT"] = "ON"
        elif (
            moisture_left is not None
            and moisture_left >= 60
            and self.last_executed["pump_LEFT"] != "OFF"
        ):
            print("Soil moisture left is high. Turning OFF Pump Left.")
            self.client.publish(topic_pump_left, "OFF")
            self.last_executed["pump_LEFT"] = "OFF"

        # Pump RIGHT
        if (
            moisture_right is not None
            and moisture_right <= 35
            and self.last_executed["pump_RIGHT"] != "ON"
        ):
            print("Soil moisture right is low. Turning ON Pump Right.")
            self.client.publish(topic_pump_right, "ON")
            self.last_executed["pump_RIGHT"] = "ON"
        elif (
            moisture_right is not None
            and moisture_right >= 60
            and self.last_executed["pump_RIGHT"] != "OFF"
        ):
            print("Soil moisture right is high. Turning OFF Pump Right.")
            self.client.publish(topic_pump_right, "OFF")
            self.last_executed["pump_RIGHT"] = "OFF"

    #! Logic fot TIMERs
    def check_timer_and_publish(
        self,
        topic_pump_left,
        topic_pump_right,
        topic_lights,
        topic_fans,
        timer_pumps_on,
        timer_pumps_off,
        timer_lights_on,
        timer_lights_off,
        timer_fans_on,
        timer_fans_off,
    ):
        # Moisture values
        moisture_left = self.sensor_values["Soil/Moisture_LEFT"]
        moisture_right = self.sensor_values["Soil/Moisture_RIGHT"]

        # Get TIMERs from firebase
        pumps_ON_time = db.reference(timer_pumps_on).get()
        pumps_OFF_time = db.reference(timer_pumps_off).get()
        lights_ON_time = db.reference(timer_lights_on).get()
        lights_OFF_time = db.reference(timer_lights_off).get()
        fans_ON_time = db.reference(timer_fans_on).get()
        fans_OFF_time = db.reference(timer_fans_off).get()

        current_time = datetime.now().strftime("%H:%M")

        # TIMER pumps ON
        if pumps_ON_time == current_time:
            if (
                moisture_left is not None
                and moisture_left < 55
                and self.last_executed["pump_LEFT"] != "ON"
            ):
                print("[TIMER] Turn ON Pumps LEFT")
                self.client.publish(topic_pump_left, "ON")
                self.last_executed["pump_LEFT"] = "ON"

            elif (
                moisture_left is not None
                and moisture_right < 55
                and self.last_executed["pump_RIGHT"] != "ON"
            ):
                print("[TIMER] Turn ON Pumps RIGHT")
                self.client.publish(topic_pump_right, "ON")
                self.last_executed["pump_RIGHT"] = "ON"

        # TIMER pumps OFF
        if pumps_OFF_time == current_time:
            if (
                moisture_right is not None
                and moisture_left >= 40
                and self.last_executed["pump_LEFT"] != "OFF"
            ):
                print("[TIMER] Turn OFF Pumps LEFT")
                self.client.publish(topic_pump_left, "OFF")
                self.last_executed["pump_LEFT"] = "OFF"

            elif (
                moisture_right is not None
                and moisture_right >= 40
                and self.last_executed["pump_RIGHT"] != "OFF"
            ):
                print("[TIMER] Turn OFF Pumps RIGHT")
                self.client.publish(topic_pump_right, "OFF")
                self.last_executed["pump_RIGHT"] = "OFF"

        if lights_ON_time == current_time and self.last_executed["lights"] != "ON":
            print("Turn ON LIGHTs")
            self.client.publish(topic_lights, "ON")
            self.last_executed["lights"] = "ON"

        if lights_OFF_time == current_time and self.last_executed["lights"] != "OFF":
            print("Turn OFF LIGHTs")
            self.client.publish(topic_lights, "OFF")
            self.last_executed["lights"] = "OFF"

        if fans_ON_time == current_time and self.last_executed["fans"] != "ON":
            print("Turn ON FANs")
            self.client.publish(topic_fans, "ON")
            self.last_executed["fans"] = "ON"

        if fans_OFF_time == current_time and self.last_executed["fans"] != "OFF":
            print("Turn OFF FANs")
            self.client.publish(topic_fans, "OFF")
            self.last_executed["fans"] = "OFF"
