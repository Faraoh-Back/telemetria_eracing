# Arquivo: Nivel_7/conductor.py (Novo Script - Comentado)
#!/usr/bin/env python3
"""
Nível 7: Conductor (Maestro) da Telemetria no Box.

Este script é o ponto de entrada principal para toda a aplicação de telemetria
que roda no computador do box. Sua responsabilidade é orquestrar o ciclo de
vida dos outros níveis (módulos) que realizam as tarefas específicas:

- Nível 3 (Collector): Recebe dados brutos via MQTT e salva em CSV (Nível 4).
- Nível 5 (Publisher): Lê os CSVs atualizados e publica os dados brutos em ROS 2.
- Nível 6 (Visualizer): Recebe os dados ROS 2 e os exibe em uma interface gráfica.

O Conductor inicia esses níveis em threads separadas, gerencia o início e
o fim da comunicação ROS 2 globalmente, e garante um encerramento limpo
quando o usuário solicita (fechando a janela do Nível 6 ou pressionando Ctrl+C).
"""

# --- Importações Essenciais ---
import threading  # Para criar e gerenciar threads para cada nível
import time       # Para usar pausas (sleep)
import rclpy      # Biblioteca principal do ROS 2 (inicialização/shutdown global)
import sys        # Para manipulação do path de importação e saída de erro
import os         # Para manipulação de caminhos de arquivo
import signal     # Para capturar sinais do sistema (como Ctrl+C) de forma mais robusta

# --- Importa as Funções de Controle dos Outros Níveis ---
# Tenta importar as funções run/stop dos módulos dos Níveis 3, 5 e 6.
try:
    # Obtém o diretório onde este script (Nível 7) está localizado.
    script_dir = os.path.dirname(__file__)
    # Constrói os caminhos absolutos para as pastas dos outros níveis (assumindo Nivel_X ao lado de Nivel_7).
    nivel3_path = os.path.abspath(os.path.join(script_dir, '../Nivel_3'))
    nivel5_path = os.path.abspath(os.path.join(script_dir, '../Nivel_5'))
    nivel6_path = os.path.abspath(os.path.join(script_dir, '../Nivel_6'))

    # Adiciona os caminhos ao sys.path para que o Python possa encontrar os módulos.
    if nivel3_path not in sys.path: sys.path.append(nivel3_path)
    if nivel5_path not in sys.path: sys.path.append(nivel5_path)
    if nivel6_path not in sys.path: sys.path.append(nivel6_path)

    # Importa os módulos agora que os paths estão configurados.
    import collector             # Módulo Nível 3
    import publisher as level5_publisher # Módulo Nível 5 (renomeado na importação)
    import visualization as level6_visualization # Módulo Nível 6 (renomeado na importação)

except ImportError as e:
    # Erro claro se não conseguir importar algum nível.
    print(f"ERRO FATAL (Nível 7): Falha ao importar módulos dos Níveis 3, 5 ou 6.")
    print(f" Verifique a estrutura de pastas e se os arquivos .py existem.")
    print(f" Caminhos tentados:")
    print(f"  Nível 3: {nivel3_path}")
    print(f"  Nível 5: {nivel5_path}")
    print(f"  Nível 6: {nivel6_path}")
    print(f" Erro detalhado: {e}")
    exit(1)
except Exception as e:
     # Captura outros erros inesperados durante a importação.
     print(f"ERRO FATAL (Nível 7) inesperado durante importação: {e}")
     exit(1)

# --- Variáveis Globais de Controle ---
# Lista para guardar as referências das threads criadas para cada nível.
threads = []
# Evento para sinalizar o encerramento limpo para a thread principal.
parar_conductor = threading.Event()

# --- Funções de Controle ---

def iniciar_niveis():
    """Cria e inicia as threads para os Níveis 3, 5 e 6."""
    global threads
    print("Nível 7 (Conductor): Iniciando níveis em background...")

    # Define as funções alvo e nomes para cada thread
    targets = {
        "Nível 3 (Collector)": collector.run_collector,
        "Nível 5 (Publisher)": level5_publisher.run_publisher_node,
        "Nível 6 (Visualizer)": level6_visualization.run_visualization,
    }

    # Cria e inicia cada thread
    for nome, target_func in targets.items():
        print(f"Nível 7 (Conductor): Iniciando thread para {nome}...")
        thread = threading.Thread(target=target_func, name=f"{nome}Thread", daemon=True)
        threads.append((nome, thread)) # Guarda nome e objeto thread
        thread.start()
        # Pequena pausa entre inícios pode ajudar a escalonar o log inicial
        time.sleep(0.5)

    print("Nível 7 (Conductor): Todos os níveis iniciados.")

