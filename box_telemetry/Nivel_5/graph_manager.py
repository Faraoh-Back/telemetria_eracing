"""
Sistema de Telimetria E-Racing UNICAMP - Gerenciador de Gráficos
Módulo responsável por todas as visualizações gráficas do dashboard
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
        NOVO: Adicionado gráfico de Freio (APS_PERC)
        """
        # Aba RPM
        rpm_tab = self._create_graph_tab(parent_notebook, "RPM")
        self.create_rpm_graph(rpm_tab)
        
        # Aba Aceleração
        accel_tab = self._create_graph_tab(parent_notebook, "Aceleração")
        self.create_acceleration_graph(accel_tab)
        
        # Aba Velocidade
        speed_tab = self._create_graph_tab(parent_notebook, "Velocidade")
        self.create_velocity_graph(speed_tab)
        
        # Aba Torque
        torque_tab = self._create_graph_tab(parent_notebook, "Torque")
        self.create_torque_graph(torque_tab)
        
        # Aba Potência
        power_tab = self._create_graph_tab(parent_notebook, "Potência")
        self.create_power_graph(power_tab)
        
        # NOVO: Aba Freio
        brake_tab = self._create_graph_tab(parent_notebook, "Freio")
        self.create_brake_graph(brake_tab)
    
    def create_suspension_graphs(self, parent_notebook):
        """Cria gráficos para dados de suspensão."""
        # Aba Percurso Total
        total_tab = self._create_graph_tab(parent_notebook, "Percurso Total")
        self.create_suspension_total_graph(total_tab)
        
        # Aba Posições Individuais
        individual_tab = self._create_graph_tab(parent_notebook, "Posições Individuais")
        self.create_suspension_individual_graph(individual_tab)
    
    def create_rpm_graph(self, parent):
        """Cria gráfico de RPM."""
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
    
    def create_acceleration_graph(self, parent):
        """Cria gráfico de aceleração."""
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Aceleração (m/s²)', 'Tempo (s)')
        
        self.figures['acceleration'] = fig
        self.axes['acceleration'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['acceleration'] = canvas
    
    def create_velocity_graph(self, parent):
        """Cria gráfico de velocidade."""
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], facecolor=COLORS['bg_light'], dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Velocidade (m/s)', 'Tempo (s)')
        
        self.figures['velocity'] = fig
        self.axes['velocity'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['velocity'] = canvas
    
    def create_torque_graph(self, parent):
        """Cria gráfico de torque."""
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
        """Cria gráfico de potência."""
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

    def create_brake_graph(self, parent):
        """
        Cria gráfico de porcentagem do freio (APS_PERC).
        NOVO: Gráfico de freio.
        """
        fig = Figure(figsize=GRAPH_CONFIG['figure_size'], 
                    facecolor=COLORS['bg_light'], 
                    dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.18)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, 'Freio (%)', 'Tempo (s)')
        
        self.figures['brake'] = fig
        self.axes['brake'] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvases['brake'] = canvas
    
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
            
            # Configura legendas
            for ax in [ax_volt, ax_temp]:
                ax.legend(loc='upper left', fontsize=8, facecolor=COLORS['bg_dark'],
                         edgecolor=COLORS['orange'], labelcolor=COLORS['white'], framealpha=0.9)
    
    def _update_automotive_graphs(self):
        """
        Atualiza gráficos automotivos.
        NOVO: Inclui atualização do gráfico de freio.
        """
        # Verifica se o gráfico de freio existe
        if 'brake' not in self.axes:
            return
        
        ax_brake = self.axes['brake']
        
        # Limpa gráfico
        ax_brake.clear()
        
        # Configura estilo
        self._setup_axis_style(ax_brake, 'Freio (%)', 'Tempo (s)')
        
        # Obtém dados de tempo
        time_data = self.data_manager.get_time_data()
        
        if len(time_data) < 2:
            return
        
        # Normaliza tempo
        time_offset = time_data[0]
        times_norm = [(t - time_offset) for t in time_data]
        
        # Obtém dados do freio (APS_PERC)
        brake_data = []
        for signal_name, values in self.data_manager.signal_history.items():
            if 'APS_PERC' in signal_name.upper():
                brake_data = list(values)
                break
        
        if brake_data and len(brake_data) == len(times_norm):
            ax_brake.plot(
                times_norm,
                brake_data,
                label='Freio (APS_PERC)',
                color=COLORS['warning'],  # Vermelho para freio
                linewidth=GRAPH_CONFIG['line_width'],
                marker='o',
                markersize=GRAPH_CONFIG['marker_size'],
                alpha=GRAPH_CONFIG['alpha']
            )
            
            # Define limites do eixo Y (0-100%)
            ax_brake.set_ylim(-5, 105)
            
            # Adiciona linhas de referência
            ax_brake.axhline(y=0, color=COLORS['gray'], linestyle='--', linewidth=1, alpha=0.5)
            ax_brake.axhline(y=100, color=COLORS['gray'], linestyle='--', linewidth=1, alpha=0.5)
            
            # Legenda
            ax_brake.legend(
                loc='upper left',
                fontsize=8,
                facecolor=COLORS['bg_dark'],
                edgecolor=COLORS['orange'],
                labelcolor=COLORS['white'],
                framealpha=0.9
            )
    
    def _update_suspension_graphs(self):
        """Atualiza gráficos de suspensão."""
        # Implementação específica para dados de suspensão
        # Placeholder para implementação detalhada
        pass
