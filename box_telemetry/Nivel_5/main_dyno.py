#!/usr/bin/env python3
"""
Sistema de Telemetria E-Racing UNICAMP - Main Dinamômetro
Arquivo principal para telemetria de dinamômetro
"""

import tkinter as tk
import threading
import queue
import time
import os
import csv
from datetime import datetime
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    print("AVISO: watchdog não disponível")
    WATCHDOG_AVAILABLE = False

# Imports dos módulos
try:
    from config_dyno import *
    print("✓ config_dyno carregado")
except ImportError as e:
    print(f"❌ Erro importando config_dyno: {e}")
    # Valores padrão caso config_dyno não esteja disponível
    PADRAO_NOME_ARQUIVO = "*.csv"
    PASTA_LOGS_PROCESSADOS = "."
    MAX_QUEUE_SIZE = 1000
    GRAPH_HISTORY_POINTS = 100

try:
    from data_manager_dyno import DynoDataManager
    print("✓ data_manager_dyno carregado")
except ImportError as e:
    print(f"❌ Erro importando data_manager_dyno: {e}")
    # Fallback para data_manager padrão
    try:
        from data_manager import TelemetryDataManager as DynoDataManager
        print("⚠️ Usando data_manager padrão como fallback")
    except ImportError:
        print("❌ Nenhum data manager disponível")
        raise

try:
    from ui_manager_dyno import DynoTelemetryUI
    print("✓ ui_manager_dyno carregado")
except ImportError as e:
    print(f"❌ Erro importando ui_manager_dyno: {e}")
    # Fallback para ui_manager padrão
    try:
        from ui_manager import TelemetryUI as DynoTelemetryUI
        print("⚠️ Usando ui_manager padrão como fallback")
    except ImportError:
        print("❌ Nenhum ui manager disponível")
        raise

# Importa o monitor inteligente de logs
try:
    from smart_log_monitor_simple import create_smart_log_monitor
    print("✓ smart_log_monitor carregado")
except ImportError as e:
    print(f"⚠️ smart_log_monitor não disponível: {e}")
    def create_smart_log_monitor(data_manager, log_file_path, max_recent_lines=500):
        print("⚠️ smart_log_monitor não disponível - usando método básico")
        return None

# === VARIÁVEIS GLOBAIS ===
tk_root_global = None

# === CLASSE PARA MANEJO DE LOGS ===

class DynoLogHandler(FileSystemEventHandler):
    """Monitora modificações nos arquivos de log."""
    
    def __init__(self, app_queue, data_manager):
        super().__init__()
        self.app_queue = app_queue
        self.data_manager = data_manager
        self.ultimo_processamento_ts = 0
        self.estado_arquivos = {}
        self.arquivo_log_sendo_lido = None
        self.status_callback = None

    def on_modified(self, event):
        global parar_script
        if parar_script.is_set():
            return

        if (not event.is_directory and event.src_path.endswith('.csv') and
                PADRAO_NOME_ARQUIVO.split('*')[0] in os.path.basename(event.src_path)):
            
            agora = time.time()
            if agora - self.ultimo_processamento_ts > 0.05:
                try:
                    tamanho_atual = os.path.getsize(event.src_path)
                    estado_anterior = self.estado_arquivos.get(event.src_path, {'size': 0})
                    tamanho_anterior = estado_anterior['size']

                    if tamanho_atual > tamanho_anterior:
                        try:
                            self.app_queue.put_nowait((event.src_path, tamanho_anterior))
                            self.estado_arquivos[event.src_path] = {'size': tamanho_atual}
                            self.ultimo_processamento_ts = agora
                        except queue.Full:
                            pass

                except FileNotFoundError:
                    if event.src_path in self.estado_arquivos:
                        del self.estado_arquivos[event.src_path]
                except Exception as e:
                    print(f"ERRO no handler: {e}")

    def process_log_update_queue(self):
        """Processa fila de atualizações de log."""
        global parar_script
        novos_dados = False
        
        try:
            while not self.app_queue.empty():
                caminho, offset = self.app_queue.get_nowait()
                
                if self.read_new_log_lines(caminho, offset):
                    novos_dados = True
                
                self.app_queue.task_done()
        
        except queue.Empty:
            pass
        except Exception as e:
            print(f"ERRO: {e}")
        finally:
            return novos_dados

    def read_new_log_lines(self, caminho, offset):
        """Lê novas linhas do arquivo de log."""
        novos_dados = False
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                f.seek(offset)
                reader = csv.reader(f)
                
                for linha in reader:
                    # Formato: NOME_SINAL,timestamp,id_can,prioridade,valor
                    if len(linha) >= 5:
                        nome = linha[0].strip()
                        timestamp_str = linha[1].strip()
                        id_can = linha[2].strip()
                        prioridade = linha[3].strip()
                        valor_str = linha[4].strip()
                        
                        if nome:
                            # Converte timestamp
                            try:
                                timestamp = float(timestamp_str)
                            except:
                                timestamp = time.time()
                            
                            # Processa dados
                            self.data_manager.process_new_data(
                                nome, valor_str, timestamp, id_can, int(prioridade)
                            )
                            
                            novos_dados = True
                            if self.status_callback:
                                self.status_callback(f"Novo dado: {nome}")
                            
                return novos_dados
                        
        except Exception as e:
            print(f"ERRO ao ler {caminho}: {e}")
            return False

