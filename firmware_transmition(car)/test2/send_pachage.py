import paho.mqtt.client as mqtt
import json
import time

# --- CONFIGURAÇÕES DO TESTE ---
# Endereço IP do computador no box que está rodando o broker MQTT
# Para testar localmente, você pode usar "localhost"
BROKER_IP = "localhost" # ou o IP do seu receptor
BROKER_PORT = 1883
MQTT_TOPIC = "telemetria/dados_brutos"
# --- FIM DAS CONFIGURAÇÕES ---

def main():
    """
    Função principal que executa o teste de envio.
    """
    print(">>> INICIANDO TESTE 2: Envio de Pacote MQTT <<<")

    # --- Etapa 1: Criar um pacote de teste simulado ---
    # Não precisamos do Nível 1 aqui, pois o foco é testar o envio.
    # Criamos o pacote diretamente.
    print("\n--- Etapa 1: Criando um pacote de dados simulado ---")
    pacote_de_teste = {
        "id_can": "0x410",
        "dados": [0xAA, 0xBB, 0xCC, 0xDD],
        "prioridade": 2,
        "timestamp": time.time()
    }
    payload = json.dumps(pacote_de_teste)
    print(f"Pacote a ser enviado: {payload}")

    # --- Etapa 2: Conectar ao broker MQTT ---
    print(f"\n--- Etapa 2: Conectando ao broker em {BROKER_IP}:{BROKER_PORT} ---")
    client = mqtt.Client()
    try:
        client.connect(BROKER_IP, BROKER_PORT, 60)
        print("Conexão bem-sucedida!")
    except Exception as e:
        print(f"ERRO: Falha ao conectar ao broker. Verifique o IP e se o broker está rodando.")
        print(e)
        print("\n>>> TESTE 2 FALHOU <<<")
        return

    # --- Etapa 3: Publicar a mensagem e verificar o resultado ---
    print("\n--- Etapa 3: Publicando a mensagem no tópico... ---")
    
    # O método publish() retorna um objeto com informações sobre a publicação.
    # O mais importante é o 'rc' (return code). Se for 0, significa sucesso.
    result = client.publish(MQTT_TOPIC, payload)
    
    # Aguarda um instante para garantir que a mensagem foi processada
    result.wait_for_publish()

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"SUCESSO! Mensagem publicada no tópico '{MQTT_TOPIC}' sem erros.")
    else:
        print(f"FALHA! A biblioteca MQTT retornou o código de erro: {result.rc}")

    # --- Etapa 4: Desconectar ---
    client.disconnect()
    print("\nDesconectado do broker.")
    print("\n>>> TESTE 2 CONCLUÍDO <<<")


if __name__ == "__main__":
    main()