from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv, set_key
from sqlmodel import Field
import os
import asyncio
import reflex as rx
import icmplib
import smtplib
import bcrypt
import uuid
import csv
import io
import ipaddress

_config_path = "config.env"
_ping_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="echo_ping")

# Criação do arquivo config.env se não existir
if not os.path.exists(_config_path):
    print("Arquivo config.env nao encontrado. Criando arquivo de exemplo...")
    with open(_config_path, "w", encoding="utf-8") as f:
        f.write("# Configurações de email\nSMTP_SERVER=mail.seudominio.com.br\nSMTP_PORT=465\nSMTP_LOGIN=alertas@seudominio.com.br\nSMTP_PASSWORD=suasenha\n# Configurações de monitoramento\nINTERVALO_SEGUNDOS=10\nLIMITE_LATENCIA_MS=100\nPINGS_MAXIMOS=12\nFREQUENCIA_EMAILS=60")

load_dotenv(_config_path, override=True)

class User(rx.Model, table=True):
    """Tabela para armazenar os usuários no banco de dados SQLite."""
    username: str = Field(index=True, unique=True)
    email: str  = Field(index=True, unique=True)
    password: str
    role: str = "operador" # "admin" ou "operador"
    session_token: str = ""

class AtivoRede(rx.Model):
    """Modelo para representar os ativos de rede em memória durante o monitoramento."""
    nome: str
    ip: str
    local: str
    grupo: str = "GERAL"
    cor_grupo: str = "gray"
    ininterrupto: bool = False
    latencia: float = 0.0
    latencia_total: float = 0.0
    qnt_pings: int = 0
    pings_offline: int = 0
    alerta_enviado: bool = False
    status: str = "Aguardando..."
    historico: list[dict[str, str | float]] = []

class AtivoDB(rx.Model, table=True):
    """Tabela para armazenar os ativos de rede no banco de dados SQLite."""
    nome: str
    ip: str = Field(index=True, unique=True)
    local: str
    grupo: str = "GERAL"
    status: str = "Aguardando..."

class GrupoDB(rx.Model, table=True):
    """Tabela para armazenar grupos no banco de dados SQLite."""
    nome: str = Field(index=True, unique=True)
    ininterrupto: bool = False
    cor: str = "gray" # Cor padrão, pode ser personalizada

def disparar_relatorio(ativos: list[AtivoRede]):
    # Travas de segurança: não tenta enviar se faltar dados
    if not carregar_emails():
        print("Operação cancelada: Nenhum e-mail cadastrado na lista de envio.")
        return
    if not ativos:
        print("Operação cancelada: Nenhum ativo de rede cadastrado para gerar o relatório.")
        return

    load_dotenv(_config_path, override=True)

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
    msg['To'] = ", ".join(carregar_emails())
    msg.attach(MIMEText(corpo_html, 'html'))

    # 4. Conecta no servidor e faz o disparo
    try:
        print(f"Conectando ao servidor SMTP {servidor} via SSL...")
        server = smtplib.SMTP_SSL(servidor, porta)
        server.login(login, senha)
        server.sendmail(login, carregar_emails(), msg.as_string())
        server.quit()
        
        print("E-mail de teste enviado e entregue com sucesso!")
    except Exception as e:
        print(f"Falha crítica ao enviar o e-mail: {e}")

def disparar_alerta_offline(ativos_criticos: list[AtivoRede]):
    if not ativos_criticos:
        return

    load_dotenv(_config_path, override=True)
    servidor=os.environ.get("SMTP_SERVER")
    porta=int(os.environ.get("SMTP_PORT", 465))
    login=os.environ.get("SMTP_LOGIN")
    senha=os.environ.get("SMTP_PASSWORD")

    linhas_tabela = ""
    for ativo in ativos_criticos:
        linhas_tabela += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;"><b>{ativo.nome}</b></td>
            <td style="padding:10px;border-bottom:1px solid #eee;">{ativo.ip}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">{ativo.local}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">{ativo.grupo}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;color:red;font-weight:bold;">
                Offline ({ativo.pings_offline} pings)
            </td>
        </tr>
        """

    corpo_html = f"""
    <html>
        <body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;">
            <h2 style="color:#cc0000;">⚠️ Echo — Alerta de Ativos Offline</h2>
            <p>Os seguintes ativos de grupos críticos (24/7) estão offline:</p>
            <table style="border-collapse:collapse;width:100%;max-width:800px;margin-top:20px;
                          text-align:left;box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                <tr style="background-color:#f4f6f8;">
                    <th style="padding:12px;border-bottom:2px solid #ccc;">Equipamento</th>
                    <th style="padding:12px;border-bottom:2px solid #ccc;">IP</th>
                    <th style="padding:12px;border-bottom:2px solid #ccc;">Localização</th>
                    <th style="padding:12px;border-bottom:2px solid #ccc;">Grupo</th>
                    <th style="padding:12px;border-bottom:2px solid #ccc;">Status</th>
                </tr>
                {linhas_tabela}
            </table>
            <p style="margin-top:30px;font-size:12px;color:#777;">
                Alerta gerado automaticamente pelo painel Echo.
            </p>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['Subject']=f"⚠️ Echo: {len(ativos_criticos)} ativo(s) offline em grupos críticos"
    msg['From']=login
    msg['To']=", ".join(carregar_emails())
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        server = smtplib.SMTP_SSL(servidor, porta)
        server.login(login, senha)
        server.sendmail(login, carregar_emails(), msg.as_string())
        server.quit()
        print(f"[ALERTA] E-mail de offline disparado para {len(ativos_criticos)} ativo(s).")
    except Exception as e:
        print(f"[ALERTA] Falha ao enviar e-mail de alerta: {e}")

