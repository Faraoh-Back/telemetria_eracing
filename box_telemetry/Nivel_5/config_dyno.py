"""
Sistema de Telemetria E-Racing UNICAMP - Configurações Dinamômetro
Configuração específica para testes no dinamômetro
"""

import os
from pathlib import Path

# === CONFIGURAÇÕES DE ARQUIVO ===
PASTA_LOGS_PROCESSADOS = "../Nivel_4/processados/"
PADRAO_NOME_ARQUIVO = "log_processado_*.csv"
LOGO_PATH = "imgs/logo.jpg"

# === CONFIGURAÇÕES DE INTERFACE ===
UI_UPDATE_INTERVAL_MS = 100  # Mais rápido para dinamômetro
GRAPH_HISTORY_POINTS = 3000  # Muitos pontos para scroll horizontal
MAX_TIME_WINDOW_SECONDS = 300  # 5 minutos de histórico
ALERT_DISPLAY_TIME = 10  # Segundos que alerta fica visível
MAX_ALERTS_VISIBLE = 10  # Máximo de alertas na tela

# === CONFIGURAÇÕES DE JANELA ===
WINDOW_MIN_WIDTH = 1400
WINDOW_MIN_HEIGHT = 900
WINDOW_RESIZABLE = True

# === BLOCOS VCU (do CSV CAN Description) ===
VCU_BLOCKS = [
    'Status of the master control',
    'Device status of the MOBILE 0',
    'Device status of the MOBILE 13',
    'Actual values from motor A 0',
    'Actual values from motor B 0',
    'Actual values from motor A 13',
    'Actual values from motor B 13',
    'Setpoints for motor A 0',
    'Setpoints for motor B 0',
    'Setpoints for motor A 13',
    'Setpoints for motor B 13',
    'VCU_DATA_OUT',
    'SETPOINTS CONTROL MOBILE 0',
    'SETPOINTS CONTROL MOBILE 13'
]

