#!/usr/bin/env python3
"""
Sistema de Telemetria E-Racing UNICAMP - Mock de Dados MELHORADO
Gera dados simulados COMPLETOS com todos os sensores e alertas
"""

import csv
import time
import random
import math
import os
from datetime import datetime

# === CONFIGURAÇÕES ===
ARQUIVO_SAIDA = "../../Nivel_4/processados/log_processado_mock.csv"
INTERVALO_ESCRITA = 1  # 50ms entre escritas (20 Hz)
DURACAO_TESTE = 300  # 5 minutos de teste
VERBOSE = True

# === IDs CAN DO VCU ===
IDS_CAN = {
    'master_control': '0x18FF1080',
    'mobile_0': '0x18FF00EA',
    'mobile_13': '0x18FF00F7',
    'motor_a0_actual': '0x18FF01EA',
    'motor_b0_actual': '0x18FF02EA',
    'motor_a13_actual': '0x18FF01F7',
    'motor_b13_actual': '0x18FF02F7',
    'motor_a0_setpoint': '0x18FF1180',
    'motor_b0_setpoint': '0x18FF1280',
    'motor_a13_setpoint': '0x18FFE180',
    'motor_b13_setpoint': '0x18FFE280',
    'vcu_data_out': '0x18FF1515',
    'control_mobile_0': '0x18FF0DEA',
    'control_mobile_13': '0x18FF0EF7',
}

# Dicionário para rastrear min/max de cada sinal
signal_stats = {}

def update_signal_stats(signal_name, value):
    """Atualiza estatísticas de min/max de um sinal."""
    if signal_name not in signal_stats:
        signal_stats[signal_name] = {'min': value, 'max': value}
    else:
        signal_stats[signal_name]['min'] = min(signal_stats[signal_name]['min'], value)
        signal_stats[signal_name]['max'] = max(signal_stats[signal_name]['max'], value)

# === CLASSES DE SIMULAÇÃO ===

class MotorSimulator:
    """Simula comportamento de um motor elétrico."""
    
    def __init__(self, motor_id, lado):
        self.motor_id = motor_id
        self.lado = lado
        
        # Estado do motor
        self.rpm = 0.0
        self.rpm_setpoint = 0.0
        self.torque = 0.0
        self.power = 0.0
        self.temperature = 25.0
        
        # Estados - AGORA VARIAM
        self.inverter_status = 0
        self.inverter_ready = 0
        self.error_status = 0
        
        # Limites
        self.rpm_max = 65000
        self.torque_max = 13000
        self.temp_max = 150
        
        # Variáveis para simular estados
        self.time_since_start = 0
        self.error_timer = 0
        
    def update(self, throttle, dt, vcu_state):
        """Atualiza estado do motor."""
        self.time_since_start += dt
        
        # Simula estado do inversor baseado no tempo e VCU
        if vcu_state >= 3:  # Ready
            self.inverter_status = 1
            self.inverter_ready = 1
        else:
            self.inverter_status = 0
            self.inverter_ready = 0
        
        # Simula erros ocasionais (mais frequentes para testar)
        self.error_timer += dt
        if self.error_timer > 45:  # A cada 45 segundos
            if random.random() < 0.3:  # 30% de chance
                self.error_status = random.choice([1, 2, 3, 4])
                print(f"⚠️ ERRO simulado em {self.motor_id}: código {self.error_status}")
            else:
                self.error_status = 0
            self.error_timer = 0
        
        # Calcula RPM alvo baseado no throttle
        if self.inverter_status == 1:
            self.rpm_setpoint = throttle * self.rpm_max
        else:
            self.rpm_setpoint = 0
        
        # Simula inércia do motor
        rpm_diff = self.rpm_setpoint - self.rpm
        self.rpm += rpm_diff * 0.3 * dt
        
        # Adiciona ruído
        self.rpm += random.uniform(-100, 100)
        self.rpm = max(0, min(self.rpm, self.rpm_max))
        
        # Calcula torque (curva realista)
        if self.rpm > 0:
            torque_factor = 1.0 - (self.rpm / self.rpm_max) * 0.5
            self.torque = throttle * self.torque_max * torque_factor
            self.torque += random.uniform(-200, 200)
            self.torque = max(0, min(self.torque, self.torque_max))
        else:
            self.torque = 0
        
        # Calcula potência
        omega = (self.rpm * 2 * math.pi) / 60
        self.power = (self.torque * omega) / 1000
        self.power = max(0, min(self.power, 350))
        
        # Simula temperatura
        heating = (self.power / 350) * 2.0 * dt
        cooling = (self.temperature - 25) * 0.01 * dt
        self.temperature += heating - cooling
        self.temperature += random.uniform(-0.5, 0.5)
        self.temperature = max(20, min(self.temperature, self.temp_max))
    
    def get_signals(self, timestamp, id_can_actual):
        """Retorna sinais do motor."""
        suffix = self.motor_id
        
        # Atualiza estatísticas
        update_signal_stats(f'ACT_SPEED {suffix}', self.rpm)
        update_signal_stats(f'ACT_TORQUE {suffix}', self.torque)
        update_signal_stats(f'ACT_POWER {suffix}', self.power)
        update_signal_stats(f'ACT_MOTORTEMPERATURE {suffix}', self.temperature)
        
        signals = [
            (f'ACT_INVERTERSTATUS {suffix}', timestamp, id_can_actual, 1, f'{self.inverter_status} state'),
            (f'ACT_INVERTERREADY {suffix}', timestamp, id_can_actual, 1, f'{self.inverter_ready} state'),
            (f'ACT_ERRORSTATUS {suffix}', timestamp, id_can_actual, 1, f'{self.error_status} state'),
            (f'ACT_SPEED {suffix}', timestamp, id_can_actual, 1, f'{int(self.rpm)} rpm'),
            (f'ACT_TORQUE {suffix}', timestamp, id_can_actual, 1, f'{self.torque:.2f} Nm'),
            (f'ACT_POWER {suffix}', timestamp, id_can_actual, 1, f'{self.power:.2f} kw'),
            (f'ACT_MOTORTEMPERATURE {suffix}', timestamp, id_can_actual, 1, f'{int(self.temperature)} °C'),
        ]
        
        return signals

