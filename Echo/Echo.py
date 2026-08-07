import reflex as rx
from .states import AppState, AuthState, ConfigState, MonitoramentoState, UserManagementState, AtivoRede, ResumoGrupo

radix_colors = ['tomato', 'red', 'ruby', 'crimson', 'pink', 'plum', 'purple', 'violet', 'iris', 'indigo', 'blue', 'cyan', 'teal', 'jade', 'green', 'grass', 'brown', 'orange', 'sky', 'mint', 'lime', 'yellow', 'amber', 'gold', 'bronze', 'gray']

# --- CARD DE ATIVO ---
def renderizar_card(ativo: AtivoRede):
    cor_status = rx.cond(ativo.status == "Online", "green",
                 rx.cond(ativo.status == "Lento", "orange", "red"))

    grafico_aberto = MonitoramentoState.ip_grafico_aberto == ativo.ip

    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.box(
                            width="8px", height="8px", border_radius="50%",
                            background=rx.color(cor_status, 9),
                        ),
                        rx.text(ativo.nome, weight="bold"),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.text(f"{ativo.ip} - {ativo.local}", color="gray", size="1"),
                    spacing="0",
                    align_items="start",
                ),
                rx.spacer(),
                rx.vstack(
                    rx.cond(
                        ativo.status != "Offline",
                        rx.text(f"{ativo.latencia:.0f} ms", weight="bold", size="3"),
                        rx.text("--", color="gray", size="3"),
                    ),
                    rx.cond(
                        ativo.total_pings > 0,
                        rx.text(f"Média: {ativo.total_latencia / ativo.total_pings:.0f} ms", color="gray", size="1"),
                        rx.text("--", color="gray", size="1"),
                    ),
                    spacing="0",
                    align_items="end",
                ),            
                rx.icon_button(
                    rx.cond(grafico_aberto, rx.icon("chevron_up"), rx.icon("chevron_down")),
                    on_click=MonitoramentoState.alternar_grafico_ativo(ativo.ip),
                    variant="ghost",
                    color_scheme="gray",
                    size="1",
                ),
                width="100%",
                align_items="center",
            ),

            # Só monta o gráfico se este for o ativo selecionado
            rx.cond(
                grafico_aberto,
                rx.recharts.bar_chart(
                    rx.recharts.bar(
                        data_key="latencia",
                        is_animation_active=False,
                        fill=rx.color(cor_status, 8),
                        stroke=rx.color(cor_status, 10),
                        stroke_width=2,
                        radius=[4, 4, 0, 0],
                    ),
                    rx.recharts.x_axis(data_key="hora"),
                    rx.recharts.y_axis(hide=False, width=40, domain=[0, ConfigState.config["limite_latencia_ms"]]),
                    rx.recharts.graphing_tooltip(),
                    data=ativo.historico,
                    height=160,
                    width="100%",
                    margin_top="0.5em",
                ),
            ),

            width="100%",
            spacing="1",
        ),
        border_left=f"4px solid var(--{cor_status}-9)",
        width="100%",
        variant="surface",
        padding="0.75em",
    )

