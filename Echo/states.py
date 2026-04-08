from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import json
import asyncio
import reflex as rx
import icmplib
import pydantic
import smtplib

# Criação do arquivo config.env se não existir
if not os.path.exists("Echo/config.env"):
    print("Arquivo config.env nao encontrado. Criando arquivo de exemplo...")
    with open("Echo/config.env", "w", encoding="utf-8") as f:
        f.write("# Configurações de email\nSMTP_SERVER=mail.seudominio.com.br\nSMTP_PORT=465\nSMTP_LOGIN=alertas@seudominio.com.br\nSMTP_PASSWORD=suasenha\n# Configurações de monitoramento\nINTERVALO_SEGUNDOS=10\nLIMITE_LATENCIA_MS=100\nPINGS_MAXIMOS=12\nFREQUENCIA_EMAILS=60")

# Carregando arquivo de acesso do email
load_dotenv("Echo/config.env")

class AtivoRede(pydantic.BaseModel):
    nome: str
    ip: str
    local: str
    latencia: float = 0.0
    latencia_total: float = 0.0
    qnt_pings: int = 0
    status: str = "Aguardando..."
    historico: list[dict[str, str | float]] = []

def disparar_email(ativos, destinatarios):
    # Travas de segurança: não tenta enviar se faltar dados
    if not destinatarios:
        print("Operação cancelada: Nenhum e-mail cadastrado na lista de envio.")
        return
    if not ativos:
        print("Operação cancelada: Nenhum ativo de rede cadastrado para gerar o relatório.")
        return

    # Puxa as configurações do .env (já carregadas no topo do seu código)
    servidor = os.environ.get("SMTP_SERVER")
    porta = int(os.environ.get("SMTP_PORT", 465))
    login = os.environ.get("SMTP_LOGIN")
    senha = os.environ.get("SMTP_PASSWORD")

    print("Montando relatório de ativos em HTML...")
    
    # 1. Constrói as linhas da tabela dinamicamente com base nos ativos
    linhas_tabela = ""
    for ativo in ativos:
        # Define a cor do texto dependendo do status atual
        cor_status = "green" if ativo.status == "Online" else "orange" if ativo.status == "Lento" else "red"
        
        linhas_tabela += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;"><b>{ativo.nome}</b></td>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">{ativo.ip}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">{ativo.local}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; color: {cor_status}; font-weight: bold;">{ativo.status}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">{ativo.latencia_total/ativo.qnt_pings if ativo.qnt_pings > 0 else 0:.0f} ms</td>
        </tr>
        """

    # 2. Constrói a casca do e-mail com a tabela dentro
    corpo_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <h2 style="color: #0056b3;">Echo - Relatório de Latencia</h2>
            <p>Segue teste de latencia média de ativos:</p>
            
            <table style="border-collapse: collapse; width: 100%; max-width: 800px; text-align: left; margin-top: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <tr style="background-color: #f4f6f8;">
                    <th style="padding: 12px; border-bottom: 2px solid #ccc;">Nome do Equipamento</th>
                    <th style="padding: 12px; border-bottom: 2px solid #ccc;">Endereço IP</th>
                    <th style="padding: 12px; border-bottom: 2px solid #ccc;">Localização</th>
                    <th style="padding: 12px; border-bottom: 2px solid #ccc;">Status Atual</th>
                    <th style="padding: 12px; border-bottom: 2px solid #ccc;">Latência (Média)</th>
                </tr>
                {linhas_tabela}
            </table>
            
            <p style="margin-top: 30px; font-size: 12px; color: #777;">
                Mensagem gerada automaticamente pelo painel de monitoramento Echo.
            </p>
        </body>
    </html>
    """

    # 3. Configura os cabeçalhos do e-mail
    msg = MIMEMultipart()
    msg['Subject'] = "Echo: Status Atual da Rede (Teste de Latência)"
    msg['From'] = login
    msg['To'] = ", ".join(destinatarios)
    msg.attach(MIMEText(corpo_html, 'html'))

    # 4. Conecta no servidor e faz o disparo
    try:
        print(f"Conectando ao servidor SMTP {servidor} via SSL...")
        server = smtplib.SMTP_SSL(servidor, porta)
        server.login(login, senha)
        server.sendmail(login, destinatarios, msg.as_string())
        server.quit()
        
        print("E-mail de teste enviado e entregue com sucesso!")
    except Exception as e:
        print(f"Falha crítica ao enviar o e-mail: {e}")

