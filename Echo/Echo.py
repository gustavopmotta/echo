from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv
import reflex as rx
import icmplib
import platform
import re
import asyncio
import json
import os
import pydantic
import smtplib

# Carregando arquivo de acesso do email
load_dotenv('Echo/email.env')

# Configurações do Brevo
SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_LOGIN = os.environ.get("BREVO_SMTP_LOGIN")
SMTP_PASSWORD = os.environ.get("BREVO_SMTP_PASSWORD")

# Configurações
INTERVALO_SEGUNDOS = 10
LIMITE_LATENCIA_MS = 100.0
PINGS_MAXIMOS = 12

# Estrutura do ativo de rede
class AtivoRede(pydantic.BaseModel):
    nome: str
    ip: str
    local: str
    latencia: float = 0.0
    status: str = "Aguardando..."
    historico: list[dict[str, str | float]] = []

# Processamento de ativos a partir do arquivo ips.json
def carregar_ativos():
    if os.path.exists('Echo/ips.json'):
        print("Carregando ativos de ips.json...")
        with open('Echo/ips.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
            return [AtivoRede(nome=item['nome'], ip=item['ip'], local=item['local']) for item in dados]
    
    return [AtivoRede(nome="Configurar ips.json", ip="127.0.0.1", local="N/A")]

# --- ESTADO DE MONITORAMENTO ---
class EchoState(rx.State):
    # Configurações iniciais
    ativos: list[AtivoRede] = carregar_ativos()
    monitorando: bool = False
    
    # Loop de ping para monitoramento contínuo
    @rx.event(background=True)
    async def loop_monitoramento(self):
        # Verificação inicial para evitar múltiplas execuções simultâneas
        async with self:
            if self.monitorando:
                return
            self.monitorando = True
        
        while True:
            # Cópia dos ativos para evitar bloqueios durante a atualização
            async with self:
                if not self.monitorando:
                    break
                ativos_atuais = self.ativos.copy()
            
            ativos_atualizados = []
            hora_atual = datetime.now().strftime("%H:%M:%S")
            
            # Criação de novos ativos com status e latência atualizados
            for ativo in ativos_atuais:
                latencia_ms = icmplib.ping(ativo.ip, count=1, timeout=2).avg_rtt
                
                novo_status = "Aguardando..."
                nova_latencia = 0.0
                
                # Estados de latência
                if latencia_ms is None:
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
                    historico=novo_historico
                )
                
                ativos_atualizados.append(novo_ativo)
            
            # Atualização dos ativos na interface
            async with self:
                if not self.monitorando:
                    break
                self.ativos = ativos_atualizados
            
            await asyncio.sleep(INTERVALO_SEGUNDOS)
    
    # Pausar monitoramento e reiniciar ativos para estado inicial   
    def parar_monitoramento(self):
        self.monitorando = False
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
                        spacing="0",
                        direction="column",
                    ),
                    align_items="start"
                ),
                rx.spacer(),
                rx.vstack(
                    rx.badge(ativo.status, color_scheme=cor_borda),
                    rx.cond(
                        ativo.status != "Offline",
                        rx.text(f"{ativo.latencia} ms", font_weight="bold", size="4"),
                    ),
                    align_items="end"
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
            rx.heading("ECHO.", size="8", margin_bottom="1em"),
            
            # Botões de controle
            rx.hstack(
                rx.button(
                    rx.icon("play"), 
                    on_click=EchoState.loop_monitoramento, 
                    color_scheme="green",
                    disabled=EchoState.monitorando
                ),
                rx.button(
                    rx.icon("pause"), 
                    on_click=EchoState.parar_monitoramento, 
                    color_scheme="red",
                    disabled=~EchoState.monitorando
                ),
                rx.button(
                    rx.icon("pencil")
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
    )

# --- CONFIGURAÇÃO DO APP ---
app = rx.App()
app.add_page(index, title="Painel Echo")