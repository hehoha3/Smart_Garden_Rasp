import os
import time

from dotenv import load_dotenv

from mqtt_controller import MQTTController

# Load .env file
load_dotenv(".env")

#! ----------------------------------- Variables -----------------------------------

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_POST = int(os.getenv("MQTT_POST"))
KEEP_ALIVE = int(os.getenv("KEEP_ALIVE"))
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH")
DB_URL = os.getenv("DB_URL")

TOPICS_SENSOR = os.getenv("TOPICS_SENSOR").split(",")

TOPIC_PUMP_LEFT = os.getenv("TOPIC_PUMP_LEFT")
TOPIC_PUMP_RIGHT = os.getenv("TOPIC_PUMP_RIGHT")
TOPIC_LIGHTS = os.getenv("TOPIC_LIGHTS")
TOPIC_FANS = os.getenv("TOPIC_FANS")

TIMER_PUMP_ON_PATH = os.getenv("TIMER_PUMP_ON_PATH")
TIMER_PUMP_OFF_PATH = os.getenv("TIMER_PUMP_OFF_PATH")
TIMER_LIGHTS_ON_PATH = os.getenv("TIMER_LIGHTS_ON_PATH")
TIMER_LIGHTS_OFF_PATH = os.getenv("TIMER_LIGHTS_OFF_PATH")
TIMER_FANS_ON_PATH = os.getenv("TIMER_FANS_ON_PATH")
TIMER_FANS_OFF_PATH = os.getenv("TIMER_FANS_OFF_PATH")


#! ----------------------------------- Main -----------------------------------


def main():
    controller = MQTTController(
        MQTT_HOST, MQTT_POST, KEEP_ALIVE, FIREBASE_KEY_PATH, DB_URL
    )
    controller.subscribe_to_topics(TOPICS_SENSOR)

    while True:
        controller.client.loop()  # Process MQTT messages
        controller.control_pumps(TOPIC_PUMP_LEFT, TOPIC_PUMP_RIGHT)  # Control pumps
        controller.check_timer_and_publish(
            TOPIC_PUMP_LEFT,
            TOPIC_PUMP_RIGHT,
            TOPIC_LIGHTS,
            TOPIC_FANS,
            TIMER_PUMP_ON_PATH,
            TIMER_PUMP_OFF_PATH,
            TIMER_LIGHTS_ON_PATH,
            TIMER_LIGHTS_OFF_PATH,
            TIMER_FANS_ON_PATH,
            TIMER_FANS_OFF_PATH,
        )
        time.sleep(1)


if __name__ == "__main__":
    main()
