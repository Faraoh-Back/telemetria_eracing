# Arquivo: Nivel_3/collector.py (Versão 2 - COM OFFSET para BMS e LV_BMS)

import paho.mqtt.client as mqtt
import json
import os
import csv
from datetime import datetime
import time
import threading
import pandas as pd

# --- CONFIGURAÇÕES ---
BROKER_IP = "localhost"
BROKER_PORT = 1883
MQTT_TOPIC = "telemetria/dados_brutos"

PASTA_CSV_COMPONENTES = "componentes_csv_linux/"
PASTA_ARMAZENAMENTO_PROCESSADO = "../Nivel_4/processados/"
NOME_ARQUIVO_PROCESSADO_PREFIXO = "log_processado_"

# DEBUG: Ative para ver informações detalhadas
DEBUG_MODE = True  # Mude para False para produção

# --- Variáveis Globais ---
caminho_arquivo_log_proc = ""
client_mqtt = None
parar_collector = threading.Event()
planilhas_can = {}

# --- Funções de Processamento CAN (COM OFFSET) ---

def carregar_planilhas_can(pasta_csv):
    """Carrega os CSVs de descrição CAN."""
    global planilhas_can
    print(f"Nível 3: Carregando descrições CAN de: {pasta_csv}")
    arquivos_carregados = 0
    
    try:
        if not os.path.isdir(pasta_csv):
            raise FileNotFoundError(f"Pasta não encontrada: {pasta_csv}")

        for nome_arquivo in os.listdir(pasta_csv):
            if nome_arquivo.lower().endswith(".csv") and "CAN Description" in nome_arquivo:
                caminho_completo = os.path.join(pasta_csv, nome_arquivo)
                try:
                    df = pd.read_csv(caminho_completo, header=None, skip_blank_lines=True)
                    chave_planilha = nome_arquivo.split(' - ')[-1].split('.')[0]
                    planilhas_can[chave_planilha] = df
                    print(f"  ✓ Carregado: '{nome_arquivo}' como '{chave_planilha}'")
                    arquivos_carregados += 1
                except Exception as e:
                    print(f"  ✗ Erro ao ler '{nome_arquivo}': {e}")

        if arquivos_carregados == 0:
            print("AVISO: Nenhuma planilha CAN carregada!")
        else:
            print(f"Total: {arquivos_carregados} planilhas carregadas.\n")

    except Exception as e:
        print(f"ERRO FATAL ao carregar planilhas: {e}")
        exit(1)


def extrair_valor_can(data_bytes, posicao_str, tipo='int'):
    """
    Extrai valor dos bytes CAN baseado na posição.
    Corrigido para suportar byte(X), byte(X-Y), bit(X), bit(X-Y)
    """
    try:
        posicao_str = posicao_str.strip()
        
        # Caso 1: byte(X) - extrai 1 byte
        if 'byte(' in posicao_str and '-' not in posicao_str:
            byte_num = int(posicao_str.replace('byte(', '').replace(')', ''))
            if byte_num >= len(data_bytes):
                return None
            return data_bytes[byte_num]
        
        # Caso 2: byte(X-Y) - extrai múltiplos bytes (Little Endian)
        elif 'byte(' in posicao_str and '-' in posicao_str:
            range_str = posicao_str.replace('byte(', '').replace(')', '')
            start, end = map(int, range_str.split('-'))
            if end >= len(data_bytes):
                return None
            # Little Endian
            valor = int.from_bytes(data_bytes[start:end+1], byteorder='little')
            return valor
        
        # Caso 3: bit(X) - extrai 1 bit
        elif 'bit(' in posicao_str and '-' not in posicao_str:
            bit_num = int(posicao_str.replace('bit(', '').replace(')', ''))
            byte_idx = bit_num // 8
            bit_idx = bit_num % 8
            if byte_idx >= len(data_bytes):
                return None
            return (data_bytes[byte_idx] >> bit_idx) & 1
        
        # Caso 4: bit(X-Y) - extrai range de bits
        elif 'bit(' in posicao_str and '-' in posicao_str:
            range_str = posicao_str.replace('bit(', '').replace(')', '')
            start_bit, end_bit = map(int, range_str.split('-'))
            
            # Calcula quantos bytes precisamos
            start_byte = start_bit // 8
            end_byte = end_bit // 8
            
            if end_byte >= len(data_bytes):
                return None
            
            # Converte bytes para inteiro
            num_bytes = end_byte - start_byte + 1
            valor_total = int.from_bytes(data_bytes[start_byte:end_byte+1], byteorder='little')
            
            # Aplica máscara
            num_bits = end_bit - start_bit + 1
            mascara = (1 << num_bits) - 1
            bit_offset = start_bit % 8
            valor = (valor_total >> bit_offset) & mascara
            
            return valor
        
        return None
        
    except Exception as e:
        print(f"Erro em extrair_valor_can: {e} (pos='{posicao_str}')")
        return None


