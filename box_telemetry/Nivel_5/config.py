"""
Sistema de Telemetria E-Racing UNICAMP - Configurações
Arquivo de configuração central do sistema
"""

import os
from pathlib import Path

# === CONFIGURAÇÕES DE ARQUIVO ===
PASTA_LOGS_PROCESSADOS = "../Nivel_4/processados/"
PADRAO_NOME_ARQUIVO = "log_processado_*.csv"
LOGO_PATH = "imgs/logo.jpg"

# === CONFIGURAÇÕES DE INTERFACE ===
UI_UPDATE_INTERVAL_MS = 1000
GRAPH_HISTORY_POINTS = 300  # Aumentado para mais precisão
MAX_TIME_WINDOW_SECONDS = 60  # Janela de tempo maior para análise precisa

# === CONFIGURAÇÕES DE JANELA RESPONSIVA ===
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
WINDOW_RESIZABLE = True

# === SISTEMAS DE TELEMETRIA ===
# Lista completa de sistemas suportados
SYSTEMS = [
    'ACD',      # Acumulador
    'BMS',      # Battery Management System (Alta) - 96 células
    'IMU',      # Inertial Measurement Unit
    'LV_BMS',   # Low Voltage BMS (Baixa) - 8 células
    'PAINEL',   # Painel de controle
    'PT',       # Pressure/Temperature sensors
    'VCU',      # Vehicle Control Unit
    'MOTOR',    # Sistemas de motor
    'FLUIDOS',  # Fluidos de arrefecimento
    'SUSPENSAO' # Sistema de suspensão
]

# === CONFIGURAÇÕES DE TEMPERATURA ===
# Limites de temperatura para cores
TEMP_LIMITS = {
    'safe': 50,    # Verde
    'warning': 70, # Amarelo
    'danger': 85   # Vermelho
}

# === SINAIS AUTOMOTIVOS ===
# POTENCIA: Potência calculada como P = V × I, onde V é tensão do motor e I é corrente
AUTOMOTIVE_SIGNALS = {
    'RPM': ['RPM', 'RPM_0', 'RPM_1', 'RPM_2', 'RPM_3'],
    'ACCELERACAO': ['ACCEL', 'THROTTLE', 'THROTTLE_POS'],
    'VELOCIDADE': ['VELOCIDADE', 'SPEED', 'VEL_X', 'VEL_Y'],
    'TORQUE': ['TORQUE', 'TORQUE_0', 'TORQUE_1', 'TORQUE_2', 'TORQUE_3'],
    'POTENCIA': ['POWER', 'ACT_POWER', 'POWER_TOTAL']
}

# === SINAIS DE SUSPENSÃO ===
SUSPENSION_SIGNALS = {
    'LEFT_FRONT': ['SUSP_FRONT_LEFT', 'SUSP_FL'],
    'RIGHT_FRONT': ['SUSP_FRONT_RIGHT', 'SUSP_FR'],
    'LEFT_BACK': ['SUSP_BACK_LEFT', 'SUSP_BL'],
    'RIGHT_BACK': ['SUSP_BACK_RIGHT', 'SUSP_BR'],
    'PERCURSO_TOTAL': ['SUSP_AVG', 'SUSP_TOTAL']
}

# === CONFIGURAÇÕES DE EXPORTAÇÃO ===
EXPORT_COLUMNS = [
    'timestamp',
    'signal_name', 
    'value', 
    'unit', 
    'system',
    'category'
]

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
    'green': '#00ffaa'
}

# === CONFIGURAÇÕES DE MODO DE ANÁLISE ===
ANALYSIS_MODES = {
    'live': 'Em tempo real',
    'paused': 'Pausado',
    'analyzing': 'Analisando'
}

# === CONFIGURAÇÕES DE THREADING ===
MAX_QUEUE_SIZE = 100
DATA_LOCK_TIMEOUT = 5.0

# === CONFIGURAÇÕES DE GRÁFICOS ===
GRAPH_CONFIG = {
    'figure_size': (14, 4),
    'dpi': 80,
    'line_width': 2,
    'marker_size': 4,
    'alpha': 0.8
}