# --- CARD DE GRUPO (resumo sempre visível, detalhes sob demanda) ---
def renderizar_bloco_grupo(resumo: ResumoGrupo):
    cor_borda = rx.cond(
        resumo.offline > 0, "red",
        rx.cond(resumo.lentos > 0, "orange", "green")
    )

    termo_busca = MonitoramentoState.busca_ativos.get(resumo.nome, "")
    status_filtro = MonitoramentoState.filtro_status.get(resumo.nome, "Todos")
    sem_resultado = MonitoramentoState.nenhum_resultado.get(resumo.nome, False)

    def badge_filtro(label: str, contador, cor: str, chave_status: str):
        ativo_selecionado = status_filtro == chave_status
        return rx.badge(
            contador, f" {label}",
            color_scheme=cor,
            variant=rx.cond(ativo_selecionado, "solid", "soft"),
            cursor="pointer",
            on_click=MonitoramentoState.alternar_filtro_status(resumo.nome, chave_status),
        )

    def card_filtravel(ativo: AtivoRede):
        passa_busca = (
            (termo_busca == "")
            | ativo.nome.lower().contains(termo_busca.lower())
            | ativo.ip.contains(termo_busca)
        )
        passa_status = (status_filtro == "Todos") | (ativo.status == status_filtro)
        return rx.cond(passa_busca & passa_status, renderizar_card(ativo), rx.fragment())

    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.flex(
                    rx.hstack(
                        rx.box(
                            width="12px", height="12px", border_radius="50%",
                            background=rx.color(cor_borda, 9),
                        ),
                        rx.heading(resumo.nome, size="6"),
                        rx.cond(resumo.ininterrupto, rx.tooltip(rx.icon("clock_fading", color_scheme="blue", variant="surface", size=20), content="Este grupo é ininterrupto")),
                        align_items="center"
                    ),                               
                    align="baseline",
                    direction="row",
                    width="stretch",
                    spacing="2",
                ),
                rx.spacer(),
                badge_filtro("Online", resumo.online, "green", "Online"),
                badge_filtro("Lento", resumo.lentos, "orange", "Lento"),
                badge_filtro("Offline", resumo.offline, "red", "Offline"),
                rx.badge(resumo.latencia_media, " ms", color_scheme="blue", variant="soft"),
                width="100%",
                align_items="center",
                margin_top="0.25em",
            ),

            rx.divider(margin_y="0.25em"),

            rx.debounce_input(
                rx.input(
                    rx.input.slot(rx.icon("search", size=14)),
                    placeholder=f"Buscar em {resumo.nome}...",
                    value=termo_busca,
                    on_change=lambda v: MonitoramentoState.set_busca_grupo(resumo.nome, v),
                    size="2",
                    width="100%",
                ),
                debounce_timeout=250,
            ),

            rx.scroll_area(
                rx.vstack(
                    rx.foreach(resumo.ativos_lista, card_filtravel),
                    width="100%",
                    spacing="2",
                ),
                width="100%",
                type="scroll",
                style={"max_height": "22rem"},
                padding_right="1em",
            ),

            rx.cond(
                sem_resultado,
                rx.vstack(
                    rx.text("Nenhum ativo encontrado.", color="gray", size="3", text_align="center"),
                    rx.icon("search_x", size=50, color="gray"),
                    width="100%",
                    align_items="center",
                    padding="2em"
                ),
            ),

            align_items="start",
            width="100%",
        ),
        width="100%",
        margin_bottom="4",
    )

# --- TELA DE LOGIN ---
def tela_login() -> rx.Component:
    return rx.center(
        rx.form(
            rx.card(
                rx.vstack(
                    rx.image(src="/icon-white256x256.svg", alt="Logo", width="6em", margin_bottom="1em"),
                    rx.heading("Bem-vindo ao Echo!", size="7"),
                    rx.text("Faça login com sua conta", size="3", text_align="center", color="gray", margin_bottom="0.5em"),

                    rx.vstack(
                        rx.text("Email", size="3", weight="medium", width="100%", text_align="left"),
                        rx.input(
                            rx.input.slot(rx.icon("user")),
                            placeholder="usuário@echo.com", 
                            on_change=AuthState.set_email_input,
                            value=AuthState.email_input,
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
                    rx.button("Fazer Login", on_click=AuthState.tentar_login, width="100%", color_scheme="blue", size="3", weight="bold", type="submit", loading=AuthState.tentando_login),

                    align_items="center",
                    spacing="3",
                    width="100%"
                ),
                padding="2em",
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
        rx.form(
            rx.card(
                rx.vstack(
                    rx.image(src="/icon-white256x256.svg", alt="Logo", width="6em", margin_bottom="1em"),
                    rx.heading("Bem-vindo ao Echo!", size="7"),
                    rx.text("Crie o usuário Administrador para inicializar o sistema.", size="1", text_align="center", color="gray", margin_bottom="1em"),

                    rx.input(
                        rx.input.slot(rx.icon("user_star")),
                        placeholder="Nome do Administrador", 
                        on_change=AuthState.set_setup_username,
                        value=AuthState.setup_username,
                        width="100%",
                        auto_complete=False
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("mail")),
                        placeholder="Email do Administrador", 
                        on_change=AuthState.set_setup_email,
                        value=AuthState.setup_email,
                        width="100%",
                        auto_complete=False
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("lock")),
                        type="password",
                        placeholder="Senha",
                        on_change=AuthState.set_setup_password,
                        value=AuthState.setup_password,
                        width="100%",
                        auto_complete=False
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("lock")),
                        type="password", 
                        placeholder="Confirme a Senha",
                        on_change=AuthState.set_setup_confirmacao,
                        value=AuthState.setup_confirmacao,
                        width="100%",
                        auto_complete=False
                    ),

                    rx.button("Criar Administrador", on_click=AuthState.registrar_primeiro_admin, width="100%", color_scheme="purple", size="3", weight="bold", type="submit", loading=AuthState.tentando_login),

                    align_items="center",
                    spacing="4"
                ),
                padding="2em"
            ),
            size="4",
            width="100%",
            max_width="24em",
        ),
        height="100vh"
    )

# --- CAIXA/ABA DE CONFIGURAÇÕES GERAIS ---
def configurações_gerais() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("settings"),
                "Configurações",
                color_scheme="blue",
                variant="surface",
                disabled=AppState.monitorando | AuthState.role_logado != "admin",
                width="100%",
                justify_content="start",
            )
        ),

        rx.dialog.content(
            rx.dialog.title("Configurações Gerais", padding_top="1em"),
            rx.dialog.description("Ajuste os parâmetros do servidor e do monitoramento de rede."),
            rx.divider(margin_y="1em"),
        
            # Scroll area previne que o modal fique gigante na tela
            rx.cond(
                AuthState.role_logado != "admin",
        
                rx.callout("Acesso restrito para administradores.", icon="shield_check", color_scheme="red", variant="soft"),
        
                rx.scroll_area(
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
            ),
            
            rx.divider(margin_y="1em"),
            
            rx.button(
                "Salvar Alterações", 
                on_click=ConfigState.salvar_configs_env, 
                color_scheme="purple",
                variant="soft",
                width="100%" 
            ),
            width="35%",
        ),
    ),

