"""Navigation callbacks."""

from dash import Input, Output


def register(app):
    @app.callback(
        Output("main-tabs", "active_tab"),
        Output("analysis-tabs", "active_tab"),
        Output("browse-search", "value"),
        Input("nav-search-btn", "n_clicks"),
        Input("mode-explorer-btn", "n_clicks"),
        Input("mode-analysis-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def navigate_tabs(nav_click, mode_explore, mode_analysis):
        from dash import ctx
        trigger = ctx.triggered_id
        if trigger == "mode-analysis-btn":
            return "tab-analysis", "tab-overall-trends", ""
        return "tab-browse", "tab-overall-trends", ""
