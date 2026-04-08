import reflex as rx
from .states import AppState, ConfigState, MonitoramentoState, AtivoRede

# --- CARD ---
def renderizar_card(ativo: AtivoRede):
    cor_borda = rx.cond(ativo.status == "Online", "green", 
                rx.cond(ativo.status == "Lento", "orange", "red"))
    
    # Configuração do gráfico de barras de latência
    grafico = rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key="latencia",
            is_animation_active=True,
            fill=rx.color(cor_borda, 8),
            stroke=rx.color(cor_borda, 10),
            stroke_width=2,
            radius=[4, 4, 0, 0]
        ),
        rx.recharts.x_axis(data_key="hora", hide=False),
        # Lê o limite dinamicamente do ConfigState
        rx.recharts.y_axis(hide=False, width=40, domain=[0, ConfigState.config["limite_latencia_ms"]]),
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
                    on_click=MonitoramentoState.loop_monitoramento, 
                    color_scheme="green",
                    disabled=MonitoramentoState.monitorando,
                    variant="soft"
                ),
                rx.button(
                    rx.icon("pause"), 
                    on_click=MonitoramentoState.parar_monitoramento, 
                    color_scheme="red",
                    disabled=~MonitoramentoState.monitorando,
                    variant="soft"
                ),
                
                # Configurações gerais
                rx.dialog.root(
                    rx.dialog.trigger(rx.button(rx.icon("settings"), color_scheme="blue", variant="soft", disabled=MonitoramentoState.monitorando)),

                    rx.dialog.content(
                        rx.tabs.root(
                            rx.tabs.list(
                                rx.tabs.trigger("Configurações", value="config", color_scheme="purple"),
                                rx.tabs.trigger("Gerenciar Emails", value="emails", color_scheme="orange"),
                                rx.tabs.trigger("Gerenciar Ativos", value="ativos", color_scheme="blue"),
                            ),

                            # --- Configurações Gerais ---
                            rx.tabs.content(
                                rx.dialog.title("Configurações Gerais", padding_top="1em"),
                                rx.dialog.description("Ajuste os parâmetros do servidor e do monitoramento de rede."),
                                rx.divider(margin_y="1em"),

                                # Scroll area previne que o modal fique gigante na tela
                                rx.scroll_area(
                                    rx.callout("O sistema reiniciará ao salvar alterações", icon="info", color_scheme="blue", variant="surface"),
                                    rx.vstack(
                                        # SEÇÃO 1: SERVIDOR DE E-MAIL
                                        rx.text("Servidor de E-mail (SMTP)", weight="bold", padding_top="0.5em"),
                                        rx.grid(
                                            rx.vstack(
                                                rx.text("Servidor SMTP:", size="2"),
                                                rx.input(
                                                    value=AppState.config_buffer["smtp_server"],
                                                    on_change=lambda v: ConfigState.atualizar_buffer("smtp_server", v),
                                                    placeholder="mail.dominio.com.br"
                                                ),
                                            ),
                                            rx.vstack(
                                                rx.text("Porta SMTP:", size="2"),
                                                rx.input(
                                                    value=AppState.config_buffer["smtp_port"],
                                                    on_change=lambda v: ConfigState.atualizar_buffer("smtp_port", v),
                                                    placeholder="465"
                                                ),
                                            ),
                                            rx.vstack(
                                                rx.text("Login:", size="2"),
                                                rx.input(
                                                    value=AppState.config_buffer["smtp_login"],
                                                    on_change=lambda v: ConfigState.atualizar_buffer("smtp_login", v),
                                                    placeholder="alertas@dominio.com.br"
                                                ),
                                            ),
                                            rx.vstack(
                                                rx.text("Senha:", size="2"),
                                                rx.input(
                                                    value=AppState.config_buffer["smtp_password"],
                                                    on_change=lambda v: ConfigState.atualizar_buffer("smtp_password", v),
                                                    type="password", # Oculta os caracteres digitados
                                                    placeholder="********"
                                                ),
                                            ),
                                            columns="2",
                                            spacing="2",
                                            width="100%",
                                        ),

                                        rx.divider(margin_y=".5em"),

                                        # SEÇÃO 2: REGRAS DE MONITORAMENTO
                                        rx.text("Regras de Monitoramento", weight="bold"),
                                        rx.grid(
                                            rx.vstack(
                                                rx.text("Intervalo de Ping (segundos):", size="2"),
                                                rx.input(
                                                    value=AppState.config_buffer["intervalo_segundos"],
                                                    on_change=lambda v: ConfigState.atualizar_buffer("intervalo_segundos", v),
                                                    placeholder="10"
                                                ),
                                            ),
                                            rx.vstack(
                                                rx.text("Latência Crítica (ms):", size="2"),
                                                rx.input(
                                                    value=AppState.config_buffer["limite_latencia_ms"],
                                                    on_change=lambda v: ConfigState.atualizar_buffer("limite_latencia_ms", v),
                                                    placeholder="100"
                                                ),
                                            ),
                                            rx.vstack(
                                                rx.text("Máximo Pings no Gráfico:", size="2"),
                                                rx.input(
                                                    value=AppState.config_buffer["pings_maximos"],
                                                    on_change=lambda v: ConfigState.atualizar_buffer("pings_maximos", v),
                                                    placeholder="12"
                                                ),
                                            ),
                                            rx.vstack(
                                                rx.text("Frequência de E-mail (minutos):", size="2"),
                                                rx.input(
                                                    value=AppState.config_buffer["frequencia_emails"],
                                                    on_change=lambda v: ConfigState.atualizar_buffer("frequencia_emails", v),
                                                    placeholder="60"
                                                ),
                                            ),
                                            columns="2",
                                            spacing="2",
                                            width="100%",
                                            justify="between",
                                        ),
                                        width="100%",
                                        align_items="stretch",
                                    ),
                                    type="scroll",
                                    style={"max_height": "50vh"}, # Limita a altura para caber em telas menores
                                    padding_right="1em"
                                ),

                                rx.divider(margin_y="1em"),

                                rx.button(
                                    "Salvar Alterações", 
                                    on_click=ConfigState.salvar_configuracoes, 
                                    color_scheme="purple", 
                                    width="100%"
                                ),

                                value="config"
                            ),

                            # --- Configurações de Emails ---
                            rx.tabs.content(
                                rx.dialog.title("Cadastro de Emails", padding_top="1em"),
                                rx.dialog.description("Gerencie os emails que receberão os alertas de status dos ativos."),

                                rx.divider(margin_y="1em"),

                                rx.vstack(
                                    # Lista de emails atuais
                                    rx.foreach(
                                        ConfigState.emails, 
                                        lambda email: rx.card(
                                            rx.hstack(
                                                rx.text(email, width="100%"),
                                                rx.button(rx.icon("trash"), on_click=ConfigState.remover_email(email), color_scheme="red", variant="ghost"),
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
                                                on_change=lambda v: ConfigState.set_novo_attr("novo_email_input", v), 
                                                value=ConfigState.novo_email_input,
                                                width="100%"
                                            ),
                                            rx.button(rx.icon("plus"), on_click=ConfigState.adicionar_email, color_scheme="green"),
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
                                        MonitoramentoState.ativos_buffer, 
                                        lambda ativo: rx.card(
                                            rx.hstack(
                                                rx.vstack(
                                                    rx.text(ativo["nome"], font_weight="bold"),
                                                    rx.text(f"{ativo['ip']} - {ativo['local']}", size="1", color="gray"),
                                                    spacing="0",
                                                    align_items="start",
                                                    width="100%"
                                                ),

                                                rx.button(rx.icon("trash"), on_click=MonitoramentoState.remover_ativo_buffer(ativo["ip"]), color_scheme="red", variant="ghost"),

                                                width="100%",
                                                align_items="center",
                                            ),

                                            border_top="4px solid var(--blue-7)",
                                        )
                                    ),

                                    rx.divider(margin_y="1em"),
                                    rx.card(
                                        rx.text("Adicionar Novo Ativo:", size="3", font_weight="bold", padding_bottom="0.5em"),
                                        rx.hstack(
                                            rx.input(placeholder="Nome", on_change=lambda v: MonitoramentoState.set_novo_attr("novo_ativo_nome", v), value=MonitoramentoState.novo_ativo_nome),

                                            rx.input(placeholder="IP", on_change=lambda v: MonitoramentoState.set_novo_attr("novo_ativo_ip", v), value=MonitoramentoState.novo_ativo_ip),

                                            rx.input(placeholder="Local", on_change=lambda v: MonitoramentoState.set_novo_attr("novo_ativo_local", v), value=MonitoramentoState.novo_ativo_local),
                                            
                                            rx.button(rx.icon("plus"), on_click=MonitoramentoState.adicionar_ativo_buffer, color_scheme="green"),

                                            width="100%"
                                        ),
                                    ),
                                    align_items="stretch",
                                    width="100%",
                                    padding_bottom="1em",
                                ),
                                # Botões de Ação do Modal
                                rx.button("Salvar e Atualizar", on_click=MonitoramentoState.salvar_ativos, color_scheme="blue",justify_self="end", width="100%"),

                                value="ativos"
                            ),
                            default_value="emails"
                        ),

                        width="35%",
                    ),
                ),
            ),
            
            rx.divider(margin_y="1em"),
            
            # Cards de ativos
            rx.grid(
                rx.foreach(MonitoramentoState.ativos, renderizar_card),
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
# Aciona o on_load e o loop de email no MonitoramentoState
app.add_page(index, title="Painel Echo", on_load=[MonitoramentoState.on_load, MonitoramentoState.loop_relatorio])