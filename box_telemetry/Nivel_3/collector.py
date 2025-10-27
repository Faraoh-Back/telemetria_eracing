# Arquivo: Nivel_3/collector.py (Refatorado para Processar Dados e Salvar CSV Decodificado)

# --- Importações Essenciais ---
import paho.mqtt.client as mqtt # Biblioteca MQTT
import json                     # Decodificar JSON
import os                       # Manipulação de arquivos/pastas
import csv                      # Escrita em CSV
from datetime import datetime   # Timestamps para nome de arquivo
import time                     # Timestamps fallback
import threading                # Para Event de parada (se usado como lib)
import pandas as pd             # Para ler eficientemente os CSVs de descrição CAN

# --- CONFIGURAÇÕES ---
# MQTT
BROKER_IP = "localhost"         # IP do Broker MQTT (onde o Mosquitto está)
BROKER_PORT = 1883              # Porta MQTT padrão
MQTT_TOPIC = "telemetria/dados_brutos" # Tópico para escutar dados brutos do Nível 2

# Processamento CAN
# ATENÇÃO: Verifique se este caminho está correto para onde seus CSVs de descrição CAN estão!
# Deve apontar para a pasta que contém 'CAN Description 2025 - BMS.csv', etc.
# Exemplo: Se Nível 3 está ao lado de Nível 1, o caminho pode ser "../Nivel_1/componentes_csv_linux/"
PASTA_CSV_COMPONENTES = "componentes_csv_linux/"

# Nível 4: Onde salvar o CSV com os DADOS PROCESSADOS
# O caminho '../Nivel_4/' assume Nivel_3 e Nivel_4 lado a lado, um nível abaixo do orquestrador.
PASTA_ARMAZENAMENTO_PROCESSADO = "../Nivel_4/processados/" # Pasta para logs processados
NOME_ARQUIVO_PROCESSADO_PREFIXO = "log_processado_"
# --- FIM DAS CONFIGURAÇÕES ---

# --- Variáveis Globais ---
# Guarda o caminho completo do arquivo CSV PROCESSADO sendo escrito nesta sessão.
caminho_arquivo_log_proc = ""
# Cliente MQTT
client_mqtt = None
# Flag para parada (se usado como biblioteca)
parar_collector = threading.Event()
# Dicionário para guardar os DataFrames do Pandas com as descrições CAN carregadas.
planilhas_can = {}

# --- Funções de Processamento CAN (Adaptadas) ---

def carregar_planilhas_can(pasta_csv):
    """
    Lê todos os arquivos 'CAN Description*.csv' da pasta especificada
    e os armazena no dicionário global 'planilhas_can' como DataFrames Pandas.
    Chave do dicionário: Nome base do componente (ex: 'BMS', 'VCU').
    Valor: DataFrame Pandas com o conteúdo do CSV.
    """
    global planilhas_can
    print(f"Nível 3 (Collector-Processor): Carregando descrições CAN de: {pasta_csv}")
    arquivos_carregados = 0
    try:
        if not os.path.isdir(pasta_csv):
            raise FileNotFoundError(f"Pasta de descrições CAN não encontrada: {pasta_csv}")

        for nome_arquivo in os.listdir(pasta_csv):
            # Procura por arquivos que sigam o padrão esperado
            if nome_arquivo.lower().endswith(".csv") and "CAN Description" in nome_arquivo:
                caminho_completo = os.path.join(pasta_csv, nome_arquivo)
                try:
                    # Lê o CSV usando pandas. Assume sem cabeçalho, ignora linhas vazias/comentários.
                    df = pd.read_csv(caminho_completo, header=None, skip_blank_lines=True, comment='/')
                    # Extrai o nome do componente do nome do arquivo (ex: 'BMS', 'VCU').
                    chave_planilha = nome_arquivo.split(' - ')[-1].split('.')[0]
                    planilhas_can[chave_planilha] = df
                    print(f"  - Carregado: '{nome_arquivo}' como chave '{chave_planilha}'")
                    arquivos_carregados += 1
                except pd.errors.EmptyDataError:
                    print(f"AVISO (Nível 3): Arquivo CSV vazio ou inválido: {nome_arquivo}")
                except Exception as e:
                    print(f"ERRO (Nível 3) ao ler CSV '{nome_arquivo}': {e}")

        if arquivos_carregados == 0:
             print("AVISO (Nível 3): Nenhuma planilha de descrição CAN foi carregada. O processamento de dados não funcionará.")
        else:
             print(f"Nível 3: {arquivos_carregados} planilhas CAN carregadas.")

    except FileNotFoundError as e:
        print(f"ERRO FATAL (Nível 3): {e}. Verifique a configuração PASTA_CSV_COMPONENTES.")
        # Se não puder carregar, não adianta continuar. Poderia parar o script aqui.
        exit(1) # Ou retornar False para indicar falha na inicialização
    except Exception as e:
        print(f"ERRO inesperado (Nível 3) ao carregar planilhas CAN: {e}")
        exit(1) # Ou retornar False