# === APLICAÇÃO PRINCIPAL ===

class DynoTelemetryApplication:
    """Aplicação principal para dinamômetro."""
    
    def __init__(self):
        # Componentes principais
        print("📊 Inicializando gerenciador de dados...")
        self.data_manager = DynoDataManager()
        print("✓ Gerenciador de dados inicializado")
        
        print("🖥️ Inicializando interface...")
        self.ui_manager = DynoTelemetryUI(self.data_manager)
        if self.ui_manager is None:
            raise Exception("❌ Falha ao inicializar ui_manager")
        print("✓ Interface inicializada")
        
        self.log_handler = None
        
        # Threading
        self.log_update_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.processing_thread = None
        
        # Monitor inteligente
        self.smart_log_monitor = None
        self.monitoring_active = False
        self.arquivo_log_sendo_lido = None
        
        # Controle
        self.stop_event = threading.Event()
        
        # NÃO cria a interface ainda - isso será feito no método initialize()
        
    def initialize(self):
        """Inicializa todos os componentes."""
        try:
            print("🚀 Iniciando Sistema de Telemetria Dinamômetro E-Racing UNICAMP...")
            
            # Inicializa watchdog se disponível
            self._initialize_watchdog()
            
            # Cria a interface gráfica
            self._create_ui()
            
            # Carrega log existente
            self._load_existing_log()
            
            # Configura handlers
            self._setup_handlers()
            
            print("✓ Sistema inicializado com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro na inicialização: {e}")
            raise
    
    def _create_ui(self):
        """Cria e configura a interface gráfica"""
        try:
            print("🔧 Criando interface gráfica...")
            
            # Apenas inicializa o UI manager (não cria janela ainda)
            # A janela será criada no método run()
            
            # Verifica se o UI manager está inicializado
            if not hasattr(self.ui_manager, 'root'):
                raise Exception("UI manager não foi inicializado corretamente")
            
            print("✓ Interface gráfica criada com sucesso")
            
        except Exception as e:
            print(f"❌ Erro ao criar interface: {e}")
            raise
    

    
    def _initialize_watchdog(self):
        """Inicializa sistema de monitoramento."""
        try:
            if WATCHDOG_AVAILABLE:
                print("📊 Gerenciador de dados (Dinamômetro) inicializado")
                print("🖥️ Interface (Dinamômetro) inicializada")
                print("🚀 Aplicação de telemetria (Dinamômetro) inicializada")
            else:
                print("⚠️ Watchdog não disponível - usando método alternativo")
            
            # Cria diretório se não existir
            if not os.path.isdir(PASTA_LOGS_PROCESSADOS):
                print(f"📁 Criando pasta: {PASTA_LOGS_PROCESSADOS}")
                os.makedirs(PASTA_LOGS_PROCESSADOS, exist_ok=True)
                
        except Exception as e:
            print(f"Erro ao inicializar watchdog: {e}")
    
    def _load_existing_log(self):
        """Carrega log de forma inteligente: histórico recente + monitoramento."""
        try:
            import glob
            
            pattern = os.path.join(PASTA_LOGS_PROCESSADOS, "*.csv")
            logs = glob.glob(pattern)
            
            if logs:
                log_mais_recente = max(logs, key=os.path.getmtime)
                print(f"📂 Carregando log: {os.path.basename(log_mais_recente)}")
                
                # Usa carregamento inteligente
                self.smart_log_monitor = create_smart_log_monitor(
                    self.data_manager, 
                    log_mais_recente, 
                    max_recent_lines=500  # Apenas 500 linhas recentes
                )
                
                # Define callback para status
                def update_status(msg):
                    if hasattr(self, 'ui_manager') and self.ui_manager.status_var:
                        self.ui_manager.status_var.set(msg)
                
                if self.smart_log_monitor:
                    self.smart_log_monitor.set_status_callback(update_status)
                    
                    # Carrega histórico recente
                    if self.smart_log_monitor.load_initial_data():
                        print("✓ Log inteligente carregado!")
                        self.arquivo_log_sendo_lido = log_mais_recente
                        self.monitoring_active = True
                    else:
                        print("⚠️ Não foi possível carregar o log")
                else:
                    print("⚠️ Monitor inteligente não disponível")
            else:
                print("⚠️ Nenhum arquivo de log encontrado")
            
        except Exception as e:
            print(f"⚠️ Erro no carregamento inteligente: {e}")
    
    def check_for_new_data(self):
        """Verifica novos dados de forma eficiente."""
        if hasattr(self, 'smart_log_monitor') and getattr(self, 'monitoring_active', False):
            try:
                return self.smart_log_monitor.check_for_new_data()
            except Exception as e:
                print(f"⚠️ Erro no monitoramento: {e}")
                return False
        return False
    
    def _setup_handlers(self):
        """Configura callbacks."""
        if self.log_handler:
            def update_status(msg):
                if hasattr(self.ui_manager, 'status_var') and self.ui_manager.status_var:
                    self.ui_manager.status_var.set(msg)
            
            self.log_handler.status_callback = update_status
    
    def start_processing_thread(self):
        """Inicia thread de processamento."""
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        print("✓ Thread de processamento iniciada")
    
    def _processing_loop(self):
        """Loop inteligente de processamento."""
        print("🔄 Iniciando loop de processamento inteligente...")
        
        last_check = time.time()
        
        try:
            while getattr(self, 'monitoring_active', True) and not self.stop_event.is_set():
                current_time = time.time()
                
                # Verifica novos dados de forma inteligente (a cada 100ms)
                if current_time - last_check >= 0.1:  # 100ms
                    self.check_for_new_data()
                    last_check = current_time
                
                # Processa fila de eventos da UI (se existir)
                try:
                    if hasattr(self, 'app_queue'):
                        while not self.app_queue.empty():
                            callback, args, kwargs = self.app_queue.get_nowait()
                            try:
                                callback(*args, **kwargs)
                            except Exception as e:
                                print(f"Erro no callback: {e}")
                            finally:
                                self.app_queue.task_done()
                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"Erro na fila: {e}")
                
                # Sleep curto para não sobrecarregar CPU
                time.sleep(0.05)  # 50ms
                
        except Exception as e:
            print(f"ERRO no loop: {e}")
        finally:
            print("🔚 Loop de processamento finalizado")
    
    def run(self):
        """Executa a aplicação."""
        try:
            print("\n" + "="*70)
            print("║")
            print("║    🏎️  E-RACING UNICAMP - DYNO TELEMETRY  ⚡")
            print("║")
            print("║    Sistema de Monitoramento para Dinamômetro")
            print("║    Versão Focada em VCU/Motores")
            print("║")
            print("="*70 + "\n")
            
            # Verifica se ui_manager está inicializado
            if self.ui_manager is None:
                raise Exception("UI manager não foi inicializado")
            
            print(f"🔍 Debug UI Manager: {type(self.ui_manager)}")
            print(f"🔍 Debug Root exists: {self.ui_manager.root is not None}")
            
            if self.ui_manager.root is None:
                print("⚠️ UI root não foi criado - tentando criar...")
                root = self.ui_manager.create_main_window()
                if root is None:
                    raise Exception("Falha ao criar UI root")
                print("✅ UI root criado com sucesso")
            else:
                print(f"✅ UI root já existe: {self.ui_manager.root}")
                print(f"📐 Tamanho: {self.ui_manager.root.geometry()}")
                print(f"📍 Visível: {self.ui_manager.root.winfo_viewable()}")
            
            # Inicializa sistema
            self.initialize()
            
            # Inicia monitoramento
            self.start_processing_thread()
            
            print("✅ Dashboard iniciado com sucesso!")
            print("📊 Aguardando dados de telemetria...")
            print("🎯 Funcionalidades disponíveis:")
            print("   • Métricas principais (9 itens)")
            print("   • Gráficos (RPM, Torque, Potência, Temp, DC Bus, Pedal)")
            print("   • Status dos 4 motores")
            print("   • Detalhes por blocos VCU (14 blocos)")
            print("   • Sistema de alertas críticos")
            print("   • Controles de análise e exportação")
            
            print("="*70)
            
            # Inicia GUI
            print("🚀 Iniciando interface gráfica...")
            global tk_root_global
            tk_root_global = self.ui_manager.root
            
            # Debug da janela antes do mainloop
            print(f"📊 Verificando janela antes do mainloop:")
            print(f"  - Título: {self.ui_manager.root.title()}")
            print(f"  - Tamanho: {self.ui_manager.root.geometry()}")
            print(f"  - Visível: {self.ui_manager.root.winfo_viewable()}")
            print(f"  - Estado: {self.ui_manager.root.state()}")
            
            print("▶️ Executando mainloop()...")
            self.ui_manager.root.mainloop()
            print("🛑 mainloop() finalizado")
            
        except Exception as e:
            print(f"❌ Erro na execução: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.stop_event.set()
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=2.0)

# === FUNÇÃO MAIN ===

def main():
    """Função principal."""
    try:
        app = DynoTelemetryApplication()
        app.run()
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário!")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()