import can
import struct
import paho.mqtt.client as mqtt
import json
import time

broker_ip = "172.20.10.2"  # IP do box, enviar pra notebook
broker_port = 1883
mqtt_topic = "telemetria"
can_interface = "can0"
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

        # Verificar se é mensagem de 1 byte (ID de requisição)
        if len(dados["data"]) == 1:
            print(f"Id de requisicao {hex(dados['arbitration_id'])}")
            continue
        else:
            mqtt_client.publish(mqtt_topic, json.dumps(dados))
            ids_excluidos = "789"
            if str(dados["arbitration_id"]) not in ids_excluidos:
                id_hexa = hex(dados["arbitration_id"])
                print("Id_Hexa:", id_hexa)
                print("Enviado:", dados)

except KeyboardInterrupt:
    print("\nParou")
