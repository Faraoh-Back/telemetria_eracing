#!/usr/bin/env python3
"""
Sistema de Monitoramento Inteligente de Logs - Versão Simplificada
Carrega apenas dados recentes e monitora incrementalmente
ATUALIZADO para novo formato: signal,timestamp,id_can,priority,value,unit,min,max
"""

import time
import csv
import os
from threading import Lock

def create_smart_log_monitor(data_manager, log_file_path, max_recent_lines=500):
    """
    Cria monitor inteligente de logs
    Carrega apenas histórico recente + monitoramento incremental
    """
    return SmartLogHandler(data_manager, log_file_path, max_recent_lines)

class SmartLogHandler:
    """Monitor inteligente que carrega dados de forma eficiente"""
    
    def __init__(self, data_manager, log_file_path, max_recent_lines=500):
        self.data_manager = data_manager
        self.log_file_path = log_file_path
        self.max_recent_lines = max_recent_lines
        self.file_position = 0
        self.last_file_size = 0
        self.file_lock = Lock()
        self.status_callback = None
        self.initial_load_complete = False
        
        # Verifica se arquivo existe
        if not os.path.exists(log_file_path):
            print(f"⚠️ Arquivo de log não encontrado: {log_file_path}")
            return
        
        try:
            self.last_file_size = os.path.getsize(log_file_path)
            print(f"📊 Arquivo encontrado: {os.path.basename(log_file_path)} ({self.last_file_size:,} bytes)")
        except Exception as e:
            print(f"❌ Erro ao verificar arquivo: {e}")
    
    def set_status_callback(self, callback):
        """Define callback para atualizações de status"""
        self.status_callback = callback
    
    def load_initial_data(self):
        """Carrega dados iniciais de forma inteligente"""
        try:
            if self.status_callback:
                self.status_callback("🔄 Carregando histórico recente...")
            
            with self.file_lock:
                # Estratégia adaptativa baseada no tamanho do arquivo
                file_size = os.path.getsize(self.log_file_path)
                
                print(f"📊 Tamanho do arquivo: {file_size:,} bytes")
                
                lines_to_read = []
                
                if file_size < 1024 * 100:  # 100KB - pequeno
                    print("📋 Estratégia: arquivo pequeno - lendo tudo")
                    lines_to_read = self._read_all_lines()
                    
                elif file_size < 1024 * 1024:  # 1MB - médio
                    print("📋 Estratégia: arquivo médio - lendo últimas linhas")
                    lines_to_read = self._read_last_lines()
                    
                else:  # Grande (>1MB)
                    print("📋 Estratégia: arquivo grande - otimizado")
                    lines_to_read = self._read_optimized_large_file()
                
                # Processa as linhas coletadas
                processed_count = self._process_lines(lines_to_read)
                
                # Atualiza posição do arquivo
                self.file_position = self._get_file_position()
                self.last_file_size = file_size
                self.initial_load_complete = True
                
                print(f"✅ Carregamento inteligente concluído: {processed_count} linhas processadas")
                
                if self.status_callback:
                    self.status_callback(f"✓ {processed_count} dados carregados")
                
                return True
                
        except Exception as e:
            print(f"❌ Erro no carregamento inteligente: {e}")
            if self.status_callback:
                self.status_callback(f"❌ Erro: {e}")
            return False
    
    def _read_all_lines(self):
        """Lê todas as linhas (para arquivos pequenos)"""
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    
    def _read_last_lines(self):
        """Lê últimas linhas (para arquivos médios)"""
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            if len(all_lines) > self.max_recent_lines:
                return all_lines[-self.max_recent_lines:]
            return all_lines
    
    def _read_optimized_large_file(self):
        """Lê de forma otimizada arquivos grandes (>1MB)"""
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            # Vai para 1MB antes do final
            file_size = os.path.getsize(self.log_file_path)
            start_pos = max(0, file_size - 1024 * 1024)  # Último 1MB
            
            f.seek(start_pos)
            
            # Pula primeira linha incompleta
            first_line = f.readline()
            
            # Lê linhas restantes
            lines = []
            for line in f:
                lines.append(line)
            
            # Se ainda muitas linhas, pega apenas as últimas
            if len(lines) > self.max_recent_lines:
                lines = lines[-self.max_recent_lines:]
            
            return lines
    
    def _process_lines(self, lines):
        """
        Processa lista de linhas e adiciona ao data manager
        NOVO FORMATO: signal,timestamp,id_can,priority,value,unit,min,max
        """
        processed_count = 0
        
        for linha in lines:
            linha = linha.strip()
            if not linha:
                continue
            
            try:
                # Parse do CSV
                partes = linha.split(',')
                
                # Formato novo: signal,timestamp,id_can,priority,value,unit,min,max
                if len(partes) >= 6:  # Mínimo 6 colunas
                    signal_name = partes[0].strip()
                    timestamp_str = partes[1].strip()
                    id_can = partes[2].strip()
                    priority_str = partes[3].strip()
                    value = partes[4].strip()
                    unit = partes[5].strip() if len(partes) > 5 else ''
                    
                    # Min e max são opcionais
                    min_val = partes[6].strip() if len(partes) > 6 else None
                    max_val = partes[7].strip() if len(partes) > 7 else None
                    
                    if signal_name:  # Apenas se nome não estiver vazio
                        # Converte timestamp
                        try:
                            timestamp = float(timestamp_str)
                        except:
                            timestamp = time.time()
                        
                        # Converte prioridade
                        try:
                            priority = int(priority_str)
                        except:
                            priority = 5
                        
                        # Adiciona ao data manager (COM NOVO FORMATO)
                        self.data_manager.process_new_data(
                            signal_name, value, timestamp, id_can, priority, 
                            unit, min_val, max_val
                        )
                        
                        processed_count += 1
                        
                        # Atualiza status ocasionalmente
                        if processed_count % 100 == 0 and self.status_callback:
                            self.status_callback(f"📊 Processando... {processed_count} dados")
            
            except Exception as e:
                # Log error mas continua processando
                if processed_count < 5:  # Apenas primeiros erros
                    print(f"⚠️ Erro processando linha: {e}")
                continue
        
        return processed_count
    
    def _get_file_position(self):
        """Obtém posição atual do arquivo"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                return f.seek(0, 2)  # Vai ao final e retorna posição
        except:
            return 0
    
    def check_for_new_data(self):
        """Verifica novos dados de forma eficiente"""
        if not self.initial_load_complete:
            return False
        
        try:
            with self.file_lock:
                current_size = os.path.getsize(self.log_file_path)
                
                # Se arquivo não cresceu, não há novos dados
                if current_size <= self.last_file_size:
                    return False
                
                # Lê apenas os novos bytes
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    f.seek(self.last_file_size)
                    new_lines = []
                    
                    for line in f:
                        new_lines.append(line)
                    
                    if new_lines:
                        processed_count = self._process_lines(new_lines)
                        self.last_file_size = current_size
                        
                        if self.status_callback and processed_count > 0:
                            self.status_callback(f"📈 +{processed_count} novos dados")
                        
                        return processed_count > 0
                
                return False
                
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"⚠️ Erro monitoramento: {e}")
            return False
    
    def get_status(self):
        """Retorna status atual do monitor"""
        try:
            current_size = os.path.getsize(self.log_file_path)
            return {
                'file_size': current_size,
                'last_size': self.last_file_size,
                'initial_load': self.initial_load_complete,
                'new_data_available': current_size > self.last_file_size
            }
        except:
            return {
                'file_size': 0,
                'last_size': 0,
                'initial_load': False,
                'new_data_available': False
            }