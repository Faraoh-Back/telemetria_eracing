#!/usr/bin/env python3
"""
Sistema de Telimetria E-Racing UNICAMP - Arquivo Principal
Arquivo principal que integra todos os módulos do sistema

Melhorias implementadas:
1. Sistema modular e didático
2. Abas expandidas para gráficos automotivos e suspensão
3. Tabela classificada por ordem de chegada
4. Botões de controle de análise (iniciar/parar/zerar/exportar)
5. Intervalo de tempo aumentado para análise precisa
6. Separação correta BMS e LV_BMS
7. Detalhes por sistema dinâmicos para todas as planilhas
8. Monitor de temperaturas com layout de 15 colunas
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
from config import *
from data_manager import TelemetryDataManager
from ui_manager import TelemetryUI

# === VARIÁVEIS GLOBAIS ===
tk_root_global = None
dashboard_app_global = None
observer_watchdog = None
parar_script = threading.Event()

# === HANDLER DO WATCHDOG ===
class ProcessedLogHandler(FileSystemEventHandler):
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

    def queue_log_update(self, caminho_arquivo, inicio_offset):
        try:
            self.app_queue.put_nowait((caminho_arquivo, inicio_offset))
        except queue.Full:
            pass

    def process_log_update_queue(self):
        """Processa fila de atualizações de log."""
        global parar_script
        novos_dados = False
        
        try:
            while not self.app_queue.empty():
                caminho, offset = self.app_queue.get_nowait()
                
                if self.arquivo_log_sendo_lido != caminho:
                    self.arquivo_log_sendo_lido = caminho
                    # Atualiza status via callback
                    if hasattr(self, 'status_callback'):
                        self.status_callback(f"🟢 LIVE: {os.path.basename(caminho)}")
                
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
                    if len(linha) == 5:
                        nome = linha[0].strip()
                        timestamp_str = linha[1].strip()
                        valor_str = linha[4].strip()
                        
                        if nome:
                            # Converte timestamp
                            try:
                                if '.' in timestamp_str:
                                    timestamp = float(timestamp_str)
                                else:
                                    timestamp = time.time()
                            except:
                                timestamp = time.time()
                            
                            # Determina sistema
                            system = self._determine_system(nome)
                            
                            # Processa dados
                            self.data_manager.process_new_data(nome, valor_str, timestamp, system)
                            
                            novos_dados = True
        
        except Exception as e:
            print(f"ERRO ao ler log: {e}")
        
        return novos_dados

    def _determine_system(self, signal_name):
        """Determina o sistema baseado no nome do sinal."""
        signal_upper = signal_name.upper()
        
        # Mapeamento de sinais para sistemas
        system_mapping = {
            'BMS': 'BMS',
            'LV': 'LV_BMS', 
            'VCU': 'VCU',
            'VENTOR': 'IMU',
            'IMU': 'IMU',
            'FLUID': 'FLUIDOS',
            'MOTOR': 'MOTOR',
            'SUSP': 'SUSPENSAO',
            'PRESSURE': 'PT',
            'TEMP': 'PT',
            'PANEL': 'PAINEL',
            'CURRENT': 'ACD',
            'VOLTAGE': 'ACD'
        }
        
        for keyword, system in system_mapping.items():
            if keyword in signal_upper:
                return system
        
        return 'GENERAL'

        """def _determine_system(self, signal_name):
        Determina o sistema baseado no nome do sinal.
        signal_upper = signal_name.upper()
        
        # BMS Alta (VCELL_0 a VCELL_95, TCELL_0 a TCELL_95)
        if signal_upper.startswith('VCELL_') or signal_upper.startswith('TCELL_'):
            try:
                num_str = signal_upper.replace('VCELL_', '').replace('TCELL_', '').split()[0]
                if num_str.isdigit():
                    num = int(num_str)
                    if 0 <= num <= 95:
                        return 'BMS'
            except:
                pass
        
        # LV_BMS
        if 'LV' in signal_upper or 'LOW' in signal_upper:
            return 'LV_BMS'
        
        # VCU
        if any(k in signal_upper for k in ['VCU', 'THROTTLE', 'TORQUE', 'RPM', 'INVERTER', 'SPEED', 'POWER']):
            return 'VCU'
        
        # IMU
        if any(k in signal_upper for k in ['VENTOR', 'IMU', 'ACCEL', 'GYRO']):
            return 'IMU'
        
        # Fluidos/PT
        if any(k in signal_upper for k in ['FLUID', 'COOLANT', 'TEMP']):
            return 'PT'
        
        # Suspensão
        if 'SUSP' in signal_upper or 'SUSPENSION' in signal_upper:
            return 'SUSPENSAO'
        
        # Motor
        if 'MOTOR' in signal_upper:
            return 'MOTOR'
        
        return 'GENERAL'"""
    
# === APLICAÇÃO PRINCIPAL ===
class TelemetryApplication:
    """Aplicação principal do sistema de telemetria."""
    
    def __init__(self):
        # Componentes principais
        self.data_manager = TelemetryDataManager()
        self.ui_manager = TelemetryUI(self.data_manager)
        self.log_handler = None
        
        # Threading
        self.log_update_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.processing_thread = None
        
        # Estado
        self.arquivo_log_sendo_lido = None
        
        print("🚀 Aplicação de telemetria inicializada")
    
    def initialize(self):
        """Inicializa todos os componentes."""
        try:
            # Inicializa watchdog
            self._initialize_watchdog()
            
            # Carrega log existente
            self._load_existing_log()
            
            # Configura handlers
            self._setup_handlers()
            
            print("✓ Sistema inicializado com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro na inicialização: {e}")
            raise
    
    def _initialize_watchdog(self):
        """Inicializa o sistema de monitoramento de arquivos."""
        try:
            from watchdog.observers import Observer
            
            # Cria diretório se não existir
            if not os.path.isdir(PASTA_LOGS_PROCESSADOS):
                print(f"📁 Criando pasta: {PASTA_LOGS_PROCESSADOS}")
                os.makedirs(PASTA_LOGS_PROCESSADOS, exist_ok=True)
            
            # Cria handler
            self.log_handler = ProcessedLogHandler(self.log_update_queue, self.data_manager)
            
            # Inicia observer
            global observer_watchdog
            observer_watchdog = Observer()
            observer_watchdog.schedule(self.log_handler, path=PASTA_LOGS_PROCESSADOS, recursive=False)
            observer_watchdog.start()
            
            print(f"✓ Monitorando: {PASTA_LOGS_PROCESSADOS}")
            
        except ImportError:
            print("AVISO: Biblioteca 'watchdog' não encontrada. Monitoramento desabilitado.")
        except Exception as e:
            print(f"Erro ao inicializar watchdog: {e}")
    
    def _load_existing_log(self):
        """Carrega o log mais recente ao iniciar."""
        import glob
        try:
            pattern = os.path.join(PASTA_LOGS_PROCESSADOS, "*.csv")
            logs = glob.glob(pattern)
            
            if logs:
                log_mais_recente = max(logs, key=os.path.getmtime)
                print(f"📂 Carregando log existente: {os.path.basename(log_mais_recente)}")
                
                # Lê o log
                if self.log_handler:
                    if self.log_handler.read_new_log_lines(log_mais_recente, 0):
                        print("✓ Log carregado com sucesso!")
                
                self.arquivo_log_sendo_lido = log_mais_recente
                
        except Exception as e:
            print(f"⚠️ Nenhum log encontrado ou erro ao carregar: {e}")
    
    def _setup_handlers(self):
        """Configura callbacks e handlers."""
        if self.log_handler:
            # Callback para atualizar status
            def update_status(msg):
                if self.ui_manager.status_var:
                    self.ui_manager.status_var.set(msg)
            
            self.log_handler.status_callback = update_status
    
    def start_processing_thread(self):
        """Inicia thread de processamento."""
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        print("✓ Thread de processamento iniciada")
    
    def _processing_loop(self):
        """Loop principal de processamento."""
        global parar_script
        
        while not parar_script.is_set():
            try:
                # Processa fila de logs
                if self.log_handler:
                    novos_dados = self.log_handler.process_log_update_queue()
                    
                    if novos_dados:
                        # Calcula médias
                        self.data_manager.calculate_averages()
                        
                        # Atualiza interface
                        if self.ui_manager.root:
                            self.ui_manager.root.after(0, self.ui_manager.update_all_displays)
                
                # Sleep curto para evitar uso excessivo de CPU
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Erro no loop de processamento: {e}")
                time.sleep(1.0)  # Sleep maior em caso de erro
    
    def run(self):
        """Executa a aplicação."""
        try:
            print("\n" + "="*70)
            print("║")
            print("║    🏎️  E-RACING UNICAMP - TELEMETRY DASHBOARD  ⚡")
            print("║")
            print("║    Sistema de Monitoramento em Tempo Real")
            print("║    Versão Modular e Didática")
            print("║")
            print("="*70 + "\n")
            
            # Inicializa componentes
            self.initialize()
            
            # Inicia thread de processamento
            self.start_processing_thread()
            
            # Cria interface
            root = self.ui_manager.create_main_window()
            
            # Configura evento de fechamento
            root.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            print("\n" + "="*70)
            print("✅ Dashboard iniciado com sucesso!")
            print("📊 Aguardando dados de telemetria...")
            print("🎯 Funcionalidades disponíveis:")
            print("   • Gráficos de baterias (BMS Alta/Baixa)")
            print("   • Gráficos automotivos (RPM, Aceleração, Velocidade, Torque, Potência)")
            print("   • Gráficos de suspensão (Percurso total e individual)")
            print("   • Monitor de temperaturas (15 colunas)")
            print("   • Controles de análise (Iniciar/Parar/Zerar/Exportar)")
            print("   • Detalhes dinâmicos por sistema")
            print("="*70 + "\n")
            
            # Inicia loop da interface
            global tk_root_global
            tk_root_global = root
            root.mainloop()
            
        except KeyboardInterrupt:
            print("\n⚠️  Ctrl+C detectado. Encerrando...")
            self._cleanup()
        except Exception as e:
            print(f"❌ ERRO FATAL: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup()
        finally:
            print("\n🛑 Finalizando dashboard...")
            self._cleanup()
    
    def _on_closing(self):
        """Evento de fechamento da aplicação."""
        if tk.messagebox.askokcancel("Sair", "Deseja realmente sair do sistema?"):
            self._cleanup()
            if self.ui_manager.root:
                self.ui_manager.root.destroy()
    
    def _cleanup(self):
        """Limpa recursos e encerra aplicação."""
        global parar_script, observer_watchdog, tk_root_global
        
        # Para processamento
        parar_script.set()
        
        # Para observer
        if observer_watchdog and observer_watchdog.is_alive():
            print("   Parando watchdog...")
            observer_watchdog.stop()
            observer_watchdog.join(timeout=2.0)
        
        # Destrói interface
        if tk_root_global:
            try:
                tk_root_global.destroy()
            except:
                pass
        
        print("✓  Dashboard encerrado.\n")

# === FUNÇÃO PRINCIPAL ===
def main():
    """Função principal de execução."""
    print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║              🏎️  E - R A C I N G   U N I C A M P  ⚡              ║
    ║                                                                   ║
    ║                  TELEMETRY DASHBOARD SYSTEM                       ║
    ║                                                                   ║
    ║           Dashboard profissional para monitoramento               ║
    ║            em tempo real de veículos elétricos de                 ║
    ║                   competição universitária                        ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Verifica dependências
    missing_deps = []
    try:
        import PIL
    except ImportError:
        missing_deps.append("Pillow")
    
    try:
        import matplotlib
    except ImportError:
        missing_deps.append("matplotlib")
    
    try:
        from watchdog.observers import Observer
    except ImportError:
        missing_deps.append("watchdog")
    
    if missing_deps:
        print("\n⚠️  AVISO: Dependências opcionais não encontradas:")
        for dep in missing_deps:
            print(f"   • {dep}")
        print("\n💡 Algumas funcionalidades podem estar desabilitadas.")
        print(f"   Instale com: pip install {' '.join(missing_deps)}\n")
        time.sleep(2)
    
    try:
        # Cria e executa aplicação
        app = TelemetryApplication()
        app.run()
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        input("\nPressione ENTER para sair...")

if __name__ == '__main__':
    main()
