"""
Sistema de Telimetria E-Racing UNICAMP - Gerenciador de Gráficos
Módulo responsável por todas as visualizações gráficas do dashboard
VERSÃO CORRIGIDA: Gráficos automotivos com dados reais da VCU
"""

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import threading
from config import *
import tkinter as tk


class GraphManager:
    """Gerenciador principal de gráficos e visualizações."""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.figures = {}
        self.axes = {}
        self.canvases = {}
        
        # Configuração de cores para sistemas
        self.system_colors = {
            'BMS_ALTA': COLORS['orange'],
            'LV_BMS': COLORS['green'],
            'VCU': COLORS['blue'],
            'IMU': COLORS['yellow'],
            'MOTOR': COLORS['warning'],
            'FLUIDOS': COLORS['gray_light']
        }
        
        # Cores para motores individuais
        self.motor_colors = {
            'A0': '#FF6600',   # Laranja (Direita Dianteiro)
            'B0': '#00FF00',   # Verde (Direita Traseiro)
            'A13': '#0088FF',  # Azul (Esquerda Dianteiro)
            'B13': '#FFCC00'   # Amarelo (Esquerda Traseiro)
        }
        
        print("📈 Gerenciador de gráficos inicializado")
    
    def create_battery_graphs(self, parent_frame):
        """Cria os gráficos de baterias (voltagens e temperaturas)."""
        graphs_container = parent_frame
        
        # === GRÁFICO 1: VOLTAGENS ===
        volt_frame = self._create_graph_frame(graphs_container, "Média Voltagem Células")
        self.create_battery_voltage_graph(volt_frame)
        
        # === GRÁFICO 2: TEMPERATURAS ===
        temp_frame = self._create_graph_frame(graphs_container, "Média Temperatura Células")
        self.create_battery_temperature_graph(temp_frame)
    
    def create_battery_voltage_graph(self, parent):
        """Cria gráfico específico de voltagens das baterias."""
        # Figure
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Voltagem (V)', 'Tempo (s)')
        
        # Armazena referências
        self.figures['battery_voltage'] = fig
        self.axes['battery_voltage'] = ax
        
        # Canvas - igual aos gráficos automotivos (sem scroll)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['battery_voltage'] = canvas
    
    def create_battery_temperature_graph(self, parent):
        """Cria gráfico específico de temperaturas das baterias."""
        # Figure
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Temperatura (°C)', 'Tempo (s)')
        
        # Armazena referências
        self.figures['battery_temperature'] = fig
        self.axes['battery_temperature'] = ax
        
        # Canvas - igual aos gráficos automotivos (sem scroll)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['battery_temperature'] = canvas
    
    def create_automotive_graphs(self, parent_notebook):
        """
        Cria gráficos para dados automotivos.
        CORRIGIDO: Usa dados reais da VCU (act_Speed, act_Torque, act_Power, APS_PERC)
        """
        # Aba RPM (4 motores)
        rpm_tab = self._create_graph_tab(parent_notebook, "RPM")
        self.create_rpm_graph(rpm_tab)
        
        # Aba Torque (4 motores + setpoints)
        torque_tab = self._create_graph_tab(parent_notebook, "Torque")
        self.create_torque_graph(torque_tab)
        
        # Aba Potência (4 motores)
        power_tab = self._create_graph_tab(parent_notebook, "Potência")
        self.create_power_graph(power_tab)
        
        # Aba Acelerador (APS_PERC)
        throttle_tab = self._create_graph_tab(parent_notebook, "Acelerador")
        self.create_throttle_graph(throttle_tab)

        # Aba Aceleração (vetor_linear_acc_x, vetor_linear_acc_y)
        acceleration_tab = self._create_graph_tab(parent_notebook, "Aceleração")
        self.create_acceleration_graph(acceleration_tab)

        # Aba Velocidade (vetor_linear_speed_x)
        speed_tab = self._create_graph_tab(parent_notebook, "Velocidade")
        self.create_speed_graph(speed_tab)
    
    def create_suspension_graphs(self, parent_notebook):
        """Cria gráficos para dados de suspensão."""
        # Aba Percurso Total
        total_tab = self._create_graph_tab(parent_notebook, "Percurso Total")
        self.create_suspension_total_graph(total_tab)
        
        # Aba Posições Individuais
        individual_tab = self._create_graph_tab(parent_notebook, "Posições Individuais")
        self.create_suspension_individual_graph(individual_tab)
    
    def create_rpm_graph(self, parent):
        """
        Cria gráfico de RPM para os 4 motores.
        Dados: act_Speed A0, act_Speed B0, act_Speed A13, act_Speed B13
        """
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'RPM', 'Tempo (s)')
        
        self.figures['rpm'] = fig
        self.axes['rpm'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['rpm'] = canvas
    
    def create_torque_graph(self, parent):
        """
        Cria gráfico de torque para os 4 motores.
        Mostra act_Torque (linha sólida) e setp_Torque (linha tracejada) para cada motor.
        """
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Torque (Nm)', 'Tempo (s)')
        
        self.figures['torque'] = fig
        self.axes['torque'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['torque'] = canvas
    
    def create_power_graph(self, parent):
        """
        Cria gráfico de potência para os 4 motores.
        Dados: act_Power A0, act_Power B0, act_Power A13, act_Power B13
        """
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Potência (kW)', 'Tempo (s)')
        
        self.figures['power'] = fig
        self.axes['power'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['power'] = canvas
    
    def create_throttle_graph(self, parent):
        """
        Cria gráfico de porcentagem do acelerador (APS_PERC).
        RENOMEADO de "Freio" para "Acelerador".
        """
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], 
                    facecolor=COLORS['bg_light'], 
                    dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Acelerador (%)', 'Tempo (s)')
        
        self.figures['throttle'] = fig
        self.axes['throttle'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['throttle'] = canvas
    
    def create_acceleration_graph(self, parent):
        """
        Cria gráfico de aceleração (vetor_linear_acc_x, vetor_linear_acc_y)
        """
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], 
                    facecolor=COLORS['bg_light'], 
                    dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Aceleração (m/s²)', 'Tempo (s)')
        
        self.figures['acceleration'] = fig
        self.axes['acceleration'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['acceleration'] = canvas

    def create_speed_graph(self, parent):
        """
        Cria gráfico de velocidade (vetor_linear_speed_x).
        """
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], 
                    facecolor=COLORS['bg_light'], 
                    dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Velocidade (Km/h)', 'Tempo (s)')
        
        self.figures['speed'] = fig
        self.axes['speed'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['speed'] = canvas

    def create_suspension_total_graph(self, parent):
        """Cria gráfico de percurso total da suspensão."""
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Percurso (cm)', 'Tempo (s)')
        
        self.figures['suspension_total'] = fig
        self.axes['suspension_total'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['suspension_total'] = canvas
    
    def create_suspension_individual_graph(self, parent):
        """Cria gráfico de posições individuais da suspensão."""
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Percurso (cm)', 'Tempo (s)')
        
        self.figures['suspension_individual'] = fig
        self.axes['suspension_individual'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['suspension_individual'] = canvas
    
    def _create_graph_frame(self, parent, title):
        """Cria um frame para gráfico com título."""
        frame = tk.Frame(parent, bg=COLORS['bg_light'])
        frame.pack(side=tk.LEFT, fill='both', expand=True, padx=3)
        return frame
    
    def _create_graph_tab(self, notebook, title):
        """Cria uma aba para gráfico no notebook."""
        import tkinter as tk
        tab = tk.Frame(notebook, bg=COLORS['bg_light'])
        notebook.add(tab, text=title)
        return tab
    
    def _setup_axis_style(self, ax, ylabel, xlabel):
        """Configura o estilo de um eixo."""
        ax.set_facecolor(COLORS['bg_medium'])
        ax.tick_params(colors=COLORS['gray'], labelsize=8)
        ax.grid(True, alpha=0.15, color=COLORS['gray'])
        ax.spines['bottom'].set_color(COLORS['orange'])
        ax.spines['left'].set_color(COLORS['orange'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_xlabel(xlabel, color=COLORS['gray'], fontsize=9)
        ax.set_ylabel(ylabel, color=COLORS['gray'], fontsize=9)
    
    def update_all_graphs(self):
        """Atualiza todos os gráficos com dados atuais."""
        try:
            # Atualiza gráficos de bateria
            self._update_battery_graphs()
            
            # Atualiza gráficos automotivos
            self._update_automotive_graphs()
            
            # Atualiza gráficos de suspensão
            self._update_suspension_graphs()
            
            # Redesenha todos os canvas
            for canvas in self.canvases.values():
                canvas.draw_idle()
        
        except Exception as e:
            print(f"Erro ao atualizar gráficos: {e}")
    
    def _update_battery_graphs(self):
        """Atualiza gráficos de bateria."""
        if 'battery_voltage' not in self.axes or 'battery_temperature' not in self.axes:
            return
        
        ax_volt = self.axes['battery_voltage']
        ax_temp = self.axes['battery_temperature']
        
        # Limpa gráficos
        ax_volt.clear()
        ax_temp.clear()
        
        # Configura estilo
        self._setup_axis_style(ax_volt, 'Voltagem (V)', 'Tempo (s)')
        self._setup_axis_style(ax_temp, 'Temperatura (°C)', 'Tempo (s)')
        
        # Obtém dados
        time_data = self.data_manager.get_time_data()
        
        if len(time_data) > 1:
            # Normaliza tempo (零点 ao primeiro ponto)
            time_offset = time_data[0]
            times_norm = [(t - time_offset) for t in time_data]
            
            # BMS Alta - Voltagem
            bms_alta_volt = self.data_manager.get_average_data('bms_alta_volt')
            if bms_alta_volt and any(v > 0 for v in bms_alta_volt):
                ax_volt.plot(times_norm, bms_alta_volt, 
                           label='BMS Alta (96 células)', 
                           color=COLORS['orange'], 
                           linewidth=GRAPH_CONFIG['line_width'], 
                           marker='o', 
                           markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
            
            # LV_BMS - Voltagem
            lv_bms_volt = self.data_manager.get_average_data('lv_bms_volt')
            if lv_bms_volt and any(v > 0 for v in lv_bms_volt):
                ax_volt.plot(times_norm, lv_bms_volt, 
                           label='LV_BMS Baixa (8 células)', 
                           color=COLORS['green'], 
                           linewidth=GRAPH_CONFIG['line_width'], 
                           marker='s', 
                           markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
            
            # BMS Alta - Temperatura
            bms_alta_temp = self.data_manager.get_average_data('bms_alta_temp')
            if bms_alta_temp and any(t > 0 for t in bms_alta_temp):
                ax_temp.plot(times_norm, bms_alta_temp, 
                           label='BMS Alta (96 células)', 
                           color=COLORS['warning'], 
                           linewidth=GRAPH_CONFIG['line_width'], 
                           marker='o', 
                           markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
            
            # LV_BMS - Temperatura
            lv_bms_temp = self.data_manager.get_average_data('lv_bms_temp')
            if lv_bms_temp and any(t > 0 for t in lv_bms_temp):
                ax_temp.plot(times_norm, lv_bms_temp, 
                           label='LV_BMS Baixa (8 células)', 
                           color=COLORS['yellow'], 
                           linewidth=GRAPH_CONFIG['line_width'], 
                           marker='s', 
                           markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
            
            # Configura legendas APENAS se houver dados plotados
            for ax in [ax_volt, ax_temp]:
                handles, labels = ax.get_legend_handles_labels()
                if handles:  # Só cria legenda se houver dados
                    ax.legend(loc='upper left', fontsize=8, facecolor=COLORS['bg_dark'],
                             edgecolor=COLORS['orange'], labelcolor=COLORS['white'], framealpha=0.9)
    
    def _update_automotive_graphs(self):
        """
        Atualiza gráficos automotivos.
        VERSÃO CORRIGIDA: Usa dados reais da VCU
        """
        # Lista de motores
        motors = ['A0', 'B0', 'A13', 'B13']
        motor_names = {
            'A0': 'Dir. Diant.',
            'B0': 'Dir. Tras.',
            'A13': 'Esq. Diant.',
            'B13': 'Esq. Tras.'
        }
        
        # === GRÁFICO RPM ===
        if 'rpm' in self.axes:
            ax = self.axes['rpm']
            ax.clear()
            self._setup_axis_style(ax, 'RPM', 'Tempo (s)')
            
            has_data = False
            for motor in motors:
                signal_name = f'ACT_SPEED {motor}'
                
                # Busca dados do sinal
                times = []
                values = []
                if signal_name in self.data_manager.time_history and signal_name in self.data_manager.signal_history:
                    times = list(self.data_manager.time_history[signal_name])
                    values = list(self.data_manager.signal_history[signal_name])
                
                if len(times) > 1 and len(values) > 1:
                    # Normaliza tempo
                    time_offset = times[0]
                    times_norm = [(t - time_offset) for t in times]
                    
                    # Plota
                    ax.plot(times_norm, values,
                           label=motor_names[motor],
                           color=self.motor_colors[motor],
                           linewidth=GRAPH_CONFIG['line_width'],
                           marker='o',
                           markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
                    has_data = True
            
            # Legenda
            if has_data:
                handles, labels = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(loc='upper left', fontsize=8, facecolor=COLORS['bg_dark'],
                             edgecolor=COLORS['orange'], labelcolor=COLORS['white'], framealpha=0.9)
        
        # === GRÁFICO TORQUE (com setpoints) ===
        if 'torque' in self.axes:
            ax = self.axes['torque']
            ax.clear()
            self._setup_axis_style(ax, 'Torque (Nm)', 'Tempo (s)')
            
            has_data = False
            for motor in motors:
                act_signal = f'ACT_TORQUE {motor}'
                setp_signal = f'SETP_TORQUE {motor}'
                
                # Plota act_Torque (valor real) - linha sólida
                times_act = []
                values_act = []
                if act_signal in self.data_manager.time_history and act_signal in self.data_manager.signal_history:
                    times_act = list(self.data_manager.time_history[act_signal])
                    values_act = list(self.data_manager.signal_history[act_signal])
                
                if len(times_act) > 1 and len(values_act) > 1:
                    time_offset = times_act[0]
                    times_norm = [(t - time_offset) for t in times_act]
                    
                    ax.plot(times_norm, values_act,
                           label=f'{motor_names[motor]} (Real)',
                           color=self.motor_colors[motor],
                           linewidth=GRAPH_CONFIG['line_width'],
                           linestyle='-',  # Linha sólida
                           marker='o',
                           markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
                    has_data = True
                
                # Plota setp_Torque (setpoint) - linha tracejada
                times_setp = []
                values_setp = []
                if setp_signal in self.data_manager.time_history and setp_signal in self.data_manager.signal_history:
                    times_setp = list(self.data_manager.time_history[setp_signal])
                    values_setp = list(self.data_manager.signal_history[setp_signal])
                
                if len(times_setp) > 1 and len(values_setp) > 1:
                    time_offset = times_setp[0]
                    times_norm = [(t - time_offset) for t in times_setp]
                    
                    ax.plot(times_norm, values_setp,
                           label=f'{motor_names[motor]} (Setp)',
                           color=self.motor_colors[motor],
                           linewidth=GRAPH_CONFIG['line_width'],
                           linestyle='--',  # Linha tracejada
                           marker='x',
                           markersize=GRAPH_CONFIG['marker_size'],
                           alpha=0.6)  # Mais transparente
                    has_data = True
            
            # Legenda
            if has_data:
                handles, labels = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(loc='upper left', fontsize=7, facecolor=COLORS['bg_dark'],
                             edgecolor=COLORS['orange'], labelcolor=COLORS['white'], 
                             framealpha=0.9, ncol=2)  # 2 colunas para caber tudo
        
        # === GRÁFICO POTÊNCIA ===
        if 'power' in self.axes:
            ax = self.axes['power']
            ax.clear()
            self._setup_axis_style(ax, 'Potência (kW)', 'Tempo (s)')
            
            has_data = False
            for motor in motors:
                signal_name = f'ACT_POWER {motor}'
                
                # Busca dados do sinal
                times = []
                values = []
                if signal_name in self.data_manager.time_history and signal_name in self.data_manager.signal_history:
                    times = list(self.data_manager.time_history[signal_name])
                    values = list(self.data_manager.signal_history[signal_name])
                
                if len(times) > 1 and len(values) > 1:
                    # Normaliza tempo
                    time_offset = times[0]
                    times_norm = [(t - time_offset) for t in times]
                    
                    # Plota
                    ax.plot(times_norm, values,
                           label=motor_names[motor],
                           color=self.motor_colors[motor],
                           linewidth=GRAPH_CONFIG['line_width'],
                           marker='o',
                           markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
                    has_data = True
            
            # Legenda
            if has_data:
                handles, labels = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(loc='upper left', fontsize=8, facecolor=COLORS['bg_dark'],
                             edgecolor=COLORS['orange'], labelcolor=COLORS['white'], framealpha=0.9)
        
        # === GRÁFICO ACELERADOR (APS_PERC) ===
        if 'throttle' in self.axes:
            ax = self.axes['throttle']
            ax.clear()
            self._setup_axis_style(ax, 'Acelerador (%)', 'Tempo (s)')
            
            # Busca dados do APS_PERC
            signal_name = 'APS_PERC'
            times = []
            values = []
            
            if signal_name in self.data_manager.time_history and signal_name in self.data_manager.signal_history:
                times = list(self.data_manager.time_history[signal_name])
                values = list(self.data_manager.signal_history[signal_name])
            
            if len(times) > 1 and len(values) > 1:
                # Normaliza tempo
                time_offset = times[0]
                times_norm = [(t - time_offset) for t in times]
                
                # Plota
                ax.plot(times_norm, values,
                       label='Acelerador',
                       color=COLORS['green'],  # Verde para acelerador
                       linewidth=GRAPH_CONFIG['line_width'],
                       marker='o',
                       markersize=GRAPH_CONFIG['marker_size'],
                       alpha=GRAPH_CONFIG['alpha'])
                
                # Define limites do eixo Y (0-100%)
                ax.set_ylim(-5, 105)
                
                # Adiciona linhas de referência
                ax.axhline(y=0, color=COLORS['gray'], linestyle='--', linewidth=1, alpha=0.5)
                ax.axhline(y=100, color=COLORS['gray'], linestyle='--', linewidth=1, alpha=0.5)
                
                # Legenda
                handles, labels = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(loc='upper left', fontsize=8, facecolor=COLORS['bg_dark'],
                             edgecolor=COLORS['orange'], labelcolor=COLORS['white'], framealpha=0.9)

        # === GRÁFICO ACELERAÇÃO (IMU - 3 eixos) ===
        if 'acceleration' in self.axes:
            ax = self.axes['acceleration']
            ax.clear()
            self._setup_axis_style(ax, 'Aceleração (m/s²)', 'Tempo (s)')
            
            has_data = False
            
            # Todos os sinais possíveis (variações de nome)
            imu_accel_signals = [
                (['VENTOR_LINEAR_ACC_X', 'VETOR_LINEAR_ACC_X'], 'Acel. X', COLORS['orange']),
                (['VENTOR_LINEAR_ACC_Y', 'VETOR_LINEAR_ACC_Y'], 'Acel. Y', COLORS['green']),
                (['VENTOR_LINEAR_ACC_Z', 'VETOR_LINEAR_ACC_Z'], 'Acel. Z', COLORS['blue']),
            ]
            
            ref_time = None  # Tempo de referência comum
            for candidatos, label, color in imu_accel_signals:
                times, values = [], []
                # Busca o sinal de forma case-insensitive
                for key in self.data_manager.time_history.keys():
                    if any(c in key.upper() for c in candidatos):
                        times  = list(self.data_manager.time_history[key])
                        values = list(self.data_manager.signal_history.get(key, []))
                        break
                
                if len(times) > 1 and len(values) > 1:
                    if ref_time is None:
                        ref_time = times[0]
                    times_norm = [(t - ref_time) for t in times]
                    ax.plot(times_norm, values,
                           label=label, color=color,
                           linewidth=GRAPH_CONFIG['line_width'],
                           marker='o', markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
                    has_data = True
            
            if has_data:
                handles, labels_leg = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(loc='upper left', fontsize=8,
                             facecolor=COLORS['bg_dark'], edgecolor=COLORS['orange'],
                             labelcolor=COLORS['white'], framealpha=0.9)

        # === GRÁFICO VELOCIDADE (IMU - X e Y) ===
        if 'velocity' in self.axes or 'speed' in self.axes:
            ax_key = 'velocity' if 'velocity' in self.axes else 'speed'
            ax = self.axes[ax_key]
            ax.clear()
            self._setup_axis_style(ax, 'Velocidade (km/h)', 'Tempo (s)')
            
            has_data = False
            
            imu_speed_signals = [
                (['VENTOR_LINEAR_SPEED_X', 'VETOR_LINEAR_SPEED_X'], 'Vel. X (North)', COLORS['orange']),
                (['VENTOR_LINEAR_SPEED_Y', 'VETOR_LINEAR_SPEED_Y'], 'Vel. Y (East)',  COLORS['green']),
            ]
            
            ref_time = None
            for candidatos, label, color in imu_speed_signals:
                times, values = [], []
                for key in self.data_manager.time_history.keys():
                    if any(c in key.upper() for c in candidatos):
                        times  = list(self.data_manager.time_history[key])
                        values = list(self.data_manager.signal_history.get(key, []))
                        break
                
                if len(times) > 1 and len(values) > 1:
                    if ref_time is None:
                        ref_time = times[0]
                    times_norm = [(t - ref_time) for t in times]
                    ax.plot(times_norm, values,
                           label=label, color=color,
                           linewidth=GRAPH_CONFIG['line_width'],
                           marker='o', markersize=GRAPH_CONFIG['marker_size'],
                           alpha=GRAPH_CONFIG['alpha'])
                    has_data = True
            
            if has_data:
                handles, labels_leg = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(loc='upper left', fontsize=8,
                             facecolor=COLORS['bg_dark'], edgecolor=COLORS['orange'],
                             labelcolor=COLORS['white'], framealpha=0.9)
                    
    def _update_suspension_graphs(self):
        """Atualiza gráficos de suspensão."""
        # Implementação específica para dados de suspensão
        # Placeholder para implementação detalhada
        pass