"""
Sistema de Telemetria E-Racing UNICAMP - Gerenciador de Dados Dinamômetro
Módulo focado em dados VCU/Motores para testes no dinamômetro
ATUALIZADO para novo formato: signal,timestamp,id_can,priority,value,unit,min,max
"""

import time
import csv
import threading
from collections import deque, defaultdict
from datetime import datetime
from pathlib import Path
import os
from config_dyno import *

class DynoDataManager:
    """Gerenciador de dados para dinamômetro."""
    
    def __init__(self):
        # Dados em tempo real
        self.latest_signal_values = {}
        self.signal_history = {}
        self.time_history = {}
        
        # Histórico para gráficos
        self.signal_graph_history = defaultdict(lambda: deque(maxlen=GRAPH_HISTORY_POINTS))
        self.time_graph_history = defaultdict(lambda: deque(maxlen=GRAPH_HISTORY_POINTS))
        
        # Valores mínimos e máximos (AGORA vem do CSV)
        self.signal_min = {}
        self.signal_max = {}
        
        # Sinais por bloco VCU
        self.signals_by_block = defaultdict(list)
        
        # Alertas ativos
        self.active_alerts = {}
        
        # Estado do sistema
        self.current_analysis_mode = 'paused'
        self.analysis_start_time = None
        self.analysis_end_time = None
        self.export_data = []
        
        # Controle de threads
        self.data_lock = threading.Lock()
        
        print("📊 Gerenciador de dados (Dinamômetro) inicializado")
    
    def reset_analysis(self):
        """Reseta toda a análise."""
        with self.data_lock:
            self.latest_signal_values.clear()
            self.signal_history.clear()
            self.time_history.clear()
            self.signal_graph_history.clear()
            self.time_graph_history.clear()
            self.signals_by_block.clear()
            self.active_alerts.clear()
            self.export_data.clear()
            self.signal_min.clear()
            self.signal_max.clear()
            
            self.current_analysis_mode = 'paused'
            self.analysis_start_time = None
            self.analysis_end_time = None
        
        print(MESSAGES['analysis_reset'])
    
    def start_analysis(self):
        """Inicia nova análise."""
        with self.data_lock:
            self.current_analysis_mode = 'live'
            self.analysis_start_time = time.time()
            self.analysis_end_time = None
            self.export_data.clear()
        
        print(MESSAGES['analysis_started'])
    
    def pause_analysis(self):
        """Pausa a análise."""
        with self.data_lock:
            if self.current_analysis_mode == 'live':
                self.current_analysis_mode = 'paused'
                self.analysis_end_time = time.time()
        
        print(MESSAGES['analysis_paused'])
    
    def process_new_data(self, signal_name, value, timestamp, id_can='0x000', prioridade=0, unit='', min_val=None, max_val=None):
        """
        Processa um novo dado de telemetria.
        NOVO FORMATO: agora recebe unit, min_val e max_val
        """
        with self.data_lock:
            # Armazena valor mais recente (COM UNIDADE)
            if unit:
                self.latest_signal_values[signal_name] = f"{value} {unit}"
            else:
                self.latest_signal_values[signal_name] = str(value)
            
            # Determina bloco VCU
            block = self._get_signal_block(signal_name)
            
            # Atualiza histórico para gráficos
            if signal_name not in self.signal_history:
                self.signal_history[signal_name] = deque(maxlen=GRAPH_HISTORY_POINTS)
                self.time_history[signal_name] = deque(maxlen=GRAPH_HISTORY_POINTS)
            
            try:
                # Extrai valor numérico
                if isinstance(value, str):
                    val_num = float(value.split()[0]) if ' ' in value else float(value)
                else:
                    val_num = float(value)
                
                self.signal_history[signal_name].append(val_num)
                self.time_history[signal_name].append(timestamp)
                
                # Adiciona ao histórico de gráficos com seu próprio tempo
                self.signal_graph_history[signal_name].append(val_num)
                self.time_graph_history[signal_name].append(timestamp)
                
                # Atualiza min/max (PRIORIZA valores do CSV)
                if min_val is not None and max_val is not None:
                    # Valores vieram do CSV
                    try:
                        min_float = float(min_val)
                        max_float = float(max_val)
                        
                        if signal_name not in self.signal_min:
                            self.signal_min[signal_name] = min_float
                            self.signal_max[signal_name] = max_float
                        else:
                            # Atualiza apenas se o novo valor for mais extremo
                            self.signal_min[signal_name] = min(self.signal_min[signal_name], min_float)
                            self.signal_max[signal_name] = max(self.signal_max[signal_name], max_float)
                    except:
                        pass
                else:
                    # Fallback: calcula localmente
                    if signal_name not in self.signal_min:
                        self.signal_min[signal_name] = val_num
                        self.signal_max[signal_name] = val_num
                    else:
                        self.signal_min[signal_name] = min(self.signal_min[signal_name], val_num)
                        self.signal_max[signal_name] = max(self.signal_max[signal_name], val_num)
                
            except:
                pass
            
            # Adiciona ao bloco específico
            if signal_name not in self.signals_by_block[block]:
                self.signals_by_block[block].append(signal_name)
            
            # Verifica alertas
            self._check_alerts(signal_name, self.latest_signal_values[signal_name])
            
            # Adiciona aos dados de exportação
            if self.current_analysis_mode == 'live':
                self._add_to_export_data(signal_name, value, timestamp, block, id_can, prioridade, unit)
    
    def _get_signal_block(self, signal_name):
        """Determina o bloco VCU do sinal."""
        signal_clean = signal_name.strip()
        
        if signal_clean in SIGNAL_TO_BLOCK:
            return SIGNAL_TO_BLOCK[signal_clean]
        
        return 'OUTROS'
    
    def _check_alerts(self, signal_name, value):
        """Verifica se há alertas para o sinal."""
        if signal_name in CRITICAL_SIGNALS:
            config = CRITICAL_SIGNALS[signal_name]
            
            try:
                # Para sinais booleanos
                if 'TRUE' in value.upper() or 'FALSE' in value.upper():
                    is_active = 'TRUE' in value.upper()
                    
                    # Inverte lógica se necessário (ex: SAFETY_OK deve ser TRUE)
                    if config.get('inverted', False):
                        is_active = not is_active
                    
                    if is_active:
                        self.active_alerts[signal_name] = {
                            'type': config['type'],
                            'msg': config['msg'],
                            'value': value,
                            'timestamp': time.time(),
                            'expires_at': time.time() + ALERT_DISPLAY_TIME
                        }
                    elif signal_name in self.active_alerts:
                        del self.active_alerts[signal_name]
                
                # Para códigos de erro numéricos
                elif 'ERROR CODE' in signal_name:
                    error_val = int(value.split()[0])
                    if error_val != 0:
                        self.active_alerts[signal_name] = {
                            'type': config['type'],
                            'msg': f"{config['msg']}: {error_val}",
                            'value': value,
                            'timestamp': time.time(),
                            'expires_at': time.time() + ALERT_DISPLAY_TIME
                        }
                    elif signal_name in self.active_alerts:
                        del self.active_alerts[signal_name]
                
                # Para status de erro
                elif 'ERRORSTATUS' in signal_name:
                    status_val = int(value.split()[0])
                    if status_val != 0:
                        self.active_alerts[signal_name] = {
                            'type': config['type'],
                            'msg': f"{config['msg']}: Status {status_val}",
                            'value': value,
                            'timestamp': time.time(),
                            'expires_at': time.time() + ALERT_DISPLAY_TIME
                        }
                    elif signal_name in self.active_alerts:
                        del self.active_alerts[signal_name]
                        
            except Exception as e:
                pass
    
    def _add_to_export_data(self, signal_name, value, timestamp, block, id_can, prioridade, unit):
        """Adiciona dados para exportação."""
        try:
            self.export_data.append({
                'timestamp': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f'),
                'signal_name': signal_name,
                'value': value,
                'unit': unit,
                'block': block,
                'id_can': id_can,
                'prioridade': prioridade,
                'min': self.signal_min.get(signal_name, ''),
                'max': self.signal_max.get(signal_name, '')
            })
        except Exception as e:
            print(f"Erro ao adicionar dados para exportação: {e}")
    
    def get_current_metrics(self):
        """Calcula métricas atuais para o dashboard."""
        with self.data_lock:
            metrics = {}
            
            # RPM médio de todos os motores
            rpms = []
            for signal in ['ACT_SPEED A0', 'ACT_SPEED B0', 'ACT_SPEED A13', 'ACT_SPEED B13']:
                if signal in self.latest_signal_values:
                    try:
                        rpm = float(self.latest_signal_values[signal].split()[0])
                        rpms.append(rpm)
                    except:
                        pass
            if rpms:
                metrics['rpm_avg'] = sum(rpms) / len(rpms)
            
            # Torque total
            torques = []
            for signal in ['ACT_TORQUE A0', 'ACT_TORQUE B0', 'ACT_TORQUE A13', 'ACT_TORQUE B13']:
                if signal in self.latest_signal_values:
                    try:
                        torque = float(self.latest_signal_values[signal].split()[0])
                        torques.append(torque)
                    except:
                        pass
            if torques:
                metrics['torque_total'] = sum(torques)
            
            # Potência total
            powers = []
            for signal in ['ACT_POWER A0', 'ACT_POWER B0', 'ACT_POWER A13', 'ACT_POWER B13']:
                if signal in self.latest_signal_values:
                    try:
                        power = float(self.latest_signal_values[signal].split()[0])
                        powers.append(power)
                    except:
                        pass
            if powers:
                metrics['power_total'] = sum(powers)
            
            # Temperatura máxima dos motores
            motor_temps = []
            for signal in ['ACT_MOTORTEMPERATURE A0', 'ACT_MOTORTEMPERATURE B0', 
                          'ACT_MOTORTEMPERATURE A13', 'ACT_MOTORTEMPERATURE B13']:
                if signal in self.latest_signal_values:
                    try:
                        temp = float(self.latest_signal_values[signal].split()[0])
                        motor_temps.append(temp)
                    except:
                        pass
            if motor_temps:
                metrics['temp_motor_max'] = max(motor_temps)
            
            # Temperatura máxima dos inversores
            inv_temps = []
            for signal in ['ACT_DEVICETEMPERATURE M0', 'ACT_DEVICETEMPERATURE M13']:
                if signal in self.latest_signal_values:
                    try:
                        temp = float(self.latest_signal_values[signal].split()[0])
                        inv_temps.append(temp)
                    except:
                        pass
            if inv_temps:
                metrics['temp_inv_max'] = max(inv_temps)
            
            # Tensão DC média
            dc_voltages = []
            for signal in ['ACT_DCBUSVOLTAGE M0', 'ACT_DCBUSVOLTAGE M13']:
                if signal in self.latest_signal_values:
                    try:
                        volt = float(self.latest_signal_values[signal].split()[0])
                        dc_voltages.append(volt)
                    except:
                        pass
            if dc_voltages:
                metrics['dc_voltage_avg'] = sum(dc_voltages) / len(dc_voltages)
            
            # Pedal (APS)
            if 'APS_PERC' in self.latest_signal_values:
                try:
                    metrics['aps_percent'] = float(self.latest_signal_values['APS_PERC'].split()[0])
                except:
                    pass
            
            # RPM individual
            if 'ACT_SPEED A0' in self.latest_signal_values:
                try:
                    metrics['motor_a0_rpm'] = float(self.latest_signal_values['ACT_SPEED A0'].split()[0])
                except:
                    pass
            
            if 'ACT_SPEED B0' in self.latest_signal_values:
                try:
                    metrics['motor_b0_rpm'] = float(self.latest_signal_values['ACT_SPEED B0'].split()[0])
                except:
                    pass
            
            return metrics
    
    def get_block_signals(self, block):
        """Retorna sinais de um bloco específico."""
        with self.data_lock:
            return self.signals_by_block.get(block, [])
    
    def get_signal_data(self, signal_name):
        """Retorna dados de histórico de um sinal."""
        with self.data_lock:
            if signal_name in self.signal_graph_history:
                return list(self.signal_graph_history[signal_name])
            return []
    
    def get_time_data(self, signal_name=None):
        """Retorna dados de tempo."""
        with self.data_lock:
            if signal_name and signal_name in self.time_history:
                return list(self.time_history[signal_name])
            elif self.time_graph_history:
                return list(self.time_graph_history)
            return []
    
    def get_active_alerts(self):
        """Retorna alertas ativos, removendo expirados."""
        with self.data_lock:
            current_time = time.time()
            # Remove alertas expirados
            expired = [k for k, v in self.active_alerts.items() 
                      if v['expires_at'] < current_time]
            for k in expired:
                del self.active_alerts[k]
            
            return dict(self.active_alerts)
    
    def export_to_csv(self, filename=None):
        """Exporta dados para CSV."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"dyno_telemetry_{timestamp}.csv"
        
        try:
            columns = ['timestamp', 'signal_name', 'value', 'unit', 'block', 
                      'id_can', 'prioridade', 'min', 'max']
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if self.export_data:
                    writer = csv.DictWriter(csvfile, fieldnames=columns)
                    writer.writeheader()
                    writer.writerows(self.export_data)
            
            print(MESSAGES['data_exported'].format(filename))
            return filename
        except Exception as e:
            print(MESSAGES['error_export'].format(e))
            return None
    
    def get_signal_min_max(self, signal_name):
        """Retorna min e max de um sinal."""
        with self.data_lock:
            return (
                self.signal_min.get(signal_name, 0),
                self.signal_max.get(signal_name, 0)
            )
    
    def update_graph_time(self):
        """Atualiza timestamp para gráficos."""
        # Não precisa mais de timestamp global, cada sinal tem seu próprio tempo
        pass