# --- CAIXA/ABA DE CONFIGURAÇÕES DE ATIVOS ---
def configurações_ativos() -> rx.Component:
    def modal_adicionar_ativo() -> rx.Component:
        return rx.alert_dialog.root(
            rx.alert_dialog.trigger(
                rx.tooltip(rx.icon_button(rx.icon("plus"), color_scheme="green", variant="soft"), content="Adicionar ativo")
            ),

            rx.alert_dialog.content(
                rx.alert_dialog.title("Adicionar Ativo de Rede"),
                rx.alert_dialog.description("Preencha os detalhes do novo dispositivo."),

                rx.divider(margin_y="1em"),

                rx.form(
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
                                    type="submit", 
                                    color_scheme="green"
                                ),
                            ),

                            spacing="3",
                            justify="end",
                            width="100%",
                        ),

                        spacing="3",
                    ),
                    on_submit=MonitoramentoState.adicionar_ativo_buffer,
                ),
                

                width="30%",
                open=MonitoramentoState.novo_ativo_nome != ""
            ),
        ),

    def modal_gerenciar_grupos() -> rx.Component:
        return rx.alert_dialog.root(
            rx.tooltip(
                rx.alert_dialog.trigger(rx.icon_button(rx.icon("tags"), color_scheme="blue", variant="soft")),
                content="Gerenciar grupos",
            ),

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
                                    rx.hstack(
                                        rx.text(g["nome"]),
                                        rx.cond(g["ininterrupto"], rx.tooltip(rx.icon("clock-fading", size=16), content="Este grupo é ininterrupto")),
                                        width="100%",
                                        align_items="center",
                                        spacing="1"
                                    ),
                                    
                                    rx.icon_button(rx.icon("trash"), on_click=ConfigState.remover_grupo(g["nome"]), color_scheme="red", variant="ghost"),
                                    width="100%",
                                    align_items="center",
                                ),
                                border_left=f"4px solid var(--{g["cor"]}-9)",
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
                
                rx.card(
                    rx.vstack(
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

                            spacing="1",
                        ),

                        rx.tooltip(
                            rx.checkbox(
                                "Grupo ininterrupto",
                                checked=ConfigState.novo_grupo_ininterrupto_input,
                                on_change=ConfigState.set_novo_grupo_ininterrupto_input
                            ),
                            content="Ativo que sempre deve estar ligado. O sistema enviará alertas mais frequentes se um ativo ininterrupto ficar offline.",
                        ),

                        rx.hstack(
                            rx.button(rx.icon("plus"), "Adicionar", on_click=ConfigState.adicionar_grupo, color_scheme="green", variant="soft", flex="1"),

                            rx.alert_dialog.cancel(
                                rx.button("Sair", variant="soft", color_scheme="gray", width="100%", flex="1")
                            ),
                            spacing="1",
                            width="100%"
                        )                
                    )
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
                            rx.button("Atualizar", on_click=MonitoramentoState.salvar_edicao_ativo,     color_scheme="blue", variant="soft")
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

    def modal_importacao() -> rx.Component:
        return rx.alert_dialog.root(
            rx.tooltip(
                rx.alert_dialog.trigger(
                    rx.icon_button(rx.icon("download"), color_scheme="green", variant="soft")
                ),
                content="Importar CSV"
            ),

            rx.alert_dialog.content(
                rx.alert_dialog.title("Importar Ativos via CSV"),
                rx.alert_dialog.description(
                    "O arquivo deve conter as colunas: ",
                    rx.code("nome, ip, local, grupo"),
                    ". IPs já cadastrados serão ignorados. Certifique-se de que os grupos existam antes de importar."
                ),

                rx.divider(margin_y="1em"),

                rx.vstack(
                    # Área de upload — some quando há preview
                    rx.cond(
                        ~MonitoramentoState.preview_total > 0,
                        rx.upload(
                            rx.vstack(
                                rx.icon("file_up", size=30, color="gray"),
                                rx.text(
                                    "Clique ou arraste o arquivo CSV aqui",
                                    color="gray",
                                    font_weight="bold"
                                ),
                                rx.text(
                                    "Uma pré-visualização aparecerá antes de confirmar.",
                                    size="2",
                                    color="gray"
                                ),
                                spacing="1",
                                align_items="center",
                            ),
                            id="upload_csv",
                            on_drop=MonitoramentoState.carregar_preview_csv(
                                rx.upload_files(upload_id="upload_csv")
                            ),
                            accept={".csv": ["text/csv"]},
                            border="2px dashed gray",
                            padding="1em",
                            border_radius="md",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.hstack(
                                rx.icon("table", size=16, color="gray"),
                                rx.text(
                                    f"{MonitoramentoState.preview_total} linha(s) encontrada(s)",
                                    size="2",
                                    color="gray"
                                ),
                                spacing="1",
                                align_items="center",
                            ),

                            rx.scroll_area(
                                rx.table.root(
                                    rx.table.header(
                                        rx.table.row(
                                            rx.table.column_header_cell("Nome"),
                                            rx.table.column_header_cell("IP"),
                                            rx.table.column_header_cell("Local"),
                                            rx.table.column_header_cell("Grupo"),
                                            rx.table.column_header_cell("Status"),
                                        )
                                    ),
                                    rx.table.body(
                                        rx.foreach(
                                            MonitoramentoState.preview_csv,
                                            lambda linha: rx.table.row(
                                                rx.table.cell(linha["nome"]),
                                                rx.table.cell(rx.code(linha["ip"], size="1")),
                                                rx.table.cell(linha["local"]),
                                                rx.table.cell(
                                                    rx.badge(linha["grupo"], variant="surface")
                                                ),
                                                rx.table.cell(
                                                    rx.cond(
                                                        linha["erro"] != "",
                                                        rx.badge(linha["erro"], color_scheme="red", variant="soft"),
                                                        rx.badge("OK", color_scheme="green", variant="soft"),
                                                    )
                                                ),
                                            )
                                        )
                                    ),
                                    variant="surface",
                                    width="100%",
                                ),
                                type="scroll",
                                style={"max_height": "35vh"},
                            ),

                            rx.hstack(
                                rx.badge(
                                    rx.icon("check", size=12),
                                    f"{MonitoramentoState.preview_validos} válido(s)",
                                    color_scheme="green",
                                    variant="soft"
                                ),
                                rx.badge(
                                    rx.icon("x", size=12),
                                    f"{MonitoramentoState.preview_erros} com erro(s)",
                                    color_scheme="red",
                                    variant="soft"
                                ),
                                spacing="2",
                            ),

                            width="100%",
                            spacing="2",
                        ),
                    ),

                    # Botões de ação
                    rx.hstack(
                        rx.alert_dialog.cancel(
                            rx.button(
                                "Cancelar",
                                color_scheme="gray",
                                variant="soft",
                                on_click=MonitoramentoState.limpar_preview_csv,
                            )
                        ),
                        rx.cond(
                            MonitoramentoState.preview_csv != [],
                            rx.alert_dialog.action(
                                rx.button(
                                    rx.icon("check", size=16),
                                    "Confirmar Importação",
                                    color_scheme="green",
                                    variant="soft",
                                    on_click=MonitoramentoState.confirmar_importacao_csv,
                                    disabled=MonitoramentoState.preview_validos == 0,
                                )
                            ),
                        ),
                        spacing="3",
                        justify="end",
                        width="100%",
                    ),

                    width="100%",
                    spacing="3",
                    padding="4",
                ),

                width="45%",
            )
        )

    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("server"),
                "Gerenciar Ativos",
                color_scheme="blue",
                variant="surface",
                disabled=AppState.monitorando,
                width="100%",
                justify_content="start",
            )
        ),

        rx.dialog.content(
            rx.dialog.title("Gerenciar Ativos de Rede", padding_top="1em"),
            rx.dialog.description("Adicione ou remova dispositivos. O monitoramento será pausado duranteaedição."),
        
            rx.divider(margin_y="1em"),

            rx.debounce_input(
                rx.input(
                    rx.input.slot(rx.icon("search", size=14)),
                    placeholder="Buscar por nome, IP, local ou grupo...",
                    value=MonitoramentoState.busca_gerenciamento,
                    on_change=MonitoramentoState.set_busca_gerenciamento,
                    width="100%",
                    margin_bottom="1em"
                ),
                debounce_timeout=250,
            ),
        
            rx.vstack(
                # Lista de ativos no buffer
                rx.scroll_area(
                    rx.vstack(
                        rx.foreach(
                            AppState.ativos_buffer, 
                            lambda ativo: rx.cond(
                            (MonitoramentoState.busca_gerenciamento == "")
                            | ativo["nome"].lower().contains(MonitoramentoState.busca_gerenciamento.lower())
                            | ativo["ip"].contains(MonitoramentoState.busca_gerenciamento)
                            | ativo["local"].lower().contains(MonitoramentoState.busca_gerenciamento.lower())
                            | ativo["grupo"].lower().contains(MonitoramentoState.busca_gerenciamento.lower()),

                                rx.card(
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
        
                                    width="100%",
                                ),
                            ),
                        ),
        
                        spacing="2",
                        padding_right="0.1em",
                    ),
        
                    type="scroll",
                    style={"max_height": "40vh"},
                    padding_right="1em",
                ),
        
                rx.divider(),
                
                align_items="stretch",
                width="100%",
                padding_bottom="1em",
            ),
            # Botões de Ação do Modal

            rx.hstack(
                modal_adicionar_ativo(),
                modal_importacao(),
                modal_gerenciar_grupos(),

                rx.tooltip(
                    rx.icon_button(rx.icon("upload"), on_click=MonitoramentoState.exportar_ativos_csv, color_scheme="blue", variant="soft"),
                    content="Exportar CSV"

                ),

                rx.button(rx.icon("save"), "Salvar e Atualizar", on_click=MonitoramentoState.salvar_ativos, color_scheme="blue",justify_self="end", flex="1", variant="soft"),
                width="100%",
            ),
            
        
            modal_edicao_ativo(),
            width="35%",
        ),
    ),