class InverterSimulator:
    """Simula comportamento de um inversor."""
    
    def __init__(self, inverter_id):
        self.inverter_id = inverter_id
        
        # Estado - AGORA VARIA
        self.device_state = 1
        self.error_lamp = 0
        self.device_number = 0 if inverter_id == 'M0' else 13
        self.clamp15_status = 1
        self.precharged = 1
        self.error_code = 0
        
        # Medições
        self.dc_voltage = 450.0
        self.dc_power = 0.0
        self.temperature = 30.0
        
        # Controle de estados
        self.state_timer = 0
        self.error_timer = 0
        
    def update(self, motor_power, dt, vcu_state):
        """Atualiza estado do inversor."""
        self.state_timer += dt
        self.error_timer += dt
        
        # Simula transição de estados baseado no VCU
        if vcu_state == 0:  # LV
            self.device_state = 0
            self.precharged = 0
        elif vcu_state == 1:  # HV
            self.device_state = 1
            self.precharged = 1
        elif vcu_state == 2:  # Transition
            self.device_state = 1
            self.precharged = 1
        elif vcu_state == 3:  # Ready
            self.device_state = 2  # Running
            self.precharged = 1
        
        # Simula clamp15 variando
        if self.state_timer > 20:
            self.clamp15_status = random.choice([0, 1, 1, 1])  # Mais frequente em 1
            self.state_timer = 0
        
        # Simula erros mais frequentes (para testar alertas)
        if self.error_timer > 60:  # A cada 60 segundos
            if random.random() < 0.4:  # 40% de chance
                self.error_code = random.randint(1000, 9999)
                self.error_lamp = 1
                print(f"⚠️ ERRO simulado no inversor {self.inverter_id}: código {self.error_code}")
            else:
                self.error_code = 0
                self.error_lamp = 0
            self.error_timer = 0
        
        # Potência DC
        self.dc_power = motor_power + random.uniform(-5, 5)
        
        # Tensão DC varia
        self.dc_voltage = 450 + random.uniform(-20, 20)
        
        # Temperatura
        heating = (self.dc_power / 200) * 1.0 * dt
        cooling = (self.temperature - 30) * 0.02 * dt
        self.temperature += heating - cooling
        self.temperature += random.uniform(-0.3, 0.3)
        self.temperature = max(25, min(self.temperature, 120))
        
        # Atualiza estatísticas
        update_signal_stats(f'ACT_DCBUSVOLTAGE {self.inverter_id}', self.dc_voltage)
        update_signal_stats(f'ACT_DCBUSPOWER {self.inverter_id}', self.dc_power)
        update_signal_stats(f'ACT_DEVICETEMPERATURE {self.inverter_id}', self.temperature)
    
    def get_signals(self, timestamp, id_can):
        """Retorna sinais do inversor."""
        suffix = self.inverter_id
        
        signals = [
            (f'DEVICESTATE {suffix}', timestamp, id_can, 1, f'{self.device_state} state'),
            (f'ERRORLAMP {suffix}', timestamp, id_can, 1, f'{self.error_lamp} state'),
            (f'DEVICENUMBER {suffix}', timestamp, id_can, 1, f'{self.device_number} state'),
            (f'CLAMP15_STATUS {suffix}', timestamp, id_can, 1, f'{self.clamp15_status} state'),
            (f'PRECHARGED {suffix}', timestamp, id_can, 1, f'{self.precharged} state'),
            (f'STATUS_ BIT_FLEX_IN_OUT_SIGNAL1 {suffix}', timestamp, id_can, 1, f'{random.randint(0,3)} state'),
            (f'STATUS_ BIT_FLEX_IN_OUT_SIGNAL2 {suffix}', timestamp, id_can, 1, f'{random.randint(0,3)} state'),
            (f'ERROR CODE {"" if suffix == "M0" else " "}{suffix}', timestamp, id_can, 1, f'{self.error_code} state'),
            (f'ACT_DCBUSVOLTAGE {suffix}', timestamp, id_can, 1, f'{self.dc_voltage:.2f} V'),
            (f'ACT_DCBUSPOWER {suffix}', timestamp, id_can, 1, f'{self.dc_power:.2f} kw'),
            (f'ACT_DEVICETEMPERATURE {suffix}', timestamp, id_can, 1, f'{int(self.temperature)} °C'),
        ]
        
        return signals

