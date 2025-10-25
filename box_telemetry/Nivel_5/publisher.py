"""
Nível 5: Leitor de CSV e Publisher ROS 2.

Este script atua como uma ponte entre os dados brutos salvos em CSV (Nível 4)
e o sistema ROS 2. Sua única responsabilidade é:
1.  **Monitorar** a pasta do Nível 4 usando 'watchdog' para detectar
    eficientemente quando o arquivo CSV mais recente é modificado (ou criado).
2.  **Ler** a **última linha** adicionada a este arquivo CSV.
3.  **Converter** essa linha num formato **JSON**, utilizando o cabeçalho do
    CSV como chaves para os valores.
4.  **Publicar** a string JSON resultante num tópico ROS 2.

-> Este script **NÃO** se conecta ao MQTT.
-> Este script **NÃO** faz processamento/interpretação dos dados CAN.
-> Ele assume que o Nível 3 ('collector.py') está a rodar e a gerar os CSVs.
"""

# --- Importações Essenciais ---
import rclpy                      # Biblioteca principal do ROS 2 para Python
from rclpy.node import Node         # Classe base para criar um nó ROS 2
from std_msgs.msg import String     # Tipo de mensagem padrão do ROS 2 para enviar strings (usaremos para o JSON)
import json                         # Para converter dicionários Python em strings JSON
import csv                          # Para ler arquivos CSV corretamente (lidando com vírgulas, aspas)
import time                         # Para usar pausas (sleep) e timestamps
import os                           # Para interagir com o sistema de arquivos (verificar pastas, tamanho de arquivos)
import glob                         # Para encontrar arquivos usando padrões (wildcards como *)
# 'watchdog' é uma biblioteca externa para monitorar mudanças no sistema de arquivos
# de forma mais eficiente do que verificar manualmente em loop.
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading                    # Para usar 'Events' para sinalizar parada da thread ROS

# --- CONFIGURAÇÕES ---
# Nível 4: Caminho para a pasta onde o 'collector.py' (Nível 3) salva os arquivos CSV.
# IMPORTANTE: Ajuste este caminho! Deve ser relativo à localização de ONDE você
# executa o Nível 6 (que importa este script), ou um caminho absoluto.
# Exemplo: Se Nível 5 e Nível 4 estão ao lado um do outro, e Nível 6 está acima, use "../Nivel_4/"
PASTA_LOGS_CSV = "../Nivel_4/"
# Padrão do nome dos arquivos CSV criados pelo collector.py. Usado para encontrar o mais recente.
PADRAO_NOME_ARQUIVO = "log_telemetria_*.csv"

# ROS 2
ROS_TOPIC = "telemetria/dados_brutos_csv" # Nome do tópico ROS 2 onde publicaremos o JSON
NODE_NAME = "telemetria_csv_publisher"   # Nome deste nó no grafo de computação ROS 2
# --- FIM DAS CONFIGURAÇÕES ---

# Variável global usada como "bandeira" para sinalizar de forma segura (thread-safe)
# que a thread principal do ROS 2 (rodando rclpy.spin) deve parar.
parar_publisher = threading.Event()

# --- Classe Helper para Watchdog ---

