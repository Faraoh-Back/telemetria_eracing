import os
import pandas as pd
import time

def carregar_mapa_de_prioridade(pasta_csv):
    """
    Lê todos os arquivos CSV na pasta especificada e cria um dicionário
    mapeando cada ID CAN a uma prioridade.

    A prioridade é definida de forma simples:
    - Prioridade 1 (Alta): VCU, BMS
    - Prioridade 2 (Média): PT (Powertrain), Painel
    - Prioridade 3 (Baixa): Outros (ACD, etc.)
    """
    mapa_prioridade = {}
    print(f"Nível 1: Carregando descrições CAN de '{pasta_csv}' para definir prioridades...")

    try:
        if not os.path.isdir(pasta_csv):
            raise FileNotFoundError

        # Percorre todos os arquivos CSV na pasta
        for nome_arquivo in os.listdir(pasta_csv):

            # Somente processa arquivos .csv
            if nome_arquivo.endswith(".csv"):
                caminho_completo = os.path.join(pasta_csv, nome_arquivo)
                
                # Define a prioridade com base no nome do arquivo
                if "VCU" in nome_arquivo or "BMS" in nome_arquivo:
                    prioridade = 1
                
                elif "PT" in nome_arquivo or "PAINEL" in nome_arquivo:
                    prioridade = 2

                else:
                    prioridade = 3

                try:
                    # Lê o arquivo CSV usando pandas.
                    # header=None: Não há linha de cabeçalho nos CSVs de exemplo.
                    # usecols=[1]: Lê apenas a segunda coluna (índice 1), que contém os IDs.
                    # skip_blank_lines=True: Ignora linhas vazias.
                    # comment='/': Ignora linhas que começam com / (se houver comentários).
                    df = pd.read_csv(caminho_completo, header=None, usecols=[1], skip_blank_lines=True, comment='/')

                    # Itera sobre cada ID lido da coluna (dropna remove valores ausentes, se houver).
                    for id_hex_str in df[1].dropna():
                        try:
                            # Converte a string hexadecimal (ex: '0x1A3') para um inteiro.
                            id_int = int(str(id_hex_str), 16)
                            # Armazena no dicionário: {ID_inteiro: prioridade_inteiro}
                            mapa_prioridade[id_int] = prioridade
                        except (ValueError, TypeError):
                            # Ignora a linha se o valor na coluna não for um hexadecimal válido.
                            # print(f"AVISO (Nível 1): Ignorando ID inválido '{id_hex_str}' no arquivo {nome_arquivo}")
                            continue
                except pd.errors.EmptyDataError:
                    print(f"AVISO (Nível 1): Arquivo CSV vazio ou inválido: {nome_arquivo}")
                except Exception as e:
                    print(f"ERRO (Nível 1) ao ler CSV '{nome_arquivo}': {e}")


        print(f"Nível 1 (Former): Mapa de prioridade carregado com {len(mapa_prioridade)} IDs.")
        return mapa_prioridade
    
    except FileNotFoundError as e:
        # Erro se a pasta principal não for encontrada.
        print(f"ERRO FATAL (Nível 1): {e}. Verifique o caminho da pasta de CSVs.")
        # Retorna um mapa vazio para evitar que o Nível 2 falhe completamente,
        # embora as prioridades ficarão erradas (todas serão 4).
        return {}
    except Exception as e:
        print(f"ERRO inesperado (Nível 1) ao carregar prioridades: {e}")
        return {}

def formatar_pacote_can(can_id, data, timestamp, mapa_prioridade):
    """
    Recebe um ID CAN (int), dados (lista/tupla de int), timestamp (float)
    e o mapa de prioridades, e retorna um dicionário com o pacote de dados
    estruturado para envio via MQTT.
    Esta é a função central do Nível 1.
    """
    # Verifica se os dados recebidos são válidos (precaução)
    if can_id is None or data is None or timestamp is None:
        print("AVISO (Nível 1): Dados inválidos recebidos para formatação (None).")
        return None

    # Busca a prioridade no mapa usando o ID inteiro.
    # Se o ID não for encontrado no mapa, usa a prioridade padrão 4 (a mais baixa).
    prioridade = mapa_prioridade.get(can_id, 4)

    # Monta o pacote de dados (dicionário Python)
    pacote = {
        # Formata o ID inteiro de volta para string hexadecimal (0x...) para legibilidade no JSON.
        # ':03X' garante pelo menos 3 dígitos hexadecimais com zero à esquerda, se necessário. Ajuste se precisar de mais.
        "id_can": f"0x{can_id:03X}",
        # Garante que os dados sejam uma LISTA de inteiros (necessário para json.dumps).
        # A biblioteca Ixxat pode retornar tupla, então convertemos.
        "dados": list(data),
        # Usa o timestamp fornecido pelo Nível 2.
        "prioridade": prioridade,
        "timestamp": timestamp
    }

    return pacote