class VCUSimulator:
    """Simula VCU (Vehicle Control Unit)."""
    
    def __init__(self):
        # Estado VCU - AGORA VARIA
        self.system_enable = 1
        self.clamp15_can = 2
        self.dc_link_voltage = 450.0
        self.voltage_precharge_demand = 400.0
        
        # Pedal e controles
        self.aps_perc = 0.0
        self.apps_range_error = False
        self.safety_ok = True
        self.brake = 0
        self.vcu_state = 3
        
        # Perfil de aceleração
        self.time_elapsed = 0
        self.scenario = 'idle'
        
        # Timers para simular estados variáveis
        self.state_change_timer = 0
        self.error_timer = 0
        
    def update(self, dt):
        """Atualiza estado do VCU."""
        self.time_elapsed += dt
        self.state_change_timer += dt
        self.error_timer += dt
        
        # Simula transições de estado do VCU (mais dinâmico)
        if self.state_change_timer > 40:  # A cada 40 segundos
            # Ciclo: LV -> HV -> Transition -> Ready
            cycle_pos = int(self.time_elapsed / 40) % 4
            self.vcu_state = cycle_pos
            self.state_change_timer = 0
            print(f"🔄 VCU mudou para estado {self.vcu_state}")
        
        # Simula system_enable variando
        if int(self.time_elapsed) % 35 == 0 and dt < 0.1:
            self.system_enable = random.choice([0, 1, 1, 1])  # Mais frequente em 1
        
        # Simula clamp15_can variando
        if int(self.time_elapsed) % 25 == 0 and dt < 0.1:
            self.clamp15_can = random.choice([0, 1, 2, 2, 2])
        
        # Simula erros de APPS (MAIS FREQUENTE para testar alertas)
        if self.error_timer > 30:  # A cada 30 segundos
            if random.random() < 0.5:  # 50% de chance
                self.apps_range_error = True
                print(f"⚠️ APPS_RANGE_ERROR ativado!")
            else:
                self.apps_range_error = False
            self.error_timer = 0
        
        # Simula SAFETY_OK variando
        if int(self.time_elapsed) % 50 == 0 and dt < 0.1:
            if random.random() < 0.3:  # 30% de chance de falhar
                self.safety_ok = False
                print(f"⚠️ SAFETY_OK = FALSE!")
            else:
                self.safety_ok = True
        
        # Tensões variam
        self.dc_link_voltage = 450 + random.uniform(-30, 30)
        self.voltage_precharge_demand = 400 + random.uniform(-20, 20)
        
        # Cenários realistas de teste
        cycle_time = self.time_elapsed % 30
        
        if cycle_time < 5:
            self.scenario = 'idle'
            target_throttle = 0
            self.brake = 1
        elif cycle_time < 10:
            self.scenario = 'accelerating'
            progress = (cycle_time - 5) / 5
            target_throttle = progress * 80
            self.brake = 0
        elif cycle_time < 20:
            self.scenario = 'constant'
            target_throttle = 70 + random.uniform(-10, 10)
            self.brake = 0
        elif cycle_time < 25:
            self.scenario = 'decelerating'
            progress = (cycle_time - 20) / 5
            target_throttle = 70 * (1 - progress)
            self.brake = 0
        else:
            self.scenario = 'braking'
            target_throttle = 0
            self.brake = 1
        
        # Suaviza transição do pedal
        throttle_diff = target_throttle - self.aps_perc
        self.aps_perc += throttle_diff * 0.2
        self.aps_perc = max(0, min(100, self.aps_perc))
        
        # Atualiza estatísticas
        update_signal_stats('APS_PERC', self.aps_perc)
        update_signal_stats('SETP_DCLINKVOLTAGE', self.dc_link_voltage)
        update_signal_stats('VOLTAGEPRECHARGEDEMAND', self.voltage_precharge_demand)
    
    def get_throttle(self):
        """Retorna throttle normalizado (0-1)."""
        return self.aps_perc / 100.0
    
    def get_signals(self, timestamp):
        """Retorna sinais do VCU."""
        signals = []
        
        # Master control
        signals.extend([
            ('SYSTEMENABLE', timestamp, IDS_CAN['master_control'], 1, self.system_enable, 'state'),
            ('CLAMP15_CAN', timestamp, IDS_CAN['master_control'], 1, self.clamp15_can, 'state'),
            ('SETP_DCLINKVOLTAGE', timestamp, IDS_CAN['master_control'], 1, f'{self.dc_link_voltage:.2f}', 'V'),
            ('VOLTAGEPRECHARGEDEMAND', timestamp, IDS_CAN['master_control'], 1, f'{self.voltage_precharge_demand:.2f}', 'V'),
        ])
        
        # VCU Data Out
        signals.extend([
            ('APPS_RANGE_ERROR', timestamp, IDS_CAN['vcu_data_out'], 1, 'TRUE' if self.apps_range_error else 'FALSE', 'state'),
            ('SAFETY_OK', timestamp, IDS_CAN['vcu_data_out'], 1, 'TRUE' if self.safety_ok else 'FALSE', 'state'),
            ('BRAKE', timestamp, IDS_CAN['vcu_data_out'], 1, self.brake, 'state'),
            ('VCU_STATE', timestamp, IDS_CAN['vcu_data_out'], 1, self.vcu_state, 'state'),
            ('APS_PERC', timestamp, IDS_CAN['vcu_data_out'], 1, f'{self.aps_perc:.2f}', '%'),
        ])
        
        return signals