class LogFileHandler(FileSystemEventHandler):
    """
    Classe auxiliar que herda de FileSystemEventHandler do watchdog.
    Define o que fazer quando um evento (como modificação de arquivo) ocorre
    na pasta monitorada.
    """
    def __init__(self, node_callback):
        """
        Inicializa o handler.
        Args:
            node_callback: A função do nó ROS 2 que deve ser chamada quando
                           um arquivo relevante for modificado.
        """
        super().__init__()
        # Armazena a referência à função de callback do nó ROS (será processar_modificacao_log).
        self.node_callback = node_callback
        # Guarda o timestamp da última vez que processamos um evento. Usado para
        # evitar que múltiplos eventos on_modified muito rápidos para o mesmo
        # arquivo causem processamento redundante (debouncing simples).
        self.ultimo_processamento_ts = 0
        # Dicionário para rastrear o último tamanho conhecido de cada arquivo monitorado.
        # Usado para garantir que só processamos quando o arquivo realmente cresceu (nova linha).
        self.ultimo_tamanho_arquivo = {} # Formato: {caminho_completo_arquivo: tamanho_em_bytes}

    def on_modified(self, event):
        """
        Método chamado automaticamente pelo 'watchdog' quando qualquer coisa
        (arquivo ou diretório) é modificada dentro da pasta monitorada.
        """
        # Ignora o evento se for relativo a um diretório (só nos importam arquivos).
        # Verifica se o nome do arquivo termina com '.csv'.
        # Verifica se o nome do arquivo corresponde ao padrão inicial (antes do '*')
        # para ignorar outros CSVs que possam existir na pasta.
        if (not event.is_directory and
                event.src_path.endswith('.csv') and
                PADRAO_NOME_ARQUIVO.split('*')[0] in os.path.basename(event.src_path)):

            agora = time.time()
            # Implementa um limite de taxa (rate limiting/debouncing) simples:
            # Só processa se passou mais de 0.1 segundos desde o último processamento.
            if agora - self.ultimo_processamento_ts > 0.1: # Ajuste o valor (em segundos) conforme necessário
                try:
                    # Obtém o tamanho atual do arquivo modificado.
                    tamanho_atual = os.path.getsize(event.src_path)
                    # Obtém o tamanho que registramos na última vez que processamos este arquivo.
                    # Se for a primeira vez, usa 0 como tamanho anterior.
                    tamanho_anterior = self.ultimo_tamanho_arquivo.get(event.src_path, 0)

                    # Condição principal: Só processa se o arquivo cresceu.
                    # Isso evita processar eventos de modificação que não adicionaram dados (ex: só mudou timestamp).
                    if tamanho_atual > tamanho_anterior:
                        # Chama a função de callback do nó ROS 2, passando o caminho do arquivo modificado.
                        self.node_callback(event.src_path)
                        # Atualiza o último tamanho conhecido para este arquivo.
                        self.ultimo_tamanho_arquivo[event.src_path] = tamanho_atual
                        # Atualiza o timestamp do último processamento bem-sucedido.
                        self.ultimo_processamento_ts = agora
                    # else: # Debug: útil para ver se o evento dispara sem novas linhas
                    #     print(f"DEBUG (Nível 5): Evento on_modified, mas tamanho não aumentou: {event.src_path}")

                except FileNotFoundError:
                    # Tratamento de caso raro: o arquivo foi modificado e deletado muito rapidamente.
                    # Remove o arquivo do nosso rastreamento de tamanho.
                    if event.src_path in self.ultimo_tamanho_arquivo:
                        del self.ultimo_tamanho_arquivo[event.src_path]
                except Exception as e:
                     # Loga outros erros que possam ocorrer ao verificar o tamanho.
                     print(f"ERRO no handler on_modified (Nível 5) ao verificar tamanho: {e}")

# --- Classe do Nó ROS 2 ---