# --- CAIXA/ABA DE CONFIGURAÇÕES DE USUÁRIOS ---
def configurações_usuarios() -> rx.Component:
    def modal_edicao_senha() -> rx.Component:
        return rx.alert_dialog.root(
            rx.alert_dialog.content(
                rx.alert_dialog.title("Alterar Senha"),
                rx.alert_dialog.description(
                    "Digite a nova senha para o usuário: ",
                    rx.text(UserManagementState.usuario_edicao.title(), weight="bold", as_="span"),
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
                    rx.alert_dialog.action(
                        rx.button(
                            "Salvar Senha", 
                            on_click=UserManagementState.salvar_nova_senha, 
                            color_scheme="green",
                            variant="soft",
                        )
                    ),
                    rx.alert_dialog.cancel(
                        rx.button(
                            "Cancelar", 
                            on_click=UserManagementState.cancelar_edicao, 
                            color_scheme="gray", 
                            variant="soft",
                        )
                    ),
                    spacing="3",
                    justify="end"
                ),

                width="25%",
            ),
            open=UserManagementState.usuario_edicao != "",
        )

    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("users"),
                "Usuários",
                color_scheme="blue",
                variant="surface",
                width="100%",
                justify_content="start",
            )
        ),

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
                                    rx.text(u["username"], text_transform="capitalize", font_weight="bold"),
                                    rx.text(f"Email: {u['email']}", size="1", color="gray", padding_bottom="0.5em"),
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
                                    spacing="0",
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
                    padding_bottom="1em",
                    padding_right="0.1em",
                ),
                type="scroll", style={"max_height": "55vh"}, padding_right="1em"
            ),
        
            rx.divider(margin_y="1em"),

            rx.dialog.root(
                rx.dialog.trigger(
                    rx.button(
                        rx.icon("user-plus"),
                        "Adicionar Usuário",
                        color_scheme="green",
                        variant="soft",
                        width="100%",
                    )
                ),

                rx.dialog.content(
                    rx.dialog.title("Criar Novo Usuário"),
                    rx.dialog.description("Preencha os dados para criar um novo usuário."),
                    rx.divider(margin_y="1em"),
                    rx.vstack(
                        rx.input(
                            rx.input.slot(rx.icon("user", color="gray")),
                            placeholder="Nome de Usuário", 
                            value=UserManagementState.form_username, 
                            on_change=UserManagementState.set_form_username,
                            width="100%"
                        ),
                        rx.input(
                            rx.input.slot(rx.icon("mail", color="gray")),
                            placeholder="Email", 
                            value=UserManagementState.form_email, 
                            on_change=UserManagementState.set_form_email,
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
                            "Criar Usuário", 
                            on_click=UserManagementState.adicionar_usuario, 
                            color_scheme="green",
                            variant="soft",
                            width="100%"
                        ),

                        align_items="start", width="100%", spacing="3"
                    ),
                    width="30%",
                ),
            ),        
            modal_edicao_senha(),

            width="30%",
        ),
    ),

