# Biblioteca para comunicação MQTT (enviar dados para o box)
import paho.mqtt.client as mqtt
# Para converter o pacote formatado em string JSON
import json
# Para gerar timestamps e usar pausas (sleep)
import time
# Para rodar a leitura CAN em uma thread separada
import threading

# Importa as funções do nosso módulo de Nível 1 (former.py)
try:
    # Adiciona o diretório pai (onde está Nivel_1) ao path, se necessário
    import sys
    import os
    script_dir = os.path.dirname(__file__)
    nivel1_path = os.path.abspath(os.path.join(script_dir, '../Nivel_1'))
    if nivel1_path not in sys.path: sys.path.append(nivel1_path)
    import former as n1 # Assume que former.py está em Nivel_1/
except ImportError as e:
    print(f"ERRO FATAL (Nível 2): Não foi possível importar 'former.py' do Nível 1.")
    print(f" Verifique a estrutura de pastas e o caminho: {nivel1_path}")
    print(f" Erro: {e}")
    exit(1)

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

# --- CONFIGURAÇÕES ---
# IP do PC no Box onde o Broker MQTT (Mosquitto) está rodando.
# !!! AJUSTE ESTE IP para o endereço correto do seu PC Debian !!!
BROKER_IP = "192.168.1.4"
# Porta padrão do MQTT.
BROKER_PORT = 1883
# Tópico MQTT onde os dados serão publicados.
MQTT_TOPIC = "telemetria/dados_brutos"

# Configurações da Interface CAN Ixxat
# A biblioteca IxxatCANSimple parece não usar 'channel' diretamente.
# Pode ser necessário passar um índice de hardware se tiver múltiplas interfaces Ixxat.
# Para este exemplo, assumimos que conectará à primeira interface encontrada.
# IXXAT_HW_INDEX = 0 # Descomente e ajuste se precisar especificar um índice
CAN_BAUDRATE = 500000 # Taxa de bits do barramento CAN (500 kbps)

# Caminho para a pasta com os arquivos CSV de descrição CAN (usado pelo Nível 1).
# Ajuste o caminho relativo conforme sua estrutura.
PASTA_CSV_COMPONENTES = "../Nivel_1/componentes_csv_linux/"

# Intervalo (em milissegundos) para o timeout da leitura CAN.
# Define quanto tempo esperar por novas mensagens antes de verificar a flag de parada.
CAN_RECEIVE_TIMEOUT_MS = 100
# --- FIM DAS CONFIGURAÇÕES ---

# --- Variáveis Globais ---
# Guarda a instância da interface CAN para poder desconectá-la ao parar.
bus_can = None
# Guarda a instância do cliente MQTT.
client_mqtt = None
# Evento para sinalizar parada da thread de leitura CAN.
parar_leitura_can = threading.Event()

