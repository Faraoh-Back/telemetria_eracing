# Arquivo: nivel_3_e_4_receptor.py
import paho.mqtt.client as mqtt
import json
import os
import csv
from datetime import datetime
import time

# --- CONFIGURAÇÕES ---
# Como o broker (Mosquitto) está rodando na mesma máquina, usamos "localhost".
BROKER_IP = "localhost"
BROKER_PORT = 1883
MQTT_TOPIC = "telemetria/dados_brutos" # O tópico que vamos escutar

# Nível 4: Pasta onde os logs CSV serão salvos.
PASTA_ARMAZENAMENTO = "./dados_brutos_telemetria_teste_local/" # Pasta diferente para o teste
# --- FIM DAS CONFIGURAÇÕES ---

# Variável global para guardar o caminho do arquivo de log da sessão atual
caminho_arquivo_log = ""

def on_connect(client, userdata, flags, rc):
    """Callback chamado quando o cliente se conecta ao broker."""
    if rc == 0:
        print("Nível 3: Conectado ao Broker MQTT local com sucesso!")
        # Inscreve-se no tópico para começar a receber mensagens
        client.subscribe(MQTT_TOPIC)
        print(f"Nível 3: Inscrito no tópico: {MQTT_TOPIC}")
    else:
        print(f"Falha na conexão, código de retorno: {rc} ({mqtt.error_string(rc)})\n")

def on_message(client, userdata, msg):
    """
    Callback chamado sempre que uma mensagem é recebida do tópico assinado.
    Nível 3: Recebe a mensagem.
    Nível 4: Formata e salva a mensagem no CSV.
    """
    global caminho_arquivo_log

    try:
        # Nível 3: Decodifica o payload JSON recebido
        payload_str = msg.payload.decode("utf-8")
        pacote = json.loads(payload_str)
        print(f"Nível 3: Mensagem recebida -> {payload_str}") # Mostra a mensagem recebida

        # Nível 4: Extrai os dados e prepara a linha para o CSV
        timestamp = pacote.get("timestamp", time.time()) # Usa timestamp atual se não vier
        id_can = pacote.get("id_can", "N/A")
        prioridade = pacote.get("prioridade", "N/A")
        # Converte a lista de inteiros para uma string hexadecimal formatada
        dados_str = ' '.join(f'{b:02X}' for b in pacote.get("dados", []))

        linha_csv = [timestamp, id_can, prioridade, dados_str]

        # Nível 4: Escreve a linha no arquivo CSV da sessão
        with open(caminho_arquivo_log, mode='a', newline='', encoding='utf-8') as arquivo_csv:
            escritor_csv = csv.writer(arquivo_csv)
            escritor_csv.writerow(linha_csv)

        print(f"Nível 4: Dado salvo no CSV -> {linha_csv}")

    except json.JSONDecodeError:
        print(f"ERRO: Mensagem recebida não é um JSON válido: {msg.payload.decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"ERRO ao processar mensagem: {e} | Payload: {msg.payload}")


if __name__ == "__main__":
    # Nível 4: Garante que a pasta de armazenamento exista
    os.makedirs(PASTA_ARMAZENAMENTO, exist_ok=True)

    # Cria um nome de arquivo único para esta sessão de teste
    timestamp_inicio = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_arquivo = f"log_teste_local_{timestamp_inicio}.csv"
    caminho_arquivo_log = os.path.join(PASTA_ARMAZENAMENTO, nome_arquivo)

    # Cria o arquivo CSV e escreve o cabeçalho
    try:
        with open(caminho_arquivo_log, mode='w', newline='', encoding='utf-8') as arquivo_csv:
            escritor_csv = csv.writer(arquivo_csv)
            escritor_csv.writerow(["timestamp", "id_can", "prioridade", "dados_hex"])
        print(f"Nível 4: Sessão de log iniciada. Salvando dados em: {caminho_arquivo_log}")
    except IOError as e:
        print(f"ERRO ao criar o arquivo de log: {e}")
        exit(1)


    # Nível 3: Configura o cliente MQTT para receber
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # Tenta conectar ao broker local
        client.connect(BROKER_IP, BROKER_PORT, 60)
    except Exception as e:
        print(f"ERRO (Nível 3): Não foi possível conectar ao Broker local. Verifique se o Mosquitto está rodando. {e}")
        exit(1)

    # Inicia o loop para receber mensagens. Este comando bloqueia a execução
    # até que o script seja interrompido (Ctrl+C).
    try:
        print("Nível 3: Aguardando mensagens... (Pressione Ctrl+C para sair)")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nNível 3: Interrupção recebida. Desconectando...")
        client.disconnect()
        print("Nível 3: Desconectado.")