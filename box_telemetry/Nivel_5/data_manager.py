"""
Sistema de Telimetria E-Racing UNICAMP - Gerenciador de Dados
Módulo responsável pelo processamento, categorização e armazenamento de dados
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
        
        print("📊 Gerenciador de dados inicializado")
    
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
    
    def process_new_data(self, signal_name, value, timestamp, system='GENERAL'):
        """Processa um novo dado de telemetria."""
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
                # Extrai valor numérico
                val_num = float(value.split()[0])
                self.signal_history[signal_name].append(val_num)
                self.time_history[signal_name].append(timestamp)
            except:
                pass
            
            # Adiciona ao sistema específico
            if signal_name not in self.signals_by_system[system]:
                self.signals_by_system[system].append(signal_name)
            
            # Calcula velocidade do IMU se aplicável
            if 'VENTOR_0' in signal_name or 'VENTOR_2' in signal_name:
                self._update_velocity_calculation(signal_name, value, timestamp)
            
            # Adiciona aos dados de exportação se estiver analisando
            if self.current_analysis_mode == 'live':
                self._add_to_export_data(signal_name, value, timestamp, system)
    
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
                # Aceleração X
                self.velocidade_x += val_num * dt
                self.velocidade_x *= 0.995  # Decaimento
            elif 'VENTOR_2' in signal_name:
                # Aceleração Y
                self.velocidade_y += val_num * dt
                self.velocidade_y *= 0.995  # Decaimento
            
            # Calcula velocidade total
            self.velocidade_total = (self.velocidade_x**2 + self.velocidade_y**2)**0.5
            
            self.ultimo_tempo_imu = timestamp
            
        except Exception as e:
            print(f"Erro no cálculo de velocidade: {e}")
    
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
        
        # Verifica se é de um sistema específico
        for system in SYSTEMS:
            if system in signal_upper:
                return system
        
        # Verifica categorias automotivas
        for category, signals in AUTOMOTIVE_SIGNALS.items():
            for signal in signals:
                if signal in signal_upper:
                    return category
        
        # Verifica sinais de suspensão
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
            
            current_time = time.time()
            
            # Calcula médias por sistema
            averages = {}
            
            # BMS Alta (96 células)
            bms_alta_voltages = []
            bms_alta_temps = []
            
            # BMS Baixa (8 células)
            bms_baixa_voltages = []
            bms_baixa_temps = []
            
            # LV_BMS
            lv_bms_voltages = []
            lv_bms_temps = []
            
            # Processa todos os sinais
            for signal_name, values in self.signal_history.items():
                if not values:
                    continue
                
                latest_val = values[-1]
                signal_upper = signal_name.upper()
                
                # BMS Alta (VCELL_0 a VCELL_95, TCELL_0 a TCELL_95)
                if ('VCELL_' in signal_upper or 'TCELL_' in signal_upper) and \
                   not any(x in signal_upper for x in ['LV', 'LOW']):
                    try:
                        num = int(signal_upper.replace('VCELL_', '').replace('TCELL_', '').split()[0])
                        if 0 <= num <= 95:
                            if 'VCELL_' in signal_upper:
                                bms_alta_voltages.append(latest_val)
                            elif 'TCELL_' in signal_upper:
                                bms_alta_temps.append(latest_val)
                    except:
                        pass
                
                # LV_BMS
                elif 'LV' in signal_upper:
                    if 'VCELL_' in signal_upper:
                        lv_bms_voltages.append(latest_val)
                    elif 'TCELL_' in signal_upper:
                        lv_bms_temps.append(latest_val)
            
            # Calcula médias
            if bms_alta_voltages:
                averages['bms_alta_volt'] = sum(bms_alta_voltages) / len(bms_alta_voltages)
            if bms_alta_temps:
                averages['bms_alta_temp'] = sum(bms_alta_temps) / len(bms_alta_temps)
            if lv_bms_voltages:
                averages['lv_bms_volt'] = sum(lv_bms_voltages) / len(lv_bms_voltages)
            if lv_bms_temps:
                averages['lv_bms_temp'] = sum(lv_bms_temps) / len(lv_bms_temps)
            
            # Adiciona ao histórico
            if averages:
                self.time_avg_history.append(current_time)
                
                for metric, value in averages.items():
                    self.signal_avg_history[metric].append(value)
    
    def get_sorted_signals(self):
        """Retorna sinais ordenados por timestamp (mais recentes primeiro)."""
        with self.data_lock:
            return list(self.signal_with_timestamp)
    
    def get_system_signals(self, system):
        """Retorna sinais de um sistema específico."""
        with self.data_lock:
            return self.signals_by_system.get(system, [])
    
    def get_average_data(self, metric):
        """Retorna dados de média para um metric específico."""
        with self.data_lock:
            if metric in self.signal_avg_history:
                return list(self.signal_avg_history[metric])
            return []
    
    def get_time_data(self):
        """Retorna dados de tempo para gráficos."""
        with self.data_lock:
            return list(self.time_avg_history)
    
    def export_to_csv(self, filename=None):
        """Exporta dados para CSV."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"telemetria_eracing_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if self.export_data:
                    writer = csv.DictWriter(csvfile, fieldnames=EXPORT_COLUMNS)
                    writer.writeheader()
                    writer.writerows(self.export_data)
                
            print(MESSAGES['data_exported'].format(filename))
            return filename
        except Exception as e:
            print(MESSAGES['error_export'].format(e))
            return None
    
    def categorize_temperature_sensors(self):
        """Categoriza todos os sensores de temperatura por tipo."""
        temperature_sensors = {
            'BMS_ALTA': [],
            'LV_BMS': [],
            'MOTORES': [],
            'INVERSORES': [],
            'FLUIDOS': [],
            'OUTROS': []
        }
        
        # Obtém todos os sinais de temperatura
        for signal_name in self.latest_signal_values.keys():
            signal_upper = signal_name.upper()
            
            # BMS_ALTA: TCELL_0 a TCELL_95 (96 células)
            if signal_upper.startswith('TCELL_'):
                try:
                    num_part = signal_upper.replace('TCELL_', '').split()[0]
                    if num_part.isdigit():
                        cell_num = int(num_part)
                        if 0 <= cell_num <= 95:
                            temperature_sensors['BMS_ALTA'].append(signal_name)
                            continue
                except:
                    pass
            
            # LV_BMS: LV_TCELL_X (8 células)
            if 'LV_TCELL_' in signal_upper:
                temperature_sensors['LV_BMS'].append(signal_name)
                continue
            
            # MOTORES: sensores de temperatura de motores
            if any(keyword in signal_upper for keyword in ['MOTOR', 'MTR', 'TEMPERATURE_ENGINE']):
                temperature_sensors['MOTORES'].append(signal_name)
                continue
            
            # INVERSORES: sensores de temperatura de inversores
            if any(keyword in signal_upper for keyword in ['INVERTER', 'INV', 'INVTMP']):
                temperature_sensors['INVERSORES'].append(signal_name)
                continue
            
            # FLUIDOS: sensores de temperatura de fluidos
            if any(keyword in signal_upper for keyword in ['FLUID', 'COOLANT', 'COOL', 'COOLANT_TMP']):
                temperature_sensors['FLUIDOS'].append(signal_name)
                continue
            
            # OUTROS: demais sensores de temperatura
            if any(keyword in signal_upper for keyword in ['TEMP', 'TEMPERATURE']):
                temperature_sensors['OUTROS'].append(signal_name)
        
        return temperature_sensors
    
    def get_sensor_display_name(self, signal_name):
        """Converte nomes técnicos em nomes amigáveis para display."""
        signal_upper = signal_name.upper()
        
        # TCELL_0 → C1, TCELL_1 → C2, etc.
        if signal_upper.startswith('TCELL_'):
            try:
                num = int(signal_upper.replace('TCELL_', '').split()[0])
                if 0 <= num <= 95:
                    return f"C{num + 1}"
            except:
                pass
        
        # LV_TCELL_2 → LV C3
        if 'LV_TCELL_' in signal_upper:
            try:
                num = int(signal_upper.replace('LV_TCELL_', '').split()[0])
                return f"LV C{num + 1}"
            except:
                pass
        
        # VCELL_5 → V6 (voltagem)
        if signal_upper.startswith('VCELL_'):
            try:
                num = int(signal_upper.replace('VCELL_', '').split()[0])
                if 0 <= num <= 95:
                    return f"V{num + 1}"
            except:
                pass
        
        # LV_VCELL_1 → LV V2
        if 'LV_VCELL_' in signal_upper:
            try:
                num = int(signal_upper.replace('LV_VCELL_', '').split()[0])
                return f"LV V{num + 1}"
            except:
                pass
        
        # INVERTER_0_TEMP → INV 1
        if 'INVERTER_' in signal_upper and 'TEMP' in signal_upper:
            try:
                num = int(signal_upper.replace('INVERTER_', '').split('_')[0])
                return f"INV {num + 1}"
            except:
                pass
        
        # MOTOR_1_TEMP → MTR 2
        if 'MOTOR_' in signal_upper and 'TEMP' in signal_upper:
            try:
                num = int(signal_upper.replace('MOTOR_', '').split('_')[0])
                return f"MTR {num + 1}"
            except:
                pass
        
        # FLUID_TEMP → FLUID
        if 'FLUID_TEMP' in signal_upper or 'COOLANT_TEMP' in signal_upper:
            return "FLUID"
        
        # Caso não corresponda a nenhum padrão, retorna o nome original
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
                # Extrai valor numérico
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
            
            # Calcula velocidade do IMU se aplicável
            if 'VENTOR_0' in signal_name or 'VENTOR_2' in signal_name:
                self._update_velocity_calculation(signal_name, value, timestamp)
            
            # Adiciona aos dados de exportação se estiver analisando
            if self.current_analysis_mode == 'live':
                self._add_to_export_data(signal_name, value, timestamp, system)
    
    def _auto_detect_system(self, signal_name):
        """Detecta automaticamente o sistema baseado no nome do sinal."""
        signal_upper = signal_name.upper()
        
        # BMS Alta (TCELL_0 a TCELL_95, VCELL_0 a VCELL_95)
        if (signal_upper.startswith('TCELL_') or signal_upper.startswith('VCELL_')) and \
           not any(x in signal_upper for x in ['LV', 'LOW']):
            try:
                num_part = signal_upper.replace('TCELL_', '').replace('VCELL_', '').split()[0]
                if num_part.isdigit() and 0 <= int(num_part) <= 95:
                    return 'BMS'
            except:
                pass
        
        # LV_BMS (LV_TCELL_X, LV_VCELL_X)
        if signal_upper.startswith('LV_TCELL_') or signal_upper.startswith('LV_VCELL_'):
            return 'LV_BMS'
        
        # Motores
        if any(keyword in signal_upper for keyword in ['MOTOR', 'MTR', 'RPM_']):
            return 'MOTOR'
        
        # Inversores
        if any(keyword in signal_upper for keyword in ['INVERTER', 'INV']):
            return 'INVERTER'
        
        # Fluidos
        if any(keyword in signal_upper for keyword in ['FLUID', 'COOLANT', 'COOL']):
            return 'FLUIDOS'
        
        # IMU
        if any(keyword in signal_upper for keyword in ['VENTOR', 'IMU', 'ACCEL']):
            return 'IMU'
        
        # VCU
        if any(keyword in signal_upper for keyword in ['VCU', 'THROTTLE']):
            return 'VCU'
        
        # SUSPENSAO
        if any(keyword in signal_upper for keyword in ['SUSP']):
            return 'SUSPENSAO'
        
        # Por padrão, retorna GENERAL
        return 'GENERAL'
    
    def get_current_metrics(self):
        """Retorna métricas atuais para o dashboard."""
        with self.data_lock:
            metrics = {}
            
            # Calcula voltagem média BMS Alta
            bms_alta_voltages = []
            for signal_name, values in self.signal_history.items():
                if ('VCELL_' in signal_name.upper() and 
                    not any(x in signal_name.upper() for x in ['LV', 'LOW'])):
                    try:
                        num = int(signal_name.upper().replace('VCELL_', '').split()[0])
                        if 0 <= num <= 95 and values:
                            bms_alta_voltages.append(values[-1])
                    except:
                        pass
            
            if bms_alta_voltages:
                metrics['voltage_high'] = sum(bms_alta_voltages) / len(bms_alta_voltages)
            
            # Calcula voltagem média LV_BMS
            lv_bms_voltages = []
            for signal_name, values in self.signal_history.items():
                if 'LV' in signal_name.upper() and 'VCELL_' in signal_name.upper():
                    try:
                        if values:
                            lv_bms_voltages.append(values[-1])
                    except:
                        pass
            
            if lv_bms_voltages:
                metrics['voltage_low'] = sum(lv_bms_voltages) / len(lv_bms_voltages)
            
            # Temperatura média BMS Alta
            bms_alta_temps = []
            for signal_name, values in self.signal_history.items():
                if ('TCELL_' in signal_name.upper() and 
                    not any(x in signal_name.upper() for x in ['LV', 'LOW'])):
                    try:
                        num = int(signal_name.upper().replace('TCELL_', '').split()[0])
                        if 0 <= num <= 95 and values:
                            bms_alta_temps.append(values[-1])
                    except:
                        pass
            
            if bms_alta_temps:
                metrics['temp_high'] = sum(bms_alta_temps) / len(bms_alta_temps)
            
            # Temperatura média LV_BMS
            lv_bms_temps = []
            for signal_name, values in self.signal_history.items():
                if 'LV' in signal_name.upper() and 'TCELL_' in signal_name.upper():
                    try:
                        if values:
                            lv_bms_temps.append(values[-1])
                    except:
                        pass
            
            if lv_bms_temps:
                metrics['temp_low'] = sum(lv_bms_temps) / len(lv_bms_temps)
            
            # Velocidade
            if self.velocidade_total > 0:
                metrics['speed'] = self.velocidade_total
            
            # Potência total
            potencia_total = 0.0
            for signal_name, values in self.signal_history.items():
                if 'ACT_POWER' in signal_name.upper():
                    try:
                        if values:
                            potencia_total += abs(values[-1])
                    except:
                        pass
            
            if potencia_total > 0:
                metrics['power'] = potencia_total
            
            return metrics
