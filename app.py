import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
from wordcloud import WordCloud
import pandas as pd
import io
import base64
from PIL import Image
import dash_bootstrap_components as dbc

from zotero_client import ZoteroClient
from tag_processor import TagProcessor

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Zotero Tag Cloud Visualizer", className="text-center mb-4"),
            html.Hr()
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Zotero Configuration"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Library ID:"),
                            dbc.Input(
                                id="library-id",
                                type="text",
                                placeholder="Enter your Zotero library ID",
                                value=""
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Library Type:"),
                            dcc.Dropdown(
                                id="library-type",
                                options=[
                                    {"label": "User Library", "value": "user"},
                                    {"label": "Group Library", "value": "group"}
                                ],
                                value="user"
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Label("API Key:"),
                            dbc.Input(
                                id="api-key",
                                type="password",
                                placeholder="Enter your Zotero API key",
                                value=""
                            )
                        ], width=4)
                    ]),
                    html.Br(),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "Load Tags",
                                id="load-tags-btn",
                                color="primary",
                                className="me-2"
                            ),
                            dbc.Button(
                                "Test Connection",
                                id="test-connection-btn",
                                color="secondary"
                            )
                        ])
                    ])
                ])
            ], className="mb-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Filters"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Search Tags:"),
                            dbc.Input(
                                id="search-input",
                                type="text",
                                placeholder="Search for specific tags...",
                                value=""
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Min Frequency:"),
                            dbc.Input(
                                id="min-freq",
                                type="number",
                                min=1,
                                value=1
                            )
                        ], width=2),
                        dbc.Col([
                            dbc.Label("Max Frequency:"),
                            dbc.Input(
                                id="max-freq",
                                type="number",
                                min=1,
                                placeholder="Leave empty for no limit"
                            )
                        ], width=2),
                        dbc.Col([
                            dbc.Label("Max Tags:"),
                            dbc.Input(
                                id="max-tags",
                                type="number",
                                min=10,
                                max=200,
                                value=50
                            )
                        ], width=2),
                        dbc.Col([
                            html.Br(),
                            dbc.Button(
                                "Apply Filters",
                                id="apply-filters-btn",
                                color="info"
                            )
                        ], width=2)
                    ])
                ])
            ], className="mb-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dcc.Loading(
                id="loading",
                children=[
                    html.Div(id="status-message", className="mb-3"),
                    html.Div(id="tag-cloud-container")
                ]
            )
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(id="tag-statistics", className="mt-4")
        ])
    ]),
    
    # Store components for data persistence
    dcc.Store(id="tags-data"),
    dcc.Store(id="processed-tags")
])

