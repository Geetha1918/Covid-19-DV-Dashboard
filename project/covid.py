import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd
import os
import logging
from dash.dependencies import Input, Output
from flask_caching import Cache

# Set up
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
DATA_FILE = "time_series_covid19_confirmed_global.csv"
app = dash.Dash(__name__)
cache = Cache(app.server, config={'CACHE_TYPE': 'simple'})

# Func load
def load_data(file_path):
    if not os.path.exists(file_path):
        logging.error(f"Data file '{file_path}' not found! Please check the path.")
        raise FileNotFoundError(f"Missing dataset: {file_path}")

    logging.info("Loading dataset...")
    df = pd.read_csv(file_path)

    # wide to long
    df_long = df.melt(id_vars=["Province/State", "Country/Region", "Lat", "Long"],
                      var_name="Date", value_name="Cases")

    # data to time
    df_long["Date"] = pd.to_datetime(df_long["Date"], format="%m/%d/%y", errors="coerce")

    logging.info("Dataset loaded successfully.")
    return df_long

# Load the COVID-19 data
try:
    covid_data = load_data(DATA_FILE)
except FileNotFoundError:
    logging.critical("Exiting: Required dataset not found.")
    exit(1)

app.layout = html.Div(
    [
        # Header section with title and theme toggle
        html.Div(
            [
                html.H1("COVID-19 Data Dashboard", id="header"),
                dcc.Checklist(
                    id="theme-toggle",
                    options=[{"label": "Dark Mode", "value": "dark"}],
                    value=[],
                    style={"marginRight": "20px"}
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
        ),

        # Dropdown
        dcc.Dropdown(
            id="country-selector",
            options=[{"label": country, "value": country} for country in covid_data["Country/Region"].unique()],
            multi=True,
            placeholder="Select countries...",
            style={"width": "50%", "margin": "20px auto"}
        ),

        # Line chart
        dcc.Graph(id="covid-line-chart"),

        # World map
        dcc.Graph(id="covid-map", style={"marginTop": "20px"}),
    ],
    id="app-container",
    style={"backgroundColor": "#99d6ff", "color": "black", "padding": "20px"},
)

# Func to filter
def filter_data(selected_countries):
    if selected_countries:
        return covid_data[covid_data["Country/Region"].isin(selected_countries)]
    return covid_data
@cache.memoize(timeout=60)  # Cache for 60 seconds
def get_filtered_data(selected_countries):
    return filter_data(selected_countries)

# Callback line chart user input
@app.callback(Output("covid-line-chart", "figure"),
              [Input("theme-toggle", "value"), Input("country-selector", "value")])
def update_line_chart(theme, selected_countries):
    filtered_data = get_filtered_data(selected_countries)  # Get filtered data
    # Downsample for performance (e.g., show only the last 30 days)
    recent_data = filtered_data[filtered_data['Date'] >= (filtered_data['Date'].max() - pd.Timedelta(days=30))]
    fig = px.line(recent_data, x="Date", y="Cases", color="Country/Region",
                  title="COVID-19 Cases Over Time (Last 30 Days)")
    return fig

# Callback world map user input
@app.callback(Output("covid-map", "figure"),
              [Input("theme-toggle", "value"), Input("country-selector", "value")])
def update_map(theme, selected_countries):
    latest_data = get_filtered_data(selected_countries)  # Get filtered data
    latest_date = covid_data["Date"].max()  # Get the latest date in the dataset
    latest_data = latest_data[latest_data["Date"] == latest_date]  # Filter for the latest data

    # Create a scatter geo plot for the latest COVID-19 cases
    fig = px.scatter_geo(latest_data, lat="Lat", lon="Long", size="Cases",
                         color="Country/Region", hover_name="Country/Region",
                         title="COVID-19 Cases Worldwide")
    return fig

#dark mode and light mode
@app.callback(
    [Output("app-container", "style"), Output("header", "style")],
    [Input("theme-toggle", "value")]
)
def toggle_theme(dark_mode):
    is_dark_mode = "dark" in dark_mode  # Check if dark mode is selected

    return (
        {
            "backgroundColor": "#99d6ff",  # Keep the background color consistent
            "color": "white" if is_dark_mode else "black",
            "padding": "20px",
        },
        {"textAlign": "center", "color": "white" if is_dark_mode else "black"},
    )

# Run the Dash
if __name__ == "__main__":
    app.run_server(debug=True)