def carregar_emails():
    with rx.session() as session:
        # Puxa todos os usuários do banco
        usuarios = session.exec(User.select()).all()
        
        # Filtra apenas os que têm e-mail preenchido para evitar erros
        lista_emails = [u.email for u in usuarios if u.email]
        
        return lista_emails

# 1. ESTADO BASE
class AppState(rx.SharedState):
    """Estado global compartilhado entre todas as páginas, ideal para dados que precisam ser acessados em múltiplas telas."""

    monitorando: bool = False
    ativos_live: list[AtivoRede] = []
    ciclo: int = 0
    filtro_grupo_atual: str = "Todos"

    ativos_buffer: list[dict[str, str]] = []
    buffer_iniciado: bool = False

    proximo_relatorio: int = 0

    ram_intervalo: int = 10
    ram_limite_ms: int = 100
    ram_max_pings: int = 12
    ram_freq_emails: int = 60

    @rx.var
    def ativos_agrupados(self) -> dict[str, list[AtivoRede]]:
        grupos = {}
        for ativo in self.ativos_live:
            nome_grupo = getattr(ativo, "grupo", None) or "GERAL"
            if nome_grupo not in grupos:
                grupos[nome_grupo] = []
            grupos[nome_grupo].append(ativo)
        return grupos

    @rx.event
    async def recarregar_configs_da_memoria(self):
        """O Gatilho: Puxa o .env atualizado e injeta na RAM para os loops usarem."""
        load_dotenv(_config_path, override=True)
        self.ram_intervalo = int(os.environ.get("INTERVALO_SEGUNDOS", 10))
        self.ram_limite_ms = int(os.environ.get("LIMITE_LATENCIA_MS", 100))
        self.ram_max_pings = int(os.environ.get("PINGS_MAXIMOS", 12))
        self.ram_freq_emails = int(os.environ.get("FREQUENCIA_EMAILS", 60))

    @rx.event
    async def conectar_painel(self):
        """Sintoniza o navegador na Sala Global e garante que o buffer tenha dados."""
        # 1. Vincula o navegador ao token central e pega a instância oficial do servidor
        linked_state = await self._link_to("echo-painel-central")
        
        # 2. Se for o primeiro computador a entrar na sala desde que o servidor ligou, 
        # ele vai até o banco de dados SQLite e puxa o rascunho inicial.
        if not linked_state.buffer_iniciado:
            with rx.session() as session:
                # Carrega o mapa de cores dos grupos
                grupos_db = session.exec(GrupoDB.select()).all()
                mapa_cores = {g.nome: g.cor for g in grupos_db}
                mapa_ininterrupto = {g.nome: g.ininterrupto for g in grupos_db}
                
                # Carrega os ativos salvos no HD
                registros = session.exec(AtivoDB.select()).all()
                
                # Alimenta a prancheta colaborativa oficial do Servidor
                linked_state.ativos_buffer = [
                    {
                        "nome": a.nome, 
                        "ip": a.ip, 
                        "local": a.local, 
                        "grupo": a.grupo, 
                        "cor_grupo": mapa_cores.get(a.grupo, "gray")
                    } 
                    for a in registros
                ]

                if not linked_state.monitorando:
                    linked_state.ativos_live = [
                        AtivoRede(
                            nome=a.nome, 
                            ip=a.ip, 
                            local=a.local,
                            grupo=a.grupo, 
                            cor_grupo=mapa_cores.get(a.grupo, "gray"),
                            ininterrupto=mapa_ininterrupto.get(a.grupo, False),
                            status="Aguardando...", 
                            latencia=0.0,
                            latencia_total=0.0, 
                            qnt_pings=0, 
                            historico=[]
                        ) for a in registros
                    ]

                linked_state.buffer_iniciado = True
    
    @rx.event
    def parar_monitoramento_global(self):
        """O botão Stop (visto por todos)."""
        self.monitorando = False
        self.ciclo += 1
        
        # Reseta o status visual para quem estiver assistindo
        self.ativos_live = [
            a.model_copy(update={"status": "Aguardando...", "latencia": 0.0, "historico": []}) 
            for a in self.ativos_live
        ]

        return rx.toast.info("Monitoramento pausado.", position="top-right")

    @rx.event(background=True)
    async def loop_motor_central(self):
        async with self:
            await self.recarregar_configs_da_memoria()
            meu_ciclo = self.ciclo
    
        loop = asyncio.get_running_loop()
    
        while True:
            try:
                async with self:
                    if not self.monitorando or self.ciclo != meu_ciclo:
                        break
                    
                    ativos_snapshot = [
                        {
                            "nome": str(a.nome),
                            "ip": str(a.ip),
                            "local": str(a.local),
                            "grupo": str(a.grupo),
                            "cor_grupo": str(a.cor_grupo),
                            "ininterrupto": bool(a.ininterrupto),
                            "latencia_total": float(a.latencia_total),
                            "qnt_pings": int(a.qnt_pings),
                            "pings_offline": int(a.pings_offline),
                            "alerta_enviado": bool(a.alerta_enviado),
                            "historico":[
                                {"hora": str(h["hora"]), "latencia": float(h["latencia"])}
                                for h in list(a.historico)[-(self.ram_max_pings - 1):]
                            ],
                        }
                        for a in self.ativos_live
                    ]
                    intervalo = int(self.ram_intervalo)
                    limite_ms = float(self.ram_limite_ms)
                    max_pings = int(self.ram_max_pings)
    
                if not ativos_snapshot:
                    await asyncio.sleep(intervalo)
                    continue
                
                hora_atual = datetime.now().strftime("%H:%M:%S")
    
                def pingar_sync(ip: str) -> tuple[str, float]:
                    try:
                        resultado = icmplib.ping(
                            ip,
                            count=1,
                            timeout=2,
                            privileged=False,
                        )
                        if resultado.is_alive:
                            return "vivo", round(resultado.avg_rtt, 1)
                        return "morto", 0.0
                    except Exception as e:
                        print(f"[PING] Erro ao pingar {ip}: {e}")
                        return "morto", 0.0
    
                resultados = await asyncio.gather(*[
                    loop.run_in_executor(_ping_executor, pingar_sync, a["ip"])
                    for a in ativos_snapshot
                ])
    
                ativos_atualizados = []
                disparar_alerta = False

                for ativo, (estado, nova_latencia) in zip(ativos_snapshot, resultados):
                    novo_status = (
                        "Offline" if estado == "morto"
                        else "Lento" if nova_latencia > limite_ms
                        else "Online"
                    )

                    # Atualiza contador de pings offline consecutivos
                    if novo_status == "Offline":
                        novo_pings_offline = ativo["pings_offline"] + 1
                    else:
                        novo_pings_offline = 0

                    # Reseta o alerta quando o ativo voltar online
                    novo_alerta_enviado = ativo["alerta_enviado"]
                    if novo_status != "Offline":
                        novo_alerta_enviado = False

                    # Marca para disparar alerta se ativo ininterrupto atingiu 5 pings offline
                    if (
                        ativo["ininterrupto"]
                        and novo_pings_offline >= 5
                        and not novo_alerta_enviado
                    ):
                        disparar_alerta = True

                    novo_historico = ativo["historico"] + [
                        {"hora": hora_atual, "latencia": nova_latencia}
                    ]

                    ativos_atualizados.append(AtivoRede(
                        nome=ativo["nome"],
                        ip=ativo["ip"],
                        local=ativo["local"],
                        grupo=ativo["grupo"],
                        cor_grupo=ativo["cor_grupo"],
                        ininterrupto=ativo["ininterrupto"],
                        latencia=nova_latencia,
                        latencia_total=ativo["latencia_total"] + nova_latencia,
                        qnt_pings=ativo["qnt_pings"] + 1,
                        pings_offline=novo_pings_offline,
                        alerta_enviado=novo_alerta_enviado,
                        status=novo_status,
                        historico=novo_historico,
                    ))

                # Dispara alerta e marca os ativos para não repetir
                if disparar_alerta:
                    ativos_criticos = [
                        a for a in ativos_atualizados
                        if a.ininterrupto and a.pings_offline >= 3
                    ]
                    if ativos_criticos:
                        # Marca alerta_enviado para não repetir no próximo ciclo
                        for a in ativos_atualizados:
                            if a.ininterrupto and a.pings_offline >= 5:
                                a.alerta_enviado = True

                        loop.run_in_executor(
                            _ping_executor,
                            disparar_alerta_offline,
                            ativos_criticos.copy()
                        )
    
                async with self:
                    if not self.monitorando or self.ciclo != meu_ciclo:
                        break
                    self.ativos_live = ativos_atualizados
    
                await asyncio.sleep(intervalo)
    
            except asyncio.CancelledError:
                # O Reflex cancelou o task intencionalmente — encerra limpo
                print("[MOTOR] Task cancelada pelo Reflex. Encerrando loop.")
                break
            except Exception as e:
                # Qualquer outro erro: loga e continua na próxima iteração
                print(f"[MOTOR] Erro inesperado no ciclo de monitoramento: {e}")
                await asyncio.sleep(5)  # Pausa curta antes de tentar de novo
                continue
    
    @rx.event(background=True)
    async def loop_relatorio(self):
        """Loop contínuo que dispara os e-mails baseados no tempo configurado."""
        async with self:
            meu_ciclo = self.ciclo
            
        while True:
            # 1. Pega a frequência da RAM (e converte para segundos)
            async with self:
                if not self.monitorando or self.ciclo != meu_ciclo:
                    break
                tempo_espera_segundos = self.ram_freq_emails * 60 

            # 2. O SEGREDO: As Micro-Sonecas!
            # Dorme 1 segundo por vez para poder checar se o usuário clicou em Pausar
            for t in range(tempo_espera_segundos):
                await asyncio.sleep(1)
                
                # A cada segundo, dá uma espiada no status da Sala Global
                async with self:
                    # Se o sistema foi pausado ou reiniciado, MATA o loop imediatamente
                    self.proximo_relatorio = tempo_espera_segundos - t

                    if not self.monitorando or self.ciclo != meu_ciclo:
                        return 

            # 3. O tempo de espera acabou completo. Hora de tirar a fotografia da rede!
            async with self:
                if not self.monitorando or self.ciclo != meu_ciclo:
                    break
            
            # 5. Dispara o e-mail
            disparar_relatorio(self.ativos_live.copy())

