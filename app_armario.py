import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import serial
import serial.tools.list_ports
import json
import os
import threading
import time
from datetime import datetime

# Configurações da Porta Serial
BAUD_RATE = 115200

class SeletorPorta:
    """Janela de seleção de porta COM antes de abrir o app principal."""
    def __init__(self, root):
        self.root = root
        self.root.title("Selecionar Porta Serial")
        self.root.geometry("400x220")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f2f5")
        self.porta_escolhida = None

        # Centraliza a janela na tela
        self.root.eval('tk::PlaceWindow . center')

        tk.Label(root, text="ARMÁRIO INTELIGENTE RFID", bg="#1a73e8", fg="white",
                 font=("Arial", 13, "bold")).pack(fill="x", ipady=10)

        tk.Label(root, text="Selecione a porta do ESP32:", bg="#f0f2f5",
                 font=("Arial", 10, "bold")).pack(pady=(15, 5))

        frame_combo = tk.Frame(root, bg="#f0f2f5")
        frame_combo.pack(fill="x", padx=30)

        self.combo_portas = ttk.Combobox(frame_combo, state="readonly", font=("Arial", 10))
        self.combo_portas.pack(side="left", fill="x", expand=True)

        btn_atualizar = tk.Button(frame_combo, text="↻ Atualizar", bg="#1a73e8", fg="white",
                                  font=("Arial", 9, "bold"), command=self.atualizar_portas)
        btn_atualizar.pack(side="left", padx=(8, 0))

        self.lbl_aviso = tk.Label(root, text="", bg="#f0f2f5", fg="red", font=("Arial", 9))
        self.lbl_aviso.pack(pady=5)

        btn_conectar = tk.Button(root, text="Conectar e Abrir Sistema", bg="#34a853", fg="white",
                                 font=("Arial", 10, "bold"), command=self.confirmar)
        btn_conectar.pack(pady=5, padx=30, fill="x")

        self.atualizar_portas()

    def atualizar_portas(self):
        portas = serial.tools.list_ports.comports()
        opcoes = [f"{p.device} — {p.description}" for p in portas]

        if opcoes:
            self.combo_portas['values'] = opcoes
            self.combo_portas.current(0)
            self.lbl_aviso.config(text="")
        else:
            self.combo_portas['values'] = []
            self.combo_portas.set("")
            self.lbl_aviso.config(text="Nenhuma porta encontrada. Conecte o ESP32 e clique em Atualizar.")

    def confirmar(self):
        selecao = self.combo_portas.get()
        if not selecao:
            self.lbl_aviso.config(text="Selecione uma porta antes de continuar.")
            return
        # Extrai só "COM5" da string "COM5 — USB-SERIAL CH340"
        self.porta_escolhida = selecao.split(" — ")[0].strip()
        self.root.destroy()


