from datetime import datetime
from dotenv import load_dotenv
import reflex as rx
import icmplib
import asyncio
import json
import os
import pydantic
import smtplib
import email

# Criação do arquivo email.env se não existir
if not os.path.exists("Echo/email.env"):
    print("Arquivo email.env nao encontrado. Criando arquivo de exemplo...")
    with open("Echo/email.env", "w", encoding="utf-8") as f:
        f.write("SMTP_SERVER=mail.seudominio.com.br\nSMTP_PORT=465\nSMTP_LOGIN=alertas@seudominio.com.br\nSMTP_PASSWORD=sua_senha_segura_aqui")

# Carregando arquivo de acesso do email
load_dotenv("Echo/email.env")

# Configurações de Dominio
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT"))
SMTP_LOGIN = os.environ.get("SMTP_LOGIN")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

# Configurações
INTERVALO_SEGUNDOS = 10
LIMITE_LATENCIA_MS = 100.0
PINGS_MAXIMOS = 12
FREQUENCIA_EMAILS = 60

# Estrutura do ativo de rede
class AtivoRede(pydantic.BaseModel):
    nome: str
    ip: str
    local: str
    latencia: float = 0.0
    latencia_total: float = 0.0
    qnt_pings: int = 0
    status: str = "Aguardando..."
    historico: list[dict[str, str | float]] = []

