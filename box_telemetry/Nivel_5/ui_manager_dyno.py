"""
Sistema de Telemetria E-Racing UNICAMP - Interface Dinamômetro
Interface focada para testes no dinamômetro - VERSÃO CORRIGIDA
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from datetime import datetime
from PIL import Image, ImageTk
from config_dyno import *

# Verifica matplotlib
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class DynoTelemetryUI:
    """Interface principal para dinamômetro."""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.root = None
        
        # Elementos da UI
        self.main_tree = None
        self.metric_cards = {}
        self.block_trees = {}
        self.alert_labels = []
        
        # Gráficos
        self.graph_figures = {}
        self.graph_axes = {}
        self.graph_canvases = {}
        
        # Status
        self.status_var = None
        self.time_var = None
        self.analysis_mode_var = None
        
        # Controles
        self.analysis_running = False
        
        # Timer de atualização
        self.update_timer = None
        
        print("🖥️ Interface (Dinamômetro) inicializada")
    
    def create_main_window(self):
        """Cria janela principal."""
        if self.root is not None:
            print("⚠️ Janela já existe, retornando janela existente")
            return self.root
            
        print("🖥️ Criando root window...")
        self.root = tk.Tk()
        print("✅ Root window criado")
        
        self.root.title("E-Racing UNICAMP - Telemetria Dinamômetro")
        self.root.geometry("1400x900")
        self.root.configure(bg=COLORS['bg_dark'])
        
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.resizable(True, True)
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        print("🔧 Configurando layout da janela...")
        print("🗂️ Construindo interface...")
        
        # Constrói interface
        self._build_header()
        print("  ✅ Header construído")
        
        self._build_main_content()
        print("  ✅ Conteúdo principal construído")
        
        # FORÇAR A JANELA A APARECER
        print("🔧 Tornando janela visível...")
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        
        # INICIA ATUALIZAÇÃO AUTOMÁTICA DA UI
        self._start_ui_updates()
        
        print("✅ Interface completa criada e visível!")
        print(f"📊 Janela: {self.root.title()}")
        print(f"📏 Tamanho: {self.root.geometry()}")
        
        return self.root
    
    def _start_ui_updates(self):
        """Inicia loop de atualização da UI."""
        def update_loop():
            try:
                self.update_all_displays()
            except Exception as e:
                print(f"Erro na atualização da UI: {e}")
            finally:
                # Reagenda atualização
                if self.root and self.root.winfo_exists():
                    self.update_timer = self.root.after(UI_UPDATE_INTERVAL_MS, update_loop)
        
        # Inicia o loop
        update_loop()
        print("🔄 Loop de atualização da UI iniciado")
    
    def _build_header(self):
        """Constrói cabeçalho."""
        header_frame = tk.Frame(self.root, bg=COLORS['bg_dark'], height=100)
        header_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        header_frame.grid_propagate(False)
        
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(2, weight=1)
        
        # Logo e título
        header_content = tk.Frame(header_frame, bg=COLORS['bg_dark'])
        header_content.grid(row=0, column=0, sticky='w', padx=20, pady=15)
        
        self._create_logo_and_title(header_content)
        
        # Controles
        self._create_analysis_controls(header_frame)
        
        # Status
        self._create_status_and_time(header_frame)
        
        # Separador
        separator = tk.Frame(self.root, bg=COLORS['orange'], height=3)
        separator.grid(row=2, column=0, sticky='ew')
    
    def _create_logo_and_title(self, parent):
        """Cria logo e título."""
        logo_frame = tk.Frame(parent, bg=COLORS['bg_dark'])
        logo_frame.pack(side=tk.LEFT, padx=(0, 20))
        
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
            font=("Arial Black", 22, "bold")
        )
        eracing_label.pack(anchor=tk.W)
        
        subtitle = tk.Label(
            title_container,
            text="TELEMETRY DYNO • Real-Time Motor Testing",
            bg=COLORS['bg_dark'],
            fg=COLORS['gray_light'],
            font=("Arial", 11)
        )
        subtitle.pack(anchor=tk.W)
    
    def _create_text_logo(self, parent):
        """Logo em texto."""
        text_logo = tk.Label(parent, text="🏎️", bg=COLORS['bg_dark'], 
                            fg=COLORS['orange'], font=("Arial", 40))
        text_logo.pack()
    
    def _create_analysis_controls(self, parent):
        """Controles de análise."""
        controls_frame = tk.Frame(parent, bg=COLORS['bg_dark'])
        controls_frame.grid(row=0, column=1, sticky='', padx=20, pady=15)
        
        # Modo
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
        
        # Botões
        buttons_frame = tk.Frame(controls_frame, bg=COLORS['bg_dark'])
        buttons_frame.pack(side=tk.RIGHT)
        
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
        
        export_btn = tk.Button(
            buttons_frame,
            text="💾 Exportar",
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
        """Status e tempo."""
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
        
        def update_clock():
            if self.root and self.root.winfo_exists():
                self.time_var.set(datetime.now().strftime("%H:%M:%S"))
                self.root.after(1000, update_clock)
        update_clock()
    
    def _build_main_content(self):
        """Conteúdo principal."""
        main_container = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main_container.grid(row=1, column=0, sticky='nsew', padx=15, pady=15)
        
        main_container.grid_columnconfigure(0, weight=3)
        main_container.grid_columnconfigure(1, weight=2)
        main_container.grid_rowconfigure(0, weight=1)
        
        # Colunas
        left_column = tk.Frame(main_container, bg=COLORS['bg_dark'])
        left_column.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
        right_column = tk.Frame(main_container, bg=COLORS['bg_dark'])
        right_column.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        
        left_column.grid_columnconfigure(0, weight=1)
        left_column.grid_rowconfigure(0, weight=0)  # Alertas
        left_column.grid_rowconfigure(1, weight=1)  # Gráficos
        left_column.grid_rowconfigure(2, weight=0)  # Status Motores
        
        right_column.grid_columnconfigure(0, weight=1)
        right_column.grid_rowconfigure(0, weight=0)  # Métricas
        right_column.grid_rowconfigure(1, weight=1)  # Todos sinais
        right_column.grid_rowconfigure(2, weight=1)  # Detalhes por bloco
        
        # Seções esquerda
        self._build_alerts_section(left_column)
        if MATPLOTLIB_AVAILABLE:
            self._build_graphs_section(left_column)
        self._build_motor_status_section(left_column)
        
        # Seções direita
        self._build_key_metrics(right_column)
        self._build_main_table(right_column)
        self._build_block_details(right_column)
    
    def _build_alerts_section(self, parent):
        """Seção de alertas com scroll."""
        section_frame = self._create_section(parent, "⚠️  ALERTAS DO SISTEMA", height=120)
        parent.grid_rowconfigure(0, weight=0)
        
        # Frame com canvas para scroll
        canvas = tk.Canvas(section_frame, bg=COLORS['bg_light'], 
                          highlightthickness=0, height=90)
        scrollbar = tk.Scrollbar(section_frame, orient="vertical", 
                                command=canvas.yview)
        
        self.alerts_frame = tk.Frame(canvas, bg=COLORS['bg_light'])
        
        # Configura scroll
        self.alerts_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.alerts_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Label padrão
        no_alerts = tk.Label(
            self.alerts_frame,
            text="✅ NENHUM ALERTA ATIVO",
            bg=COLORS['bg_light'],
            fg=COLORS['safe'],
            font=("Arial", 12, "bold")
        )
        no_alerts.pack(pady=20)
        self.alert_labels.append(no_alerts)
    
    def _build_graphs_section(self, parent):
        """Seção de gráficos."""
        content = self._create_section(parent, "📊  GRÁFICOS EM TEMPO REAL", height=450)
        parent.grid_rowconfigure(1, weight=1)
        
        # Notebook
        style = ttk.Style()
        style.configure("Dyno.TNotebook", background=COLORS['bg_light'])
        style.configure("Dyno.TNotebook.Tab",
                       background=COLORS['bg_medium'],
                       foreground=COLORS['white'],
                       padding=[12, 5],
                       font=("Arial", 9, "bold"))
        style.map("Dyno.TNotebook.Tab",
                 background=[("selected", COLORS['orange'])],
                 foreground=[("selected", COLORS['white'])])
        
        self.graph_notebook = ttk.Notebook(content, style="Dyno.TNotebook")
        self.graph_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Abas de gráficos
        self._create_scrollable_graph(self.graph_notebook, "🔄 RPM", "RPM", "rpm")
        self._create_scrollable_graph(self.graph_notebook, "⚡ Torque", "Torque (Nm)", "torque")
        self._create_scrollable_graph(self.graph_notebook, "💪 Potência", "Potência (kW)", "power")
        self._create_scrollable_graph(self.graph_notebook, "🌡️ Temperaturas", "Temperatura (°C)", "temperature")
        self._create_scrollable_graph(self.graph_notebook, "🔋 DC Bus", "Tensão (V)", "voltage")
        self._create_scrollable_graph(self.graph_notebook, "🦶 Pedal", "Pedal (%)", "pedal")
    
    def _create_scrollable_graph(self, notebook, title, ylabel, graph_key):
        """Cria um gráfico com scroll horizontal."""
        tab = tk.Frame(notebook, bg=COLORS['bg_light'])
        notebook.add(tab, text=title)
        
        # Frame para canvas e scrollbar
        graph_frame = tk.Frame(tab, bg=COLORS['bg_light'])
        graph_frame.pack(fill=tk.BOTH, expand=True)
        
        fig = Figure(figsize=(20, 3.5),
                    facecolor=COLORS['bg_light'], 
                    dpi=GRAPH_CONFIG['dpi'])
        fig.subplots_adjust(left=0.05, right=0.98, top=0.92, bottom=0.12)
        
        ax = fig.add_subplot(111)
        self._setup_axis_style(ax, ylabel, 'Tempo (s)')
        
        self.graph_figures[graph_key] = fig
        self.graph_axes[graph_key] = ax
        
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        
        # Scrollbar horizontal
        scrollbar = tk.Scrollbar(graph_frame, orient=tk.HORIZONTAL)
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.graph_canvases[graph_key] = canvas
    
    def _setup_axis_style(self, ax, ylabel, xlabel):
        """Configura estilo do eixo."""
        ax.set_facecolor(COLORS['bg_medium'])
        ax.tick_params(colors=COLORS['gray'], labelsize=8)
        ax.grid(True, alpha=0.15, color=COLORS['gray'])
        ax.spines['bottom'].set_color(COLORS['orange'])
        ax.spines['left'].set_color(COLORS['orange'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_xlabel(xlabel, color=COLORS['gray'], fontsize=9)
        ax.set_ylabel(ylabel, color=COLORS['gray'], fontsize=9)
    
    def _build_motor_status_section(self, parent):
        """Status resumido dos motores - MAIOR."""
        content = self._create_section(parent, "🏎️  STATUS DOS MOTORES", height=140)  # Aumentado de 100 para 140
        parent.grid_rowconfigure(2, weight=0)
        
        status_grid = tk.Frame(content, bg=COLORS['bg_light'])
        status_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Grid 2x2 para os 4 motores
        motors = [
            ('A0', 'FD', 0, 0),   # Frente Direita
            ('A13', 'FE', 0, 1),  # Frente Esquerda
            ('B0', 'TD', 1, 0),   # Traseira Direita
            ('B13', 'TE', 1, 1),  # Traseira Esquerda
        ]
        
        self.motor_status_labels = {}
        
        for motor_id, pos, row, col in motors:
            frame = tk.Frame(status_grid, bg=COLORS['bg_medium'], 
                           relief=tk.FLAT, bd=1,
                           highlightbackground=MOTOR_COLORS[motor_id],
                           highlightthickness=2)
            frame.grid(row=row, column=col, padx=4, pady=4, sticky='nsew')
            
            # Label com nome do motor - MAIOR
            name_label = tk.Label(frame, 
                           text=f"MTR {motor_id} ({pos})",
                           bg=COLORS['bg_medium'],
                           fg=MOTOR_COLORS[motor_id],
                           font=("Arial", 11, "bold"))  # Aumentado de 9 para 11
            name_label.pack(pady=(8, 2))  # Mais padding
            
            # Label com dados - MAIOR
            data_label = tk.Label(frame, 
                           text="---\n---",
                           bg=COLORS['bg_medium'],
                           fg=COLORS['white'],
                           font=("Arial", 10),  # Aumentado de 8 para 10
                           justify=tk.CENTER)
            data_label.pack(pady=(0, 8))  # Mais padding
            
            self.motor_status_labels[motor_id] = data_label
        
        status_grid.grid_rowconfigure(0, weight=1)
        status_grid.grid_rowconfigure(1, weight=1)
        status_grid.grid_columnconfigure(0, weight=1)
        status_grid.grid_columnconfigure(1, weight=1)
    
    def _build_key_metrics(self, parent):
        """Métricas principais (9 itens)."""
        content = self._create_section(parent, "🎯  MÉTRICAS PRINCIPAIS", height=280)
        parent.grid_rowconfigure(0, weight=0)
        
        metrics_grid = tk.Frame(content, bg=COLORS['bg_light'])
        metrics_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.metric_cards = {}
        
        # Grid 3x3
        for idx, (key, label, unit) in enumerate(KEY_METRICS):
            row = idx // 3
            col = idx % 3
            card = self._create_metric_card(metrics_grid, label, unit)
            card['frame'].grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
            self.metric_cards[key] = card
        
        for i in range(3):
            metrics_grid.grid_rowconfigure(i, weight=1)
            metrics_grid.grid_columnconfigure(i, weight=1)
    
    def _create_metric_card(self, parent, label, unit):
        """Cria card de métrica."""
        card = tk.Frame(parent, bg=COLORS['bg_medium'], relief=tk.FLAT,
                       highlightbackground=COLORS['orange'], highlightthickness=1)
        
        label_widget = tk.Label(card, text=label, bg=COLORS['bg_medium'],
                               fg=COLORS['gray_light'], font=("Arial", 7, "bold"))
        label_widget.pack(pady=(5, 1))
        
        value_widget = tk.Label(card, text="--", bg=COLORS['bg_medium'],
                               fg=COLORS['orange'], font=("Arial", 16, "bold"))
        value_widget.pack()
        
        unit_widget = tk.Label(card, text=unit, bg=COLORS['bg_medium'],
                              fg=COLORS['gray'], font=("Arial", 8))
        unit_widget.pack(pady=(0, 5))
        
        return {'frame': card, 'value': value_widget, 'label': label_widget}
    
    def _build_main_table(self, parent):
        """Tabela de todos os sinais."""
        content = self._create_section(parent, "📋  TODOS OS SINAIS (RAW)")
        parent.grid_rowconfigure(1, weight=1)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Dyno.Treeview",
            background=COLORS['bg_light'],
            foreground=COLORS['white'],
            fieldbackground=COLORS['bg_light'],
            borderwidth=0,
            font=("Arial", 8)
        )
        style.configure("Dyno.Treeview.Heading", 
                       background=COLORS['bg_medium'],
                       foreground=COLORS['orange'],
                       font=("Arial", 9, "bold"))
        style.map('Dyno.Treeview', background=[('selected', COLORS['orange_dark'])])
        
        columns = ('signal', 'value', 'min', 'max')
        self.main_tree = ttk.Treeview(
            content, 
            columns=columns, 
            show='headings', 
            height=10,
            style="Dyno.Treeview"
        )
        
        self.main_tree.heading('signal', text='SINAL')
        self.main_tree.column('signal', anchor=tk.W, width=180)
        self.main_tree.heading('value', text='VALOR')
        self.main_tree.column('value', anchor=tk.E, width=100)
        self.main_tree.heading('min', text='MÍNIMO')
        self.main_tree.column('min', anchor=tk.E, width=80)
        self.main_tree.heading('max', text='MÁXIMO')
        self.main_tree.column('max', anchor=tk.E, width=80)
        
        vsb = ttk.Scrollbar(content, orient="vertical", command=self.main_tree.yview)
        self.main_tree.configure(yscrollcommand=vsb.set)
        
        self.main_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _build_block_details(self, parent):
        """Detalhes por bloco VCU."""
        content = self._create_section(parent, "🔧  DETALHES POR BLOCO VCU")
        parent.grid_rowconfigure(2, weight=1)
        
        # Notebook
        style = ttk.Style()
        style.configure("Block.TNotebook", background=COLORS['bg_light'])
        style.configure("Block.TNotebook.Tab",
                       background=COLORS['bg_medium'],
                       foreground=COLORS['white'],
                       padding=[8, 4],
                       font=("Arial", 8, "bold"))
        style.map("Block.TNotebook.Tab",
                 background=[("selected", COLORS['orange'])],
                 foreground=[("selected", COLORS['white'])])
        
        self.block_notebook = ttk.Notebook(content, style="Block.TNotebook")
        self.block_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Cria aba para cada bloco
        for block in VCU_BLOCKS:
            self._create_block_tab(block)
    
    def _create_block_tab(self, block):
        """Cria aba para bloco."""
        tab = tk.Frame(self.block_notebook, bg=COLORS['bg_light'])
        
        # Nome curto para aba
        short_name = block.replace('Status of the master control', 'Master')
        short_name = short_name.replace('Device status of the MOBILE', 'Device')
        short_name = short_name.replace('Actual values from motor', 'Act')
        short_name = short_name.replace('Setpoints for motor', 'Setp')
        short_name = short_name.replace('SETPOINTS CONTROL MOBILE', 'Ctrl')
        
        self.block_notebook.add(tab, text=short_name)
        
        tree = ttk.Treeview(tab, columns=('signal', 'value'), 
                          show='headings', height=8, 
                          style="Dyno.Treeview")
        tree.heading('signal', text='SINAL')
        tree.column('signal', width=180)
        tree.heading('value', text='VALOR')
        tree.column('value', width=100)
        
        vsb = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.block_trees[block] = tree
    
    def _create_section(self, parent, title, height=None):
        """Cria seção com título."""
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
            font=("Arial", 10, "bold"),
            anchor=tk.W,
            padx=12,
            pady=8
        )
        header.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        content = tk.Frame(section, bg=COLORS['bg_light'])
        content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        return content
    
    def toggle_analysis(self):
        """Inicia/para análise."""
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
        """Reseta análise."""
        if messagebox.askyesno("Confirmar", "Deseja realmente zerar toda a análise?\nIsso apagará todos os dados atuais."):
            self.data_manager.reset_analysis()
            self.analysis_mode_var.set("⏸️ Pausado")
            self.start_stop_btn.config(text="▶️ Iniciar", bg=COLORS['bg_medium'])
            self.analysis_running = False
            self.status_var.set("🔄 Análise zerada")
            self._clear_all_displays()
    
    def export_data(self):
        """Exporta dados."""
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
        if self.main_tree:
            for item in self.main_tree.get_children():
                self.main_tree.delete(item)
        
        # Limpa métricas
        for card in self.metric_cards.values():
            card['value'].config(text="--", fg=COLORS['orange'])
        
        # Limpa blocos
        for tree in self.block_trees.values():
            for item in tree.get_children():
                tree.delete(item)
        
        # Limpa alertas
        for widget in self.alerts_frame.winfo_children():
            widget.destroy()
        self.alert_labels.clear()
        
        no_alerts = tk.Label(
            self.alerts_frame,
            text="✅ NENHUM ALERTA ATIVO",
            bg=COLORS['bg_light'],
            fg=COLORS['safe'],
            font=("Arial", 12, "bold")
        )
        no_alerts.pack(pady=20)
        self.alert_labels.append(no_alerts)
        
        # Limpa status dos motores
        for label in self.motor_status_labels.values():
            label.config(text="---\n---")
    
    def update_all_displays(self):
        """Atualiza todos os displays - CORRIGIDO."""
        try:
            # Verifica se a janela ainda existe
            if not self.root or not self.root.winfo_exists():
                return
            
            # Atualiza métricas
            self._update_key_metrics()
            
            # Atualiza tabela principal
            self._update_main_table()
            
            # Atualiza blocos
            self._update_block_details()
            
            # Atualiza alertas
            self._update_alerts()
            
            # Atualiza status motores
            self._update_motor_status()
            
            # Atualiza gráficos
            if MATPLOTLIB_AVAILABLE:
                self._update_all_graphs()
                
        except Exception as e:
            print(f"Erro ao atualizar interface: {e}")
    
    def _update_key_metrics(self):
        """Atualiza métricas principais."""
        metrics = self.data_manager.get_current_metrics()
        
        for key, value in metrics.items():
            if key in self.metric_cards:
                card = self.metric_cards[key]
                
                # Formatação específica
                if 'temp' in key:
                    if value > TEMP_LIMITS['motor_danger']:
                        color = COLORS['red']
                    elif value > TEMP_LIMITS['motor_warning']:
                        color = COLORS['yellow']
                    else:
                        color = COLORS['safe']
                    card['value'].config(text=f"{value:.0f}", fg=color)
                elif 'rpm' in key:
                    card['value'].config(text=f"{value:.0f}", fg=COLORS['orange'])
                elif 'torque' in key:
                    card['value'].config(text=f"{value:.1f}", fg=COLORS['blue'])
                elif 'power' in key:
                    card['value'].config(text=f"{value:.1f}", fg=COLORS['purple'])
                elif 'voltage' in key or 'dc' in key:
                    card['value'].config(text=f"{value:.1f}", fg=COLORS['cyan'])
                elif 'aps' in key or 'pedal' in key:
                    card['value'].config(text=f"{value:.1f}", fg=COLORS['green'])
                else:
                    card['value'].config(text=f"{value:.1f}", fg=COLORS['orange'])
    
    def _update_main_table(self):
        """Atualiza tabela principal - CORRIGIDO."""
        if not self.main_tree:
            return
            
        # Limpa
        for item in self.main_tree.get_children():
            self.main_tree.delete(item)
        
        # Pega todos os sinais
        try:
            with self.data_manager.data_lock:
                signals_dict = dict(self.data_manager.latest_signal_values)
            
            for signal_name, value in signals_dict.items():
                # Pega min e max
                min_val, max_val = self.data_manager.get_signal_min_max(signal_name)
                
                # Formata valores
                try:
                    val_display = value.split()[0]
                    min_display = f"{min_val:.2f}" if min_val != 0 else "---"
                    max_display = f"{max_val:.2f}" if max_val != 0 else "---"
                except:
                    val_display = value
                    min_display = "---"
                    max_display = "---"
                
                values = (signal_name, val_display, min_display, max_display)
                self.main_tree.insert("", tk.END, values=values)
                
        except Exception as e:
            print(f"Erro ao atualizar tabela: {e}")
    
    def _update_block_details(self):
        """Atualiza detalhes por bloco - CORRIGIDO."""
        try:
            for block, tree in self.block_trees.items():
                # Limpa
                for item in tree.get_children():
                    tree.delete(item)
                
                # Pega sinais do bloco
                signals = self.data_manager.get_block_signals(block)
                
                with self.data_manager.data_lock:
                    for signal in signals:
                        if signal in self.data_manager.latest_signal_values:
                            value = self.data_manager.latest_signal_values[signal]
                            tree.insert("", tk.END, values=(signal, value))
        except Exception as e:
            print(f"Erro ao atualizar blocos: {e}")
    
    def _update_alerts(self):
        """Atualiza alertas."""
        # Limpa
        for widget in self.alerts_frame.winfo_children():
            widget.destroy()
        self.alert_labels.clear()
        
        # Pega alertas ativos
        alerts = self.data_manager.get_active_alerts()
        
        if not alerts:
            no_alerts = tk.Label(
                self.alerts_frame,
                text="✅ NENHUM ALERTA ATIVO",
                bg=COLORS['bg_light'],
                fg=COLORS['safe'],
                font=("Arial", 12, "bold")
            )
            no_alerts.pack(pady=20)
            self.alert_labels.append(no_alerts)
        else:
            for signal, alert in alerts.items():
                color = COLORS['red'] if alert['type'] == 'error' else COLORS['yellow']
                icon = "❌" if alert['type'] == 'error' else "⚠️"
                
                alert_label = tk.Label(
                    self.alerts_frame,
                    text=f"{icon} {alert['msg']}: {alert['value']}",
                    bg=COLORS['bg_light'],
                    fg=color,
                    font=("Arial", 9, "bold")
                )
                alert_label.pack(anchor=tk.W, padx=10, pady=2)
                self.alert_labels.append(alert_label)
    
    def _update_motor_status(self):
        """Atualiza status resumido dos motores - CORRIGIDO."""
        motors = ['A0', 'B0', 'A13', 'B13']
        
        try:
            with self.data_manager.data_lock:
                for motor_id in motors:
                    if motor_id in self.motor_status_labels:
                        label = self.motor_status_labels[motor_id]
                        
                        # Busca RPM e temperatura
                        rpm_signal = f'ACT_SPEED {motor_id}'
                        temp_signal = f'ACT_MOTORTEMPERATURE {motor_id}'
                        
                        rpm = "---"
                        temp = "---"
                        
                        if rpm_signal in self.data_manager.latest_signal_values:
                            try:
                                rpm_val = float(self.data_manager.latest_signal_values[rpm_signal].split()[0])
                                rpm = f"{rpm_val:.0f} rpm"
                            except:
                                pass
                        
                        if temp_signal in self.data_manager.latest_signal_values:
                            try:
                                temp_val = float(self.data_manager.latest_signal_values[temp_signal].split()[0])
                                temp = f"{temp_val:.0f}°C"
                            except:
                                pass
                        
                        # Atualiza
                        text = f"{rpm}\n{temp}"
                        label.config(text=text)
        except Exception as e:
            print(f"Erro ao atualizar status motores: {e}")
    
    def _update_all_graphs(self):
        """Atualiza todos os gráficos - CORRIGIDO."""
        try:
            self._update_rpm_graph()
            self._update_torque_graph()
            self._update_power_graph()
            self._update_temperature_graph()
            self._update_voltage_graph()
            self._update_pedal_graph()
            
            # Redesenha
            for canvas in self.graph_canvases.values():
                try:
                    canvas.draw_idle()
                except:
                    pass
        except Exception as e:
            print(f"Erro ao atualizar gráficos: {e}")
    
    def _plot_motor_signals(self, ax, ylabel, signals_config):
        """Helper genérico para plotar sinais dos motores - GRÁFICOS CRESCEM."""
        ax.clear()
        self._setup_axis_style(ax, ylabel, 'Tempo (s)')
        
        min_time = None
        max_time = None
        has_data = False
        
        for signal, label, color in signals_config:
            data = self.data_manager.get_signal_data(signal)
            times = self.data_manager.get_time_data(signal)
            
            if data and times and len(data) > 1:
                if min_time is None:
                    min_time = times[0]
                    max_time = times[-1]
                else:
                    min_time = min(min_time, times[0])
                    max_time = max(max_time, times[-1])
                
                times_norm = [(t - min_time) for t in times]
                
                ax.plot(times_norm, data, 
                       label=label,
                       color=color,
                       linewidth=GRAPH_CONFIG['line_width'],
                       alpha=GRAPH_CONFIG['alpha'])
                has_data = True
        
        if has_data:
            # Define limites do eixo X para crescer continuamente
            if max_time and min_time:
                time_range = max_time - min_time
                # IMPORTANTE: xlim cresce com o tempo, não fica fixo
                ax.set_xlim(0, max(time_range, 10))  # Mínimo de 10s visível
            
            ax.legend(loc='upper left', fontsize=7, facecolor=COLORS['bg_dark'],
                     edgecolor=COLORS['orange'], labelcolor=COLORS['white'], framealpha=0.9)
    
    def _update_rpm_graph(self):
        """Atualiza gráfico de RPM."""
        if 'rpm' not in self.graph_axes:
            return
        
        motors = [
            ('ACT_SPEED A0', FRIENDLY_NAMES['A0'], MOTOR_COLORS['A0']),
            ('ACT_SPEED B0', FRIENDLY_NAMES['B0'], MOTOR_COLORS['B0']),
            ('ACT_SPEED A13', FRIENDLY_NAMES['A13'], MOTOR_COLORS['A13']),
            ('ACT_SPEED B13', FRIENDLY_NAMES['B13'], MOTOR_COLORS['B13']),
        ]
        
        self._plot_motor_signals(self.graph_axes['rpm'], 'RPM', motors)
    
    def _update_torque_graph(self):
        """Atualiza gráfico de Torque."""
        if 'torque' not in self.graph_axes:
            return
        
        motors = [
            ('ACT_TORQUE A0', FRIENDLY_NAMES['A0'], MOTOR_COLORS['A0']),
            ('ACT_TORQUE B0', FRIENDLY_NAMES['B0'], MOTOR_COLORS['B0']),
            ('ACT_TORQUE A13', FRIENDLY_NAMES['A13'], MOTOR_COLORS['A13']),
            ('ACT_TORQUE B13', FRIENDLY_NAMES['B13'], MOTOR_COLORS['B13']),
        ]
        
        self._plot_motor_signals(self.graph_axes['torque'], 'Torque (Nm)', motors)
    
    def _update_power_graph(self):
        """Atualiza gráfico de Potência."""
        if 'power' not in self.graph_axes:
            return
        
        motors = [
            ('ACT_POWER A0', FRIENDLY_NAMES['A0'], MOTOR_COLORS['A0']),
            ('ACT_POWER B0', FRIENDLY_NAMES['B0'], MOTOR_COLORS['B0']),
            ('ACT_POWER A13', FRIENDLY_NAMES['A13'], MOTOR_COLORS['A13']),
            ('ACT_POWER B13', FRIENDLY_NAMES['B13'], MOTOR_COLORS['B13']),
        ]
        
        self._plot_motor_signals(self.graph_axes['power'], 'Potência (kW)', motors)
    
    def _update_temperature_graph(self):
        """Atualiza gráfico de Temperaturas."""
        if 'temperature' not in self.graph_axes:
            return
        
        # Motores + Inversores
        sensors = [
            ('ACT_MOTORTEMPERATURE A0', 'Motor A0', MOTOR_COLORS['A0']),
            ('ACT_MOTORTEMPERATURE B0', 'Motor B0', MOTOR_COLORS['B0']),
            ('ACT_MOTORTEMPERATURE A13', 'Motor A13', MOTOR_COLORS['A13']),
            ('ACT_MOTORTEMPERATURE B13', 'Motor B13', MOTOR_COLORS['B13']),
            ('ACT_DEVICETEMPERATURE M0', 'Inv M0', COLORS['cyan']),
            ('ACT_DEVICETEMPERATURE M13', 'Inv M13', COLORS['yellow']),
        ]
        
        self._plot_motor_signals(self.graph_axes['temperature'], 'Temperatura (°C)', sensors)
    
    def _update_voltage_graph(self):
        """Atualiza gráfico de DC Bus."""
        if 'voltage' not in self.graph_axes:
            return
        
        voltages = [
            ('ACT_DCBUSVOLTAGE M0', 'DC Bus M0', COLORS['cyan']),
            ('ACT_DCBUSVOLTAGE M13', 'DC Bus M13', COLORS['yellow']),
        ]
        
        self._plot_motor_signals(self.graph_axes['voltage'], 'Tensão DC (V)', voltages)
    
    def _update_pedal_graph(self):
        """Atualiza gráfico de Pedal."""
        if 'pedal' not in self.graph_axes:
            return
        
        pedal = [
            ('APS_PERC', 'APS', COLORS['green']),
        ]
        
        self._plot_motor_signals(self.graph_axes['pedal'], 'Pedal (%)', pedal)
    
    def on_closing(self):
        """Evento de fechamento."""
        # Cancela timer de atualização
        if self.update_timer:
            try:
                self.root.after_cancel(self.update_timer)
            except:
                pass
        
        if self.root and self.root.winfo_exists():
            if messagebox.askokcancel("Sair", "Deseja realmente sair do sistema?"):
                try:
                    self.root.destroy()
                except:
                    pass
    
    def start_ui_loop(self):
        """Inicia loop da interface."""
        if self.root:
            self.root.mainloop()