# 2. ESTADO DE AUTENTICAÇÃO
class AuthState(rx.State):
    usuario_logado: str = rx.SessionStorage("", name="echo_session_user")
    role_logado: str = rx.SessionStorage("operador", name="echo_user_role")
    token_logado: str = rx.SessionStorage("", name="echo_session_token")

    email_input: str = ""
    senha_input: str = ""

    # Variáveis de setup inicial
    setup_username: str = "admin" # Sugestão padrão
    setup_email: str = ""
    setup_password: str = ""
    setup_confirmacao: str = ""

    tentando_login: bool = False

    @rx.event
    def tentar_login(self):
        with rx.session() as session:
            # Procura o utilizador na base de dados
            user = session.exec(
                User.select().where(User.email == self.email_input.lower().strip())
            ).first()

            self.tentando_login = True
            print(self.tentando_login)

            if user:    
                # Verifica a senha usando o Hash Bcrypt
                password_bytes = self.senha_input.encode('utf-8')
                hash_bytes = user.password.encode('utf-8')
                novo_token = str(uuid.uuid4())

                if bcrypt.checkpw(password_bytes, hash_bytes):
                    novo_token = str(uuid.uuid4())
                    
                    # Atualiza o token no banco de dados (anulando logins antigos)
                    user.session_token = novo_token
                    session.add(user)
                    session.commit()

                    self.usuario_logado = user.username
                    self.role_logado = user.role
                    self.token_logado = novo_token # Manda para o navegador atual
                    
                    self.email_input = ""
                    self.senha_input = ""

                    print(f"Token local: {self.token_logado} | Token banco: {user.session_token}")
                    
                    self.tentando_login = False
                    print(self.tentando_login)
                    yield rx.redirect("/")          
                    return

            # Se falhar (utilizador não existe ou senha errada)
            yield rx.toast.error("Usuário ou senha incorretos.", position="top-right")
            self.senha_input = ""
            self.tentando_login = False
            print(self.tentando_login)

    @rx.event
    def fazer_logout(self):
        with rx.session() as db_session:
            user = db_session.exec(User.select().where(User.username == self.usuario_logado)).first()
            if user:
                user.session_token = ""
                db_session.add(user)
                db_session.commit()

        # Limpa o navegador
        self.usuario_logado = ""
        self.token_logado = ""
        return rx.redirect("/login")

    @rx.event
    async def verificar_acesso(self):
        """O Novo Guarda-Costas: Verifica banco vazio -> Login -> Painel"""
        with rx.session() as session:
            # Se não existe NENHUM usuário no banco, força a ir para a tela de Setup
            if not session.exec(User.select()).first():
                print("Nenhum usuário encontrado no banco de dados. Redirecionando para a tela de configuração inicial.")
                self.usuario_logado, self.token_logado = "", ""
                return rx.redirect("/setup")
                
            # Se existem usuários, mas o navegador não tem sessão, vai pro Login
            if not self.usuario_logado or not self.token_logado:
                print("Acesso negado: Nenhuma sessão ativa encontrada no navegador.")
                return rx.redirect("/login")
    
            user = session.exec(User.select().where(User.username == self.usuario_logado)).first()

            if user:
                # O PULO DO GATO: Se o token do navegador for diferente do banco, 
                # significa que outro PC fez login com essa conta depois de nós!
                if user.session_token != self.token_logado:
                    print("Acesso negado: Token de sessão inválido. Outro login detectado para este usuário.")
                    self.usuario_logado, self.token_logado = "", ""   
                    return rx.redirect("/login")

                self.role_logado = user.role
            else:
                print("Acesso negado: Usuário não encontrado no banco de dados.")
                self.usuario_logado, self.token_logado = "", ""
                return rx.redirect("/login")

    @rx.event
    def checar_acesso_login(self):
        """Protege a própria tela de login. Se o banco estiver vazio, expulsa pro Setup."""
        with rx.session() as session:
            if not session.exec(User.select()).first():
                return rx.redirect("/setup")
                
        # Se já estiver logado e tentar abrir o /login, manda pro Painel
        if self.usuario_logado:
            return rx.redirect("/")

    @rx.event
    def registrar_primeiro_admin(self):
        """Cria o usuário Master e destranca o sistema."""
        if not self.setup_username or not self.setup_password or not self.setup_confirmacao or not self.setup_email:
            yield rx.toast.error("Todos os campos são obrigatórios para criar o administrador.", position="top-right")
            return
        
        if self.setup_password != self.setup_confirmacao:
            yield rx.toast.warning("As senhas não coincidem.", position="top-right")
            return

        with rx.session() as session:
            # Proteção: Se alguém já criou, bloqueia a operação
            if session.exec(User.select()).first():
                yield rx.toast.error("O sistema já possui um administrador.", position="top-right")
                return
            
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(self.setup_password.encode('utf-8'), salt)
            
            novo_admin = User(
                username=self.setup_username.lower().strip(),
                email=self.setup_email.lower().strip(),
                password=hashed.decode('utf-8'),
                role="admin",
            )
            session.add(novo_admin)
            session.commit()
        
        # Loga automaticamente o criador e joga para o painel principal!
        self.setup_username = ""
        self.setup_email = ""
        self.setup_password = ""
        self.setup_confirmacao = ""
        return rx.redirect("/login")