# Disparo de relatórios por email
def disparar_relatorio(corpo_html: str):
    msg = email.mime.multipart.MIMEMultipart()
    msg['Subject'] = "Relatório Diário de Desempenho - Echo"
    msg['From'] = SMTP_LOGIN
    msg['To'] = ", ".join(EchoState.emails)
    msg.attach(email.mime.text.MIMEText(corpo_html, 'html'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_LOGIN, SMTP_PASSWORD)
        server.sendmail(SMTP_LOGIN, EchoState.emails, msg.as_string())
        server.quit()
        print("Relatório diário enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar relatório: {e}")

# Processamento de ativos a partir do arquivo ips.json
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

# Processamento de emails a partir do arquivo emails.json
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

# --- ESTADO DE MONITORAMENTO ---
class EchoState(rx.State):
    # Configurações iniciais
    ativos: list[AtivoRede] = carregar_ativos()
    ativos_buffer: list[dict[str, str]] = []
    monitorando: bool = False
    ciclo_atual: int = 0
    
    emails: list[str] = carregar_emails()
    novo_email_input: str = ""

    ativos_buffer = [{"nome": a.nome, "ip": a.ip, "local": a.local} for a in ativos]

    def set_novo_email(self, valor: str):
        self.novo_email_input = valor.strip()

    def adicionar_email(self):
        if self.novo_email_input and self.novo_email_input not in self.emails:
            self.emails.append(self.novo_email_input)
            self.novo_email_input = ""
            self.salvar_emails()

    def remover_email(self, email_alvo: str):
        if email_alvo in self.emails:
            self.emails.remove(email_alvo)
            self.salvar_emails()

    def salvar_emails(self):
        with open('Echo/emails.json', 'w', encoding='utf-8') as f:
            json.dump(self.emails, f)

    # Inputs temporários do modal
    novo_ativo_nome: str = ""
    novo_ativo_ip: str = ""
    novo_ativo_local: str = ""

    def set_novo_ativo_nome(self, valor: str):
        self.novo_ativo_nome = valor

    def set_novo_ativo_ip(self, valor: str):
        self.novo_ativo_ip = valor

    def set_novo_ativo_local(self, valor: str):
        self.novo_ativo_local = valor
        
    def adicionar_ativo_buffer(self):
        """Adiciona à lista temporária (não salva no json ainda)"""
        if self.novo_ativo_nome and self.novo_ativo_ip and self.novo_ativo_local:
            self.ativos_buffer.append({
                "nome": self.novo_ativo_nome.strip(),
                "ip": self.novo_ativo_ip.strip(),
                "local": self.novo_ativo_local.strip()
            })
            # Limpa os inputs
            self.novo_ativo_nome = ""
            self.novo_ativo_ip = ""
            self.novo_ativo_local = ""
            
    def remover_ativo_buffer(self, ip_alvo: str):
        """Remove da lista temporária com base no IP"""
        self.ativos_buffer = [a for a in self.ativos_buffer if a["ip"] != ip_alvo]
        
    def salvar_ativos(self):
        """Salva as modificações, reescreve o json e atualiza a interface"""
        # 1. Salva no arquivo JSON
        with open('Echo/ips.json', 'w', encoding='utf-8') as f:
            json.dump(self.ativos_buffer, f)
            
        # 2. Recria a lista oficial de Ativos da interface (limpando o histórico)
        novos_ativos = []
        for item in self.ativos_buffer:
            novos_ativos.append(AtivoRede(
                nome=item['nome'], 
                ip=item['ip'], 
                local=item['local'],
                status="Aguardando...",
                latencia=0.0,
                latencia_total=0.0,
                qnt_pings=0,
                historico=[]
            ))
        
        # 3. Atualiza os cards da interface
        self.ativos = novos_ativos

    # Loop de ping para monitoramento contínuo
    @rx.event(background=True)
    async def loop_relatorio_diario(self):
        while True:
            await asyncio.sleep(FREQUENCIA_EMAILS)
            
            async with self:
                if not self.monitorando or not self.ativos:
                    continue
                
                linhas_tabela = ""
                ativos_zerados = []
                
                for ativo in self.ativos:
                    # 1. O Cálculo da Média Segura (evitando divisão por zero)
                    if ativo.qnt_pings > 0:
                        media = ativo.latencia_total / ativo.qnt_pings
                    else:
                        media = 0.0
                    
                    # 2. Monta a linha do HTML
                    linhas_tabela += f"""
                    <tr style="text-align: center;">
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: left;"><b>{ativo.nome}</b></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{ativo.ip}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{ativo.qnt_pings}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{media:.0f} ms</td>
                    </tr>
                    """
                    
                    # 3. Prepara o ativo zerado para o novo dia
                    ativo_limpo = AtivoRede(
                        nome=ativo.nome,
                        ip=ativo.ip,
                        local=ativo.local,
                        status=ativo.status,
                        latencia=ativo.latencia,
                        historico=ativo.historico,
                        latencia_total=0.0,
                        qnt_pings=0
                    )
                    ativos_zerados.append(ativo_limpo)

                # Atualiza a interface com os ativos zerados para o próximo dia
                self.ativos = ativos_zerados
                
                # Monta a estrutura do email
                html_final = f"""
                <html>
                  <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2 style="color: #0056b3;">Fechamento Diário - Echo</h2>
                    <p>Abaixo estão as médias de latência consolidadas das últimas 24 horas.</p>
                    <table style="border-collapse: collapse; width: 100%; max-width: 700px;">
                        <tr style="background-color: #f2f2f2;">
                            <th style="padding: 8px; border: 1px solid #ddd;">Equipamento</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">IP</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Pings Bem-Sucedidos</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Média de Latência</th>
                        </tr>
                        {linhas_tabela}
                    </table>
                  </body>
                </html>
                """
                
            # Dispara o email (fora do bloco async with self para não congelar o painel)
            disparar_relatorio(html_final, self.emails)

    @rx.event(background=True)
    async def loop_monitoramento(self):
        # 1. Cria um RG único para este loop
        async with self:
            if self.monitorando:
                return
            self.monitorando = True
            self.ciclo_atual += 1
            meu_ciclo = self.ciclo_atual 
        
        while True:
            # 2. Verifica se foi pausado OU se outro loop tomou o lugar
            async with self:
                if not self.monitorando or self.ciclo_atual != meu_ciclo:
                    break
                ativos_atuais = self.ativos.copy()
            
            ativos_atualizados = []
            hora_atual = datetime.now().strftime("%H:%M:%S")
            
            for ativo in ativos_atuais:
                # 3. USANDO ASYNC_PING PARA NÃO TRAVAR O SISTEMA
                resultado = await icmplib.async_ping(ativo.ip, count=1, timeout=2)
                latencia_ms = resultado.avg_rtt
                
                novo_status = "Aguardando..."
                nova_latencia = 0.0
                
                # Estados de latência
                if not resultado.is_alive: # async_ping verifica se está vivo assim
                    novo_status = "Offline"
                    nova_latencia = 0.0
                elif latencia_ms > LIMITE_LATENCIA_MS:
                    novo_status = "Lento"
                    nova_latencia = latencia_ms
                else:
                    novo_status = "Online"
                    nova_latencia = latencia_ms
                
                novo_historico = ativo.historico.copy()
                novo_historico.append({"hora": hora_atual, "latencia": nova_latencia})
                
                if len(novo_historico) > 15:
                    novo_historico.pop(0)
                
                novo_ativo = AtivoRede(
                    nome=ativo.nome,
                    ip=ativo.ip,
                    local=ativo.local,
                    status=novo_status,
                    latencia=nova_latencia,
                    latencia_total=ativo.latencia_total + nova_latencia,
                    qnt_pings=ativo.qnt_pings + 1,
                    historico=novo_historico
                )
                
                ativos_atualizados.append(novo_ativo)
            
            # 4. Segunda verificação de segurança antes de atualizar a tela
            async with self:
                if not self.monitorando or self.ciclo_atual != meu_ciclo:
                    break
                self.ativos = ativos_atualizados
            
            await asyncio.sleep(INTERVALO_SEGUNDOS)
    
    # Pausar monitoramento e reiniciar ativos para estado inicial   
    def parar_monitoramento(self):
        self.monitorando = False
        self.ciclo_atual += 1

        ativos_resetados = []
        for ativo in self.ativos:
            ativo_limpo = AtivoRede(
                nome=ativo.nome,
                ip=ativo.ip,
                local=ativo.local,
                status="Aguardando...",
                latencia=0.0,
                historico=[]
            )
            ativos_resetados.append(ativo_limpo)
        self.ativos = ativos_resetados

# --- CARD ---
def renderizar_card(ativo: AtivoRede):
    cor_borda = rx.cond(ativo.status == "Online", "green", 
                rx.cond(ativo.status == "Lento", "orange", "red"))
    
    # Configuração do gráfico de barras de latência
    grafico = rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key="latencia",
            is_animation_active=True,
            fill=rx.color(cor_borda,8),
            stroke=rx.color(cor_borda, 10),
            stroke_width=2,
            radius=[4, 4, 0, 0]
        ),
        rx.recharts.x_axis(data_key="hora", hide=False),
        rx.recharts.y_axis(hide=False, width=40, domain=[0, LIMITE_LATENCIA_MS]),
        rx.recharts.graphing_tooltip(),
        data=ativo.historico,
        height=160,
        width="100%",
    )
    
    # Configuração do card de ativos
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading(ativo.nome, size="4"),
                    rx.flex(
                        rx.text(f"IP: {ativo.ip}", color="gray"),
                        rx.text(f"Local: {ativo.local}", color="gray", size="1"),
                        direction="column",
                    ),
                    align_items="start",
                    spacing="0",
                ),
                rx.spacer(),
                rx.vstack(
                    rx.badge(ativo.status, color_scheme=cor_borda),
                    rx.cond(
                        ativo.status != "Offline",
                        rx.text(f"{ativo.latencia:.0f} ms", font_weight="bold", size="4"),
                    ),
                    align_items="end",
                ),
                width="100%"
            ),
            rx.divider(margin_y="0.5em"),
            grafico,
            width="100%"
        ),
        border_top=f"4px solid var(--{cor_borda}-9)",
        width="100%",
    )

