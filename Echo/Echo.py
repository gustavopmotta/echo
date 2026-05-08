import reflex as rx
from .states import AppState, AuthState, ConfigState, MonitoramentoState, UserManagementState, AtivoRede, User

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

# No Echo.py
def tela_login():
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Bem-vindo ao Echo!", size="7"),
                rx.text("Faça login com sua conta", size="3", text_align="center", color="gray", margin_bottom="1em"),

                rx.vstack(
                    rx.text("Email", size="3", weight="medium", width="100%", text_align="left"),
                    rx.input(
                        rx.input.slot(rx.icon("user")),
                        placeholder="usuário@echo.com", 
                        on_change=lambda v: AuthState.set_novo_attr("usuario_input", v),
                        value=AuthState.usuario_input,
                        width="100%",
                        size="3"
                    ),
                    width="100%",
                    justify="start",
                    spacing="1"
                ),

                rx.vstack(
                    rx.text("Senha", size="3", weight="medium", width="100%", text_align="left"),
                    rx.input(
                        rx.input.slot(rx.icon("lock")),
                        type="password", 
                        placeholder="**********",
                        on_change=lambda v: AuthState.set_novo_attr("senha_input", v),
                        value=AuthState.senha_input,
                        width="100%",
                        size="3"
                    ),
                    width="100%",
                    justify="start",
                    spacing="1"
                ),
                rx.button("Fazer Login", on_click=AuthState.tentar_login, width="100%", color_scheme="purple", size="3", weight="bold"),

                align_items="center",
                spacing="3",
                width="100%"
            ),
            size="4",
            width="100%",
            max_width="24em",
        ),
        height="100vh"
    )

# --- TELA DE SETUP INICIAL ---
def tela_setup_inicial():
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Bem-vindo ao Echo!", size="7"),
                rx.text("Crie o usuário Administrador para inicializar o sistema.", size="1", text_align="center", color="gray", margin_bottom="1em"),
                
                rx.input(
                    rx.input.slot(rx.icon("user_star")),
                    placeholder="Nome do Administrador", 
                    on_change=lambda v: AuthState.set_novo_attr("setup_username", v),
                    value=AuthState.setup_username,
                    width="100%"
                ),
                rx.input(
                    rx.input.slot(rx.icon("lock")),
                    type="password",
                    placeholder="Senha",
                    on_change=lambda v: AuthState.set_novo_attr("setup_password", v),
                    value=AuthState.setup_password,
                    width="100%"
                ),
                rx.input(
                    rx.input.slot(rx.icon("lock")),
                    type="password", 
                    placeholder="Confirme a Senha",
                    on_change=lambda v: AuthState.set_novo_attr("setup_confirmacao", v),
                    value=AuthState.setup_confirmacao,
                    width="100%"
                ),
                
                rx.button("Criar Administrador", on_click=AuthState.registrar_primeiro_admin, width="100%", color_scheme="purple", size="3", weight="bold"),
                
                align_items="center",
                spacing="4"
            ),
            size="4",
            width="100%",
            max_width="24em",
        ),
        height="100vh"
    )