# 3. ESTADO DE CONFIGURAÇÕES
class ConfigState(rx.State):
    """Gerencia exclusivamente as variáveis de ambiente e e-mails."""

    # Variáveis de e-mails
    emails: list[str] = []
    novo_email_input: str = ""

    # Variáveis de grupos
    grupos: list[dict[str, str]] = []
    novo_grupo_input: str = ""
    novo_grupo_cor_input: str = "gray"
    novo_grupo_ininterrupto_input: bool = False
    filtro_grupo_atual: str = "Todos"
    cor_grupo_atual: str = "gray"

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

    @rx.var
    def nomes_dos_grupos(self) -> list[str]:
        """Gera uma lista com o nome dos grupos para os filtros e dropdowns."""
        return [g["nome"] for g in self.grupos]

    # --- CONFIGURAÇÕES GERAIS ---
    @rx.event
    def carregar_configs(self):
        self.config: dict[str, str | int]  = {
            "smtp_server": os.environ.get("SMTP_SERVER", ""), 
            "smtp_port": int(os.environ.get("SMTP_PORT", 465)),
            "smtp_login": os.environ.get("SMTP_LOGIN", ""), 
            "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
            "intervalo_segundos": int(os.environ.get("INTERVALO_SEGUNDOS", 10)),
            "limite_latencia_ms": int(os.environ.get("LIMITE_LATENCIA_MS", 100)),
            "pings_maximos": int(os.environ.get("PINGS_MAXIMOS", 12)),
            "frequencia_emails": int(os.environ.get("FREQUENCIA_EMAILS", 60))
        }
        self.config_buffer: dict[str, str | int] = self.config.copy()

    @rx.event
    def atualizar_buffer(self, chave: str, valor: str):
        chaves_numericas = ["smtp_port", "intervalo_segundos", "limite_latencia_ms", "pings_maximos", "frequencia_emails"]
        if chave in chaves_numericas:
            self.config_buffer[chave] = int(valor) if valor.isdigit() else self.config[chave]
        else:
            self.config_buffer[chave] = valor

    @rx.event
    async def salvar_configs_env(self):
        """Salva as alterações do buffer fisicamente no arquivo .env."""      
        
        # Garante que o arquivo exista
        if not os.path.exists(_config_path):
            open(_config_path, 'w').close()
            
        # O set_key pede Strings, então convertemos tudo para str() ao salvar
        set_key(_config_path, "SMTP_SERVER", str(self.config_buffer["smtp_server"]))
        set_key(_config_path, "SMTP_PORT", str(self.config_buffer["smtp_port"]))
        set_key(_config_path, "SMTP_LOGIN", str(self.config_buffer["smtp_login"]))
        set_key(_config_path, "SMTP_PASSWORD", str(self.config_buffer["smtp_password"]))
        set_key(_config_path, "INTERVALO_SEGUNDOS", str(self.config_buffer["intervalo_segundos"]))
        set_key(_config_path, "LIMITE_LATENCIA_MS", str(self.config_buffer["limite_latencia_ms"]))
        set_key(_config_path, "PINGS_MAXIMOS", str(self.config_buffer["pings_maximos"]))
        set_key(_config_path, "FREQUENCIA_EMAILS", str(self.config_buffer["frequencia_emails"]))

        # Atualiza a tela privada do usuário que acabou de clicar
        self.config = self.config_buffer.copy()

        # Retorna o aviso de sucesso e o "Gatilho" para atualizar a RAM do Servidor Global
        return [
            rx.toast.success("Configurações salvas e aplicadas!", position="top-right"),
            AppState.recarregar_configs_da_memoria
        ]

    # --- GRUPOS ---
    @rx.event
    def carregar_grupos(self):
        with rx.session() as session:
            grupo_padrao = session.exec(GrupoDB.select().where(GrupoDB.nome == "GERAL")).first()
            
            # Se não existir (ex: primeira vez rodando o app), ele cria na hora!
            if not grupo_padrao:
                novo_padrao = GrupoDB(nome="GERAL", cor="gray", ininterrupto=False)
                session.add(novo_padrao)
                session.commit()

            registros = session.exec(GrupoDB.select()).all()
            self.grupos = [{"nome": s.nome, "cor": s.cor, "ininterrupto": s.ininterrupto} for s in registros]

    @rx.event
    def adicionar_grupo(self):
        grupo_limpo = self.novo_grupo_input.strip().upper() # Padroniza tudo em maiúsculo (ex: TI, GALPÃO)
        cor_limpa = self.novo_grupo_cor_input.strip()
        ininterrupto = self.novo_grupo_ininterrupto_input

        if not grupo_limpo: 
            return rx.toast.warning("O nome do grupo é obrigatório.", position="top-right")
        
        with rx.session() as session:
            registro = session.exec(GrupoDB.select().where(GrupoDB.nome == grupo_limpo)).first()

            if not registro:
                novo = GrupoDB(nome=grupo_limpo, cor=cor_limpa, ininterrupto=ininterrupto)
                session.add(novo)
                session.commit()

                self.novo_grupo_input = ""
                self.novo_grupo_cor_input = "gray"
                self.novo_grupo_ininterrupto_input = False
                self.carregar_grupos()

                return rx.toast.success(f"Grupo '{grupo_limpo}' adicionado!", position="top-right")
            return rx.toast.warning("Grupo já existe.", position="top-right")

    @rx.event
    def remover_grupo(self, grupo_alvo: str):
        if grupo_alvo == "Nenhum":
            return rx.toast.error("O grupo padrão não pode ser apagado.", position="top-right")
            
        with rx.session() as session:
            registro = session.exec(GrupoDB.select().where(GrupoDB.nome == grupo_alvo)).first()

            if registro:
                session.delete(registro)
                session.commit()

                self.carregar_grupos()
                return rx.toast.success(f"Grupo '{grupo_alvo}' removido!", position="top-right")

