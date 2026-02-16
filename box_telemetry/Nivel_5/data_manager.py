"""
Sistema de Telimetria E-Racing UNICAMP - Gerenciador de Dados
VERSÃO COM MÉTRICAS CORRIGIDAS - Snapshot após receber todas as células
"""

import time
import csv
import threading
from collections import deque, defaultdict
from datetime import datetime
from pathlib import Path
import os
from config import *

class TelemetryDataManager:
    """Gerenciador principal de dados de telemetria."""
    
    def __init__(self):
        # Dados em tempo real
        self.latest_signal_values = {}
        self.signal_history = {}
        self.time_history = {}
        
        # Dados com timestamp para ordenação
        self.signal_with_timestamp = deque(maxlen=MAX_QUEUE_SIZE)
        
        # Histórico para gráficos
        self.signal_avg_history = defaultdict(lambda: deque(maxlen=GRAPH_HISTORY_POINTS))
        self.time_avg_history = deque(maxlen=GRAPH_HISTORY_POINTS)
        
        # Sinais categorizados por sistema
        self.signals_by_system = defaultdict(list)
        
        # Estado do sistema
        self.current_analysis_mode = 'paused'
        self.analysis_start_time = None
        self.analysis_end_time = None
        self.export_data = []
        
        # Controle de threads
        self.data_lock = threading.Lock()
        
        # Cálculos específicos
        self.velocidade_x = 0.0
        self.velocidade_y = 0.0
        self.velocidade_total = 0.0
        self.ultimo_tempo_imu = None
        
        # === NOVO: Snapshot de células para métricas ===
        self.bms_snapshot = {
            'vcell_values': {},  # {0: 3.96, 1: 3.95, ...}
            'tcell_values': {},  # {0: 28.0, 1: 29.0, ...}
            'vcell_count': 0,
            'tcell_count': 0,
            'last_update': None
        }
        
        self.lv_bms_snapshot = {
            'vcell_values': {},
            'tcell_values': {},
            'vcell_count': 0,
            'tcell_count': 0,
            'last_update': None
        }
        
        # Métricas calculadas (atualizadas após snapshot completo)
        self.current_metrics = {
            'voltage_avg': None,
            'voltage_max': None,
            'voltage_min': None,
            'temp_avg': None,
            'temp_max': None,
            'temp_min': None,
            'speed': 0.0,
            'brake': 0.0
        }
        
        print("📊 Gerenciador de dados inicializado (com métricas snapshot)")
    
    def reset_analysis(self):
        """Reseta toda a análise para começar do zero."""
        with self.data_lock:
            self.latest_signal_values.clear()
            self.signal_history.clear()
            self.time_history.clear()
            self.signal_with_timestamp.clear()
            self.signal_avg_history.clear()
            self.time_avg_history.clear()
            self.signals_by_system.clear()
            self.export_data.clear()
            
            # Reset cálculos
            self.velocidade_x = 0.0
            self.velocidade_y = 0.0
            self.velocidade_total = 0.0
            self.ultimo_tempo_imu = None
            
            # Reset snapshots
            self.bms_snapshot = {'vcell_values': {}, 'tcell_values': {}, 'vcell_count': 0, 'tcell_count': 0, 'last_update': None}
            self.lv_bms_snapshot = {'vcell_values': {}, 'tcell_values': {}, 'vcell_count': 0, 'tcell_count': 0, 'last_update': None}
            self.current_metrics = {'voltage_avg': None, 'voltage_max': None, 'voltage_min': None, 
                                   'temp_avg': None, 'temp_max': None, 'temp_min': None, 'speed': 0.0, 'brake': 0.0}
            
            # Reset estado
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
        """Pausa a análise atual."""
        with self.data_lock:
            if self.current_analysis_mode == 'live':
                self.current_analysis_mode = 'paused'
                self.analysis_end_time = time.time()
        
        print(MESSAGES['analysis_paused'])
    
    def _update_velocity_calculation(self, signal_name, value, timestamp):
        """Atualiza cálculo de velocidade baseado no IMU."""
        try:
            if self.ultimo_tempo_imu is None:
                self.ultimo_tempo_imu = timestamp
                return
            
            dt = timestamp - self.ultimo_tempo_imu
            if dt > 1.0 or dt <= 0:
                self.ultimo_tempo_imu = timestamp
                return
            
            val_num = float(value.split()[0])
            
            if 'VENTOR_0' in signal_name:
                self.velocidade_x += val_num * dt
                self.velocidade_x *= 0.995
            elif 'VENTOR_2' in signal_name:
                self.velocidade_y += val_num * dt
                self.velocidade_y *= 0.995
            
            self.velocidade_total = (self.velocidade_x**2 + self.velocidade_y**2)**0.5
            self.current_metrics['speed'] = self.velocidade_total
            
            self.ultimo_tempo_imu = timestamp
            
        except Exception as e:
            print(f"Erro no cálculo de velocidade: {e}")
    
    def _update_brake_percentage(self, value):
        """Atualiza porcentagem do freio (APS_PERC)."""
        try:
            val_num = float(value.split()[0])
            self.current_metrics['brake'] = val_num
        except:
            pass
    
    def _add_to_export_data(self, signal_name, value, timestamp, system):
        """Adiciona dados para exportação."""
        try:
            val_parts = value.split()
            val = val_parts[0]
            unit = ' '.join(val_parts[1:]) if len(val_parts) > 1 else ''
            
            self.export_data.append({
                'timestamp': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                'signal_name': signal_name,
                'value': val,
                'unit': unit,
                'system': system,
                'category': self._get_signal_category(signal_name)
            })
        except Exception as e:
            print(f"Erro ao adicionar dados para exportação: {e}")
    
    def _get_signal_category(self, signal_name):
        """Determina a categoria do sinal."""
        signal_upper = signal_name.upper()
        
        for system in SYSTEMS:
            if system in signal_upper:
                return system
        
        for category, signals in AUTOMOTIVE_SIGNALS.items():
            for signal in signals:
                if signal in signal_upper:
                    return category
        
        for category, signals in SUSPENSION_SIGNALS.items():
            for signal in signals:
                if signal in signal_upper:
                    return category
        
        return 'GENERAL'
    
    def calculate_averages(self):
        """Calcula médias dos sinais para gráficos."""
        with self.data_lock:
            if not self.signal_history:
                return
            
            # Cálculo de médias de BMS Alta
            bms_alta_volts = []
            bms_alta_temps = []
            
            for signal_name, values in self.signal_history.items():
                signal_upper = signal_name.upper()
                
                if signal_upper.startswith('VCELL_') and not any(x in signal_upper for x in ['LV', 'LOW']):
                    try:
                        num = int(signal_upper.replace('VCELL_', '').split()[0])
                        if 0 <= num <= 95 and values:
                            bms_alta_volts.extend(values)
                    except:
                        pass
                
                if signal_upper.startswith('TCELL_') and not any(x in signal_upper for x in ['LV', 'LOW']):
                    try:
                        num = int(signal_upper.replace('TCELL_', '').split()[0])
                        if 0 <= num <= 95 and values:
                            bms_alta_temps.extend(values)
                    except:
                        pass
            
            if bms_alta_volts:
                avg_volt = sum(bms_alta_volts) / len(bms_alta_volts)
                self.signal_avg_history['bms_alta_volt'].append(avg_volt)
            
            if bms_alta_temps:
                avg_temp = sum(bms_alta_temps) / len(bms_alta_temps)
                self.signal_avg_history['bms_alta_temp'].append(avg_temp)
            
            # Cálculo de médias de LV_BMS
            lv_bms_volts = []
            lv_bms_temps = []
            
            for signal_name, values in self.signal_history.items():
                signal_upper = signal_name.upper()
                
                if 'LV' in signal_upper and 'VCELL_' in signal_upper:
                    if values:
                        lv_bms_volts.extend(values)
                
                if 'LV' in signal_upper and 'TCELL_' in signal_upper:
                    if values:
                        lv_bms_temps.extend(values)
            
            if lv_bms_volts:
                avg_volt = sum(lv_bms_volts) / len(lv_bms_volts)
                self.signal_avg_history['lv_bms_volt'].append(avg_volt)
            
            if lv_bms_temps:
                avg_temp = sum(lv_bms_temps) / len(lv_bms_temps)
                self.signal_avg_history['lv_bms_temp'].append(avg_temp)
            
            if self.time_history:
                latest_time = max([times[-1] for times in self.time_history.values() if times])
                self.time_avg_history.append(latest_time)
    
    def get_average_data(self, key):
        """Retorna dados de média para gráficos."""
        with self.data_lock:
            return list(self.signal_avg_history.get(key, []))
    
    def get_time_data(self):
        """Retorna dados de tempo para gráficos."""
        with self.data_lock:
            return list(self.time_avg_history)
    
    def get_sorted_signals(self):
        """Retorna lista de sinais ordenados por timestamp."""
        with self.data_lock:
            signals_list = []
            for signal_name, value in self.latest_signal_values.items():
                if signal_name in self.time_history and self.time_history[signal_name]:
                    timestamp = self.time_history[signal_name][-1]
                else:
                    timestamp = time.time()
                
                signals_list.append({
                    'signal': signal_name,
                    'value': value,
                    'timestamp': timestamp
                })
            
            signals_list.sort(key=lambda x: x['timestamp'], reverse=True)
            return signals_list
    
    def get_signals_by_system(self, system):
        """Retorna sinais de um sistema específico."""
        with self.data_lock:
            signals = []
            for signal_name in self.signals_by_system.get(system, []):
                if signal_name in self.latest_signal_values:
                    signals.append({
                        'signal': signal_name,
                        'value': self.latest_signal_values[signal_name]
                    })
            return signals
    
    def get_temperature_signals(self):
        """Retorna TODOS os sinais de temperatura."""
        with self.data_lock:
            temp_signals = []
            
            for signal_name, value in self.latest_signal_values.items():
                signal_upper = signal_name.upper()
                
                temp_patterns = [
                    'TCELL_', 'TEMP', 'TEMPERATURE', '_T_',
                ]
                
                is_temp_signal = any(pattern in signal_upper for pattern in temp_patterns)
                
                if is_temp_signal:
                    if signal_name in self.time_history and self.time_history[signal_name]:
                        timestamp = self.time_history[signal_name][-1]
                    else:
                        timestamp = time.time()
                    
                    temp_signals.append({
                        'signal': signal_name,
                        'value': value,
                        'timestamp': timestamp
                    })
            
            temp_signals.sort(key=lambda x: x['signal'])
            return temp_signals
    
    def get_formatted_signal_name(self, signal_name):
        """Formata nome de sinal para exibição mais legível."""
        signal_upper = signal_name.upper()
        
        if signal_upper.startswith('TCELL_'):
            try:
                num = int(signal_upper.replace('TCELL_', '').split()[0])
                if 0 <= num <= 95:
                    return f"T{num + 1}"
            except:
                pass
        
        if signal_upper.startswith('VCELL_'):
            try:
                num = int(signal_upper.replace('VCELL_', '').split()[0])
                if 0 <= num <= 95:
                    return f"V{num + 1}"
            except:
                pass
        
        if 'LV_VCELL_' in signal_upper or 'LV_TCELL_' in signal_upper:
            try:
                parts = signal_upper.split('_')
                if len(parts) >= 3:
                    num = int(parts[2].split()[0])
                    prefix = 'V' if 'VCELL' in signal_upper else 'T'
                    return f"LV {prefix}{num + 1}"
            except:
                pass
        
        if 'MOTORTEMPERATURE' in signal_upper:
            return signal_name.replace('ACT_MOTORTEMPERATURE', 'MTR TEMP')
        
        if 'DEVICETEMPERATURE' in signal_upper:
            return signal_name.replace('ACT_DEVICETEMPERATURE', 'DEV TEMP')
        
        if 'FLUID_TEMP' in signal_upper:
            return signal_name.replace('FLUID_TEMP', 'FLUID')
        
        return signal_name
    
    def process_new_data(self, signal_name, value, timestamp, system='GENERAL'):
        """Processa um novo dado de telemetria com categorização automática."""
        with self.data_lock:
            # Armazena valor mais recente
            self.latest_signal_values[signal_name] = value
            
            # Armazena com timestamp para ordenação
            self.signal_with_timestamp.append({
                'signal': signal_name,
                'value': value,
                'timestamp': timestamp,
                'system': system
            })
            
            # Atualiza histórico para gráficos
            if signal_name not in self.signal_history:
                self.signal_history[signal_name] = deque(maxlen=GRAPH_HISTORY_POINTS)
                self.time_history[signal_name] = deque(maxlen=GRAPH_HISTORY_POINTS)
            
            try:
                val_num = float(value.split()[0])
                self.signal_history[signal_name].append(val_num)
                self.time_history[signal_name].append(timestamp)
            except:
                pass
            
            # Determina sistema automaticamente se não especificado
            if system == 'GENERAL':
                system = self._auto_detect_system(signal_name)
            
            # Adiciona ao sistema específico
            if signal_name not in self.signals_by_system[system]:
                self.signals_by_system[system].append(signal_name)
            
            # === NOVO: Atualiza snapshot de células ===
            self._update_cell_snapshot(signal_name, value, timestamp)
            
            # Calcula velocidade do IMU se aplicável
            if 'VENTOR_0' in signal_name or 'VENTOR_2' in signal_name:
                self._update_velocity_calculation(signal_name, value, timestamp)
            
            # Atualiza freio (APS_PERC)
            if 'APS_PERC' in signal_name.upper():
                self._update_brake_percentage(value)
            
            # Adiciona aos dados de exportação se estiver analisando
            if self.current_analysis_mode == 'live':
                self._add_to_export_data(signal_name, value, timestamp, system)
    
    def _update_cell_snapshot(self, signal_name, value, timestamp):
        """
        Atualiza snapshot de células e recalcula métricas quando receber todas.
        NOVO: Sistema de snapshot para métricas precisas.
        """
        signal_upper = signal_name.upper()
        
        try:
            val_num = float(value.split()[0])
        except:
            return
        
        # BMS Alta - Voltagem (VCELL_0 a VCELL_95)
        if signal_upper.startswith('VCELL_') and not any(x in signal_upper for x in ['LV', 'LOW']):
            try:
                num = int(signal_upper.replace('VCELL_', '').split()[0])
                if 0 <= num <= 95:
                    self.bms_snapshot['vcell_values'][num] = val_num
                    self.bms_snapshot['vcell_count'] = len(self.bms_snapshot['vcell_values'])
                    self.bms_snapshot['last_update'] = timestamp
                    
                    # Se recebeu todas as 96 células, atualiza métricas
                    if self.bms_snapshot['vcell_count'] >= 96:
                        self._calculate_metrics_from_snapshot()
            except:
                pass
        
        # BMS Alta - Temperatura (TCELL_0 a TCELL_95)
        if signal_upper.startswith('TCELL_') and not any(x in signal_upper for x in ['LV', 'LOW']):
            try:
                num = int(signal_upper.replace('TCELL_', '').split()[0])
                if 0 <= num <= 95:
                    self.bms_snapshot['tcell_values'][num] = val_num
                    self.bms_snapshot['tcell_count'] = len(self.bms_snapshot['tcell_values'])
                    self.bms_snapshot['last_update'] = timestamp
                    
                    # Se recebeu todas as 96 células, atualiza métricas
                    if self.bms_snapshot['tcell_count'] >= 96:
                        self._calculate_metrics_from_snapshot()
            except:
                pass
    
    def _calculate_metrics_from_snapshot(self):
        """
        Calcula métricas a partir do snapshot completo das células.
        NOVO: Métricas calculadas após receber todas as células.
        """
        # Voltagens
        if self.bms_snapshot['vcell_values']:
            volts = list(self.bms_snapshot['vcell_values'].values())
            self.current_metrics['voltage_avg'] = sum(volts) / len(volts)
            self.current_metrics['voltage_max'] = max(volts)
            self.current_metrics['voltage_min'] = min(volts)
        
        # Temperaturas
        if self.bms_snapshot['tcell_values']:
            temps = list(self.bms_snapshot['tcell_values'].values())
            self.current_metrics['temp_avg'] = sum(temps) / len(temps)
            self.current_metrics['temp_max'] = max(temps)
            self.current_metrics['temp_min'] = min(temps)
    
    def _auto_detect_system(self, signal_name):
        """Detecta automaticamente o sistema baseado no nome do sinal."""
        signal_upper = signal_name.upper()
        
        if any(keyword in signal_upper for keyword in ['LV_TCELL', 'LV_VCELL', 'LV_BMS', 'LV BMS']):
            return 'LV_BMS'
        
        if signal_upper.startswith('TCELL_') or signal_upper.startswith('VCELL_'):
            try:
                num_part = signal_upper.replace('TCELL_', '').replace('VCELL_', '').split()[0]
                if num_part.isdigit() and 0 <= int(num_part) <= 95:
                    return 'BMS'
            except:
                pass
        
        if signal_upper in ['UNDER_VOLTAGE', 'OVER_VOLTAGE', 'DISCHARGE_OVER_CURRENT', 
                           'CHARGE_OVER_CURRENT', 'CELL_MODULE_OVERHEAT', 'LEAKAGE', 
                           'NO_CELL_COMMUNICATION', 'LOW_VOLTAGE_W', 'HIGH_CURRENT_W',
                           'HIGH_TEMPERATURE_W', 'CELL_OVERHEAT', 'NO_CURRENT_SENSOR',
                           'PACK_UNDER_VOLTAGE', 'VALIDITY']:
            return 'BMS'
        
        if any(keyword in signal_upper for keyword in ['MOTOR', 'MTR', 'RPM']):
            return 'MOTOR'
        
        if any(keyword in signal_upper for keyword in ['INVERTER', 'INV', 'ACT_']):
            return 'MOTOR'
        
        if any(keyword in signal_upper for keyword in ['FLUID', 'COOLANT', 'ARREF']):
            return 'FLUIDOS'
        
        if any(keyword in signal_upper for keyword in ['VENTOR', 'IMU', 'ACCEL', 'GYRO']):
            return 'IMU'
        
        if any(keyword in signal_upper for keyword in ['VCU', 'THROTTLE', 'APPS', 'APS', 'BRAKE', 'SAFETY']):
            return 'VCU'
        
        if any(keyword in signal_upper for keyword in ['SUSP', 'SUSPENSION']):
            return 'SUSPENSAO'
        
        if any(keyword in signal_upper for keyword in ['PRESS', 'PRESSURE']):
            return 'PT'
        
        return 'GENERAL'
    
    def get_current_metrics(self):
        """
        Retorna métricas atuais para o dashboard.
        NOVO: Retorna métricas calculadas por snapshot.
        """
        with self.data_lock:
            return self.current_metrics.copy()
    
    def get_system_alerts(self):
        """
        Retorna lista de alertas ativos do sistema.
        NOVO: Para seção de alertas.
        """
        with self.data_lock:
            alerts = []
            
            # Verifica sinais de erro/alerta do BMS
            alert_signals = [
                ('UNDER_VOLTAGE', 'Subtensão detectada', 'critical'),
                ('OVER_VOLTAGE', 'Sobretensão detectada', 'critical'),
                ('DISCHARGE_OVER_CURRENT', 'Sobre-corrente de descarga', 'critical'),
                ('CHARGE_OVER_CURRENT', 'Sobre-corrente de carga', 'critical'),
                ('CELL_MODULE_OVERHEAT', 'Superaquecimento do módulo', 'critical'),
                ('LEAKAGE', 'Vazamento detectado', 'critical'),
                ('NO_CELL_COMMUNICATION', 'Falha de comunicação', 'warning'),
                ('LOW_VOLTAGE_W', 'Aviso de baixa tensão', 'warning'),
                ('HIGH_CURRENT_W', 'Aviso de alta corrente', 'warning'),
                ('HIGH_TEMPERATURE_W', 'Aviso de alta temperatura', 'warning'),
                ('CELL_OVERHEAT', 'Célula superaquecida', 'critical'),
                ('NO_CURRENT_SENSOR', 'Sensor de corrente falhou', 'warning'),
                ('PACK_UNDER_VOLTAGE', 'Pack com subtensão', 'critical'),
            ]
            
            for signal_name, message, severity in alert_signals:
                if signal_name in self.latest_signal_values:
                    value = self.latest_signal_values[signal_name]
                    # Se o valor é TRUE ou contém TRUE, é um alerta ativo
                    if 'TRUE' in value.upper():
                        alerts.append({
                            'signal': signal_name,
                            'message': message,
                            'severity': severity,
                            'timestamp': time.time()
                        })
            
            # Verifica temperatura crítica
            if self.current_metrics['temp_max'] and self.current_metrics['temp_max'] > 85:
                alerts.append({
                    'signal': 'TEMP_CRITICAL',
                    'message': f"Temperatura crítica: {self.current_metrics['temp_max']:.1f}°C",
                    'severity': 'critical',
                    'timestamp': time.time()
                })
            
            # Verifica voltagem crítica
            if self.current_metrics['voltage_min'] and self.current_metrics['voltage_min'] < 2.5:
                alerts.append({
                    'signal': 'VOLTAGE_CRITICAL',
                    'message': f"Voltagem crítica: {self.current_metrics['voltage_min']:.2f}V",
                    'severity': 'critical',
                    'timestamp': time.time()
                })
            
            return alerts