def carregar_ativos():
    if os.path.exists('Echo/ips.json'):
        print("Carregando ativos de ips.json...")

        with open('Echo/ips.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
            return [AtivoRede(nome=item['nome'], ip=item['ip'], local=item['local']) for item in dados]
    else:
        print("Arquivo ips.json não encontrado. Criando arquivo de exemplo...")

        os.makedirs('Echo', exist_ok=True)

        with open('Echo/ips.json', 'w', encoding='utf-8') as f:
            exemplo = [{"nome": "Google", "ip": "8.8.8.8", "local": "N/A"},{"nome": "Cloudflare", "ip": "1.1.1.1", "local": "N/A"}]
            json.dump(exemplo, f)

        return [AtivoRede(nome=item['nome'], ip=item['ip'], local=item['local']) for item in exemplo]

def carregar_emails():
    if os.path.exists('Echo/emails.json'):
        print("Carregando emails de emails.json...")
        with open('Echo/emails.json', 'r', encoding='utf-8') as f:
            return json.load(f) 
    else:
        print("Arquivo emails.json não encontrado. Criando arquivo de exemplo...")
        os.makedirs('Echo', exist_ok=True)
        exemplo = ["exemplo@dominio.com"]
        with open('Echo/emails.json', 'w', encoding='utf-8') as f:
            json.dump(exemplo, f)
        return exemplo

# 1. ESTADO BASE
class AppState(rx.State):
    """Estado principal do qual todos os outros herdam."""

    ativos: list[AtivoRede] = carregar_ativos() # Função externa
    ativos_buffer: list[dict[str, str]] = []
    
    monitorando: bool = False
    loop_relatorio_ativo: bool = False
    ciclo_atual: int = 0

    novo_ativo_nome: str = ""
    novo_ativo_ip: str = ""
    novo_ativo_local: str = ""

    # --- Dicionários de Configuração ---
    config: dict[str, str | int]  = {
        "smtp_server": os.environ.get("SMTP_SERVER", ""), 
        "smtp_port": int(os.environ.get("SMTP_PORT", 465)),
        "smtp_login": os.environ.get("SMTP_LOGIN", ""), 
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "intervalo_segundos": int(os.environ.get("INTERVALO_SEGUNDOS", 10)),
        "limite_latencia_ms": int(os.environ.get("LIMITE_LATENCIA_MS", 100)),
        "pings_maximos": int(os.environ.get("PINGS_MAXIMOS", 12)),
        "frequencia_emails": int(os.environ.get("FREQUENCIA_EMAILS", 60))
    }
    config_buffer: dict[str, str | int] = config.copy()

    # --- E-mails ---
    emails: list[str] = carregar_emails() # Função externa
    novo_email_input: str = ""
    
    @rx.event
    def set_novo_attr(self, atributo: str, valor: str):
        """Setter universal disponível para todas as classes filhas."""
        setattr(self, atributo, valor)

# 2. ESTADO DE CONFIGURAÇÕES
class ConfigState(AppState):
    """Gerencia exclusivamente as variáveis de ambiente e e-mails."""

    @rx.event
    def atualizar_buffer(self, chave: str, valor: str):
        chaves_numericas = ["smtp_port", "intervalo_segundos", "limite_latencia_ms", "pings_maximos", "frequencia_emails"]
        if chave in chaves_numericas:
            self.config_buffer[chave] = int(valor) if valor.isdigit() else self.config[chave]
        else:
            self.config_buffer[chave] = valor

    @rx.event
    def salvar_configuracoes(self):
        self.config = self.config_buffer.copy()
        
        # Atualiza a memória e salva no disco
        chaves = ["smtp_server", "smtp_port", "smtp_login", "smtp_password", 
                  "intervalo_segundos", "limite_latencia_ms", "pings_maximos", "frequencia_emails"]
                  
        for chave in chaves:
            os.environ[chave.upper()] = str(self.config[chave])

        conteudo_env = "\n".join([f"{k.upper()}={self.config[k]}" for k in chaves]) + "\n"
        with open("Echo/config.env", "w", encoding="utf-8") as f:
            f.write(conteudo_env)
            
    @rx.event
    def adicionar_email(self):
        if self.novo_email_input and self.novo_email_input not in self.emails:
            self.emails.append(self.novo_email_input)
            self.novo_email_input = ""
            self.salvar_emails()

    @rx.event
    def remover_email(self, email_alvo: str):
        if email_alvo in self.emails:
            self.emails.remove(email_alvo)
            self.salvar_emails()

    def salvar_emails(self):
        with open('Echo/emails.json', 'w', encoding='utf-8') as f:
            json.dump(self.emails, f)


# 3. ESTADO DE MONITORAMENTO
class MonitoramentoState(AppState):
    """Gerencia exclusivamente os pings, ativos e relatórios."""

    def on_load(self):
        """Inicializa o buffer com os ativos existentes"""
        self.ativos_buffer = [{"nome": a.nome, "ip": a.ip, "local": a.local} for a in self.ativos]

    @rx.event
    def reiniciar_sistema_local(self):
        """Reseta o monitoramento e o timer de e-mail sem recarregar a página"""
        
        # 1. Mata os loops atuais
        self.monitorando = False
        self.loop_relatorio_ativo = False
        self.ciclo_atual += 1 # Isso faz os 'while' pararem no próximo check
        
        # 3. Limpa o visual dos ativos para o estado inicial
        # Usamos uma compreensão de lista para resetar o status de todos
        self.ativos = [
            a.model_copy(update={
                "status": "Aguardando...",
                "latencia": 0.0,
                "historico": []
            }) for a in self.ativos
        ]
        
        print("🔄 Estados reiniciados com sucesso!")

    @rx.event
    def adicionar_ativo_buffer(self):
        if self.novo_ativo_nome and self.novo_ativo_ip and self.novo_ativo_local:
            self.ativos_buffer.append({
                "nome": self.novo_ativo_nome.strip(),
                "ip": self.novo_ativo_ip.strip(),
                "local": self.novo_ativo_local.strip()
            })
            self.novo_ativo_nome = ""
            self.novo_ativo_ip = ""
            self.novo_ativo_local = ""
            
    @rx.event
    def remover_ativo_buffer(self, ip_alvo: str):
        self.ativos_buffer = [a for a in self.ativos_buffer if a["ip"] != ip_alvo]
        
    @rx.event
    def salvar_ativos(self):
        with open('Echo/ips.json', 'w', encoding='utf-8') as f:
            json.dump(self.ativos_buffer, f)
            
        novos_ativos = []
        for item in self.ativos_buffer:
            novos_ativos.append(AtivoRede(
                nome=item['nome'], ip=item['ip'], local=item['local'], status="Aguardando...",
                latencia=0.0, latencia_total=0.0, qnt_pings=0, historico=[]
            ))
        self.ativos = novos_ativos

    @rx.event
    def parar_monitoramento(self):
        self.monitorando = False
        self.ciclo_atual += 1
        
        # Reseta e corrige a adição dos atributos obrigatórios do Pydantic
        ativos_resetados = [AtivoRede(
            nome=a.nome, ip=a.ip, local=a.local, status="Aguardando...", 
            latencia=0.0, latencia_total=0.0, qnt_pings=0, historico=[]
        ) for a in self.ativos]
        self.ativos = ativos_resetados

    @rx.event(background=True)
    async def loop_monitoramento(self):
        async with self:
            if self.monitorando: return
            self.monitorando = True
            self.ciclo_atual += 1
            meu_ciclo = self.ciclo_atual 
        
        while True:
            async with self:
                if not self.monitorando or self.ciclo_atual != meu_ciclo: break
                ativos_atuais = self.ativos.copy()
                
                # COMUNICAÇÃO ENTRE ESTADOS: Busca as configs do ConfigState
                estado_config = await self.get_state(ConfigState)
                limite_ms = estado_config.config["limite_latencia_ms"]
                max_pings = estado_config.config["pings_maximos"]
                intervalo = estado_config.config["intervalo_segundos"]
            
            ativos_atualizados = []
            hora_atual = datetime.now().strftime("%H:%M:%S")
            
            # Pings acontecem fora do 'async with self' para não travar a interface
            for ativo in ativos_atuais:
                resultado = await icmplib.async_ping(ativo.ip, count=1, timeout=2)
                latencia_ms = resultado.avg_rtt
                
                if not resultado.is_alive:
                    novo_status, nova_latencia = "Offline", 0.0
                elif latencia_ms > limite_ms:
                    novo_status, nova_latencia = "Lento", latencia_ms
                else:
                    novo_status, nova_latencia = "Online", latencia_ms
                
                novo_historico = ativo.historico.copy()
                novo_historico.append({"hora": hora_atual, "latencia": nova_latencia})
                
                if len(novo_historico) > max_pings:
                    novo_historico = novo_historico[-max_pings:]
                
                novo_ativo = ativo.model_copy(update={
                    "status": novo_status, "latencia": nova_latencia,
                    "latencia_total": ativo.latencia_total + nova_latencia,
                    "qnt_pings": ativo.qnt_pings + 1, "historico": novo_historico
                })
                ativos_atualizados.append(novo_ativo)
            
            async with self:
                if not self.monitorando or self.ciclo_atual != meu_ciclo: break
                self.ativos = ativos_atualizados
            
            await asyncio.sleep(intervalo)

    @rx.event(background=True)
    async def loop_relatorio(self):
        async with self:
            if getattr(self, "loop_relatorio_ativo", False): return
            self.loop_relatorio_ativo = True

        while True:
            async with self:
                estado_config = await self.get_state(ConfigState)
                tempo_espera = estado_config.config["frequencia_emails"]
                
            await asyncio.sleep(tempo_espera*60)
            
            async with self:
                if not self.monitorando or not self.ativos: continue
                
                ativos_para_relatorio = []
                ativos_zerados = []

                for ativo in self.ativos:
                    media_da_hora = ativo.latencia_total / ativo.qnt_pings if ativo.qnt_pings > 0 else 0.0
                    
                    ativo_relatorio = ativo.model_copy(update={"latencia": media_da_hora})
                    ativos_para_relatorio.append(ativo_relatorio)

                    ativo_limpo = ativo.model_copy(update={"latencia_total": 0.0, "qnt_pings": 0})
                    ativos_zerados.append(ativo_limpo)

                self.ativos = ativos_zerados
                
                estado_config = await self.get_state(ConfigState)
                destinatarios = estado_config.emails.copy()

            if destinatarios:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Enviando relatório horário automático...")
                disparar_email(ativos_para_relatorio, destinatarios) # Função externa