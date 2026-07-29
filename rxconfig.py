import reflex as rx

config = rx.Config(
    app_name="Echo",
    api_url="http://0.0.0.0:8001", # Recomendado: Para rodar o sistema em modo de produção altere a porta para 8000
    state_auto_setters=True,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)