# --- Função da Thread de Leitura CAN ---
def thread_leitura_can(cliente_mqtt_local, mapa_prioridade):
    """
    Função executada em uma thread separada para ler continuamente
    da interface CAN Ixxat, formatar os dados (usando Nível 1) e
    publicá-los via MQTT.

    Args:
        cliente_mqtt_local: A instância conectada do cliente Paho MQTT.
        mapa_prioridade: O dicionário {id_can_int: prioridade_int} carregado pelo Nível 1.
    """
    global bus_can, parar_leitura_can # Acessa as variáveis globais

    print(f"Nível 2 (Transmitter): Iniciando leitura CAN (Ixxat)...")
    try:
        # 1. Inicializa a interface CAN Ixxat
        bus_can = IxxatCANSimple()

        # 2. Conecta à interface CAN
        #    Passa a taxa de bits configurada.
        #    O método connect pode precisar de um índice de hardware se houver múltiplos.
        #    Ex: if not bus_can.connect(hw_index=IXXAT_HW_INDEX, baudrate=CAN_BAUDRATE):
        if not bus_can.connect(baudrate=CAN_BAUDRATE):
            print(f"ERRO FATAL (Nível 2): Falha ao conectar à interface CAN Ixxat (Baudrate: {CAN_BAUDRATE}).")
            # Sinaliza para a thread principal (se houver espera) que a inicialização falhou.
            parar_leitura_can.set() # Usamos a flag de parada para indicar falha aqui
            return # Encerra a thread
        print(f"Nível 2 (Transmitter): Conectado à interface CAN Ixxat (Baudrate: {CAN_BAUDRATE}).")

    except NameError as e:
         print(f"ERRO FATAL (Nível 2): Parece que IxxatCANSimple não está definida corretamente. {e}")
         parar_leitura_can.set()
         return
    except Exception as e:
        # Captura outros erros durante a conexão CAN (ex: driver não instalado, dispositivo não conectado)
        print(f"ERRO FATAL (Nível 2) ao inicializar/conectar CAN Ixxat: {e}")
        parar_leitura_can.set()
        return # Encerra a thread

    # --- Loop Principal de Leitura e Envio ---
    print(f"Nível 2 (Transmitter): Aguardando mensagens CAN...")
    while not parar_leitura_can.is_set(): # Continua enquanto a flag de parada não for levantada
        try:
            # 3. Recebe mensagens CAN
            #    O método receive da IxxatCANSimple retorna uma LISTA de mensagens
            #    ou uma lista vazia se o timeout ocorrer.
            #    Cada mensagem na lista é uma tupla: (can_id_int, dados_tupla_int)
            mensagens_recebidas = bus_can.receive(timeout=CAN_RECEIVE_TIMEOUT_MS)

            # Se não recebeu nenhuma mensagem neste ciclo, volta ao início do loop
            if not mensagens_recebidas:
                continue # Volta para o 'while not parar_leitura_can.is_set()'

            # Processa cada mensagem recebida na lista
            for can_id, data in mensagens_recebidas:
                # Se a flag de parada foi setada enquanto processava a lista, sai logo
                if parar_leitura_can.is_set(): break

                # 4. Obtém o Timestamp ATUAL:
                #    A biblioteca IxxatCANSimple (no exemplo) não fornece timestamp.
                #    Geramos o timestamp *agora*, no momento do processamento.
                #    A precisão será menor que a do hardware, mas é o melhor que temos.
                timestamp_atual = time.time()

                # 5. Chama o Nível 1 para Formatar:
                #    Passa o ID (int), os dados (convertidos para lista) e o timestamp gerado.
                pacote_formatado = n1.formatar_pacote_can(can_id, list(data), timestamp_atual, mapa_prioridade)

                # 6. Publica via MQTT (se o pacote foi formatado corretamente):
                if pacote_formatado:
                    try:
                        # Converte o dicionário Python para string JSON.
                        payload = json.dumps(pacote_formatado)
                        # Publica a string JSON no tópico MQTT configurado.
                        # Usamos qos=0 por padrão (mais rápido, pode perder pacotes).
                        # Para maior confiabilidade, considere qos=1.
                        result_info = cliente_mqtt_local.publish(MQTT_TOPIC, payload, qos=0)
                        # Log de debug opcional para verificar se a publicação foi aceita pela biblioteca
                        # if result_info.rc != mqtt.MQTT_ERR_SUCCESS:
                        #    print(f"AVISO (Nível 2): Falha ao enfileirar publicação MQTT (rc={result_info.rc})")
                        # else:
                        #    print(f"Nível 2: Pacote enviado -> {payload}") # Log verboso

                    except Exception as pub_e:
                        print(f"ERRO (Nível 2) ao publicar MQTT: {pub_e}")

            # Pequena pausa opcional para ceder CPU, se necessário (geralmente não)
            # time.sleep(0.001)

        except Exception as loop_e:
            # Captura erros inesperados durante o loop de leitura/envio.
            print(f"ERRO (Nível 2) no loop de leitura CAN: {loop_e}")
            # Espera um pouco antes de tentar novamente para evitar spam de erros.
            time.sleep(1)

    # --- Fim do Loop (Parada Solicitada) ---
    print("Nível 2 (Transmitter): Loop de leitura CAN encerrado.")
    # Desconecta da interface CAN ao sair do loop
    if bus_can:
        try:
            print("Nível 2 (Transmitter): Desconectando da interface CAN Ixxat...")
            bus_can.disconnect()
            print("Nível 2 (Transmitter): Interface CAN Ixxat desconectada.")
        except Exception as disc_e:
            print(f"ERRO (Nível 2) ao desconectar CAN Ixxat: {disc_e}")


