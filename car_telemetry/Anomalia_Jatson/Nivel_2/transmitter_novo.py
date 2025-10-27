#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
Nivel 2: Transmissor MQTT Otimizado (transmitter_novo.py) - Versão Modificada
========================================================================
- OBJETIVO: Ler arquivos .jsonl (contendo JSONs de mensagens CAN, um por linha)
  da pasta 'dados_brutos', enriquecê-los com prioridade (se possível),
  e publicá-los via MQTT linha por linha, de forma confiável, movendo
  o arquivo processado somente após confirmação do envio de todas as linhas.
- ARQUITETURA:
  1. Conecta ao Broker MQTT com callbacks para conexão e confirmação de publicação.
  2. Usa um contador thread-safe ('mensagens_na_fila_de_publicacao') para
     rastrear mensagens enviadas mas ainda não confirmadas pelo broker (QoS > 0).
  3. Loop Principal:
     a. Encontra o arquivo .jsonl mais antigo na pasta 'dados_brutos'.
     b. VERIFICA SE O ARQUIVO ESTÁ VAZIO. Se sim, remove-o e continua o loop.
     c. Lê o arquivo LINHA POR LINHA.
     d. Para cada linha (que deve ser um JSON válido):
        i.  Tenta adicionar/atualizar a chave 'prioridade' com base no ID CAN.
        ii. Converte o dicionário Python (com prioridade) de volta para JSON.
        iii.Publica a linha como uma MENSAGEM MQTT SEPARADA.
        iv. Incrementa o contador de mensagens em fila.
     e. O callback 'on_publish' (rodando em background pela Paho) decrementa
        o contador quando o broker confirma o recebimento de uma mensagem (ACK).
     f. Após tentar publicar todas as linhas do arquivo, o script ESPERA
        (com timeout) até que o contador chegue a zero.
     g. Se o contador zerar (todas as linhas confirmadas), o arquivo .jsonl
        original é movido para a pasta 'processados'. Se houver timeout,
        o arquivo NÃO é movido.