def identificar_tipo_bms(nome_planilha):
    """
    Identifica se a planilha é BMS ou LV_BMS para aplicar offset.
    Retorna: 'BMS', 'LV_BMS', ou None
    """
    nome_upper = nome_planilha.upper()
    if 'LV_BMS' in nome_upper or 'LV-BMS' in nome_upper or 'LVBMS' in nome_upper:
        return 'LV_BMS'
    elif 'BMS' in nome_upper and 'LV' not in nome_upper:
        return 'BMS'
    return None


def processar_mensagem_can(id_int, data_bytes):
    """
    Processa mensagem CAN e retorna lista de sinais decodificados.
    VERSÃO 2: COM SUPORTE A OFFSET para BMS e LV_BMS
    
    Fórmula: valor_final = (valor_bruto * multiplier) + offset
    """
    global planilhas_can
    sinais_decodificados = []
    
    id_hex_str = f"0x{id_int:08X}"  # Formato completo
    id_hex_str_short = f"0x{id_int:X}"  # Formato curto
    
    for nome_planilha, df in planilhas_can.items():
        try:
            # Identifica se é BMS ou LV_BMS
            tipo_bms = identificar_tipo_bms(nome_planilha)
            
            # Busca o ID na coluna 1 (índice 1)
            df[1] = df[1].astype(str).str.strip().str.upper()
            
            # Tenta encontrar o ID em diferentes formatos
            mascara = df[1].isin([id_hex_str.upper(), id_hex_str_short.upper()])
            linhas_id = df[mascara]
            
            if not linhas_id.empty:
                if DEBUG_MODE:
                    print(f"  → ID {id_hex_str_short} encontrado em {nome_planilha}")
                    if tipo_bms:
                        print(f"  → Tipo detectado: {tipo_bms} (OFFSET ATIVO)")
                
                # Pega a PRIMEIRA linha que contém o ID (linha de cabeçalho do bloco)
                idx_id = linhas_id.index[0]
                linha_cabecalho = df.iloc[idx_id]
                
                # Extrai o tamanho em bytes da coluna 2 (ex: "8B" = 8 bytes)
                tamanho_str = str(linha_cabecalho[2]).strip() if pd.notna(linha_cabecalho[2]) else "0B"
                
                # Remove o 'B' e converte para inteiro
                try:
                    num_bytes = int(tamanho_str.replace('B', '').replace('b', ''))
                except:
                    num_bytes = 8  # Default se não conseguir parsear
                
                if DEBUG_MODE:
                    print(f"  → Tamanho da mensagem: {num_bytes} bytes")
                    print(f"  → Bytes recebidos: {len(data_bytes)} bytes")
                
                # Agora processa as linhas de SINAIS que vêm depois do cabeçalho
                idx_inicio = idx_id + 1
                
                # Itera pelas linhas seguintes
                for i in range(idx_inicio, min(idx_inicio + 50, len(df))):  # Limita busca
                    try:
                        linha = df.iloc[i]
                        
                        # Para se encontrar linha vazia completa
                        if linha.isna().all():
                            break
                        
                        # Para se encontrar próximo bloco (novo ID)
                        if pd.notna(linha[1]) and str(linha[1]).strip().upper().startswith('0X'):
                            break
                        
                        # Verifica se é linha de SINAL:
                        # - Coluna 0 vazia (começa com vírgula no CSV)
                        # - Coluna 1 tem o NOME do sinal
                        col_0 = str(linha[0]).strip() if pd.notna(linha[0]) else ''
                        col_1 = str(linha[1]).strip() if pd.notna(linha[1]) else ''
                        
                        # É linha de sinal se col_0 está vazia e col_1 tem conteúdo
                        if col_0 == '' and col_1 != '':
                            nome_sinal = col_1
                            
                            # Pula linha de cabeçalho interno (se existir)
                            if nome_sinal.lower() in ['type', 'min', 'max', 'unit', '']:
                                continue
                            
                            # Extrai informações do sinal
                            posicao_str = str(linha[2]).strip() if pd.notna(linha[2]) else None
                            tipo = str(linha[3]).strip().lower() if pd.notna(linha[3]) else 'int'
                            
                            # ====== NOVA LÓGICA: MULTIPLIER E OFFSET ======
                            # Multiplier está na coluna 6
                            try:
                                multiplicador = float(linha[6]) if pd.notna(linha[6]) and str(linha[6]).strip() != '' else 1.0
                            except (ValueError, TypeError):
                                multiplicador = 1.0
                            
                            # OFFSET está na coluna 7 (NOVO!)
                            try:
                                offset = float(linha[7]) if pd.notna(linha[7]) and str(linha[7]).strip() != '' else 0.0
                            except (ValueError, TypeError):
                                offset = 0.0
                            
                            # Unit está na coluna 8
                            try:
                                unit = str(linha[8]).strip() if pd.notna(linha[8]) and str(linha[8]).strip() not in ['nan', ''] else ''
                            except:
                                unit = ''
                            # ============================================
                            
                            if DEBUG_MODE:
                                if offset != 0.0:
                                    print(f"    🔍 {nome_sinal}: pos={posicao_str}, tipo={tipo}, mult={multiplicador}, offset={offset}, unit={unit}")
                                else:
                                    print(f"    🔍 {nome_sinal}: pos={posicao_str}, tipo={tipo}, mult={multiplicador}, unit={unit}")
                            
                            # Extrai valor dos bytes
                            valor_bruto = extrair_valor_can(data_bytes, posicao_str, tipo)
                            
                            if valor_bruto is not None:
                                # ====== NOVA FÓRMULA COM OFFSET ======
                                # Para BMS/LV_BMS: valor_final = (valor_bruto * multiplier) + offset
                                # Para outros: valor_final = valor_bruto / multiplier (lógica antiga)
                                
                                if tipo_bms and (offset != 0.0 or multiplicador != 1.0):
                                    # Lógica BMS/LV_BMS: multiplica primeiro, depois soma offset
                                    valor_final = (valor_bruto * multiplicador) + offset
                                    
                                    if DEBUG_MODE:
                                        print(f"    📐 Cálculo BMS: ({valor_bruto} * {multiplicador}) + {offset} = {valor_final}")
                                else:
                                    # Lógica antiga (outros componentes): divide pelo multiplicador
                                    if multiplicador != 1.0 and multiplicador != 0:
                                        valor_final = valor_bruto / multiplicador
                                    else:
                                        valor_final = valor_bruto
                                # ======================================
                                
                                # Formata saída baseado no tipo
                                if tipo == 'bool':
                                    valor_str = 'TRUE' if valor_final else 'FALSE'
                                elif tipo == 'float' or multiplicador != 1.0 or offset != 0.0:
                                    valor_str = f"{valor_final:.2f}"
                                else:
                                    valor_str = str(int(valor_final))
                                
                                # Adiciona unidade se existir
                                if unit:
                                    valor_str = f"{valor_str} {unit}"
                                
                                sinais_decodificados.append((nome_sinal, valor_str))
                                
                                if DEBUG_MODE:
                                    print(f"    ✅ {nome_sinal} = {valor_str} (bruto={valor_bruto})")
                            else:
                                if DEBUG_MODE:
                                    print(f"    ❌ Falha ao extrair {nome_sinal}")
                                
                    except Exception as e:
                        if DEBUG_MODE:
                            print(f"  ⚠️ Erro na linha {i}: {e}")
                        continue
                
                # Se encontrou sinais, retorna
                if sinais_decodificados:
                    return sinais_decodificados
                else:
                    if DEBUG_MODE:
                        print(f"  ⚠️ Nenhum sinal decodificado para este ID")
                
        except Exception as e:
            print(f"❌ Erro ao processar planilha {nome_planilha}: {e}")
            if DEBUG_MODE:
                import traceback
                traceback.print_exc()
            continue
    
    return sinais_decodificados