def extrair_valor_can(data_bytes, posicao_str, tamanho_str, tipo='int'):
    """
    Função auxiliar para extrair um valor de 'data_bytes' com base na
    'posicao_str' (ex: 'byte(0)', 'bit(8-15)') e 'tamanho_str' (bits).

    Retorna o valor bruto (int) ou None em caso de erro.

    IMPORTANTE: Assume Little Endian e numeração de bits padrão. Ajustar se necessário.
    """
    try:
        tamanho_bits = int(tamanho_str)
        posicao_inicial_bits = 0

        # Determina a posição inicial em bits
        if 'byte(' in posicao_str:
            byte_num = int(posicao_str.replace('byte(', '').replace(')', ''))
            posicao_inicial_bits = byte_num * 8
        elif 'bit(' in posicao_str:
            # Assume que 'bit(X)' ou 'bit(X-Y)' se refere ao bit inicial (LSB)
            bit_def = posicao_str.replace('bit(', '').replace(')', '')
            posicao_inicial_bits = int(bit_def.split('-')[0]) # Pega o primeiro número
        else:
            # print(f"AVISO (Nível 3): Formato de posição desconhecido '{posicao_str}'")
            return None # Formato não reconhecido

        # Calcula quantos bytes são necessários
        byte_final_necessario = (posicao_inicial_bits + tamanho_bits + 7) // 8
        if len(data_bytes) < byte_final_necessario:
            # print(f"AVISO (Nível 3): Bytes insuficientes ({len(data_bytes)}) para extrair sinal na pos {posicao_inicial_bits}, tam {tamanho_bits}")
            return None

        # Converte os bytes relevantes para um único inteiro (assumindo Little Endian)
        valor_total_int = int.from_bytes(data_bytes[:byte_final_necessario], byteorder='little')

        # Cria a máscara de bits
        mascara = (1 << tamanho_bits) - 1

        # Desloca e aplica a máscara para isolar o valor
        valor_extraido_int = (valor_total_int >> posicao_inicial_bits) & mascara

        # TODO: Implementar tratamento para 'signed' se necessário
        # Ex: if tipo == 'signed_int' and (valor_extraido_int >> (tamanho_bits - 1)) & 1:
        #        valor_extraido_int = valor_extraido_int - (1 << tamanho_bits)

        return valor_extraido_int

    except (ValueError, TypeError) as e:
        # print(f"ERRO (Nível 3) ao converter parâmetros de extração: {e} (pos='{posicao_str}', tam='{tamanho_str}')")
        return None
    except Exception as e:
        # print(f"ERRO (Nível 3) inesperado em extrair_valor_can: {e}")
        return None


