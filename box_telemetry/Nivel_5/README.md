# 🏎️ E-Racing UNICAMP - Telemetria Dinamômetro

Sistema de telemetria especializado para testes no dinamômetro, com foco em VCU, motores e inversores.

## 📋 Características

### ✨ Funcionalidades Principais

- **9 Métricas Principais**: RPM médio, torque total, potência total, temperaturas, tensão DC, pedal
- **6 Gráficos em Tempo Real**: 
  - RPM dos 4 motores
  - Torque dos 4 motores
  - Potência dos 4 motores
  - Temperaturas (motores + inversores)
  - Tensão DC Bus
  - Posição do pedal (APS)
- **Status dos 4 Motores**: Visualização resumida com RPM e temperatura
- **14 Blocos VCU**: Detalhamento completo dos sinais organizados por blocos
- **Sistema de Alertas**: Monitoramento de erros críticos em tempo real
- **Exportação de Dados**: Salva análise completa em CSV

### 🎯 Diferenças da Versão Original

| Aspecto       | Versão Original                   | Versão Dinamômetro                        |
|---------      |----------------                   |-------------------                        |
| Foco          | Telemetria geral (BMS, IMU, etc)  | VCU, Motores e Inversores                 |
| Métricas      | 6 itens                           | 9 itens                                   |
| Gráficos      | Baterias, Automotivo, Suspensão   | RPM, Torque, Potência, Temp, DC, Pedal    |
| Organização   | Por sistemas gerais               | Por blocos VCU específicos                |
| Sensores      | 96 células BMS + diversos         | Focado em 4 motores + 2 inversores        |

## 🚀 Instalação

### Requisitos

- Python 3.7+
- Dependências:
  ```bash
  pip install Pillow matplotlib watchdog
  ```

### Estrutura de Arquivos

```
Nivel_5/
├── config_dyno.py           # Configurações
├── data_manager_dyno.py     # Gerenciamento de dados
├── ui_manager_dyno.py       # Interface gráfica
├── main_dyno.py             # Aplicação principal
├── run_dyno.py              # Script de execução
├── imgs/
│   └── logo.jpg             # Logo da equipe
└── README_DYNO.md           # Esta documentação
```

## 🎮 Como Usar

### Execução Rápida

```bash
python run_dyno.py
```

### Verificar Dependências

```bash
python run_dyno.py --check
```

### Ajuda

```bash
python run_dyno.py --help
```

## 📊 Interface

### Layout Principal

```
┌───────────────────────────────────────────────────────── ┐
│  HEADER: Logo + Controles + Status                       │
├────────────────────── ┬──────────────────────────────────┤
│  ESQUERDA (60%)       │  DIREITA (40%)                   │
│                       │                                  │
│  ⚠️  ALERTAS          │  🎯 MÉTRICAS (Grid 3x3)          │
│                       │                                  │
│  📊 GRÁFICOS          │  📋 TODOS OS SINAIS              │
│  - RPM                │     (Tabela Raw)                 │
│  - Torque             │                                  │
│  - Potência           │  🔧 DETALHES POR BLOCO           │
│  - Temperaturas       │     (14 abas VCU)                │
│  - DC Bus             │                                  │
│  - Pedal              │                                  │
│                       │                                  │
│  🏎️ STATUS MOTORES    │                                  │
│  [A0] [A13]           │                                  │
│  [B0] [B13]           │                                  │
└────────────────────── ┴──────────────────────────────────┘
```

### Métricas Principais (9 itens)

1. **RPM MÉDIO**: Média dos 4 motores
2. **TORQUE TOTAL**: Soma dos torques
3. **POTÊNCIA TOTAL**: Soma das potências
4. **TEMP. MOTOR MAX**: Maior temperatura dos motores
5. **TEMP. INV MAX**: Maior temperatura dos inversores
6. **TENSÃO DC MÉDIA**: Média dos DC Bus
7. **PEDAL (APS)**: Posição do pedal
8. **RPM MOTOR A0**: RPM individual frente direita
9. **RPM MOTOR B0**: RPM individual traseira direita

### 14 Blocos VCU

