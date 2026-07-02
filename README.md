# 🔧 Armário Inteligente de Ferramentas

Sistema de controle de retirada e devolução de ferramentas com ESP32, RFID e servo motor, comunicando via protocolo **MQTT** sobre WiFi.  
Desenvolvido por **Lucas** e **Gustavo**.

---

## 📋 Sobre o Projeto

O usuário se identifica com uma tag RFID pessoal. O ESP32 publica a requisição em um broker MQTT (Mosquitto). O app Python no PC decide se autoriza o acesso, aciona o servo motor para abrir a tranca e registra cada ferramenta retirada ou devolvida via etiquetas RFID individuais. Após 35 segundos de inatividade, o armário trava automaticamente.

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────┐     WiFi / MQTT      ┌──────────────────┐     ┌─────────────────┐
│  ESP32      │ ──── armario/req ──► │  Broker MQTT     │ ──► │  App Python     │
│  WROOM-32   │ ◄─── armario/cmd ─── │  Mosquitto       │ ◄── │  (PC)           │
│  + MFRC522  │ ──── armario/status ►│  10.70.xx.xx:1883│     │  app_armario.py │
│  + Servo    │                      └──────────────────┘     └─────────────────┘
└─────────────┘
```

---

## 📡 Tópicos MQTT

| Tópico | Publicador | Assinante | Mensagens |
|---|---|---|---|
| `armario/req` | ESP32 | App Python | `REQ_AUTH:<UID>` \| `REQ_TOOL:<UID>` |
| `armario/cmd` | App Python | ESP32 | `CMD:OPEN:<UID>:<NOME>` \| `CMD:DENIED` \| `CMD:TOOL_OK` \| `CMD:REG_OK` |
| `armario/status` | ESP32 | App Python | `PRONTO` \| `TIMEOUT` \| `FECHADO_VOLUNTARIO` |

---

## 🛠️ Hardware

| Componente | Especificação |
|---|---|
| Microcontrolador | ESP32 WROOM-32 (DevKit V1) |
| Módulo RFID | MFRC522 Mifare 13,56 MHz |
| Servo Motor | SG90 — fios laranja / vermelho / branco |
| Tags RFID | Mifare Classic 1K |
| Rede | WiFi 802.11 b/g/n (mesma rede do PC com o broker) |

---

## 🔌 Pinagem

**MFRC522 → ESP32**

| MFRC522 | ESP32 |
|---|---|
| 3.3V | 3V3 |
| GND | GND |
| SDA / SS | GPIO 5 |
| SCK | GPIO 18 |
| MOSI | GPIO 23 |
| MISO | GPIO 19 |
| RST | GPIO 4 |

**Servo SG90 → ESP32**

| Fio | ESP32 |
|---|---|
| Laranja (sinal) | GPIO 13 |
| Vermelho (VCC) | 3V3 |
| Branco (GND) | GND |

---

## 🏷️ Tags RFID Cadastradas

| Nome | UID | Tipo |
|---|---|---|
| Lucas | `42A66C06` | Usuário |
| Gustavo | `61E30417` | Usuário |
| Multímetro | `D0C8CD3D` | Ferramenta |
| Trena | `C038CE3D` | Ferramenta |
| Martelo | `60C2CD3D` | Ferramenta |

---

## 📁 Estrutura de Arquivos

```
armario-inteligente/
├── firmware4.ino                 # Código do ESP32 (WiFi + MQTT + RFID + Servo)
├── app_armario.py                # Aplicativo Python com interface gráfica
├── usuarios.json                 # Cadastro de usuários (gerado automaticamente)
├── ferramentas.json              # Cadastro de ferramentas (gerado automaticamente)
├── status_ferramentas.json       # Estado atual de cada ferramenta (gerado automaticamente)
└── logs.txt                      # Histórico completo de operações (gerado automaticamente)
```

---

## 🚀 Instalação e Uso

### 1. Instalar o Broker MQTT — Mosquitto

**Windows:**
```
1. Baixe em: mosquitto.org/download
2. Instale e abra o Prompt de Comando como Administrador
3. Crie o arquivo mosquitto.conf com o conteúdo abaixo
4. Inicie o broker
```

**mosquitto.conf:**
```conf
listener 1883
allow_anonymous true
```

**Iniciar o broker:**
```bash
mosquitto -c mosquitto.conf -v
```

Deixe este terminal aberto enquanto usar o sistema.

---

### 2. Descobrir o IP do PC

Abra o **Prompt de Comando** e execute:
```bash
ipconfig
```
Anote o **IPv4** da rede WiFi. Exemplo: `10.70.xx.xx`

---

### 3. Configurar o IP nos dois arquivos

**firmware4.ino:**
```cpp
const char* WIFI_SSID     = "NOME_DA_REDE";
const char* WIFI_PASSWORD = "SENHA_DA_REDE";
const char* MQTT_BROKER   = "10.70.xx.xx"; // IP do seu PC
```

**app_armario.py:**
```python
MQTT_BROKER = "10.70.xx.xx"  # IP do seu PC
```

---

### 4. Instalar suporte ao ESP32 no Arduino IDE

Adicione em **File → Preferences → Additional boards manager URLs**:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

Instale as bibliotecas em **Sketch → Include Library → Manage Libraries**:

| Biblioteca | Autor |
|---|---|
| MFRC522 | GithubCommunity |
| ESP32Servo | Kevin Harrington |
| PubSubClient | Nick O'Leary |

---

### 5. Gravar o Firmware

```
1. Abra firmware4.ino no Arduino IDE
2. Tools → Board → ESP32 Arduino → ESP32 Dev Module
3. Tools → Port → COM7 (ou a porta que aparecer)
4. Clique em Upload (→)
   ⚠ Se der erro: segure o botão BOOT durante o upload e solte ao ver "Connecting..."
