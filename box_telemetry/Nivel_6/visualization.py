"""
Nível 6: Visualizador Tkinter e Orquestrador dos Níveis 3 e 5.

Este script é o ponto de entrada principal para a telemetria no box.
Ele realiza as seguintes funções:
1.  **Orquestra:** Importa e inicia os scripts do Nível 3 (Collector MQTT->CSV)
    e Nível 5 (Publisher CSV->ROS 2) em threads separadas, tratando-os
    como módulos/bibliotecas.
2.  **Recebe Dados ROS 2:** Cria um nó ROS 2 e se inscreve (subscribe) no tópico
    publicado pelo Nível 5 ('/telemetria/dados_brutos_csv'), que contém
    os dados brutos lidos do CSV em formato JSON.
3.  **Visualiza:** Cria uma interface gráfica simples usando a biblioteca Tkinter
    para exibir os dados recebidos em uma tabela (widget Treeview). A interface
    é atualizada em tempo real à medida que novos dados chegam via ROS 2.
4.  **Gerencia Ciclo de Vida:** Controla o início dos Níveis 3 e 5 quando
    o programa inicia e solicita a parada deles de forma organizada quando
    a janela é fechada ou o programa é interrompido (Ctrl+C).
"""

# --- Importações Essenciais ---
import rclpy                      # Biblioteca principal do ROS 2 para Python
from rclpy.node import Node         # Classe base para criar um nó ROS 2
from std_msgs.msg import String     # Tipo de mensagem padrão do ROS 2 para strings (usaremos para o JSON)
import json                         # Para parsear a string JSON recebida via ROS 2
import tkinter as tk                # Biblioteca padrão do Python para interfaces gráficas (GUI)
from tkinter import ttk             # Módulo do Tkinter com widgets mais modernos (themed widgets)
import threading                    # Para rodar os Níveis 3, 5 e o spin do ROS 2 em threads separadas
import queue                        # Fila segura para comunicação entre a thread ROS (que recebe dados)
                                    # e a thread principal do Tkinter (que atualiza a UI)
import time                         # Para usar pausas (sleep)
import sys                          # Para manipular o path de importação
import os                           # Para manipulação de caminhos de arquivo

# --- Importa as Funções de Controle dos Outros Níveis ---
# Tenta importar os módulos 'collector' (Nível 3) e 'publisher' (Nível 5).
# Para isso funcionar, as pastas Nivel_3/ e Nivel_5/ precisam estar acessíveis
# a partir de onde este script (Nivel_6/visualization.py) está.
# Adicionamos as pastas ao sys.path para garantir a importação.
try:
    # Obtém o diretório onde este script está localizado.
    script_dir = os.path.dirname(__file__)
    # Constrói os caminhos absolutos para as pastas dos Níveis 3 e 5.
    nivel3_path = os.path.abspath(os.path.join(script_dir, '../Nivel_3'))
    nivel5_path = os.path.abspath(os.path.join(script_dir, '../Nivel_5'))
    # Adiciona os caminhos ao sys.path se ainda não estiverem lá.
    if nivel3_path not in sys.path: sys.path.append(nivel3_path)
    if nivel5_path not in sys.path: sys.path.append(nivel5_path)

    # Agora, tenta importar os módulos usando os nomes dos arquivos.
    import collector # Importa Nivel_3/collector.py
    # Importa Nivel_5/publisher.py 
    # para evitar conflito com a variável 'publisher_' dentro da classe ROS.
    import publisher
except ImportError as e:
    # Se a importação falhar, imprime um erro claro e encerra.
    print(f"ERRO FATAL (Nível 6): Não foi possível importar os módulos dos Níveis 3 ou 5.")
    print(f"Verifique se a estrutura de pastas está correta:")
    print(f"  box_telemetry/")
    print(f"  ├── Nivel_3/collector.py")
    print(f"  ├── Nivel_4/")
    print(f"  ├── Nivel_5/publisher.py")
    print(f"  └── Nivel_6/visualization.py")
    print(f"Erro detalhado: {e}")
    exit(1)
