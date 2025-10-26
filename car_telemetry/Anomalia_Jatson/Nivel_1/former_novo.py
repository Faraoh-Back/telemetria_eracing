#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Nivel 1: Coletor CAN (former_novo.py)
- Executar com PYTHON 2
- Le dados do IXXAT
- Salva dados em PEQUENOS LOTES (ex: 100 msgs ou 5 seg)
- Salva em JSON LINES (.jsonl)
"""

import os
import sys
import time
import json
import threading
from datetime import datetime

# ========================================
# IMPORTAR BIBLIOTECAS IXXAT (CRÍTICO!)
# ========================================
try:
    from ECI109 import *
    from ECI_hwtype import *
    from ECI_error import *
except ImportError:
    print "ERRO FATAL: Nao foi possivel encontrar os drivers IXXAT (ECI109.py, etc.)"
    print "Certifique-se que eles estao na pasta 'src/'"
    sys.exit(1)

# ========================================
# CONFIGURACOES
# ========================================
PASTA_DADOS_BRUTOS = "dados_brutos/"
CAN_BAUDRATE = 500000
CAN_RECEIVE_TIMEOUT_MS = 100 # Timeout curto para polling

# NOVO: Configuracoes de Lote
MENSAGENS_POR_LOTE = 20
MAX_SEGUNDOS_POR_LOTE = 0.5

# ========================================
# CLASSE IXXAT (Sem alteracoes)
# ========================================
class IxxatCANSimple:
    def __init__(self):
        self.eci = ECI109()
        self.hCtrl = ECI_INVALID_HANDLE
        self.running = False
    
    def connect(self, baudrate=500000):
        print "Nivel 1: Conectando ao IXXAT USB-to-CAN..."
        hwpara = ECI_HW_PARA()
        hwpara.wHardwareClass = ECI_HW_USB
        
        result = self.eci.ECIDRV_Initialize(1, hwpara)
        if result != ECI_OK:
            errstr = self.eci.ECIDRV_GetErrorString(result)
            print "Nivel 1: X Erro ao inicializar: %s" % errstr
            print "  Codigo: 0x%08X" % result
            print "\n  Execute como root: sudo python Nivel_1/former_novo.py"
            return False
        
        print "Nivel 1: + Driver inicializado"
        
        config = ECI_CTRL_CONFIG()
        config.wCtrlClass = WORD(ECI_CTRL_CAN)
        config.u.sCanConfig.dwVer = DWORD(ECI_STRUCT_VERSION_V0)
        config.u.sCanConfig.u.V0.bOpMode = BYTE(ECI_CAN_OPMODE_STANDARD | ECI_CAN_OPMODE_EXTENDED | ECI_CAN_OPMODE_ERRFRAME)
        
        if baudrate == 1000000: bt0, bt1 = ECI_CAN_BT0_1000KB, ECI_CAN_BT1_1000KB
        elif baudrate == 500000: bt0, bt1 = ECI_CAN_BT0_500KB, ECI_CAN_BT1_500KB
        elif baudrate == 250000: bt0, bt1 = ECI_CAN_BT0_250KB, ECI_CAN_BT1_250KB
        elif baudrate == 125000: bt0, bt1 = ECI_CAN_BT0_125KB, ECI_CAN_BT1_125KB
        else: bt0, bt1 = ECI_CAN_BT0_500KB, ECI_CAN_BT1_500KB
        
        config.u.sCanConfig.u.V0.bBtReg0 = BYTE(bt0)
        config.u.sCanConfig.u.V0.bBtReg1 = BYTE(bt1)
        
        result = self.eci.ECIDRV_CtrlOpen(self.hCtrl, DWORD(0), DWORD(0), config)
        if result != ECI_OK:
            errstr = self.eci.ECIDRV_GetErrorString(result)
            if hasattr(errstr, 'decode'): errstr = errstr.decode('utf-8', 'ignore')
            print "Nivel 1: X Erro ao abrir: %s" % errstr
            self.eci.ECIDRV_Release()
            return False
        
        print "Nivel 1: + Controlador aberto (handle: %s)" % self.hCtrl.value
        
        result = self.eci.ECIDRV_CtrlStart(self.hCtrl)
        if result != ECI_OK:
            errstr = self.eci.ECIDRV_GetErrorString(result)
            if hasattr(errstr, 'decode'): errstr = errstr.decode('utf-8', 'ignore')
            print "Nivel 1: X Erro ao iniciar: %s" % errstr
            self.eci.ECIDRV_CtrlClose(self.hCtrl)
            self.eci.ECIDRV_Release()
            return False
        
        self.running = True
        print "Nivel 1: + Conectado! Baudrate: %d bps\n" % baudrate
        return True
    
    def receive(self, timeout=100, max_msgs=10):
        if not self.running: return []
        count = DWORD(max_msgs)
        msgs_array = (ECI_CTRL_MESSAGE * max_msgs)()
        result = self.eci.ECIDRV_CtrlReceive(self.hCtrl, count, msgs_array, DWORD(timeout))
        
        received = []
        if result == ECI_OK and count.value > 0:
            for i in range(count.value):
                if msgs_array[i].wCtrlClass == ECI_CTRL_CAN:
                    can_msg = msgs_array[i].u.sCanMessage
                    msg_id = can_msg.u.V0.dwMsgId
                    dlc = can_msg.u.V0.uMsgInfo.Bits.dlc
                    data = [can_msg.u.V0.abData[j] for j in range(dlc)]
                    received.append({'id': msg_id, 'data': data})
        return received
    
    def disconnect(self):
        if self.running:
            try:
                self.eci.ECIDRV_CtrlStop(self.hCtrl, ECI_STOP_FLAG_NONE)
                self.eci.ECIDRV_CtrlClose(self.hCtrl)
                self.eci.ECIDRV_Release()
                self.running = False
                print "\nNivel 1: + IXXAT desconectado"
            except Exception as e:
                print "Nivel 1: Erro ao desconectar IXXAT: %s" % e

# ========================================
# BLOCO PRINCIPAL (Coletor CAN)
# ========================================
def main():
    global bus_can
    bus_can = None
    
    print "="*60
    print "Nivel 1: Coletor CAN -> JSONL (former_novo.py)"
    print "EXECUTANDO COM PYTHON 2"
    print "Modo: Lotes (batch)"
    print "="*60
    
    try:
        # 1. Criar pasta de dados brutos se nao existir
        if not os.path.exists(PASTA_DADOS_BRUTOS):
            print "Nivel 1: Criando pasta %s" % PASTA_DADOS_BRUTOS
            os.makedirs(PASTA_DADOS_BRUTOS)
            
        # 2. Conectar ao IXXAT
        bus_can = IxxatCANSimple()
        if not bus_can.connect(baudrate=CAN_BAUDRATE):
            print "Nivel 1: ERRO FATAL: Falha ao conectar ao IXXAT."
            return

        # 3. Loop principal de Lotes
        print "Nivel 1: Iniciando coleta... (Pressione Ctrl+C para parar)"
        contador_msgs_total = 0
        
        # MUDANCA: Loop principal agora controla os lotes
        while True:
            
            # 1. Abrir um novo arquivo para este lote
            # Adiciona microsegundos para garantir nome unico
            nome_arquivo = "log_can_%s.jsonl" % datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            caminho_arquivo = os.path.join(PASTA_DADOS_BRUTOS, nome_arquivo)
            
            json_file_handle = None
            contador_msgs_lote = 0
            
            try:
                json_file_handle = open(caminho_arquivo, 'w')
                tempo_inicio_lote = time.time()
                
                # 2. Loop interno: Coleta 1 lote (100 msgs ou 5 seg)
                while (contador_msgs_lote < MENSAGENS_POR_LOTE and 
                       (time.time() - tempo_inicio_lote) < MAX_SEGUNDOS_POR_LOTE):
                    
                    mensagens_recebidas = bus_can.receive(timeout=CAN_RECEIVE_TIMEOUT_MS)
                    
                    if not mensagens_recebidas:
                        continue # Poll novamente
                    
                    timestamp_atual = time.time()
                    
                    for msg in mensagens_recebidas:
                        pacote = {
                            "id_can": "0x%03X" % msg['id'],
                            "dados": msg['data'],
                            "timestamp": timestamp_atual
                        }
                        
                        try:
                            json_string = json.dumps(pacote)
                            json_file_handle.write(json_string + '\n')
                        except Exception as e:
                            print "Nivel 1: ERRO ao serializar JSON: %s" % e
                        
                        contador_msgs_lote += 1
                        contador_msgs_total += 1
                        
                        # Atualiza o status
                        sys.stdout.write("Nivel 1: %d mensagens salvas (lote: %d/%d)...\r" % 
                                         (contador_msgs_total, contador_msgs_lote, MENSAGENS_POR_LOTE))
                        sys.stdout.flush()
                        
                        # Se o lote encheu, sai do loop interno
                        if contador_msgs_lote >= MENSAGENS_POR_LOTE:
                            break
            
            finally:
                # 3. Fechar o arquivo (MUITO IMPORTANTE)
                # Isso "libera" o arquivo para o Nivel 2 processar
                if json_file_handle:
                    json_file_handle.close()
                
                # 4. Se o lote estava vazio, apaga o arquivo
                if contador_msgs_lote == 0:
                    try:
                        os.remove(caminho_arquivo)
                    except OSError:
                        pass # ignora se o arquivo nao existir
                else:
                    # Opcional: Log de lote salvo
                    # print "Nivel 1: Lote %s salvo com %d mensagens." % (nome_arquivo, contador_msgs_lote)
                    pass
                    
    except KeyboardInterrupt:
        print "\nNivel 1: Ctrl+C recebido. Finalizando..."
        
    except Exception as e:
        print "\nNivel 1: ERRO INESPERADO: %s" % e
        import traceback
        traceback.print_exc()
        
    finally:
        print "\nNivel 1: Encerrando..."
        if bus_can:
            bus_can.disconnect()
        
        print "Nivel 1: Finalizado. Total de %d mensagens salvas." % contador_msgs_total
        print "="*60

if __name__ == "__main__":
    main()