# === MAPEAMENTO DE SINAIS PARA BLOCOS ===
SIGNAL_TO_BLOCK = {
    # Status of the master control
    'SYSTEMENABLE': 'Status of the master control',
    'CLAMP15_CAN': 'Status of the master control',
    'SETP_DCLINKVOLTAGE': 'Status of the master control',
    'VOLTAGEPRECHARGEDEMAND': 'Status of the master control',
    
    # Device status MOBILE 0
    'DEVICESTATE M0': 'Device status of the MOBILE 0',
    'ERRORLAMP M0': 'Device status of the MOBILE 0',
    'DEVICENUMBER M0': 'Device status of the MOBILE 0',
    'CLAMP15_STATUS M0': 'Device status of the MOBILE 0',
    'PRECHARGED M0': 'Device status of the MOBILE 0',
    'ERROR CODE M0': 'Device status of the MOBILE 0',
    'ACT_DCBUSVOLTAGE M0': 'Device status of the MOBILE 0',
    'ACT_DCBUSPOWER M0': 'Device status of the MOBILE 0',
    'ACT_DEVICETEMPERATURE M0': 'Device status of the MOBILE 0',
    
    # Device status MOBILE 13
    'DEVICESTATE M13': 'Device status of the MOBILE 13',
    'ERRORLAMP M13': 'Device status of the MOBILE 13',
    'DEVICENUMBER M13': 'Device status of the MOBILE 13',
    'CLAMP15_STATUS M13': 'Device status of the MOBILE 13',
    'PRECHARGED M13': 'Device status of the MOBILE 13',
    'ERROR CODE  M13': 'Device status of the MOBILE 13',
    'ACT_DCBUSVOLTAGE M13': 'Device status of the MOBILE 13',
    'ACT_DCBUSPOWER M13': 'Device status of the MOBILE 13',
    'ACT_DEVICETEMPERATURE M13': 'Device status of the MOBILE 13',
    
    # Actual values motor A 0
    'ACT_INVERTERSTATUS A0': 'Actual values from motor A 0',
    'ACT_INVERTERREADY A0': 'Actual values from motor A 0',
    'ACT_ERRORSTATUS A0': 'Actual values from motor A 0',
    'ACT_SPEED A0': 'Actual values from motor A 0',
    'ACT_TORQUE A0': 'Actual values from motor A 0',
    'ACT_POWER A0': 'Actual values from motor A 0',
    'ACT_MOTORTEMPERATURE A0': 'Actual values from motor A 0',
    
    # Actual values motor B 0
    'ACT_INVERTERSTATUS B0': 'Actual values from motor B 0',
    'ACT_INVERTERREADY B0': 'Actual values from motor B 0',
    'ACT_ERRORSTATUS B0': 'Actual values from motor B 0',
    'ACT_SPEED B0': 'Actual values from motor B 0',
    'ACT_TORQUE B0': 'Actual values from motor B 0',
    'ACT_POWER B0': 'Actual values from motor B 0',
    'ACT_MOTORTEMPERATURE B0': 'Actual values from motor B 0',
    
    # Actual values motor A 13
    'ACT_INVERTERSTATUS A13': 'Actual values from motor A 13',
    'ACT_INVERTERREADY A13': 'Actual values from motor A 13',
    'ACT_ERRORSTATUS A13': 'Actual values from motor A 13',
    'ACT_SPEED A13': 'Actual values from motor A 13',
    'ACT_TORQUE A13': 'Actual values from motor A 13',
    'ACT_POWER A13': 'Actual values from motor A 13',
    'ACT_MOTORTEMPERATURE A13': 'Actual values from motor A 13',
    
    # Actual values motor B 13
    'ACT_INVERTERSTATUS B13': 'Actual values from motor B 13',
    'ACT_INVERTERREADY B13': 'Actual values from motor B 13',
    'ACT_ERRORSTATUS B13': 'Actual values from motor B 13',
    'ACT_SPEED B13': 'Actual values from motor B 13',
    'ACT_TORQUE B13': 'Actual values from motor B 13',
    'ACT_POWER B13': 'Actual values from motor B 13',
    'ACT_MOTORTEMPERATURE B13': 'Actual values from motor B 13',
    
    # Setpoints motor A 0
    'CTRLDCU A0': 'Setpoints for motor A 0',
    'SETP_DCLINKTOLERANCE A0': 'Setpoints for motor A 0',
    'SETP_MOTPOWER A0': 'Setpoints for motor A 0',
    'SETP_GENPOWER A0': 'Setpoints for motor A 0',
    'SETP_SPEED A0': 'Setpoints for motor A 0',
    'SETP_TORQUE A0': 'Setpoints for motor A 0',
    
    # Setpoints motor B 0
    'CTRLDCU B0': 'Setpoints for motor B 0',
    'SETP_DCLINKTOLERANCE B0': 'Setpoints for motor B 0',
    'SETP_MOTPOWER B0': 'Setpoints for motor B 0',
    'SETP_GENPOWER B0': 'Setpoints for motor B 0',
    'SETP_SPEED B0': 'Setpoints for motor B 0',
    'SETP_TORQUE B0': 'Setpoints for motor B 0',
    
    # Setpoints motor A 13
    'CTRLDCU A13': 'Setpoints for motor A 13',
    'SETP_DCLINKTOLERANCE A13': 'Setpoints for motor A 13',
    'SETP_MOTPOWER A13': 'Setpoints for motor A 13',
    'SETP_GENPOWER A13': 'Setpoints for motor A 13',
    'SETP_SPEED A13': 'Setpoints for motor A 13',
    'SETP_TORQUE A13': 'Setpoints for motor A 13',
    
    # Setpoints motor B 13
    'CTRLDCU B13': 'Setpoints for motor B 13',
    'SETP_DCLINKTOLERANCE B13': 'Setpoints for motor B 13',
    'SETP_MOTPOWER B13': 'Setpoints for motor B 13',
    'SETP_GENPOWER B13': 'Setpoints for motor B 13',
    'SETP_SPEED B13': 'Setpoints for motor B 13',
    'SETP_TORQUE B13': 'Setpoints for motor B 13',
    
    # VCU_DATA_OUT
    'APPS_RANGE_ERROR': 'VCU_DATA_OUT',
    'SAFETY_OK': 'VCU_DATA_OUT',
    'BRAKE': 'VCU_DATA_OUT',
    'VCU_STATE': 'VCU_DATA_OUT',
    'APS_PERC': 'VCU_DATA_OUT',
    
    # SETPOINTS CONTROL MOBILE 0
    'TORQUE 0A': 'SETPOINTS CONTROL MOBILE 0',
    'RPM 0A': 'SETPOINTS CONTROL MOBILE 0',
    'TORQUE 0B': 'SETPOINTS CONTROL MOBILE 0',
    'RPM 0B': 'SETPOINTS CONTROL MOBILE 0',
    
    # SETPOINTS CONTROL MOBILE 13
    'TORQUE 13A': 'SETPOINTS CONTROL MOBILE 13',
    'RPM 13A': 'SETPOINTS CONTROL MOBILE 13',
    'TORQUE 13B': 'SETPOINTS CONTROL MOBILE 13',
    'RPM 13B': 'SETPOINTS CONTROL MOBILE 13',
}

