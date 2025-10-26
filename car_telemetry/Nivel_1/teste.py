#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ECI Demo para USB-to-CAN Compact V1 (baseado em EciDemo109.py)
Exemplo simplificado de uso do IXXAT USB-to-CAN Compact
Compatível com Python 2 e Python 3
"""

from ECI109 import *
from EciDemoCommon import *
import time
import struct
import sys

# Constantes
ECIDEMO_TX_TIMEOUT = DWORD(500)
ECIDEMO_RX_TIMEOUT = DWORD(500)
ECIDEMO_RX_TOTALTIMEOUT = 30.0
ECIDEMO_HWUSEPOLLINGMODE = False

class EciDemo109:
    """
    Demo oficial para USB-to-CAN compact
    """
    
    def __init__(self):
        self.eci = ECI109()
    
    def _chkStatus(self, hResult, sFuncName):
        """Verifica status e imprime resultado"""
        if ECI_OK == hResult:
            print("%s ...succeeded." % sFuncName)
        else:
            print("%s ...failed with error code: 0x%08X. %s" %
                  (sFuncName, hResult, self.eci.ECIDRV_GetErrorString(hResult)))
    
    def RunDemo(self):
        """Executa o demo completo"""
        hResult = ECI_OK
        stcHwPara = ECI_HW_PARA()
        stcHwInfo = ECI_HW_INFO()
        dwHwIndex = DWORD(0)
        dwCtrlIndex = DWORD(0)
        
        print("\n>> ECI Demo for USB-to-CAN compact <<\n")
        
        # Preparar estrutura de hardware
        stcHwPara.wHardwareClass = ECI_HW_USB
        if ECIDEMO_HWUSEPOLLINGMODE:
            stcHwPara.dwFlags = ECI_SETTINGS_FLAG_POLLING_MODE
        
        # Inicializar ECI driver com 1 dispositivo
        hResult = self.eci.ECIDRV_Initialize(1, stcHwPara)
        self._chkStatus(hResult, "ECIDRV_Initialize")
        
        # Obter informações do hardware
        if ECI_OK == hResult:
            hResult = self.eci.ECIDRV_GetInfo(dwHwIndex, stcHwInfo)
            self._chkStatus(hResult, "ECIDRV_GetInfo")
            if ECI_OK == hResult:
                EciPrintHwInfo(stcHwInfo)
        
        # Encontrar primeiro controlador CAN
        if ECI_OK == hResult:
            dwCtrlIndex = EciGetNthCtrlOfClass(stcHwInfo, ECI_CTRL_CAN, 0, dwCtrlIndex)
            if ECI_OK == hResult:
                # Iniciar demo CAN
                hResult = self.EciCanDemo(dwHwIndex, dwCtrlIndex)
                self._chkStatus(hResult, "EciCanDemo")
            else:
                hResult = ECI_OK
        
        # Liberar driver
        self.eci.ECIDRV_Release()
        
        print("-> Returning from ECI Demo for USB-to-CAN compact <-\n")
        
        return hResult
    
    def EciCanDemo(self, dwHwIndex, dwCtrlIndex):
        """Demo CAN completo"""
        hResult = ECI_OK
        dwCtrlHandle = ECI_INVALID_HANDLE
        
        print("\n>> ECI CAN Demo <<\n")
        
        # Abrir controlador
        if ECI_OK == hResult:
            stcCtrlConfig = ECI_CTRL_CONFIG()
            
            # Configurar CAN 1000 kbps
            stcCtrlConfig.wCtrlClass = WORD(ECI_CTRL_CAN)
            stcCtrlConfig.u.sCanConfig.dwVer = DWORD(ECI_STRUCT_VERSION_V0)
            stcCtrlConfig.u.sCanConfig.u.V0.bBtReg0 = BYTE(ECI_CAN_BT0_1000KB)
            stcCtrlConfig.u.sCanConfig.u.V0.bBtReg1 = BYTE(ECI_CAN_BT1_1000KB)
            stcCtrlConfig.u.sCanConfig.u.V0.bOpMode = BYTE(ECI_CAN_OPMODE_STANDARD | 
                                                           ECI_CAN_OPMODE_EXTENDED | 
                                                           ECI_CAN_OPMODE_ERRFRAME)
            
            hResult = self.eci.ECIDRV_CtrlOpen(dwCtrlHandle, dwHwIndex, dwCtrlIndex, stcCtrlConfig)
            self._chkStatus(hResult, "ECIDRV_CtrlOpen")
        
        # Obter capabilities
        if ECI_OK == hResult:
            stcCtrlCaps = ECI_CTRL_CAPABILITIES()
            hResult = self.eci.ECIDRV_CtrlGetCapabilities(dwCtrlHandle, stcCtrlCaps)
            self._chkStatus(hResult, "ECIDRV_CtrlGetCapabilities")
            if ECI_OK == hResult:
                EciPrintCtrlCapabilities(stcCtrlCaps)
        
        # Iniciar controlador
        if ECI_OK == hResult:
            hResult = self.eci.ECIDRV_CtrlStart(dwCtrlHandle)
            self._chkStatus(hResult, "ECIDRV_CtrlStart")
        
        # Enviar mensagens CAN
        if ECI_OK == hResult:
            stcCtrlMsg = ECI_CTRL_MESSAGE()
            dwTxMsgCount = 10  # Enviar apenas 10 mensagens para teste
            
            print("Now, sending %u CAN Messages" % dwTxMsgCount)
            
            for dwIndex in range(0, dwTxMsgCount):
                # Preparar mensagem CAN
                stcCtrlMsg.wCtrlClass = ECI_CTRL_CAN
                stcCtrlMsg.u.sCanMessage.dwVer = ECI_STRUCT_VERSION_V0
                stcCtrlMsg.u.sCanMessage.u.V0.dwMsgId = (dwIndex % (ECI_CAN_MAX_11BIT_ID + 1))
                stcCtrlMsg.u.sCanMessage.u.V0.uMsgInfo.Bits.dlc = 8
                
                # Preencher dados
                a = struct.pack("<I", dwIndex)
                for i in range(0, 4):
                    if sys.version_info[0] >= 3:
                        stcCtrlMsg.u.sCanMessage.u.V0.abData[i] = a[i]
                        stcCtrlMsg.u.sCanMessage.u.V0.abData[i+4] = a[i]
                    else:
                        stcCtrlMsg.u.sCanMessage.u.V0.abData[i] = ord(a[i])
                        stcCtrlMsg.u.sCanMessage.u.V0.abData[i+4] = ord(a[i])
                
                # Enviar mensagem
                if ECIDEMO_HWUSEPOLLINGMODE:
                    dwStartTime = time.time()
                    while True:
                        hResult = self.eci.ECIDRV_CtrlSend(dwCtrlHandle, stcCtrlMsg, 0)
                        if ECI_OK != hResult:
                            time.sleep(0.001)
                        if (ECI_OK == hResult) or ((time.time() - dwStartTime) > ECIDEMO_TX_TIMEOUT.value/1000.0):
                            break
                else:
                    hResult = self.eci.ECIDRV_CtrlSend(dwCtrlHandle, stcCtrlMsg, ECIDEMO_TX_TIMEOUT)
                
                if ECI_OK != hResult:
                    print("Error while sending CAN Messages")
                    self._chkStatus(hResult, "ECIDRV_CtrlSend")
                    hResult = ECI_OK
                    break
                else:
                    # Ler mensagens recebidas
                    astcPyCtrlMsg = ECI_CTRL_MESSAGE * 20
                    astcCtrlMsg = astcPyCtrlMsg()
                    dwCount = DWORD(len(astcCtrlMsg))
                    
                    hResult = self.eci.ECIDRV_CtrlReceive(dwCtrlHandle, dwCount, astcCtrlMsg, 0)
                    
                    dwMsgIndex = 0
                    while (ECI_OK == hResult) and (dwCount.value > dwMsgIndex):
                        EciPrintCtrlMessage(astcCtrlMsg[dwMsgIndex])
                        dwMsgIndex += 1
                    
                    hResult = ECI_OK
        
        # Receber mensagens CAN
        if ECI_OK == hResult:
            stcCtrlMsg = ECI_CTRL_MESSAGE()
            dwRxTimeout = 5.0  # 5 segundos apenas
            
            print("Now, receiving CAN Messages for %u seconds" % int(dwRxTimeout))
            
            dwStartTime = time.time()
            dwCurrentTime = dwStartTime
            hResult = ECI_ERR_TIMEOUT
            
            while (dwRxTimeout >= (dwCurrentTime - dwStartTime)):
                if ECIDEMO_HWUSEPOLLINGMODE:
                    dwStartTime2 = time.time()
                    while True:
                        dwCount = DWORD(1)
                        hResult = self.eci.ECIDRV_CtrlReceive(dwCtrlHandle, dwCount, stcCtrlMsg, 0)
                        if (ECI_OK != hResult) or (0 == dwCount.value):
                            time.sleep(0.001)
                        if (ECI_OK == hResult) or ((time.time() - dwStartTime2) > ECIDEMO_RX_TIMEOUT.value/1000.0):
                            break
                else:
                    dwCount = DWORD(1)
                    hResult = self.eci.ECIDRV_CtrlReceive(dwCtrlHandle, dwCount, stcCtrlMsg, ECIDEMO_RX_TIMEOUT)
                
                if ECI_OK == hResult and dwCount.value > 0:
                    print("")
                    EciPrintCtrlMessage(stcCtrlMsg, sameLine=True)
                else:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                
                dwCurrentTime = time.time()
            
            print("")
            hResult = ECI_OK
        
        # Parar controlador
        if ECI_OK == hResult:
            print("")
            hResult = self.eci.ECIDRV_CtrlStop(dwCtrlHandle, ECI_STOP_FLAG_NONE)
            self._chkStatus(hResult, "ECIDRV_CtrlStop")
        
        time.sleep(0.250)
        
        # Reset controlador
        if ECI_OK == hResult:
            hResult = self.eci.ECIDRV_CtrlStop(dwCtrlHandle, ECI_STOP_FLAG_RESET_CTRL)
            self._chkStatus(hResult, "ECIDRV_CtrlStop")
        
        # Fechar controlador
        self.eci.ECIDRV_CtrlClose(dwCtrlHandle)
        dwCtrlHandle = ECI_INVALID_HANDLE
        
        return hResult


class IxxatCANSimple:
    """
    Classe simplificada para uso rápido (API fácil)
    """
    
    def __init__(self):
        self.eci = ECI109()
        self.hCtrl = ECI_INVALID_HANDLE
        self.running = False
    
    def connect(self, baudrate=500000):
        """
        Conecta ao dispositivo
        
        baudrate: 125000, 250000, 500000, 1000000
        """
        print("Conectando ao IXXAT USB-to-CAN...")
        
        # Preparar hardware
        hwpara = ECI_HW_PARA()
        hwpara.wHardwareClass = ECI_HW_USB
        
        # Inicializar com 1 dispositivo
        result = self.eci.ECIDRV_Initialize(1, hwpara)
        if result != ECI_OK:
            errstr = self.eci.ECIDRV_GetErrorString(result)
            print("X Erro ao inicializar: %s" % errstr)
            print("  Codigo: 0x%08X" % result)
            print("\n  Execute como root: sudo python teste.py")
            return False
        
        print("+ Driver inicializado")
        
        # Configurar controlador
        config = ECI_CTRL_CONFIG()
        config.wCtrlClass = WORD(ECI_CTRL_CAN)
        config.u.sCanConfig.dwVer = DWORD(ECI_STRUCT_VERSION_V0)
        config.u.sCanConfig.u.V0.bOpMode = BYTE(ECI_CAN_OPMODE_STANDARD | 
                                                ECI_CAN_OPMODE_EXTENDED | 
                                                ECI_CAN_OPMODE_ERRFRAME)
        
        # Configurar baudrate
        if baudrate == 1000000:
            bt0, bt1 = ECI_CAN_BT0_1000KB, ECI_CAN_BT1_1000KB
        elif baudrate == 500000:
            bt0, bt1 = ECI_CAN_BT0_500KB, ECI_CAN_BT1_500KB
        elif baudrate == 250000:
            bt0, bt1 = ECI_CAN_BT0_250KB, ECI_CAN_BT1_250KB
        elif baudrate == 125000:
            bt0, bt1 = ECI_CAN_BT0_125KB, ECI_CAN_BT1_125KB
        else:
            bt0, bt1 = ECI_CAN_BT0_500KB, ECI_CAN_BT1_500KB
        
        config.u.sCanConfig.u.V0.bBtReg0 = BYTE(bt0)
        config.u.sCanConfig.u.V0.bBtReg1 = BYTE(bt1)
        
        # Abrir controlador
        result = self.eci.ECIDRV_CtrlOpen(self.hCtrl, DWORD(0), DWORD(0), config)
        if result != ECI_OK:
            errstr = self.eci.ECIDRV_GetErrorString(result)
            print("X Erro ao abrir: %s" % errstr)
            self.eci.ECIDRV_Release()
            return False
        
        print("+ Controlador aberto (handle: %s)" % self.hCtrl.value)
        
        # Iniciar
        result = self.eci.ECIDRV_CtrlStart(self.hCtrl)
        if result != ECI_OK:
            errstr = self.eci.ECIDRV_GetErrorString(result)
            print("X Erro ao iniciar: %s" % errstr)
            self.eci.ECIDRV_CtrlClose(self.hCtrl)
            self.eci.ECIDRV_Release()
            return False
        
        self.running = True
        print("+ Conectado! Baudrate: %d bps\n" % baudrate)
        return True
    
    def send(self, can_id, data):
        """Envia mensagem CAN"""
        if not self.running:
            return False
        
        msg = ECI_CTRL_MESSAGE()
        msg.wCtrlClass = ECI_CTRL_CAN
        msg.u.sCanMessage.dwVer = ECI_STRUCT_VERSION_V0
        msg.u.sCanMessage.u.V0.dwMsgId = can_id
        msg.u.sCanMessage.u.V0.uMsgInfo.Bits.dlc = len(data)
        msg.u.sCanMessage.u.V0.uMsgInfo.Bits.ext = 0
        msg.u.sCanMessage.u.V0.uMsgInfo.Bits.rtr = 0
        
        for i, byte in enumerate(data):
            msg.u.sCanMessage.u.V0.abData[i] = byte
        
        result = self.eci.ECIDRV_CtrlSend(self.hCtrl, msg, DWORD(100))
        
        if result == ECI_OK:
            data_str = ' '.join(['%02X' % b for b in data])
            print("-> Enviado: ID=0x%03X Data=[%s]" % (can_id, data_str))
            return True
        else:
            errstr = self.eci.ECIDRV_GetErrorString(result)
            print("X Erro ao enviar: %s" % errstr)
            return False
    
    def receive(self, timeout=1000, max_msgs=10):
        """Recebe mensagens CAN"""
        if not self.running:
            return []
        
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
                    data_str = ' '.join(['%02X' % b for b in data])
                    print("<- Recebido: ID=0x%03X Data=[%s]" % (msg_id, data_str))
        
        return received
    
    def disconnect(self):
        """Desconecta"""
        if self.running:
            self.eci.ECIDRV_CtrlStop(self.hCtrl, ECI_STOP_FLAG_NONE)
            self.eci.ECIDRV_CtrlClose(self.hCtrl)
            self.eci.ECIDRV_Release()
            self.running = False
            print("\n+ Desconectado")


# Programa principal
if __name__ == '__main__':
    print("="*60)
    print("IXXAT USB-to-CAN Compact - Python Demo")
    print("="*60)
    print("1. Demo completo (oficial IXXAT)")
    print("2. Uso simples (enviar/receber)")
    print("="*60)
    
    escolha = raw_input("\nEscolha (1 ou 2): ").strip() if sys.version_info[0] < 3 else input("\nEscolha (1 ou 2): ").strip()
    
    if escolha == "1":
        # Demo oficial completo
        demo = EciDemo109()
        result = demo.RunDemo()
        sys.exit(0 if result == ECI_OK else 1)
    
    elif escolha == "2":
        # Interface simples
        can = IxxatCANSimple()
        
        try:
            if not can.connect(baudrate=500000):
                print("\nX Falha ao conectar!")
                sys.exit(1)
            
            print("Comandos:")
            print("  s <ID> <dados>  - Enviar (ex: s 123 11 22 33)")
            print("  r               - Receber")
            print("  q               - Sair\n")
            
            while True:
                if sys.version_info[0] < 3:
                    cmd = raw_input("> ").strip().split()
                else:
                    cmd = input("> ").strip().split()
                
                if not cmd:
                    continue
                
                if cmd[0] == 'q':
                    break
                
                elif cmd[0] == 's' and len(cmd) >= 3:
                    can_id = int(cmd[1], 16)
                    data = [int(x, 16) for x in cmd[2:]]
                    can.send(can_id, data)
                
                elif cmd[0] == 'r':
                    msgs = can.receive(timeout=1000)
                    if not msgs:
                        print("  (nenhuma mensagem)")
                
                else:
                    print("X Comando invalido")
        
        except KeyboardInterrupt:
            print("\n\nInterrompido!")
        
        finally:
            can.disconnect()
    
    else:
        print("X Opcao invalida!")