# === CONFIGURAÇÕES DE TEMPERATURA ===
TEMPERATURE_COLUMNS = 20  # Layout: sensor, valor, sensor, valor...

# === CONFIGURAÇÕES DE ABAS DE TEMPERATURA ===
TEMPERATURE_TAB_COLUMNS = 6  # 3 pares nome/valor por linha
TEMPERATURE_TAB_ROWS = 20    # Linhas dinâmicas para sensores

# Configuração das abas de temperatura
TEMPERATURE_TAB_CONFIG = {
    'BMS_ALTA': {
        'icon': '🔋', 
        'title': 'BMS ALTA (96 células)', 
        'sensors': [
            # Padrões para BMS Alta - 96 células
            'BMS_CELL_TEMP_', 'BMS_TEMP_', 'BMS_CELL_', 'TEMP_CELL_',
            'BMS_MODULE_TEMP_', 'BMS_BALANCER_TEMP_', 'BMS_FET_TEMP_'
        ]
    },
    'LV_BMS': {
        'icon': '🔋', 
        'title': 'LV_BMS (8 células)', 
        'sensors': [
            # Padrões para LV BMS - 8 células
            'LV_BMS_TEMP_', 'LV_BMS_CELL_TEMP_', 'LV_TEMP_', 'LV_CELL_TEMP_',
            'LV_BMS_MODULE_TEMP_', 'AUX_BMS_TEMP_', 'AUX_TEMP_'
        ]
    },
    'MOTORES': {
        'icon': '🏎️', 
        'title': 'MOTORES', 
        'sensors': [
            # Padrões para motores
            'MOTOR_TEMP_', 'ENGINE_TEMP_', 'MOT_', 'INV_TEMP_',
            'INVERTER_TEMP_', 'DRIVE_TEMP_', 'MOTOR_COOLING_TEMP_'
        ]
    },
    'INVERSORES': {
        'icon': '⚡', 
        'title': 'INVERSORES', 
        'sensors': [
            # Padrões para inversores
            'INVERTER_TEMP_', 'INV_TEMP_', 'INV_COOLING_TEMP_', 'POWER_STAGE_TEMP_',
            'IGBT_TEMP_', 'GATE_DRIVER_TEMP_', 'DC_LINK_TEMP_'
        ]
    },
    'FLUIDOS': {
        'icon': '🌡️', 
        'title': 'FLUIDOS', 
        'sensors': [
            # Padrões para fluidos
            'COOLANT_TEMP_', 'FLUID_TEMP_', 'COOLING_TEMP_', 'RADIATOR_TEMP_',
            'PUMP_TEMP_', 'HEAT_EXCHANGER_TEMP_', 'BATTERY_COOLING_TEMP_'
        ]
    },
    'OUTROS': {
        'icon': '🌡️', 
        'title': 'OUTROS SENSORES', 
        'sensors': [
            # Padrões para outros sensores
            'TEMP_', 'TEMPERATURE_', 'AMBIENT_TEMP_', 'ENV_TEMP_',
            'PT_TEMP_', 'SENSOR_TEMP_', 'BOARD_TEMP_', 'PCB_TEMP_'
        ]
    }
}

# === MENSAGENS DO SISTEMA ===
MESSAGES = {
    'init': '✓ Dashboard E-Racing inicializado!',
    'loading_log': '📂 Carregando log existente: {}',
    'no_logs': '⚠️ Nenhum log encontrado. Aguardando dados...',
    'error_loading': '❌ Erro ao carregar log: {}',
    'live_mode': '🟢 LIVE: {}',
    'all_systems_ok': '✅ TODOS OS SISTEMAS OPERACIONAIS',
    'analysis_started': '▶️ Análise iniciada',
    'analysis_paused': '⏸️ Análise pausada',
    'analysis_reset': '🔄 Análise resetada',
    'data_exported': '💾 Dados exportados para: {}',
    'error_export': '❌ Erro ao exportar dados: {}'
}