# --- PÁGINA DO PAINEL ---
def controles_sidebar() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.image(src="/icon-white256x256.svg", width="64px"),
            rx.heading("ECHO", size="8"),        
            width="100%",
            spacing="1",
            align_items="center",
        ),

        rx.divider(margin_y="0.5em"),

        rx.cond(
            ~AppState.monitorando,
            rx.button(
                rx.icon("play"),
                "Iniciar Monitoramento",
                on_click=MonitoramentoState.dar_ignicao_global,
                color_scheme="green",
                variant="surface",
                width="100%",
                justify_content="start",
            ),
            rx.button(
                rx.icon("pause"),
                "Parar Monitoramento",
                on_click=AppState.parar_monitoramento_global,
                color_scheme="red",
                variant="surface",
                width="100%",
                justify_content="start",
            ),
        ),

        configurações_gerais(),
        configurações_ativos(),
        configurações_usuarios(),

        rx.text(
            rx.cond(
                AppState.monitorando,
                f"Próximo relátorio em: {AppState.relatorio_min}:{AppState.relatorio_seg}",
                "App não está monitorando",
            ),
            size="1",
            color="gray",
            text_align="center",
            width="100%",
        ),

        rx.spacer(),

        rx.hstack(
            rx.vstack(
                rx.text("Conectado como:", size="2", color="gray"),
                rx.text(AuthState.usuario_logado.title() | "Desconhecido", weight="bold"),
                rx.text(
                    rx.cond(
                        AuthState.role_logado == "admin",
                        "Administrador",
                        "Operador",
                    ),
                    size="1",
                    color="gray",
                ),
                
                spacing="1",
                align_items="start",
                padding_top="1em",
                flex="1",
            ),

            rx.vstack(
                rx.tooltip(
                    rx.icon_button(
                        rx.icon("door_open"),
                        on_click=AuthState.fazer_logout,
                        color_scheme="red",
                        variant="ghost",
                    ),
                    content="Sair",
                ),
                direction="column-reverse",
                height="stretch",
            ),
            align_items="center",
        ),

        spacing="3",
        align_items="stretch",
        width="260px",
        min_width="260px",
        padding="1.25em",
        border_right="1px solid var(--gray-6)",
        min_height="100vh",
        background=rx.color("gray", 1),
        position="sticky",
        top="0",
    )

def index() -> rx.Component:
    return rx.flex(
        controles_sidebar(),

        rx.box(
            rx.vstack(
                rx.flex(
                    rx.foreach(
                        AppState.resumo_grupos,
                        renderizar_bloco_grupo,
                    ),
                    width="100%",
                    padding="4",
                    spacing="3",
                    columns="2",
                ),

                padding="2em",
                width="100%",
                align_items="center",
            ),

            flex="1",
            width="100%",
        ),

        width="100%",
        min_height="100vh",
        align_items="start",
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
    ConfigState.carregar_grupos,
    ConfigState.carregar_configs,
    AppState.conectar_painel
])