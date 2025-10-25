HowToExecute.md

Markdown

# Como Executar o Sistema de Telemetria

Este guia detalha os passos para configurar e executar o sistema de telemetria modularizado, tanto no veículo (Jetson/Carro) quanto na estação base (Debian/Box).

## Estrutura de Pastas Esperada

Certifique-se de que seu projeto esteja organizado da seguinte forma:

telemetria_eracing/ 
│   ├── box_telemetry
│   ├── Nivel_3
│   │   └── collector.py
│   ├── Nivel_4
│   │   └── log_teste_local_2025-10-23_23-44-18.csv *Tirar com o .gitignore
│   ├── Nivel_5
│   │   ├── publisher.py
│   │   └── ros2_Ws *Tirar com o .gitignore
│   │       ├── build
│   │       ├── install
│   │       ├── log
│   │       └── src
│   ├── Nivel_6
│   │   └── visualization.py
│   └── Nivel_7
│       └── conductor.py
├── car_telemetry
│   ├── Nivel_1
│   │   ├── componentes_csv_linux
│   │   │   ├── CAN Description 2025 - ACD.csv
│   │   │   ├── CAN Description 2025 - BMS.csv
│   │   │   ├── CAN Description 2025 - LV_BMS.csv
│   │   │   ├── CAN Description 2025 - PAINEL.csv
│   │   │   ├── CAN Description 2025 - PT.csv
│   │   │   └── CAN Description 2025 - VCU.csv
│   │   └── former.py
│   └── Nivel_2
│       └── transmitter.py
├── HowToExecute.md
├── PointsToImprove.md
├── README.md
├── requirements.txt
└── test
    ├── dados_brutos_telemetria_teste_local
    │   └── log_teste_local_2025-10-23_23-44-18.csv *Tirar com o .gitignore
    ├── receved_pachage.py
    ├── send_pachage.py
    └── txt.txt


**Importante:** Verifique os caminhos relativos (ex: `../Nivel_X/`) dentro dos scripts Python para garantir que correspondam a esta estrutura.

---

## 1. Configuração do Ambiente (Ambas as Máquinas)

Execute estes passos tanto no PC Debian (Box) quanto na Jetson (Carro), adaptando conforme necessário.

### 1.1. Pré-requisitos Básicos

Instale as ferramentas essenciais:

