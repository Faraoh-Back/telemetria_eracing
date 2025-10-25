import paho.mqtt.client as mqtt # Biblioteca para comunicação MQTT (receber dados do carro)
import json                     # Para decodificar mensagens JSON recebidas
import os                       # Para interagir com o sistema de arquivos (criar pasta, verificar arquivos)
import csv                      # Para escrever dados no formato CSV
from datetime import datetime   # Para gerar timestamps e nomes de arquivo únicos
import time                     # Para usar pausas (sleep)
import threading                # Para usar 'Events' para sinalizar parada da thread

# --- CONFIGURAÇÕES ---
# Endereço IP do Broker MQTT. Como este script roda no mesmo PC que o Mosquitto, usamos "localhost".
BROKER_IP = "localhost"
# Porta padrão do protocolo MQTT.
BROKER_PORT = 1883
# Tópico MQTT onde o Nível 2 (transmitter.py no carro) publica os dados brutos.
MQTT_TOPIC = "telemetria/dados_brutos"

# Nível 4: Define a pasta onde os arquivos CSV de log serão salvos.
# O caminho '../Nivel_4/' assume que este script está em Nivel_3/ e Nivel_4/ está ao lado.
# Ajuste se sua estrutura de pastas for diferente.
PASTA_ARMAZENAMENTO = "../Nivel_4/"
# --- FIM DAS CONFIGURAÇÕES ---

# --- Variáveis Globais ---
# Guarda o caminho completo do arquivo CSV que está sendo escrito nesta sessão.
caminho_arquivo_log = ""
# Guarda a instância do cliente MQTT para podermos desconectá-lo ao parar.
client_mqtt = None
# Um objeto 'Event' do threading. Usado como uma "bandeira" para sinalizar
# de forma segura (thread-safe) que a thread principal deve parar sua execução.
parar_collector = threading.Event()

# --- Callbacks MQTT (Funções chamadas pela biblioteca Paho MQTT) ---

def on_connect(client, userdata, flags, rc):
    """
    Função chamada automaticamente pela biblioteca Paho MQTT quando a conexão
    com o Broker é estabelecida (ou falha).
    'rc' (result code) indica o status da conexão. 0 significa sucesso.
    """
    if rc == 0:
        # Se conectou com sucesso, imprime uma mensagem informativa.
        print("Nível 3 (Collector): Conectado ao Broker MQTT com sucesso!")
        try:
            # Tenta se inscrever (subscribe) no tópico configurado.
            # A partir daqui, o Broker enviará para este cliente todas as mensagens
            # publicadas no tópico MQTT_TOPIC.
            client.subscribe(MQTT_TOPIC)
            print(f"Nível 3 (Collector): Inscrito no tópico: {MQTT_TOPIC}")
        except Exception as e:
            # Informa se houve erro durante a inscrição.
            print(f"Nível 3 (Collector): Erro ao inscrever no tópico: {e}")
    else:
        # Se a conexão falhou, informa o código de erro.
        # Códigos comuns: 3 (Servidor indisponível), 4 (Usuário/senha inválidos), 5 (Não autorizado).
        print(f"Nível 3 (Collector): Falha na conexão, código: {rc} ({mqtt.error_string(rc)})")

