import dash
from dash import dcc, html, Input, Output, State, callback_context, DiskcacheManager, callback, no_update
import plotly.graph_objects as go
import plotly.express as px
from wordcloud import WordCloud
import pandas as pd
import io
import base64
from PIL import Image
import dash_bootstrap_components as dbc
import diskcache
import hashlib

from zotero_client import ZoteroClient
from tag_processor import TagProcessor
from zotero_local_client import ZoteroLocalClient, detect_local_zotero
from database import db
from advanced_filters import AdvancedFilter, FilterCriteria, create_item_type_groups

# Initialize background callback manager
cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                background_callback_manager=background_callback_manager,
                suppress_callback_exceptions=True)

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Zotero Tag Cloud Visualizer", className="text-center mb-4"),
            html.Hr()
        ])
    ]),
    
    # Connection Type Selection
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Connection Type"),
                dbc.CardBody([
                    dbc.RadioItems(
                        id="connection-type",
                        options=[
                            {"label": "Local Zotero Instance (Faster)", "value": "local"},
                            {"label": "Web API (Internet Required)", "value": "web"}
                        ],
                        value="local",
                        inline=True
                    ),
                    html.Div(id="connection-status", className="mt-2")
                ])
            ], className="mb-3")
        ])
    ]),
    
    # Configuration Panel
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Zotero Configuration"),
                dbc.CardBody([
                    html.Div(id="config-panel")
                ])
            ], className="mb-4")
        ])
    ]),
    
    # Progress Section
    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Progress(
                    id="progress-bar",
                    value=0,
                    striped=True,
                    animated=True,
                    style={"display": "none"}
                ),
                html.Div(id="progress-text", className="mt-2")
            ], id="progress-section")
        ])
    ]),
    
    # Cache Management Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Cache & Storage"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div(id="cache-stats"),
                            dbc.ButtonGroup([
                                dbc.Button("Use Cache", id="use-cache-btn", color="success", size="sm"),
                                dbc.Button("Clear Cache", id="clear-cache-btn", color="warning", size="sm"),
                                dbc.Button("Refresh", id="refresh-cache-btn", color="info", size="sm")
                            ])
                        ], width=8),
                        dbc.Col([
                            dbc.Label("Recent Libraries:"),
                            dcc.Dropdown(
                                id="recent-libraries",
                                placeholder="Select a recent library...",
                                options=[]
                            )
                        ], width=4)
                    ])
                ])
            ], className="mb-4")
        ])
    ]),
    
    # Advanced Filters Panel
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Advanced Filters", className="mb-0"),
                    dbc.Button(
                        "Show/Hide Advanced Options",
                        id="toggle-advanced-filters",
                        color="link",
                        size="sm",
                        className="float-end"
                    )
                ]),
                dbc.CardBody([
                    # Basic Filters (Always Visible)
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
                    ], className="mb-3"),
                    
                    # Advanced Filters (Collapsible)
                    dbc.Collapse([
                        html.Hr(),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Item Types:"),
                                dcc.Dropdown(
                                    id="item-types-filter",
                                    placeholder="Select item types...",
                                    multi=True,
                                    options=[]
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Label("Publication Year Range:"),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Input(
                                            id="start-year",
                                            type="number",
                                            placeholder="Start year",
                                            min=1900,
                                            max=2030
                                        )
                                    ], width=6),
                                    dbc.Col([
                                        dbc.Input(
                                            id="end-year",
                                            type="number",
                                            placeholder="End year",
                                            min=1900,
                                            max=2030
                                        )
                                    ], width=6)
                                ])
                            ], width=4),
                            dbc.Col([
                                dbc.Label("Languages:"),
                                dcc.Dropdown(
                                    id="languages-filter",
                                    placeholder="Select languages...",
                                    multi=True,
                                    options=[]
                                )
                            ], width=4)
                        ], className="mb-3"),
                        
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Collections:"),
                                dcc.Dropdown(
                                    id="collections-filter",
                                    placeholder="Select collections...",
                                    multi=True,
                                    options=[]
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Label("Creator/Author:"),
                                dbc.Input(
                                    id="creator-filter",
                                    type="text",
                                    placeholder="Search by author name..."
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Label("Boolean Tag Query:"),
                                dbc.Input(
                                    id="boolean-query",
                                    type="text",
                                    placeholder="e.g., python AND (machine OR learning)"
                                )
                            ], width=4)
                        ], className="mb-3"),
                        
                        # Filter Presets and Actions
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Filter Presets:"),
                                dcc.Dropdown(
                                    id="filter-presets",
                                    placeholder="Load a saved filter...",
                                    options=[]
                                )
                            ], width=4),
                            dbc.Col([
                                html.Br(),
                                dbc.ButtonGroup([
                                    dbc.Button("Save Current Filter", id="save-filter-btn", color="success", size="sm"),
                                    dbc.Button("Clear All Filters", id="clear-filters-btn", color="warning", size="sm"),
                                    dbc.Button("Export Results", id="export-results-btn", color="info", size="sm")
                                ])
                            ], width=8)
                        ])
                    ], id="advanced-filters-collapse", is_open=False)
                ])
            ], className="mb-4")
        ])
    ]),
    
    # Collection Browser Panel
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Collection Browser"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dcc.Dropdown(
                                id="collection-browser",
                                placeholder="Browse collections...",
                                options=[]
                            )
                        ], width=8),
                        dbc.Col([
                            dbc.Button(
                                "Load Collection Tags",
                                id="load-collection-tags-btn",
                                color="primary",
                                disabled=True
                            )
                        ], width=4)
                    ]),
                    html.Div(id="collection-info", className="mt-2")
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
    dcc.Store(id="processed-tags"),
    dcc.Store(id="connection-config"),
    dcc.Store(id="cache-info"),
    dcc.Interval(id="progress-interval", interval=1000, n_intervals=0, disabled=True)
])