# === SIMULADOR PRINCIPAL ===

class TelemetryMock:
    """Simulador principal de telemetria."""
    
    def __init__(self):
        # Componentes
        self.vcu = VCUSimulator()
        
        # 4 motores
        self.motor_a0 = MotorSimulator('A0', 'direita')
        self.motor_b0 = MotorSimulator('B0', 'direita')
        self.motor_a13 = MotorSimulator('A13', 'esquerda')
        self.motor_b13 = MotorSimulator('B13', 'esquerda')
        
        # 2 inversores
        self.inverter_m0 = InverterSimulator('M0')
        self.inverter_m13 = InverterSimulator('M13')
        
        # Arquivo CSV
        self.csv_file = None
        self.csv_writer = None
        
        # Estatísticas
        self.samples_written = 0
        self.start_time = None
    
    def initialize(self):
        """Inicializa o mock."""
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
        
        # Abre arquivo CSV
        self.csv_file = open(ARQUIVO_SAIDA, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        
        print("="*70)
        print("🏎️  E-RACING UNICAMP - MOCK DE TELEMETRIA DINAMÔMETRO")
        print("="*70)
        print(f"\n📁 Arquivo de saída: {ARQUIVO_SAIDA}")
        print(f"⏱️  Intervalo: {INTERVALO_ESCRITA*1000:.0f}ms ({1/INTERVALO_ESCRITA:.0f} Hz)")
        print(f"⏳ Duração: {DURACAO_TESTE}s ({DURACAO_TESTE/60:.1f} min)")
        print("\n🎮 Cenários simulados:")
        print("   • 0-5s: Parado (freio)")
        print("   • 5-10s: Aceleração progressiva")
        print("   • 10-20s: Velocidade constante (~70%)")
        print("   • 20-25s: Desaceleração")
        print("   • 25-30s: Frenagem")
        print("   (Ciclo se repete)")
        print("\n⚠️  ALERTAS SIMULADOS:")
        print("   • Erros de motores a cada ~45s")
        print("   • Erros de inversores a cada ~60s")
        print("   • APPS_RANGE_ERROR a cada ~30s")
        print("   • SAFETY_OK falhas ocasionais")
        print("   • Estados do VCU variando\n")
        
        self.start_time = time.time()
        
        # Liga motores
        self.motor_a0.inverter_status = 1
        self.motor_a0.inverter_ready = 1
        self.motor_b0.inverter_status = 1
        self.motor_b0.inverter_ready = 1
        self.motor_a13.inverter_status = 1
        self.motor_a13.inverter_ready = 1
        self.motor_b13.inverter_status = 1
        self.motor_b13.inverter_ready = 1
    
    def update(self, dt):
        """Atualiza simulação."""
        # Atualiza VCU
        self.vcu.update(dt)
        throttle = self.vcu.get_throttle()
        vcu_state = self.vcu.vcu_state
        
        # Atualiza motores
        self.motor_a0.update(throttle, dt, vcu_state)
        self.motor_b0.update(throttle, dt, vcu_state)
        self.motor_a13.update(throttle, dt, vcu_state)
        self.motor_b13.update(throttle, dt, vcu_state)
        
        # Atualiza inversores
        power_direita = self.motor_a0.power + self.motor_b0.power
        power_esquerda = self.motor_a13.power + self.motor_b13.power
        
        self.inverter_m0.update(power_direita, dt, vcu_state)
        self.inverter_m13.update(power_esquerda, dt, vcu_state)
    
    def write_sample(self):
        """Escreve uma amostra de dados no NOVO FORMATO."""
        timestamp = time.time()
        
        all_signals = []
        
        # VCU
        all_signals.extend(self.vcu.get_signals(timestamp))
        
        # Motores
        all_signals.extend(self.motor_a0.get_signals(timestamp, IDS_CAN['motor_a0_actual']))
        all_signals.extend(self.motor_b0.get_signals(timestamp, IDS_CAN['motor_b0_actual']))
        all_signals.extend(self.motor_a13.get_signals(timestamp, IDS_CAN['motor_a13_actual']))
        all_signals.extend(self.motor_b13.get_signals(timestamp, IDS_CAN['motor_b13_actual']))
        
        # Inversores
        all_signals.extend(self.inverter_m0.get_signals(timestamp, IDS_CAN['mobile_0']))
        all_signals.extend(self.inverter_m13.get_signals(timestamp, IDS_CAN['mobile_13']))
        
        # Setpoints
        for motor, id_can in [(self.motor_a0, IDS_CAN['motor_a0_setpoint']),
                               (self.motor_b0, IDS_CAN['motor_b0_setpoint']),
                               (self.motor_a13, IDS_CAN['motor_a13_setpoint']),
                               (self.motor_b13, IDS_CAN['motor_b13_setpoint'])]:
            suffix = motor.motor_id
            tolerance = 450 + random.uniform(-50, 50)
            update_signal_stats(f'SETP_DCLINKTOLERANCE {suffix}', tolerance)
            
            all_signals.extend([
                (f'CTRLDCU {suffix}', timestamp, id_can, 1, motor.inverter_status, 'state'),
                (f'SETP_DCLINKTOLERANCE {suffix}', timestamp, id_can, 1, f'{tolerance:.2f}', 'V'),
                (f'SETP_MOTPOWER {suffix}', timestamp, id_can, 1, random.randint(50, 250), '%'),
                (f'SETP_GENPOWER {suffix}', timestamp, id_can, 1, random.randint(0, 100), '%'),
                (f'SETP_SPEED {suffix}', timestamp, id_can, 1, int(motor.rpm_setpoint), 'rpm'),
                (f'SETP_TORQUE {suffix}', timestamp, id_can, 1, f'{motor.torque:.2f}', 'Nm'),
            ])
        
        # Control setpoints
        all_signals.extend([
            ('TORQUE 0A', timestamp, IDS_CAN['control_mobile_0'], 1, f'{self.motor_a0.torque:.2f}', 'Nm'),
            ('RPM 0A', timestamp, IDS_CAN['control_mobile_0'], 1, f'{self.motor_a0.rpm:.2f}', 'RPM'),
            ('TORQUE 0B', timestamp, IDS_CAN['control_mobile_0'], 1, f'{self.motor_b0.torque:.2f}', 'Nm'),
            ('RPM 0B', timestamp, IDS_CAN['control_mobile_0'], 1, f'{self.motor_b0.rpm:.2f}', 'RPM'),
            
            ('TORQUE 13A', timestamp, IDS_CAN['control_mobile_13'], 1, f'{self.motor_a13.torque:.2f}', 'Nm'),
            ('RPM 13A', timestamp, IDS_CAN['control_mobile_13'], 1, f'{self.motor_a13.rpm:.2f}', 'RPM'),
            ('TORQUE 13B', timestamp, IDS_CAN['control_mobile_13'], 1, f'{self.motor_b13.torque:.2f}', 'Nm'),
            ('RPM 13B', timestamp, IDS_CAN['control_mobile_13'], 1, f'{self.motor_b13.rpm:.2f}', 'RPM'),
        ])
        
        # Escreve no CSV no NOVO FORMATO
        for signal_data in all_signals:
            # Lidar com tuplas de 5 ou 6 elementos
            if len(signal_data) == 5:
                signal_name, ts, id_can, priority, value = signal_data
                unit = 'unit'  # Valor padrão
            elif len(signal_data) == 6:
                signal_name, ts, id_can, priority, value, unit = signal_data
            else:
                # Para tuplas com mais elementos, usar os primeiros 6
                signal_name, ts, id_can, priority, value, unit = signal_data[:6]
            
            # Pega min/max das estatísticas
            if signal_name in signal_stats:
                min_val = signal_stats[signal_name]['min']
                max_val = signal_stats[signal_name]['max']
            else:
                # Tenta converter valor para número para inicializar
                try:
                    if isinstance(value, str):
                        num_val = float(value.split()[0]) if ' ' in value else float(value)
                    else:
                        num_val = float(value)
                    min_val = num_val
                    max_val = num_val
                except:
                    min_val = value
                    max_val = value
            
            # Formato: signal,timestamp,id_can,priority,value,unit,min,max
            linha = [signal_name, ts, id_can, priority, value, unit, min_val, max_val]
            self.csv_writer.writerow(linha)
        
        self.csv_file.flush()
        self.samples_written += 1
    
    def print_status(self):
        """Imprime status da simulação."""
        elapsed = time.time() - self.start_time
        
        print(f"\r⏱️  {elapsed:.1f}s | "
              f"📦 {self.samples_written} amostras | "
              f"🎮 APS: {self.vcu.aps_perc:.1f}% | "
              f"🔄 RPM: A0={self.motor_a0.rpm:.0f} B0={self.motor_b0.rpm:.0f} | "
              f"🌡️  Temp: {self.motor_a0.temperature:.0f}°C | "
              f"⚠️  Erros: M0={self.inverter_m0.error_code} M13={self.inverter_m13.error_code}", 
              end='', flush=True)
    
    def run(self):
        """Executa simulação."""
        self.initialize()
        
        print("▶️  Iniciando simulação...\n")
        
        try:
            last_time = time.time()
            next_status_print = time.time()
            
            while (time.time() - self.start_time) < DURACAO_TESTE:
                current_time = time.time()
                dt = current_time - last_time
                
                # Atualiza simulação
                self.update(dt)
                
                # Escreve amostra
                self.write_sample()
                
                # Imprime status a cada segundo
                if VERBOSE and current_time >= next_status_print:
                    self.print_status()
                    next_status_print = current_time + 1.0
                
                last_time = current_time
                
                # Sleep para manter taxa de atualização
                time.sleep(INTERVALO_ESCRITA)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrompido pelo usuário!")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Finaliza simulação."""
        if self.csv_file:
            self.csv_file.close()
        
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        print("\n\n" + "="*70)
        print("✅ SIMULAÇÃO FINALIZADA")
        print("="*70)
        print(f"⏱️  Tempo total: {elapsed:.1f}s")
        print(f"📦 Amostras escritas: {self.samples_written}")
        print(f"📊 Taxa média: {self.samples_written/elapsed:.1f} amostras/s")
        print(f"📁 Arquivo: {ARQUIVO_SAIDA}")
        print(f"💾 Tamanho: {os.path.getsize(ARQUIVO_SAIDA)/1024:.1f} KB")
        print(f"\n📈 Estatísticas de sinais rastreados: {len(signal_stats)}")
        print("\n🚀 Agora você pode executar o dashboard:")
        print("   cd ../../Nivel_5")
        print("   python run_dyno.py")
        print("="*70 + "\n")

# === MAIN ===

if __name__ == '__main__':
    print("\n")
    mock = TelemetryMock()
    mock.run()