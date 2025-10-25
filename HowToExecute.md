Estrutura de Pastas Assumida

Vamos assumir que você organizou seu código da seguinte forma:

telemetria_erancing/
├── car_telemetry/
│   ├── Nivel_1/
│   │   ├── former.py
│   │   └── componentes_csv_linux/ # Pasta com os arquivos CAN Description *.csv
│   └── Nivel_2/
│       └── transmitter.py
└── box_telemetry/
    ├── Nivel_3/
    │   └── collector.py
    ├── Nivel_4/        # Esta pasta será criada automaticamente
    ├── Nivel_5/
    │   └── publisher.py # O nome do seu arquivo aqui
    └── Nivel_6/
        └── visualization.py

    IMPORTANTE: Ajuste os caminhos relativos nos scripts (../Nivel_X/) se sua estrutura for diferente.

1. Passo a Passo: Instalação do Zero no Debian (box_telemetry)

Este guia é para o computador do box_telemetry (seu PC Debian). A Jetson (car_telemetry) terá passos similares, mas adaptados.

Passo 1.1: Pré-requisitos Básicos (Python, Pip, Git)

Abra um terminal e execute:

# Atualiza a lista de pacotes
sudo apt update

# Instala Python 3, Pip (gerenciador de pacotes Python) e Venv (ambientes virtuais)
# python3-full inclui venv e outras ferramentas úteis.
sudo apt install -y python3 python3-pip python3-full

# Instala Git (para baixar o código, se estiver num repositório)
sudo apt install -y git

# Verifica as instalações
python3 --version
pip3 --version
git --version

Passo 1.2: Obter o Código

    Se o código estiver no Git:

git clone <URL_DO_SEU_REPOSITORIO>
cd telemetria_erancing

Se você já tem os arquivos: Copie a pasta telemetria_erancing para o local desejado e navegue até ela no terminal:
Bash

    cd /caminho/para/telemetria_erancing

Passo 1.3: Instalar Dependências do Sistema

Estas são dependências que NÃO são instaladas via pip.

# 1. Broker MQTT (Mosquitto)
sudo apt install -y mosquitto mosquitto-clients

# 2. ROS 2 (Exemplo para Humble - Verifique a versão correta para seu Debian!)
#    A instalação do ROS 2 é complexa. SIGA O GUIA OFICIAL para sua versão do Debian:
#    => https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html
#    Resumo dos passos (ADAPTE CONFORME O GUIA OFICIAL):
#    a. Configurar locale (UTF-8)
#    b. Adicionar repositório ROS 2 (apt sources, key)
#    c. sudo apt update
#    d. sudo apt install ros-humble-desktop # Ou ros-humble-ros-base se não precisar de GUI/simuladores
#    e. Instalar colcon (ferramenta de build): sudo apt install python3-colcon-common-extensions

# 3. Suporte Tkinter para Python (para Nível 6)
sudo apt install -y python3-tk

# 4. Pandas (Alternativa via apt, pode ajudar a evitar problemas de compilação)
#    (Se preferir instalar via pip com requirements.txt, pule este)
# sudo apt install -y python3-pandas

# 5. Watchdog (Alternativa via apt)
#    (Se preferir instalar via pip com requirements.txt, pule este)
# sudo apt install -y python3-watchdog

    MUITO IMPORTANTE: A instalação do ROS 2 é a parte mais crítica. Dedique tempo para seguir o guia oficial corretamente.

Passo 1.4: Configurar Ambiente Virtual Python (Recomendado)

Usar um ambiente virtual isola as dependências do seu projeto do Python do sistema, evitando conflitos.

# Dentro da pasta raiz 'telemetria_erancing/'

# Cria um ambiente virtual chamado '.venv' (o '.' torna a pasta oculta)
python3 -m venv .venv

# Ativa o ambiente virtual (o prompt do terminal mudará)
source .venv/bin/activate

# Agora, qualquer comando 'pip' ou 'python' usará este ambiente isolado.
# O prompt deve mostrar (.venv) no início. Ex: (.venv) caire@Oltado:~/telemetria_erancing$

Passo 1.5: Instalar Dependências Python (via Pip)

Com o ambiente virtual ativo, instale as bibliotecas listadas no requirements.txt:

# Garante que pip está atualizado dentro do venv
pip install --upgrade pip