# --- Bloco Principal de Execução ---
if __name__ == "__main__":
    # Este bloco é executado quando o script é chamado diretamente (python3 transmitter.py)

    # 1. Carrega o Mapa de Prioridades (usando o Nível 1)
    #    Chama a função do former.py para ler os CSVs.
    mapa_prioridade_global = n1.carregar_mapa_de_prioridade(PASTA_CSV_COMPONENTES)
    # Se o mapa não pôde ser carregado, podemos decidir parar ou continuar (com prioridade 4 para tudo)
    # if not mapa_prioridade_global:
    #     print("ERRO FATAL (Nível 2): Não foi possível carregar o mapa de prioridades. Encerrando.")
    #     exit(1)

    # 2. Configura e Conecta o Cliente MQTT
    client_mqtt = mqtt.Client() # Cria a instância do cliente MQTT
    try:
        print(f"Nível 2 (Transmitter): Conectando ao Broker MQTT em {BROKER_IP}:{BROKER_PORT}...")
        # Tenta conectar ao broker no IP e porta configurados. '60' é o keep_alive.
        client_mqtt.connect(BROKER_IP, BROKER_PORT, 60)
        # Inicia a thread de rede do Paho MQTT em background. Essencial!
        client_mqtt.loop_start()
        # Espera um pouco para garantir que a conexão foi estabelecida (opcional, mas bom)
        time.sleep(1)
        if not client_mqtt.is_connected():
             raise ConnectionError("Falha ao estabelecer conexão inicial com o Broker MQTT.")
        print(f"Nível 2 (Transmitter): Conectado ao Broker MQTT.")
    except Exception as e:
        print(f"ERRO FATAL (Nível 2): Não foi possível conectar ao Broker MQTT. Verifique o IP ({BROKER_IP}) e se o broker está rodando.")
        print(f"  Erro: {e}")
        exit(1) # Encerra o script se não conseguir conectar ao MQTT

    # 3. Cria e Inicia a Thread de Leitura CAN
    #    Cria um objeto Thread que executará nossa função 'thread_leitura_can'.
    #    Passa os argumentos necessários para a função: o cliente MQTT e o mapa.
    can_thread = threading.Thread(
        target=thread_leitura_can,
        args=(client_mqtt, mapa_prioridade_global),
        daemon=True, # Define como daemon para que ela encerre se o script principal terminar
        name="CANReaderThread" # Nomeia a thread para facilitar depuração
    )
    # Inicia a execução da thread. A função thread_leitura_can começará a rodar.
    can_thread.start()

    # --- Loop Principal (Mantém o script vivo e trata Ctrl+C) ---
    try:
        # Loop infinito que apenas espera. O trabalho real está na thread CAN e na thread MQTT.
        # Verifica periodicamente se a thread CAN ainda está viva (se ela falhou na inicialização)
        while can_thread.is_alive():
            # Verifica se a flag de parada foi setada (ex: por falha na inicialização da thread)
            if parar_leitura_can.is_set():
                 print("Nível 2 (Transmitter): Thread CAN falhou na inicialização. Encerrando.")
                 break # Sai do loop principal se a thread CAN falhar
            time.sleep(1) # Espera 1 segundo

        # Se saiu do loop porque a thread CAN não está mais viva (normalmente não deveria acontecer
        # a menos que haja um erro fatal dentro dela ou a inicialização falhe)
        if not parar_leitura_can.is_set(): # Se não foi uma parada normal solicitada
            print("AVISO (Nível 2): Thread de leitura CAN terminou inesperadamente.")


    except KeyboardInterrupt:
        # Captura o sinal de Ctrl+C pressionado pelo usuário no terminal.
        print("\nNível 2 (Transmitter): Ctrl+C recebido. Solicitando parada...")
        # Sinaliza para a thread de leitura CAN parar levantando a "bandeira".
        parar_leitura_can.set()
    except Exception as main_e:
        print(f"ERRO inesperado (Nível 2) no loop principal: {main_e}")
        # Tenta parar a thread CAN mesmo em caso de erro.
        parar_leitura_can.set()
    finally:
        # --- Bloco de Limpeza Final ---
        print("Nível 2 (Transmitter): Encerrando...")

        # Aguarda a thread de leitura CAN terminar sua execução (com um timeout).
        if can_thread.is_alive():
            print("Nível 2 (Transmitter): Aguardando thread CAN finalizar...")
            can_thread.join(timeout=5.0) # Espera até 5 segundos
            if can_thread.is_alive():
                 print("AVISO (Nível 2): Thread CAN não finalizou no tempo esperado.")

        # Garante a desconexão da interface CAN (caso a thread não tenha conseguido)
        if bus_can:
            try: bus_can.disconnect()
            except: pass # Ignora erros na desconexão final

        # Para a thread de rede MQTT e desconecta do broker de forma limpa.
        if client_mqtt and client_mqtt.is_connected():
            print("Nível 2 (Transmitter): Desconectando do Broker MQTT...")
            client_mqtt.loop_stop()
            client_mqtt.disconnect()
            print("Nível 2 (Transmitter): Desconectado do Broker MQTT.")

        print("Nível 2 (Transmitter): Programa finalizado.")