def processar_mensagem_can(id_int, data_bytes):
    """
    Busca o ID CAN nas planilhas carregadas e retorna uma lista de tuplas
    contendo os sinais decodificados encontrados para essa mensagem.
    Formato da tupla: (nome_sinal_unico, valor_final_processado)
    Retorna uma lista vazia se o ID não for encontrado ou não houver sinais válidos.
    """
    global planilhas_can
    sinais_decodificados = [] # Lista para guardar os resultados

    # Formata ID como string hexadecimal (Ex: 0x1A3) para busca no DataFrame
    id_hex_str_upper = f"0x{id_int:03X}"

    # Itera sobre cada planilha carregada (BMS, VCU, etc.)
    for nome_planilha, df in planilhas_can.items():
        try:
            # Procura linhas onde a coluna 1 (índice 1) corresponde ao ID_hex (case-insensitive)
            linhas_id = df[df[1].astype(str).str.strip().str.upper() == id_hex_str_upper]

            # Se encontrou linhas para este ID nesta planilha...
            if not linhas_id.empty:
                # Itera sobre cada linha encontrada (pode haver múltiplos sinais por ID)
                for index, linha in linhas_id.iterrows():
                    try:
                        # Extrai informações das colunas conforme o formato do seu CSV
                        # Os índices [0], [1], [2]... correspondem às colunas A, B, C...
                        nome_sinal = str(linha[0]).strip() if pd.notna(linha[0]) else None
                        # id_hex_csv = str(linha[1]).strip() # Já usamos para encontrar a linha
                        posicao_str = str(linha[2]).strip() if pd.notna(linha[2]) else None # Ex: 'byte(0)', 'bit(8-15)'
                        tamanho_str = str(linha[3]).strip() if pd.notna(linha[3]) else None # Ex: '8', '16' (em bits)
                        tipo = str(linha[4]).strip().lower() if pd.notna(linha[4]) else 'int' # int, float, bool, state, etc.
                        # min_val = linha[5] # Não usado na decodificação, mas poderia ser para validação
                        # max_val = linha[6] # Não usado
                        multiplicador_str = str(linha[7]).strip() if pd.notna(linha[7]) else '1' # Coluna H (índice 7)
                        offset_str = str(linha[8]).strip() if pd.notna(linha[8]) else '0' # Coluna I (índice 8)
                        # unit = linha[9] # Não usado aqui, mas útil para visualização
                        # description = linha[10] # Não usado

                        # Verifica se temos as informações mínimas para decodificar
                        if not nome_sinal or not posicao_str or not tamanho_str:
                            continue # Pula esta linha/sinal se estiver mal formatada

                        # Converte multiplicador e offset para números float
                        multiplicador = float(multiplicador_str) if multiplicador_str else 1.0
                        offset = float(offset_str) if offset_str else 0.0

                        # Extrai o valor bruto (inteiro) dos bytes usando a função auxiliar
                        valor_bruto = extrair_valor_can(data_bytes, posicao_str, tamanho_str, tipo)

                        # Se a extração foi bem-sucedida...
                        if valor_bruto is not None:
                            # Aplica a fórmula: valor_final = (valor_bruto * multiplicador) + offset
                            valor_final = (valor_bruto * multiplicador) + offset

                            # Cria um nome único para o sinal (ex: 'BMS_vcell_0')
                            chave_unica = f"{nome_planilha}_{nome_sinal}"

                            # Adiciona o resultado à lista de sinais decodificados
                            sinais_decodificados.append((chave_unica, valor_final))
                            # print(f"  -> Decodificado: {chave_unica} = {valor_final}") # Debug

                    except Exception as e_linha:
                        # Loga erro se falhar ao processar uma linha específica do CSV
                        # print(f"AVISO (Nível 3): Erro ao processar linha {index} da planilha {nome_planilha} para ID {id_hex_str_upper}: {e_linha}")
                        continue # Continua para o próximo sinal/linha

                # Se encontrou o ID nesta planilha, não precisa procurar nas outras
                # (Assume que um ID pertence a apenas um componente/planilha)
                return sinais_decodificados # Retorna a lista de sinais encontrados

        except Exception as e_planilha:
            # Loga erro se falhar ao processar uma planilha inteira (raro)
            print(f"ERRO (Nível 3) ao processar planilha {nome_planilha} para ID {id_hex_str_upper}: {e_planilha}")
            continue # Tenta a próxima planilha

    # Se saiu do loop sem retornar, significa que o ID não foi encontrado em nenhuma planilha
    # print(f"AVISO (Nível 3): ID {id_hex_str_upper} não definido em nenhuma planilha CAN.")
    return sinais_decodificados # Retorna lista vazia


# --- Callbacks MQTT ---

def on_connect(client, userdata, flags, rc):
    """Callback de conexão MQTT (igual ao anterior)."""
    if rc == 0:
        print("Nível 3 (Collector-Processor): Conectado ao Broker MQTT!")
        try:
            client.subscribe(MQTT_TOPIC)
            print(f"Nível 3: Inscrito no tópico: {MQTT_TOPIC}")
        except Exception as e:
            print(f"Nível 3: Erro ao inscrever no tópico: {e}")
    else:
        print(f"Nível 3: Falha na conexão MQTT, código: {rc} ({mqtt.error_string(rc)})")