5. Aguarde "Done uploading"
```

---

### 6. Instalar dependência Python

```bash
pip install paho-mqtt
```

---

### 7. Rodar o App

```bash
python app_armario.py
```

Aguarde a mensagem na interface:
```
Armário Online e pronto para uso.
```

> ⚠️ O Mosquitto precisa estar rodando **antes** de ligar o ESP32 e antes de abrir o app.

---

## 🔄 Fluxo de Uso

### Retirada de Ferramenta

| Passo | Ação | Tópico | Mensagem |
|---|---|---|---|
| 1 | Usuário aproxima tag pessoal | `armario/req` | `REQ_AUTH:42A66C06` |
| 2 | Python autoriza | `armario/cmd` | `CMD:OPEN:42A66C06:Lucas` |
| 3 | Servo abre (0°) | — | — |
| 4 | Aproxima tag da ferramenta | `armario/req` | `REQ_TOOL:60C2CD3D` |
| 5 | Python registra RETIRADA | `armario/cmd` | `CMD:TOOL_OK` |
| 6 | 35s sem leitura | `armario/status` | `TIMEOUT` |
| 7 | Servo trava (90°) | — | — |

### Encerramento Voluntário

O usuário passa a própria tag novamente com a porta aberta → ESP32 publica `FECHADO_VOLUNTARIO` → servo trava imediatamente.

### Cadastro de Novo Item pelo App

1. Digite o nome no campo **"Nome para Registro"**
2. Clique em **"Cadastrar Novo Usuário"** ou **"Cadastrar Nova Ferramenta"**
3. Aproxime a tag RFID nova do módulo
4. O UID é capturado via MQTT e salvo automaticamente no JSON correspondente

---

## 📄 Exemplo de logs.txt

```
[01/07/2026 08:30:15] Acesso liberado: Lucas (UID: 42A66C06)
[01/07/2026 08:30:22] Ferramenta Martelo RETIRADA
[01/07/2026 08:31:30] Sessão encerrada por inatividade.
[01/07/2026 09:00:44] Acesso liberado: Gustavo (UID: 61E30417)
[01/07/2026 09:00:51] Ferramenta Martelo DEVOLUÇÃO
```

---

## 🔧 Troubleshooting

| Problema | Causa | Solução |
|---|---|---|
| ESP32 não conecta ao WiFi | SSID ou senha errados | Verifique `WIFI_SSID` e `WIFI_PASSWORD` no firmware |
| App não recebe mensagens | Mosquitto não está rodando | Execute `mosquitto -c mosquitto.conf -v` |
| "Falha ao conectar ao broker" | IP errado | Rode `ipconfig` e atualize o IP nos dois arquivos |
| RFID não lê tags | MOSI e MISO trocados | GPIO 23 = MOSI, GPIO 19 = MISO |
| Servo não se move | GPIO ou alimentação errada | Fio laranja → GPIO 13, vermelho → 3V3 |
| ESP32 reseta ao mover servo | Pico de corrente em 3V3 | Adicione capacitor 100µF entre 3V3 e GND próximo ao servo |

---

## ⚠️ Observações

- O ESP32 e o PC precisam estar na **mesma rede WiFi** para o MQTT funcionar.
- O broker Mosquitto precisa estar **rodando antes** de ligar o ESP32 e antes de abrir o app Python.
- O servo SG90 é alimentado pelo pino **3V3 do ESP32**. Para trancas leves funciona bem, mas o torque é reduzido em relação à tensão nominal de 5V.
- Os ângulos `SERVO_TRAVADO = 90` e `SERVO_DESTRAVADO = 0` podem ser ajustados no firmware conforme a mecânica da tranca física.