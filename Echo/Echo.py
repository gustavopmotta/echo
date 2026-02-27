import reflex as rx
import subprocess
import platform
import re
import asyncio

# === Etapa 1: Configuracoes Iniciais ===
# Define o tempo de espera entre os testes e o limite para considerar a rede lenta.
INTERVALO_SEGUNDOS = 300
LIMITE_LATENCIA_MS = 100.0

# === Etapa 2: Modelagem de Dados ===
# Cria a estrutura de variaveis que cada equipamento tera na interface.
class AtivoRede(rx.Base):
    nome: str
    ip: str
    latencia: float = 0.0
    status: str = "Aguardando..."

# === Etapa 3: Funcoes de Monitoramento ===
# Executa o comando ping no sistema operacional e extrai o tempo de resposta.
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

# === Etapa 4: Estado e Logica de Fundo ===
# Gerencia os dados em tempo real e mantem o loop de testes rodando sem travar a tela.
class EchoState(rx.State):
    ativos: list[AtivoRede] = [
        AtivoRede(nome="Roteador Local", ip="192.168.0.1"), 
        AtivoRede(nome="Meu PC", ip="192.168.0.247"), 
        AtivoRede(nome="Internet", ip="8.8.8.8"), 
    ]
    monitorando: bool = False

    async def loop_monitoramento(self):
        # Inicia o monitoramento e envia a primeira atualizacao para a interface
        self.monitorando = True
        yield
        
        while self.monitorando:
            ativos_atualizados = []
            
            for ativo in self.ativos:
                latencia_ms = obter_latencia(ativo.ip)
                
                if latencia_ms is None:
                    ativo.status = "Offline"
                    ativo.latencia = 0.0
                elif latencia_ms > LIMITE_LATENCIA_MS:
                    ativo.status = "Lento"
                    ativo.latencia = latencia_ms
                else:
                    ativo.status = "Online"
                    ativo.latencia = latencia_ms
                
                ativos_atualizados.append(ativo)
            
            self.ativos = ativos_atualizados
            
            # O comando yield empurra os dados atualizados para o navegador
            yield
            
            # Pausa a execucao pelo intervalo definido antes do proximo teste
            await asyncio.sleep(INTERVALO_SEGUNDOS)

    def parar_monitoramento(self):
        self.monitorando = False

# === Etapa 5: Interface Grafica ===
# Constroi o visual da aplicacao usando componentes do Reflex.
def renderizar_card(ativo: AtivoRede):
    cor_borda = rx.cond(ativo.status == "Online", "green", 
                rx.cond(ativo.status == "Lento", "orange", "red"))
    
    return rx.card(
        rx.vstack(
            rx.heading(ativo.nome, size="4"),
            rx.text(f"IP: {ativo.ip}", color="gray"),
            rx.hstack(
                rx.badge(ativo.status, color_scheme=cor_borda),
                rx.cond(
                    ativo.status != "Offline",
                    rx.text(f"{ativo.latencia} ms", font_weight="bold"),
                    rx.text("Falha de conexao")
                )
            ),
        ),
        border_top=f"4px solid var(--{cor_borda}-9)",
        width="100%"
    )

def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Painel Echo", size="8", margin_bottom="1em"),
            
            rx.hstack(
                rx.button(
                    "Iniciar Monitoramento", 
                    on_click=EchoState.loop_monitoramento, 
                    color_scheme="blue",
                    disabled=EchoState.monitorando
                ),
                rx.button(
                    "Pausar", 
                    on_click=EchoState.parar_monitoramento, 
                    color_scheme="red",
                    disabled=~EchoState.monitorando
                ),
            ),
            
            rx.divider(margin_y="2em"),
            
            rx.grid(
                rx.foreach(EchoState.ativos, renderizar_card),
                columns="3",
                spacing="4",
                width="100%"
            ),
            padding="2em",
            align_items="center"
        )
    )

app = rx.App()
app.add_page(index, title="Echo - Monitoramento de Rede")