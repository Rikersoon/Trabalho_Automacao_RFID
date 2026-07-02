import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import os
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# Configurações do MQTT
MQTT_BROKER = "seu_ipv4" # Substitua pelo IP do seu Mosquitto local se preferir
MQTT_PORT = 1883
TOPIC_REQ = "armario/req"       # ESP32 publica, PC assina (REQ_AUTH, REQ_TOOL)
TOPIC_CMD = "armario/cmd"       # PC publica, ESP32 assina (OPEN, DENIED, etc)
TOPIC_STATUS = "armario/status" # ESP32 publica, PC assina (PRONTO, TIMEOUT)

class AppArmarioInteligente:
    def __init__(self, root):
        self.root = root
        self.root.title("Painel de Controle - Armário Inteligente MQTT")
        self.root.geometry("750x550")
        self.root.configure(bg="#f0f2f5")

        self.modo_cadastro = None  
        self.nome_cadastro = ""
        self.usuario_atual_nome = "Nenhum"
        
        self.inicializar_arquivos_pc()
        self.setup_gui()
        self.setup_mqtt()

        self.root.protocol("WM_DELETE_WINDOW", self.fechar_aplicativo)

    def inicializar_arquivos_pc(self):
        if not os.path.exists('usuarios.json'):
            with open('usuarios.json', 'w') as f:
                json.dump({"42A66C06": "Lucas", "61E30417": "Gustavo"}, f)
        if not os.path.exists('ferramentas.json'):
            with open('ferramentas.json', 'w') as f:
                json.dump({"D0C8CD3D": "Multimetro", "C038CE3D": "Trena", "60C2CD3D": "Martelo"}, f)
        if not os.path.exists('status_ferramentas.json'):
            with open('status_ferramentas.json', 'w') as f:
                json.dump({"D0C8CD3D": False, "C038CE3D": False, "60C2CD3D": False}, f)

    def setup_gui(self):
        banner = tk.Frame(self.root, bg="#1a73e8", height=60)
        banner.pack(fill="x")
        lbl_titulo = tk.Label(banner, text="SISTEMA DE ARMÁRIO INTELIGENTE (MQTT)", fg="white", bg="#1a73e8", font=("Arial", 16, "bold"))
        lbl_titulo.pack(pady=15)

        main_container = tk.Frame(self.root, bg="#f0f2f5")
        main_container.pack(fill="both", expand=True, padx=15, pady=15)

        frame_esquerdo = tk.LabelFrame(main_container, text=" Log de Eventos em Tempo Real ", font=("Arial", 10, "bold"), bg="white", bd=2)
        frame_esquerdo.place(x=0, y=0, width=420, height=440)

        self.txt_logs = scrolledtext.ScrolledText(frame_esquerdo, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.txt_logs.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_interface("Iniciando cliente MQTT...")

        frame_status = tk.LabelFrame(main_container, text=" Estado do Armário ", font=("Arial", 10, "bold"), bg="white", bd=2)
        frame_status.place(x=435, y=0, width=270, height=110)

        self.lbl_status_porta = tk.Label(frame_status, text="PORTA: TRANCADA", fg="red", bg="white", font=("Arial", 11, "bold"))
        self.lbl_status_porta.pack(pady=5)
        self.lbl_user_ativo = tk.Label(frame_status, text="Usuário: Nenhum", fg="black", bg="white", font=("Arial", 10))
        self.lbl_user_ativo.pack(pady=5)

        frame_cadastro = tk.LabelFrame(main_container, text=" Gerenciamento & Cadastro ", font=("Arial", 10, "bold"), bg="white", bd=2)
        frame_cadastro.place(x=435, y=125, width=270, height=315)

        tk.Label(frame_cadastro, text="Nome para Registro:", bg="white", font=("Arial", 9, "bold")).pack(pady=(10,0), anchor="w", padx=10)
        self.ent_nome = tk.Entry(frame_cadastro, font=("Arial", 10), bd=2, relief="groove")
        self.ent_nome.pack(fill="x", padx=10, pady=5)

        tk.Button(frame_cadastro, text="Cadastrar Novo Usuário", bg="#34a853", fg="white", font=("Arial", 9, "bold"), command=lambda: self.preparar_cadastro('usuario')).pack(fill="x", padx=10, pady=5)
        tk.Button(frame_cadastro, text="Cadastrar Nova Ferramenta", bg="#fbbc05", fg="black", font=("Arial", 9, "bold"), command=lambda: self.preparar_cadastro('ferramenta')).pack(fill="x", padx=10, pady=5)

        self.lbl_modo_cadastro = tk.Label(frame_cadastro, text="Modo: Operação Normal", fg="blue", bg="white", font=("Arial", 9, "italic"))
        self.lbl_modo_cadastro.pack(pady=15)

        tk.Button(frame_cadastro, text="Ver Itens Cadastrados", bg="#757575", fg="white", font=("Arial", 9), command=self.janela_visualizar_banco).pack(fill="x", padx=10, pady=5)

    def setup_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start() # Roda o MQTT em background
        except Exception as e:
            messagebox.showerror("Erro MQTT", f"Falha ao conectar ao broker {MQTT_BROKER}: {e}")

    def on_connect(self, client, userdata, flags, rc):
        self.log_interface(f"Conectado ao Broker MQTT. Assinando tópicos...")
        self.client.subscribe(TOPIC_REQ)
        self.client.subscribe(TOPIC_STATUS)

    def on_message(self, client, userdata, msg):
        linha = msg.payload.decode('utf-8')
        topico = msg.topic
        
        # Como callbacks rodam em threads separadas, usamos self.root.after para atualizar a interface
        self.root.after(10, self.processar_dados, topico, linha)

    def log_interface(self, mensagem):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.insert(tk.END, f"[{timestamp}] {mensagem}\n")
        self.txt_logs.see(tk.END)

    def registrar_no_arquivo_log(self, texto):
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(f"[{data_hora}] {texto}\n")

    def preparar_cadastro(self, tipo):
        nome = self.ent_nome.get().strip()
        if not nome:
            messagebox.showwarning("Aviso", "Digite um nome para cadastrar!")
            return
        self.modo_cadastro = tipo
        self.nome_cadastro = nome
        self.lbl_modo_cadastro.config(text=f"APROXIME A TAG:\n{nome} ({tipo.upper()})", fg="orange")
        self.log_interface(f"Modo cadastro: Aguardando tag para '{nome}'...")

    def processar_dados(self, topico, linha):
        if topico == TOPIC_STATUS:
            if linha == "PRONTO":
                self.log_interface("Armário Online e pronto para uso.")
                self.atualizar_interface_status("TRANCADA", "Nenhum")
            elif linha == "TIMEOUT":
                self.log_interface(f"Sessão encerrada por inatividade.")
                self.atualizar_interface_status("TRANCADA", "Nenhum")
            elif linha == "FECHADO_VOLUNTARIO":
                self.log_interface(f"Sessão encerrada voluntariamente.")
                self.atualizar_interface_status("TRANCADA", "Nenhum")
            return

        if topico == TOPIC_REQ and ":" in linha:
            prefixo, uid = linha.split(":", 1)
            uid = uid.upper()

            if self.modo_cadastro is not None:
                self.processar_cadastro(uid)
                return

            if prefixo == "REQ_AUTH":
                self.processar_autenticacao(uid)
            elif prefixo == "REQ_TOOL":
                self.processar_ferramenta(uid)

    def processar_cadastro(self, uid):
        arquivo = 'usuarios.json' if self.modo_cadastro == 'usuario' else 'ferramentas.json'
        
        with open(arquivo, 'r') as f:
            dados = json.load(f)
            
        self.client.publish(TOPIC_CMD, "CMD:REG_OK")
        
        with open(arquivo, 'r+') as f:
            dados[uid] = self.nome_cadastro
            f.seek(0)
            json.dump(dados, f, indent=4)
            f.truncate()
            
        if self.modo_cadastro == 'ferramenta':
            with open('status_ferramentas.json', 'r+') as f:
                status = json.load(f)
                status[uid] = False 
                f.seek(0)
                json.dump(status, f, indent=4)
                f.truncate()
                
        self.log_interface(f"SUCESSO: '{self.nome_cadastro}' cadastrado (UID: {uid})")
        
        self.modo_cadastro = None
        self.ent_nome.delete(0, tk.END)
        self.lbl_modo_cadastro.config(text="Modo: Operação Normal", fg="blue")

    def processar_autenticacao(self, uid):
        with open('usuarios.json', 'r') as f:
            usuarios = json.load(f)
        
        if uid in usuarios:
            nome = usuarios[uid]
            self.log_interface(f"Acesso AUTORIZADO: {nome}")
            self.registrar_no_arquivo_log(f"Acesso liberado: {nome} (UID: {uid})")
            self.atualizar_interface_status("ABERTA", nome)
            self.client.publish(TOPIC_CMD, f"CMD:OPEN:{uid}:{nome}")
        else:
            self.log_interface(f"Acesso NEGADO: {uid}")
            self.client.publish(TOPIC_CMD, "CMD:DENIED")

    def processar_ferramenta(self, uid):
        with open('ferramentas.json', 'r') as f:
            ferramentas = json.load(f)
        
        if uid in ferramentas:
            nome = ferramentas[uid]
            with open('status_ferramentas.json', 'r+') as f_status:
                status_dict = json.load(f_status)
                if uid not in status_dict: status_dict[uid] = False
                
                novo_estado = not status_dict[uid]
                status_dict[uid] = novo_estado
                
                f_status.seek(0)
                json.dump(status_dict, f_status, indent=4)
                f_status.truncate()
            
            acao = "RETIRADA" if novo_estado else "DEVOLUÇÃO"
            self.log_interface(f"Ferramenta [{nome}] -> {acao}")
            self.registrar_no_arquivo_log(f"Ferramenta {nome} {acao}")
            self.client.publish(TOPIC_CMD, "CMD:TOOL_OK")
        else:
            self.log_interface(f"Aviso: Ferramenta não cadastrada: {uid}")
            self.client.publish(TOPIC_CMD, "CMD:DENIED")

    def atualizar_interface_status(self, estado, usuario):
        self.usuario_atual_nome = usuario
        self.lbl_user_ativo.config(text=f"Usuário: {usuario}")
        if estado == "ABERTA":
            self.lbl_status_porta.config(text="PORTA: DESTRAVADA", fg="green")
        else:
            self.lbl_status_porta.config(text="PORTA: TRANCADA", fg="red")

    def janela_visualizar_banco(self):
        janela_banco = tk.Toplevel(self.root)
        janela_banco.title("Banco de Dados Atual")
        janela_banco.geometry("400x400")
        
        txt_banco = scrolledtext.ScrolledText(janela_banco, width=45, height=22)
        txt_banco.pack(padx=10, pady=10)
        
        txt_banco.insert(tk.END, "=== USUÁRIOS ===\n")
        with open('usuarios.json', 'r') as f:
            for k, v in json.load(f).items(): txt_banco.insert(tk.END, f" {k} -> {v}\n")
            
        txt_banco.insert(tk.END, "\n=== FERRAMENTAS ===\n")
        with open('ferramentas.json', 'r') as f_f, open('status_ferramentas.json', 'r') as f_s:
            ferr = json.load(f_f)
            stat = json.load(f_s)
            for k, v in ferr.items():
                estado = "FORA" if stat.get(k, False) else "No armário"
                txt_banco.insert(tk.END, f" {k} -> {v} ({estado})\n")
        txt_banco.config(state=tk.DISABLED)

    def fechar_aplicativo(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AppArmarioInteligente(root)
    root.mainloop()