# --- PÁGINA DO PAINEL ---
def index() -> rx.Component:
    return rx.box(
        rx.color_mode.button(position="top-right"),
        
        rx.vstack(
            # Titulo do painel
            rx.heading("ECHO", size="9"),
            
            # Botões de controle
            rx.hstack(
                rx.cond(
                    ~MonitoramentoState.monitorando,
                    rx.button(
                        rx.icon("play"),
                        "Iniciar Monitoramento", 
                        on_click=MonitoramentoState.loop_monitoramento, 
                        color_scheme="green",
                        variant="solid"
                    ),
                    rx.button(
                        rx.icon("pause"),
                        "Parar Monitoramento", 
                        on_click=MonitoramentoState.parar_monitoramento, 
                        color_scheme="red",
                        variant="solid"
                    ),
                ),
                
                # Configurações gerais
                rx.dialog.root(
                    rx.dialog.trigger(rx.button(rx.icon("settings"), "Configurações", color_scheme="blue", variant="surface", disabled=MonitoramentoState.monitorando)),

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
                                                rx.icon_button(rx.icon("trash"), on_click=ConfigState.remover_email(email), color_scheme="red", variant="ghost"),
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
                                            rx.icon_button(rx.icon("plus"), on_click=ConfigState.adicionar_email, color_scheme="green"),
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

                                                rx.icon_button(rx.icon("trash"), on_click=MonitoramentoState.remover_ativo_buffer(ativo["ip"]), color_scheme="red", variant="ghost"),

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
                                            
                                            rx.icon_button(rx.icon("plus"), on_click=MonitoramentoState.adicionar_ativo_buffer, color_scheme="green"),

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

                            default_value="config"
                        ),

                        width="35%",
                    ),
                ),

                # Configurações de usuários
                rx.dialog.root(
                    rx.dialog.trigger(rx.button(rx.icon("users"), "Usuários", color_scheme="orange", variant="surface")),

                    rx.dialog.content(
                        rx.dialog.title("Gerenciar Usuários", padding_top="1em"),
                        rx.dialog.description("Crie ou remova credenciais de acesso ao painel."),
                        rx.divider(margin_y="1em"),
                    
                        # Lista de usuários existentes
                        rx.scroll_area(
                            rx.vstack(
                                rx.foreach(
                                    UserManagementState.lista_usuarios,
                                    lambda u: rx.card(
                                        rx.hstack(
                                            rx.vstack(
                                                rx.text(u["username"], font_weight="bold"),
                                                rx.hstack(
                                                    rx.badge(
                                                        rx.icon(rx.cond(u["role"] == "admin", "crown", "database"), size=16, stroke_width=2),
                                                        rx.cond(u["role"] == "admin", "Admin", "Operador"),
                                                        color_scheme=rx.cond(u["role"] == "admin", "yellow", "blue"),
                                                        radius="full",
                                                    ),
                                                    rx.cond(UserManagementState.usuario_logado == u["username"],
                                                        rx.badge(rx.icon("user", size=16), "Usuário Atual", color_scheme="green", radius="full")
                                                    ),
                                                ),
                                                spacing="1",
                                                align_items="start"
                                            ),
                                            rx.spacer(),
                                            rx.cond(
                                                (UserManagementState.usuario_logado == u["username"]) | (UserManagementState.role_logado == "admin"),
                                                rx.hstack(
                                                    # Botão da chave abre o formulário
                                                    rx.icon_button(rx.icon("key"), on_click=UserManagementState.iniciar_edicao_senha(u["username"]), color_scheme="blue", variant="outline"),
                                                    rx.icon_button(rx.icon("trash"), on_click=UserManagementState.deletar_usuario(u["username"]), color_scheme="red", variant="outline"),
                                                ),
                                            ),
                                            width="100%", align_items="center"
                                        ),
                                        width="100%"
                                    )
                                ),
                                width="100%",
                                padding_bottom="1em"
                            ),
                            type="scroll", style={"max_height": "30vh"}
                        ),
                    
                        rx.divider(margin_y="1em"),
                    
                        # Formulário de Adição
                        rx.card(
                            rx.text("Criar Novo Usuário", font_weight="bold", margin_bottom="1em"),
                            rx.vstack(
                                rx.input(
                                    rx.input.slot(rx.icon("mail")),
                                    placeholder="Email", 
                                    value=UserManagementState.form_username, 
                                    on_change=lambda v: UserManagementState.set_novo_attr("form_username", v),
                                    width="100%"
                                ),
                                rx.input(
                                    rx.input.slot(rx.icon("lock")),
                                    placeholder="Senha", 
                                    type="password", 
                                    value=UserManagementState.form_password, 
                                    on_change=lambda v: UserManagementState.set_novo_attr("form_password", v),
                                    width="100%"
                                ),
                                rx.cond(UserManagementState.role_logado == "admin",
                                    rx.checkbox(
                                        "Administrador", 
                                        checked=UserManagementState.form_is_admin, 
                                        on_change=lambda v: UserManagementState.set_novo_attr("form_is_admin", v)
                                    ),
                                ),
                                rx.button(
                                    rx.icon("user-plus"), 
                                    "Adicionar Usuário", 
                                    on_click=UserManagementState.adicionar_usuario, 
                                    color_scheme="green", 
                                    width="100%"
                                ),

                                align_items="start", width="100%", spacing="3"
                            ),
                            width="100%",
                            variant="surface"
                        ),
                        width="30%",
                    ),
                ),
            
                # Logoff
                rx.icon_button(rx.icon("door_open"), on_click=AuthState.fazer_logout, color_scheme="red", variant="surface"),
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
app.add_page(tela_setup_inicial, route="/setup", title="Configuração Inicial - Echo")
app.add_page(tela_login, route="/login", title="Login - Echo")
app.add_page(index, title="Painel - Echo", on_load=[
    AuthState.verificar_acesso,
    MonitoramentoState.on_load, 
    MonitoramentoState.loop_relatorio,
    UserManagementState.carregar_usuarios,
])