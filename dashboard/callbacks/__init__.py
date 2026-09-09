"""Callback registration dispatcher."""

from dashboard.callbacks import navigation, flagship, explorer, datasets, institutions, thematic, uptake, portfolio


def register_callbacks(app):
    navigation.register(app)
    flagship.register(app)
    explorer.register(app)
    portfolio.register(app)
    datasets.register(app)
    institutions.register(app)
    thematic.register(app)
    uptake.register(app)
