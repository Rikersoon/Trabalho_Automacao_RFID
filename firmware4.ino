#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>

// Configurações de Rede e MQTT
const char* WIFI_SSID = "nome_da_rede"; // Coloque o nome da sua rede Wi-Fi
const char* WIFI_PASSWORD = "sua_senha"; // Coloque a senha da sua rede Wi-Fi
const char* MQTT_BROKER = "IPv4_endereço"; // Mesmo IP colocado no Python
const int MQTT_PORT = 1883;

// Tópicos MQTT
const char* TOPIC_REQ = "armario/req";
const char* TOPIC_CMD = "armario/cmd";
const char* TOPIC_STATUS = "armario/status";

// Pinos
#define RFID_SS_PIN   5
#define RFID_RST_PIN  4
#define SERVO_PIN     13
#define SERVO_TRAVADO   90
#define SERVO_DESTRAVADO 0
#define TIMEOUT_SESSAO_MS   35000UL
#define DELAY_ANTIDUPLA_MS   3000UL

MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
Servo servoTranca;
WiFiClient espClient;
PubSubClient mqttClient(espClient);

enum Estado { AGUARDANDO_USUARIO, PORTA_ABERTA };
Estado estadoAtual = AGUARDANDO_USUARIO;

String sessaoUsuarioUID = "";
String sessaoUsuarioNome = "";
uint32_t tempoUltimaAtiv = 0;

String ultimaTagLida = "";
uint32_t ultimaTagTempo = 0;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando ao WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Conectado!");
}

// Callback de recebimento de mensagens MQTT
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String cmd = "";
  for (unsigned int i = 0; i < length; i++) {
    cmd += (char)payload[i];
  }
  
  if (cmd.startsWith("CMD:OPEN:")) {
    int segundoDoisPontos = cmd.indexOf(':', 9);
    sessaoUsuarioUID = cmd.substring(9, segundoDoisPontos);
    sessaoUsuarioNome = cmd.substring(segundoDoisPontos + 1);
    
    destrancarPorta();
    tempoUltimaAtiv = millis();
    estadoAtual = PORTA_ABERTA;
  }
  else if (cmd.equals("CMD:DENIED") || cmd.equals("CMD:REG_OK")) {
    ultimaTagLida = "";
  }
  else if (cmd.startsWith("CMD:TOOL_OK")) {
    tempoUltimaAtiv = millis();
  }
}

void reconnect() {
  while (!mqttClient.connected()) {
    Serial.print("Tentando conexao MQTT...");
    if (mqttClient.connect("ESP32ArmarioClient")) {
      Serial.println("Conectado ao Broker!");
      mqttClient.subscribe(TOPIC_CMD);
      mqttClient.publish(TOPIC_STATUS, "PRONTO"); // Avisa o PC
    } else {
      Serial.print("Falhou, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" tentando novamente em 5 segundos");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  setup_wifi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  SPI.begin();
  rfid.PCD_Init();
  
  servoTranca.attach(SERVO_PIN);
  trancarPorta();
}

void loop() {
  if (!mqttClient.connected()) {
    reconnect();
  }
  mqttClient.loop();

  switch (estadoAtual) {
    case AGUARDANDO_USUARIO: {
      String uid = lerRFID();
      if (uid.isEmpty()) break;
      
      String req = "REQ_AUTH:" + uid;
      mqttClient.publish(TOPIC_REQ, req.c_str());
      delay(1000);
      break;
    }
    
    case PORTA_ABERTA: {
      uint32_t inativo = millis() - tempoUltimaAtiv;
      if (inativo >= TIMEOUT_SESSAO_MS) {
        mqttClient.publish(TOPIC_STATUS, "TIMEOUT");
        encerrarSessaoLocal();
        break;
      }
      
      String uid = lerRFID();
      if (uid.isEmpty()) break;
      
      if (uid.equalsIgnoreCase(sessaoUsuarioUID)) {
        mqttClient.publish(TOPIC_STATUS, "FECHADO_VOLUNTARIO");
        encerrarSessaoLocal();
        delay(1000);
        break;
      }
      
      if (uid.equalsIgnoreCase(ultimaTagLida) && (millis() - ultimaTagTempo) < DELAY_ANTIDUPLA_MS) break;
      
      String req = "REQ_TOOL:" + uid;
      mqttClient.publish(TOPIC_REQ, req.c_str());
      
      ultimaTagLida = uid;
      ultimaTagTempo = millis();
      tempoUltimaAtiv = millis();
      break;
    }
  }
  delay(50);
}

void encerrarSessaoLocal() {
  trancarPorta();
  sessaoUsuarioUID = "";
  sessaoUsuarioNome = "";
  ultimaTagLida = "";
  ultimaTagTempo = 0;
  estadoAtual = AGUARDANDO_USUARIO;
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
  if (!rfid.PICC_ReadCardSerial()) return "";
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