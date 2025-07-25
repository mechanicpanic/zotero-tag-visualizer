import dash
from dash import dcc, html, Input, Output, State, callback_context, DiskcacheManager, callback, no_update, ALL
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
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("Zotero Tag Cloud Visualizer", className="text-center mb-4"),
            html.Hr()
        ])
    ]),
    
    # Main Layout: Left sidebar + Right content
    dbc.Row([
        # Left Sidebar - Connection & Configuration
        dbc.Col([
            # Connection & Configuration Panel
            dbc.Card([
                dbc.CardHeader("Zotero Connection"),
                dbc.CardBody([
                    dbc.Label("Connection Type:", className="small fw-bold"),
                    dbc.RadioItems(
                        id="connection-type",
                        options=[
                            {"label": "Local Zotero", "value": "local"},
                            {"label": "Web API", "value": "web"}
                        ],
                        value="local",
                        className="mb-2"
                    ),
                    html.Div(id="connection-status", className="mb-3"),
                    html.Hr(),
                    html.Div(id="config-panel")
                ])
            ], className="mb-3"),
            
            # Cache Management
            dbc.Card([
                dbc.CardHeader("Cache & Storage"),
                dbc.CardBody([
                    html.Div(id="cache-stats", className="mb-2"),
                    dbc.ButtonGroup([
                        dbc.Button("Use Cache", id="use-cache-btn", color="success", size="sm"),
                        dbc.Button("Clear", id="clear-cache-btn", color="warning", size="sm"),
                        dbc.Button("Refresh", id="refresh-cache-btn", color="info", size="sm")
                    ], className="mb-2"),
                    dbc.Label("Recent Libraries:", className="small"),
                    dcc.Dropdown(
                        id="recent-libraries",
                        placeholder="Select recent...",
                        options=[]
                    )
                ])
            ], className="mb-3")
        ], width=3),
        
        # Center Content - Tag Cloud
        dbc.Col([
            # Progress Section
            html.Div([
                dbc.Progress(
                    id="progress-bar",
                    value=0,
                    striped=True,
                    animated=True,
                    style={"display": "none"}
                ),
                html.Div(id="progress-text", className="mt-2")
            ], id="progress-section", className="mb-3"),
            
            # Tag Cloud
            dcc.Loading(
                id="loading",
                children=[
                    html.Div(id="status-message", className="mb-3"),
                    html.Div(id="tag-cloud-container")
                ]
            ),
            html.Div(id="tag-statistics", className="mt-3")
        ], width=6),
        
        # Right Sidebar - Advanced Filters & Analysis
        dbc.Col([
            # Advanced Filters Panel
            dbc.Card([
                dbc.CardHeader([
                    html.H6("Advanced Filters", className="mb-0"),
                    dbc.Button(
                        "Show/Hide",
                        id="toggle-advanced-filters",
                        color="link",
                        size="sm",
                        className="float-end"
                    )
                ]),
                dbc.CardBody([
                    # Apply Filters Button - Prominently placed at top
                    html.Div([
                        dbc.Button(
                            "Apply Filters",
                            id="apply-filters-btn",
                            color="primary",
                            size="sm",
                            className="w-100"
                        )
                    ], className="text-center mb-3"),
                    
                    # Basic Filters (Always Visible)
                    dbc.Label("Search Tags:", className="small"),
                    dbc.Input(
                        id="search-input",
                        type="text",
                        placeholder="Search tags...",
                        value="",
                        size="sm",
                        className="mb-2"
                    ),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Min Freq:", className="small"),
                            dbc.Input(
                                id="min-freq",
                                type="number",
                                min=1,
                                value=1,
                                size="sm"
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Max Freq:", className="small"),
                            dbc.Input(
                                id="max-freq",
                                type="number",
                                min=1,
                                placeholder="Max",
                                size="sm"
                            )
                        ], width=6)
                    ], className="mb-2"),
                    
                    dbc.Label("Max Tags:", className="small"),
                    dbc.Input(
                        id="max-tags",
                        type="number",
                        min=10,
                        max=200,
                        value=50,
                        size="sm",
                        className="mb-2"
                    ),
                    
                    # Advanced Filters (Collapsible)
                    dbc.Collapse([
                        html.Hr(),
                        dbc.Label("Item Types:", className="small"),
                        dcc.Dropdown(
                            id="item-types-filter",
                            placeholder="Select types...",
                            multi=True,
                            options=[]
                        ),
                        html.Br(),
                        
                        dbc.Label("Year Range:", className="small"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Input(
                                    id="start-year",
                                    type="number",
                                    placeholder="Start",
                                    min=1900,
                                    max=2030,
                                    size="sm"
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.Input(
                                    id="end-year",
                                    type="number",
                                    placeholder="End",
                                    min=1900,
                                    max=2030,
                                    size="sm"
                                )
                            ], width=6)
                        ], className="mb-2"),
                        
                        dbc.Label("Languages:", className="small"),
                        dcc.Dropdown(
                            id="languages-filter",
                            placeholder="Select languages...",
                            multi=True,
                            options=[]
                        ),
                        html.Br(),
                        
                        dbc.Label("Collections:", className="small"),
                        dcc.Dropdown(
                            id="collections-filter",
                            placeholder="Select collections...",
                            multi=True,
                            options=[]
                        ),
                        html.Br(),
                        
                        dbc.Label("Creator/Author:", className="small"),
                        dbc.Input(
                            id="creator-filter",
                            type="text",
                            placeholder="Author name...",
                            size="sm",
                            className="mb-2"
                        ),
                        
                        dbc.Label("Boolean Query:", className="small"),
                        dbc.Input(
                            id="boolean-query",
                            type="text",
                            placeholder="python AND learning",
                            size="sm",
                            className="mb-2"
                        ),
                        
                        # Filter Presets and Actions
                        dbc.Label("Presets:", className="small"),
                        dcc.Dropdown(
                            id="filter-presets",
                            placeholder="Load preset...",
                            options=[]
                        ),
                        html.Br(),
                        
                        dbc.ButtonGroup([
                            dbc.Button("Save", id="save-filter-btn", color="success", size="sm"),
                            dbc.Button("Clear", id="clear-filters-btn", color="warning", size="sm"),
                            dbc.Button("Export", id="export-results-btn", color="info", size="sm")
                        ])
                    ], id="advanced-filters-collapse", is_open=False)
                ])
            ], className="mb-3"),
            
            # Collection Browser Panel
            dbc.Card([
                dbc.CardHeader("Collections"),
                dbc.CardBody([
                    dcc.Dropdown(
                        id="collection-browser",
                        placeholder="Browse collections...",
                        options=[]
                    ),
                    html.Br(),
                    dbc.Button(
                        "Load",
                        id="load-collection-tags-btn",
                        color="primary",
                        size="sm",
                        disabled=True
                    ),
                    html.Div(id="collection-info", className="mt-2")
                ])
            ], className="mb-3"),
            
            # Tag Analysis Panel
            dbc.Card([
                dbc.CardHeader([
                    html.H6("Tag Analysis", className="mb-0"),
                    dbc.Button(
                        "Show/Hide",
                        id="toggle-tag-analysis",
                        color="link",
                        size="sm",
                        className="float-end"
                    )
                ]),
                dbc.CardBody([
                    dbc.Collapse([
                        dbc.Label("Tag Relationships:", className="small"),
                        dbc.Input(
                            id="tag-analysis-input",
                            type="text",
                            placeholder="Analyze tag (e.g., 'machine learning')",
                            value="",
                            size="sm"
                        ),
                        html.Br(),
                        dbc.Button(
                            "Analyze",
                            id="analyze-cooccurrence-btn",
                            color="primary",
                            size="sm"
                        ),
                        html.Hr(),
                        
                        dbc.Label("Suggestions:", className="small"),
                        html.Div(id="filter-suggestions", className="mb-2"),
                        
                        html.H6("Related Tags:", className="small mb-1"),
                        html.Div(id="cooccurrence-results", className="mb-2"),
                        
                        html.H6("Hierarchy:", className="small mb-1"),
                        html.Div(id="tag-hierarchy-results")
                    ], id="tag-analysis-collapse", is_open=False)
                ])
            ], className="mb-3")
        ], width=3)
    ]),
    
    # Store components for data persistence
    dcc.Store(id="tags-data"),
    dcc.Store(id="processed-tags"),
    dcc.Store(id="connection-config"),
    dcc.Store(id="cache-info"),
    dcc.Store(id="filter-presets-data"),  # Store for saved filter presets
    dcc.Store(id="items-metadata"),  # Store for items metadata
    dcc.Interval(id="progress-interval", interval=1000, n_intervals=0, disabled=True)
], fluid=True)

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
                            "Load Tags",
                            id="load-tags-btn",
                            color="primary",
                            className="me-2"
                        ),
                        dbc.Button(
                            "Test",
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
                        "Test",
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
     Output("progress-interval", "disabled"),
     Output("item-types-filter", "options"),
     Output("languages-filter", "options")],
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
        return None, dbc.Alert("💡 Web API mode requires manual setup. Switch to Local mode or configure Web API credentials in the config panel.", color="info"), {"display": "none"}, True, [], []
    
    else:  # Local connection
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
                
                # Get metadata summary for filter options
                try:
                    metadata_summary = local_client.get_library_metadata_summary()
                    print(f"DEBUG: Metadata summary retrieved: {metadata_summary is not None}")
                    
                    if metadata_summary:
                        print(f"DEBUG: Item types found: {list(metadata_summary.get('itemTypes', {}).keys())}")
                        print(f"DEBUG: Languages found: {list(metadata_summary.get('languages', {}).keys())}")
                        
                        # Get item types and add common fallbacks if none found
                        item_types_dict = metadata_summary.get('itemTypes', {})
                        if not item_types_dict:
                            print("DEBUG: No item types found, adding common fallbacks")
                            item_types_dict = {
                                'book': 0, 'journalArticle': 0, 'thesis': 0, 'report': 0, 
                                'webpage': 0, 'conferencePaper': 0, 'document': 0
                            }
                        
                        item_types_options = [{"label": item_type.replace('_', ' ').title(), "value": item_type} 
                                             for item_type in sorted(item_types_dict.keys())]
                        
                        # Get languages and add common fallbacks if none found  
                        languages_dict = metadata_summary.get('languages', {})
                        if not languages_dict:
                            print("DEBUG: No languages found, adding common fallbacks")
                            languages_dict = {
                                'en': 0, 'English': 0, 'en-US': 0, 'Spanish': 0, 'French': 0, 'German': 0
                            }
                        
                        languages_options = [{"label": lang, "value": lang} 
                                           for lang in sorted(languages_dict.keys())]
                    else:
                        print("DEBUG: Metadata summary is None, using fallbacks")
                        item_types_options = [
                            {"label": "Book", "value": "book"},
                            {"label": "Journal Article", "value": "journalArticle"},
                            {"label": "Thesis", "value": "thesis"},
                            {"label": "Report", "value": "report"},
                            {"label": "Webpage", "value": "webpage"},
                            {"label": "Conference Paper", "value": "conferencePaper"}
                        ]
                        languages_options = [
                            {"label": "English", "value": "en"},
                            {"label": "Spanish", "value": "es"},
                            {"label": "French", "value": "fr"},
                            {"label": "German", "value": "de"}
                        ]
                        
                except Exception as e:
                    # Fallback if metadata fetch fails
                    print(f"DEBUG: Metadata fetch failed with error: {str(e)}")
                    item_types_options = []
                    languages_options = []
                
                # Create centered, bigger "Completed!" message
                completed_message = html.Div([
                    html.H3("🎉 Completed!", className="text-center text-success", style={"fontSize": "2rem", "margin": "20px 0"})
                ], className="text-center")
                
                return tags_data, completed_message, {"display": "none"}, True, item_types_options, languages_options
            else:
                return None, dbc.Alert([
                    "❌ Could not fetch tags from local Zotero. ",
                    html.Br(),
                    "Make sure you've enabled 'Allow other applications on this computer to communicate with Zotero' in Zotero Settings → Advanced.",
                    html.Br(),
                    "Try the 'Test Local Connection' button first."
                ], color="warning"), {"display": "none"}, True, [], []
                
        except Exception as e:
            print(f"ERROR: {str(e)}")
            return None, dbc.Alert(f"Error loading tags: {str(e)}", color="danger"), {"display": "none"}, True, [], []