"""

import paho.mqtt.client as mqtt
import json
import time
import os
import sys
import glob # Para encontrar arquivos com padrões
import threading # Para Lock do contador
import pandas as pd # Para carregar prioridades

# --- CONFIGURAÇÕES ---
# MQTT
BROKER_IP = "192.168.1.4"  # !!! AJUSTE: IP do PC Debian (Box) !!!
BROKER_PORT = 1883
MQTT_TOPIC = "telemetria/dados_brutos"
# QoS: 0 (rápido, pode perder), 1 (garantido, pode duplicar), 2 (garantido, sem duplicar, mais lento)
# Usar QoS 1 é um bom equilíbrio para telemetria se a rede for instável.
QOS_NIVEL = 1

# Pastas (Ajuste os caminhos relativos conforme sua estrutura!)
# Assume que este script roda de uma pasta que contém 'dados_brutos', 'processados', e 'Nivel_1'
PASTA_DADOS_BRUTOS = "dados_brutos/"
PASTA_PROCESSADOS = "processados/"
# Caminho para os CSVs de descrição CAN (usados para definir prioridade)
PASTA_CSV_PRIORIDADE = "../Nivel_1/componentes_csv_linux/"

# Controle de Fluxo
INTERVALO_VERIFICACAO_SEGUNDOS = 0.5 # Tempo de espera entre verificações por novos arquivos
TIMEOUT_CONEXAO_SEGUNDOS = 10
TIMEOUT_CONFIRMACAO_SEGUNDOS = 30.0 # Tempo máximo para esperar confirmação de todas as msgs de um arquivo
# --- FIM DAS CONFIGURAÇÕES ---

# --- Variáveis Globais ---
client_mqtt = None
conectado_mqtt = False
# Contador thread-safe para mensagens publicadas aguardando confirmação (ACK do broker)
mensagens_na_fila_de_publicacao = 0
contador_lock = threading.Lock() # Lock para proteger o acesso ao contador
# Dicionário para guardar o mapa de prioridades {id_int: prioridade_int}
mapa_prioridade = {}

# --- Funções Auxiliares ---

def carregar_mapa_de_prioridade(pasta_csv):
    """
    Lê os arquivos 'CAN Description*.csv' e retorna um dicionário
    mapeando ID CAN (inteiro) para prioridade (inteiro).
    """
    mapa_prio = {}
    print(f"Nível 2: Carregando mapa de prioridades de '{pasta_csv}'...")
    arquivos_lidos = 0
    try:
        if not os.path.isdir(pasta_csv):
            print(f"Nível 2: AVISO: Pasta de prioridades '{pasta_csv}' não encontrada.")
            return {}

        for nome_arquivo in os.listdir(pasta_csv):
            if nome_arquivo.lower().endswith(".csv") and "CAN Description" in nome_arquivo:
                caminho_completo = os.path.join(pasta_csv, nome_arquivo)
                # Define prioridade baseado no nome
                prioridade = 3 # Default baixa
                if "VCU" in nome_arquivo or "BMS" in nome_arquivo: prioridade = 1
                elif "PT" in nome_arquivo or "PAINEL" in nome_arquivo: prioridade = 2

                try:
                    # Lê apenas a coluna de IDs (coluna 1 = índice 1)
                    df = pd.read_csv(caminho_completo, header=None, usecols=[1], skip_blank_lines=True, comment='/')
                    for id_hex_str in df[1].dropna():
                        try:
                            id_int = int(str(id_hex_str), 16)
                            mapa_prio[id_int] = prioridade
                        except (ValueError, TypeError): continue # Ignora ID inválido
                    arquivos_lidos += 1
                except Exception as e_read: print(f"Nível 2: AVISO: Falha ao ler '{nome_arquivo}': {e_read}")

        print(f"Nível 2: Mapa de prioridade carregado com {len(mapa_prio)} IDs de {arquivos_lidos} arquivos.")
        return mapa_prio

    except Exception as e:
        print(f"Nível 2: ERRO ao carregar mapa de prioridades: {e}")
        return {} # Retorna vazio em caso de erro

def encontrar_arquivo_mais_antigo(pasta):
    """Encontra o arquivo .jsonl modificado mais antigamente na pasta."""
    try:
        # Lista todos os arquivos .jsonl na pasta
        arquivos_jsonl = glob.glob(os.path.join(pasta, "*.jsonl"))
        if not arquivos_jsonl:
            return None # Nenhum arquivo encontrado
        # Retorna o arquivo com o menor tempo de modificação (o mais antigo)
        return min(arquivos_jsonl, key=os.path.getmtime)
    except Exception as e:
        print(f"Nível 2: ERRO ao procurar arquivo mais antigo em '{pasta}': {e}")
        return None

# --- Callbacks MQTT ---

def on_connect(client, userdata, flags, rc):
    """Callback - Chamado quando a conexão MQTT é estabelecida."""
    global conectado_mqtt
    if rc == 0:
        print("Nível 2: Conectado ao Broker MQTT com sucesso!")
        conectado_mqtt = True
    else:
        print(f"Nível 2: Falha na conexão MQTT, código: {rc} ({mqtt.error_string(rc)})")
        conectado_mqtt = False
        # Considerar tentar reconectar ou sair se a conexão falhar aqui?

def on_disconnect(client, userdata, rc):
    """Callback - Chamado quando a desconexão MQTT ocorre."""
    global conectado_mqtt
    print(f"Nível 2: Desconectado do Broker MQTT (código: {rc}).")
    conectado_mqtt = False
    # A biblioteca Paho tentará reconectar automaticamente se loop_start() estiver ativo

def on_publish(client, userdata, mid):
    """
    Callback - Chamado quando o Broker confirma o recebimento de uma mensagem
    publicada com QoS > 0 (neste caso, QoS 1).
    'mid' é o ID da mensagem que foi confirmada.
    """
    global mensagens_na_fila_de_publicacao, contador_lock
    # Decrementa o contador de forma segura (thread-safe)
    with contador_lock:
        if mensagens_na_fila_de_publicacao > 0:
            mensagens_na_fila_de_publicacao -= 1
        else:
            # Isso não deveria acontecer, indica um erro de lógica
            print("Nível 2: AVISO: on_publish chamado, mas contador já era zero!")
    # print(f"Nível 2: Mensagem MID {mid} confirmada. Pendentes: {mensagens_na_fila_de_publicacao}") # Log verboso

# --- Funções Principais ---

def conectar_mqtt():
    """Configura e tenta conectar o cliente MQTT."""
    global client_mqtt, conectado_mqtt
    if client_mqtt and conectado_mqtt:
        return True # Já conectado

    client_mqtt = mqtt.Client()
    client_mqtt.on_connect = on_connect
    client_mqtt.on_disconnect = on_disconnect
    client_mqtt.on_publish = on_publish # Define o callback de confirmação

    try:
        print(f"Nível 2: Tentando conectar ao Broker MQTT em {BROKER_IP}:{BROKER_PORT}...")
        client_mqtt.connect(BROKER_IP, BROKER_PORT, keepalive=60)
        client_mqtt.loop_start() # Inicia a thread de rede Paho em background

        # Espera um pouco pela conexão ser estabelecida (ou falhar)
        timeout = time.time() + TIMEOUT_CONEXAO_SEGUNDOS
        while not conectado_mqtt and time.time() < timeout:
            time.sleep(0.1)

        if not conectado_mqtt:
             print("Nível 2: ERRO: Timeout ao conectar ao Broker MQTT.")
             client_mqtt.loop_stop() # Para a thread se a conexão falhou
             return False
        return True

    except Exception as e:
        print(f"Nível 2: ERRO durante conexão MQTT: {e}")
        conectado_mqtt = False
        if client_mqtt: client_mqtt.loop_stop() # Tenta parar a thread
        return False

def loop_monitoramento(mapa_prioridade):
    """Loop principal que monitora a pasta, lê arquivos e publica mensagens."""
    global client_mqtt, conectado_mqtt, mensagens_na_fila_de_publicacao, contador_lock

    while True: # Loop infinito principal (parar com Ctrl+C)
        try:
            # 0. Garante Conexão MQTT
            if not conectado_mqtt:
                print("Nível 2: Desconectado. Tentando reconectar ao MQTT...")
                if not conectar_mqtt():
                    # Se não conseguir reconectar após um tempo, espera antes de tentar de novo
                    print(f"Nível 2: Falha ao reconectar. Aguardando {INTERVALO_VERIFICACAO_SEGUNDOS * 5}s...")
                    time.sleep(INTERVALO_VERIFICACAO_SEGUNDOS * 5)
                    continue # Volta ao início do loop while True

            # 1. Encontra o arquivo .jsonl mais antigo
            arquivo_antigo = encontrar_arquivo_mais_antigo(PASTA_DADOS_BRUTOS)

            # Se não encontrou arquivo, espera e tenta novamente
            if not arquivo_antigo:
                # print("Nível 2: Nenhum arquivo .jsonl encontrado. Aguardando...") # Log verboso
                time.sleep(INTERVALO_VERIFICACAO_SEGUNDOS)
                continue # Volta ao início do loop while True

            nome_base_arquivo = os.path.basename(arquivo_antigo)
            print(f"\nNível 2: Processando arquivo: {nome_base_arquivo}")

            # 2. *** NOVO: Verifica se o arquivo está vazio ***
            try:
                if os.path.getsize(arquivo_antigo) == 0:
                    print(f"Nível 2: AVISO: Arquivo '{nome_base_arquivo}' está vazio. Removendo.")
                    os.remove(arquivo_antigo) # Remove o arquivo vazio
                    continue # Pula para a próxima iteração do loop, procurando outro arquivo
            except OSError as e_size:
                 print(f"Nível 2: ERRO ao verificar tamanho/remover arquivo vazio '{nome_base_arquivo}': {e_size}")
                 time.sleep(INTERVALO_VERIFICACAO_SEGUNDOS) # Espera antes de tentar de novo
                 continue


            # 3. Processa o arquivo linha por linha
            linhas_publicadas_count = 0
            confirmacao_ok = True # Flag para saber se todas as mensagens foram confirmadas

            try:
                with open(arquivo_antigo, 'r', encoding='utf-8') as f:
                    for numero_linha, linha in enumerate(f):
                        linha = linha.strip()
                        if not linha: continue # Pula linhas em branco

                        try:
                            # a. Parseia a linha JSON para dicionário Python
                            pacote_bruto = json.loads(linha)

                            # b. Adiciona/Atualiza prioridade
                            id_can_str = pacote_bruto.get("id_can")
                            prioridade = 4 # Padrão
                            if id_can_str:
                                try:
                                    id_int = int(id_can_str, 16)
                                    prioridade = mapa_prioridade.get(id_int, 4)
                                except ValueError: pass # ID inválido, mantém prioridade 4
                            pacote_bruto['prioridade'] = prioridade

                            # c. Converte de volta para JSON para enviar
                            payload_linha = json.dumps(pacote_bruto)

                            # d. Publica a linha individualmente via MQTT
                            with contador_lock:
                                mensagens_na_fila_de_publicacao += 1
                            # Publica com o QoS definido
                            info = client_mqtt.publish(MQTT_TOPIC, payload_linha, qos=QOS_NIVEL)

                            # Verifica se o publish foi aceito pela biblioteca Paho
                            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                                print(f"Nível 2: ERRO ao enfileirar linha {numero_linha + 1} para MID {info.mid} (rc={info.rc}).")
                                # Se falhou aqui, o on_publish não será chamado, decrementa manualmente
                                with contador_lock:
                                    mensagens_na_fila_de_publicacao -= 1
                            else:
                                linhas_publicadas_count += 1
                                # print(f"  Linha {numero_linha + 1} publicada (MID: {info.mid}). Pendentes: {mensagens_na_fila_de_publicacao}") # Log muito verboso

                            # Pausa mínima para evitar flood (opcional, ajuste se necessário)
                            # time.sleep(0.001)

                        except json.JSONDecodeError:
                            print(f"Nível 2: ERRO: Linha {numero_linha + 1} em '{nome_base_arquivo}' não é JSON válido. Pulando linha: {linha[:100]}...")
                            continue # Pula para a próxima linha do arquivo
                        except Exception as e_pub:
                            print(f"Nível 2: ERRO ao publicar linha {numero_linha + 1} de '{nome_base_arquivo}': {e_pub}")
                            # Se ocorreu erro aqui, a confirmação pode falhar.
                            # Não decrementamos o contador aqui para forçar o timeout mais tarde.

                # --- Fim da leitura do arquivo ---

                # 4. Espera confirmação de TODAS as linhas publicadas (se alguma foi publicada)
                if linhas_publicadas_count > 0:
                    print(f"Nível 2: {linhas_publicadas_count} mensagens de '{nome_base_arquivo}' enfileiradas. Aguardando {TIMEOUT_CONFIRMACAO_SEGUNDOS}s por confirmações...")
                    tempo_inicio_espera = time.time()
                    while True:
                        with contador_lock:
                            msgs_pendentes = mensagens_na_fila_de_publicacao
                        if msgs_pendentes == 0:
                            print(f"Nível 2: Todas as {linhas_publicadas_count} mensagens confirmadas para '{nome_base_arquivo}'.")
                            confirmacao_ok = True
                            break # Sai do loop de espera

                        # Verifica timeout
                        if time.time() - tempo_inicio_espera > TIMEOUT_CONFIRMACAO_SEGUNDOS:
                            print(f"Nível 2: ERRO TIMEOUT! {msgs_pendentes} mensagens de '{nome_base_arquivo}' não confirmadas após {TIMEOUT_CONFIRMACAO_SEGUNDOS}s.")
                            confirmacao_ok = False
                            break # Sai do loop de espera

                        time.sleep(0.1) # Espera um pouco antes de verificar o contador novamente

                else: # Nenhuma linha foi publicada (ex: arquivo só tinha linhas inválidas)
                      print(f"Nível 2: Nenhuma linha válida publicada de '{nome_base_arquivo}'.")
                      confirmacao_ok = True # Considera OK para poder mover/remover


                # 5. Move o arquivo SOMENTE se todas as mensagens foram confirmadas
                if confirmacao_ok:
                    caminho_destino = os.path.join(PASTA_PROCESSADOS, nome_base_arquivo)
                    print(f"Nível 2: Movendo '{nome_base_arquivo}' para '{PASTA_PROCESSADOS}'...")
                    try:
                        os.rename(arquivo_antigo, caminho_destino)
                        print(f"Nível 2: Arquivo '{nome_base_arquivo}' movido com sucesso.")
                    except OSError as e_mov:
                        print(f"Nível 2: ERRO ao mover arquivo '{nome_base_arquivo}': {e_mov}")
                        # O arquivo pode ficar preso aqui se mover falhar. Próximo loop tentará de novo.
                else:
                    print(f"Nível 2: AVISO: Arquivo '{nome_base_arquivo}' NÃO foi movido devido a falha na confirmação MQTT.")
                    # Na próxima iteração, ele tentará processar este mesmo arquivo novamente.

            except IOError as e_io:
                print(f"Nível 2: ERRO de I/O ao ler '{nome_base_arquivo}': {e_io}")
                # Espera antes de tentar de novo o mesmo arquivo
                time.sleep(INTERVALO_VERIFICACAO_SEGUNDOS)
            except Exception as e_proc:
                print(f"Nível 2: ERRO inesperado processando '{nome_base_arquivo}': {e_proc}")
                # Espera antes de tentar de novo o mesmo arquivo
                time.sleep(INTERVALO_VERIFICACAO_SEGUNDOS)


        except KeyboardInterrupt:
            # Captura Ctrl+C durante o loop principal
            print("\nNível 2: Interrupção solicitada dentro do loop.")
            break # Sai do loop while True para ir para o bloco finally
        except Exception as e_main_loop:
            print(f"Nível 2: ERRO inesperado no loop principal: {e_main_loop}")
            time.sleep(5) # Espera 5 segundos antes de continuar

# --- Bloco Principal ---
if __name__ == "__main__":
    print("--- Nível 2: Transmissor MQTT Otimizado ---")

    try:
        # 1. Cria pastas de destino se não existirem
        if not os.path.isdir(PASTA_DADOS_BRUTOS):
            print(f"Nível 2: Criando pasta de dados brutos: {PASTA_DADOS_BRUTOS}")
            os.makedirs(PASTA_DADOS_BRUTOS)
        if not os.path.isdir(PASTA_PROCESSADOS):
            print(f"Nível 2: Criando pasta de processados: {PASTA_PROCESSADOS}")
            os.makedirs(PASTA_PROCESSADOS)

        # 2. Carregar mapa de prioridades
        mapa_prioridade_global = carregar_mapa_de_prioridade(PASTA_CSV_PRIORIDADE)
        # Não consideramos fatal se o mapa estiver vazio, apenas logamos

        # 3. Conectar ao MQTT (com a nova logica robusta)
        if not conectar_mqtt():
            # Se não conectar na primeira vez, não há o que fazer.
            sys.exit(1)

        # 4. Iniciar loop de monitoramento (esta função só termina com Ctrl+C ou erro fatal)
        loop_monitoramento(mapa_prioridade_global)

    except KeyboardInterrupt:
        # Captura Ctrl+C se ocorrer ANTES do loop principal começar
        print("\nNível 2: Ctrl+C recebido durante inicialização. Finalizando...")

    except Exception as e:
        print(f"\nNível 2: ERRO INESPERADO (fora do loop): {e}")

    finally:
        # Bloco de limpeza: sempre será executado ao sair
        print("\nNível 2: Encerrando...")
        if client_mqtt:
            print("Nível 2: Parando a thread de rede MQTT...")
            client_mqtt.loop_stop() # Para a thread (importante antes de desconectar)
            # Verifica se ainda está conectado antes de tentar desconectar
            # A desconexão pode já ter ocorrido devido a erro ou Ctrl+C
            # Usar is_connected() pode não ser 100% seguro após loop_stop().
            # Vamos tentar desconectar de qualquer forma.
            try:
                 if client_mqtt._state != mqtt.mqtt_cs_disconnected:
                      print("Nível 2: Desconectando do Broker MQTT...")
                      client_mqtt.disconnect()
                      print("Nível 2: Desconectado.")
            except Exception as e_disc:
                 print(f"Nível 2: Erro durante a desconexão final: {e_disc}")

        print("--- Nível 2: Finalizado ---")