def parar_niveis():
    """Solicita a parada de todos os níveis e aguarda o término das threads."""
    global threads, parar_conductor

    # Sinaliza para a thread principal (e qualquer outra que possa estar esperando) parar.
    parar_conductor.set()

    print("Nível 7 (Conductor): Solicitando parada dos níveis...")

    # Solicita parada dos níveis na ordem inversa (Visualização primeiro, depois Publisher, depois Collector)
    # Isso pode ajudar a garantir que dependências sejam encerradas corretamente.
    print("Nível 7 (Conductor): Solicitando parada do Nível 6...")
    level6_visualization.stop_visualization()

    print("Nível 7 (Conductor): Solicitando parada do Nível 5...")
    level5_publisher.stop_publisher_node()

    print("Nível 7 (Conductor): Solicitando parada do Nível 3...")
    collector.stop_collector()

    # Aguarda as threads finalizarem
    print("Nível 7 (Conductor): Aguardando finalização das threads...")
    for nome, thread in threads:
        if thread.is_alive():
            print(f"Nível 7 (Conductor): Aguardando {nome}...")
            thread.join(timeout=7.0) # Aumenta o timeout geral
            if thread.is_alive():
                print(f"Nível 7 (Conductor): AVISO - Thread {nome} não finalizou no tempo esperado.")
        # else: # Debug
            # print(f"Nível 7 (Conductor): Thread {nome} já finalizada.")

    print("Nível 7 (Conductor): Todas as threads background finalizadas ou timeout.")

def signal_handler(sig, frame):
    """Handler para sinais do sistema (como SIGINT de Ctrl+C)."""
    print(f'\nNível 7 (Conductor): Sinal {signal.Signals(sig).name} recebido. Iniciando encerramento...')
    # Chama a função principal de parada.
    parar_niveis()
    # Força a saída se a parada não funcionar (raro)
    # sys.exit(0)

# --- Função Principal de Execução ---
def main(args=None):
    """
    Ponto de entrada principal do Conductor (Nível 7).
    Inicializa ROS 2 globalmente, inicia os outros níveis e aguarda interrupção.
    """
    global parar_conductor # Acessa o evento global de parada

    print("--- Iniciando Conductor da Telemetria (Nível 7) ---")

    # Configura handlers para sinais de interrupção (Ctrl+C) e terminação
    signal.signal(signal.SIGINT, signal_handler)  # Captura Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler) # Captura sinal de terminação (ex: systemctl stop)

    rclpy_initialized = False # Flag para saber se precisamos chamar shutdown

    try:
        # Inicializa ROS 2 globalmente. Todos os nós (Nível 5 e 6) usarão este contexto.
        print("Nível 7 (Conductor): Inicializando contexto ROS 2 global...")
        rclpy.init(args=args)
        rclpy_initialized = True
        print("Nível 7 (Conductor): Contexto ROS 2 inicializado.")

        # Inicia os Níveis 3, 5 e 6 em suas respectivas threads.
        iniciar_niveis()

        # Mantém a thread principal viva aguardando o sinal de parada.
        print("Nível 7 (Conductor): Sistema iniciado. Aguardando sinal de parada (Ctrl+C ou fechamento da janela)...")
        # Espera indefinidamente até que parar_conductor.set() seja chamado pelo signal_handler
        # ou pela função de fechamento da janela do Nível 6 (que também chama parar_niveis).
        # Adicionamos um loop com sleep para permitir que KeyboardInterrupt funcione melhor em alguns sistemas.
        while not parar_conductor.is_set():
            time.sleep(1) # Verifica a cada segundo

        print("Nível 7 (Conductor): Sinal de parada recebido na thread principal.")

    except KeyboardInterrupt:
        # Captura Ctrl+C diretamente na thread principal (redundância com signal_handler).
        print("\nNível 7 (Conductor): Ctrl+C recebido na thread principal. Iniciando encerramento...")
        if not parar_conductor.is_set(): # Só chama se o signal handler ainda não chamou
             parar_niveis()
    except Exception as e:
        # Captura outros erros inesperados na inicialização ou no loop principal.
        print(f"Nível 7 (Conductor): ERRO FATAL no Conductor: {e}", file=sys.stderr, exc_info=True)
        print("Nível 7 (Conductor): Tentando encerramento de emergência...")
        if not parar_conductor.is_set():
             parar_niveis() # Tenta parar os níveis mesmo em caso de erro.
    finally:
        # Bloco de limpeza final, executado sempre.
        print("Nível 7 (Conductor): Bloco finally - Garantindo encerramento...")

        # Garante que as threads foram aguardadas (caso tenha saído por erro antes de parar_niveis completar)
        for nome, thread in threads:
             if thread.is_alive():
                  print(f"Nível 7 (Conductor): Aguardando {nome} (limpeza final)...")
                  thread.join(timeout=2.0)

        # Encerra o ROS 2 globalmente, se foi inicializado.
        if rclpy_initialized and rclpy.ok():
            print("Nível 7 (Conductor): Encerrando contexto ROS 2 global...")
            rclpy.shutdown()

        print("--- Conductor da Telemetria (Nível 7) Finalizado ---")

# Ponto de entrada padrão para scripts Python.
if __name__ == '__main__':
    # Chama a função principal para iniciar o maestro.
    main()