# Toggle advanced filters collapse
@callback(
    Output("advanced-filters-collapse", "is_open"),
    Input("toggle-advanced-filters", "n_clicks"),
    State("advanced-filters-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_advanced_filters(n_clicks, is_open):
    return not is_open

# Enhanced filters callback with advanced options
@callback(
    [Output("processed-tags", "data", allow_duplicate=True),
     Output("tag-cloud-container", "children", allow_duplicate=True),
     Output("tag-statistics", "children", allow_duplicate=True)],
    Input("apply-filters-btn", "n_clicks"),
    State("tags-data", "data"),
    State("search-input", "value"),
    State("min-freq", "value"),
    State("max-freq", "value"),
    State("max-tags", "value"),
    State("boolean-query", "value"),
    State("item-types-filter", "value"),
    State("start-year", "value"),
    State("end-year", "value"),
    State("creator-filter", "value"),
    State("languages-filter", "value"),
    State("collections-filter", "value"),
    prevent_initial_call=True
)
def update_visualization_advanced(n_clicks, tags_data, search_term, min_freq, max_freq, max_tags,
                                  boolean_query, item_types, start_year, end_year, creator_filter, languages, collections):
    if not tags_data:
        return None, html.Div("No tags data available. Please load tags first."), html.Div()
    
    try:
        processor = TagProcessor()
        tag_freq = processor.process_zotero_tags(tags_data)
        
        # Apply basic filters first
        if search_term and not boolean_query:
            tag_freq = processor.search_tags(search_term)
        
        # Apply Boolean query if provided
        if boolean_query:
            tag_freq = processor.get_tags_by_boolean_query(boolean_query)
        
        # Update processor with current results before applying frequency filters
        processor.processed_tags = tag_freq
        
        # Apply frequency filters
        min_freq = min_freq or 1
        filtered_tags = processor.filter_by_frequency(min_freq, max_freq)
        
        # Apply metadata-based filters (item types, languages, years)
        if item_types or languages or start_year or end_year:
            try:
                from zotero_local_client import ZoteroLocalClient
                local_client = ZoteroLocalClient()
                
                # Get items that match metadata criteria
                matching_items = local_client.get_items_by_metadata(
                    item_types=item_types,
                    languages=languages, 
                    start_year=start_year,
                    end_year=end_year
                )
                
                # Extract tags from matching items
                metadata_tags = set()
                for item in matching_items:
                    item_tags = item.get('data', {}).get('tags', [])
                    for tag_obj in item_tags:
                        tag_name = tag_obj.get('tag')
                        if tag_name:
                            metadata_tags.add(tag_name)
                
                # Filter to only include tags from items matching metadata criteria
                if metadata_tags:
                    filtered_tags = {tag: freq for tag, freq in filtered_tags.items() 
                                   if tag in metadata_tags}
                    print(f"DEBUG: Metadata filtering reduced tags to {len(filtered_tags)} from {len(metadata_tags)} unique item tags")
                else:
                    print("DEBUG: No tags found in items matching metadata criteria")
                    filtered_tags = {}
                    
            except Exception as e:
                print(f"Error applying metadata filters: {e}")
        
        # Apply advanced text filters if provided
        if creator_filter:
            # For now, just filter tags containing creator name
            filtered_tags = {tag: freq for tag, freq in filtered_tags.items() 
                           if creator_filter.lower() in tag.lower()}
        
        # Apply collection filter if provided
        if collections:
            try:
                from zotero_local_client import ZoteroLocalClient
                local_client = ZoteroLocalClient()
                
                # Get tags from selected collections
                collection_tags = set()
                for collection_key in collections:
                    if collection_key != "disabled":  # Skip disabled placeholder
                        collection_tag_freq = local_client.get_tags_for_collection(collection_key)
                        collection_tags.update(collection_tag_freq.keys())
                
                # Filter to only include tags that exist in selected collections
                filtered_tags = {tag: freq for tag, freq in filtered_tags.items() 
                               if tag in collection_tags}
                
            except Exception as e:
                print(f"Error applying collection filter: {e}")
        
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

# Clear all filters callback
@callback(
    [Output("search-input", "value"),
     Output("min-freq", "value"),
     Output("max-freq", "value"),
     Output("boolean-query", "value"),
     Output("creator-filter", "value"),
     Output("item-types-filter", "value"),
     Output("languages-filter", "value"),
     Output("collections-filter", "value"),
     Output("start-year", "value"),
     Output("end-year", "value")],
    Input("clear-filters-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_all_filters(n_clicks):
    return "", 1, None, "", "", [], [], [], None, None

# Collection browser callback
@callback(
    [Output("collection-browser", "options"),
     Output("load-collection-tags-btn", "disabled")],
    Input("tags-data", "data"),
    State("connection-type", "value")
)
def update_collections(tags_data, connection_type):
    if not tags_data:
        return [], True
    
    try:
        if connection_type == "web":
            # Web API collections require manual setup - disable for now
            return [], True
            
        elif connection_type == "local":
            local_client = ZoteroLocalClient()
            collections = local_client.get_collections()
            
            if collections:
                options = [{"label": f"{col['name']}", 
                           "value": col['key']} for col in collections if not col.get('parentCollection')]  # Use 'key' for REST API
                print(f"DEBUG: Created {len(options)} collection options")
                return options, False
            else:
                print("DEBUG: No collections found via REST API")
                return [], True
        
        return [], True
        
    except Exception as e:
        print(f"Error loading collections: {e}")
        return [], True

# Populate collections filter dropdown
@callback(
    Output("collections-filter", "options"),
    Input("tags-data", "data"),
    State("connection-type", "value")
)
def populate_collections_filter(tags_data, connection_type):
    """Populate collections filter dropdown with available collections"""
    if not tags_data:
        return []
    
    try:
        if connection_type == "local":
            local_client = ZoteroLocalClient()
            collections = local_client.get_collections()
            
            if collections:
                # Create options for collections filter
                options = [
                    {"label": col['name'], 
                     "value": col['key']} 
                    for col in collections 
                    if not col.get('parentCollection')  # Only top-level collections
                ]
                print(f"DEBUG: Found {len(options)} collections for filter")
                return options
            else:
                print("DEBUG: No collections found via REST API")
                return []
        
        # Web API collections would need additional implementation
        return [{"label": "Web API collections not yet supported", "value": "disabled", "disabled": True}]
        
    except Exception as e:
        print(f"Error populating collections filter: {e}")
        return [{"label": "Collections loading failed", "value": "disabled", "disabled": True}]

# Export functionality callback
@callback(
    Output("status-message", "children", allow_duplicate=True),
    Input("export-results-btn", "n_clicks"),
    State("processed-tags", "data"),
    prevent_initial_call=True
)
def export_results(n_clicks, processed_tags):
    if not processed_tags:
        return dbc.Alert("⚠️ No filtered results to export. Apply filters first.", color="warning")
    
    try:
        processor = TagProcessor()
        processor.processed_tags = processed_tags
        
        # Export to JSON
        export_data = processor.export_filtered_tags(processed_tags, format='json', include_metadata=True)
        
        # For demo, show success message (in production, this would trigger a download)
        return dbc.Alert([
            "✅ Export ready! ",
            html.Br(),
            f"Generated export with {len(processed_tags)} tags.",
            html.Br(),
            html.Small("(In a real application, this would download the file)")
        ], color="success")
        
    except Exception as e:
        return dbc.Alert(f"❌ Export failed: {str(e)}", color="danger")

# Filter presets management
@callback(
    [Output("filter-presets-data", "data"),
     Output("filter-presets", "options")],
    Input("save-filter-btn", "n_clicks"),
    State("search-input", "value"),
    State("min-freq", "value"),
    State("max-freq", "value"),
    State("boolean-query", "value"),
    State("creator-filter", "value"),
    State("item-types-filter", "value"),
    State("languages-filter", "value"),
    State("collections-filter", "value"),
    State("start-year", "value"),
    State("end-year", "value"),
    State("filter-presets-data", "data"),
    prevent_initial_call=True
)
def manage_filter_presets(save_clicks, search_term, min_freq, max_freq, boolean_query, 
                         creator_filter, item_types, languages, collections, start_year, end_year, existing_presets):
    # Initialize presets if empty
    if existing_presets is None:
        existing_presets = []
    
    # If save button was clicked, create new preset
    if save_clicks:
        # Create filter criteria
        from advanced_filters import FilterCriteria, AdvancedFilter
        
        criteria = FilterCriteria(
            search_terms=[search_term] if search_term else None,
            item_types=item_types,
            start_year=start_year,
            end_year=end_year,
            creators=[creator_filter] if creator_filter else None,
            languages=languages,
            collections=[str(cid) for cid in collections] if collections else None,
            min_frequency=min_freq,
            max_frequency=max_freq
        )
        
        # Generate preset name
        preset_name = f"Filter {len(existing_presets) + 1}"
        if search_term:
            preset_name = f"Search: {search_term[:20]}"
        elif boolean_query:
            preset_name = f"Query: {boolean_query[:20]}"
        elif item_types:
            preset_name = f"Types: {', '.join(item_types[:2])}"
        
        # Create preset
        filter_engine = AdvancedFilter()
        preset = filter_engine.create_filter_preset(preset_name, criteria)
        preset['boolean_query'] = boolean_query  # Add boolean query to preset
        
        # Add to existing presets
        existing_presets.append(preset)
        
        # Save to database preferences
        db.save_preference("filter_presets", existing_presets)
    
    # Load presets from database if not in memory
    if not existing_presets:
        existing_presets = db.get_preference("filter_presets", [])
    
    # Create options for dropdown
    options = [{"label": preset["name"], "value": i} for i, preset in enumerate(existing_presets)]
    
    return existing_presets, options

# Initialize filter presets on app start
@callback(
    [Output("filter-presets-data", "data", allow_duplicate=True),
     Output("filter-presets", "options", allow_duplicate=True)],
    Input("tags-data", "data"),  # Trigger when tags are first loaded
    prevent_initial_call=True
)
def initialize_filter_presets(tags_data):
    """Initialize filter presets from database on app start"""
    if tags_data is None:
        return [], []
    
    # Load existing presets from database
    existing_presets = db.get_preference("filter_presets", [])
    
    # Create options for dropdown
    options = [{"label": preset["name"], "value": i} for i, preset in enumerate(existing_presets)]
    
    return existing_presets, options

# Load filter preset callback
@callback(
    [Output("search-input", "value", allow_duplicate=True),
     Output("min-freq", "value", allow_duplicate=True),
     Output("max-freq", "value", allow_duplicate=True),
     Output("boolean-query", "value", allow_duplicate=True),
     Output("creator-filter", "value", allow_duplicate=True),
     Output("item-types-filter", "value", allow_duplicate=True),
     Output("languages-filter", "value", allow_duplicate=True),
     Output("collections-filter", "value", allow_duplicate=True),
     Output("start-year", "value", allow_duplicate=True),
     Output("end-year", "value", allow_duplicate=True)],
    Input("filter-presets", "value"),
    State("filter-presets-data", "data"),
    prevent_initial_call=True
)
def load_filter_preset(preset_index, presets_data):
    if preset_index is None or not presets_data or preset_index >= len(presets_data):
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    preset = presets_data[preset_index]
    criteria = preset.get("criteria", {})
    
    # Extract values from preset
    search_terms = criteria.get("search_terms", [])
    search_value = search_terms[0] if search_terms else ""
    
    creators = criteria.get("creators", [])
    creator_value = creators[0] if creators else ""
    
    return (
        search_value,
        criteria.get("min_frequency", 1),
        criteria.get("max_frequency"),
        preset.get("boolean_query", ""),
        creator_value,
        criteria.get("item_types", []),
        criteria.get("languages", []),
        criteria.get("collections", []),
        criteria.get("start_year"),
        criteria.get("end_year")
    )

# Toggle tag analysis panel
@callback(
    Output("tag-analysis-collapse", "is_open"),
    Input("toggle-tag-analysis", "n_clicks"),
    State("tag-analysis-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_tag_analysis(n_clicks, is_open):
    return not is_open

# Tag co-occurrence analysis
@callback(
    [Output("cooccurrence-results", "children"),
     Output("tag-hierarchy-results", "children"),
     Output("filter-suggestions", "children")],
    Input("analyze-cooccurrence-btn", "n_clicks"),
    State("tag-analysis-input", "value"),
    State("items-metadata", "data"),
    State("processed-tags", "data"),
    prevent_initial_call=True
)
def analyze_tag_relationships(n_clicks, target_tag, items_metadata, processed_tags):
    if not target_tag or not processed_tags:
        return (
            dbc.Alert("Enter a tag to analyze", color="info"),
            dbc.Alert("No hierarchy detected", color="info"),
            dbc.Alert("Load tags first", color="info")
        )
    
    try:
        # Find matching tags (partial match)
        matching_tags = [tag for tag in processed_tags.keys() if target_tag.lower() in tag.lower()]
        
        if not matching_tags:
            return (
                dbc.Alert(f"No tags found containing '{target_tag}'", color="warning"),
                dbc.Alert("No hierarchy detected", color="info"),
                dbc.Alert("No suggestions available", color="info")
            )
        
        # Use the first/best matching tag
        best_match = min(matching_tags, key=len)  # Shortest match is likely most relevant
        
        # Mock co-occurrence analysis (in real implementation, would use actual item data)
        processor = TagProcessor()
        processor.processed_tags = processed_tags
        
        # Generate mock co-occurrence data based on tag similarity
        cooccurring_tags = []
        for tag, freq in processed_tags.items():
            if tag != best_match:
                # Simple heuristic: tags with common words are likely to co-occur
                target_words = set(best_match.lower().split())
                tag_words = set(tag.lower().split())
                overlap = len(target_words.intersection(tag_words))
                
                if overlap > 0 or any(word in tag.lower() for word in target_words):
                    cooccurring_tags.append((tag, freq, overlap))
        
        # Sort by frequency and word overlap
        cooccurring_tags.sort(key=lambda x: (x[2], x[1]), reverse=True)
        
        # Create co-occurrence results
        if cooccurring_tags:
            cooccur_badges = []
            for tag, freq, overlap in cooccurring_tags[:10]:  # Top 10
                badge_color = "primary" if overlap > 1 else "secondary"
                cooccur_badges.append(
                    dbc.Badge([
                        tag,
                        dbc.Badge(freq, color="light", text_color="dark", className="ms-1")
                    ], color=badge_color, className="me-2 mb-2", style={"cursor": "pointer"})
                )
            cooccur_results = html.Div(cooccur_badges)
        else:
            cooccur_results = dbc.Alert("No related tags found", color="info")
        
        # Analyze hierarchical patterns
        hierarchy_results = processor.parse_hierarchical_tags()
        hierarchy_display = []
        
        for parent, children in hierarchy_results.items():
            if target_tag.lower() in parent.lower() or any(target_tag.lower() in child.lower() for child in children):
                hierarchy_display.append(
                    html.Div([
                        html.Strong(parent),
                        html.Ul([html.Li(child) for child in children[:5]])  # Max 5 children
                    ], className="mb-2")
                )
        
        if hierarchy_display:
            hierarchy_results = html.Div(hierarchy_display)
        else:
            hierarchy_results = dbc.Alert("No hierarchical patterns detected", color="info")
        
        # Generate filter suggestions
        suggestions = []
        
        # Suggest Boolean queries
        if cooccurring_tags:
            top_related = cooccurring_tags[0][0]
            suggestions.append(
                dbc.Button(
                    f'"{best_match}" AND "{top_related}"',
                    id={"type": "suggestion-btn", "query": f'"{best_match}" AND "{top_related}"'},
                    color="outline-primary",
                    size="sm",
                    className="me-2 mb-2"
                )
            )
            suggestions.append(
                dbc.Button(
                    f'"{best_match}" OR "{top_related}"',
                    id={"type": "suggestion-btn", "query": f'"{best_match}" OR "{top_related}"'},
                    color="outline-secondary",
                    size="sm",
                    className="me-2 mb-2"
                )
            )
        
        # Suggest exclusions
        if len(matching_tags) > 1:
            other_match = matching_tags[1]
            suggestions.append(
                dbc.Button(
                    f'"{best_match}" NOT "{other_match}"',
                    id={"type": "suggestion-btn", "query": f'"{best_match}" NOT "{other_match}"'},
                    color="outline-warning",
                    size="sm",
                    className="me-2 mb-2"
                )
            )
        
        suggestions_display = html.Div([
            html.P("Click to apply:", className="small text-muted"),
            html.Div(suggestions)
        ]) if suggestions else dbc.Alert("No suggestions available", color="info")
        
        return cooccur_results, hierarchy_results, suggestions_display
        
    except Exception as e:
        print(f"Error in tag analysis: {e}")
        return (
            dbc.Alert(f"Analysis error: {str(e)}", color="danger"),
            dbc.Alert("Analysis failed", color="danger"),
            dbc.Alert("Suggestions unavailable", color="danger")
        )

# Apply suggested query
@callback(
    Output("boolean-query", "value", allow_duplicate=True),
    Input({"type": "suggestion-btn", "query": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def apply_suggested_query(n_clicks_list):
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    
    # Get the query from the button ID
    button_id = ctx.triggered[0]["prop_id"]
    if button_id:
        # Extract query from the button ID
        import json
        try:
            # Parse the component ID to get the query
            button_data = json.loads(button_id.split('.')[0])
            return button_data.get("query", "")
        except:
            return no_update
    
    return no_update

# Collection-based tag loading
@callback(
    [Output("tags-data", "data", allow_duplicate=True),
     Output("collection-info", "children")],
    Input("load-collection-tags-btn", "n_clicks"),
    State("collection-browser", "value"),
    State("connection-type", "value"),
    prevent_initial_call=True
)
def load_collection_tags(n_clicks, collection_key, connection_type):
    if not collection_key:
        return no_update, dbc.Alert("Select a collection first", color="warning")
    
    try:
        if connection_type == "web":
            return no_update, dbc.Alert("Web API collection loading requires manual setup", color="warning")
                
        elif connection_type == "local":
            local_client = ZoteroLocalClient()
            # collection_key is now a string key for REST API
            if collection_key == "disabled":
                return no_update, dbc.Alert("Collections feature not available", color="warning")
                
            tag_freq = local_client.get_tags_for_collection(collection_key)
            
            if tag_freq:
                tags_data = [{"tag": tag, "meta": {"numItems": count}} for tag, count in tag_freq.items()]
                info_msg = dbc.Alert(f"✅ Loaded {len(tag_freq)} tags from collection", color="success")
                return tags_data, info_msg
            else:
                return no_update, dbc.Alert("No tags found in this collection", color="warning")
        
        return no_update, dbc.Alert("Collection loading not supported for current connection", color="warning")
        
    except Exception as e:
        print(f"Error loading collection tags: {e}")
        return no_update, dbc.Alert(f"Error loading collection: {str(e)}", color="danger")

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