# 4. ESTADO DE MONITORAMENTO
class MonitoramentoState(rx.State):
    """Gerencia exclusivamente os pings, ativos e relatórios."""
    ativos: list[AtivoRede] = []

    # Variáveis do formulário de novo ativo
    novo_ativo_nome: str = ""
    novo_ativo_ip: str = ""
    novo_ativo_local: str = ""
    novo_ativo_grupo: str = ""

    # Variáveis de edição de ativo
    ip_edicao = ""
    edit_nome = ""
    edit_ip = ""
    edit_local = ""
    edit_grupo = "GERAL"

    preview_csv: list[dict[str, str]] = []
    preview_total: int = 0
    preview_validos: int = 0
    preview_erros: int = 0
    _arquivo_csv_buffer: list[AtivoDB] = []

    @rx.event
    async def carregar_preview_csv(self, arquivos: list[rx.UploadFile]):
        """Lê o CSV, valida cada linha e monta a tabela de pré-visualização."""
        if not arquivos:
            return rx.toast.error("Nenhum arquivo foi enviado!", position="top-right")

        arquivo = arquivos[0]
        conteudo_bytes = await arquivo.read()
        conteudo_texto = conteudo_bytes.decode("utf-8")

        leitor_csv = csv.DictReader(io.StringIO(conteudo_texto))

        preview = []
        ativos_validos = []

        with rx.session() as session:
            grupos_existentes = {g.nome for g in session.exec(GrupoDB.select()).all()}
            ips_existentes = {a.ip for a in session.exec(AtivoDB.select()).all()}

        ips_no_csv = set()

        for index, linha in enumerate(leitor_csv, start=1):
            nome = linha.get("nome", "").strip()
            ip = linha.get("ip", "").strip()
            local = linha.get("local", "").strip()
            grupo = linha.get("grupo", "GERAL").strip() or "GERAL"
            erro = ""

            if not nome or not ip:
                erro = "Nome ou IP ausente"

            if not erro and ip in ips_existentes:
                erro = "IP já cadastrado"

            if not erro and ip in ips_no_csv:
                erro = "IP duplicado no CSV"

            if not erro and grupo not in grupos_existentes:
                grupo = "GERAL"

            preview.append({
                "nome": nome,
                "ip": ip,
                "local": local,
                "grupo": grupo,
                "erro": erro,
            })

            if not erro:
                ips_no_csv.add(ip)
                ativos_validos.append(
                    AtivoDB(nome=nome, ip=ip, local=local, grupo=grupo, status="Aguardando...")
                )

        self.preview_csv = preview
        self.preview_total = len(preview)
        self.preview_validos = len(ativos_validos)
        self.preview_erros = len(preview) - len(ativos_validos)
        self._arquivo_csv_buffer = ativos_validos

    @rx.event
    async def confirmar_importacao_csv(self):
        """Grava no banco apenas os ativos válidos do buffer e sincroniza o painel."""
        if not self._arquivo_csv_buffer:
            return rx.toast.warning("Nenhum ativo válido para importar.", position="top-right")

        try:
            with rx.session() as session:
                for ativo in self._arquivo_csv_buffer:
                    session.add(ativo)
                session.commit()
        except Exception as e:
            return rx.toast.error(f"Erro ao salvar no banco: {e}", position="top-right")

        total = len(self._arquivo_csv_buffer)
        self.limpar_preview_csv()

        sala = await self.get_state(AppState)
        sala.buffer_iniciado = False
        await sala.conectar_painel()

        return rx.toast.success(f"{total} ativo(s) importado(s) com sucesso!", position="top-right")

    @rx.event
    def limpar_preview_csv(self):
        """Reseta o estado de preview."""
        self.preview_csv = []
        self.preview_total = 0
        self.preview_validos = 0
        self.preview_erros = 0
        self._arquivo_csv_buffer = []

    @rx.event
    def exportar_ativos_csv(self):
        """Busca os dados no banco e gera um CSV para download."""
        # 1. Puxa a fonte da verdade absoluta (O Banco de Dados)
        with rx.session() as session:
            ativos_db = session.exec(AtivoDB.select()).all()
            
        if not ativos_db:
            return rx.toast.warning("Não há ativos cadastrados para exportar.", position="top-right")

        # 2. Cria um arquivo de texto virtual na memória RAM
        saida_csv = io.StringIO()
        
        # 3. Define o cabeçalho EXATAMENTE igual ao esperado na importação
        campos = ["nome", "ip", "local", "grupo"]
        escritor = csv.DictWriter(saida_csv, fieldnames=campos)
        
        escritor.writeheader()
        
        # 4. Preenche as linhas
        for ativo in ativos_db:
            escritor.writerow({
                "nome": ativo.nome,
                "ip": ativo.ip,
                "local": ativo.local,
                "grupo": ativo.grupo
            })
            
        # 5. Extrai o texto final gerado
        conteudo_csv = saida_csv.getvalue()
        
        # 6. Gera um nome de arquivo elegante com a data de hoje
        data_atual = datetime.now().strftime("%Y-%m-%d_%H-%M")
        nome_arquivo = f"backup_ativos_{data_atual}.csv"
        
        # 7. Dispara o gatilho de download nativo do Reflex para o navegador
        return [
            rx.download(
                data=conteudo_csv,
                filename=nome_arquivo
            ),
            rx.toast.info("Download do backup iniciado!", position="top-right")
        ]

    @rx.event
    def carregar_ativos(self):
        with rx.session() as session:
            grupos_db = session.exec(GrupoDB.select()).all()
            mapa_cores = {g.nome: g.cor for g in grupos_db}
            mapa_ininterrupto = {g.nome: g.ininterrupto for g in grupos_db}

            registros = session.exec(AtivoDB.select()).all()
            self.ativos = [
                AtivoRede(
                    nome=a.nome,
                    ip=a.ip,
                    local=a.local,
                    grupo=a.grupo,
                    cor_grupo=mapa_cores.get(a.grupo, "gray"),
                    ininterrupto=mapa_ininterrupto.get(a.grupo, False),
                    status="Aguardando...",
                    latencia=0.0,
                    latencia_total=0.0,
                    qnt_pings=0,
                    pings_offline=0,
                    alerta_enviado=False,
                    historico=[],
                )
                for a in registros
            ]

    @rx.event
    async def on_load(self):
        """Inicializa o buffer com os ativos existentes e joga na tela."""
        self.carregar_ativos() # Lê o banco de dados e salva no self.ativos (Privado)
        
        # Conecta na Sala Global para verificar o status
        sala = await self.get_state(AppState)
        
        # Se o motor central estiver DESLIGADO, joga a lista inativa na TV para os usuários verem!
        if not sala.monitorando and len(sala.ativos_live) == 0:
            sala.ativos_live = self.ativos

    @rx.event
    async def adicionar_ativo_buffer(self):
        ip_limpo = self.novo_ativo_ip.strip()
        grupo_limpo = self.novo_ativo_grupo.strip() or "GERAL"

        sala = await self.get_state(AppState)
        estado_config = await self.get_state(ConfigState)

        # Trava para IPs repetidos no buffer
        for ativo in sala.ativos_buffer:
            if ativo["ip"] == ip_limpo:
                return rx.toast.warning("Este IP já está na lista!", position="top-right")
    
        if self.novo_ativo_nome and ip_limpo and self.novo_ativo_local and grupo_limpo:
            cor_encontrada = "gray"
            for g in estado_config.grupos:
                if g["nome"] == grupo_limpo:
                    cor_encontrada = g["cor"]
                    break
            
            sala.ativos_buffer.append({
                "nome": self.novo_ativo_nome.strip(),
                "ip": ip_limpo,
                "local": self.novo_ativo_local.strip(),
                "grupo": grupo_limpo,
                "cor_grupo": cor_encontrada
            })

            self.novo_ativo_nome = ""
            self.novo_ativo_ip = ""
            self.novo_ativo_local = ""
            self.novo_ativo_grupo = ""
            
    @rx.event
    async def remover_ativo_buffer(self, ip_alvo: str):
        sala = await self.get_state(AppState)
        sala.ativos_buffer = [a for a in sala.ativos_buffer if a["ip"] != ip_alvo]

    @rx.event
    async def salvar_ativos(self):
        """Salva a lista do buffer GLOBAL diretamente no Banco de Dados (sem JSON)"""
        
        # 1. Pega a prancheta colaborativa da Sala Global PRIMEIRO
        sala = await self.get_state(AppState)
        
        with rx.session() as session:
            # Apaga a tabela antiga
            todos_antigos = session.exec(AtivoDB.select()).all()
            for antigo in todos_antigos:
                session.delete(antigo)
            
            session.commit()

            # Insere os ativos usando a lista da SALA GLOBAL (sala.ativos_buffer)
            for item in sala.ativos_buffer:
                novo_ativo = AtivoDB(
                    nome=item['nome'], 
                    ip=item['ip'], 
                    local=item['local'], 
                    grupo=item['grupo'],
                    status="Aguardando..."
                )
                session.add(novo_ativo)
                
            session.commit()
            
        # 2. Recarrega do banco para o estado privado (HD)
        self.carregar_ativos() 
        
        # 3. Mesclagem Inteligente (Atualiza a tela na hora!)
        if not sala.monitorando:
            # Se o sistema estiver pausado, é só jogar a lista nova na tela
            sala.ativos_live = self.ativos
        else:
            # Se estiver rodando, mantemos o status dos antigos e adicionamos os novos!
            ativos_rodando = {a.ip: a for a in sala.ativos_live}
            nova_lista_global = []
            
            for ativo_base in self.ativos:
                if ativo_base.ip in ativos_rodando:
                    # Atualiza os dados de configuração mas mantém o status de ping
                    ativo_mantido = ativos_rodando[ativo_base.ip]
                    ativo_mantido.nome = ativo_base.nome
                    ativo_mantido.local = ativo_base.local
                    ativo_mantido.grupo = ativo_base.grupo
                    ativo_mantido.cor_grupo = ativo_base.cor_grupo
                    nova_lista_global.append(ativo_mantido)
                else:
                    # IP novo
                    nova_lista_global.append(ativo_base)
            
            # O Reflex avisa todos os PCs
            sala.ativos_live = nova_lista_global
            
        return rx.toast.success("Ativos atualizados e sincronizados!", position="top-right")

    @rx.event
    async def iniciar_edicao_ativo(self, ip_alvo: str):
        """Puxa os dados do ativo selecionado para dentro do formulário."""
        sala = await self.get_state(AppState)

        for ativo in sala.ativos_buffer:
            if ativo["ip"] == ip_alvo:
                self.ip_edicao = ip_alvo
                self.edit_nome = ativo["nome"]
                self.edit_ip = ativo["ip"]
                self.edit_local = ativo["local"]
                self.edit_grupo = ativo["grupo"]
                break

    @rx.event
    async def cancelar_edicao_ativo(self):
        """Fecha o modal e limpa as variáveis."""
        self.ip_edicao = ""
        self.edit_nome = ""
        self.edit_ip = ""
        self.edit_local = ""
        self.edit_grupo = "GERAL"

    @rx.event
    async def salvar_edicao_ativo(self):
        """Aplica as mudanças no buffer (com verificação de IP duplo e cor)."""
        ip_antigo = self.ip_edicao
        novo_ip = self.edit_ip.strip()
        novo_grupo = self.edit_grupo.strip() or "GERAL"

        sala = await self.get_state(AppState)
        estado_config = await self.get_state(ConfigState)

        # Trava: Verifica se o usuário trocou o IP para um que já existe
        if novo_ip != ip_antigo:
            for ativo in sala.ativos_buffer:
                if ativo["ip"] == novo_ip:
                    return rx.toast.warning("Este IP já pertence a outro ativo!", position="top-right")

        # Busca a cor atualizada do grupo selecionado
        cor_encontrada = "gray"
        for g in estado_config.grupos:
            if g["nome"] == novo_grupo:
                cor_encontrada = g["cor"]
                break

        # Atualiza a linha exata no buffer
        for ativo in sala.ativos_buffer:
            if ativo["ip"] == ip_antigo:
                ativo["nome"] = self.edit_nome.strip()
                ativo["ip"] = novo_ip
                ativo["local"] = self.edit_local.strip()
                ativo["grupo"] = novo_grupo
                ativo["cor_grupo"] = cor_encontrada
                break

        await self.cancelar_edicao_ativo() # Fecha o modal
        return rx.toast.info("Alteração feita. Clique em 'Salvar' para aplicar no Banco!", position="top-right")

    @rx.event
    async def dar_ignicao_global(self):
        sala = await self.get_state(AppState)
        
        if sala.monitorando:
            return rx.toast.info("O servidor já está monitorando!", position="top-right")

        self.carregar_ativos() 
        
        sala.monitorando = True
        
        # Agora ele passa a lista fresca com todos os novos ativos
        sala.ativos_live = self.ativos 
        sala.ciclo += 1
        
        return [AppState.loop_motor_central(), AppState.loop_relatorio()]

