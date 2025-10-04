import can
import struct
import paho.mqtt.client as mqtt
import json
import time

broker_ip = "172.20.10.2"  # IP do box, enviar pra notebook
broker_port = 1883
mqtt_topic = "telemetria"
can_interface = "can1"
bitrate = 500000

mqtt_client = mqtt.Client()
mqtt_client.connect(broker_ip, broker_port)
print(f"Conectado ao broker MQTT em {broker_ip}:{broker_port}")

print(f"Leitura da interface {can_interface}")
bus = can.interface.Bus(channel=can_interface, bustype="socketcan")

try:
    while True:
        msg = bus.recv()
        dados = {
            "arbitration_id": msg.arbitration_id,
            "data": list(msg.data),
            "timestamp": msg.timestamp
        }

        if dados["arbitration_id"] == 123: 
            print(f"Id do INS, enviando dados...")
            mqtt_client.publish(mqtt_topic, json.dumps(dados))
            print("Enviado:", dados)            

except KeyboardInterrupt:
    print("\nParou")