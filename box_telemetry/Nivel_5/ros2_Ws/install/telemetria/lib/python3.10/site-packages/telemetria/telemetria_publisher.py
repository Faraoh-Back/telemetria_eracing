#!/usr/bin/env python3
"""
Publisher ROS2 para Telemetria CAN
Publica dados no formato JSON compatível com receba.py
Monitora arquivo CSV em tempo real com watchdog
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import csv
from collections import defaultdict
import time
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ament_index_python.packages import get_package_share_directory


class CSVFileHandler(FileSystemEventHandler):
    """Handler para monitorar mudanças no arquivo CSV"""
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def on_modified(self, event):
        """Chamado quando o arquivo é modificado"""
        if not event.is_directory and event.src_path.endswith('.csv'):
            self.callback()


class TelemetriaPublisher(Node):
    """Nó que publica dados de telemetria no formato JSON"""
    
    def __init__(self):
        super().__init__('telemetria_publisher')
        
        # Publisher no tópico 'telemetria'
        self.publisher_ = self.create_publisher(String, 'telemetria', 10)
        
        # Timer para publicar a cada 100ms (10Hz)
        self.timer = self.create_timer(0.1, self.timer_callback)
        
        # Caminho do arquivo CSV
        # Busca o caminho do pacote instalado
        try:
            package_share_dir = get_package_share_directory('telemetria')
            self.csv_file = os.path.join(package_share_dir, 'data', 'test_can_data.csv')
        except Exception:
            # Fallback para desenvolvimento (quando rodando direto do source)
            self.csv_file = os.path.join(os.path.dirname(__file__), 'data', 'test_can_data.csv')
        
        self.csv_path = Path(self.csv_file).resolve()
        self.csv_dir = self.csv_path.parent
        
        # Carrega dados iniciais
        self.dados = self.carregar_dados()
        
        # Configura watchdog para monitorar mudanças
        self.setup_watchdog()
        
        self.get_logger().info('=== Telemetria Publisher Iniciado ===')
        self.get_logger().info(f'Publicando no tópico: telemetria')
        self.get_logger().info(f'Frequência: 10 Hz')
        self.get_logger().info(f'Fonte de dados: {self.csv_file}')
        self.get_logger().info(f'Monitoramento em tempo real: ATIVO')
    
    def setup_watchdog(self):
        """Configura watchdog para monitorar o arquivo CSV"""
        try:
            self.event_handler = CSVFileHandler(self.on_csv_modified)
            self.observer = Observer()
            self.observer.schedule(self.event_handler, str(self.csv_dir), recursive=False)
            self.observer.start()
            self.get_logger().info(f'✓ Watchdog ativo monitorando: {self.csv_dir}')
        except Exception as e:
            self.get_logger().error(f'Erro ao iniciar watchdog: {e}')
            self.observer = None
    
    def on_csv_modified(self):
        """Callback quando o CSV é modificado"""
        self.get_logger().info('🔄 Arquivo CSV modificado - Recarregando dados...')
        # Pequeno delay para garantir que a escrita foi completada
        time.sleep(0.1)
        self.dados = self.carregar_dados()
        self.get_logger().info('✓ Dados atualizados com sucesso')
    
    def carregar_dados(self):
        """Carrega e processa dados do CSV, filtrando pelo maior timestamp"""
        self.get_logger().info('Carregando dados do CSV...')
        
        try:
            # Primeiro, encontra o maior timestamp
            max_timestamp = 0.0
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    timestamp = float(row['Timestamp'])
                    if timestamp > max_timestamp:
                        max_timestamp = timestamp
            
            self.get_logger().info(f'Timestamp máximo encontrado: {max_timestamp:.6f}s')
            self.get_logger().info('Filtrando apenas dados mais recentes...')
            
            # Estruturas temporárias
            bms_voltages_raw = defaultdict(lambda: defaultdict(dict))
            bms_temperatures_raw = defaultdict(lambda: defaultdict(dict))
            lv_bms_voltages_raw = defaultdict(lambda: defaultdict(dict))
            lv_bms_temperatures_raw = defaultdict(lambda: defaultdict(dict))
            vcu_motors_raw = defaultdict(lambda: defaultdict(dict))
            
            # Agora lê apenas as linhas com o maior timestamp
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                linhas_processadas = 0
                
                for row in reader:
                    timestamp = float(row['Timestamp'])
                    
                    # Filtra apenas o timestamp mais recente
                    if timestamp != max_timestamp:
                        continue
                    
                    linhas_processadas += 1
                    sistema = row['Sistema']
                    can_id = row['ID']
                    byte_num = int(row['Byte'])
                    valor = float(row['Valor'])
                    
                    if sistema == 'BMS_Voltage':
                        bms_voltages_raw[can_id][byte_num] = valor
                    elif sistema == 'BMS_Temperature':
                        bms_temperatures_raw[can_id][byte_num] = valor
                    elif sistema == 'LV_BMS_Voltage':
                        lv_bms_voltages_raw[can_id][byte_num] = valor
                    elif sistema == 'LV_BMS_Temperature':
                        lv_bms_temperatures_raw[can_id][byte_num] = valor
                    elif sistema == 'VCU_Motor':
                        vcu_motors_raw[can_id][byte_num] = valor
            
            self.get_logger().info(f'✓ {linhas_processadas} linhas com dados mais recentes processadas')
            
            # Processa dados
            dados_processados = {
                'bms_voltages': self.concatenar_valores(bms_voltages_raw),
                'bms_temperatures': self.concatenar_valores(bms_temperatures_raw),
                'lv_bms_voltages': self.concatenar_valores(lv_bms_voltages_raw),
                'lv_bms_temperatures': self.concatenar_valores(lv_bms_temperatures_raw),
                'vcu_motors': self.concatenar_valores(vcu_motors_raw)
            }
            
            self.get_logger().info('✓ Dados carregados com sucesso')
            self.get_logger().info(f'  - BMS Voltages: {len(dados_processados["bms_voltages"]["values"])} valores')
            self.get_logger().info(f'  - LV BMS Voltages: {len(dados_processados["lv_bms_voltages"]["values"])} valores')
            self.get_logger().info(f'  - BMS Temperatures: {len(dados_processados["bms_temperatures"]["values"])} valores')
            self.get_logger().info(f'  - VCU Motors: {len(dados_processados["vcu_motors"]["values"])} valores')
            
            return dados_processados
            
        except Exception as e:
            self.get_logger().error(f'Erro ao carregar dados: {e}')
            return None
    
    def concatenar_valores(self, dados_raw):
        """Concatena valores ordenados por ID e byte"""
        if not dados_raw:
            return {'values': [], 'ids': [], 'byte_count_per_id': []}
        
        # Ordena IDs
        ids_ordenados = sorted(dados_raw.keys(), key=lambda x: int(x, 16))
        
        values = []
        ids = []
        byte_count_per_id = []
        
        for can_id in ids_ordenados:
            bytes_ordenados = sorted(dados_raw[can_id].keys())
            
            for byte_num in bytes_ordenados:
                values.append(dados_raw[can_id][byte_num])
            
            ids.append(can_id)
            byte_count_per_id.append(len(bytes_ordenados))
        
        return {
            'values': values,
            'ids': ids,
            'byte_count_per_id': byte_count_per_id
        }
    
    def criar_json_telemetria(self):
        """Cria JSON no formato esperado pelo receba.py"""
        if self.dados is None:
            return None
        
        # Calcula tensão do pack alta (soma das células)
        tensao_pack_alta = sum(self.dados['bms_voltages']['values'])
        
        # Cria dicionário com os valores indexados
        # O receba.py espera dict ou list, vamos usar dict com índices como chaves
        tensoes_celulas_alta_dict = {
            str(i): valor 
            for i, valor in enumerate(self.dados['bms_voltages']['values'])
        }
        
        tensoes_celulas_baixa_dict = {
            str(i): valor 
            for i, valor in enumerate(self.dados['lv_bms_voltages']['values'])
        }
        
        temps_pack_alta_dict = {
            str(i): valor 
            for i, valor in enumerate(self.dados['bms_temperatures']['values'])
        }
        
        temps_pack_dict = {
            str(i): valor 
            for i, valor in enumerate(self.dados['lv_bms_temperatures']['values'])
        }
        
        temps_motores_dict = {
            str(i): valor 
            for i, valor in enumerate(self.dados['vcu_motors']['values'])
        }
        
        # Temperaturas inversores (placeholder - não temos esses dados)
        temps_inversores_dict = {
            str(i): 0.0 
            for i in range(4)  # Assumindo 4 inversores
        }
        
        # Monta JSON no formato esperado
        json_data = {
            "Velocidade": {
                "value": 0.0  # Placeholder - não temos esse dado
            },
            "Tensao_pack_alta": {
                "value": tensao_pack_alta
            },
            "Tensao_pack_baixa": {
                "value": 0.0  # Placeholder - não temos esse dado
            },
            "Tensoes_celulas_alta": {
                "values": tensoes_celulas_alta_dict
            },
            "Tensoes_celulas_baixa": {
                "values": tensoes_celulas_baixa_dict
            },
            "Temps_pack": {
                "values": temps_pack_dict
            },
            "Temps_pack_alta": {
                "values": temps_pack_alta_dict
            },
            "Temps_motores": {
                "values": temps_motores_dict
            },
            "Temps_inversores": {
                "values": temps_inversores_dict
            }
        }
        
        return json_data
    
    def timer_callback(self):
        """Callback do timer - publica mensagem"""
        json_data = self.criar_json_telemetria()
        
        if json_data is None:
            self.get_logger().warn('Dados não disponíveis')
            return
        
        # Cria mensagem String com JSON
        msg = String()
        msg.data = json.dumps(json_data)
        
        # Publica
        self.publisher_.publish(msg)
        
        # Log ocasional (a cada 50 mensagens = 5 segundos)
        if not hasattr(self, 'msg_count'):
            self.msg_count = 0
        
        self.msg_count += 1
        if self.msg_count % 50 == 0:
            self.get_logger().info(f'Publicadas {self.msg_count} mensagens')
            self.get_logger().info(f'  Tensão pack alta: {json_data["Tensao_pack_alta"]["value"]:.2f} V')


def main(args=None):
    rclpy.init(args=args)
    
    node = TelemetriaPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Para o observer do watchdog
        if hasattr(node, 'observer') and node.observer is not None:
            node.observer.stop()
            node.observer.join()
        
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()