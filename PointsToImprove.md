---

## PointsToImprove.md

```markdown
# Pontos de Melhoria para o Sistema de Telemetria

Esta seção descreve possíveis otimizações e funcionalidades futuras para a arquitetura atual do sistema de telemetria (Níveis 1 a 7).

---

## 1. Redução de Latência na Visualização (Prioridade Alta) ⏱️

* **Problema:** O fluxo atual no Box (MQTT -> Nível 3 escreve CSV -> Nível 4 -> Nível 5 lê CSV -> Nível 5 publica ROS -> Nível 6 recebe ROS) introduz latência significativa devido às operações de escrita e leitura em disco (CSV) no caminho crítico dos dados em tempo real.
* **Proposta:**
    1.  **Modificar Nível 3 (`collector.py`):** Além de (ou em vez de) salvar o CSV bruto, este nível deve **processar os dados CAN** imediatamente ao recebê-los via MQTT (lendo os arquivos de descrição CAN e extraindo valores como Velocidade, Temperatura, etc.).
    2.  **Modificar Nível 5 (`publisher.py`):** Este nível deve receber os dados **já processados** diretamente do Nível 3 (via comunicação inter-thread/processo, como uma `Queue` em Python, ou via um tópico ROS 2 intermediário) e publicar esses dados **processados** (ex: `{'Velocidade': 50.0, 'RPM': 3000}`) num novo tópico ROS 2 (ex: `/telemetria/dados_processados`). **Eliminar a dependência de ler o CSV.**
    3.  **Modificar Nível 6 (`visualization.py`):** Inscrever-se no novo tópico ROS 2 `/telemetria/dados_processados` para receber diretamente os valores significativos.
* **Vantagens:** Redução drástica da latência de ponta a ponta, dados mais úteis diretamente no Nível 6, simplificação do Nível 5. O Nível 3 ainda pode salvar o log CSV bruto em paralelo como backup, se desejado.
* **Implementação Sugerida:** Considerar **unificar** a lógica de recepção MQTT (Nível 3), processamento CAN e publicação ROS (Nível 5 de dados processados) em **um único script/nó ROS 2** no Box para maior eficiência.

---

## 2. Melhorias no Front-End (Nível 6 - `visualization.py`) 📊

* **Problema:** A visualização atual mostra apenas os dados brutos do CSV. Com a Proposta 1 implementada, podemos exibir informações muito mais ricas.
* **Proposta:**
    1.  **Exibir Dados Processados:** A tabela principal (ou novas tabelas/widgets) deve mostrar os **nomes dos sinais CAN** (ex: "VCU\_Velocidade", "BMS\_TempCelula0") e seus **valores reais** com unidades.
    2.  **Widgets Visuais:** Utilizar:
        * **Mostradores (Gauges):** Para valores importantes (Velocidade, RPM, SoC).
        * **Indicadores de Status:** Labels coloridos ou ícones para estados booleanos (ex: TS Ativo, Falha IMD).
        * **Barras de Progresso:** Para níveis (ex: Posição do Pedal).
    3.  **Gráficos Simples:** Integrar gráficos de linha básicos (usando `matplotlib.pyplot` e `matplotlib.backends.backend_tkagg`) para mostrar tendências recentes (últimos X segundos) de 1-3 variáveis chave (ex: Velocidade vs. Tempo).
    4.  **Organização:** Usar `ttk.LabelFrame` para agrupar widgets relacionados (ex: "Dados BMS", "Dados VCU") ou `ttk.Notebook` para criar abas.
    5.  **Otimização de Atualização:** Atualizar apenas os widgets cujos valores mudaram, em vez de redesenhar tudo, para melhorar a performance da UI.

---

## 3. Aumentar Robustez e Confiabilidade (Médio Prazo) 💪

* **Backup Local no Carro:**
    * **Proposta:** Modificar o Nível 2 (`transmitter.py`) para **salvar os dados brutos ou formatados em um arquivo CSV diretamente na Jetson**, em paralelo com o envio via MQTT.
    * **Vantagem:** Garante a gravação dos dados mesmo durante falhas temporárias do Wi-Fi, servindo como backup essencial. Requer gerenciamento de espaço em disco na Jetson.
* **MQTT QoS (Qualidade de Serviço):**
    * **Proposta:** No Nível 2 (`transmitter.py`), usar `qos=1` ao publicar dados importantes (`client.publish(topic, payload, qos=1)`).
    * **Vantagem:** Garante que mensagens importantes cheguem ao broker "pelo menos uma vez", mesmo com instabilidade na rede. O Nível 3 (ou o receptor modificado da Proposta 1) precisaria lidar com possíveis duplicatas (ex: checando timestamps).
* **MQTT LWT (Last Will and Testament):**
    * **Proposta:** No Nível 2 (`transmitter.py`), configurar uma mensagem LWT ao conectar ao broker (ex: publicar `{"status": "offline"}` no tópico `telemetria/carro/status` se a conexão cair inesperadamente).
    * **Vantagem:** Permite que o Nível 6 (ou outro sistema) saiba imediatamente se a comunicação com o carro foi perdida. O Nível 2 publicaria `{"status": "online"}` ao conectar normalmente.
* **Tratamento de Erros Aprimorado:**
    * Adicionar mais blocos `try...except` em todos os níveis para lidar com falhas (ex: arquivos CSV de descrição ausentes/corrompidos, falha ao conectar MQTT/ROS, disco cheio).
    * Exibir mensagens de erro/status de forma clara na interface do Nível 6.

---

## 4. Otimizações de Formato e Ferramentas (Longo Prazo) 🛠️

* **Mensagens ROS 2 Personalizadas:**
    * **Proposta:** Em vez de publicar dados como JSONs (`std_msgs/String`), definir tipos de mensagens ROS 2 personalizadas (arquivos `.msg`) que representem semanticamente os dados (ex: `BmsStatus.msg`, `VcuData.msg`). O Nível 5 (modificado) publicaria essas mensagens, e o Nível 6 as receberia.
    * **Vantagem:** Mais eficiente para o ROS 2, oferece checagem de tipos, facilita a integração com ferramentas padrão do ROS como `rqt_plot`, `rqt_graph`, `ros2 bag record`.
* **Banco de Dados Time-Series:**
    * **Proposta:** Em vez (ou além) de salvar em CSV no Box, considerar salvar os dados processados num banco de dados otimizado para séries temporais (como InfluxDB ou TimescaleDB).
    * **Vantagem:** Consultas muito mais rápidas e eficientes para análise pós-corrida, facilita a criação de dashboards mais avançados (ex: com Grafana).
* **Interface Web (Alternativa ao Tkinter):**
    * **Proposta:** Substituir ou complementar a UI Tkinter (Nível 6) por uma interface baseada em web (ex: usando Flask/Django no backend + JavaScript/React/Vue no frontend). A comunicação com o ROS 2 pode ser feita via `roslibpy` ou `ros2-web-bridge`.
    * **Vantagem:** Acesso de múltiplos dispositivos (laptops, tablets), interfaces potencialmente mais ricas e interativas. Maior complexidade de desenvolvimento.

**Recomendação:** Priorize a **Proposta 1** para a melhoria de latência, seguida pelas **melhorias no Front-End (Proposta 2)**. Implemente o **Backup no Carro** e as funcionalidades **MQTT (QoS/LWT)** da **Proposta 3** para robustez. As otimizações da **Proposta 4** são interessantes para evolução futura do sistema.