# 5. ESTADO DE GERENCIAMENTO DE USUÁRIOS
class UserManagementState(rx.State):
    """Gerencia a criação e exclusão de usuários do banco de dados."""

    lista_usuarios: list[dict[str, str | int]] = []
    
    # Variáveis do formulário de novo usuário
    form_username: str = ""
    form_email: str = ""
    form_password: str = ""
    form_is_admin: bool = False

    # Variáveis de edição de senha
    usuario_edicao: str = ""
    nova_senha_input: str = ""
    nova_senha_confirmacao: str = ""

    @rx.event
    def carregar_usuarios(self):
        """Lê todos os usuários do banco para exibir na tela."""
        with rx.session() as session:
            users = session.exec(User.select()).all()
            self.lista_usuarios = [{"username": u.username, "email": u.email, "role": u.role} for u in users]

    @rx.event
    def adicionar_usuario(self):
        if not self.form_username or not self.form_password or not self.form_email:
            yield rx.toast.error("Todos os campos são obrigatórios.", position="top-right")
            return

        with rx.session() as session:
            # Verifica se já existe
            registro = session.exec(User.select().where(User.username == self.form_username.lower().strip())).first()
            
            if registro:
                yield rx.toast.error("Esse nome de usuário já existe.", position="top-right")
                return

            # Cria o hash e insere
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(self.form_password.encode('utf-8'), salt)
            
            novo_usuario = User(
                username=self.form_username.lower().strip(),
                email=self.form_email.lower().strip(),
                password=hashed.decode('utf-8'),
                role="admin" if self.form_is_admin else "operador"
            )
            session.add(novo_usuario)
            session.commit()

        # Limpa o formulário e atualiza a lista
        self.form_username = ""
        self.form_password = ""
        self.form_email = ""
        self.form_is_admin = False
        yield rx.toast.success("Usuário criado com sucesso!", position="top-right")
        self.carregar_usuarios()

    @rx.event
    def deletar_usuario(self, username: str):
        if username == "admin":
            yield rx.toast.error("Proteção de sistema: Não é possível deletar o usuário admin principal.", position="top-right")
            return

        with rx.session() as session:
            user = session.exec(User.select().where(User.username == username)).first()
            if user:
                session.delete(user)
                session.commit()
        
        yield rx.toast.success(f"Usuário '{username}' deletado.", position="top-right")
        self.carregar_usuarios()
    
    @rx.event
    def iniciar_edicao_senha(self, username: str):
        """Abre o formulário de senha no cartão do usuário específico."""
        self.usuario_edicao = username
        self.nova_senha_input = ""
        self.nova_senha_confirmacao = ""

    @rx.event
    def cancelar_edicao(self):
        """Fecha o formulário sem salvar."""
        self.usuario_edicao = ""
        self.nova_senha_input = ""
        self.nova_senha_confirmacao = ""

    @rx.event
    def salvar_nova_senha(self):
        """Valida as senhas, gera o novo Hash e salva no banco de dados."""
        if not self.nova_senha_input or not self.nova_senha_confirmacao:
            return rx.toast.error("Preencha ambos os campos de senha.", position="top-right")

        # VALIDAÇÃO DE CONFIRMAÇÃO
        if self.nova_senha_input != self.nova_senha_confirmacao:
            return rx.toast.error("As senhas não coincidem. Tente novamente.", position="top-right")

        with rx.session() as session:
            user = session.exec(User.select().where(User.username == self.usuario_edicao)).first()
            
            if user:
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(self.nova_senha_input.encode('utf-8'), salt)
                
                user.password = hashed.decode('utf-8')
                session.add(user)
                session.commit()
                
                self.usuario_edicao = ""
                self.nova_senha_input = ""
                self.nova_senha_confirmacao = ""    
                return rx.toast.success(f"Senha de '{user.username}' alterada!", position="top-right")
            else:
                self.usuario_edicao = ""
                self.nova_senha_input = ""
                self.nova_senha_confirmacao = ""
                return rx.toast.error("Usuário não encontrado.", position="top-right")