def on_message(client, userdata, msg):
    """
    Função chamada automaticamente pela biblioteca Paho MQTT sempre que uma
    nova mensagem chega em um tópico que este cliente assinou (neste caso, MQTT_TOPIC).
    'msg' é um objeto que contém o tópico (msg.topic) e o payload (msg.payload).
    """
    global caminho_arquivo_log # Acessa a variável global que contém o nome do arquivo de log

    # Verifica se o arquivo de log foi criado com sucesso antes de tentar escrever.
    if not caminho_arquivo_log:
        print("Nível 3 (Collector): AVISO - Arquivo de log não definido, descartando mensagem.")
        return # Sai da função se não houver onde salvar

    try:
        # 1. Decodifica o Payload: O payload da mensagem MQTT chega como bytes.
        #    Assumimos que o Nível 2 enviou texto codificado em UTF-8.
        payload_str = msg.payload.decode("utf-8")

        # 2. Parseia o JSON: Converte a string JSON recebida em um dicionário Python.
        pacote = json.loads(payload_str)

        # 3. Extrai os Dados: Pega os valores do dicionário.
        #    Usa .get() com um valor padrão para evitar erros caso a chave não exista na mensagem.
        timestamp = pacote.get("timestamp", time.time()) # Pega o timestamp do pacote ou usa o atual
        id_can = pacote.get("id_can", "ID_AUSENTE")      # Pega o ID CAN ou "ID_AUSENTE"
        prioridade = pacote.get("prioridade", "PRIO_AUSENTE") # Pega a prioridade ou "PRIO_AUSENTE"
        # Pega a lista de dados (inteiros) e converte para uma string hexadecimal formatada.
        # Ex: [11, 22, 33, 44] -> "0B 16 21 2C"
        dados_lista = pacote.get("dados", [])
        dados_str = ' '.join(f'{b:02X}' for b in dados_lista)

        # 4. Prepara a Linha CSV: Cria uma lista com os dados na ordem das colunas do CSV.
        linha_csv = [timestamp, id_can, prioridade, dados_str]

        # 5. Escreve no CSV:
        #    Abre o arquivo CSV no modo 'append' ('a'), o que adiciona a linha no final.
        #    'newline=''' evita linhas em branco extras no CSV.
        with open(caminho_arquivo_log, mode='a', newline='', encoding='utf-8') as arquivo_csv:
            # Cria um objeto escritor CSV.
            escritor_csv = csv.writer(arquivo_csv)
            # Escreve a linha preparada no arquivo.
            escritor_csv.writerow(linha_csv)

        # 6. Log (Opcional): Imprime no console que o dado foi salvo (pode ser removido se gerar muito output).
        # print(f"Nível 3 (Collector): Dado salvo -> {linha_csv}")

    except json.JSONDecodeError:
        # Captura erro se a mensagem recebida não for um JSON válido.
        print(f"Nível 3 (Collector): ERRO - Mensagem recebida não é JSON válido: {msg.payload.decode('utf-8', errors='ignore')}")
    except Exception as e:
        # Captura outros erros inesperados durante o processamento ou escrita.
        print(f"Nível 3 (Collector): ERRO ao processar/salvar mensagem: {e}")

# --- Funções de Controle (para serem chamadas pelo Nível 6) ---

