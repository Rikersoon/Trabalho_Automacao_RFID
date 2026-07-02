# 🔧 Armário Inteligente de Ferramentas

Sistema de controle de retirada e devolução de ferramentas com ESP32, RFID e servo motor.  
Desenvolvido por **Henrique** **Lucas** e **Gustavo**.

---

## 📋 Sobre o Projeto

Uma pessoa se identifica com uma tag RFID pessoal, o servo motor abre a tranca do armário, as ferramentas são lidas por etiquetas RFID individuais e tudo é registrado em tempo real no PC via cabo USB. Após 35 segundos sem atividade, o armário trava automaticamente.

---

## 🛠️ Hardware

| Componente | Especificação |
|---|---|
| Microcontrolador | ESP32 WROOM-32 (DevKit V1) |
| Módulo RFID | MFRC522 Mifare 13,56 MHz |
| Servo Motor | SG90 — fios laranja / vermelho / Marrom |
| Tags RFID | Mifare Classic 1K |
| Conexão PC | Cabo USB (também alimenta o ESP32) |

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
| Alicate | `D0C8CD3D` | Ferramenta |
| Trena | `C038CE3D` | Ferramenta |
| Martelo | `60C2CD3D` | Ferramenta |

---

## 📁 Estrutura de Arquivos

```
armario-inteligente/
├── firmware_armario_final.ino    # Código do ESP32
├── app_armario_final.py          # Aplicativo Python (PC)
├── usuarios.json                 # Cadastro de usuários (gerado automaticamente)
├── ferramentas.json              # Cadastro de ferramentas (gerado automaticamente)
├── status_ferramentas.json       # Estado atual de cada ferramenta (gerado automaticamente)
└── logs.txt                      # Histórico completo de operações (gerado automaticamente)
```

---

## ⚙️ Como Funciona

### Protocolo Serial (ESP32 ↔ PC via USB a 115200 baud)

**ESP32 → PC**
```
STATUS:PRONTO        → ESP32 inicializou e está pronto
STATUS:TIMEOUT       → Sessão encerrada por inatividade
STATUS:FECHADO_VOL   → Usuário fechou passando a própria tag
REQ_AUTH:<UID>       → Pede autenticação de usuário
REQ_TOOL:<UID>       → Pede registro de ferramenta
```

**PC → ESP32**
```
CMD:OPEN:<UID>:<NOME> → Acesso autorizado, abre a tranca
CMD:DENIED            → Acesso negado
CMD:TOOL_OK           → Ferramenta registrada, renova o timer
CMD:REG_OK            → Cadastro aceito
```

### Fluxo de Retirada
1. Usuário aproxima a tag pessoal → ESP32 envia `REQ_AUTH`
2. Python verifica `usuarios.json` → responde `CMD:OPEN`
3. Servo gira para 0° (destravado)
4. Usuário aproxima a tag da ferramenta → ESP32 envia `REQ_TOOL`
5. Python registra **RETIRADA** em `logs.txt` → responde `CMD:TOOL_OK`
6. Após 35s sem leitura → `STATUS:TIMEOUT` → servo trava (90°)

### Fluxo de Devolução
1. Usuário se identifica → servo abre
2. Aproxima a tag da ferramenta → Python alterna status → registra **DEVOLUÇÃO**
3. Usuário passa a própria tag novamente → `STATUS:FECHADO_VOL` → servo trava

---

## 🚀 Instalação e Uso

### 1. Pré-requisitos

- [Arduino IDE 2.x](https://www.arduino.cc/en/software)
- Python 3.x
- Suporte ESP32 instalado no Arduino IDE

### 2. Configurar o Arduino IDE

Adicione em **File → Preferences → Additional boards manager URLs**:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

Instale as bibliotecas em **Sketch → Include Library → Manage Libraries**:
- `MFRC522` — GithubCommunity
- `ESP32Servo` — Kevin Harrington
- `ArduinoJson` — Benoit Blanchon (v6.x)

### 3. Gravar o Firmware

```
1. Abra firmware_armario_final.ino no Arduino IDE
2. Tools → Board → ESP32 Arduino → ESP32 Dev Module
3. Tools → Port → COM7 (ou a porta que aparecer)
4. Clique em Upload (→)
   ⚠ Se der erro: segure o botão BOOT durante o upload e solte ao ver "Connecting..."
5. Aguarde "Done uploading"
```

### 4. Instalar dependência Python

```bash
pip install pyserial
```

### 5. Rodar o App

```bash
python app_armario_final.py
```

> ⚠️ **Importante:** feche o Serial Monitor do Arduino IDE antes de rodar o app.

1. Selecione a porta **COM7** na janela de conexão
2. Clique em **Conectar e Abrir Sistema**
3. Aguarde a mensagem `ESP32 online e pronto para uso`

---

## 📂 Cadastro de Novos Itens

Pelo app Python:
1. Digite o nome no campo **"Nome para Registro"**
2. Clique em **"Cadastrar Novo Usuário"** ou **"Cadastrar Nova Ferramenta"**
3. Aproxime a tag RFID nova do módulo
4. O UID é capturado e salvo automaticamente no JSON correspondente

---

## 📄 Exemplo de logs.txt

```
[01/07/2026 08:30:15] Acesso liberado — Lucas (UID: 42A66C06)
[01/07/2026 08:30:22] RETIRADA — Ferramenta: Martelo | Usuário: Lucas | UID: 60C2CD3D
[01/07/2026 08:31:30] Sessão de Lucas encerrada por timeout.
[01/07/2026 09:00:44] Acesso liberado — Gustavo (UID: 61E30417)
[01/07/2026 09:00:51] DEVOLUÇÃO — Ferramenta: Martelo | Usuário: Gustavo | UID: 60C2CD3D
```

---

## ⚠️ Observações

- O servo SG90 é alimentado pelo pino **3V3 do ESP32**.
- Os ângulos `SERVO_TRAVADO = 90` e `SERVO_DESTRAVADO = 0` podem ser ajustados no firmware conforme a mecânica da tranca.
- O sistema funciona **100% offline** — não requer WiFi ou servidor. A comunicação é feita pelo cabo USB entre o ESP32 e o PC.
