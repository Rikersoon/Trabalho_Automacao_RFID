#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>

#define RFID_SS_PIN   5
#define RFID_RST_PIN  4
#define SERVO_PIN     13
#define SERVO_TRAVADO   90
#define SERVO_DESTRAVADO 0
#define TIMEOUT_SESSAO_MS   35000UL // 35 segundos sem atividade
#define DELAY_ANTIDUPLA_MS   3000UL // 3 segundos para a mesma tag

MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
Servo   servoTranca;

enum Estado { AGUARDANDO_USUARIO, PORTA_ABERTA };
Estado estadoAtual = AGUARDANDO_USUARIO;

String   sessaoUsuarioUID  = "";
String   sessaoUsuarioNome = "";
uint32_t tempoUltimaAtiv   = 0;
String   ultimaTagLida     = "";
uint32_t ultimaTagTempo    = 0;

void setup() {
  Serial.begin(115200);
  delay(500);
  
  SPI.begin();
  rfid.PCD_Init();
  
  servoTranca.attach(SERVO_PIN);
  trancarPorta();
  
  // Avisa o programa do PC que o ESP32 reiniciou e está pronto
  Serial.println("STATUS:PRONTO");
}

void loop() {
  // Verifica se chegou algum comando vindo do PC via USB
  verificarComandosPC();

  switch (estadoAtual) {
    case AGUARDANDO_USUARIO: {
      String uid = lerRFID();
      if (uid.isEmpty()) break;
      
      // Envia uma requisição de autenticação para o PC
      Serial.println("REQ_AUTH:" + uid);
      delay(1000); // Aguarda o processamento e evita reenvio imediato
      break;
    }
    
    case PORTA_ABERTA: {
      uint32_t inativo = millis() - tempoUltimaAtiv;
      if (inativo >= TIMEOUT_SESSAO_MS) {
        Serial.println("STATUS:TIMEOUT");
        encerrarSessaoLocal();
        break;
      }
      
      String uid = lerRFID();
      if (uid.isEmpty()) break;
      
      // Se o usuário logado passar a própria tag de novo, fecha o armário
      if (uid.equalsIgnoreCase(sessaoUsuarioUID)) {
        Serial.println("STATUS:FECHADO_VOLUNTARIO");
        encerrarSessaoLocal();
        delay(1000);
        break;
      }
      
      // Filtro anti-dupla leitura para ferramentas
      if (uid.equalsIgnoreCase(ultimaTagLida) &&
          (millis() - ultimaTagTempo) < DELAY_ANTIDUPLA_MS) break;
          
      // Envia o ID da ferramenta lida para o PC processar
      Serial.println("REQ_TOOL:" + uid);
      
      ultimaTagLida   = uid;
      ultimaTagTempo  = millis();
      tempoUltimaAtiv = millis(); // Renova o timeout por ter tido atividade
      break;
    }
  }
  delay(50);
}

void verificarComandosPC() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    // Comando enviado pelo PC quando o acesso é permitido
    // Formato esperado: CMD:OPEN:UID_DO_CARA:NOME_DO_CARA
    if (cmd.startsWith("CMD:OPEN:")) {
      int segundoDoisPontos = cmd.indexOf(':', 9);
      sessaoUsuarioUID = cmd.substring(9, segundoDoisPontos);
      sessaoUsuarioNome = cmd.substring(segundoDoisPontos + 1);
      
      destrancarPorta();
      tempoUltimaAtiv = millis();
      estadoAtual = PORTA_ABERTA;
    }
    // Comando enviado pelo PC se a tag não for cadastrada ou se o PC estiver em modo cadastro
    else if (cmd.equals("CMD:DENIED") || cmd.equals("CMD:REG_OK")) {
      // Apenas reseta variáveis locais se necessário, continua aguardando
      ultimaTagLida = ""; 
    }
    // Comando enviado pelo PC confirmando o registro da ferramenta para atualizar o timer
    else if (cmd.startsWith("CMD:TOOL_OK")) {
      tempoUltimaAtiv = millis();
    }
  }
}

void encerrarSessaoLocal() {
  trancarPorta();
  sessaoUsuarioUID  = "";
  sessaoUsuarioNome = "";
  ultimaTagLida     = "";
  ultimaTagTempo    = 0;
  estadoAtual       = AGUARDANDO_USUARIO;
}

void destrancarPorta() {
  servoTranca.write(SERVO_DESTRAVADO);
  delay(600);
}

void trancarPorta() {
  servoTranca.write(SERVO_TRAVADO);
  delay(600);
}

String lerRFID() {
  if (!rfid.PICC_IsNewCardPresent()) return "";
  if (!rfid.PICC_ReadCardSerial())   return "";
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  return uid;
}