@app.callback(
    Output("status-message", "children"),
    Input("test-connection-btn", "n_clicks"),
    State("library-id", "value"),
    State("library-type", "value"),
    State("api-key", "value"),
    prevent_initial_call=True
)
def test_connection(n_clicks, library_id, library_type, api_key):
    if not all([library_id, library_type, api_key]):
        return dbc.Alert("Please fill in all required fields.", color="warning")
    
    try:
        client = ZoteroClient(library_id, library_type, api_key)
        if client.test_connection():
            return dbc.Alert("Connection successful!", color="success")
        else:
            return dbc.Alert("Connection failed. Please check your credentials.", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")

@app.callback(
    [Output("tags-data", "data"),
     Output("status-message", "children", allow_duplicate=True)],
    Input("load-tags-btn", "n_clicks"),
    State("library-id", "value"),
    State("library-type", "value"),
    State("api-key", "value"),
    prevent_initial_call=True
)
def load_tags(n_clicks, library_id, library_type, api_key):
    if not all([library_id, library_type, api_key]):
        return None, dbc.Alert("Please fill in all required fields.", color="warning")
    
    try:
        client = ZoteroClient(library_id, library_type, api_key)
        
        # Try fetching tags directly first
        tags_data = client.fetch_all_tags()
        
        if not tags_data:
            # Fallback: fetch items and extract tags
            items_data = client.get_items_with_tags()
            processor = TagProcessor()
            tag_freq = processor.process_items_tags(items_data)
            tags_data = [{"tag": tag, "meta": {"numItems": count}} for tag, count in tag_freq.items()]
        
        if tags_data:
            return tags_data, dbc.Alert(f"Successfully loaded {len(tags_data)} tags!", color="success")
        else:
            return None, dbc.Alert("No tags found in your library.", color="warning")
            
    except Exception as e:
        return None, dbc.Alert(f"Error loading tags: {str(e)}", color="danger")

@app.callback(
    [Output("processed-tags", "data"),
     Output("tag-cloud-container", "children"),
     Output("tag-statistics", "children")],
    Input("apply-filters-btn", "n_clicks"),
    State("tags-data", "data"),
    State("search-input", "value"),
    State("min-freq", "value"),
    State("max-freq", "value"),
    State("max-tags", "value"),
    prevent_initial_call=True
)
def update_visualization(n_clicks, tags_data, search_term, min_freq, max_freq, max_tags):
    if not tags_data:
        return None, html.Div("No tags data available. Please load tags first."), html.Div()
    
    try:
        processor = TagProcessor()
        tag_freq = processor.process_zotero_tags(tags_data)
        
        # Apply filters
        if search_term:
            tag_freq = processor.search_tags(search_term)
        
        min_freq = min_freq or 1
        filtered_tags = processor.filter_by_frequency(min_freq, max_freq)
        
        if max_tags:
            processor.processed_tags = filtered_tags
            filtered_tags = processor.get_top_tags(max_tags)
        
        if not filtered_tags:
            return None, html.Div("No tags match the current filters."), html.Div()
        
        # Generate word cloud
        wordcloud = WordCloud(
            width=1200,
            height=600,
            background_color='white',
            max_words=len(filtered_tags),
            colormap='viridis'
        ).generate_from_frequencies(filtered_tags)
        
        # Convert to image
        img = wordcloud.to_image()
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        encoded_image = base64.b64encode(buffer.getvalue()).decode()
        
        # Create bar chart for top tags
        top_tags = dict(sorted(filtered_tags.items(), key=lambda x: x[1], reverse=True)[:20])
        
        bar_fig = px.bar(
            x=list(top_tags.values()),
            y=list(top_tags.keys()),
            orientation='h',
            title="Top 20 Tags by Frequency",
            labels={'x': 'Frequency', 'y': 'Tags'}
        )
        bar_fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        
        # Generate statistics
        processor.processed_tags = filtered_tags
        stats = processor.get_tag_statistics()
        
        stats_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(stats.get('total_tags', 0), className="card-title"),
                        html.P("Total Tags", className="card-text")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(stats.get('total_occurrences', 0), className="card-title"),
                        html.P("Total Occurrences", className="card-text")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{stats.get('avg_frequency', 0):.1f}", className="card-title"),
                        html.P("Avg Frequency", className="card-text")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(stats.get('max_frequency', 0), className="card-title"),
                        html.P("Max Frequency", className="card-text")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(stats.get('unique_tags', 0), className="card-title"),
                        html.P("Unique Tags", className="card-text")
                    ])
                ])
            ], width=2)
        ])
        
        visualization = html.Div([
            dbc.Tabs([
                dbc.Tab(
                    html.Img(
                        src=f"data:image/png;base64,{encoded_image}",
                        style={'width': '100%', 'height': 'auto'}
                    ),
                    label="Word Cloud"
                ),
                dbc.Tab(
                    dcc.Graph(figure=bar_fig),
                    label="Bar Chart"
                )
            ])
        ])
        
        return filtered_tags, visualization, stats_cards
        
    except Exception as e:
        return None, html.Div(f"Error generating visualization: {str(e)}"), html.Div()

# Auto-apply filters when tags are loaded
@app.callback(
    Output("apply-filters-btn", "n_clicks"),
    Input("tags-data", "data"),
    prevent_initial_call=True
)
def auto_apply_filters(tags_data):
    if tags_data:
        return 1
    return 0

if __name__ == "__main__":
    app.run(debug=True)