# --- PÁGINA DO PAINEL ---
def index() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Titulo do painel
            rx.heading("ECHO", size="9"),
            
            # Botões de controle
            rx.hstack(
                rx.button(
                    rx.icon("play"), 
                    on_click=EchoState.loop_monitoramento, 
                    color_scheme="green",
                    disabled=EchoState.monitorando,
                    variant="soft"
                ),
                rx.button(
                    rx.icon("pause"), 
                    on_click=EchoState.parar_monitoramento, 
                    color_scheme="red",
                    disabled=~EchoState.monitorando,
                    variant="soft"
                ),
                
                # Configurações gerais
                rx.dialog.root(
                    rx.dialog.trigger(rx.button(rx.icon("settings"), color_scheme="blue", variant="soft"), disabled=EchoState.monitorando),

                    rx.dialog.content(
                        rx.tabs.root(
                            rx.tabs.list(
                                rx.tabs.trigger("Gerenciar Emails", value="emails", color_scheme="orange"),
                                rx.tabs.trigger("Gerenciar Ativos", value="ativos", color_scheme="blue"),
                            ),

                            # --- Configurações de Emails ---
                            rx.tabs.content(
                                rx.dialog.title("Cadastro de Emails", padding_top="1em"),
                                rx.dialog.description("Gerencie os emails que receberão os alertas de status dos ativos."),

                                rx.divider(margin_y="1em"),

                                rx.vstack(
                                    # Lista de emails atuais
                                    rx.foreach(
                                        EchoState.emails, 
                                        lambda email: rx.card(
                                            rx.hstack(
                                                rx.text(email, width="100%"),
                                                rx.button(rx.icon("trash"), on_click=EchoState.remover_email(email), color_scheme="red", variant="ghost"),
                                                width="100%",
                                                align_items="center",
                                            ),
                                        )
                                    ),
                                    rx.divider(margin_y="1em"),

                                    rx.card(
                                        rx.text("Adicionar novo email:", size="3", font_weight="bold", padding_bottom="0.5em"),
                                        rx.hstack(
                                            rx.input(
                                                placeholder="novo@dominio.com", 
                                                on_change=EchoState.set_novo_email, 
                                                value=EchoState.novo_email_input,
                                                width="100%"
                                            ),
                                            rx.button(rx.icon("plus"), on_click=EchoState.adicionar_email, color_scheme="green"),
                                            width="100%"
                                        ),
                                    ),
                                    align_items="stretch",
                                    width="100%",
                                ),

                                value="emails"
                            ),

                            # --- Configurações de Ativos ---
                            rx.tabs.content(
                                rx.dialog.title("Gerenciar Ativos de Rede", padding_top="1em"),
                                rx.dialog.description("Adicione ou remova dispositivos. O monitoramento será pausado durante a edição."),

                                rx.divider(margin_y="1em"),

                                rx.vstack(
                                    # Lista de ativos no buffer
                                    rx.foreach(
                                        EchoState.ativos_buffer, 
                                        lambda ativo: rx.card(
                                            rx.hstack(
                                                rx.vstack(
                                                    rx.text(ativo["nome"], font_weight="bold"),
                                                    rx.text(f"{ativo['ip']} - {ativo['local']}", size="1", color="gray"),
                                                    spacing="0",
                                                    align_items="start",
                                                    width="100%"
                                                ),

                                                rx.button(rx.icon("trash"), on_click=EchoState.remover_ativo_buffer(ativo["ip"]), color_scheme="red", variant="ghost"),

                                                width="100%",
                                                align_items="center",
                                            ),

                                            border_top="4px solid var(--blue-7)",
                                        )
                                    ),

                                    rx.divider(margin_y="1em"),
                                    rx.text("Adicionar Novo Ativo", font_weight="bold"),
                                    # Inputs para novo ativo
                                    rx.hstack(
                                        rx.input(placeholder="Nome", on_change=EchoState.set_novo_ativo_nome,value=EchoState.novo_ativo_nome),
                                        rx.input(placeholder="IP", on_change=EchoState.set_novo_ativo_ip,value=EchoState.novo_ativo_ip),
                                        rx.input(placeholder="Local", on_change=EchoState.set_novo_ativo_local,value=EchoState.novo_ativo_local),
                                        rx.button(rx.icon("plus"), on_click=EchoState.adicionar_ativo_buffer, color_scheme="green"),
                                        width="100%"
                                    ),
                                    align_items="stretch",
                                    width="100%",
                                    padding_bottom="1em",
                                ),
                                # Botões de Ação do Modal
                                rx.button("Salvar e Atualizar", on_click=EchoState.salvar_ativos, color_scheme="blue",justify_self="end", width="100%"),

                                value="ativos"
                            ),
                        ),

                        width="30%",
                    ),
                ),
            ),
            
            rx.divider(margin_y="1em"),
            
            # Cards de ativos
            rx.grid(
                rx.foreach(EchoState.ativos, renderizar_card),
                columns="4",
                spacing="4",
                width="100%"
            ),
            padding="2em",
            align_items="center",
        ),

        width="100%",
        height="100%",
    ),

# --- CONFIGURAÇÃO DO APP ---
app = rx.App()
app.add_page(index, title="Painel Echo")