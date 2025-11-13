"""
Sistema de Telimetria E-Racing UNICAMP - Interface Gráfica
Módulo responsável por toda a interface do usuário
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
from datetime import datetime
from PIL import Image, ImageTk
from config import *
from graph_manager import GraphManager

# Verifica se matplotlib está disponível
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class TelemetryUI:
    """Interface principal do sistema de telemetria."""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.root = None
        self.graph_manager = GraphManager(data_manager)
        
        # Elementos da UI
        self.main_tree = None
        self.metric_cards = {}
        self.temp_trees = {}
        self.detail_trees = {}
        self.tree_items = {}
        
        # Status
        self.status_var = None
        self.time_var = None
        self.analysis_mode_var = None
        
        # Controles de análise
        self.analysis_running = False
        
        print("🖥️ Interface gráfica inicializada")
    
    def create_main_window(self):
        """Cria a janela principal."""
        self.root = tk.Tk()
        self.root.title("E-Racing UNICAMP - Telemetria")
        self.root.geometry("")  # Tamanho automático
        self.root.configure(bg=COLORS['bg_dark'])
        
        # Configurações de responsividade
        self.root.minsize(1200, 800)
        self.root.resizable(True, True)
        
        # Configura o grid como sistema de layout padrão
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Evento de fechamento
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Constrói interface
        self._build_header()
        self._build_main_content()
        
        return self.root
    
    def _build_header(self):
        """Constrói o cabeçalho da aplicação."""
        header_frame = tk.Frame(self.root, bg=COLORS['bg_dark'], height=100)
        header_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        header_frame.grid_propagate(False)
        
        # Configura grid do cabeçalho
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(2, weight=1)
        
        # Conteúdo do cabeçalho
        header_content = tk.Frame(header_frame, bg=COLORS['bg_dark'])
        header_content.grid(row=0, column=0, sticky='w', padx=20, pady=15)
        
        # Logo e título
        self._create_logo_and_title(header_content)
        
        # Controles de análise (centro)
        self._create_analysis_controls(header_frame)
        
        # Status e tempo (direita)
        self._create_status_and_time(header_frame)
        
        # Separador
        separator = tk.Frame(self.root, bg=COLORS['orange'], height=3)
        separator.grid(row=2, column=0, sticky='ew')
    
    def _create_logo_and_title(self, parent):
        """Cria logo e título da equipe."""
        logo_frame = tk.Frame(parent, bg=COLORS['bg_dark'])
        logo_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # Logo
        if os.path.exists(LOGO_PATH):
            try:
                logo_img = Image.open(LOGO_PATH)
                logo_img.thumbnail((80, 80), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(logo_frame, image=self.logo_photo, bg=COLORS['bg_dark'])
                logo_label.pack()
            except:
                self._create_text_logo(logo_frame)
        else:
            self._create_text_logo(logo_frame)
        
        # Título
        title_container = tk.Frame(parent, bg=COLORS['bg_dark'])
        title_container.pack(side=tk.LEFT)
        
        eracing_label = tk.Label(
            title_container,
            text="E-RACING UNICAMP",
            bg=COLORS['bg_dark'],
            fg=COLORS['white'],
            font=("Arial Black", 24, "bold")
        )
        eracing_label.pack(anchor=tk.W)
        
        subtitle = tk.Label(
            title_container,
            text="TELEMETRY DASHBOARD • Real-Time Monitoring",
            bg=COLORS['bg_dark'],
            fg=COLORS['gray_light'],
            font=("Arial", 12)
        )
        subtitle.pack(anchor=tk.W)
    
    def _create_text_logo(self, parent):
        """Cria logo em texto como fallback."""
        text_logo = tk.Label(parent, text="🏎️", bg=COLORS['bg_dark'], fg=COLORS['orange'], font=("Arial", 40))
        text_logo.pack()
    
    def _create_analysis_controls(self, parent):
        """Cria controles de análise (botões)."""
        controls_frame = tk.Frame(parent, bg=COLORS['bg_dark'])
        controls_frame.grid(row=0, column=1, sticky='e', padx=20, pady=15)
        
        # Modo de análise
        mode_frame = tk.Frame(controls_frame, bg=COLORS['bg_dark'])
        mode_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        self.analysis_mode_var = tk.StringVar(value="⏸️ Pausado")
        mode_label = tk.Label(
            mode_frame,
            textvariable=self.analysis_mode_var,
            bg=COLORS['bg_dark'],
            fg=COLORS['orange'],
            font=("Arial", 12, "bold")
        )
        mode_label.pack()
        
        # Botões de controle
        buttons_frame = tk.Frame(controls_frame, bg=COLORS['bg_dark'])
        buttons_frame.pack(side=tk.RIGHT)
        
        # Botão Iniciar/Parar
        self.start_stop_btn = tk.Button(
            buttons_frame,
            text="▶️ Iniciar",
            command=self.toggle_analysis,
            bg=COLORS['bg_medium'],
            fg=COLORS['white'],
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        self.start_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Botão Zerar
        reset_btn = tk.Button(
            buttons_frame,
            text="🔄 Zerar",
            command=self.reset_analysis,
            bg=COLORS['warning'],
            fg=COLORS['white'],
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Botão Exportar
        export_btn = tk.Button(
            buttons_frame,
            text="💾 Exportar CSV",
            command=self.export_data,
            bg=COLORS['green'],
            fg=COLORS['white'],
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        export_btn.pack(side=tk.LEFT, padx=5)
    
    def _create_status_and_time(self, parent):
        """Cria status e informações de tempo."""
        status_frame = tk.Frame(parent, bg=COLORS['bg_dark'])
        status_frame.grid(row=0, column=2, sticky='e', padx=30)
        
        self.status_var = tk.StringVar(value="⚪ Inicializando...")
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=COLORS['bg_dark'],
            fg=COLORS['gray_light'],
            font=("Arial", 11)
        )
        status_label.pack()
        
        self.time_var = tk.StringVar(value=datetime.now().strftime("%H:%M:%S"))
        time_label = tk.Label(
            status_frame,
            textvariable=self.time_var,
            bg=COLORS['bg_dark'],
            fg=COLORS['gray'],
            font=("Arial", 10)
        )
        time_label.pack()
        
        # Atualiza relógio
        def update_clock():
            self.time_var.set(datetime.now().strftime("%H:%M:%S"))
            self.root.after(1000, update_clock)
        update_clock()
    
    def _build_main_content(self):
        """Constrói o conteúdo principal da interface."""
        main_container = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main_container.grid(row=1, column=0, sticky='nsew', padx=15, pady=15)
        
        # Configura grid para expansão - 3/5 para esquerda, 2/5 para direita
        main_container.grid_columnconfigure(0, weight=3)  # Coluna esquerda: 60%
        main_container.grid_columnconfigure(0, weight=2)  # Coluna direita: 40%
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_rowconfigure(2, weight=1)
        
        # Colunas principais usando grid
        left_column = tk.Frame(main_container, bg=COLORS['bg_dark'])
        left_column.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
        right_column = tk.Frame(main_container, bg=COLORS['bg_dark'])
        right_column.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        
        # Configurar grid responsivo para as colunas
        left_column.grid_columnconfigure(0, weight=1)
        left_column.grid_rowconfigure(0, weight=0)  # ALERTAS (seção compacta)
        left_column.grid_rowconfigure(1, weight=0)  # GRÁFICOS (mais altos)
        left_column.grid_rowconfigure(2, weight=0)  # MONITOR DE TEMPERATURAS (seção média)
        
        right_column.grid_columnconfigure(0, weight=1)
        right_column.grid_rowconfigure(0, weight=0)  # MÉTRICAS PRINCIPAIS
        right_column.grid_rowconfigure(1, weight=1)  # TODOS OS SINAIS (nova posição)
        right_column.grid_rowconfigure(2, weight=1)  # DETALHES POR SISTEMA
        
        # Seções esquerda
        self._build_alerts_section(left_column)
        
        if MATPLOTLIB_AVAILABLE:
            self._build_graphs_section(left_column)
        
        # Seção de temperatura agora na parte inferior da esquerda
        self._build_temperature_section(left_column)
        
        # Seções direita
        self._build_key_metrics(right_column)
        self._build_main_table(right_column)  # Tabela de sinais agora na direita
        self._build_detail_tables(right_column)
    
    def _build_alerts_section(self, parent):
        """Constrói seção de alertas."""
        content = self._create_section(parent, "⚠️  ALERTAS DO SISTEMA", height=100)  # Reduzido de 130 para 80
        # Configura grid para expansão
        parent.grid_rowconfigure(0, weight=0)
        self.alerts_frame = tk.Frame(content, bg=COLORS['bg_light'])
        self.alerts_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _build_graphs_section(self, parent):
        """Constrói seção de gráficos com abas."""
        content = self._create_section(parent, "📊  GRÁFICOS EM TEMPO REAL (MÉDIAS)", height=400)  # Aumentado de 350 para 500
        
        # Configura grid para expansão
        parent.grid_rowconfigure(1, weight=0)
        
        # Notebook para abas
        style = ttk.Style()
        style.configure("GraphNotebook.TNotebook", background=COLORS['bg_light'])
        style.configure("GraphNotebook.TNotebook.Tab",
                       background=COLORS['bg_medium'],
                       foreground=COLORS['white'],
                       padding=[15, 6],
                       font=("Arial", 10, "bold"))
        style.map("GraphNotebook.TNotebook.Tab",
                 background=[("selected", COLORS['orange'])],
                 foreground=[("selected", COLORS['white'])])
        
        self.graph_notebook = ttk.Notebook(content, style="GraphNotebook.TNotebook")
        self.graph_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Aba Principal - Baterias
        battery_tab = tk.Frame(self.graph_notebook, bg=COLORS['bg_light'])
        self.graph_notebook.add(battery_tab, text="🔋 Baterias")
        
        # Frame para gráficos de bateria
        battery_graphs_frame = tk.Frame(battery_tab, bg=COLORS['bg_light'])
        battery_graphs_frame.pack(fill=tk.BOTH, expand=True)
        
        self.graph_manager.create_battery_graphs(battery_graphs_frame)
        
        # Abas Automotivas
        automotive_tab = tk.Frame(self.graph_notebook, bg=COLORS['bg_light'])
        self.graph_notebook.add(automotive_tab, text="🚗 Automotivo")
        
        # Sub-notebook para gráficos automotivos
        automotive_notebook = ttk.Notebook(automotive_tab, style="GraphNotebook.TNotebook")
        automotive_notebook.pack(fill=tk.BOTH, expand=True)
        
        self.graph_manager.create_automotive_graphs(automotive_notebook)
        
        # Abas Suspensão
        suspension_tab = tk.Frame(self.graph_notebook, bg=COLORS['bg_light'])
        self.graph_notebook.add(suspension_tab, text="🔧 Suspensão")
        
        # Sub-notebook para gráficos de suspensão
        suspension_notebook = ttk.Notebook(suspension_tab, style="GraphNotebook.TNotebook")
        suspension_notebook.pack(fill=tk.BOTH, expand=True)
        
        self.graph_manager.create_suspension_graphs(suspension_notebook)
    
    def _build_main_table(self, parent):
        """Constrói tabela principal de sinais."""
        content = self._create_section(parent, "📋  TODOS OS SINAIS")
        
        # Configura grid para expansão
        parent.grid_rowconfigure(2, weight=1)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Eracing.Treeview",
            background=COLORS['bg_light'],
            foreground=COLORS['white'],
            fieldbackground=COLORS['bg_light'],
            borderwidth=0,
            font=("Arial", 9)
        )
        style.configure("Eracing.Treeview.Heading", 
                       background=COLORS['bg_medium'],
                       foreground=COLORS['orange'],
                       font=("Arial", 10, "bold"))
        style.map('Eracing.Treeview', background=[('selected', COLORS['orange_dark'])])
        
        columns = ('timestamp', 'signal_name', 'value', 'unit')
        self.main_tree = ttk.Treeview(
            content, 
            columns=columns, 
            show='headings', 
            height=8,
            style="Eracing.Treeview"
        )
        
        self.main_tree.heading('timestamp', text='TIMESTAMP')
        self.main_tree.column('timestamp', anchor=tk.W, width=120)
        self.main_tree.heading('signal_name', text='SINAL')
        self.main_tree.column('signal_name', anchor=tk.W, width=250)
        self.main_tree.heading('value', text='VALOR')
        self.main_tree.column('value', anchor=tk.E, width=100)
        self.main_tree.heading('unit', text='UNIDADE')
        self.main_tree.column('unit', anchor=tk.W, width=80)
        
        # Scrollbar
        vsb = ttk.Scrollbar(content, orient="vertical", command=self.main_tree.yview)
        self.main_tree.configure(yscrollcommand=vsb.set)
        
        self.main_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_items = {}
    
    def _build_key_metrics(self, parent):
        """Constrói seção de métricas principais."""
        content = self._create_section(parent, "🎯  MÉTRICAS PRINCIPAIS", height=220)
        
        # Configura grid para expansão
        parent.grid_rowconfigure(0, weight=0)
        
        metrics_grid = tk.Frame(content, bg=COLORS['bg_light'])
        metrics_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.metric_cards = {}
        metrics = [
            ('voltage_high', 'VOLTAGEM ALTA', 'V', 0, 0),
            ('voltage_low', 'VOLTAGEM BAIXA', 'V', 0, 1),
            ('speed', 'VELOCIDADE (IMU)', 'm/s', 1, 0),
            ('temp_high', 'TEMP. MÉDIA ALTA', '°C', 1, 1),
            ('temp_low', 'TEMP. MÉDIA BAIXA', '°C', 2, 0),
            ('power', 'POTÊNCIA TOTAL', 'kW', 2, 1),
        ]
        
        for key, label, unit, row, col in metrics:
            card = self._create_metric_card(metrics_grid, label, unit)
            card['frame'].grid(row=row, column=col, padx=4, pady=4, sticky='nsew')
            self.metric_cards[key] = card
        
        metrics_grid.grid_rowconfigure(0, weight=1)
        metrics_grid.grid_rowconfigure(1, weight=1)
        metrics_grid.grid_rowconfigure(2, weight=1)
        metrics_grid.grid_columnconfigure(0, weight=1)
        metrics_grid.grid_columnconfigure(1, weight=1)
    
    def _create_metric_card(self, parent, label, unit):
        """Cria um card de métrica."""
        card = tk.Frame(parent, bg=COLORS['bg_medium'], relief=tk.FLAT,
                       highlightbackground=COLORS['orange'], highlightthickness=1)
        
        label_widget = tk.Label(card, text=label, bg=COLORS['bg_medium'],
                               fg=COLORS['gray_light'], font=("Arial", 8, "bold"))
        label_widget.pack(pady=(8, 2))
        
        value_widget = tk.Label(card, text="--", bg=COLORS['bg_medium'],
                               fg=COLORS['orange'], font=("Arial", 22, "bold"))
        value_widget.pack()
        
        unit_widget = tk.Label(card, text=unit, bg=COLORS['bg_medium'],
                              fg=COLORS['gray'], font=("Arial", 9))
        unit_widget.pack(pady=(0, 8))
        
        return {'frame': card, 'value': value_widget, 'label': label_widget}
    
    def _build_temperature_section(self, parent):
        """Constrói seção de monitor de temperaturas com sistema de abas."""
        content = self._create_section(parent, "🌡️  MONITOR DE TEMPERATURAS", height=350)
        
        # Configura estilo para o notebook de temperaturas
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "TempNotebook.TNotebook",
            background=COLORS['bg_light']
        )
        style.configure(
            "TempNotebook.TNotebook.Tab",
            background=COLORS['bg_medium'],
            foreground=COLORS['white'],
            padding=[15, 8],
            font=("Arial", 9, "bold")
        )
        style.map(
            "TempNotebook.TNotebook.Tab",
            background=[("selected", COLORS['orange'])],
            foreground=[("selected", COLORS['white'])]
        )
        
        # Cria notebook com abas
        self.temp_notebook = ttk.Notebook(content, style="TempNotebook.TNotebook")
        self.temp_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configura estrutura de dados para as abas
        self.temp_trees = {}
        
        # Define as categorias de temperatura
        temp_categories = [
            {"name": "BMS_ALTA", "title": "🔋 BMS ALTA (96 células)", "pattern": "TCELL_"},
            {"name": "LV_BMS", "title": "🔋 LV_BMS (8 células)", "pattern": "LV_TCELL"},
            {"name": "MOTORES", "title": "🏎️ MOTORES", "pattern": ["motor", "MGM", "MGP"]},
            {"name": "INVERSORES", "title": "⚡ INVERSORES", "pattern": ["inverter", "INV", "temp_inv"]},
            {"name": "FLUIDOS", "title": "🌡️ FLUIDOS", "pattern": ["fluid", "agua", "oleo", "coolant"]},
            {"name": "OUTROS", "title": "🌡️ OUTROS SENSORES", "pattern": ["temp", "temperature"]}
        ]
        
        # Cria aba para cada categoria
        for category in temp_categories:
            self._create_temperature_tab(category)
    
    def _create_temperature_tab(self, category):
        """Cria uma aba para uma categoria específica de temperatura."""
        # Frame da aba
        tab_frame = tk.Frame(self.temp_notebook, bg=COLORS['bg_light'])
        self.temp_notebook.add(tab_frame, text=category["title"])
        
        # Cria Treeview para 6 colunas (3 pares: nome + valor)
        columns = []
        for i in range(3):  # 3 sensores por linha
            columns.append(f"sensor_{i}_name")
            columns.append(f"sensor_{i}_value")
        
        # Configura estilo da Treeview
        tree_style = ttk.Style()
        tree_style.configure(
            f"Temp.{category['name']}.Treeview",
            background=COLORS['bg_light'],
            foreground=COLORS['white'],
            fieldbackground=COLORS['bg_light'],
            borderwidth=0,
            font=("Arial", 9)
        )
        tree_style.configure(
            f"Temp.{category['name']}.Treeview.Heading", 
            background=COLORS['bg_medium'],
            foreground=COLORS['orange'],
            font=("Arial", 10, "bold")
        )
        tree_style.map(
            f'Temp.{category["name"]}.Treeview', 
            background=[('selected', COLORS['orange_dark'])]
        )
        
        # Cria Treeview
        temp_tree = ttk.Treeview(
            tab_frame,
            columns=columns,
            show='headings',
            height=6,
            style=f"Temp.{category['name']}.Treeview"
        )
        
        # Configura cabeçalhos para os 3 sensores
        for i in range(3):
            # Coluna do nome do sensor
            temp_tree.heading(f"sensor_{i}_name", text=f"SENSOR {i+1}")
            temp_tree.column(f"sensor_{i}_name", anchor=tk.W, width=150)
            
            # Coluna do valor do sensor
            temp_tree.heading(f"sensor_{i}_value", text=f"VALOR {i+1}")
            temp_tree.column(f"sensor_{i}_value", anchor=tk.CENTER, width=100)
        
        # Scrollbars
        scrollbar_h = ttk.Scrollbar(tab_frame, orient="horizontal", command=temp_tree.xview)
        scrollbar_v = ttk.Scrollbar(tab_frame, orient="vertical", command=temp_tree.yview)
        
        temp_tree.configure(xscrollcommand=scrollbar_h.set, yscrollcommand=scrollbar_v.set)
        
        # Empacota Treeview e scrollbars
        temp_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Armazena referência da Treeview
        self.temp_trees[category['name']] = {
            'tree': temp_tree,
            'pattern': category['pattern'],
            'tab_frame': tab_frame
        }
        
        # Adiciona linha inicial vazia
        initial_values = [""] * 6
        temp_tree.insert("", tk.END, values=initial_values)    

    def _update_temperature_section(self):
        """Atualiza dados em todas as abas de temperatura."""
        if not hasattr(self, 'temp_trees') or not self.temp_trees:
            return
        
        # Obtém todos os sinais de temperatura
        all_temp_signals = [signal for signal in self.data_manager.get_sorted_signals() 
                           if 'temp' in signal['signal'].lower()]
        
        # Para cada categoria de temperatura
        for category_name, category_data in self.temp_trees.items():
            temp_tree = category_data['tree']
            pattern = category_data['pattern']
            
            # Limpa linha existente
            for item in temp_tree.get_children():
                temp_tree.delete(item)
            
            # Filtra sinais baseado no padrão da categoria
            if category_name == "BMS_ALTA":
                # BMS_ALTA: TCELL_0 a TCELL_95
                filtered_signals = [s for s in all_temp_signals 
                                  if s['signal'].startswith('TCELL_')]
                filtered_signals.sort(key=lambda x: int(x['signal'].split('_')[1]))
            elif category_name == "LV_BMS":
                # LV_BMS: LV_TCELL_X
                filtered_signals = [s for s in all_temp_signals 
                                  if s['signal'].startswith('LV_TCELL')]
                filtered_signals.sort(key=lambda x: int(x['signal'].split('_')[2]) if len(x['signal'].split('_')) > 2 else 0)
            else:
                # Outras categorias: busca por padrões múltiplos
                if isinstance(pattern, list):
                    filtered_signals = []
                    for pat in pattern:
                        filtered_signals.extend([s for s in all_temp_signals 
                                               if pat.lower() in s['signal'].lower()])
                    # Remove duplicatas
                    filtered_signals = list({s['signal']: s for s in filtered_signals}.values())
                else:
                    filtered_signals = [s for s in all_temp_signals 
                                      if pattern.lower() in s['signal'].lower()]
            
            # Preenche as abas com os sensores encontrados (máximo 12 sensores por aba = 6 linhas × 2 colunas)
            sensor_data = []
            max_sensors = 12  # 6 linhas × 2 colunas (nome + valor)
            
            for i in range(min(len(filtered_signals), max_sensors)):
                signal_data = filtered_signals[i]
                sensor_name = signal_data['signal']
                sensor_value = signal_data['value']
                
                # Ajusta nome do sensor para exibição mais limpa
                if sensor_name.startswith('TCELL_'):
                    cell_num = sensor_name.split('_')[1]
                    sensor_name = f"C{cell_num}"
                elif sensor_name.startswith('LV_TCELL_'):
                    cell_num = sensor_name.split('_')[2]
                    sensor_name = f"LV C{cell_num}"
                
                sensor_data.append(sensor_name)
                sensor_data.append(sensor_value)
            
            # Preenche com valores vazios se necessário
            while len(sensor_data) < 6:  # 6 colunas total (3 pares)
                sensor_data.append("")
                sensor_data.append("")
            
            # Insere linha na aba
            temp_tree.insert("", tk.END, values=sensor_data)

    def _build_detail_tables(self, parent):
        """Constrói seção de detalhes por sistema."""
        content = self._create_section(parent, "🔧  DETALHES POR SISTEMA")
        
        # Configura grid para expansão
        parent.grid_rowconfigure(2, weight=1)
        
        # Notebook com abas dinâmicas para cada sistema
        style = ttk.Style()
        style.configure("Eracing.TNotebook", background=COLORS['bg_light'])
        style.configure("Eracing.TNotebook.Tab",
                       background=COLORS['bg_medium'],
                       foreground=COLORS['white'],
                       padding=[15, 6],
                       font=("Arial", 9, "bold"))
        style.map("Eracing.TNotebook.Tab",
                 background=[("selected", COLORS['orange'])],
                 foreground=[("selected", COLORS['white'])])
        
        self.detail_notebook = ttk.Notebook(content, style="Eracing.TNotebook")
        self.detail_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Cria aba para cada sistema
        for system in SYSTEMS:
            self._create_system_tab(system)
    
    def _create_system_tab(self, system):
        """Cria aba para um sistema específico."""
        tab = tk.Frame(self.detail_notebook, bg=COLORS['bg_light'])
        self.detail_notebook.add(tab, text=system)
        
        # Treeview para o sistema
        tree = ttk.Treeview(tab, columns=('name', 'value'), show='headings',
                          height=8, style="Eracing.Treeview")
        tree.heading('name', text='PARÂMETRO')
        tree.column('name', width=200)
        tree.heading('value', text='VALOR')
        tree.column('value', width=150)
        
        # Scrollbar
        vsb = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Armazena referência
        self.detail_trees[system] = {'tree': tree, 'items': {}}
    
    def _create_section(self, parent, title, height=None):
        """Cria uma seção com título."""
        section = tk.Frame(parent, bg=COLORS['bg_medium'], relief=tk.FLAT, bd=0)
        section.pack(fill=tk.BOTH, expand=True if height is None else False, pady=7)
        if height:
            section.configure(height=height)
            section.pack_propagate(False)
        
        header_container = tk.Frame(section, bg=COLORS['bg_medium'])
        header_container.pack(fill=tk.X)
        
        orange_accent = tk.Frame(header_container, bg=COLORS['orange'], width=4)
        orange_accent.pack(side=tk.LEFT, fill=tk.Y)
        
        header = tk.Label(
            header_container,
            text=title,
            bg=COLORS['bg_medium'],
            fg=COLORS['white'],
            font=("Arial", 11, "bold"),
            anchor=tk.W,
            padx=15,
            pady=10
        )
        header.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        content = tk.Frame(section, bg=COLORS['bg_light'])
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        return content
    
    def toggle_analysis(self):
        """Inicia ou para a análise."""
        if not self.analysis_running:
            self.data_manager.start_analysis()
            self.analysis_mode_var.set("▶️ Analisando")
            self.start_stop_btn.config(text="⏸️ Parar", bg=COLORS['warning'])
            self.analysis_running = True
        else:
            self.data_manager.pause_analysis()
            self.analysis_mode_var.set("⏸️ Pausado")
            self.start_stop_btn.config(text="▶️ Iniciar", bg=COLORS['bg_medium'])
            self.analysis_running = False
    
    def reset_analysis(self):
        """Reseta toda a análise."""
        if messagebox.askyesno("Confirmar", "Deseja realmente zerar toda a análise?\nIsso apagará todos os dados atuais."):
            self.data_manager.reset_analysis()
            self.analysis_mode_var.set("⏸️ Pausado")
            self.start_stop_btn.config(text="▶️ Iniciar", bg=COLORS['bg_medium'])
            self.analysis_running = False
            self.status_var.set("🔄 Análise zerada")
            # Limpa interface
            self._clear_all_displays()
    
    def export_data(self):
        """Exporta dados para CSV."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Salvar dados de telemetria"
            )
            
            if filename:
                self.data_manager.export_to_csv(filename)
                messagebox.showinfo("Sucesso", f"Dados exportados para:\n{filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar dados:\n{e}")
    
    def _clear_all_displays(self):
        """Limpa todos os displays."""
        # Limpa tabela principal
        for item in self.main_tree.get_children():
            self.main_tree.delete(item)
        self.tree_items.clear()
        
        # Limpa métricas
        for card in self.metric_cards.values():
            card['value'].config(text="--", fg=COLORS['orange'])
        
        # Limpa detalhes por sistema
        for system_data in self.detail_trees.values():
            tree = system_data['tree']
            for item in tree.get_children():
                tree.delete(item)
            system_data['items'].clear()
        
        # Limpa abas de temperatura
        if hasattr(self, 'temp_trees'):
            for category_data in self.temp_trees.values():
                tree = category_data['tree']
                for item in tree.get_children():
                    tree.delete(item)
                # Reinsere linha vazia
                tree.insert("", tk.END, values=[""] * 6)
    
    def update_all_displays(self):
        """Atualiza todos os displays da interface."""
        try:
            # Atualiza métricas principais
            self._update_key_metrics()
            
            # Atualiza tabela principal (ordenada por timestamp)
            self._update_main_table()
            
            # Atualiza detalhes por sistema
            self._update_detail_tables()
            
            # Atualiza seção de temperaturas
            self._update_temperature_section()
            
            # Atualiza gráficos
            if MATPLOTLIB_AVAILABLE:
                self.graph_manager.update_all_graphs()
                
        except Exception as e:
            print(f"Erro ao atualizar interface: {e}")
    
    def _update_key_metrics(self):
        """Atualiza métricas principais."""
        metrics = self.data_manager.get_current_metrics()
        
        for key, value in metrics.items():
            if key in self.metric_cards:
                card = self.metric_cards[key]
                if key == 'temp_high' or key == 'temp_low':
                    # Cores baseadas na temperatura
                    if value > 70:
                        color = COLORS['warning']
                    else:
                        color = COLORS['orange']
                    card['value'].config(text=f"{value:.1f}", fg=color)
                else:
                    # Formato específico por métrica
                    if key == 'power':
                        card['value'].config(text=f"{value:.1f}")
                    else:
                        card['value'].config(text=f"{value:.2f}")
    
    def _update_main_table(self):
        """Atualiza tabela principal com ordenação por timestamp."""
        # Remove itens antigos
        for item in self.main_tree.get_children():
            self.main_tree.delete(item)
        
        # Obtém sinais ordenados por timestamp (mais recentes primeiro)
        sorted_signals = self.data_manager.get_sorted_signals()
        
        for signal_data in sorted_signals:
            timestamp = signal_data['timestamp']
            signal_name = signal_data['signal']
            value = signal_data['value']
            
            # Parse valor e unidade
            parts = value.split()
            val = parts[0]
            unit = ' '.join(parts[1:]) if len(parts) > 1 else ''
            
            # Converte timestamp para formato legível
            time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            
            values = (time_str, signal_name, val, unit)
            self.main_tree.insert("", 0, values=values)
    
    def _update_detail_tables(self):
        """Atualiza detalhes por sistema."""
        for system in SYSTEMS:
            if system in self.detail_trees:
                tree_data = self.detail_trees[system]
                tree = tree_data['tree']
                items = tree_data['items']
                
                # Limpa tree
                for item in tree.get_children():
                    tree.delete(item)
                
                # Obtém sinais do sistema
                system_signals = self.data_manager.get_system_signals(system)
                
                for signal_name in system_signals:
                    if signal_name in self.data_manager.latest_signal_values:
                        value = self.data_manager.latest_signal_values[signal_name]
                        tree.insert("", tk.END, values=(signal_name, value))
    
    def on_closing(self):
        """Evento de fechamento da janela."""
        if messagebox.askokcancel("Sair", "Deseja realmente sair do sistema?"):
            self.root.destroy()
    
    def start_ui_loop(self):
        """Inicia o loop principal da interface."""
        if self.root:
            self.root.mainloop()
