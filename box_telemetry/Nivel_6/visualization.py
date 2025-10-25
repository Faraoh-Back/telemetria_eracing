"""
Nível 6: Biblioteca de Visualização Tkinter e Receptor ROS 2.

Este script, quando importado como um módulo, fornece a funcionalidade para:
1.  **Receber Dados ROS 2:** Criar um nó ROS 2 e se inscrever no tópico
    publicado pelo Nível 5 ('/telemetria/dados_brutos_csv'), que contém
    os dados brutos lidos do CSV em formato JSON.
2.  **Visualizar:** Criar uma interface gráfica simples usando Tkinter para
    exibir os dados recebidos em uma tabela (Treeview).

-> Este script NÃO inicia ou para os Níveis 3 ou 5 diretamente.
-> A inicialização e o encerramento do ROS 2 (rclpy.init/shutdown) devem
   ser gerenciados pelo script que importa este módulo (Nível 7 - conductor.py).
-> O loop principal do Tkinter (mainloop) e o spin do ROS 2 são gerenciados
   internamente pelas funções run_visualization/stop_visualization.
"""

# --- Importações Essenciais ---
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import tkinter as tk
from tkinter import ttk
import threading
import queue
import time
import sys # Para mensagens de erro
import os  # Para manipulação de caminhos (embora não usado diretamente aqui)

# --- CONFIGURAÇÕES ---
ROS_TOPIC_TO_SUBSCRIBE = "/telemetria/dados_brutos_csv" # Tópico ROS 2 do Nível 5
NODE_NAME = "telemetria_visualizer_node" # Nome do nó ROS 2 do Nível 6
UI_UPDATE_INTERVAL_MS = 100 # Intervalo de atualização da UI (ms)
MAX_TABLE_ROWS = 30         # Máximo de linhas na tabela
# --- FIM DAS CONFIGURAÇÕES ---

# --- Variáveis Globais do Módulo ---
# Usadas para controlar o ciclo de vida do Tkinter e ROS spin a partir do Nível 7
tk_root_global = None
dashboard_node_global = None
ros_spin_thread_global = None
parar_visualization = threading.Event() # Flag para sinalizar parada

