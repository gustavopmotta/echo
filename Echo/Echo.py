import reflex as rx
from .states import AppState, AuthState, ConfigState, MonitoramentoState, UserManagementState, AtivoRede, AppState

radix_colors = ['tomato', 'red', 'ruby', 'crimson', 'pink', 'plum', 'purple', 'violet', 'iris', 'indigo', 'blue', 'cyan', 'teal', 'jade', 'green', 'grass', 'brown', 'orange', 'sky', 'mint', 'lime', 'yellow', 'amber', 'gold', 'bronze', 'gray']

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
                    rx.hstack(
                        rx.heading(ativo.nome, size="3"),
                        rx.badge(ativo.grupo, color_scheme=ativo.cor_grupo, variant="surface"),
                        spacing="1",
                    ),
                    
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
                    rx.badge(rx.icon(rx.cond(ativo.status == "Online", "signal", rx.cond(ativo.status == "Lento", "signal_low", "x")) ,size=16), ativo.status, color_scheme=cor_borda),
                    
                    rx.cond(
                        ativo.status != "Offline",
                        rx.text(f"{ativo.latencia:.0f} ms", font_weight="bold", size="4"),
                    ),
                    align_items="end",
                ),
                align_items="top",
                width="100%"
            ),
            rx.divider(margin_y="0.5em"),
            grafico,
            width="100%"
        ),
        border_top=f"4px solid var(--{cor_borda}-9)",
        width="100%",
    )

