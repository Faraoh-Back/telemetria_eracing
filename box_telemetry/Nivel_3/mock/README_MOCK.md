# 🎭 Mock de Telemetria - E-Racing UNICAMP

Gerador de dados simulados para testar o dashboard de dinamômetro.

## 📋 O que faz?

Este script **simula dados realistas** de telemetria de um carro elétrico no dinamômetro, gerando um arquivo CSV idêntico ao que o `collector.py` (Nivel_3) produziria.

### ✨ Dados Simulados

- **4 Motores Elétricos** (A0, B0, A13, B13)
  - RPM com inércia realista (0-65000 rpm)
  - Torque variável (0-13000 Nm)
  - Potência calculada (kW)
  - Temperatura que aquece/resfria naturalmente (20-150°C)

- **2 Inversores** (M0, M13)
  - Tensão DC (~450V com variação)
  - Potência DC
  - Temperatura dos inversores
  - Códigos de erro aleatórios (raros)

- **VCU (Vehicle Control Unit)**
  - Posição do pedal (APS) 0-100%
  - Estados do sistema
  - Freio
  - Erros (muito raros para testar alertas)

### 🎬 Cenários Simulados

O mock simula **ciclos realistas de teste** de 30 segundos:

| Tempo | Cenário | Descrição |
|-------|---------|-----------|
| 0-5s | 🛑 Parado | Freio acionado, throttle 0% |
| 5-10s | ⚡ Acelerando | Aceleração progressiva até 80% |
| 10-20s | ➡️ Constante | Mantém ~70% throttle |
| 20-25s | 🔻 Desacelerando | Reduz throttle gradualmente |
| 25-30s | 🛑 Frenando | Freio acionado, throttle 0% |

Depois o ciclo se repete!

## 🚀 Como Usar

### 1️⃣ Vá para a pasta mock

```bash
cd Nivel_3/mock/
```

### 2️⃣ Execute o mock

```bash
python mock_telemetry.py
```

### 3️⃣ Acompanhe a geração

Você verá algo como:

```
╔═══════════════════════════════════════════════════════════════╗
║  🏎️  E-RACING UNICAMP - MOCK DE TELEMETRIA DINAMÔMETRO      ║
╚═══════════════════════════════════════════════════════════════╝

📁 Arquivo de saída: ../../Nivel_4/processados/log_processado_mock.csv
⏱️  Intervalo: 50ms (20 Hz)
⏳ Duração: 300s (5.0 min)

🎮 Cenários simulados:
   • 0-5s: Parado (freio)
   • 5-10s: Aceleração progressiva
   • 10-20s: Velocidade constante (~70%)
   • 20-25s: Desaceleração
   • 25-30s: Frenagem
   (Ciclo se repete)

▶️  Iniciando simulação...

⏱️  45.2s | 📦 904 amostras | 🎮 APS: 68.3% | 🔄 RPM: A0=42350 B0=41890 | 🌡️  Temp: 95°C
```

### 4️⃣ Após a geração, execute o dashboard

```bash
cd ../../Nivel_5/
python run_dyno.py
```

## ⚙️ Configurações

Você pode ajustar no início do arquivo `mock_telemetry.py`:

```python
INTERVALO_ESCRITA = 0.05  # 50ms entre escritas (20 Hz)
DURACAO_TESTE = 300       # 5 minutos de teste
VERBOSE = True            # Mostra progresso em tempo real
```

### Sugestões de Duração:

- **30 segundos**: Teste rápido (1 ciclo completo)
- **60 segundos**: Teste médio (2 ciclos)
- **300 segundos**: Teste completo (10 ciclos - 5 minutos)
- **600 segundos**: Teste longo (20 ciclos - 10 minutos)

## 📊 Formato de Saída

O arquivo gerado tem o formato:

```csv
SIGNAL_NAME,timestamp,id_can,priority,value unit
ACT_SPEED A0,1761552384.305,0x18FF01EA,1,12500 rpm
ACT_TORQUE A0,1761552384.305,0x18FF01EA,1,250.5 Nm
ACT_POWER A0,1761552384.305,0x18FF01EA,1,45.2 kw
...
```