except Exception as e:
     # Captura outros erros inesperados durante a importação.
     print(f"ERRO FATAL (Nível 6) inesperado durante importação: {e}")
     exit(1)


# --- CONFIGURAÇÕES ---
# Tópico ROS 2 onde o Nível 5 está publicando os JSONs (deve ser o mesmo ROS_TOPIC do Nível 5).
ROS_TOPIC_TO_SUBSCRIBE = "/telemetria/dados_brutos_csv"
# Nome deste nó ROS 2 (Nível 6).
NODE_NAME = "telemetria_visualizer"
# Intervalo (em milissegundos) com que a interface gráfica (Tkinter) verificará
# se há novos dados na fila para exibir. Valores menores = mais responsivo, mas mais CPU.
UI_UPDATE_INTERVAL_MS = 100 # 100ms = 10 vezes por segundo
# Número máximo de linhas a serem mantidas na tabela de visualização.
# Ajuda a evitar que a tabela cresça indefinidamente e consuma muita memória/performance.
MAX_TABLE_ROWS = 50
# --- FIM DAS CONFIGURAÇÕES ---

# --- Classe Principal (Nó ROS 2 + Aplicação Tkinter) ---

class TelemetryDashboard(Node):
    """
    Combina a funcionalidade de um nó ROS 2 (para receber dados) com a
    lógica de uma aplicação Tkinter (para exibir os dados).
    Também gerencia o ciclo de vida dos Níveis 3 e 5.
    """
    def __init__(self, tk_root):
        """
        Inicializa o nó ROS 2, a interface gráfica e prepara a comunicação.
        Args:
            tk_root: A janela principal (root) da aplicação Tkinter.
        """
        # 1. Inicializa a parte do Nó ROS 2 primeiro.
        super().__init__(NODE_NAME)
        self.get_logger().info(f"Nível 6 (Visualizer): Iniciando nó '{NODE_NAME}'...")

        # Guarda a referência à janela principal do Tkinter.
        self.root = tk_root
        # Define o título da janela.
        self.root.title("Dashboard Telemetria e-Racing - Nível 6")
        # Define o tamanho inicial da janela (largura x altura).
        self.root.geometry("800x600")

        # 2. Cria uma Fila (Queue) Thread-Safe:
        #    A thread do ROS 2 (que recebe mensagens) não pode modificar diretamente
        #    a interface gráfica (que roda na thread principal do Tkinter).
        #    Usamos uma fila como intermediário seguro: a thread ROS coloca os dados
        #    na fila, e a thread Tkinter os retira periodicamente para atualizar a UI.
        self.data_queue = queue.Queue()

        # 3. Constrói os Elementos da Interface Gráfica:
        #    Chama um método separado para criar labels, tabelas, etc.
        self._build_ui()

        # 4. Cria o Subscriber ROS 2:
        #    Inscreve-se no tópico definido em ROS_TOPIC_TO_SUBSCRIBE.
        #    Quando uma mensagem do tipo String chegar, a função self.ros_callback será chamada.
        #    '10' é o tamanho da fila de QoS (Quality of Service).
        self.subscription = self.create_subscription(
            String,
            ROS_TOPIC_TO_SUBSCRIBE,
            self.ros_callback, # Função a ser chamada quando uma mensagem chegar
            10)
        self.get_logger().info(f"Nível 6 (Visualizer): Inscrito no tópico ROS 2 '{ROS_TOPIC_TO_SUBSCRIBE}'")

        # 5. Variáveis para Controlar as Threads dos Outros Níveis:
        #    Guardaremos referências às threads para podermos pará-las depois.
        self.collector_thread = None
        self.publisher_thread = None

        # 6. Agenda a Atualização da UI:
        #    Pede ao loop principal do Tkinter para chamar a função self.process_data_queue
        #    após UI_UPDATE_INTERVAL_MS milissegundos. Essa função, por sua vez,
        #    se reagendará, criando um loop de atualização da UI.
        self.root.after(UI_UPDATE_INTERVAL_MS, self.process_data_queue)

        self.get_logger().info("Nível 6 (Visualizer): Nó e UI inicializados.")

    def _build_ui(self):
        """Cria e organiza os widgets (elementos visuais) da interface Tkinter."""
        self.get_logger().info("Nível 6 (Visualizer): Construindo UI...")

        # Frame principal para organizar os widgets, com um pouco de padding.
        main_frame = ttk.Frame(self.root, padding="10")
        # Faz o frame ocupar todo o espaço disponível na janela.
        main_frame.pack(expand=True, fill="both")

        # Rótulo (Label) para o título do dashboard.
        title_label = ttk.Label(main_frame, text="Dados Brutos da Telemetria (CSV via ROS 2)", font=("Helvetica", 16))
        # Coloca o título no topo, com um espaço abaixo (pady).
        title_label.pack(pady=10)

        # Tabela (Treeview) para exibir os dados linha a linha.
        # Define as colunas que a tabela terá. Estes nomes DEVEM corresponder
        # às chaves do JSON publicado pelo Nível 5 (que vêm do cabeçalho do CSV).
        columns = ("timestamp", "id_can", "prioridade", "dados_hex")
        # Cria o widget Treeview, associando as colunas e definindo para mostrar apenas os cabeçalhos.
        # 'height' define quantas linhas são visíveis inicialmente (a scrollbar cuida do resto).
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)

        # Configura a aparência de cada cabeçalho de coluna.
        for col in columns:
            # Define o texto do cabeçalho (troca '_' por espaço e capitaliza).
            self.tree.heading(col, text=col.replace('_', ' ').title())
            # Define o alinhamento ('anchor') e a largura inicial da coluna.
            self.tree.column(col, anchor=tk.W, width=150) # 'W' = West (Esquerda)

        # Adiciona barras de rolagem (Scrollbars) à tabela.
        # Barra de rolagem vertical.
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        # Barra de rolagem horizontal.
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        # Associa as barras de rolagem ao widget Treeview.
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Organiza a tabela e as barras de rolagem no frame usando o gerenciador 'pack'.
        # A tabela ocupa o espaço à esquerda, expandindo para preencher.
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # A barra vertical fica à direita, preenchendo na vertical.
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        # A barra horizontal fica na parte inferior, preenchendo na horizontal.
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.get_logger().info("Nível 6 (Visualizer): UI construída.")


    def start_background_levels(self):
        """
        Inicia os scripts dos Níveis 3 e 5, cada um em sua própria thread.
        Isso permite que eles rodem em paralelo com a interface gráfica (Nível 6).
        """
        self.get_logger().info("Nível 6 (Visualizer): Iniciando Nível 3 (Collector) em background...")
        # Cria uma nova thread que executará a função 'run_collector' do módulo 'collector'.
        # 'daemon=True' significa que esta thread será encerrada automaticamente se o programa principal (Nível 6) terminar.
        self.collector_thread = threading.Thread(target=collector.run_collector, daemon=True)
        # Inicia a execução da thread.
        self.collector_thread.start()

        # Pequena pausa: O Nível 3 pode precisar de um instante para criar a pasta Nível_4
        # antes que o Nível 5 tente monitorá-la. Ajuste se necessário.
        time.sleep(1)

        self.get_logger().info("Nível 6 (Visualizer): Iniciando Nível 5 (Publisher) em background...")
        # Cria uma nova thread que executará a função 'run_publisher_node' do módulo 'publisher'.
        # Esta função já cuida de inicializar rclpy, criar o nó e rodar o spin dentro da thread dela.
        self.publisher_thread = threading.Thread(target=publisher.run_publisher_node, daemon=True)
        # Inicia a execução da thread.
        self.publisher_thread.start()

    def stop_background_levels(self):
        """
        Sinaliza para as threads dos Níveis 3 e 5 pararem suas execuções
        e aguarda um tempo limitado para que elas encerrem.
        """
        self.get_logger().info("Nível 6 (Visualizer): Solicitando parada do Nível 5 (Publisher)...")
        # Chama a função 'stop_publisher_node' do Nível 5, que deve sinalizar
        # para a thread ROS (rodando spin_once) parar.
        publisher.stop_publisher_node()

        self.get_logger().info("Nível 6 (Visualizer): Solicitando parada do Nível 3 (Collector)...")
        # Chama a função 'stop_collector' do Nível 3, que deve sinalizar
        # para a thread MQTT parar seu loop.
        collector.stop_collector()

        # Aguarda as threads terminarem, mas com um tempo limite (timeout)
        # para evitar que o programa principal fique bloqueado indefinidamente.
        if self.publisher_thread and self.publisher_thread.is_alive():
            self.get_logger().info("Nível 6 (Visualizer): Aguardando Nível 5 encerrar...")
            self.publisher_thread.join(timeout=5.0) # Espera no máximo 5 segundos.
            if self.publisher_thread.is_alive():
                 # Se ainda estiver viva após o timeout, avisa.
                 self.get_logger().warn("Nível 5 (Publisher) não encerrou no tempo esperado.")

        if self.collector_thread and self.collector_thread.is_alive():
            self.get_logger().info("Nível 6 (Visualizer): Aguardando Nível 3 encerrar...")
            self.collector_thread.join(timeout=5.0) # Espera no máximo 5 segundos.
            if self.collector_thread.is_alive():
                 self.get_logger().warn("Nível 3 (Collector) não encerrou no tempo esperado.")

        self.get_logger().info("Nível 6 (Visualizer): Threads background (Nível 3 e 5) finalizadas ou timeout.")

    def ros_callback(self, msg):
        """
        Função chamada automaticamente pela biblioteca rclpy (em uma thread separada)
        sempre que uma mensagem chega no tópico ROS 2 que assinamos.
        Args:
            msg: Objeto da mensagem recebida (neste caso, std_msgs.msg.String).
        """
        # Log verboso (descomente para ver todas as mensagens chegando).
        # self.get_logger().debug(f"Nível 6: Mensagem ROS recebida: {msg.data}")
        try:
            # 'msg.data' contém a string JSON publicada pelo Nível 5.
            # Usa json.loads() para converter a string JSON de volta para um dicionário Python.
            data_dict = json.loads(msg.data)
            # Coloca o dicionário na fila (Queue). A fila é thread-safe,
            # então não há problema em ser chamada pela thread ROS.
            self.data_queue.put(data_dict)
        except json.JSONDecodeError:
            # Captura erro se a string recebida não for um JSON válido.
            self.get_logger().warn(f"Nível 6: Mensagem ROS recebida não é JSON válido: {msg.data}")
        except Exception as e:
            # Captura outros erros inesperados no callback.
            self.get_logger().error(f"Nível 6: Erro no callback ROS: {e}")

    def process_data_queue(self):
        """
        Função executada periodicamente pela thread principal do Tkinter (agendada com root.after).
        Verifica se há dados na fila (colocados pelo ros_callback) e, se houver,
        atualiza a interface gráfica.
        """
        try:
            # Loop para processar todos os itens atualmente na fila de uma vez.
            while not self.data_queue.empty():
                # Pega o próximo item da fila. get_nowait() levanta uma exceção
                # queue.Empty se a fila estiver vazia (não bloqueia).
                data_dict = self.data_queue.get_nowait()
                # Chama a função que atualiza a tabela na UI com os dados recebidos.
                self.update_table(data_dict)
        except queue.Empty:
            # Exceção esperada quando a fila está vazia. Simplesmente ignora.
            pass
        except Exception as e:
             # Captura outros erros durante o processamento da fila ou atualização da UI.
             self.get_logger().error(f"Nível 6: Erro ao processar fila de dados da UI: {e}")
        finally:
            # **Reagendamento:** Pede ao Tkinter para chamar esta função novamente
            # após o intervalo definido, criando o loop de atualização da UI.
            self.root.after(UI_UPDATE_INTERVAL_MS, self.process_data_queue)

    def update_table(self, data_dict):
        """
        Atualiza o widget Treeview (tabela) com os dados de um novo pacote recebido.
        Args:
            data_dict: Um dicionário Python com os dados parseados do JSON.
                       As chaves devem corresponder aos nomes das colunas definidas em _build_ui.
        """
        try:
            # Extrai os valores do dicionário na ordem correta das colunas da tabela.
            # Usa .get(chave, valor_padrao) para evitar erros se alguma chave
            # (coluna) estiver faltando no JSON recebido.
            values = (
                data_dict.get("timestamp", "N/A"),
                data_dict.get("id_can", "N/A"),
                data_dict.get("prioridade", "N/A"),
                data_dict.get("dados_hex", "N/A")
            )

            # Insere a nova linha de dados no topo da tabela (Treeview).
            # O primeiro argumento "" indica o item pai (raiz).
            # O segundo argumento '0' indica a posição (0 = início).
            # 'values=values' passa a tupla de valores para preencher as colunas.
            self.tree.insert("", 0, values=values)

            # Limita o número de linhas na tabela para evitar problemas de performance/memória.
            # Pega todos os itens (linhas) atualmente na tabela.
            items = self.tree.get_children()
            # Se o número de itens exceder o máximo definido...
            if len(items) > MAX_TABLE_ROWS:
                # Remove o item mais antigo. No Treeview, quando inserimos no início (0),
                # o item mais antigo é o último na lista retornada por get_children().
                self.tree.delete(items[-1])

        except Exception as e:
            # Captura erros durante a atualização da tabela.
            self.get_logger().error(f"Nível 6: Erro ao atualizar tabela da UI: {e}. Dados: {data_dict}")

    def on_closing(self):
        """
        Função de limpeza chamada quando o usuário fecha a janela Tkinter
        (configurada usando root.protocol("WM_DELETE_WINDOW", ...)).
        Orquestra a parada dos outros níveis e o encerramento do ROS e Tkinter.
        """
        self.get_logger().info("Nível 6 (Visualizer): Evento de fechamento da janela recebido. Encerrando aplicação...")

        # 1. Parar as Threads Background (Nível 3 e Nível 5):
        #    Chama a função que sinaliza e aguarda as threads terminarem.
        self.stop_background_levels()

        # 2. Destruir o Nó ROS 2 do Nível 6:
        #    Libera os recursos associados a este nó (publisher, subscriber, timer).
        self.get_logger().info("Nível 6 (Visualizer): Destruindo nó ROS 2 do Nível 6...")
        if rclpy.ok(): # Verifica se o rclpy ainda está ativo
            self.destroy_node()

        # 3. Encerrar o Contexto ROS 2:
        #    Fecha a comunicação global do rclpy. É importante fazer isso *depois*
        #    de parar a thread de spin e destruir o nó.
        if rclpy.ok():
            self.get_logger().info("Nível 6 (Visualizer): Encerrando contexto ROS 2...")
            rclpy.shutdown()

        # 4. Fechar a Janela Tkinter:
        self.get_logger().info("Nível 6 (Visualizer): Fechando janela Tkinter...")
        # self.root.quit() para o loop mainloop() do Tkinter de forma limpa.
        self.root.quit()
        # self.root.destroy() destrói a janela e todos os widgets (pode ser chamado após quit).
        self.root.destroy()

