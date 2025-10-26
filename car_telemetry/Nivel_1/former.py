import os
import pandas as pd

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

                df = pd.read_csv(caminho_completo, header=None, usecols=[1], skip_blank_lines=True, comment='/')
                
                # Interando sobre os IDs CAN na segunda coluna
                for id_hex_str in df[1].dropna():
                    try:
                        # Converte o ID de hexadecimal => string => inteiro (base 10) 
                        id_int = int(str(id_hex_str), 16)
                        mapa_prioridade[id_int] = prioridade
                    except (ValueError, TypeError):
                        continue
        print(f"Nível 1: Mapa de prioridade carregado com {len(mapa_prioridade)} IDs.")
        return mapa_prioridade
    except FileNotFoundError:
        print(f"ERRO (Nível 1): A pasta '{pasta_csv}' não foi encontrada. O mapa de prioridades estará vazio.")
        return {} 

def formatar_pacote_can(msg, mapa_prioridade):
    """
    Recebe uma mensagem CAN bruta e o mapa de prioridades,
    e retorna um dicionário com o pacote de dados estruturado.
    Esta é a função central do Nível 1.
    """
    if msg is None:
        return None

    # Busca a prioridade no mapa. Se não encontrar, usa 4 (a mais baixa).
    prioridade = mapa_prioridade.get(msg.arbitration_id, 4)

    # Monta o pacote de dados estruturado
    pacote = {
        "id_can": f"0x{msg.arbitration_id:03X}",
        "dados": list(msg.data),
        "prioridade": prioridade,
        "timestamp": msg.timestamp
    }
    
    return pacote