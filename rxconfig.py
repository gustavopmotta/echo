import reflex as rx

config = rx.Config(
    app_name="Echo",
    db_url="sqlite:///reflex.db",
    plugins=[
        rx.plugins.RadixThemesPlugin(),
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
)