# --- Função Principal de Execução ---

def main(args=None):
    """
    Ponto de entrada principal do script.
    Inicializa Tkinter, ROS 2, cria o nó/aplicação, inicia os níveis
    background e entra nos loops principais. Gerencia o encerramento.
    """
    print("--- Iniciando Orquestrador da Telemetria (Nível 6) ---")

    # Inicializa a biblioteca Tkinter e cria a janela principal (root).
    tk_root = tk.Tk()

    # Inicializa a comunicação ROS 2 globalmente. Necessário antes de criar qualquer Nó.
    print("Nível 6: Inicializando contexto ROS 2...")
    rclpy.init(args=args)

    # Cria a instância da nossa classe principal, que é um Nó ROS 2 e gerencia o Tkinter.
    dashboard_node = TelemetryDashboard(tk_root)

    # Configura o comportamento do botão 'X' da janela: em vez de fechar
    # abruptamente, ele chamará nossa função de limpeza 'on_closing'.
    tk_root.protocol("WM_DELETE_WINDOW", dashboard_node.on_closing)

    # Cria uma thread separada especificamente para rodar o 'rclpy.spin(dashboard_node)'.
    # O 'rclpy.spin()' é um loop bloqueante que processa os callbacks do ROS (subscriber, timers).
    # Se o rodássemos na thread principal, ele bloquearia o loop do Tkinter (mainloop),
    # e a interface gráfica congelaria. Rodando em thread separada, ambos podem funcionar.
    ros_spin_thread = threading.Thread(target=rclpy.spin, args=(dashboard_node,), daemon=True)

    try:
        # Inicia os Níveis 3 (Collector) e 5 (Publisher) em suas próprias threads.
        dashboard_node.start_background_levels()

        # Inicia a thread que rodará o rclpy.spin() para este nó (Nível 6).
        print("Nível 6: Iniciando spin ROS 2 (Nível 6) em thread separada...")
        ros_spin_thread.start()

        # Inicia o loop principal do Tkinter. Esta chamada é bloqueante.
        # Ela mantém a janela aberta, processa eventos da interface (cliques, etc.)
        # e executa as funções agendadas com 'root.after' (como nossa atualização da UI).
        # O programa só continuará após esta linha quando 'root.quit()' for chamado (em on_closing).
        print("Nível 6: Iniciando loop principal Tkinter (UI)...")
        tk_root.mainloop()
        print("Nível 6: Loop principal Tkinter finalizado.")


    except KeyboardInterrupt:
        # Captura o sinal de interrupção (Ctrl+C) no terminal.
        print("\nNível 6: Ctrl+C recebido no terminal principal. Solicitando encerramento limpo...")
        # Chama a mesma função de limpeza que o fechamento da janela.
        dashboard_node.on_closing()
    except Exception as e:
        # Captura outros erros inesperados que possam ocorrer no bloco principal.
        print(f"Nível 6: Erro inesperado na função main: {e}")
        # Tenta executar a limpeza mesmo em caso de erro.
        if 'dashboard_node' in locals() and dashboard_node:
             dashboard_node.on_closing()
        elif rclpy.ok(): # Se o nó falhou antes de on_closing, garante shutdown do ROS
            rclpy.shutdown()
    finally:
        # Bloco de limpeza final, executado sempre após o try ou except.
        # Garante que a thread de spin do ROS 2 finalize corretamente.
        if 'ros_spin_thread' in locals() and ros_spin_thread.is_alive():
             print("Nível 6: Aguardando thread de spin ROS 2 (Nível 6) finalizar...")
             # O rclpy.shutdown() chamado em on_closing geralmente faz o spin parar.
             # Damos um pequeno timeout para a thread terminar.
             ros_spin_thread.join(timeout=2.0)
             if ros_spin_thread.is_alive():
                  print("Nível 6: AVISO - Thread de spin ROS 2 não finalizou no tempo esperado.")

        # Garante que o rclpy seja finalizado, caso on_closing não tenha sido chamado ou falhado.
        if rclpy.ok():
            print("Nível 6: Garantindo shutdown final do ROS 2...")
            rclpy.shutdown()

        print("--- Orquestrador da Telemetria (Nível 6) Finalizado ---")

# Ponto de entrada padrão para scripts Python.
if __name__ == '__main__':
    # Chama a função principal para iniciar todo o processo.
    main()