def on_message(client, userdata, msg):
    """
    Callback chamado para cada mensagem MQTT recebida.
    Agora, decodifica a mensagem CAN e salva os sinais processados no CSV.
    """
    global caminho_arquivo_log_proc # Usa o caminho do log processado

    # Verifica se o arquivo de log foi inicializado
    if not caminho_arquivo_log_proc:
        return

    try:
        # 1. Decodifica Payload MQTT e Extrai Dados Brutos
        payload_str = msg.payload.decode("utf-8")
        pacote_bruto = json.loads(payload_str)

        id_can_str = pacote_bruto.get("id_can")
        dados_lista = pacote_bruto.get("dados")
        timestamp = pacote_bruto.get("timestamp", "Sem tempo irmão")
        prioridade = pacote_bruto.get("prioridade", 4)

        # Validação básica
        if id_can_str is None or dados_lista is None:
            print(f"AVISO (Nível 3): Mensagem MQTT inválida recebida: {payload_str}")
            return

        # Converte ID string (ex: "0xABC") para inteiro
        id_int = int(id_can_str, 16)
        # Converte lista de dados (inteiros) para objeto bytes
        data_bytes = bytes(dados_lista)

        # 2. Processa a Mensagem CAN Bruta
        #    Chama a função que usa as planilhas para decodificar os bytes
        lista_sinais_processados = processar_mensagem_can(id_int, data_bytes)

        # 3. Salva Cada Sinal Processado no CSV
        #    Se a função retornou algum sinal decodificado...
        if lista_sinais_processados:
            # Abre o arquivo CSV processado no modo append ('a')
            with open(caminho_arquivo_log_proc, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Para cada sinal (nome, valor) na lista...
                for nome_sinal, valor_sinal in lista_sinais_processados:
                    # Cria a linha no formato do log_teste_local*.csv:
                    # names, timestamp, id_can, prioridade, dado
                    linha_csv = [nome_sinal, timestamp, id_can_str, prioridade, f"{valor_sinal:.4f}"] # Formata valor com 4 casas decimais
                    # Escreve a linha no arquivo
                    writer.writerow(linha_csv)
            print(f"Nível 3: Sinais salvos para ID {id_can_str}: {len(lista_sinais_processados)}") # Log Opcional

    except json.JSONDecodeError:
        print(f"ERRO (Nível 3): Mensagem MQTT não é JSON válido: {msg.payload.decode('utf-8', errors='ignore')}")
    except ValueError as e:
         print(f"ERRO (Nível 3): Erro ao converter dados da mensagem MQTT: {e}. Payload: {payload_str}")
    except Exception as e:
        print(f"ERRO (Nível 3) inesperado em on_message: {e}")

# --- Função Principal de Execução ---
# (Mantida a mesma estrutura para iniciar/parar via Nível 7, se necessário,
#  mas o bloco if __name__ == '__main__' permite rodar standalone)

def run_collector():
    """Função principal para iniciar o coletor e processador."""
    global caminho_arquivo_log_proc, client_mqtt, parar_collector

    print("Nível 3 (Collector-Processor): Iniciando...")
    parar_collector.clear()

    # --- Carrega as Descrições CAN ---
    # É crucial carregar isso antes de conectar ao MQTT
    carregar_planilhas_can(PASTA_CSV_COMPONENTES)
    if not planilhas_can:
        print("ERRO FATAL (Nível 3): Falha ao carregar descrições CAN. Encerrando.")
        return # Sai se não conseguir carregar

    # --- Configura o Arquivo de Log Processado (Nível 4) ---
    try:
        os.makedirs(PASTA_ARMAZENAMENTO_PROCESSADO, exist_ok=True)
    except Exception as e:
        print(f"ERRO FATAL (Nível 3): ao criar pasta '{PASTA_ARMAZENAMENTO_PROCESSADO}': {e}")
        return

    timestamp_inicio = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_arquivo = f"{NOME_ARQUIVO_PROCESSADO_PREFIXO}{timestamp_inicio}.csv"
    caminho_arquivo_log_proc = os.path.join(PASTA_ARMAZENAMENTO_PROCESSADO, nome_arquivo)

    try:
        with open(caminho_arquivo_log_proc, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Define o cabeçalho conforme o exemplo log_teste_local*.csv
            writer.writerow(["names", "timestamp", "id_can", "prioridade", "dado"])
        print(f"Nível 3: Log processado iniciado. Salvando em: {caminho_arquivo_log_proc}")
    except IOError as e:
        print(f"ERRO FATAL (Nível 3): ao criar arquivo de log '{caminho_arquivo_log_proc}': {e}")
        caminho_arquivo_log_proc = ""
        return

    # --- Configura e Conecta ao MQTT ---
    client_mqtt = mqtt.Client()
    client_mqtt.on_connect = on_connect
    client_mqtt.on_message = on_message

    try:
        client_mqtt.connect(BROKER_IP, BROKER_PORT, 60)
        client_mqtt.loop_start() # Inicia loop MQTT em thread separada

        print("Nível 3: Aguardando mensagens MQTT...")
        # Mantém a função rodando (se chamada como thread)
        while not parar_collector.is_set():
            time.sleep(0.5)

    except Exception as e:
        print(f"ERRO (Nível 3) de conexão/loop MQTT: {e}")
    finally:
        print("Nível 3 (Collector-Processor): Encerrando...")
        if client_mqtt and client_mqtt.is_connected():
            client_mqtt.loop_stop()
            client_mqtt.disconnect()
        print("Nível 3: Desconectado do MQTT.")
        caminho_arquivo_log_proc = ""

def stop_collector():
    """Sinaliza para a função run_collector parar."""
    global parar_collector
    print("Nível 3 (Collector-Processor): Solicitando parada...")
    parar_collector.set()

# --- Bloco Principal (para rodar standalone) ---
if __name__ == "__main__":
    try:
        # Inicia o processo principal
        run_collector()
    except KeyboardInterrupt:
        # Se pressionar Ctrl+C, solicita a parada limpa
        print("\nNível 3: Ctrl+C recebido. Encerrando...")
        stop_collector()
    except Exception as e:
        print(f"Nível 3: Erro fatal não capturado no main: {e}")
        stop_collector() # Tenta parar mesmo em caso de erro