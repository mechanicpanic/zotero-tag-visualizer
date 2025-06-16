# Zotero Tag Cloud Visualizer

A Python web application that fetches tags from your Zotero library and displays them as an interactive tag cloud with filtering capabilities.

## Features

- **Zotero Integration**: Connect to both user and group Zotero libraries using API keys
- **Interactive Tag Cloud**: Visual word cloud representation of your tags
- **Multiple Visualizations**: Switch between word cloud and bar chart views
- **Advanced Filtering**: 
  - Search tags by keyword
  - Filter by frequency range
  - Limit number of displayed tags
- **Real-time Statistics**: View tag statistics and frequency data
- **Responsive Design**: Clean, modern web interface

## Installation & Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

1. **Clone or download this project**
2. **Install dependencies**:
```bash
uv sync
```

## Getting Your Zotero Credentials

### 1. API Key
1. Go to **https://www.zotero.org/settings/keys**
2. Click **"Create new private key"**
3. Give it a name (e.g., "Tag Visualizer")
4. Select permissions:
   - ✅ **Allow library access**
   - ✅ **Allow notes access** (optional)
   - Choose **Personal library** and/or specific **Groups**
5. Click **"Save Key"**
6. **Copy the generated API key** (you won't see it again!)

### 2. Library ID

#### For Personal Library:
1. Go to **https://www.zotero.org/settings/keys**
2. Your **userID** is shown at the top of the page
3. Use **Library Type**: `user`

#### For Group Library:
1. Go to your group's page on zotero.org
2. The URL will be: `https://www.zotero.org/groups/[GROUP_ID]/[group_name]`
3. The **GROUP_ID** number is your Library ID
4. Use **Library Type**: `group`

### Example Credentials:
- **Library ID**: `12345678` (your userID or group ID)
- **Library Type**: `user` (for personal) or `group` (for shared)
- **API Key**: `ABC123def456GHI789` (the key you generated)

## Running the Application

1. **Start the web app**:
```bash
uv run python app.py
```

2. **Open your browser** and navigate to `http://127.0.0.1:8050`

3. **Choose your connection method**:

### Local Zotero Mode (Faster)
1. **Start Zotero desktop application**
2. **Enable local API access**:
   - Go to **Zotero → Settings → Advanced → Config Editor**
   - Set `extensions.zotero.httpServer.enabled` to `true`
   - Set `extensions.zotero.httpServer.port` to `23119`
   - Enable **"Allow other applications on this computer to communicate with Zotero"** in Settings → Advanced
3. **Select "Local Zotero Instance"** in the web app
4. **Click "Load Tags from Local Zotero"**

### Web API Mode (Internet Required)
1. **Select "Web API"** in the web app
2. **Enter your Zotero credentials**:
   - Library ID
   - Library Type (user or group)  
   - API Key
3. **Test your connection** by clicking "Test Connection"
4. **Load your tags** by clicking "Load Tags"

6. **Apply filters** to customize your visualization:
   - **Search Tags**: Filter tags containing specific keywords
   - **Min/Max Frequency**: Show only tags within a frequency range
   - **Max Tags**: Limit the number of tags displayed

7. **View your tag cloud** in the Word Cloud or Bar Chart tabs

## Project Structure

- `pyproject.toml` - Project configuration and dependencies
- `app.py` - Main Dash web application
- `zotero_client.py` - Zotero API integration and data fetching
- `tag_processor.py` - Tag data processing and filtering
- `README.md` - This documentation

## Important Security Notes

- **Keep your API key secure** - don't share it publicly or commit it to version control
- The API key gives access to your library data
- You can revoke/regenerate keys anytime in your Zotero settings
- The app only reads your library data, it doesn't modify anything

## API Rate Limiting

The application includes built-in rate limiting to respect Zotero's API limits. Large libraries may take some time to load all tags.

## Troubleshooting

- **Connection Issues**: Verify your Library ID, Library Type, and API Key are correct
- **No Tags Found**: Ensure your library contains items with tags
- **Slow Loading**: Large libraries may take time to process; the app will show loading indicators
- **Import Errors**: Make sure you're using `uv run python app.py` to run with the correct environment

## Alternative Installation (without uv)

If you prefer not to use uv, you can use pip:

```bash
pip install -r requirements.txt
python app.py
```

## License

This project is open source and available under the MIT License.