def run_collector():
    """
    Função principal que configura e inicia o processo de coleta de dados MQTT.
    Esta função será executada em uma thread separada pelo Nível 6.
    """
    global caminho_arquivo_log, client_mqtt, parar_collector # Permite modificar as variáveis globais

    print("Nível 3 (Collector): Iniciando...")
    parar_collector.clear() # Garante que a "bandeira" de parada esteja abaixada no início.

    # Garante que a pasta de armazenamento (Nível 4) exista.
    try:
        # exist_ok=True evita erro se a pasta já existir.
        os.makedirs(PASTA_ARMAZENAMENTO, exist_ok=True)
    except Exception as e:
        print(f"Nível 3 (Collector): ERRO FATAL ao criar pasta de logs '{PASTA_ARMAZENAMENTO}': {e}")
        return # Encerra a função (e a thread) se não puder criar a pasta.

    # Cria um nome de arquivo único para esta sessão de coleta, baseado na data e hora.
    timestamp_inicio = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_arquivo = f"log_telemetria_{timestamp_inicio}.csv"
    # Junta o nome da pasta e o nome do arquivo para ter o caminho completo.
    caminho_arquivo_log = os.path.join(PASTA_ARMAZENAMENTO, nome_arquivo)

    # Cria o arquivo CSV e escreve a linha de cabeçalho.
    try:
        # Abre o arquivo no modo 'write' ('w') para criar ou sobrescrever.
        with open(caminho_arquivo_log, mode='w', newline='', encoding='utf-8') as arquivo_csv:
            escritor_csv = csv.writer(arquivo_csv)
            # Define os nomes das colunas.
            escritor_csv.writerow(["timestamp", "id_can", "prioridade", "dados_hex"])
        print(f"Nível 3 (Collector): Sessão de log iniciada. Salvando em: {caminho_arquivo_log}")
    except IOError as e:
        # Captura erro se não conseguir criar/escrever no arquivo (ex: permissão negada).
        print(f"Nível 3 (Collector): ERRO FATAL ao criar arquivo de log '{caminho_arquivo_log}': {e}")
        caminho_arquivo_log = "" # Reseta a variável para evitar erros no on_message.
        return # Encerra a função (e a thread).

    # Configura o cliente MQTT
    client_mqtt = mqtt.Client() # Cria a instância do cliente.
    client_mqtt.on_connect = on_connect # Associa a função on_connect ao evento de conexão.
    client_mqtt.on_message = on_message # Associa a função on_message ao evento de recebimento de mensagem.

    try:
        # Tenta conectar ao Broker MQTT. O '60' é o keep_alive em segundos.
        client_mqtt.connect(BROKER_IP, BROKER_PORT, 60)

        # Inicia o loop de rede MQTT em uma thread separada.
        # Isso permite que o Paho MQTT gerencie a rede (receber mensagens, enviar pings)
        # em background, sem bloquear nosso loop principal abaixo.
        client_mqtt.loop_start()

        print("Nível 3 (Collector): Aguardando mensagens MQTT...")
        # Loop principal da thread: mantém a thread viva enquanto a "bandeira"
        # 'parar_collector' não for levantada pela função stop_collector().
        while not parar_collector.is_set():
            # Dorme por um curto período para não consumir 100% da CPU.
            time.sleep(0.5)

    except ConnectionRefusedError:
        print(f"Nível 3 (Collector): ERRO - Conexão MQTT recusada. Verifique se o broker ({BROKER_IP}) está rodando e acessível.")
    except OSError as e: # Ex: Network is unreachable
        print(f"Nível 3 (Collector): ERRO de rede ao conectar ao MQTT: {e}")
    except Exception as e:
        # Captura outros erros inesperados durante a conexão ou loop.
        print(f"Nível 3 (Collector): ERRO inesperado: {e}")
    finally:
        # Bloco de limpeza: será executado sempre que a thread terminar (normalmente ou por erro).
        print("Nível 3 (Collector): Encerrando...")
        # Verifica se o cliente MQTT foi criado e se está conectado antes de tentar parar/desconectar.
        if client_mqtt and client_mqtt.is_connected():
            client_mqtt.loop_stop() # Para a thread de rede do Paho MQTT.
            client_mqtt.disconnect() # Envia o comando DISCONNECT para o Broker.
        print("Nível 3 (Collector): Desconectado.")
        caminho_arquivo_log = "" # Limpa o caminho do log para a próxima execução.

def stop_collector():
    """
    Função para ser chamada externamente (pelo Nível 6) para sinalizar
    que a thread do collector deve parar sua execução de forma limpa.
    """
    global parar_collector # Acessa a "bandeira" global
    print("Nível 3 (Collector): Solicitando parada...")
    # Levanta a "bandeira". O loop 'while' na função run_collector() detectará isso e sairá.
    parar_collector.set()

# --- Bloco Principal (Comentado/Removido) ---
# Removemos ou comentamos o bloco 'if __name__ == "__main__":'
# para que este script funcione como uma biblioteca que pode ser importada
# e controlada pelo Nível 6, em vez de executar automaticamente quando chamado.
#
# if __name__ == "__main__":
#     try:
#         # Inicia o processo de coleta.
#         run_collector()
#     except KeyboardInterrupt:
#         # Se o usuário pressionar Ctrl+C, solicita a parada limpa.
#         print("\nNível 3 (Collector): Ctrl+C recebido. Encerrando...")
#         stop_collector()
#     except Exception as e:
#         print(f"Nível 3 (Collector): Erro fatal não capturado: {e}")
#         stop_collector() # Tenta parar mesmo em caso de erro