class AppArmarioInteligente:
    def __init__(self, root, porta_com):
        self.root = root
        self.porta_com = porta_com
        self.root.title("Painel de Controle - Armário Inteligente RFID")
        self.root.geometry("750x550")
        self.root.configure(bg="#f0f2f5")

        # Variáveis de Controle de Cadastro
        self.modo_cadastro = None  # Pode ser 'usuario' ou 'ferramenta'
        self.nome_cadastro = ""
        self.usuario_atual_nome = "Nenhum"
        
        # Inicializa Arquivos de Banco de Dados Locais no PC
        self.inicializar_arquivos_pc()
        
        # Conexão Serial
        self.ser = None
        self.conectar_serial()

        # --- INSTALAÇÃO DA INTERFACE GRÁFICA (GUI) ---
        # Top Banner
        banner = tk.Frame(root, bg="#1a73e8", height=60)
        banner.pack(fill="x")
        lbl_titulo = tk.Label(banner, text="SISTEMA DE ARMÁRIO INTELIGENTE", fg="white", bg="#1a73e8", font=("Arial", 16, "bold"))
        lbl_titulo.pack(pady=15)

        # Container Principal (Esquerda: Logs / Direita: Cadastro e Status)
        main_container = tk.Frame(root, bg="#f0f2f5")
        main_container.pack(fill="both", expand=True, padx=15, pady=15)

        # LADO ESQUERDO: Terminal de Logs em tempo real
        frame_esquerdo = tk.LabelFrame(main_container, text=" Log de Eventos em Tempo Real ", font=("Arial", 10, "bold"), bg="white", bd=2)
        frame_esquerdo.place(x=0, y=0, width=420, height=440)

        self.txt_logs = scrolledtext.ScrolledText(frame_esquerdo, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.txt_logs.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_interface("Sistema Inicializado no PC. Aguardando dados do ESP32...")

        # LADO DIREITO SUPERIOR: Status Atual
        frame_status = tk.LabelFrame(main_container, text=" Estado do Armário ", font=("Arial", 10, "bold"), bg="white", bd=2)
        frame_status.place(x=435, y=0, width=270, height=110)

        self.lbl_status_porta = tk.Label(frame_status, text="PORTA: TRANCADA", fg="red", bg="white", font=("Arial", 11, "bold"))
        self.lbl_status_porta.pack(pady=5)
        self.lbl_user_ativo = tk.Label(frame_status, text="Usuário: Nenhum", fg="black", bg="white", font=("Arial", 10))
        self.lbl_user_ativo.pack(pady=5)

        # LADO DIREITO INFERIOR: Menu Interativo de Cadastros
        frame_cadastro = tk.LabelFrame(main_container, text=" Gerenciamento & Cadastro ", font=("Arial", 10, "bold"), bg="white", bd=2)
        frame_cadastro.place(x=435, y=125, width=270, height=315)

        tk.Label(frame_cadastro, text="Nome para Registro:", bg="white", font=("Arial", 9, "bold")).pack(pady=(10,0), anchor="w", padx=10)
        self.ent_nome = tk.Entry(frame_cadastro, font=("Arial", 10), bd=2, relief="groove")
        self.ent_nome.pack(fill="x", padx=10, pady=5)

        btn_cad_user = tk.Button(frame_cadastro, text="Cadastrar Novo Usuário", bg="#34a853", fg="white", font=("Arial", 9, "bold"), command=lambda: self.preparar_cadastro('usuario'))
        btn_cad_user.pack(fill="x", padx=10, pady=5)

        btn_cad_tool = tk.Button(frame_cadastro, text="Cadastrar Nova Ferramenta", bg="#fbbc05", fg="black", font=("Arial", 9, "bold"), command=lambda: self.preparar_cadastro('ferramenta'))
        btn_cad_tool.pack(fill="x", padx=10, pady=5)

        self.lbl_modo_cadastro = tk.Label(frame_cadastro, text="Modo: Operação Normal", fg="blue", bg="white", font=("Arial", 9, "italic"))
        self.lbl_modo_cadastro.pack(pady=15)

        btn_ver_banco = tk.Button(frame_cadastro, text="Ver Itens Cadastrados", bg="#757575", fg="white", font=("Arial", 9), command=self.janela_visualizar_banco)
        btn_ver_banco.pack(fill="x", padx=10, pady=5)

        # Inicia a Thread para escutar a Serial em background sem travar a tela
        self.rodando = True
        self.thread_serial = threading.Thread(target=self.escutar_serial, daemon=True)
        self.thread_serial.start()

        self.root.protocol("WM_DELETE_WINDOW", self.fechar_aplicativo)

    def inicializar_arquivos_pc(self):
        # Cria arquivos padrões caso não existam no computador
        if not os.path.exists('usuarios.json'):
            with open('usuarios.json', 'w') as f:
                json.dump({"42A66C06": "Lucas", "61E30417": "Gustavo"}, f)
        if not os.path.exists('ferramentas.json'):
            with open('ferramentas.json', 'w') as f:
                json.dump({"D0C8CD3D": "Multimetro", "C038CE3D": "Trena", "60C2CD3D": "Martelo"}, f)
        if not os.path.exists('status_ferramentas.json'):
            with open('status_ferramentas.json', 'w') as f:
                json.dump({"D0C8CD3D": False, "C038CE3D": False, "60C2CD3D": False}, f)

    def conectar_serial(self):
        try:
            # 1. Abre a porta normalmente
            self.ser = serial.Serial(self.porta_com, BAUD_RATE, timeout=1)
            
            # 2. Simula o clique físico no botão EN (Reset) via software
            self.ser.dtr = False
            self.ser.rts = True
            time.sleep(0.1)  # Mantém o "botão" pressionado por 100ms
            
            # 3. Solta o "botão" para o ESP32 iniciar o código
            self.ser.dtr = False
            self.ser.rts = False
            
            # 4. Aguarda o hardware ligar e limpa lixos de memória
            time.sleep(2)
            self.ser.reset_input_buffer()
            
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível abrir a porta {self.porta_com}.\nVerifique se o ESP32 está conectado e se o Serial Monitor da Arduino IDE está fechado!")

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
            messagebox.showwarning("Aviso", "Por favor, digite um nome antes de clicar para cadastrar!")
            return
        self.modo_cadastro = tipo
        self.nome_cadastro = nome
        self.lbl_modo_cadastro.config(text=f"APROXIME A TAG para cadastrar:\n{nome} ({tipo.upper()})", fg="orange")
        self.log_interface(f"Modo cadastro ativo: Aguardando tag para '{nome}'...")

    def escutar_serial(self):
        while self.rodando:
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        linha = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if linha:
                            self.root.after(10, self.processar_dados_esp32, linha)
                except Exception:
                    pass
            time.sleep(0.05)

    def processar_dados_esp32(self, linha):
        # 1. Trata reinicialização ou avisos do ESP32
        if linha == "STATUS:PRONTO":
            self.log_interface("Armário Online e pronto para uso.")
            self.atualizar_interface_status("TRANCADA", "Nenhum")
            return
        elif linha == "STATUS:TIMEOUT":
            self.log_interface(f"Sessão de {self.usuario_atual_nome} encerrada por inatividade (35s).")
            self.registrar_no_arquivo_log(f"Sessão de {self.usuario_atual_nome} encerrada por Timeout de 35s.")
            self.atualizar_interface_status("TRANCADA", "Nenhum")
            return
        elif linha == "STATUS:FECHADO_VOLUNTARIO":
            self.log_interface(f"Sessão encerrada voluntariamente por {self.usuario_atual_nome}.")
            self.registrar_no_arquivo_log(f"Sessão encerrada voluntariamente por {self.usuario_atual_nome}.")
            self.atualizar_interface_status("TRANCADA", "Nenhum")
            return

        # Separador do Protocolo
        if ":" not in linha:
            return
            
        prefixo, uid = linha.split(":", 1)
        uid = uid.upper()

        # 2. SE ESTIVER NO MODO CADASTRO DE TAGS
        if self.modo_cadastro is not None:
            if self.modo_cadastro == 'usuario':
                with open('usuarios.json', 'r') as f:
                    dados = json.load(f)
                # Verifica se a tag já está cadastrada
                if uid in dados:
                    nome_existente = dados[uid]
                    confirmar = messagebox.askyesno(
                        "Tag Já Cadastrada",
                        f"Esta tag já está cadastrada como '{nome_existente}'.\n\nDeseja substituir pelo nome '{self.nome_cadastro}'?"
                    )
                    if not confirmar:
                        self.log_interface(f"Cadastro cancelado. Tag {uid} mantida como '{nome_existente}'.")
                        self.modo_cadastro = None
                        self.ent_nome.delete(0, tk.END)
                        self.lbl_modo_cadastro.config(text="Modo: Operação Normal", fg="blue")
                        return
                self.ser.write(b"CMD:REG_OK\n")  # Destrava o ESP32 da espera
                with open('usuarios.json', 'r+') as f:
                    dados = json.load(f)
                    dados[uid] = self.nome_cadastro
                    f.seek(0)
                    json.dump(dados, f, indent=4)
                    f.truncate()
                self.log_interface(f"SUCESSO: Usuário '{self.nome_cadastro}' cadastrado com UID {uid}")
                self.registrar_no_arquivo_log(f"Novo usuário cadastrado via painel PC: {self.nome_cadastro} (UID: {uid})")

            elif self.modo_cadastro == 'ferramenta':
                with open('ferramentas.json', 'r') as f:
                    dados = json.load(f)
                # Verifica se a tag já está cadastrada
                if uid in dados:
                    nome_existente = dados[uid]
                    confirmar = messagebox.askyesno(
                        "Tag Já Cadastrada",
                        f"Esta tag já está cadastrada como ferramenta '{nome_existente}'.\n\nDeseja substituir pelo nome '{self.nome_cadastro}'?"
                    )
                    if not confirmar:
                        self.log_interface(f"Cadastro cancelado. Tag {uid} mantida como '{nome_existente}'.")
                        self.modo_cadastro = None
                        self.ent_nome.delete(0, tk.END)
                        self.lbl_modo_cadastro.config(text="Modo: Operação Normal", fg="blue")
                        return
                self.ser.write(b"CMD:REG_OK\n")  # Destrava o ESP32 da espera
                with open('ferramentas.json', 'r+') as f:
                    dados = json.load(f)
                    dados[uid] = self.nome_cadastro
                    f.seek(0)
                    json.dump(dados, f, indent=4)
                    f.truncate()
                with open('status_ferramentas.json', 'r+') as f:
                    status = json.load(f)
                    status[uid] = False  # Inicializa no armário
                    f.seek(0)
                    json.dump(status, f, indent=4)
                    f.truncate()
                self.log_interface(f"SUCESSO: Ferramenta '{self.nome_cadastro}' cadastrada com UID {uid}")
                self.registrar_no_arquivo_log(f"Nova ferramenta cadastrada via painel PC: {self.nome_cadastro} (UID: {uid})")
            
            # Reseta estado de cadastro
            self.modo_cadastro = None
            self.ent_nome.delete(0, tk.END)
            self.lbl_modo_cadastro.config(text="Modo: Operação Normal", fg="blue")
            return

        # 3. MODO DE OPERAÇÃO NORMAL (LOGIN E VERIFICAÇÃO DE FERRAMENTAS)
        if prefixo == "REQ_AUTH":
            with open('usuarios.json', 'r') as f:
                usuarios = json.load(f)
            
            if uid in usuarios:
                nome_usuario = usuarios[uid]
                self.log_interface(f"Acesso AUTORIZADO para: {nome_usuario}")
                self.registrar_no_arquivo_log(f"Acesso liberado para o usuário {nome_usuario} (UID: {uid})")
                self.atualizar_interface_status("ABERTA", nome_usuario)
                
                # Resposta de abertura de tranca para o ESP32
                comando = f"CMD:OPEN:{uid}:{nome_usuario}\n"
                self.ser.write(comando.encode('utf-8'))
            else:
                self.log_interface(f"Acesso NEGADO. Tag desconhecida: {uid}")
                self.registrar_no_arquivo_log(f"Tentativa de acesso negada com UID desconhecido: {uid}")
                self.ser.write(b"CMD:DENIED\n")

        elif prefixo == "REQ_TOOL":
            with open('ferramentas.json', 'r') as f:
                ferramentas = json.load(f)
            
            if uid in ferramentas:
                nome_ferramenta = ferramentas[uid]
                
                # Lê e alterna o estado da ferramenta (Retirada vs Devolvida)
                with open('status_ferramentas.json', 'r+') as f_status:
                    status_dict = json.load(f_status)
                    # Se não existir no dict de status por segurança, inicializa
                    if uid not in status_dict: status_dict[uid] = False
                    
                    novo_estado = not status_dict[uid]
                    status_dict[uid] = novo_estado
                    
                    f_status.seek(0)
                    json.dump(status_dict, f_status, indent=4)
                    f_status.truncate()
                
                acao = "RETIRADA" if novo_estado else "DEVOLUÇÃO"
                self.log_interface(f"Ferramenta [{nome_ferramenta}] -> {acao} por {self.usuario_atual_nome}")
                self.registrar_no_arquivo_log(f"Ferramenta {nome_ferramenta} sofreu {acao} pelo usuário {self.usuario_atual_nome}")
                
                # Avisa o ESP32 que a ferramenta foi computada para renovar o timer físico
                self.ser.write(b"CMD:TOOL_OK\n")
            else:
                self.log_interface(f"Aviso: Tag de ferramenta não cadastrada lida: {uid}")
                self.ser.write(b"CMD:DENIED\n")

    def atualizar_interface_status(self, estado, usuario):
        self.usuario_atual_nome = usuario
        self.lbl_user_ativo.config(text=f"Usuário: {usuario}")
        if estado == "ABERTA":
            self.lbl_status_porta.config(text="PORTA: DESTRAVADA", fg="green")
        else:
            self.lbl_status_porta.config(text="PORTA: TRANCADA", fg="red")

    def janela_visualizar_banco(self):
        # Abre uma janela secundária exibindo o banco de dados atual
        janela_banco = tk.Toplevel(self.root)
        janela_banco.title("Banco de Dados Cadastrado no PC")
        janela_banco.geometry("400x400")
        
        txt_banco = scrolledtext.ScrolledText(janela_banco, width=45, height=22)
        txt_banco.pack(padx=10, pady=10)
        
        txt_banco.insert(tk.END, "=== USUÁRIOS CADASTRADOS ===\n")
        with open('usuarios.json', 'r') as f:
            for k, v in json.load(f).items(): txt_banco.insert(tk.END, f" Tag: {k} -> {v}\n")
            
        txt_banco.insert(tk.END, "\n=== FERRAMENTAS & STATUS ===\n")
        with open('ferramentas.json', 'r') as f_f, open('status_ferramentas.json', 'r') as f_s:
            ferr = json.load(f_f)
            stat = json.load(f_s)
            for k, v in ferr.items():
                estado_atual = "FORA do armário" if stat.get(k, False) else "No armário"
                txt_banco.insert(tk.END, f" Tag: {k} -> {v} ({estado_atual})\n")
        txt_banco.config(state=tk.DISABLED)

    def fechar_aplicativo(self):
        self.rodando = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()

if __name__ == "__main__":
    # 1. Janela de seleção de porta
    root_seletor = tk.Tk()
    seletor = SeletorPorta(root_seletor)
    root_seletor.mainloop()

    # 2. Se o usuário fechou sem escolher, encerra
    if not seletor.porta_escolhida:
        exit()

    # 3. Abre o app principal com a porta escolhida
    root = tk.Tk()
    app = AppArmarioInteligente(root, seletor.porta_escolhida)
    root.mainloop()