# --- Classe do Nó ROS 2 e Aplicação Tkinter ---
class TelemetryDashboardNode(Node):
    """
    Nó ROS 2 que se inscreve nos dados brutos e gerencia a UI Tkinter.
    """
    def __init__(self, tk_root):
        """Inicializa o nó, a UI e a comunicação entre threads."""
        # Inicializa o Nó ROS 2
        super().__init__(NODE_NAME)
        self.get_logger().info(f"Nível 6 (Visualizer Lib): Iniciando nó '{NODE_NAME}'...")

        self.root = tk_root # Guarda a referência da janela principal Tkinter

        # Fila thread-safe para comunicação ROS Callback -> UI Tkinter
        self.data_queue = queue.Queue(maxsize=100)

        # Constrói os widgets da UI
        self._build_ui()

        # Cria o subscriber ROS 2
        self.subscription = self.create_subscription(
            String,
            ROS_TOPIC_TO_SUBSCRIBE,
            self.ros_callback, # Função a ser chamada quando mensagem chegar
            10) # QoS depth
        self.get_logger().info(f"Nível 6 (Visualizer Lib): Inscrito no tópico ROS 2 '{ROS_TOPIC_TO_SUBSCRIBE}'")

        # Agenda a primeira verificação da fila de dados na UI
        self.root.after(UI_UPDATE_INTERVAL_MS, self.process_data_queue)

        self.get_logger().info("Nível 6 (Visualizer Lib): Nó e UI inicializados.")

    def _build_ui(self):
        """Cria os widgets Tkinter (tabela, etc.)."""
        self.get_logger().debug("Nível 6: Construindo UI...") # Log de Debug

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(expand=True, fill="both")

        title_label = ttk.Label(main_frame, text="Dados Brutos Recebidos (Nível 5 via ROS 2)", font=("Helvetica", 16))
        title_label.pack(pady=10)

        # Tabela (Treeview)
        self.columns = ("timestamp", "id_can", "prioridade", "dados_hex")
        self.tree = ttk.Treeview(main_frame, columns=self.columns, show='headings', height=15)
        for col in self.columns:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            # Ajuste de larguras
            width = 180 if col == "timestamp" else (250 if col == "dados_hex" else (100 if col == "id_can" else 50))
            anchor = tk.CENTER if col == "prioridade" else tk.W
            self.tree.column(col, anchor=anchor, width=width)

        # Scrollbars
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.get_logger().debug("Nível 6: UI construída.") # Log de Debug

    def ros_callback(self, msg):
        """Callback do subscriber ROS: recebe JSON, parseia, põe na fila."""
        # self.get_logger().debug(f"Nível 6: ROS Msg Recebida: {msg.data}") # Log verboso
        try:
            data_dict = json.loads(msg.data)
            self.data_queue.put_nowait(data_dict) # Usa put_nowait para não bloquear a thread ROS
        except queue.Full:
            self.get_logger().warn("Nível 6: Fila de dados da UI cheia. Descartando mensagem ROS.")
        except json.JSONDecodeError:
            self.get_logger().warn(f"Nível 6: Mensagem ROS não é JSON válido: {msg.data[:100]}...") # Mostra só o início
        except Exception as e:
            self.get_logger().error(f"Nível 6: Erro no callback ROS: {e}")

    def process_data_queue(self):
        """Função periódica (Tkinter): esvazia a fila e atualiza a UI."""
        global parar_visualization # Acessa a flag de parada global do módulo
        try:
            # Processa mensagens na fila
            while not self.data_queue.empty():
                data_dict = self.data_queue.get_nowait()
                self.update_table(data_dict)
                self.data_queue.task_done()
        except queue.Empty:
            pass # Normal
        except Exception as e:
             self.get_logger().error(f"Nível 6: Erro ao processar fila/atualizar UI: {e}")
        finally:
            # Reagenda a si mesma APENAS se não foi solicitado para parar E ROS está ok
            if not parar_visualization.is_set() and rclpy.ok():
                self.root.after(UI_UPDATE_INTERVAL_MS, self.process_data_queue)
            # else: # Debug
            #      self.get_logger().info("Nível 6: Parando reagendamento de process_data_queue.")


    def update_table(self, data_dict):
        """Adiciona nova linha no topo da tabela Treeview."""
        try:
            # Garante que todos os valores existam no dicionário, usando 'N/A' como padrão
            values = tuple(data_dict.get(col, "N/A") for col in self.columns)

            # Insere no topo
            new_item_id = self.tree.insert("", 0, values=values, iid=None)

            # Limita o número de linhas
            items = self.tree.get_children()
            if len(items) > MAX_TABLE_ROWS:
                self.tree.delete(items[-1]) # Remove a mais antiga (última)

        except Exception as e:
            self.get_logger().error(f"Nível 6: Erro ao atualizar tabela UI: {e}. Dados: {data_dict}")

    def shutdown_node(self):
        """Rotina de limpeza específica do nó ROS 6."""
        self.get_logger().info("Nível 6 (Visualizer Lib): Destruindo nó ROS 6...")
        # A subscrição e outros recursos ROS são limpos ao destruir o nó
        self.destroy_node()
        self.get_logger().info("Nível 6 (Visualizer Lib): Nó ROS 6 destruído.")


# --- Funções de Controle (para serem chamadas pelo Nível 7) ---

def run_visualization():
    """
    Função principal para iniciar a visualização (Nível 6).
    Cria a janela Tkinter, o nó ROS 2, e inicia os loops necessários.
    Esta função deve ser chamada em uma thread pelo Nível 7.
    """
    global tk_root_global, dashboard_node_global, ros_spin_thread_global, parar_visualization

    print("Nível 6 (Visualizer Lib): Iniciando...")
    parar_visualization.clear() # Garante que a flag de parada está abaixada

    # Verifica se o ROS 2 foi inicializado pelo Nível 7
    if not rclpy.ok():
        print("ERRO FATAL (Nível 6): rclpy não foi inicializado antes de chamar run_visualization().")
        # Tenta inicializar aqui como fallback, mas o ideal é no Nível 7
        try:
             print("Nível 6: Tentando inicializar rclpy...")
             rclpy.init()
             if not rclpy.ok(): raise RuntimeError("rclpy.init() falhou")
        except Exception as init_e:
             print(f"ERRO FATAL (Nível 6): Falha ao inicializar rclpy: {init_e}")
             return # Não pode continuar sem ROS

    try:
        # 1. Cria a Janela Principal Tkinter
        print("Nível 6: Criando janela Tkinter...")
        tk_root_global = tk.Tk()

        # 2. Cria a Instância do Nó/Aplicação
        print("Nível 6: Criando nó ROS 2/Dashboard...")
        dashboard_node_global = TelemetryDashboard(tk_root_global)

        # 3. Configura o Fechamento da Janela para chamar stop_visualization
        def handle_close_wrapper():
            print("Nível 6: Fechamento da janela detectado.")
            stop_visualization() # Chama nossa função de parada
        tk_root_global.protocol("WM_DELETE_WINDOW", handle_close_wrapper)

        # 4. Inicia o Spin do ROS 2 em Thread Separada
        #    Isso é crucial para que o rclpy.spin() não bloqueie o tk_root.mainloop()
        print("Nível 6: Iniciando thread de spin ROS 2...")
        ros_spin_thread_global = threading.Thread(target=rclpy.spin, args=(dashboard_node_global,), daemon=True, name="RosSpinThread_N6")
        ros_spin_thread_global.start()

        # 5. Inicia o Loop Principal do Tkinter (Bloqueante)
        print("Nível 6: Iniciando loop principal Tkinter (UI)...")
        # Este loop só termina quando tk_root_global.quit() é chamado (em stop_visualization)
        tk_root_global.mainloop()
        print("Nível 6: Loop principal Tkinter finalizado.")

    except Exception as e:
        # Captura erros inesperados durante a inicialização ou execução
        log_func = print
        if dashboard_node_global: log_func = dashboard_node_global.get_logger().error
        log_func(f"Nível 6 (Visualizer Lib): ERRO inesperado em run_visualization: {e}", exc_info=True)
        # Tenta sinalizar parada mesmo em caso de erro
        stop_visualization()
    finally:
        # Bloco de limpeza final para esta função/thread
        print("Nível 6 (Visualizer Lib): Finalizando run_visualization...")
        # Garante que o nó seja destruído se foi criado
        if dashboard_node_global:
            # A destruição agora é feita dentro de stop_visualization para garantir ordem
            # dashboard_node_global.shutdown_node() # Movido para stop_visualization
            pass
        # A janela Tkinter é destruída em stop_visualization
        # if tk_root_global:
        #    try: tk_root_global.destroy()
        #    except: pass
        print("Nível 6 (Visualizer Lib): run_visualization concluído.")


