import csv
import random
import os

# --- Configurações ---
# Caminho para a pasta contendo os arquivos CAN Description *.csv
# Ajuste conforme a localização de onde você executa este script
PASTA_CSV_DESCRICOES = "componentes_csv_linux/" # Exemplo se rodar da raiz

# Nome do arquivo de saída para as mensagens de teste
ARQUIVO_SAIDA = "sample_can_messages_cansend.log"

# Quantidade de mensagens a gerar
NUM_MENSAGENS = 10000
# --- Fim Configurações ---

def extrair_ids_validos(pasta_csv):
    """Lê todos os CSVs na pasta e extrai os IDs CAN únicos da coluna B (índice 1)."""
    ids_validos = set()
    print(f"Lendo arquivos CSV em: {pasta_csv}")
    try:
        if not os.path.isdir(pasta_csv):
            raise FileNotFoundError(f"Pasta não encontrada: {pasta_csv}")

        for nome_arquivo in os.listdir(pasta_csv):
            if nome_arquivo.lower().endswith(".csv") and "CAN Description" in nome_arquivo:
                caminho_completo = os.path.join(pasta_csv, nome_arquivo)
                # print(f"  Processando: {nome_arquivo}") # Debug
                try:
                    with open(caminho_completo, mode='r', newline='', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        for i, linha in enumerate(reader):
                            # Pula linhas que não têm pelo menos 2 colunas ou cujo ID não começa com 0x
                            if len(linha) < 2 or not linha[1].strip().lower().startswith('0x'):
                                continue
                            try:
                                id_hex = linha[1].strip()
                                # Validação: Tenta converter para int
                                int(id_hex, 16)
                                ids_validos.add(id_hex)
                            except (ValueError):
                                continue # Ignora ID inválido
                except Exception as e:
                    print(f"    Erro ao ler {nome_arquivo}: {e}")

    except FileNotFoundError as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"ERRO inesperado ao ler CSVs: {e}")

    print(f"Total de IDs CAN únicos encontrados: {len(ids_validos)}")
    # Retorna a lista de IDs já sem o '0x'
    return [id_str.replace('0x', '').replace('0X', '') for id_str in ids_validos]

def gerar_bytes_aleatorios(num_bytes=8):
    """Gera uma lista de 'num_bytes' inteiros aleatórios entre 0 e 255."""
    return [random.randint(0, 255) for _ in range(num_bytes)]

# --- Principal ---
if __name__ == "__main__":
    # Extrai os IDs válidos já sem o prefixo '0x'
    lista_ids_sem_prefixo = extrair_ids_validos(PASTA_CSV_DESCRICOES)

    if not lista_ids_sem_prefixo:
        print("Nenhum ID CAN válido encontrado nos arquivos CSV. Não é possível gerar mensagens.")
    else:
        print(f"Gerando {NUM_MENSAGENS} mensagens de teste no formato cansend...")
        mensagens_geradas = []
        for _ in range(NUM_MENSAGENS):
            # Escolhe um ID aleatório (já sem '0x')
            id_aleatorio_sem_prefixo = random.choice(lista_ids_sem_prefixo)
            # Gera 8 bytes aleatórios
            dados_aleatorios = gerar_bytes_aleatorios(8)
            # Formata os bytes como strings hexadecimais de 2 dígitos e junta TUDO SEM ESPAÇOS
            dados_hex_concatenados = "".join([f"{byte:02X}" for byte in dados_aleatorios])
            # Monta a linha da mensagem no formato ID#DADOS
            linha_mensagem = f"{id_aleatorio_sem_prefixo}#{dados_hex_concatenados}"
            mensagens_geradas.append(linha_mensagem)

        # Salva as mensagens no arquivo de saída
        try:
            with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f_out:
                for msg in mensagens_geradas:
                    f_out.write(msg + "\n")
            print(f"Mensagens salvas com sucesso em: {ARQUIVO_SAIDA}")

            # Mostra as primeiras 5 mensagens como exemplo
            print("\nExemplo das primeiras 5 mensagens geradas:")
            for i in range(min(5, len(mensagens_geradas))):
                print(mensagens_geradas[i])

        except Exception as e:
            print(f"Erro ao salvar o arquivo {ARQUIVO_SAIDA}: {e}")