1. **Status of the master control**: Status geral do sistema
2. **Device status of the MOBILE 0**: Status inversor direito
3. **Device status of the MOBILE 13**: Status inversor esquerdo
4. **Actual values from motor A 0**: Valores reais motor A frente direita
5. **Actual values from motor B 0**: Valores reais motor B traseira direita
6. **Actual values from motor A 13**: Valores reais motor A frente esquerda
7. **Actual values from motor B 13**: Valores reais motor B traseira esquerda
8. **Setpoints for motor A 0**: Setpoints motor A0
9. **Setpoints for motor B 0**: Setpoints motor B0
10. **Setpoints for motor A 13**: Setpoints motor A13
11. **Setpoints for motor B 13**: Setpoints motor B13
12. **VCU_DATA_OUT**: Dados de saída VCU (pedal, freio, estado)
13. **SETPOINTS CONTROL MOBILE 0**: Controles inversor direito
14. **SETPOINTS CONTROL MOBILE 13**: Controles inversor esquerdo

## 🎨 Identificação dos Motores

- **A0** (Laranja): Motor A - Frente Direita (FD)
- **B0** (Azul): Motor B - Traseira Direita (TD)
- **A13** (Verde): Motor A - Frente Esquerda (FE)
- **B13** (Roxo): Motor B - Traseira Esquerda (TE)

## ⚠️ Sistema de Alertas

O sistema monitora automaticamente:

- ❌ **APPS_RANGE_ERROR**: Erro no range do pedal
- ⚠️ **SAFETY_OK**: Sistema de segurança (invertido - deve ser TRUE)
- ❌ **ERROR CODE M0/M13**: Códigos de erro dos inversores
- ❌ **ACT_ERRORSTATUS**: Status de erro dos motores

**Cores:**
- 🟢 Verde: Sem alertas
- 🟡 Amarelo: Avisos
- 🔴 Vermelho: Erros críticos

## 🔧 Controles

- **▶️ Iniciar**: Inicia captura e análise
- **⏸️ Parar**: Pausa análise
- **🔄 Zerar**: Reseta todos os dados
- **💾 Exportar**: Salva dados em CSV

## 📁 Formato do Log de Entrada

O sistema lê arquivos CSV do formato:
```
SIGNAL_NAME,timestamp,id_can,priority,value unit
```

Exemplo:
```
ACT_SPEED A0,1761552384.305087,0x18FF01EA,1,12500 rpm
ACT_TORQUE A0,1761552384.305087,0x18FF01EA,1,250.5 Nm
ACT_POWER A0,1761552384.305087,0x18FF01EA,1,45.2 kW
ACT_MOTORTEMPERATURE A0,1761552384.305087,0x18FF01EA,1,85 °C
```

## 📤 Formato de Exportação

CSV com colunas:
- `timestamp`: Data/hora
- `signal_name`: Nome do sinal
- `value`: Valor numérico
- `unit`: Unidade
- `block`: Bloco VCU
- `id_can`: ID CAN
- `prioridade`: Prioridade

## 🐛 Troubleshooting

### Problema: Gráficos não aparecem

**Solução**: Verifique se matplotlib está instalado
```bash
pip install matplotlib
```

### Problema: Não detecta logs novos

**Solução**: Verifique se watchdog está instalado
```bash
pip install watchdog
```

### Problema: Logo não aparece

**Solução**: Verifique se existe `imgs/logo.jpg` ou deixe sem logo (texto será usado)

### Problema: Sem dados na interface

**Solução**: 
1. Verifique se existe log em `../Nivel_4/processados/`
2. Certifique-se que o Nivel_3 (collector) está rodando
3. Verifique formato do log CSV

## 📝 Notas de Desenvolvimento

### Diferenças do Collector

O `collector.py` do Nivel_3 já está preparado para ler o VCU CSV. Não precisa modificações.

### Arquivo VCU CSV

O sistema usa apenas:
- `CAN Description 2025 - VCU.csv`

Localizado em: `Nivel_3/componentes_csv_linux/`

### Sinais Ignorados

Sinais que não fazem parte do VCU (ex: BMS, VCELL, TCELL, IMU VENTOR) são ignorados nesta versão e aparecem apenas na tabela "TODOS OS SINAIS".

## 🔮 Próximas Melhorias

- [ ] Cálculo automático de eficiência
- [ ] Mapeamento de curva de torque vs RPM
- [ ] Detecção automática de anomalias
- [ ] Comparação entre runs
- [ ] Exportação para formatos de análise (MoTeC, etc)

## 👥 Equipe E-Racing UNICAMP

Desenvolvido para Formula SAE Electric 2025

---

**Versão**: 2.0 Dinamômetro  
**Última atualização**: 2025