# === MÉTRICAS PRINCIPAIS (9 itens) ===
KEY_METRICS = [
    ('rpm_avg', 'RPM MÉDIO', 'rpm'),
    ('torque_total', 'TORQUE TOTAL', 'Nm'),
    ('power_total', 'POTÊNCIA TOTAL', 'kW'),
    ('temp_motor_max', 'TEMP. MOTOR MAX', '°C'),
    ('temp_inv_max', 'TEMP. INV MAX', '°C'),
    ('dc_voltage_avg', 'TENSÃO DC MÉDIA', 'V'),
    ('aps_percent', 'PEDAL (APS)', '%'),
    ('motor_a0_rpm', 'RPM MOTOR A0', 'rpm'),
    ('motor_b0_rpm', 'RPM MOTOR B0', 'rpm'),
]

# === SINAIS CRÍTICOS PARA ALERTAS ===
CRITICAL_SIGNALS = {
    'APPS_RANGE_ERROR': {'type': 'error', 'msg': 'Erro no range do pedal (APPS)'},
    'SAFETY_OK': {'type': 'warning', 'msg': 'Sistema de segurança', 'inverted': True},
    'ERROR CODE M0': {'type': 'error', 'msg': 'Erro no inversor M0'},
    'ERROR CODE  M13': {'type': 'error', 'msg': 'Erro no inversor M13'},
    'ACT_ERRORSTATUS A0': {'type': 'error', 'msg': 'Erro no motor A0'},
    'ACT_ERRORSTATUS B0': {'type': 'error', 'msg': 'Erro no motor B0'},
    'ACT_ERRORSTATUS A13': {'type': 'error', 'msg': 'Erro no motor A13'},
    'ACT_ERRORSTATUS B13': {'type': 'error', 'msg': 'Erro no motor B13'},
}

# === LIMITES DE TEMPERATURA ===
TEMP_LIMITS = {
    'motor_safe': 80,      # Verde
    'motor_warning': 100,  # Amarelo
    'motor_danger': 120,   # Vermelho
    'inv_safe': 70,
    'inv_warning': 85,
    'inv_danger': 100,
}

# === CONFIGURAÇÕES DE GRÁFICOS ===
GRAPH_CONFIG = {
    'figure_size': (12, 3.5),
    'dpi': 90,
    'line_width': 2,
    'marker_size': 3,
    'alpha': 0.85
}

# === CORES DO SISTEMA ===
COLORS = {
    'bg_dark': '#0a0a0a',
    'bg_medium': '#1a1a1a',
    'bg_light': '#2a2a2a',
    'orange': '#ff6600',
    'orange_dark': '#cc5200',
    'white': '#ffffff',
    'gray': '#808080',
    'gray_light': '#b0b0b0',
    'warning': '#ff3333',
    'safe': '#00ff00',
    'yellow': '#ffcc00',
    'blue': '#00aaff',
    'green': '#00ffaa',
    'red': '#ff0000',
    'purple': '#aa00ff',
    'cyan': '#00ffff',
}

# === CORES POR MOTOR ===
MOTOR_COLORS = {
    'A0': COLORS['orange'],      # Motor A frente direita
    'B0': COLORS['blue'],         # Motor B traseira direita
    'A13': COLORS['green'],       # Motor A frente esquerda
    'B13': COLORS['purple'],      # Motor B traseira esquerda
}

# === CONFIGURAÇÕES DE EXPORTAÇÃO ===
EXPORT_COLUMNS = [
    'timestamp',
    'signal_name', 
    'value', 
    'unit', 
    'block',
    'id_can',
    'prioridade'
]

# === MENSAGENS DO SISTEMA ===
MESSAGES = {
    'init': '✓ Dashboard Dinamômetro inicializado!',
    'loading_log': '📂 Carregando log: {}',
    'no_logs': '⚠️ Nenhum log encontrado. Aguardando dados...',
    'error_loading': '❌ Erro ao carregar log: {}',
    'live_mode': '🟢 LIVE: {}',
    'all_systems_ok': '✅ TODOS OS MOTORES OPERACIONAIS',
    'analysis_started': '▶️ Análise iniciada',
    'analysis_paused': '⏸️ Análise pausada',
    'analysis_reset': '🔄 Análise resetada',
    'data_exported': '💾 Dados exportados para: {}',
    'error_export': '❌ Erro ao exportar dados: {}'
}

# === NOMES AMIGÁVEIS PARA DISPLAY ===
FRIENDLY_NAMES = {
    # Motores dianteiros
    'A0': 'MTR A0 (FD)',   # Frente Direita
    'A13': 'MTR A13 (FE)', # Frente Esquerda
    # Motores traseiros
    'B0': 'MTR B0 (TD)',   # Traseira Direita
    'B13': 'MTR B13 (TE)', # Traseira Esquerda
    # Inversores
    'M0': 'INV M0 (DIR)',
    'M13': 'INV M13 (ESQ)',
}

# === THREADING ===
MAX_QUEUE_SIZE = 100
DATA_LOCK_TIMEOUT = 5.0