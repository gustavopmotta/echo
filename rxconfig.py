import reflex as rx

config = rx.Config(
    app_name="Echo",
    api_url="http://0.0.0.0:8000",
    state_auto_setters=True,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)