```bash
# Atualiza a lista de pacotes
sudo apt update

# Instala Python 3, Pip e ferramentas de ambiente virtual
sudo apt install -y python3 python3-pip python3-full

# Instala Git (se precisar clonar o repositório)
sudo apt install -y git

1.2. Obter o Código

Clone o repositório ou copie os arquivos para a máquina:
Bash

# Exemplo com Git
git clone <URL_DO_SEU_REPOSITORIO> telemetria_eracing
cd telemetria_eracing

1.3. Instalar Dependências Específicas de Cada Máquina

No PC Debian (Box):
Bash

# Broker MQTT
sudo apt install -y mosquitto mosquitto-clients

# ROS 2 (Ex: Humble - SIGA O GUIA OFICIAL PARA SEU DEBIAN!)
# [https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html)
# (Inclui configurar locale, repositórios, sudo apt install ros-humble-desktop, etc.)
# Instalar ferramenta de build do ROS 2
sudo apt install -y python3-colcon-common-extensions

# Suporte Tkinter para a Interface Gráfica (Nível 6)
sudo apt install -y python3-tk

# Dependências Python via apt (alternativa ao pip para evitar conflitos)
sudo apt install -y python3-paho-mqtt python3-pandas python3-watchdog

Na Jetson (Carro):
Bash

# Interface CAN
sudo apt install -y can-utils

# Dependências Python via apt
sudo apt install -y python3-paho-mqtt python3-pandas python3-can

1.4. (Opcional, Mas Recomendado) Configurar Ambiente Virtual Python

Isso isola as dependências do projeto. Execute na pasta raiz telemetria_eracing/ em ambas as máquinas:
Bash

# Criar ambiente virtual
python3 -m venv .venv

# Ativar ambiente (FAÇA ISSO EM CADA NOVO TERMINAL ANTES DE RODAR OS SCRIPTS)
source .venv/bin/activate
# O prompt mudará para indicar o ambiente ativo, ex: (.venv) user@host:...$

# (Opcional) Instalar dependências Python via pip (se não usou apt)
# pip install --upgrade pip
# pip install -r requirements.txt

2. Configuração Específica dos Scripts

2.1. No Carro (Jetson)

    Edite car_telemetry/Nivel_2/transmitter.py:

        Ajuste a variável BROKER_IP para ser o endereço IP do seu PC Debian (Box) na rede local (ex: "192.168.1.4"). Use ip a no Debian para descobrir.

        Verifique se CAN_INTERFACES (ex: ["can0", "can1"]) e PASTA_CSV_COMPONENTES (caminho para os arquivos de descrição CAN) estão corretos.

2.2. No Box (Debian)

    Verifique os caminhos relativos em:

        box_telemetry/Nivel_3/collector.py (para PASTA_ARMAZENAMENTO = "../Nivel_4/")

        box_telemetry/Nivel_5/publisher.py (para PASTA_LOGS_CSV = "../Nivel_4/")

        box_telemetry/Nivel_7/conductor.py (para os imports dos outros níveis).

    Os IPs (BROKER_IP) nos scripts do Box (collector.py, visualization.py) devem estar configurados como "localhost".

3. Execução do Sistema

3.1. No Box (Debian)

    Iniciar Broker MQTT:
    Bash

sudo systemctl start mosquitto
sudo systemctl status mosquitto # Verificar se está 'active (running)'
# Opcional: Habilitar início automático no boot
# sudo systemctl enable mosquitto

Iniciar o Orquestrador (Nível 7):

    Abra um novo terminal.

    Ative o ambiente ROS 2: (Ex: Humble)
    Bash

source /opt/ros/humble/setup.bash
# Se você compilou um workspace ROS 2:
# source /caminho/para/telemetria_eracing/install/setup.bash

(Se usar) Ative o Ambiente Virtual Python:
Bash

source /caminho/para/telemetria_eracing/.venv/bin/activate

Navegue até a pasta raiz do projeto:
Bash

cd /caminho/para/telemetria_eracing/

Execute o Conductor:
Bash

        python3 box_telemetry/Nivel_7/conductor.py

        Isso iniciará a interface gráfica (Nível 6) e, em background, os Níveis 3 e 5.

3.2. No Carro (Jetson)

    Iniciar o Transmissor (Nível 2):

        Abra um terminal.

        (Se usar) Ative o Ambiente Virtual Python:
        Bash

source /caminho/para/telemetria_eracing/.venv/bin/activate

Navegue até a pasta do Nível 2:
Bash

cd /caminho/para/telemetria_eracing/car_telemetry/Nivel_2/

Execute o Transmissor:
Bash

        python3 transmitter.py

3.3. Verificação

    O terminal do conductor.py (Box) deve mostrar logs dos Níveis 3, 5 e 6 iniciando.

    A janela do Tkinter (Nível 6) deve aparecer no Box.

    O terminal do transmitter.py (Carro) deve mostrar logs de conexão MQTT e pacotes enviados.

    Os dados enviados pelo carro devem aparecer na tabela da interface gráfica no Box.

    Novos arquivos CSV devem ser criados na pasta box_telemetry/Nivel_4/.

4. Parando o Sistema

    Método Normal: Feche a janela do Tkinter (Nível 6) no Box. O conductor.py detectará o fechamento e solicitará a parada dos Níveis 3 e 5 antes de encerrar.

    Método Alternativo: Pressione Ctrl+C no terminal onde o conductor.py está rodando.

    No Carro: Pressione Ctrl+C no terminal onde o transmitter.py está rodando.

    Broker: O serviço Mosquitto continuará rodando em segundo plano. Para pará-lo: sudo systemctl stop mosquitto.