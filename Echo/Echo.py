from datetime import datetime
import reflex as rx
import subprocess
import platform
import re
import asyncio
import json
import os
import pydantic

INTERVALO_SEGUNDOS = 10
LIMITE_LATENCIA_MS = 100.0
PINGS_MAXIMOS = 12

class AtivoRede(pydantic.BaseModel):
    nome: str
    ip: str
    local: str
    latencia: float = 0.0
    status: str = "Aguardando..."
    historico: list[dict[str, str | float]] = []

def obter_latencia(ip: str) -> float | None:
    parametro = '-n' if platform.system().lower() == 'windows' else '-c'
    comando = ['ping', parametro, '1', ip]
    
    try:
        resultado = subprocess.run(comando, stdout=subprocess.PIPE, text=True, timeout=5)
        match = re.search(r'(?:time|tempo)[=<]([\d.]+)', resultado.stdout, re.IGNORECASE)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None

def carregar_ativos():
    if os.path.exists('Echo\ips.json'):
        print("Carregando ativos de ips.json...")
        with open('Echo\ips.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
            return [AtivoRede(nome=item['nome'], ip=item['ip'], local=item['local']) for item in dados]
    
    return [AtivoRede(nome="Configurar ips.json", ip="127.0.0.1", local="N/A")]

class EchoState(rx.State):
    ativos: list[AtivoRede] = carregar_ativos()
    monitorando: bool = False
    
    @rx.event(background=True)
    async def loop_monitoramento(self):
        async with self:
            if self.monitorando:
                return
            self.monitorando = True
        
        while True:
            async with self:
                if not self.monitorando:
                    break
                ativos_atuais = self.ativos.copy()
            
            ativos_atualizados = []
            hora_atual = datetime.now().strftime("%H:%M:%S")
            
            for ativo in ativos_atuais:
                latencia_ms = obter_latencia(ativo.ip)
                
                novo_status = "Aguardando..."
                nova_latencia = 0.0
                
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
            
            async with self:
                if not self.monitorando:
                    break
                self.ativos = ativos_atualizados
            
            await asyncio.sleep(INTERVALO_SEGUNDOS)
        
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

def renderizar_card(ativo: AtivoRede):
    cor_borda = rx.cond(ativo.status == "Online", "green", 
                rx.cond(ativo.status == "Lento", "orange", "red"))
    
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
        height=200,
        width="100%",
    )
    
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

def index() -> rx.Component:
    return rx.box( 
        rx.vstack(
            rx.heading("ECHO.", size="8", margin_bottom="1em"),
            
            rx.hstack(
                rx.button(
                    "Iniciar Monitoramento", 
                    on_click=EchoState.loop_monitoramento, 
                    color_scheme="green",
                    disabled=EchoState.monitorando
                ),
                rx.button(
                    "Pausar", 
                    on_click=EchoState.parar_monitoramento, 
                    color_scheme="red",
                    disabled=~EchoState.monitorando
                ),
            ),
            
            rx.divider(margin_y="1em"),
            
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

app = rx.App()
app.add_page(index, title="Painel Echo")