# Instala as dependências do arquivo
pip install -r requirements.txt

Passo 1.6: Compilar Pacotes ROS 2 (Se Aplicável)

Se os seus scripts de Nível 5 e 6 foram estruturados como pacotes ROS 2 (com package.xml, setup.py), você precisa compilá-los:

# Certifique-se que o ambiente ROS 2 está ativo (source)
# Exemplo para Humble:
source /opt/ros/humble/setup.bash

# Na raiz do seu workspace ROS (pode ser a própria pasta 'telemetria_erancing/'
# ou uma pasta 'ros2_ws/' contendo 'src/seu_pacote')
colcon build --symlink-install # O symlink ajuda no desenvolvimento

# Após o build, source o setup local do seu workspace
# Exemplo se compilou dentro de 'telemetria_erancing/':
source install/setup.bash

    Se seus scripts NÃO são pacotes ROS 2, você pode pular este passo.

2. Passo a Passo: Como Rodar o Sistema (box_telemetry)

Após a instalação completa:

    Abra o Terminal 1 (Broker MQTT):

        Inicie e verifique o serviço Mosquitto:

    sudo systemctl start mosquitto
    sudo systemctl status mosquitto # Deve mostrar 'active (running)'
    sudo systemctl enable mosquitto # Opcional: para iniciar no boot

    Você pode monitorar os logs do broker (opcional): sudo journalctl -u mosquitto -f

Abra o Terminal 2 (Orquestrador Nível 6):

    Ative o ambiente ROS 2: (Necessário em cada novo terminal)

source /opt/ros/humble/setup.bash
# Se compilou seu workspace, source o setup local também:
# source /caminho/para/telemetria_erancing/install/setup.bash

Ative o Ambiente Virtual Python:

source /caminho/para/telemetria_erancing/.venv/bin/activate

Navegue até a pasta do Nível 6:

        cd /caminho/para/telemetria_erancing/box_telemetry/Nivel_6/

        Execute o Orquestrador:

            Se for um script simples: python3 visualization.py

            Se for um pacote ROS 2: ros2 run <nome_pacote_nivel6> <nome_entrypoint_nivel6>

        Este comando deve:

            Iniciar a interface gráfica (Nível 6).

            Iniciar o Nível 3 (Collector) em background.

            Iniciar o Nível 5 (Publisher) em background.

            Começar a exibir os dados na tabela à medida que chegam.

3. Passo a Passo: Instalação e Execução (Jetson - car_telemetry)

Os passos são muito similares aos do box_telemetry, mas focados nas dependências do car_telemetry e sem ROS 2 (a menos que você decida usar ROS 2 na Jetson também, o que não parece ser o caso nos scripts fornecidos).

    Pré-requisitos: Instalar Python 3, Pip, Venv, Git (Passo 1.1).

    Obter o Código: (Passo 1.2).

    Instalar Dependências do Sistema:

    sudo apt update
    # Essencial para a interface CAN física
    sudo apt install -y can-utils
    # Pandas (se preferir via apt)
    # sudo apt install -y python3-pandas

    Configurar Ambiente Virtual: (Passo 1.4).

    Instalar Dependências Python: (Passo 1.5). O requirements.txt instalará paho-mqtt, python-can, pandas.

    Configurar o Nível 2 (transmitter.py):

        Edite o arquivo /caminho/para/telemetria_erancing/car_telemetry/Nivel_2/transmitter.py.

        AJUSTE a variável BROKER_IP para ser o endereço IP do seu PC Debian (box_telemetry) na rede local (ex: "192.168.1.4").

        Verifique se CAN_INTERFACES e PASTA_CSV_COMPONENTES estão corretos para a Jetson.

    Rodar o Nível 2:

        Ative o Ambiente Virtual: source /caminho/para/telemetria_erancing/.venv/bin/activate

        Navegue até a pasta do Nível 2: cd /caminho/para/telemetria_erancing/car_telemetry/Nivel_2/

        Execute o Transmissor: python3 transmitter.py

Com isso, a Jetson deve começar a ler o CAN, formatar os dados usando o Nível 1, e enviar via MQTT para o Broker no seu PC Debian. O Nível 3 no Debian receberá, salvará no CSV, o Nível 5 detectará a mudança, publicará no ROS 2, e o Nível 6 exibirá na sua tela. 🎉