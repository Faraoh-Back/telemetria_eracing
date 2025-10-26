#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
Nivel 2: Transmissor MQTT (transmitter_otimizado.py)
========================================================================
- Executar com PYTHON 3
- OBJETIVO: Ler arquivos .jsonl da pasta 'dados_brutos',
  enriquecê-los com dados de prioridade, e publicá-los via MQTT
  de forma RÁPIDA e CONFIÁVEL.

- ARQUITETURA DESTA VERSÃO (OTIMIZADA):
  1. Conecta-se ao Broker MQTT usando callbacks (on_connect).
  2. Define um callback de confirmação (on_publish) que será chamado
     pela biblioteca MQTT em background.
  3. Usa um contador thread-safe (mensagens_na_fila_de_publicacao)
     para rastrear mensagens "em voo".
  4. Loop Principal:
     a. Encontra o arquivo .jsonl mais antigo.
     b. Lê todas as linhas e publica o mais rápido possível (assíncrono).
        - Para cada 'publish', incrementa o contador.
     c. O callback 'on_publish' (em outra thread) decrementa o contador
        a cada confirmação (ACK) recebida do broker.
     d. Após enfileirar todas as mensagens do arquivo, o script ESPERA
        até que o contador chegue a zero.
     e. SOMENTE APÓS o contador zerar, o arquivo é movido para 'processados',
        garantindo que nenhum dado foi perdido.
