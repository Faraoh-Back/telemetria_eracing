#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from std_msgs.msg import String
import json
import tkinter as tk
from tkinter import ttk

root = tk.Tk()

class StaticDisplay(ttk.LabelFrame):
    def __init__(self, parent, title="Valor", unit="", **kwargs):
        super().__init__(parent, text=title, padding=10, **kwargs)
        self.var = tk.StringVar(value=f"0 {unit}")
        self.label = ttk.Label(
            self,
            textvariable=self.var,
            font=("Helvetica", 12),
            anchor="center"
        )
        self.label.pack(expand=True, fill="both")

    def update(self, value: float):
        self.var.set(f"{value:.2f}")

class Application:
    def __init__(self):
        self.root = root
        self._build_ui()
        self._build_ros()
        # inicia o ciclo integrado ROS ↔ Tk
        self.root.after(50, self._ros_spin_once)

        # cria os 3 displays, mas só o primeiro será atualizado
        self.disp = StaticDisplay(root, title="Velocidade", unit="Km/h")
        self.disp2 = StaticDisplay(root, title="Tensão de alta", unit="V")
        self.disp3 = StaticDisplay(root, title="Tensão de baixa", unit="V")

        self.disp.place( relx=0.03, rely=0.03, relwidth=0.1, relheight=0.1)
        self.disp2.place(relx=0.13, rely=0.03, relwidth=0.1, relheight=0.1)
        self.disp3.place(relx=0.23, rely=0.03, relwidth=0.1, relheight=0.1)

        # restante da UI (Treeview etc.)
        self.frames_da_tela()
        self.lista_frame2()
        self.lista_frame()
        self.lista_frame3()

        # depois de self.listacl1.place(...)
        self.tree_items = []
        self.tree_items2 = []

        # insere 10 linhas vazias
        for _ in range(10):
            item_id = self.listacl1.insert(
                '', 'end',
                values=("0.00", "0.00")
            )
            self.tree_items.append(item_id)
        for _ in range(10):
            item_id = self.listacl2.insert(
                '', 'end',
                values=("0.00", "0.00", "0.00", "0.00")
            )
            self.tree_items2.append(item_id)
     # insere 10 linhas vazias em listacl3
        self.tree_items3 = []
        for _ in range(10):
            item_id = self.listacl3.insert('', 'end', values=("", ""))
            self.tree_items3.append(item_id)



    def _build_ui(self):
        self.root.configure(background='#ADD8E6')
        self.root.title("Telemetria")
        self.root.geometry("1280x720")
        self.root.minsize(640,360)

    def _build_ros(self):
        # inicializa o nó ROS e inscreve no tópico
        self.node = Node('float_subscriber')
        self.node.create_subscription(
            String,
            'telemetria',
            self.listener_callback,
            10
        )

    def _ros_spin_once(self):
        # processa callbacks ROS sem bloquear o Tk
        rclpy.spin_once(self.node, timeout_sec=0)
        self.root.after(50, self._ros_spin_once)

    def listener_callback(self, msg: String):
        data = json.loads(msg.data)

        # Atualiza displays simples
        self.disp.update(data["Velocidade"]["value"])
        self.disp2.update(data["Tensao_pack_alta"]["value"])
        self.disp3.update(data["Tensao_pack_baixa"]["value"])

        def to_items(val):
            if isinstance(val, dict):
                return list(val.items())
            elif isinstance(val, list):
                return [(str(i), v) for i, v in enumerate(val)]
            else:
                return []

        # Tensões células alta → ordena
        Vcel_a_items = to_items(data["Tensoes_celulas_alta"]["values"])
        Vcel_a_sorted = sorted(Vcel_a_items, key=lambda x: x[1])[:10]

        # Tensões células baixa → ordena
        Vcel_b_items = to_items(data["Tensoes_celulas_baixa"]["values"])
        Vcel_b_sorted = sorted(Vcel_b_items, key=lambda x: x[1])[:10]

        # Temperaturas
        t_pack_items = to_items(data["Temps_pack"]["values"])
        t_pack_sorted = sorted(t_pack_items, key=lambda x: x[1])[:10]

        t_pack_h_items = to_items(data["Temps_pack_alta"]["values"])
        t_pack_h_sorted = sorted(t_pack_h_items, key=lambda x: x[1])[:10]

        t_motores_items = to_items(data["Temps_motores"]["values"])
        t_motores_sorted = sorted(t_motores_items, key=lambda x: x[1])[:10]

        t_inversores_items = to_items(data["Temps_inversores"]["values"])
        t_inversores_sorted = sorted(t_inversores_items, key=lambda x: x[1])[:10]

        # Atualiza trees passando ids e valores
        self.update_tree1(Vcel_a_sorted, Vcel_b_sorted)
        self.update_tree2(t_pack_h_sorted, t_pack_sorted)
        self.update_tree3(t_motores_sorted, t_inversores_sorted)




    def frames_da_tela(self):
        self.frame = tk.Frame(self.root)
        self.frame.place(relx=0.4, rely=0.02, relwidth=0.3, relheight=0.35)

        self.frame_2 = tk.Frame(self.root)
        self.frame_2.place(relx=0.7, rely=0.02, relwidth=0.3, relheight=0.35)
        self.frame_3 = tk.Frame(self.root)
        self.frame_3.place(relx=0.6, rely=0.37, relwidth=0.4, relheight=0.35)
    def lista_frame2(self):
        self.listacl2 = ttk.Treeview(
            self.frame_2,
            height=10,
            columns=("col1","col2"),
            show="headings"                      # esconde a coluna #0
        )
        self.listacl2.heading("#0", text="")        
        self.listacl2.heading("#2", text="T° Células baixa")
        self.listacl2.heading("col1", text="T° Células alta")
        self.listacl2.place(relx=0.01, rely=0.03, relwidth=0.95, relheight=0.90)
        scrollbar = ttk.Scrollbar(self.frame_2, orient="vertical", command=self.listacl2.yview)
        self.listacl2.configure(yscroll=scrollbar.set)
        scrollbar.place(relx=0.96, rely=0.1, relwidth=0.04, relheight=0.85)
    def lista_frame(self):
        self.listacl1 = ttk.Treeview(self.frame, height=3, columns=("col0","col1","col2"))
        self.listacl1.heading("#1", text="V Cel Alta")
        self.listacl1.heading("#2", text="V Cel baixa")
        self.listacl1.heading("#0", text="")

        self.listacl1.column("col1", width= 100, anchor="center")
        self.listacl1.column("col2", width=100, anchor="center")
        self.listacl1.column("col0", width= 0, anchor="center")
        self.listacl1.place(relx=0.01, rely=0.03, relwidth=0.95, relheight=0.90)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.listacl1.yview)
        self.listacl1.configure(yscroll=scrollbar.set)
        scrollbar.place(relx=0.96, rely=0.1, relwidth=0.04, relheight=0.85)
    def lista_frame3(self):
        self.listacl3 = ttk.Treeview(self.frame_3, height=10, columns=("col0","col1","col2"))
        self.listacl3.heading("#0", text="")        
        self.listacl3.heading("#1", text="T° Motores")
        self.listacl3.heading("#2", text="T° Inversores")
        self.listacl3.column("col0", width= 0, anchor="center")
        self.listacl3.column("col1", width= 100, anchor="center")
        self.listacl3.column("col2", width= 100, anchor="center")
        self.listacl3.place(relx=0.01, rely=0.03, relwidth=0.95, relheight=0.90)
        
        scrollbar = ttk.Scrollbar(self.frame_2, orient="vertical", command=self.listacl2.yview)
        self.listacl3.configure(yscroll=scrollbar.set)
        scrollbar.place(relx=0.96, rely=0.1, relwidth=0.04, relheight=0.85)
    def update_tree1(self, cela, celb):
        # cela e celb são listas de [(id, valor)]
        # preenche celb se for menor que 10
        celb += [("N/A", 0.0)] * (10 - len(celb))

        for idx, item_id in enumerate(self.tree_items):
            id_alta, val_alta = cela[idx]
            id_baixa, val_baixa = celb[idx]

            self.listacl1.item(
                item_id,
                values=(
                    f"{id_alta}: {val_alta:.2f}",
                    f"{id_baixa}: {val_baixa:.2f}"
                )
            )
    def update_tree2(self, t_pack, t_pack_h):
        # t_pack e t_pack_h são listas de (id, valor)
        # preenche para 10 elementos
        t_pack   += [("N/A", 0.0)] * (10 - len(t_pack))
        t_pack_h += [("N/A", 0.0)] * (10 - len(t_pack_h))

        for idx, item_id in enumerate(self.tree_items2):
            id_p,  val_p  = t_pack_h[idx]
            id_ph, val_ph = t_pack[idx]

            self.listacl2.item(
                item_id,
                values=(
                    f"{id_p}: {val_p:.2f}",
                    f"{id_ph}: {val_ph:.2f}"
                )
            )

    def update_tree3(self, t_motores, t_inversores):
        # t_motores e t_inversores são listas de (id, valor)
        # preenche para 10 elementos
        t_motores   += [("N/A", 0.0)] * (10 - len(t_motores))
        t_inversores+= [("N/A", 0.0)] * (10 - len(t_inversores))

        for idx, item_id in enumerate(self.tree_items3):
            id_m,  val_m  = t_motores[idx]
            id_i,  val_i  = t_inversores[idx]

            self.listacl3.item(
                item_id,
                values=(
                    f"{id_m}: {val_m:.2f}",
                    f"{id_i}: {val_i:.2f}"
                )
            )

def main(args=None):
    rclpy.init(args=args)

    # 1) Cria a UI (já monta Tk e nó ROS)
    app = Application()

    # 2) Inicia o loop do Tkinter (que já faz spin_once)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        app.node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