# --- TELA DE LOGIN ---
def tela_login() -> rx.Component:
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
                        on_change=AuthState.set_usuario_input,
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
                        on_change=AuthState.set_senha_input,
                        value=AuthState.senha_input,
                        width="100%",
                        size="3"
                    ),
                    width="100%",
                    justify="start",
                    spacing="1"
                ),
                rx.button("Fazer Login", on_click=AuthState.tentar_login, width="100%", color_scheme="blue", size="3", weight="bold"),

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
def tela_setup_inicial() -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Bem-vindo ao Echo!", size="7"),
                rx.text("Crie o usuário Administrador para inicializar o sistema.", size="1", text_align="center", color="gray", margin_bottom="1em"),
                
                rx.input(
                    rx.input.slot(rx.icon("user_star")),
                    placeholder="Nome do Administrador", 
                    on_change=AuthState.set_setup_username,
                    value=AuthState.setup_username,
                    width="100%"
                ),
                rx.input(
                    rx.input.slot(rx.icon("lock")),
                    type="password",
                    placeholder="Senha",
                    on_change=AuthState.set_setup_password,
                    value=AuthState.setup_password,
                    width="100%"
                ),
                rx.input(
                    rx.input.slot(rx.icon("lock")),
                    type="password", 
                    placeholder="Confirme a Senha",
                    on_change=AuthState.set_setup_confirmacao,
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

# --- CAIXA/ABA DE CONFIGURAÇÕES GERAIS ---
def configurações_gerais() -> rx.Component:
    return rx.tabs.content(
        rx.dialog.title("Configurações Gerais", padding_top="1em"),
        rx.dialog.description("Ajuste os parâmetros do servidor e do monitoramento de rede."),
        rx.divider(margin_y="1em"),

        # Scroll area previne que o modal fique gigante na tela
        rx.scroll_area(
            rx.callout("O sistema reiniciará ao salvar alterações", icon="info", color_scheme="blue", variant="surface"),
            rx.vstack(
                # SEÇÃO 1: SERVIDOR DE E-MAIL
                rx.text("Servidor de E-mail (SMTP)", weight="bold", padding_top="0.5em"),
                rx.hstack(
                    rx.vstack(
                        rx.text("Servidor SMTP:", size="2"),
                        rx.input(
                            value=ConfigState.config_buffer["smtp_server"],
                            on_change=lambda v: ConfigState.atualizar_buffer("smtp_server", v),
                            placeholder="mail.dominio.com.br",
                            width="100%",
                            auto_complete=False
                        ),
                        spacing="1",
                        flex="1",
                    ),
                    rx.vstack(
                        rx.text("Porta SMTP:", size="2"),
                        rx.input(
                            value=ConfigState.config_buffer["smtp_port"],
                            on_change=lambda v: ConfigState.atualizar_buffer("smtp_port", v),
                            placeholder="465",
                            width="100%",
                            auto_complete=False
                        ),
                        spacing="1",
                        flex="1"
                    ),
                    spacing="2",
                    width="100%",
                ),

                rx.hstack(
                    rx.vstack(
                        rx.text("Login:", size="2"),
                        rx.input(
                            value=ConfigState.config_buffer["smtp_login"],
                            on_change=lambda v: ConfigState.atualizar_buffer("smtp_login", v),
                            placeholder="alertas@dominio.com.br",
                            width="100%",
                            auto_complete=False
                        ),
                        spacing="1",
                        flex="1"
                    ),
                    rx.vstack(
                        rx.text("Senha:", size="2"),
                        rx.input(
                            value=ConfigState.config_buffer["smtp_password"],
                            on_change=lambda v: ConfigState.atualizar_buffer("smtp_password", v),
                            type="password",
                            placeholder="********",
                            width="100%",
                            auto_complete=False
                        ),
                        spacing="1",
                        flex="1"
                    ),
                    spacing="2",
                    width="100%",
                ),

                rx.divider(margin_y=".5em"),

                # SEÇÃO 2: REGRAS DE MONITORAMENTO
                rx.text("Regras de Monitoramento", weight="bold"),
                rx.hstack(
                    rx.vstack(
                        rx.text("Intervalo de Ping (segundos):", size="2"),
                        rx.input(
                            value=ConfigState.config_buffer["intervalo_segundos"],
                            on_change=lambda v: ConfigState.atualizar_buffer("intervalo_segundos", v),
                            placeholder="10",
                            width="100%"
                        ),
                        spacing="1",
                        flex="1",
                    ),
                    rx.vstack(
                        rx.text("Latência Crítica (ms):", size="2"),
                        rx.input(
                            value=ConfigState.config_buffer["limite_latencia_ms"],
                            on_change=lambda v: ConfigState.atualizar_buffer("limite_latencia_ms", v),
                            placeholder="100",
                            width="100%"
                        ),
                        spacing="1",
                        flex="1"
                    ),
                ),
                rx.hstack(
                    rx.vstack(
                        rx.text("Máximo Pings no Gráfico:", size="2"),
                        rx.input(
                            value=ConfigState.config_buffer["pings_maximos"],
                            on_change=lambda v: ConfigState.atualizar_buffer("pings_maximos", v),
                            placeholder="12",
                            width="100%"
                        ),
                        spacing="1",
                        flex="1",
                    ),
                    rx.vstack(
                        rx.text("Frequência de E-mail (minutos):", size="2"),
                        rx.input(
                            value=ConfigState.config_buffer["frequencia_emails"],
                            on_change=lambda v: ConfigState.atualizar_buffer("frequencia_emails", v),
                            placeholder="60",
                            width="100%"
                        ),
                        spacing="1",
                        flex="1"
                    ),
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
            on_click=ConfigState.salvar_configs_env, 
            color_scheme="purple", 
            width="100%"
        ),

        value="config"
    ),

# --- CAIXA/ABA DE CONFIGURAÇÕES DE EMAILS ---
def configurações_emails() -> rx.Component:
    return rx.tabs.content(
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
                        on_change=ConfigState.set_novo_email_input, 
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

# --- CAIXA/ABA DE CONFIGURAÇÕES DE ATIVOS ---
def configurações_ativos() -> rx.Component:
    def modal_adicionar_ativo() -> rx.Component:
        return rx.alert_dialog.root(
            rx.alert_dialog.trigger(rx.button(rx.icon("plus"), "Adicionar Ativo", color_scheme="green", flex="1")),

            rx.alert_dialog.content(
                rx.alert_dialog.title("Adicionar Ativo de Rede"),
                rx.alert_dialog.description("Preencha os detalhes do dispositivo que deseja monitorar."),

                rx.divider(margin_y="1em"),

                rx.vstack(
                    rx.hstack(
                        rx.input(
                            rx.input.slot(rx.icon("tag")),
                            placeholder="Nome do Ativo", 
                            on_change=MonitoramentoState.set_novo_ativo_nome,
                            value=MonitoramentoState.novo_ativo_nome,
                            flex="1",
                        ),

                        rx.select(
                            ConfigState.nomes_dos_grupos, # Variável da lista de grupos
                            value=MonitoramentoState.novo_ativo_grupo,
                            on_change=MonitoramentoState.set_novo_ativo_grupo,
                            placeholder="Grupo",
                        ),
                        
                        width="100%",
                    ),
                    rx.hstack(
                        rx.input(
                            rx.input.slot(rx.icon("network")),
                            placeholder="Endereço IP", 
                            on_change=MonitoramentoState.set_novo_ativo_ip, 
                            value=MonitoramentoState.novo_ativo_ip,
                            width="100%"
                        ),
                        rx.input(
                            rx.input.slot(rx.icon("map_pin")),
                            placeholder="Localização", 
                            on_change=MonitoramentoState.set_novo_ativo_local, 
                            value=MonitoramentoState.novo_ativo_local,
                            width="100%"
                        ),
                    ),

                    rx.flex(
                        rx.alert_dialog.cancel(
                            rx.button(
                                "Cancelar", 
                                color_scheme="gray", 
                                variant="soft"
                            )
                        ),
                        rx.alert_dialog.action(
                            rx.button(
                                "Adicionar", 
                                on_click=MonitoramentoState.adicionar_ativo_buffer, 
                                color_scheme="green"
                            ),
                        ),

                        spacing="3",
                        justify="end",
                        width="100%",
                    ),

                    spacing="3",
                ),

                width="30%",
                open=MonitoramentoState.novo_ativo_nome != ""
            ),
        ),

    def modal_gerenciar_grupos() -> rx.Component:
        return rx.alert_dialog.root(
            rx.alert_dialog.trigger(rx.button(rx.icon("tags"), "Gerenciar Grupos", color_scheme="gray", variant="soft", flex="1")),

            rx.alert_dialog.content(
                rx.alert_dialog.title("Gerenciar Grupos de Ativos"),
                rx.alert_dialog.description("Organize seus ativos em grupos para facilitar o monitoramento."),

                rx.divider(margin_y="1em"),

                rx.scroll_area(
                    rx.vstack(
                        rx.foreach(
                            ConfigState.grupos, 
                            lambda g: rx.card(
                                rx.hstack(
                                    rx.text(g["nome"], width="100%"),
                                    rx.icon_button(rx.icon("trash"), on_click=ConfigState.remover_grupo(g["nome"]), color_scheme="red", variant="ghost"),
                                    width="100%",
                                    align_items="center",
                                ),
                                border_top=f"4px solid var(--{g["cor"]}-9)",
                                width="100%",
                            )
                        ),
                        spacing="2",
                        padding_right="0.1em",
                    ),

                    type="scroll",
                    style={"max_height": "30vh"},
                ),

                rx.divider(margin_y="1em"),

                rx.hstack(
                    rx.input(
                        rx.input.slot(rx.icon("tag")),
                        type="text",
                        placeholder="Novo Grupo",
                        value=ConfigState.novo_grupo_input,
                        on_change=ConfigState.set_novo_grupo_input,
                        flex="1",
                    ),

                    rx.select.root(
                        rx.select.trigger(placeholder="Cor destaque"),
                        rx.select.content(
                            rx.foreach(
                                    radix_colors, 
                                    lambda cor: 
                                    rx.select.item(rx.badge(cor.capitalize(), color_scheme=cor), value=cor)
                                ),
                        ),
                        default_value=ConfigState.novo_grupo_cor_input,
                        on_change=ConfigState.set_novo_grupo_cor_input
                    ),

                    rx.icon_button(rx.icon("plus"), on_click=ConfigState.adicionar_grupo, color_scheme="green"),

                    spacing="1",
                ),

                rx.alert_dialog.cancel(
                    rx.button("Sair", variant="soft", color_scheme="gray", width="100%", margin_top="1em")
                ),

                width="25%",
            ),
        )

    def modal_edicao_ativo() -> rx.Component:
        return rx.alert_dialog.root(
            rx.alert_dialog.content(
                rx.alert_dialog.title("Editar Ativo de Rede"),
                rx.alert_dialog.description("Atualize os detalhes do dispositivo."),

                rx.divider(margin_y="1em"),

                rx.vstack(
                    rx.hstack(
                        rx.input(
                                rx.input.slot(rx.icon("tag")),
                                type="text",
                                value=MonitoramentoState.edit_nome,
                                placeholder="Nome do Ativo",
                                on_change=MonitoramentoState.set_edit_nome,
                                flex="1",
                            ),

                        rx.select(
                            ConfigState.nomes_dos_grupos,
                            value=MonitoramentoState.edit_grupo,
                            placeholder="Grupo",
                            on_change=MonitoramentoState.set_edit_grupo                  
                        ),
                        width="100%",
                    ),
                    rx.hstack(
                        rx.input(
                            rx.input.slot(rx.icon("network")),
                            value=MonitoramentoState.edit_ip,
                            placeholder="Endereço IP",
                            on_change=MonitoramentoState.set_edit_ip,
                            width="100%"
                        ),
                        rx.input(
                            rx.input.slot(rx.icon("map-pin")),
                            value=MonitoramentoState.edit_local,
                            placeholder="Localização",
                            on_change=MonitoramentoState.set_edit_local,
                            width="100%"
                        ),
                        width="100%",
                    ),

                    rx.flex(
                        rx.alert_dialog.cancel(
                            rx.button("Cancelar", on_click=MonitoramentoState.cancelar_edicao_ativo,    color_scheme="gray", variant="soft")
                        ),
                        rx.alert_dialog.action(
                            rx.button("Atualizar", on_click=MonitoramentoState.salvar_edicao_ativo,     color_scheme="blue")
                        ),
                        spacing="3",
                        justify="end",
                        width="100%"
                    ),

                    spacing="3",
                ),

                width="30%",       
            ),
            open=MonitoramentoState.ip_edicao != "", 
        )

    return rx.tabs.content(
        rx.dialog.title("Gerenciar Ativos de Rede", padding_top="1em"),
        rx.dialog.description("Adicione ou remova dispositivos. O monitoramento será pausado durante a edição."),

        rx.divider(margin_y="1em"),

        rx.vstack(
            # Lista de ativos no buffer
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(
                        AppState.ativos_buffer, 
                        lambda ativo: rx.card(
                            rx.hstack(
                                rx.vstack(
                                    rx.hstack(
                                        rx.text(ativo["nome"], font_weight="bold"),
                                        rx.badge(ativo["grupo"], color_scheme=ativo["cor_grupo"], variant="surface"),

                                        align_items="center",
                                        spacing="1"
                                    ),
                                    rx.text(f"{ativo['ip']} - {ativo['local']}", size="1", color="gray"),
                                    spacing="0",
                                    align_items="start",
                                    width="100%"
                                ),

                                rx.hstack(
                                    rx.tooltip(rx.icon_button(rx.icon("pencil"), on_click=MonitoramentoState.iniciar_edicao_ativo(ativo["ip"]), color_scheme="blue", variant="soft"), content="Editar Ativo"),

                                    rx.tooltip(rx.icon_button(rx.icon("trash"), on_click=MonitoramentoState.remover_ativo_buffer(ativo["ip"]), color_scheme="red", variant="soft"), content="Remover Ativo"),
                                ),             

                                width="100%",
                                align_items="center",
                            ),

                            border_top=f"4px solid var(--{ativo['cor_grupo']}-9)",
                            width="100%",
                        )
                    ),

                    spacing="2",
                    padding_right="0.1em",
                ),

                type="scroll",
                style={"max_height": "40vh"},
                padding_right="1em",
            ),

            rx.divider(margin_y="1em"),
            
            rx.hstack(
                modal_adicionar_ativo(),

                modal_gerenciar_grupos(),

                width="100%",
                spacing="3"
            ),
            
            align_items="stretch",
            width="100%",
            padding_bottom="1em",
        ),
        # Botões de Ação do Modal
        rx.button("Salvar e Atualizar", on_click=MonitoramentoState.salvar_ativos, color_scheme="blue",justify_self="end", width="100%"),

        modal_edicao_ativo(),

        value="ativos",
    ),

# --- CAIXA DE CONFIGURAÇÕES DE USUÁRIOS ---
def configurações_usuarios() -> rx.Component:
    def modal_edicao_senha() -> rx.Component:
        return rx.alert_dialog.root(
            rx.alert_dialog.content(
                rx.alert_dialog.title("Alterar Senha"),
                rx.alert_dialog.description(
                    "Digite a nova senha para o usuário: ",
                    rx.text(UserManagementState.usuario_edicao, weight="bold", as_="span"),
                    "."
                ),

                rx.vstack(
                    rx.input(
                        rx.input.slot(rx.icon("lock", color="gray")),
                        placeholder="Nova senha",
                        type="password",
                        value=UserManagementState.nova_senha_input,
                        on_change=UserManagementState.set_nova_senha_input,
                        width="100%"
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("check", color="gray")),
                        placeholder="Confirme a senha",
                        type="password",
                        value=UserManagementState.nova_senha_confirmacao,
                        on_change=UserManagementState.set_nova_senha_confirmacao,
                        width="100%"
                    ),
                    spacing="3",
                    margin_y="1em"
                ),

                rx.flex(
                    rx.alert_dialog.cancel(
                        rx.button(
                            "Cancelar", 
                            on_click=UserManagementState.cancelar_edicao, 
                            color_scheme="gray", 
                            variant="soft"
                        )
                    ),
                    rx.alert_dialog.action(
                        rx.button(
                            "Salvar Senha", 
                            on_click=UserManagementState.salvar_nova_senha, 
                            color_scheme="green"
                        )
                    ),
                    spacing="3",
                    justify="end"
                ),

                width="25%",
            ),
            # A MÁGICA ESTÁ AQUI: O modal reage à variável do seu states.py
            open=UserManagementState.usuario_edicao != "",
        )

    return rx.dialog.root(
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
                                            rx.cond(u["role"] == "admin", "Administrador", "Operador"),
                                            color_scheme=rx.cond(u["role"] == "admin", "amber", "blue"),
                                            radius="small",
                                        ),
                                        rx.cond(AuthState.usuario_logado == u["username"],
                                            rx.badge("Usuário Atual", color_scheme="green", radius="small")
                                        ),
                                        spacing="1"
                                    ),
                                    spacing="1",
                                    align_items="start"
                                ),
                                rx.spacer(),
                                rx.cond(
                                    (AuthState.usuario_logado == u["username"]) | (AuthState.role_logado == "admin"),
                                    rx.hstack(
                                        # Botão da chave abre o formulário
                                        rx.tooltip(rx.icon_button(rx.icon("key_round"), on_click=UserManagementState.iniciar_edicao_senha(u["username"]), color_scheme="blue", variant="soft"), content="Alterar Senha"),
                                        rx.tooltip(rx.icon_button(rx.icon("trash"), on_click=UserManagementState.deletar_usuario(u["username"]), color_scheme="red", variant="soft"), content="Deletar Usuário"),
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
                        rx.input.slot(rx.icon("mail", color="gray")),
                        placeholder="Email", 
                        value=UserManagementState.form_username, 
                        on_change=UserManagementState.set_form_username,
                        width="100%"
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("lock", color="gray")),
                        placeholder="Senha", 
                        type="password", 
                        value=UserManagementState.form_password, 
                        on_change=UserManagementState.set_form_password,
                        width="100%"
                    ),
                    rx.cond(AuthState.role_logado == "admin",
                        rx.checkbox(
                            "Administrador", 
                            checked=UserManagementState.form_is_admin, 
                            on_change=UserManagementState.set_form_is_admin
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
            modal_edicao_senha(),

            width="30%",
        ),
    ),

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
                    ~AppState.monitorando,
                    rx.button(
                        rx.icon("play"),
                        "Iniciar Monitoramento", 
                        on_click=MonitoramentoState.dar_ignicao_global, 
                        color_scheme="green",
                        variant="solid"
                    ),
                    rx.button(
                        rx.icon("pause"),
                        "Parar Monitoramento", 
                        on_click=AppState.parar_monitoramento_global, 
                        color_scheme="red",
                        variant="solid"
                    ),
                ),
                
                # Configurações gerais
                rx.dialog.root(
                    rx.dialog.trigger(rx.button(rx.icon("settings"), "Configurações", color_scheme="blue", variant="surface", disabled=AppState.monitorando)),

                    rx.dialog.content(
                        rx.tabs.root(
                            rx.tabs.list(
                                rx.tabs.trigger("Configurações", value="config", color_scheme="purple"),
                                rx.tabs.trigger("Gerenciar Emails", value="emails", color_scheme="orange"),
                                rx.tabs.trigger("Gerenciar Ativos", value="ativos", color_scheme="blue"),
                            ),

                            # --- Configurações Gerais ---
                            configurações_gerais(),

                            # --- Configurações de Emails ---
                            configurações_emails(),

                            # --- Configurações de Ativos ---
                            configurações_ativos(),

                            default_value="config"
                        ),

                        width="35%",
                    ),
                ),

                # Configurações de usuários
                configurações_usuarios(),
                    
                # Logoff
                rx.tooltip(
                    rx.icon_button(rx.icon("door_open"), on_click=AuthState.fazer_logout, color_scheme="red", variant="surface"),
                    content="Sair"
                ),
            ),
            
            rx.divider(margin_y="1em"),
            
            # Cards de ativos
            rx.grid(
                rx.foreach(AppState.ativos_live, renderizar_card),
                columns="3",
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
app.add_page(tela_login, route="/login", title="Login - Echo", on_load=AuthState.checar_acesso_login)
app.add_page(index, title="Painel - Echo", on_load=[
    AuthState.verificar_acesso,
    MonitoramentoState.on_load,
    UserManagementState.carregar_usuarios,
    ConfigState.carregar_emails,
    ConfigState.carregar_grupos,
    ConfigState.carregar_configs,
    AppState.conectar_painel
])