"""

import paho.mqtt.client as mqtt
import json
import time
import os
import sys
import pandas as pd
import threading  # Usado para Event (conexão) e Lock (contador)

# ========================================
# CONFIGURACOES
# ========================================
BROKER_IP = "localhost"
BROKER_PORT = 1883
MQTT_TOPIC = "telemetria/dados_brutos"

# Caminhos (baseado na execucao a partir de 'src/')
PASTA_DADOS_BRUTOS = "../Nivel_1/dados_brutos/"
PASTA_PROCESSADOS = "processados/"
PASTA_CSV_PRIORIDADE = "componentes_csv_linux/"

TEMPO_POLLING_SEGUNDOS = 0.5
# Timeout de segurança para aguardar as confirmações (ACKS)
TIMEOUT_ACK_SEGUNDOS = 30.0

# ========================================
# VARIAVEIS GLOBAIS
# ========================================
client_mqtt = None

# Evento para sinalizar que a conexao MQTT foi estabelecida.
# A thread principal espera (wait) e a thread do MQTT avisa (set).
mqtt_connected_event = threading.Event()

# --- MUDANÇA: Variáveis de Controle Assíncrono ---

# Este contador rastreia quantas mensagens nós publicamos que ainda
# não receberam uma confirmação (ACK) do broker.
mensagens_na_fila_de_publicacao = 0

# Este Lock é CRUCIAL. Ele protege o contador 'mensagens_na_fila_de_publicacao'
# contra "race conditions".
# A thread principal (que faz publish) e a thread de rede do Paho-MQTT (que chama
# on_publish) vão tentar ler/escrever nesse contador ao mesmo tempo.
# O Lock garante que apenas uma thread o acesse por vez.
contador_lock = threading.Lock()

# --- FIM DA MUDANÇA ---

# ========================================
# FUNCOES DO NIVEL 2
# ========================================

def carregar_mapa_de_prioridade(pasta_csv):
    """
    Le os CSVs de prioridade (Python 3)
    (Função mantida do seu script original, sem alterações)
    """
    mapa_prioridade = {}
    print(f"Nivel 2: Carregando descrições CAN de '{pasta_csv}' para definir prioridades...")

    try:
        if not os.path.isdir(pasta_csv):
            raise FileNotFoundError(f"Pasta de CSVs nao encontrada: {pasta_csv}")

        for nome_arquivo in os.listdir(pasta_csv):
            if nome_arquivo.endswith(".csv"):
                caminho_completo = os.path.join(pasta_csv, nome_arquivo)
                
                if "VCU" in nome_arquivo or "BMS" in nome_arquivo: prioridade = 1
                elif "PT" in nome_arquivo or "PAINEL" in nome_arquivo: prioridade = 2
                else: prioridade = 3

                try:
                    df = pd.read_csv(caminho_completo, header=None, usecols=[1], skip_blank_lines=True, comment='/')
                    for id_hex_str in df[1].dropna():
                        try:
                            id_int = int(str(id_hex_str), 16)
                            mapa_prioridade[id_int] = prioridade
                        except (ValueError, TypeError):
                            continue
                except pd.errors.EmptyDataError:
                    print(f"Nivel 2: AVISO: Arquivo CSV vazio ou inválido: {nome_arquivo}")
                except Exception as e:
                    print(f"Nivel 2: ERRO ao ler CSV '{nome_arquivo}': {e}")

        print(f"Nivel 2: Mapa de prioridade carregado com {len(mapa_prioridade)} IDs.")
        return mapa_prioridade
    
    except (FileNotFoundError, IOError, OSError) as e:
        print(f"Nivel 2: ERRO FATAL: {e}. Verifique o caminho da pasta de CSVs.")
        return {}
    except Exception as e:
        print(f"Nivel 2: ERRO inesperado ao carregar prioridades: {e}")
        return {}

# ========================================
# FUNCOES MQTT COM CALLBACK
# ========================================

def on_connect(client, userdata, flags, rc):
    """
    Callback executado (pela thread do Paho-MQTT) quando a conexao
    é estabelecida com o broker.
    """
    global mqtt_connected_event
    if rc == 0:
        print("Nivel 2: Conectado ao Broker MQTT com sucesso.")
        # Libera o evento, avisando a thread principal que ela pode continuar
        mqtt_connected_event.set()
    else:
        print(f"Nivel 2: Falha ao conectar ao Broker, codigo de retorno: {rc}")

# --- NOVA FUNÇÃO ---
def on_publish(client, userdata, mid):
    """
    Callback executado (pela thread do Paho-MQTT) CADA VEZ que o broker
    confirma o recebimento de uma mensagem que publicamos (ACK).
    'mid' é o Message ID da mensagem que foi confirmada.
    
    Esta é a chave da otimização: esta função roda em background,
    permitindo que o loop principal continue publicando mais mensagens.
    """
    global mensagens_na_fila_de_publicacao, contador_lock
    
    # Usamos o Lock para decrementar o contador com segurança
    with contador_lock:
        mensagens_na_fila_de_publicacao -= 1
        
    # (Opcional: descomente a linha abaixo para ver os ACKs chegando em tempo real)
    # print(f"Nivel 2: ACK Recebido. {mensagens_na_fila_de_publicacao} msgs restantes na fila.")
# --- FIM DA NOVA FUNÇÃO ---


def conectar_mqtt():
    """
    Conecta ao broker MQTT de forma assíncrona, define os callbacks
    e inicia o loop de rede do Paho-MQTT.
    """
    global client_mqtt, mqtt_connected_event
    
    # Usamos o Client() padrão.
    client_mqtt = mqtt.Client()
    
    # --- MUDANÇA: Define os callbacks ---
    # Informa à biblioteca quais funções ela deve chamar para cada evento.
    client_mqtt.on_connect = on_connect
    client_mqtt.on_publish = on_publish  # <--- A GRANDE MUDANÇA
    # --- FIM DA MUDANÇA ---
    
    try:
        print(f"Nivel 2: Tentando conectar ao Broker MQTT em {BROKER_IP}:{BROKER_PORT}...")
        # Usa connect_async para não bloquear a thread principal
        client_mqtt.connect_async(BROKER_IP, BROKER_PORT, 60)
        
        # loop_start() cria uma thread dedicada em background para
        # cuidar da rede (enviar/receber, reconectar, chamar callbacks)
        client_mqtt.loop_start()
        
        # Agora, a thread principal espera (por até 10s) pelo sinal
        # que será enviado pelo callback on_connect.
        print("Nivel 2: Aguardando confirmacao de conexao do broker...")
        if not mqtt_connected_event.wait(timeout=10.0):
            # Se o timeout estourar, o on_connect nunca foi chamado.
            raise ConnectionError("Timeout de 10s. Nao foi possivel conectar ao Broker MQTT.")
        
        # Se chegou aqui, o evento foi setado e estamos conectados.
        return True
        
    except Exception as e:
        print("Nivel 2: ERRO FATAL: Nao foi possivel conectar ao Broker MQTT.")
        print(f"  Verifique o IP ({BROKER_IP}) e se o broker esta rodando.")
        print(f"  Erro: {e}")
        client_mqtt.loop_stop()
        return False

# ========================================
# FUNÇÃO PRINCIPAL DE PROCESSAMENTO
# ========================================

def processar_arquivo_jsonl(caminho_arquivo, mapa_prioridade):
    """
    Le um arquivo JSONL, publica todas as mensagens o mais rápido possível,
    aguarda a confirmação (ACK) de todas elas, e SÓ ENTÃO retorna.
    
    Retorna True se tudo foi publicado e confirmado.
    Retorna False se houve um erro (timeout, erro de leitura).
    """
    global client_mqtt, mensagens_na_fila_de_publicacao, contador_lock
    nome_arquivo = os.path.basename(caminho_arquivo)
    print(f"Nivel 2: Processando arquivo: {nome_arquivo}")
    
    total_linhas_enviadas = 0
    try:
        # Abre o arquivo e lê TODAS as linhas para a memória.
        # Isso é mais rápido para arquivos pequenos/médios do que ler linha a linha
        # e nos permite falhar rápido se o arquivo estiver vazio.
        with open(caminho_arquivo, mode='r', encoding='utf-8') as f:
            linhas_para_publicar = f.readlines()

        if not linhas_para_publicar:
            print(f"Nivel 2: AVISO: Arquivo vazio: {nome_arquivo}")
            return True # Sucesso (arquivo vazio pode ser movido)

        print(f"Nivel 2: Enfileirando {len(linhas_para_publicar)} mensagens do arquivo...")

        # Loop de publicação (RÁPIDO)
        for line in linhas_para_publicar:
            if not line.strip(): continue # Ignora linhas em branco
            
            try:
                # 1. Carrega o pacote "burro"
                pacote = json.loads(line)
                
                # 2. ADICIONA A PRIORIDADE
                id_int = int(pacote['id_can'], 16) 
                prioridade = mapa_prioridade.get(id_int, 4)
                pacote['prioridade'] = prioridade
                
                # 3. Serializa para JSON
                payload = json.dumps(pacote)

                # --- MUDANÇA: Lógica de Publicação Assíncrona ---
                
                # 4. Incrementa o contador (com segurança) ANTES de publicar
                with contador_lock:
                    mensagens_na_fila_de_publicacao += 1

                # 5. Publica (MUITO RÁPIDO, não espera confirmação)
                info = client_mqtt.publish(MQTT_TOPIC, payload)
                
                # 6. Checa se o publish foi *aceito* pela biblioteca Paho
                # (Isso não significa que foi enviado, só que foi para o buffer)
                if info.rc != mqtt.MQTT_ERR_SUCCESS:
                     print(f"  -> ERRO ao *enfileirar* mensagem (rc={info.rc}). Buffer pode estar cheio.")
                     # Se falhou aqui, o on_publish NUNCA será chamado para esta msg.
                     # Então, temos que decrementar o contador manualmente.
                     with contador_lock:
                         mensagens_na_fila_de_publicacao -= 1
                else:
                     total_linhas_enviadas += 1
                
                # --- FIM DA MUDANÇA ---
                
            except json.JSONDecodeError as e:
                print(f"Nivel 2: ERRO de JSON (linha mal formatada): {line}. Erro: {e}")
            except Exception as e:
                print(f"Nivel 2: ERRO ao enfileirar pacote: {line}. Erro: {e}")
        
        # Fim do loop de publicação
        print(f"Nivel 2: {total_linhas_enviadas} mensagens enfileiradas. Aguardando confirmações (ACKS) do broker...")
        
        # --- MUDANÇA: Loop de Espera (ROBUSTO) ---
        # Agora, esperamos o contador (que está sendo decrementado em background
        # pelo 'on_publish') chegar a zero.
        
        tempo_inicio_espera = time.time()
        ultimo_print_contador = -1
        
        while True:
            # Lê o contador (com segurança)
            with contador_lock:
                na_fila = mensagens_na_fila_de_publicacao
            
            # 1. Condição de Sucesso
            if na_fila == 0:
                print("Nivel 2: Todas as mensagens foram confirmadas pelo broker!")
                break
            
            # 2. Log de progresso (só printa quando o número muda)
            if na_fila != ultimo_print_contador:
                print(f"  ... {na_fila} mensagens restantes na fila ...")
                ultimo_print_contador = na_fila

            # 3. Condição de Falha (Timeout)
            if time.time() - tempo_inicio_espera > TIMEOUT_ACK_SEGUNDOS:
                print(f"Nivel 2: ERRO FATAL DE TIMEOUT! {na_fila} mensagens nunca foram confirmadas.")
                print(f"  Isso pode ser um problema de rede, broker lento ou QoS > 0.")
                return False # Sinaliza para NÃO mover o arquivo
            
            # Espera curta para não sobrecarregar a CPU
            time.sleep(0.05) 
            
        # --- FIM DA MUDANÇA ---

        print(f"Nivel 2: Arquivo {nome_arquivo} processado. {total_linhas_enviadas} mensagens enviadas e confirmadas.")
        return True # Sucesso, o arquivo pode ser movido

    except Exception as e:
        print(f"Nivel 2: ERRO FATAL ao ler {nome_arquivo}: {e}")
        return False # Nao move o arquivo se deu erro de leitura

# ========================================
# LOOP DE MONITORAMENTO (Thread Principal)
# ========================================
def loop_monitoramento(mapa_prioridade):
    """
    Loop principal que verifica a pasta de dados brutos.
    """
    print("Nivel 2: Iniciando monitoramento da pasta: %s" % PASTA_DADOS_BRUTOS)
    while True:
        try:
            # 1. Checa se a conexao MQTT ainda esta ativa (a thread do paho cuida disso)
            if not client_mqtt.is_connected():
                print("Nivel 2: AVISO: Conexao MQTT perdida! Tentando reconectar...")
                mqtt_connected_event.clear() # Reseta o evento para podermos esperar por ele
                try:
                    client_mqtt.reconnect()
                    
                    # Espera a reconexão ser confirmada pelo on_connect
                    if not mqtt_connected_event.wait(timeout=5.0):
                        print("Nivel 2: Falha ao reconectar. Tentando novamente em breve...")
                        time.sleep(TEMPO_POLLING_SEGUNDOS)
                        continue # Pula esta iteracao
                        
                except Exception as e:
                    print(f"Nivel 2: Erro na reconexao: {e}")
                    time.sleep(TEMPO_POLLING_SEGUNDOS)
                    continue

            # 2. Logica de encontrar arquivos (igual ao seu script)
            # Lista arquivos, filtra .jsonl, ordena por data de modificação (mais antigo primeiro)
            arquivos = sorted(
                [f for f in os.listdir(PASTA_DADOS_BRUTOS) if f.endswith('.jsonl')],
                key=lambda f: os.path.getmtime(os.path.join(PASTA_DADOS_BRUTOS, f))
            )
            
            # Se não há arquivos, apenas dorme e tenta de novo
            if not arquivos:
                time.sleep(TEMPO_POLLING_SEGUNDOS)
                continue
            
            # Pega o arquivo mais antigo da lista
            arquivo_para_processar = arquivos[0]
            caminho_completo = os.path.join(PASTA_DADOS_BRUTOS, arquivo_para_processar)
            
            # --- MUDANÇA: Lógica de Mover Arquivo ---
            
            # 3. Chama a função de processamento
            # Esta função agora é bloqueante: ela só retorna
            # (True ou False) DEPOIS que todas as msgs são confirmadas.
            sucesso_processamento = processar_arquivo_jsonl(caminho_completo, mapa_prioridade)
            
            # 4. SÓ move o arquivo se a função retornar True (sucesso)
            if sucesso_processamento:
                try:
                    nome_arquivo = os.path.basename(caminho_completo)
                    caminho_destino = os.path.join(PASTA_PROCESSADOS, nome_arquivo)
                    os.rename(caminho_completo, caminho_destino)
                    print(f"Nivel 2: Arquivo movido para {PASTA_PROCESSADOS}")
                except Exception as e:
                    print(f"Nivel 2: ERRO ao mover arquivo {nome_arquivo}: {e}")
            else:
                # Se deu erro (ex: Timeout de ACK), o arquivo NÃO é movido.
                print(f"Nivel 2: ERRO no processamento de {arquivo_para_processar}. O arquivo NÃO será movido.")
                print("  O script tentará processá-lo novamente no próximo ciclo após 5s.")
                time.sleep(5) # Pausa para não ficar em loop de erro
            
            # --- FIM DA MUDANÇA ---
            
        except KeyboardInterrupt:
            raise # Repassa o Ctrl+C para o bloco 'finally'
        except Exception as e:
            print(f"Nivel 2: ERRO grave no loop de monitoramento: {e}")
            time.sleep(10) # Pausa longa em caso de erro inesperado

# ========================================
# BLOCO PRINCIPAL (Início do Script)
# ========================================
if __name__ == "__main__":
    print("="*60)
    print("Nivel 2: Transmissor JSONL -> MQTT (VERSÃO OTIMIZADA)")
    print("EXECUTANDO COM PYTHON 3")
    print("="*60)
    
    try:
        # 1. Criar pasta de processados se nao existir
        if not os.path.exists(PASTA_PROCESSADOS):
            print(f"Nivel 2: Criando pasta {PASTA_PROCESSADOS}")
            os.makedirs(PASTA_PROCESSADOS)
            
        # 2. Carregar mapa de prioridades
        mapa_prioridade_global = carregar_mapa_de_prioridade(PASTA_CSV_PRIORIDADE)
        if not mapa_prioridade_global:
            # Não é fatal, podemos continuar, mas os pacotes
            # terão prioridade padrão (4)
            print("Nivel 2: AVISO: Mapa de prioridade vazio. Usando prioridade 4 para tudo.")
        
        # 3. Conectar ao MQTT (com a nova logica robusta)
        if not conectar_mqtt():
            # Se não conectar na primeira vez, não há o que fazer.
            sys.exit(1)
            
        # 4. Iniciar loop de monitoramento (esta função só termina com Ctrl+C)
        loop_monitoramento(mapa_prioridade_global)
        
    except KeyboardInterrupt:
        print("\nNivel 2: Ctrl+C recebido. Finalizando...")
        
    except Exception as e:
        print(f"\nNivel 2: ERRO INESPERADO (fora do loop): {e}")
        
    finally:
        # Bloco de limpeza: sempre será executado ao sair
        print("\nNivel 2: Encerrando...")
        if client_mqtt:
            print("Nivel 2: Parando a thread de rede MQTT...")
            client_mqtt.loop_stop() # Para a thread (importante)
            if client_mqtt.is_connected():
                print("Nivel 2: Desconectando do Broker MQTT...")
                client_mqtt.disconnect()
                print("Nivel 2: Desconectado.")
            
        print("Nivel 2: Finalizado.")
        print("="*60)