**Idêntico** ao que o `collector.py` gera!

## 🎯 IDs CAN Utilizados

O mock usa os IDs CAN reais do arquivo VCU:

| ID CAN | Bloco |
|--------|-------|
| 0x18FF1080 | Master Control |
| 0x18FF00EA | Device Status M0 |
| 0x18FF00F7 | Device Status M13 |
| 0x18FF01EA | Actual Values Motor A0 |
| 0x18FF02EA | Actual Values Motor B0 |
| 0x18FF01F7 | Actual Values Motor A13 |
| 0x18FF02F7 | Actual Values Motor B13 |
| 0x18FF1180 | Setpoints Motor A0 |
| 0x18FF1280 | Setpoints Motor B0 |
| 0x18FFE180 | Setpoints Motor A13 |
| 0x18FFE280 | Setpoints Motor B13 |
| 0x18FF1515 | VCU Data Out |
| 0x18FF0DEA | Control Mobile 0 |
| 0x18FF0EF7 | Control Mobile 13 |

## 🔬 Física Simulada

### Motores
- **Inércia**: RPM não muda instantaneamente
- **Curva de Torque**: Máximo em baixas RPMs, reduz em altas RPMs
- **Potência**: P = T × ω (fórmula real)
- **Aquecimento**: Proporcional à potência
- **Resfriamento**: Natural, proporcional à diferença de temperatura

### Inversores
- **Tensão DC**: 450V nominal com variação realista
- **Potência DC**: Soma das potências dos motores do lado
- **Temperatura**: Aquece com carga, resfria naturalmente

### VCU
- **Pedal**: Transição suave entre estados
- **Erros**: Ocorrem aleatoriamente (muito raros)

## 🐛 Troubleshooting

### Erro: Pasta não encontrada

```bash
mkdir -p ../../Nivel_4/processados/
```

### Interromper a geração

Pressione `Ctrl+C`. O arquivo será salvo com os dados gerados até o momento.

### Arquivo muito grande

Reduza `DURACAO_TESTE` para gerar menos dados:

```python
DURACAO_TESTE = 60  # Apenas 1 minuto
```

### Dados parecem estranhos

Ajuste os limites nas classes:
- `rpm_max` em `MotorSimulator`
- `torque_max` em `MotorSimulator`
- `temp_max` em `MotorSimulator`

## 📈 Estatísticas Típicas

Para um teste de 5 minutos (300s):

- **Amostras**: ~6000 (20 Hz)
- **Tamanho do arquivo**: ~2-3 MB
- **Taxa de escrita**: 20 amostras/s
- **Sinais por amostra**: ~50

## 🎓 Entendendo o Código

### Classes Principais:

1. **`MotorSimulator`**: Simula um motor elétrico
   - `update()`: Atualiza RPM, torque, potência, temperatura
   - `get_signals()`: Retorna sinais formatados

2. **`InverterSimulator`**: Simula um inversor
   - `update()`: Atualiza tensão, potência, temperatura
   - `get_signals()`: Retorna sinais formatados

3. **`VCUSimulator`**: Simula a VCU
   - `update()`: Gerencia cenários e pedal
   - `get_signals()`: Retorna sinais da VCU

4. **`TelemetryMock`**: Orquestrador principal
   - `run()`: Loop principal de simulação
   - `write_sample()`: Escreve dados no CSV

## 💡 Dicas

- Execute o mock **antes** de iniciar o dashboard
- Use `VERBOSE = True` para acompanhar a geração
- Para testes rápidos, use 30-60 segundos
- Para demonstrações, use 5-10 minutos
- O arquivo é sobrescrito a cada execução

## 🎉 Pronto!

Agora você tem dados realistas para testar o dashboard sem precisar do carro real no dinamômetro!

---

**Desenvolvido para Formula SAE Electric 2025**  
**E-Racing UNICAMP**

Seguinte eu falei para um amigo resolver o problema que estava tendo, mas deu ruim, agora as tabelas e gráficos não estão sendo atualizados, e o status do motor precisa ser maior, tente resolver isso e melhore a visualização com a versões anteriores.