# --- Callbacks MQTT ---

def on_connect(client, userdata, flags, rc):
    """Callback de conexão MQTT."""
    if rc == 0:
        print("✓ Conectado ao Broker MQTT!")
        try:
            client.subscribe(MQTT_TOPIC)
            print(f"✓ Inscrito no tópico: {MQTT_TOPIC}\n")
        except Exception as e:
            print(f"✗ Erro ao inscrever: {e}")
    else:
        print(f"✗ Falha na conexão MQTT, código: {rc}")


def on_message(client, userdata, msg):
    """Callback para mensagens MQTT recebidas."""
    global caminho_arquivo_log_proc
    
    if not caminho_arquivo_log_proc:
        return
    
    try:
        payload_str = msg.payload.decode("utf-8")
        pacote_bruto = json.loads(payload_str)
        
        id_can_str = pacote_bruto.get("id_can")
        dados_lista = pacote_bruto.get("dados")
        timestamp = pacote_bruto.get("timestamp", time.time())
        prioridade = pacote_bruto.get("prioridade", 3)
        
        if id_can_str is None or dados_lista is None:
            print(f"⚠ Mensagem inválida: {payload_str}")
            return
        
        # Converte para inteiro e bytes
        id_int = int(id_can_str, 16)
        data_bytes = bytes(dados_lista)
        
        if DEBUG_MODE:
            print(f"\n📨 Recebido ID={id_can_str}")
            print(f"   Bytes: {' '.join([f'{b:02X}' for b in data_bytes])}")
            print(f"   Decimal: {dados_lista}")
        else:
            print(f"\n📨 ID={id_can_str}, {len(data_bytes)} bytes")
        
        # Processa a mensagem
        lista_sinais = processar_mensagem_can(id_int, data_bytes)
        
        if lista_sinais:
            with open(caminho_arquivo_log_proc, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for nome_sinal, valor_str in lista_sinais:
                    linha = [nome_sinal, timestamp, id_can_str, prioridade, valor_str]
                    writer.writerow(linha)
            
            print(f"✓ {len(lista_sinais)} sinais salvos")
        else:
            print(f"⚠ Nenhum sinal decodificado para ID {id_can_str}")
            
    except json.JSONDecodeError:
        print(f"✗ JSON inválido: {msg.payload.decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"✗ Erro em on_message: {e}")


# --- Função Principal ---

def run_collector():
    """Inicia o coletor e processador."""
    global caminho_arquivo_log_proc, client_mqtt, parar_collector
    
    print("="*60)
    print("NÍVEL 3 - COLLECTOR & PROCESSOR v2 (COM OFFSET)")
    print("="*60 + "\n")
    
    parar_collector.clear()
    
    # Carrega descrições CAN
    carregar_planilhas_can(PASTA_CSV_COMPONENTES)
    if not planilhas_can:
        print("ERRO: Não foi possível carregar planilhas CAN!")
        return
    
    # Cria pasta de saída
    try:
        os.makedirs(PASTA_ARMAZENAMENTO_PROCESSADO, exist_ok=True)
    except Exception as e:
        print(f"ERRO ao criar pasta: {e}")
        return
    
    # Cria arquivo de log
    timestamp_inicio = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_arquivo = f"{NOME_ARQUIVO_PROCESSADO_PREFIXO}{timestamp_inicio}.csv"
    caminho_arquivo_log_proc = os.path.join(PASTA_ARMAZENAMENTO_PROCESSADO, nome_arquivo)
    
    try:
        with open(caminho_arquivo_log_proc, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["names", "timestamp", "id_can", "prioridade", "dado"])
        print(f"✓ Arquivo criado: {caminho_arquivo_log_proc}\n")
    except IOError as e:
        print(f"ERRO ao criar arquivo: {e}")
        return
    
    # Conecta ao MQTT
    client_mqtt = mqtt.Client()
    client_mqtt.on_connect = on_connect
    client_mqtt.on_message = on_message
    
    try:
        client_mqtt.connect(BROKER_IP, BROKER_PORT, 60)
        client_mqtt.loop_start()
        
        print("Aguardando mensagens MQTT...\n")
        print("Pressione Ctrl+C para parar.\n")
        
        while not parar_collector.is_set():
            time.sleep(0.001)
            
    except Exception as e:
        print(f"ERRO MQTT: {e}")
    finally:
        print("\n" + "="*60)
        print("Encerrando Nível 3...")
        print("="*60)
        if client_mqtt and client_mqtt.is_connected():
            client_mqtt.loop_stop()
            client_mqtt.disconnect()
        print("✓ Desconectado")


def stop_collector():
    """Para o coletor."""
    global parar_collector
    print("Solicitando parada...")
    parar_collector.set()


# --- Execução ---
if __name__ == "__main__":
    try:
        run_collector()
    except KeyboardInterrupt:
        print("\n\nCtrl+C recebido!")
        stop_collector()
    except Exception as e:
        print(f"\nERRO FATAL: {e}")
        stop_collector()