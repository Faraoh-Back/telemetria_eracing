import can
import paho.mqtt.client as mqtt
import json
import time
import threading # rodar em paralelo

# Importa as funções do nosso módulo de Nível 1
import Nivel_1.former as n1 

# --- CONFIGURAÇÕES ---
BROKER_IP = "192.168.1.2" # ATENÇÃO: Substitua pelo IP real do seu receptor
BROKER_PORT = 1883
MQTT_TOPIC = "telemetria/dados_brutos"
CAN_INTERFACES = ["can0", "can1"]
PASTA_CSV_COMPONENTES = "../Nivel_1/componentes_csv_linux/"
# --- FIM DAS CONFIGURAÇÕES ---

def thread_leitura_can(interface_can, cliente_mqtt, mapa_prioridade):
    """
    Esta função roda em uma thread para cada interface CAN.
    Ela lê o barramento, chama o Nível 1 para formatar e o Nível 2 (ela mesma) para enviar.
    """
    print(f"Nível 2: Iniciando escuta na interface {interface_can}...")
    try:
        # Abre a interface CAN
        bus = can.interface.Bus(channel=interface_can, bustype="socketcan")
    except Exception as e:
        print(f"ERRO (Nível 2): Não foi possível abrir a interface {interface_can}. {e}")
        return

    while True:
        try:
            #Pega uma mensagem CAN do barramento
            msg_can_bruta = bus.recv()

            # --- Chamada ao Nível 1 ---
            pacote_formatado = n1.formatar_pacote_can(msg_can_bruta, mapa_prioridade) # Forma o pacote usando o Nível 1

            # --- Nível 2: Envia via MQTT ---
            # Se o pacote foi formatado corretamente
            if pacote_formatado:
                # Nível 2: Converte o pacote para JSON e publica via MQTT
                payload = json.dumps(pacote_formatado)
                cliente_mqtt.publish(MQTT_TOPIC, payload)
                print(f"[{interface_can}] Nível 2: Pacote enviado -> {payload}")

        except Exception as e:
            print(f"ERRO na thread {interface_can}: {e}")
            time.sleep(1)


if __name__ == "__main__":
    # 1. Usa o Nível 1 para carregar as configurações de prioridade
    mapa_prioridade_global = n1.carregar_mapa_de_prioridade(PASTA_CSV_COMPONENTES)

    # 2. O Nível 2 configura e conecta o cliente MQTT
    client = mqtt.Client()
    try:
        client.connect(BROKER_IP, BROKER_PORT, 60)
        client.loop_start() 
        print(f"Nível 2: Conectado ao Broker MQTT em {BROKER_IP}:{BROKER_PORT}")
    except Exception as e:
        print(f"ERRO (Nível 2): Não foi possível conectar ao Broker MQTT. Verifique o IP e a rede. {e}")
        exit(1)

    # 3. O Nível 2 gerencia as threads para cada interface CAN
    threads = []
    # Interando sobre as interfaces CAN configuradas
    for interface in CAN_INTERFACES:
        thread = threading.Thread(
            target=thread_leitura_can,
            args=(interface, client, mapa_prioridade_global)
        )
        thread.daemon = True
        threads.append(thread)
        thread.start()

    # 4. Mantém o script principal do Nível 2 rodando
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nNível 2: Desconectando...")
        client.loop_stop()
        client.disconnect()
        print("Nível 2: Programa finalizado.")