def stop_visualization():
    """
    Função para ser chamada externamente (pelo Nível 7 ou pelo fechamento da janela)
    para sinalizar que a visualização (Tkinter e Nó ROS 6) deve parar.
    """
    global tk_root_global, dashboard_node_global, ros_spin_thread_global, parar_visualization

    # Verifica se já foi solicitado para parar para evitar chamadas múltiplas
    if parar_visualization.is_set():
        print("Nível 6: Parada já solicitada.")
        return

    print("Nível 6 (Visualizer Lib): Solicitando parada...")
    parar_visualization.set() # Levanta a "bandeira" de parada

    # 1. Parar o loop Tkinter (se estiver rodando)
    if tk_root_global:
        print("Nível 6: Solicitando parada do loop Tkinter...")
        try:
            # Chama quit() para interromper o mainloop() de forma segura
            # Usa after(0,...) para garantir que seja executado na thread Tkinter
            tk_root_global.after(0, tk_root_global.quit)
            # Espera um pouco para o quit processar
            time.sleep(0.2)
            # Tenta destruir a janela (pode dar erro se já fechada, por isso o try)
            print("Nível 6: Destruindo janela Tkinter...")
            tk_root_global.destroy()
            tk_root_global = None # Limpa a referência global
        except tk.TclError as e:
            print(f"Nível 6: Erro (esperado?) ao fechar Tkinter: {e}")
        except Exception as e:
            print(f"Nível 6: Erro inesperado ao fechar Tkinter: {e}")


    # 2. Parar o Nó ROS 2 (Nível 6)
    #    A parada do rclpy.spin() é gerenciada pelo rclpy.shutdown() global do Nível 7.
    #    Aqui, apenas destruímos os recursos específicos do nó.
    if dashboard_node_global:
        print("Nível 6: Destruindo nó ROS 2 do Nível 6...")
        try:
            # Espera um pouco caso o spin precise de tempo para sair após rclpy.shutdown()
            if ros_spin_thread_global and ros_spin_thread_global.is_alive():
                 ros_spin_thread_global.join(timeout=1.0)
            dashboard_node_global.shutdown_node()
            dashboard_node_global = None # Limpa a referência global
        except Exception as e:
             print(f"Nível 6: Erro ao destruir nó ROS 6: {e}")

    # 3. Aguardar a thread de spin finalizar (se existir)
    #    O rclpy.shutdown() chamado pelo Nível 7 deve fazer ela parar.
    if ros_spin_thread_global and ros_spin_thread_global.is_alive():
        print("Nível 6: Aguardando thread de spin ROS 6 finalizar...")
        ros_spin_thread_global.join(timeout=2.0)
        if ros_spin_thread_global.is_alive():
             print("Nível 6: AVISO - Thread de spin ROS 6 não finalizou.")
        ros_spin_thread_global = None # Limpa a referência global


    print("Nível 6 (Visualizer Lib): Parada concluída.")

# --- Bloco Principal Removido ---
# if __name__ == '__main__':
#     # Este bloco não será executado quando importado pelo Nível 7
#     print("AVISO: Este script (Nível 6) foi projetado para ser importado e iniciado pelo Nível 7 (conductor.py).")
#     # Poderia adicionar lógica aqui para rodar standalone para testes,
#     # mas precisaria inicializar/finalizar rclpy