# Callback to update connection status and config panel
@callback(
    [Output("connection-status", "children"),
     Output("config-panel", "children")],
    Input("connection-type", "value")
)
def update_connection_type(connection_type):
    if connection_type == "local":
        # Check local Zotero status
        is_available = detect_local_zotero()
        
        if is_available:
            status = dbc.Alert("✅ Local Zotero instance detected", color="success")
            config = [
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Load Tags from Local Zotero",
                            id="load-tags-btn",
                            color="primary",
                            className="me-2"
                        ),
                        dbc.Button(
                            "Test Local Connection",
                            id="test-connection-btn",
                            color="secondary"
                        )
                    ])
                ])
            ]
        else:
            status = dbc.Alert("❌ Local Zotero not detected. Please ensure Zotero is running.", color="warning")
            config = [
                dbc.Alert("Start Zotero desktop application to use local mode.", color="info")
            ]
    
    else:  # web API
        status = dbc.Alert("🌐 Web API mode selected", color="info")
        config = [
            dbc.Row([
                dbc.Col([
                    dbc.Label("Library ID:"),
                    dbc.Input(
                        id="web-library-id",
                        type="text",
                        placeholder="Enter your Zotero library ID",
                        value=db.get_preference("last_library_id", "")
                    )
                ], width=4),
                dbc.Col([
                    dbc.Label("Library Type:"),
                    dcc.Dropdown(
                        id="web-library-type",
                        options=[
                            {"label": "User Library", "value": "user"},
                            {"label": "Group Library", "value": "group"}
                        ],
                        value=db.get_preference("last_library_type", "user")
                    )
                ], width=4),
                dbc.Col([
                    dbc.Label("API Key:"),
                    dbc.Input(
                        id="web-api-key",
                        type="password",
                        placeholder="Enter your Zotero API key",
                        value=""  # Never save API keys in preferences
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
        ]
    
    return status, config

# Callback to update cache statistics
@callback(
    Output("cache-stats", "children"),
    [Input("cache-info", "data"),
     Input("clear-cache-btn", "n_clicks"),
     Input("refresh-cache-btn", "n_clicks")]
)
def update_cache_stats(cache_info, clear_clicks, refresh_clicks):
    ctx = callback_context
    
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "clear-cache-btn.n_clicks":
        db.clear_all_cache()
    
    stats = db.get_cache_stats()
    
    return dbc.Row([
        dbc.Col([
            html.Small(f"Libraries: {stats['total_libraries']}", className="text-muted me-3"),
            html.Small(f"Tags: {stats['total_tags']}", className="text-muted me-3"),
            html.Small(f"Recent: {stats['recent_activity']}", className="text-muted")
        ])
    ])

# Callback to update recent libraries dropdown
@callback(
    Output("recent-libraries", "options"),
    Input("cache-info", "data")
)
def update_recent_libraries(cache_info):
    recent = db.get_recent_libraries()
    return [
        {
            "label": f"{name} ({lib_type}) - {last_updated[:10]}",
            "value": f"{lib_id}|{lib_type}"
        }
        for lib_id, lib_type, name, last_updated in recent
    ]

@callback(
    Output("status-message", "children"),
    Input("test-connection-btn", "n_clicks"),
    State("connection-type", "value"),
    prevent_initial_call=True
)
def test_local_connection(n_clicks, connection_type):
    if connection_type == "local":
        try:
            local_client = ZoteroLocalClient()
            if local_client.test_connection():
                return dbc.Alert("✅ Local Zotero connection successful!", color="success")
            else:
                return dbc.Alert("❌ Local Zotero connection failed.", color="danger")
        except Exception as e:
            return dbc.Alert(f"Local connection error: {str(e)}", color="danger")
    
    else:  # web API
        return dbc.Alert("💡 For Web API: Fill in your credentials above and they'll be tested automatically when you load tags.", color="info")

# Note: Web API test connection will be handled differently
# since the web inputs are dynamically created

@callback(
    [Output("tags-data", "data"),
     Output("status-message", "children", allow_duplicate=True),
     Output("progress-bar", "style"),
     Output("progress-interval", "disabled")],
    Input("load-tags-btn", "n_clicks"),
    State("connection-type", "value"),
    background=True,
    running=[
        (Output("load-tags-btn", "disabled"), True, False),
        (Output("progress-bar", "style"), {"display": "block"}, {"display": "none"}),
    ],
    progress=[Output("progress-bar", "value"), Output("progress-text", "children")],
    prevent_initial_call=True
)
def load_tags_background(set_progress, n_clicks, connection_type):
    if connection_type == "web":
        return None, dbc.Alert("💡 Web API mode is not fully implemented yet. Please use Local Zotero mode for now.", color="info"), {"display": "none"}, True
    
    try:
        # local connection - no progress bar needed for fast local access
        local_client = ZoteroLocalClient()
        tag_freq = local_client.get_all_tags_with_frequencies()
        
        if tag_freq:
            # Save to cache with local identifier
            local_lib_id = "local_library"
            db.save_library_info(local_lib_id, "local", "Local Zotero Library")
            db.save_tags(local_lib_id, "local", tag_freq)
            
            tags_data = [{"tag": tag, "meta": {"numItems": count}} for tag, count in tag_freq.items()]
            
            # Create centered, bigger "Completed!" message
            completed_message = html.Div([
                html.H3("🎉 Completed!", className="text-center text-success", style={"fontSize": "2rem", "margin": "20px 0"})
            ], className="text-center")
            
            return tags_data, completed_message, {"display": "none"}, True
        else:
            return None, dbc.Alert([
                "❌ Could not fetch tags from local Zotero. ",
                html.Br(),
                "Make sure you've enabled 'Allow other applications on this computer to communicate with Zotero' in Zotero Settings → Advanced.",
                html.Br(),
                "Try the 'Test Local Connection' button first."
            ], color="warning"), {"display": "none"}, True
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return None, dbc.Alert(f"Error loading tags: {str(e)}", color="danger"), {"display": "none"}, True

@callback(
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
@callback(
    Output("apply-filters-btn", "n_clicks"),
    Input("tags-data", "data"),
    prevent_initial_call=True
)
def auto_apply_filters(tags_data):
    if tags_data:
        return 1
    return 0

if __name__ == "__main__":
    app.run(debug=True, port=8051)  # Use port 8051 instead