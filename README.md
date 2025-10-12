## Telemetria_Eracing
Este repositório serve de apoio ao desenvolvimento de um sistema de telemetria para equipe Unicamp Eracing.

#Comandos para usar ROS:

#primeiro, depois de qualquer atualzação
colcon build no diretório da pasta ros2

setup ~/.bashrc

ros2 run box_backend box_telemetria 

usr/bin/mosquitto
mosquitto -v -c meu.config

Como Rodar o Projeto (Instrução Completa)

Agora que você tem o arquivo de dependências, o processo para configurar e rodar o projeto do zero em qualquer máquina (seja na Jetson do carro ou no computador do box) fica muito mais simples.

Siga estes passos:

Passo 1: Instalar as Dependências

Este passo deve ser feito tanto na Jetson (carro) quanto no computador do box.

    Abra o terminal.

    Navegue até a pasta onde estão os seus scripts Python e o arquivo requirements.txt que você acabou de criar.

    Execute o seguinte comando. Ele vai ler o arquivo requirements.txt e instalar automaticamente todas as bibliotecas listadas com um único comando:
    Bash

    pip install -r requirements.txt

    O pip cuidará de baixar e instalar paho-mqtt, python-can e pandas para você.

Passo 2: Iniciar o Broker MQTT (No Computador do Box)

O broker é o servidor central que gerencia as mensagens MQTT. Ele precisa estar rodando antes de qualquer outra coisa.

    No computador do box, abra um novo terminal.

    Inicie o broker. Se você estiver usando o Mosquitto, o comando geralmente é:
    Bash

    mosquitto -v

    O -v é para o modo "verbose", que mostra as conexões e mensagens no terminal, o que é ótimo para depuração.

    Deixe este terminal aberto. Ele é o seu servidor de mensagens.

Passo 3: Iniciar o Receptor (No Computador do Box)

Agora, vamos rodar o script que recebe e salva os dados.

    No computador do box, abra outro terminal.

    Navegue até a pasta do seu projeto.

    Execute o script do Nível 3 e 4:
    Bash

    python3 nivel_3_e_4_receptor.py

    Você verá a mensagem "Conectado ao Broker MQTT com sucesso!" e ele ficará aguardando os dados.

Passo 4: Iniciar o Transmissor (Na Jetson do Carro)

Finalmente, vamos iniciar o script no carro para começar a coletar e enviar os dados.

    Na Jetson, abra um terminal.

    Navegue até a pasta do projeto (onde estão nivel_1_formatador.py, nivel_2_transmissor.py e a pasta componentes_csv_linux).

    IMPORTANTE: Verifique se a variável BROKER_IP no arquivo nivel_2_transmissor.py está configurada com o endereço IP correto do computador do box na rede Wi-Fi.

    Execute o script do Nível 2:
    Bash

    python3 nivel_2_transmissor.py

Resumo do Processo

    Em cada máquina: pip install -r requirements.txt

    No Box (Terminal 1): mosquitto -v

    No Box (Terminal 2): python3 nivel_3_e_4_receptor.py

    No Carro: python3 nivel_2_transmissor.py

Assim que você executar o Passo 4, começará a ver as mensagens de "Pacote enviado" no terminal do carro e, simultaneamente, as mensagens de "Dado recebido e salvo" no terminal do receptor no box. O seu arquivo .csv na pasta dados_brutos_telemetria começará a ser preenchido em tempo real.