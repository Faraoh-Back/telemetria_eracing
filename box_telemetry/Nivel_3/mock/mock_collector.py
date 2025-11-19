#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏎️  E-RACING UNICAMP - MOCK DE TELEMETRIA DINAMÔMETRO V3
================================================================

Sistema de simulação de telemetria com formato CORRETO solicitado.
- signal_name em MAIÚSCULAS
- timestamp em Unix timestamp
- value numérico para valores numéricos, TRUE/FALSE para booleanos

Formato de saída: signal_name, timestamp, id_can, priority, value, unit, min, max

Autor: MiniMax Agent
Data: 2025-11-19
================================================================
"""

import csv
import time
import random
import math
from datetime import datetime
from pathlib import Path

class MotorSimulator:
    """Simulador de motor elétrico."""
    
    def __init__(self, motor_id):
        self.motor_id = motor_id
        self.rpm = 0.0
        self.torque = 0.0
        self.temperature = 25.0
        self.current = 0.0
        self.voltage = 400.0
        self.power = 0.0
        
    def update(self, acceleration, brake, dt):
        """Atualiza estado do motor."""
        max_rpm = 8000
        max_torque = 300
        
        if acceleration > 0:
            target_rpm = min(max_rpm, self.rpm + acceleration * 500 * dt)
            target_torque = min(max_torque, self.torque + acceleration * 50 * dt)
        elif brake > 0:
            target_rpm = max(0, self.rpm - brake * 1000 * dt)
            target_torque = max(0, self.torque - brake * 80 * dt)
        else:
            target_rpm = max(0, self.rpm - 200 * dt)
            target_torque = max(0, self.torque - 30 * dt)
        
        self.rpm += (target_rpm - self.rpm) * 0.1
        self.torque += (target_torque - self.torque) * 0.15
        self.power = (self.torque * self.rpm) / 9549
        self.current = (self.power * 1000) / self.voltage if self.voltage > 0 else 0
        
        heat_factor = abs(acceleration) + abs(brake)
        self.temperature += heat_factor * 0.1 * dt
        self.temperature -= (self.temperature - 25) * 0.05 * dt

class MockTelemetriaFormatoCorreto:
    """Sistema com formato de saída correto."""
    
    def __init__(self):
        self.output_file = Path("../../Nivel_4/processados/log_processado_mock.csv")
        self.sample_interval = 0.05  # 50ms = 20 Hz
        self.duration = 300  # 5 minutos
        self.start_time = None
        
        # Motores
        self.motor_a0 = MotorSimulator("A0")
        self.motor_b0 = MotorSimulator("B0")
        self.motor_a13 = MotorSimulator("A13")
        self.motor_b13 = MotorSimulator("B13")
        
        # Sinais reais do VCU
        self.vcu_signals = self._load_vcu_signals()
        self.signal_stats = {}
        
        # Valores simulados em tempo real
        self.system_enable = 1
        
        print("🏎️  E-RACING UNICAMP - MOCK TELEMETRIA FORMATO CORRETO V3")
        print("=" * 70)
        
    def _load_vcu_signals(self):
        """Carrega sinais reais do VCU."""
        signals = {}
        
        # Sinais específicos importantes com dados do VCU CSV
        important_signals = {
            'ACT_SPEED A0': {'can_id': '0x18FF01EA', 'min': -32000, 'max': 33535, 'unit': 'rpm'},
            'ACT_TORQUE A0': {'can_id': '0x18FF01EA', 'min': -6400, 'max': 6707, 'unit': 'Nm'},
            'ACT_DEVICETEMPERATURE A0': {'can_id': '0x18FF01EA', 'min': -40, 'max': 215, 'unit': '°C'},
            'ACT_DCBUSPOWER A0': {'can_id': '0x18FF01EA', 'min': -160, 'max': 167.675, 'unit': 'kW'},
            'ACT_DCBUSVOLTAGE A0': {'can_id': '0x18FF01EA', 'min': 0, 'max': 1020, 'unit': 'V'},
            'ACT_SPEED B0': {'can_id': '0x18FF02EA', 'min': -32000, 'max': 33535, 'unit': 'rpm'},
            'ACT_TORQUE B0': {'can_id': '0x18FF02EA', 'min': -6400, 'max': 6707, 'unit': 'Nm'},
            'ACT_DEVICETEMPERATURE B0': {'can_id': '0x18FF02EA', 'min': -40, 'max': 215, 'unit': '°C'},
            'ACT_SPEED A13': {'can_id': '0x18FF01F7', 'min': -32000, 'max': 33535, 'unit': 'rpm'},
            'ACT_TORQUE A13': {'can_id': '0x18FF01F7', 'min': -6400, 'max': 6707, 'unit': 'Nm'},
            'ACT_DEVICETEMPERATURE A13': {'can_id': '0x18FF01F7', 'min': -40, 'max': 215, 'unit': '°C'},
            'ACT_SPEED B13': {'can_id': '0x18FF01F7', 'min': -32000, 'max': 33535, 'unit': 'rpm'},
            'ACT_TORQUE B13': {'can_id': '0x18FF01F7', 'min': -6400, 'max': 6707, 'unit': 'Nm'},
            'ACT_DEVICETEMPERATURE B13': {'can_id': '0x18FF01F7', 'min': -40, 'max': 215, 'unit': '°C'},
            'SYSTEMENABLE': {'can_id': '0x18FF1080', 'min': 0, 'max': 3, 'unit': 'state'},
            'DEVICESTATE M13': {'can_id': '0x18FF00F7', 'min': 0, 'max': 3, 'unit': 'state'},
        }
        
        # Adiciona sinais
        for key, value in important_signals.items():
            signals[key] = value
        
        print(f"📋 Carregados {len(signals)} sinais do VCU")
        return signals
        
    def setup_output(self):
        """Configura arquivo de saída."""
        try:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.output_file = Path("log_processado_mock.csv")
            print(f"⚠️  Usando diretório atual: {self.output_file}")
        
        self.csv_file = open(self.output_file, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        
        # Cabeçalho
        header = ['signal_name', 'timestamp', 'id_can', 'priority', 'value', 'unit', 'min', 'max']
        self.csv_writer.writerow(header)
        
        print(f"📁 Arquivo de saída: {self.output_file}")
        print(f"⏱️  Intervalo: {self.sample_interval*1000:.0f}ms ({1/self.sample_interval:.0f} Hz)")
        print(f"⏳ Duração: {self.duration}s ({self.duration/60:.1f} min)")
        
    def get_scenario(self, elapsed_time):
        """Retorna cenário baseado no tempo."""
        cycle_time = elapsed_time % 30  # Ciclo de 30 segundos
        
        if cycle_time < 5:
            return 0, 0  # Parado
        elif cycle_time < 10:
            accel = (cycle_time - 5) / 5  # Aceleração progressiva
            return accel, 0
        elif cycle_time < 20:
            return 0.8, 0  # Velocidade constante
        elif cycle_time < 25:
            return 0, (cycle_time - 20) / 5  # Desaceleração
        else:
            return 0, 1  # Frenagem
            
    def update_vehicle_state(self, dt):
        """Atualiza estado do veículo."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            acceleration, brake = self.get_scenario(elapsed)
            
            self.motor_a0.update(acceleration, brake, dt)
            self.motor_b0.update(acceleration, brake, dt)
            self.motor_a13.update(acceleration * 0.5, brake * 0.5, dt)
            self.motor_b13.update(acceleration * 0.5, brake * 0.5, dt)
            
    def generate_alerts(self, elapsed_time):
        """Gera alertas simulados."""
        alerts = []
        
        # APPS range error a cada 30 segundos
        if int(elapsed_time) % 30 == 0 and elapsed_time % 1 < 0.1:
            alerts.append(('APPS_RANGE_ERROR', 0x18FF1515, True))
            
        # System enable/disable (atualiza valor, mas não como alerta)
        if int(elapsed_time) % 10 == 0 and elapsed_time % 1 < 0.1:
            self.system_enable = int(elapsed_time) % 4
            
        return alerts
        
    def format_value(self, signal_name, value):
        """Formata valor conforme tipo do sinal."""
        # Se for valor numérico, retorna como float/int
        if isinstance(value, (int, float)):
            return float(value)
        # Se for alerta/error, retorna TRUE/FALSE
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        # Se for string que representa número
        elif isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
            return float(value)
        # Se for estado/erro, pode ser TRUE/FALSE ou número
        else:
            # Verifica se o sinal sugere boolean
            if any(keyword in signal_name.upper() for keyword in ['ERROR', 'RANGE_ERROR', 'FAULT', 'ENABLE']):
                return "TRUE" if str(value) == "1" or str(value).upper() == "TRUE" else "FALSE"
            else:
                try:
                    return float(value)
                except:
                    return str(value)
        
    def write_sample(self):
        """Escreve amostra no formato correto."""
        if not self.start_time:
            return
            
        elapsed = time.time() - self.start_time
        unix_timestamp = int(time.time() * 1000) / 1000  # Precisão de 3 casas
        
        # Sinais dos motores + estados do sistema
        signals_data = [
            ('ACT_SPEED A0', self.motor_a0.rpm),
            ('ACT_TORQUE A0', self.motor_a0.torque),
            ('ACT_DEVICETEMPERATURE A0', self.motor_a0.temperature),
            ('ACT_DCBUSPOWER A0', self.motor_a0.power),
            ('ACT_SPEED B0', self.motor_b0.rpm),
            ('ACT_TORQUE B0', self.motor_b0.torque),
            ('ACT_DEVICETEMPERATURE B0', self.motor_b0.temperature),
            ('ACT_SPEED A13', self.motor_a13.rpm),
            ('ACT_TORQUE A13', self.motor_a13.torque),
            ('ACT_DEVICETEMPERATURE A13', self.motor_a13.temperature),
            ('ACT_SPEED B13', self.motor_b13.rpm),
            ('ACT_TORQUE B13', self.motor_b13.torque),
            ('ACT_DEVICETEMPERATURE B13', self.motor_b13.temperature),
            ('SYSTEMENABLE', self.system_enable),
        ]
        
        # Processa sinais
        for signal_name, value in signals_data:
            if signal_name in self.vcu_signals:
                signal_data = self.vcu_signals[signal_name]
                can_id = signal_data['can_id']
                unit = signal_data['unit']
                min_val = signal_data['min']
                max_val = signal_data['max']
                
                # Para SYSTEMENABLE e estados, manter como número
                if signal_name == 'SYSTEMENABLE':
                    formatted_value = int(value)  # 1, 2, 3, etc.
                elif isinstance(value, (int, float)):
                    formatted_value = value  # RPM, torque, temperatura, etc.
                else:
                    formatted_value = self.format_value(signal_name, value)
                
                # Escreve: signal_name, timestamp, id_can, priority, value, unit, min, max
                linha = [signal_name, unix_timestamp, can_id, 1, formatted_value, unit, min_val, max_val]
                self.csv_writer.writerow(linha)
                
        # Adiciona alertas
        alerts = self.generate_alerts(elapsed)
        for alert_name, alert_can_id, alert_value in alerts:
            if alert_name in self.vcu_signals:
                alert_data = self.vcu_signals[alert_name]
                unit = alert_data['unit']
                min_val = alert_data['min']
                max_val = alert_data['max']
                
                # Formata valor do alerta (TRUE/FALSE para erros)
                formatted_value = self.format_value(alert_name, alert_value)
                
                linha = [alert_name, unix_timestamp, f"0x{alert_can_id:08X}", 1, formatted_value, unit, min_val, max_val]
                self.csv_writer.writerow(linha)
                
        self.csv_file.flush()
        self.samples_written += 1
        
    def print_status(self):
        """Imprime status."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            rate = self.samples_written / elapsed if elapsed > 0 else 0
            print(f"\r⏱️  Tempo: {elapsed:.1f}s | 📦 Amostras: {self.samples_written} | 📊 Taxa: {rate:.1f}/s", end='', flush=True)
    
    def print_final_summary(self):
        """Resumo final."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            rate = self.samples_written / elapsed if elapsed > 0 else 0
            
            print(f"\n\n{'='*70}")
            print("✅ SIMULAÇÃO FINALIZADA - FORMATO CORRETO")
            print("=" * 70)
            print(f"⏱️  Tempo total: {elapsed:.1f}s")
            print(f"📦 Amostras escritas: {self.samples_written}")
            print(f"📊 Taxa média: {rate:.1f} amostras/s")
            print(f"📁 Arquivo: {self.output_file}")
            
            if self.output_file.exists():
                print(f"💾 Tamanho: {self.output_file.stat().st_size / 1024:.1f} KB")
                
            print(f"📈 Sinais do VCU: {len(self.vcu_signals)}")
            print(f"📈 Sinais rastreados: {len(self.signal_stats)}")
            print("\n🚀 Execute o dashboard:")
            print("   cd ../../Nivel_5")
            print("   python run_dyno.py")
            print("=" * 70)
            
    def run(self):
        """Executa simulação."""
        self.setup_output()
        
        print("\n🎮 Cenários:")
        print("   • 0-5s: Parado")
        print("   • 5-10s: Aceleração progressiva")
        print("   • 10-20s: Velocidade constante")
        print("   • 20-25s: Desaceleração")
        print("   • 25-30s: Frenagem")
        print("   (Ciclo se repete)")
        
        print("\n✅ FORMATO CORRETO:")
        print("   • signal_name em MAIÚSCULAS")
        print("   • timestamp em Unix timestamp")
        print("   • value numérico para RPM/torque, TRUE/FALSE para erros")
        
        print("\n▶️  Iniciando simulação...")
        print()
        
        self.start_time = time.time()
        self.samples_written = 0
        last_status_time = 0
        
        try:
            while time.time() - self.start_time < self.duration:
                current_time = time.time()
                
                dt = current_time - (self.start_time + self.samples_written * self.sample_interval)
                self.update_vehicle_state(dt)
                
                self.write_sample()
                
                if current_time - last_status_time >= 2:
                    self.print_status()
                    last_status_time = current_time
                
                next_sample_time = self.start_time + (self.samples_written + 1) * self.sample_interval
                sleep_time = max(0, next_sample_time - current_time)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrompido pelo usuário")
            
        finally:
            self.print_final_summary()
            self.csv_file.close()

if __name__ == "__main__":
    print("🚀 Iniciando mock com formato correto...")
    mock = MockTelemetriaFormatoCorreto()
    mock.run()