class CsvRosPublisherNode(Node):
    """
    Nó ROS 2 principal do Nível 5.
    - Configura o publisher ROS 2.
    - Inicia o monitoramento da pasta de logs CSV (Nível 4) usando watchdog.
    - Quando notificado de uma modificação, lê a última linha do CSV e a publica.
    """
    def __init__(self):
        """Inicializa o nó ROS 2, o publisher e o monitoramento de arquivos."""
        # Inicializa a classe base Node do rclpy com o nome definido.
        super().__init__(NODE_NAME)
        # Loga o início da inicialização usando o logger do ROS 2.
        self.get_logger().info(f"Nível 5 (Publisher): Iniciando nó '{NODE_NAME}'...")

        # 1. Configurar o Publisher ROS 2:
        #    Cria um publisher que enviará mensagens do tipo 'String'
        #    para o tópico definido em 'ROS_TOPIC'.
        #    '10' é o tamanho da fila (Quality of Service depth) - quantas mensagens
        #    manter em buffer se a rede estiver lenta.
        self.publisher_ = self.create_publisher(String, ROS_TOPIC, 10)
        self.get_logger().info(f"Nível 5 (Publisher): Publicador ROS 2 criado para o tópico '{ROS_TOPIC}'")

        # 2. Encontrar o Arquivo de Log Inicial:
        #    Verifica se já existe algum arquivo de log na pasta ao iniciar.
        self.arquivo_log_atual = self.encontrar_arquivo_log_mais_recente()
        if self.arquivo_log_atual:
            # Se encontrou, loga qual arquivo está a monitorar inicialmente.
            self.get_logger().info(f"Nível 5 (Publisher): Monitorando inicialmente o arquivo: {self.arquivo_log_atual}")
            # Tenta ler o cabeçalho já no início
            self.cabecalho_csv = self.ler_cabecalho_csv(self.arquivo_log_atual)
            if not self.cabecalho_csv:
                 self.get_logger().error(f"Nível 5: Impossível ler cabeçalho do arquivo inicial '{self.arquivo_log_atual}'.")
        else:
            # Se não encontrou, avisa que está a aguardar a criação pelo Nível 3.
            self.get_logger().warn(f"Nível 5 (Publisher): Nenhum arquivo de log CSV encontrado em '{PASTA_LOGS_CSV}'. Aguardando criação pelo Nível 3...")
            self.cabecalho_csv = [] # Inicializa cabeçalho como vazio

        # Guarda o conteúdo (lista) da última linha que foi publicada com sucesso.
        # Usado para evitar republicar exatamente a mesma linha se o evento on_modified
        # disparar múltiplas vezes para a mesma escrita no arquivo.
        self.ultima_linha_publicada_conteudo = None

        # 3. Configurar e Iniciar o Watchdog:
        #    Cria uma instância do nosso handler de eventos, passando a função
        #    'self.processar_modificacao_log' como callback.
        self.event_handler = LogFileHandler(self.processar_modificacao_log)
        #    Cria o objeto Observer do watchdog, que gerencia o monitoramento.
        self.observer = Observer()
        try:
            # Garante que a pasta de logs (Nível 4) exista antes de tentar observá-la.
            # Se não existir, tenta criá-la.
            if not os.path.isdir(PASTA_LOGS_CSV):
                 self.get_logger().info(f"Nível 5 (Publisher): Criando pasta de logs (Nível 4): {PASTA_LOGS_CSV}")
                 os.makedirs(PASTA_LOGS_CSV, exist_ok=True) # exist_ok=True evita erro se já existir

            # Agenda o monitoramento: diz ao observer para usar nosso 'event_handler'
            # para monitorar a pasta 'PASTA_LOGS_CSV'.
            # 'recursive=False' significa que não monitorará subpastas.
            self.observer.schedule(self.event_handler, path=PASTA_LOGS_CSV, recursive=False)
            # Inicia a thread do observer em background. A partir daqui, ele chamará
            # 'on_modified' no nosso handler sempre que houver mudanças.
            self.observer.start()
            self.get_logger().info(f"Nível 5 (Publisher): Monitorando a pasta '{PASTA_LOGS_CSV}' por modificações...")
        except Exception as e:
            # Captura erros que podem ocorrer ao iniciar o observer (ex: pasta não existe e não pode ser criada).
            self.get_logger().error(f"Nível 5 (Publisher): Falha ao iniciar o monitoramento da pasta '{PASTA_LOGS_CSV}': {e}")
            # Levanta a exceção novamente para sinalizar ao código que o chamou que a inicialização falhou.
            raise

        self.get_logger().info("Nível 5 (Publisher): Nó inicializado e pronto.")

    def encontrar_arquivo_log_mais_recente(self):
        """
        Busca na pasta PASTA_LOGS_CSV pelo arquivo que corresponde ao padrão
        PADRAO_NOME_ARQUIVO e que foi modificado mais recentemente.
        Retorna o caminho completo do arquivo ou None se nenhum for encontrado.
        """
        try:
            # Constrói o caminho completo para a busca (ex: ../Nivel_4/log_telemetria_*.csv)
            padrao_busca = os.path.join(PASTA_LOGS_CSV, PADRAO_NOME_ARQUIVO)
            # Usa glob para obter uma lista de todos os arquivos que correspondem ao padrão.
            lista_arquivos = glob.glob(padrao_busca)
            # Se a lista estiver vazia, retorna None.
            if not lista_arquivos:
                return None
            # Usa a função max() com a chave os.path.getmtime para encontrar
            # o arquivo com o maior timestamp de modificação (o mais recente).
            arquivo_mais_recente = max(lista_arquivos, key=os.path.getmtime)
            return arquivo_mais_recente
        except Exception as e:
            # Loga erro se a busca falhar por algum motivo (ex: permissão negada).
            self.get_logger().error(f"Nível 5: Erro ao procurar pelo arquivo de log mais recente: {e}")
            return None

    def ler_ultima_linha_csv(self, caminho_arquivo):
        """
        Lê a última linha de dados de um arquivo CSV de forma relativamente eficiente.
        Retorna a linha como uma lista de strings, ou None se falhar ou não houver dados.
        """
        try:
            # Abre o arquivo CSV para leitura ('r').
            with open(caminho_arquivo, mode='r', newline='', encoding='utf-8') as f:
                # Move o cursor para o final do arquivo para saber o tamanho total.
                f.seek(0, os.SEEK_END)
                tamanho_arquivo = f.tell()
                # Se o arquivo estiver vazio, retorna None.
                if tamanho_arquivo == 0:
                     return None

                # Estratégia de eficiência: Em vez de ler o arquivo inteiro (que pode ser enorme),
                # tentamos ler apenas os últimos ~2KB. Isso geralmente é suficiente
                # para conter várias linhas, incluindo a última.
                tamanho_leitura = 2048
                # Move o cursor para 2KB antes do fim (ou para o início se o arquivo for menor).
                f.seek(max(0, tamanho_arquivo - tamanho_leitura), os.SEEK_SET)
                # Lê as linhas a partir dessa posição até o fim.
                linhas_finais = f.readlines()
                # Se não conseguiu ler nenhuma linha (caso raro), retorna None.
                if not linhas_finais:
                    return None

                # Pega a última linha lida e remove espaços/quebras de linha extras do início/fim.
                ultima_linha_raw = linhas_finais[-1].strip()
                # Se a última linha estiver em branco (pode acontecer), tenta pegar a penúltima, etc.
                while not ultima_linha_raw and len(linhas_finais) > 1:
                     linhas_finais.pop() # Remove a última linha em branco
                     ultima_linha_raw = linhas_finais[-1].strip() # Pega a nova última

                # Se, após remover brancos, não sobrou nenhuma linha de dados, retorna None.
                if not ultima_linha_raw:
                     return None

                # Usa csv.reader para processar a string da última linha.
                # Isso lida corretamente com casos onde os dados podem ter vírgulas
                # dentro de aspas (embora improvável no seu caso, é mais robusto).
                # Passamos a linha como uma lista de uma única string.
                leitor_linha = csv.reader([ultima_linha_raw])
                # Pega o resultado (a linha parseada como uma lista de strings).
                ultima_linha_lista = next(leitor_linha)
                return ultima_linha_lista

        except FileNotFoundError:
             # Se o arquivo foi deletado entre a detecção e a leitura.
             self.get_logger().warn(f"Nível 5: Arquivo '{caminho_arquivo}' não encontrado ao tentar ler a última linha.")
             return None
        except StopIteration: # Caso o csv.reader não consiga parsear a linha.
             self.get_logger().warn(f"Nível 5: Não foi possível parsear a última linha de '{caminho_arquivo}'.")
             return None
        except Exception as e:
            # Captura outros erros de leitura.
            self.get_logger().error(f"Nível 5: Erro ao ler a última linha de '{caminho_arquivo}': {e}")
            return None

    def ler_cabecalho_csv(self, caminho_arquivo):
        """Lê apenas a primeira linha (cabeçalho) de um arquivo CSV."""
        try:
            with open(caminho_arquivo, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                cabecalho = next(reader) # Lê a primeira linha
                # Limpa espaços extras de cada nome de coluna.
                return [col.strip() for col in cabecalho]
        except FileNotFoundError:
             self.get_logger().warn(f"Nível 5: Arquivo '{caminho_arquivo}' não encontrado ao tentar ler cabeçalho.")
             return []
        except StopIteration: # Arquivo está completamente vazio.
             self.get_logger().warn(f"Nível 5: Arquivo '{caminho_arquivo}' está vazio, sem cabeçalho.")
             return []
        except Exception as e:
            self.get_logger().error(f"Nível 5: Erro ao ler cabeçalho de '{caminho_arquivo}': {e}")
            return []

    def processar_modificacao_log(self, caminho_arquivo_modificado):
        """
        Função principal chamada pelo LogFileHandler quando um arquivo CSV relevante
        é modificado e o tamanho aumentou.
        - Verifica se é o arquivo mais recente.
        - Lê/verifica o cabeçalho.
        - Lê a última linha.
        - Compara com a última linha publicada para evitar duplicatas.
        - Cria o JSON usando o cabeçalho como chaves.
        - Publica no ROS 2.
        """
        # 1. Confirma qual é o arquivo mais recente AGORA.
        #    Isso é importante caso o Nível 3 tenha criado um NOVO arquivo de log.
        arquivo_recente = self.encontrar_arquivo_log_mais_recente()

        # Se não há mais arquivos de log ou se o arquivo modificado não é o mais recente,
        # simplesmente ignora este evento de modificação.
        if not arquivo_recente or caminho_arquivo_modificado != arquivo_recente:
             # self.get_logger().debug(f"Nível 5: Modificação ignorada (não é o arquivo mais recente): {caminho_arquivo_modificado}")
             return

        # 2. Gerencia o Cabeçalho:
        #    Se o arquivo que estamos monitorando mudou (um novo foi criado) OU
        #    se ainda não temos um cabeçalho lido, precisamos ler o cabeçalho
        #    do arquivo atual/recente.
        if self.arquivo_log_atual != arquivo_recente or not self.cabecalho_csv:
            self.get_logger().info(f"Nível 5: Novo arquivo de log detectado ou cabeçalho ausente. Lendo cabeçalho de: {arquivo_recente}")
            self.arquivo_log_atual = arquivo_recente # Atualiza qual arquivo estamos a seguir
            self.cabecalho_csv = self.ler_cabecalho_csv(self.arquivo_log_atual) # Lê o cabeçalho
            self.ultima_linha_publicada_conteudo = None # Reseta a última linha para forçar publicação
            # Se não conseguiu ler o cabeçalho, não podemos continuar, pois não saberíamos
            # o nome das colunas para criar o JSON.
            if not self.cabecalho_csv:
                self.get_logger().error(f"Nível 5: Não foi possível ler o cabeçalho do arquivo '{self.arquivo_log_atual}'. Publicação interrompida para este arquivo.")
                return # Interrompe o processamento desta modificação

        # 3. Lê a Última Linha:
        #    Chama a função para ler a última linha do arquivo CSV atual.
        ultima_linha_lista = self.ler_ultima_linha_csv(self.arquivo_log_atual)

        # 4. Verifica e Publica:
        #    Se conseguiu ler uma linha E ela é diferente da última que publicamos...
        if ultima_linha_lista and ultima_linha_lista != self.ultima_linha_publicada_conteudo:
            # Atualiza o conteúdo da última linha publicada para a próxima verificação.
            self.ultima_linha_publicada_conteudo = ultima_linha_lista

            # Verifica se o número de colunas na linha lida corresponde ao número de colunas no cabeçalho.
            if len(ultima_linha_lista) == len(self.cabecalho_csv):
                # Cria um dicionário Python combinando o cabeçalho (chaves) e a linha (valores).
                # Ex: {'timestamp': '1234.5', 'id_can': '0xABC', ...}
                dados_para_json = dict(zip(self.cabecalho_csv, ultima_linha_lista))

                # Cria uma mensagem ROS 2 do tipo String.
                msg = String()
                # Converte o dicionário Python para uma string formatada em JSON.
                msg.data = json.dumps(dados_para_json)

                # Publica a mensagem JSON no tópico ROS 2.
                self.publisher_.publish(msg)
                # Loga a mensagem publicada.
                self.get_logger().info(f"Nível 5 Publicado: {msg.data}")
            else:
                # Avisa se a linha lida não tem o mesmo número de colunas que o cabeçalho.
                self.get_logger().warn(f"Nível 5: Discrepância de colunas em '{self.arquivo_log_atual}'. Cabeçalho={len(self.cabecalho_csv)}, Linha={len(ultima_linha_lista)}. Linha: {ultima_linha_lista}")
        # else: # Debug - Descomente para ver logs quando linhas são ignoradas
        #     if not ultima_linha_lista:
        #          self.get_logger().debug(f"Nível 5: Nenhuma linha de dados encontrada em {self.arquivo_log_atual}")
        #     else:
        #          self.get_logger().debug("Nível 5: Última linha lida é idêntica à anterior. Não publicando.")


    def shutdown_observer(self):
        """Para a thread do observer do watchdog de forma segura antes de encerrar."""
        # Verifica se o observer foi criado e se a thread ainda está ativa.
        if hasattr(self, 'observer') and self.observer.is_alive():
            self.observer.stop() # Sinaliza para a thread parar.
            self.observer.join() # Espera a thread terminar completamente.
            self.get_logger().info("Nível 5 (Publisher): Monitoramento de arquivos encerrado.")

# --- Funções de Controle (para serem chamadas pelo Nível 6) ---

def run_publisher_node():
    """
    Função para ser chamada pelo Nível 6 para iniciar todo o processo do Nível 5.
    Inicializa o rclpy, cria o nó e entra no loop 'spin' do ROS 2.
    """
    global parar_publisher # Acessa a flag de parada global
    node = None # Inicializa a variável do nó
    observer_active = False # Flag para saber se o observer foi iniciado com sucesso
    parar_publisher.clear() # Garante que a flag de parada está abaixada

    try:
        print("Nível 5 (Publisher): Iniciando contexto ROS 2...")
        # Inicializa a comunicação ROS 2. Necessário antes de criar um Nó.
        # Usa 'try...except' para garantir que rclpy.shutdown() seja chamado mesmo se falhar.
        try:
            rclpy.init()
        except Exception as e:
            print(f"Nível 5 (Publisher): ERRO FATAL ao inicializar rclpy: {e}")
            return # Sai se não conseguir inicializar o ROS

        print("Nível 5 (Publisher): Criando nó...")
        # Cria a instância do nosso nó. A inicialização do observer acontece aqui dentro.
        node = CsvRosPublisherNode()
        # Verifica se o observer foi realmente iniciado (pode falhar se a pasta não existir)
        observer_active = hasattr(node, 'observer') and node.observer.is_alive()

        print("Nível 5 (Publisher): Iniciando spin (aguardando eventos ROS e watchdog)...")
        # Entra no loop principal do ROS 2.
        # Em vez de rclpy.spin(node) que bloqueia totalmente, usamos spin_once em loop.
        # Isso permite processar os callbacks do ROS (assinaturas, timers - embora não tenhamos timer aqui)
        # E também verificar nossa flag 'parar_publisher' para permitir um encerramento limpo.
        while rclpy.ok() and not parar_publisher.is_set():
            # Processa quaisquer eventos ROS pendentes (ex: sinais de shutdown).
            # timeout_sec=0.1 faz ele esperar um pouco, evitando 100% de uso da CPU.
            rclpy.spin_once(node, timeout_sec=0.1)
        print("Nível 5 (Publisher): Loop spin encerrado (parada solicitada ou rclpy não ok).")

    except Exception as e:
        # Captura erros inesperados que possam ocorrer durante a criação do nó ou spin.
        if node: node.get_logger().error(f"Nível 5 (Publisher): Erro inesperado durante execução: {e}", exc_info=True)
        else: print(f"Nível 5 (Publisher): Erro inesperado durante inicialização: {e}")
    finally:
        # Bloco de limpeza: garante que tudo seja encerrado corretamente.
        print("Nível 5 (Publisher): Encerrando...")
        if node:
            # Se o observer foi iniciado, garante que ele pare.
            if observer_active:
                 node.shutdown_observer()
            print("Nível 5 (Publisher): Destruindo nó...")
            # Libera os recursos do nó ROS 2.
            node.destroy_node()
        # Verifica se o rclpy ainda está ativo antes de chamar shutdown.
        if rclpy.ok():
             print("Nível 5 (Publisher): Encerrando contexto ROS 2...")
             # Encerra a comunicação ROS 2.
             rclpy.shutdown()
        print("Nível 5 (Publisher): Finalizado.")

def stop_publisher_node():
    """
    Função para ser chamada externamente (pelo Nível 6) para sinalizar
    que a thread do publisher deve parar sua execução (sair do loop spin_once).
    """
    global parar_publisher # Acessa a flag global
    print("Nível 5 (Publisher): Solicitando parada...")
    # Levanta a "bandeira". O loop 'while' na função run_publisher_node() detectará isso.
    parar_publisher.set()

# --- Bloco Principal (Comentado/Removido) ---
# Removemos ou comentamos o bloco 'if __name__ == "__main__":'
# para que este script funcione como uma biblioteca controlada pelo Nível 6.
#
# if __name__ == '__main__':
#     try:
#         run_publisher_node()
#     except KeyboardInterrupt:
#         # Se o usuário pressionar Ctrl+C no terminal onde este script foi iniciado,
#         # solicita a parada.
#         print("\nNível 5 (Publisher): Ctrl+C recebido. Encerrando...")
#         stop_publisher_node()