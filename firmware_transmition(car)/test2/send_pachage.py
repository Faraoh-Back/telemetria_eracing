# Arquivo: test2_envio_pacote.py
import paho.mqtt.client as mqtt
import json
import time

# --- CONFIGURAÇÕES DO TESTE ---
# Como o broker (Mosquitto) está rodando na mesma máquina, usamos "localhost"
BROKER_IP = "localhost"
BROKER_PORT = 1883
MQTT_TOPIC = "telemetria/dados_brutos" # O mesmo tópico que o receptor escuta
# --- FIM DAS CONFIGURAÇÕES ---

def main():
    """
    Função principal que executa o teste de envio.
    """
    print(">>> INICIANDO TESTE 2 (Modificado): Envio de Pacote MQTT Local <<<")

    # --- Etapa 1: Criar um pacote de dados simulado ("mocado") ---
    print("\n--- Etapa 1: Criando um pacote de dados simulado ---")
    pacote_de_teste = {
        "id_can": "0xABC", # ID simulado
        "dados": [11, 22, 33, 44], # Dados simulados
        "prioridade": 3,
        "timestamp": time.time() # Timestamp atual
    }
    payload = json.dumps(pacote_de_teste)
    print(f"Pacote a ser enviado: {payload}")

    # --- Etapa 2: Conectar ao broker MQTT local ---
    print(f"\n--- Etapa 2: Conectando ao broker em {BROKER_IP}:{BROKER_PORT} ---")
    client = mqtt.Client()
    try:
        # Tenta conectar ao broker local
        client.connect(BROKER_IP, BROKER_PORT, 60)
        # Inicia a thread de rede do MQTT em background
        client.loop_start()
        print("Conexão bem-sucedida!")
    except Exception as e:
        print(f"ERRO: Falha ao conectar ao broker local. Verifique se o Mosquitto está rodando.")
        print(e)
        print("\n>>> TESTE 2 FALHOU <<<")
        return

    # --- Etapa 3: Publicar a mensagem e verificar o resultado ---
    print("\n--- Etapa 3: Publicando a mensagem no tópico... ---")
    # Publica a mensagem no tópico especificado
    result = client.publish(MQTT_TOPIC, payload)

    # Espera a confirmação da publicação (ou timeout)
    try:
        result.wait_for_publish(timeout=5) # Espera até 5 segundos
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"SUCESSO! Mensagem publicada no tópico '{MQTT_TOPIC}' sem erros.")
        else:
            print(f"FALHA! A biblioteca MQTT retornou o código de erro: {result.rc} ({mqtt.error_string(result.rc)})")
    except ValueError:
        print("FALHA! Timeout esperando confirmação da publicação. A mensagem pode não ter sido enviada.")
    except RuntimeError as e:
         print(f"FALHA! Erro durante a publicação: {e}")


    # --- Etapa 4: Desconectar ---
    # Para a thread de rede e desconecta
    client.loop_stop()
    client.disconnect()
    print("\nDesconectado do broker.")
    print("\n>>> TESTE 2 CONCLUÍDO <<<")


if __name__ == "__main__":
    main()