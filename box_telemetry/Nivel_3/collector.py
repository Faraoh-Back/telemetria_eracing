import paho.mqtt.client as mqtt
import json
import os
import csv
from datetime import datetime

# --- CONFIGURAÇÕES ---
# Endereço do broker MQTT. Se estiver rodando na mesma máquina, use "localhost".
BROKER_IP = "localhost"
BROKER_PORT = 1883
MQTT_TOPIC = "telemetria/dados_brutos"

# Nível 4: Pasta onde os logs CSV serão salvos.
PASTA_ARMAZENAMENTO = "./Nivel_4/"
# --- FIM DAS CONFIGURAÇÕES ---

# Variável global para guardar o caminho do arquivo de log da sessão atual
caminho_arquivo_log = ""

def on_connect(client, userdata, flags, rc):
    """Callback chamado quando o cliente se conecta ao broker."""
    if rc == 0:
        print("Conectado ao Broker MQTT com sucesso!")
        client.subscribe(MQTT_TOPIC)
        print(f"Inscrito no tópico: {MQTT_TOPIC}")
    else:
        print(f"Falha na conexão, código de retorno: {rc}\n")

def on_message(client, userdata, msg):
    """
    Callback chamado sempre que uma mensagem é recebida do tópico assinado.
    Esta é a função principal do Nível 3.
    """
    global caminho_arquivo_log
    
    try:
        # 1. Decodifica o payload JSON
        payload_str = msg.payload.decode("utf-8")
        pacote = json.loads(payload_str)
        
        # 2. Extrai os dados do pacote
        timestamp = pacote.get("timestamp", "")
        id_can = pacote.get("id_can", "")
        prioridade = pacote.get("prioridade", "")
        # Converte a lista de inteiros para uma string formatada
        dados_str = ' '.join(f'{b:02X}' for b in pacote.get("dados", []))

        # 3. Prepara a linha para o CSV
        linha_csv = [timestamp, id_can, prioridade, dados_str]
        
        # 4. Escreve a linha no arquivo CSV
        with open(caminho_arquivo_log, mode='a', newline='', encoding='utf-8') as arquivo_csv:
            escritor_csv = csv.writer(arquivo_csv)
            escritor_csv.writerow(linha_csv)
            
        print(f"Recebido e salvo: {linha_csv}")

    except Exception as e:
        print(f"ERRO ao processar mensagem: {e} | Payload recebido: {msg.payload}")


if __name__ == "__main__":
    # Garante que a pasta de armazenamento (Nível 4) exista
    os.makedirs(PASTA_ARMAZENAMENTO, exist_ok=True)
    
    # Cria um nome de arquivo único para esta sessão de telemetria
    timestamp_inicio = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_arquivo = f"log_telemetria_{timestamp_inicio}.csv"
    caminho_arquivo_log = os.path.join(PASTA_ARMAZENAMENTO, nome_arquivo)

    # Cria o arquivo CSV e escreve o cabeçalho
    with open(caminho_arquivo_log, mode='w', newline='', encoding='utf-8') as arquivo_csv:
        escritor_csv = csv.writer(arquivo_csv)
        escritor_csv.writerow(["timestamp", "id_can", "prioridade", "dados_hex"])
    
    print(f"Sessão de log iniciada. Salvando dados em: {caminho_arquivo_log}")

    # Configura e conecta o cliente MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER_IP, BROKER_PORT, 60)
    except Exception as e:
        print(f"ERRO: Não foi possível conectar ao Broker MQTT. {e}")
        print("Verifique se o broker (como Mosquitto) está rodando.")
        exit(1)

    # Inicia o loop para receber mensagens. Este comando bloqueia a execução.
    client.loop_forever()