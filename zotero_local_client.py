import requests
import json
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin
import time
import re


class ZoteroLocalClient:
    """
    Client for Zotero local API (localhost:23119)
    Works with running Zotero desktop application
    """
    
    def __init__(self, base_url: str = "http://localhost:23119"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10
    
    def test_connection(self) -> bool:
        """
        Test if local Zotero instance is running and accessible
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test connector ping endpoint (this is what actually works)
            response = self.session.get(f"{self.base_url}/connector/ping", timeout=5)
            if response.status_code == 200 and "Zotero is running" in response.text:
                print("DEBUG: Local Zotero instance detected via connector API")
                return True
            
            print(f"DEBUG: Local Zotero connector ping failed: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Local Zotero connection failed: {e}")
            return False
    
    def test_better_bibtex(self) -> bool:
        """
        Test if Better BibTeX plugin is available
        
        Returns:
            True if Better BibTeX is available, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/better-bibtex/", timeout=5)
            if response.status_code in [200, 404]:  # 404 might be normal for root endpoint
                print("DEBUG: Better BibTeX plugin detected")
                return True
            
            return False
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Better BibTeX not available: {e}")
            return False
    
    def execute_javascript(self, script: str) -> Optional[Dict]:
        """
        Execute JavaScript in Zotero context using debug bridge
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result dictionary or None if failed
        """
        try:
            endpoint = f"{self.base_url}/debug-bridge/execute"
            data = {"script": script}
            
            response = self.session.post(
                endpoint,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"DEBUG: JavaScript execution failed: {response.status_code}")
                print(f"DEBUG: Response content: {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: JavaScript execution error: {e}")
            print(f"DEBUG: Debug bridge endpoint: {endpoint}")
            return None
    
    def get_all_tags_with_frequencies(self) -> Dict[str, int]:
        """
        Get all tags with their frequencies using the local API
        
        Returns:
            Dictionary mapping tag names to frequencies
        """
        print("DEBUG: Fetching tags from local Zotero API...")
        
        try:
            # Use the local API endpoint for tags
            response = self.session.get(f"{self.base_url}/api/users/0/tags", timeout=30)
            
            if response.status_code == 200:
                tags_data = response.json()
                tag_frequencies = {}
                
                for tag_info in tags_data:
                    tag_name = tag_info.get('tag', '')
                    num_items = tag_info.get('meta', {}).get('numItems', 1)
                    
                    if tag_name:
                        tag_frequencies[tag_name] = num_items
                
                print(f"DEBUG: Successfully retrieved {len(tag_frequencies)} tags from local API")
                return tag_frequencies
            
            else:
                print(f"DEBUG: Local API returned status {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Error fetching from local API: {e}")
            return {}
    
    def get_library_info(self) -> Optional[Dict]:
        """
        Get basic library information using local API
        
        Returns:
            Library info dictionary or None if failed
        """
        try:
            # Get a few items to understand the library structure
            response = self.session.get(f"{self.base_url}/api/users/0/items?limit=1", timeout=10)
            
            if response.status_code == 200:
                items_data = response.json()
                
                if items_data and len(items_data) > 0:
                    first_item = items_data[0]
                    library_info = first_item.get('library', {})
                    
                    return {
                        'libraryID': library_info.get('id', 0),
                        'libraryName': library_info.get('name', 'Local Zotero Library'),
                        'libraryType': library_info.get('type', 'user'),
                        'api_available': True
                    }
                
                # If no items, still return basic info
                return {
                    'libraryID': 0,
                    'libraryName': 'Local Zotero Library',
                    'libraryType': 'user',
                    'api_available': True
                }
            
            else:
                print(f"DEBUG: Library info API returned status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Error getting library info: {e}")
            return None
    
    def get_collections(self) -> List[Dict]:
        """
        Get all collections from local Zotero using REST API
        
        Returns:
            List of collection dictionaries
        """
        try:
            print("DEBUG: Getting collections via REST API...")
            response = self.session.get(f"{self.base_url}/api/users/0/collections", timeout=30)
            
            if response.status_code == 200:
                collections_data = response.json()
                collections = []
                
                for col in collections_data:
                    data = col.get('data', {})
                    collections.append({
                        'key': col.get('key'),
                        'id': col.get('key'),  # Use key as id for REST API
                        'name': data.get('name', 'Unknown Collection'),
                        'parentCollection': data.get('parentCollection'),
                        'itemCount': 0  # Will be populated separately if needed
                    })
                
                print(f"DEBUG: Found {len(collections)} collections via REST API")
                return collections
            
            else:
                print(f"DEBUG: Collections API failed with status {response.status_code}")
                return []
        
        except Exception as e:
            print(f"DEBUG: Error getting collections via REST API: {e}")
            return []
    
    def get_tags_for_collection(self, collection_key: str) -> Dict[str, int]:
        """
        Get tags with frequencies for a specific collection using REST API
        
        Args:
            collection_key: Zotero collection key (string)
            
        Returns:
            Dictionary mapping tag names to frequencies
        """
        try:
            print(f"DEBUG: Getting tags for collection {collection_key} via REST API...")
            
            # Get items in the collection
            url = f"{self.base_url}/api/users/0/collections/{collection_key}/items?itemType=-annotation&itemType=-attachment"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                items = response.json()
                tag_freq = {}
                
                for item in items:
                    item_tags = item.get('data', {}).get('tags', [])
                    for tag_obj in item_tags:
                        tag_name = tag_obj.get('tag')
                        if tag_name:
                            tag_freq[tag_name] = tag_freq.get(tag_name, 0) + 1
                
                print(f"DEBUG: Found {len(tag_freq)} unique tags in collection {collection_key}")
                return tag_freq
            
            else:
                print(f"DEBUG: Collection items API failed with status {response.status_code}")
                return {}
        
        except Exception as e:
            print(f"DEBUG: Error getting collection tags via REST API: {e}")
            return {}
    
    def search_items(self, query: str) -> List[Dict]:
        """
        Search items in local Zotero
        
        Args:
            query: Search query
            
        Returns:
            List of matching items
        """
        script = f"""
        // Search items
        let searchResults = [];
        let search = new Zotero.Search();
        search.addCondition('quicksearch-titleCreatorYear', 'contains', '{query}');
        
        let itemIDs = await search.search();
        
        for (let itemID of itemIDs.slice(0, 100)) {{ // Limit to 100 results
            let item = Zotero.Items.get(itemID);
            if (item && item.isRegularItem()) {{
                searchResults.push({{
                    id: item.id,
                    key: item.key,
                    title: item.getField('title') || 'Untitled',
                    creators: item.getCreators().map(c => c.firstName + ' ' + c.lastName).join(', '),
                    date: item.getField('date') || '',
                    tags: item.getTags().map(t => t.tag)
                }});
            }}
        }}
        
        return searchResults;
        """
        
        result = self.execute_javascript(script)
        
        if result and 'return' in result:
            return result['return'] or []
        
        return []
    
    def get_connection_info(self) -> Dict[str, any]:
        """
        Get comprehensive connection information
        
        Returns:
            Dictionary with connection details
        """
        info = {
            'type': 'local',
            'base_url': self.base_url,
            'connected': False,
            'better_bibtex': False,
            'library_info': None,
            'collections_count': 0,
            'error': None
        }
        
        try:
            # Test basic connection
            info['connected'] = self.test_connection()
            
            if info['connected']:
                # Test Better BibTeX
                info['better_bibtex'] = self.test_better_bibtex()
                
                # Get library info
                lib_info = self.get_library_info()
                if lib_info:
                    info['library_info'] = lib_info
                    
                    # Get collections count
                    collections = self.get_collections()
                    info['collections_count'] = len(collections)
                else:
                    info['error'] = "Could not retrieve library information"
            else:
                info['error'] = "Could not connect to local Zotero instance"
                
        except Exception as e:
            info['error'] = f"Connection error: {str(e)}"
        
        return info
    
    def get_items_filtered(self, 
                          collection_id: int = None,
                          item_types: List[str] = None,
                          tags: List[str] = None,
                          start_year: int = None,
                          end_year: int = None,
                          search_query: str = None) -> List[Dict]:
        """
        Get items with advanced filtering
        
        Args:
            collection_id: Filter by collection ID
            item_types: List of item types to include
            tags: List of tags (AND operation)
            start_year: Earliest publication year
            end_year: Latest publication year
            search_query: Search query for title/author
            
        Returns:
            List of filtered items
        """
        script = f"""
        // Advanced item filtering
        let filteredItems = [];
        let searchResults = [];
        
        // Start with all items or collection items
        let allItems = [];
        if ({collection_id}) {{
            let collection = Zotero.Collections.get({collection_id});
            if (collection) {{
                allItems = collection.getChildItems();
            }}
        }} else {{
            allItems = Zotero.Items.getAll();
        }}
        
        // Filter items
        for (let item of allItems) {{
            if (!item.isRegularItem()) continue;
            
            let itemData = {{
                id: item.id,
                key: item.key,
                title: item.getField('title') || 'Untitled',
                itemType: item.itemType,
                date: item.getField('date') || '',
                creators: item.getCreators().map(c => (c.firstName || '') + ' ' + (c.lastName || '')).join(', '),
                tags: item.getTags().map(t => t.tag),
                year: null
            }};
            
            // Extract year from date
            if (itemData.date) {{
                let yearMatch = itemData.date.match(/\\b(19|20)\\d{{2}}\\b/);
                if (yearMatch) {{
                    itemData.year = parseInt(yearMatch[0]);
                }}
            }}
            
            // Apply filters
            let passesFilter = true;
            
            // Item type filter
            {f"if ({json.dumps(item_types)}) {{" if item_types else "// No item type filter"}
                {"let allowedTypes = " + json.dumps(item_types) + ";" if item_types else ""}
                {"if (!allowedTypes.includes(itemData.itemType)) passesFilter = false;" if item_types else ""}
            {f"}}" if item_types else ""}
            
            // Tag filter (AND operation)
            {f"if ({json.dumps(tags)}) {{" if tags else "// No tag filter"}
                {"let requiredTags = " + json.dumps(tags) + ";" if tags else ""}
                {"for (let requiredTag of requiredTags) {{" if tags else ""}
                    {"if (!itemData.tags.includes(requiredTag)) {{ passesFilter = false; break; }}" if tags else ""}
                {"}" if tags else ""}
            {f"}}" if tags else ""}
            
            // Year range filter
            if (itemData.year) {{
                {f"if ({start_year} && itemData.year < {start_year}) passesFilter = false;" if start_year else ""}
                {f"if ({end_year} && itemData.year > {end_year}) passesFilter = false;" if end_year else ""}
            }}
            
            // Search query filter
            {f"if ('{search_query}') {{" if search_query else "// No search query"}
                {"let query = '" + (search_query or '').lower() + "';" if search_query else ""}
                {"let searchText = (itemData.title + ' ' + itemData.creators).toLowerCase();" if search_query else ""}
                {"if (!searchText.includes(query)) passesFilter = false;" if search_query else ""}
            {f"}}" if search_query else ""}
            
            if (passesFilter) {{
                filteredItems.push(itemData);
            }}
        }}
        
        return filteredItems;
        """
        
        result = self.execute_javascript(script)
        
        if result and 'return' in result:
            return result['return'] or []
        
        return []
    
    def get_items_by_tag_boolean(self, tag_query: str) -> List[Dict]:
        """
        Search items using Boolean tag operations
        
        Args:
            tag_query: Boolean tag query (e.g., 'python OR programming', 'research AND NOT draft')
            
        Returns:
            List of matching items
        """
        # Parse the boolean query
        # Convert to JavaScript-compatible format
        js_query = tag_query.replace(' AND ', ' && ').replace(' OR ', ' || ').replace(' NOT ', ' !')
        
        script = f"""
        // Boolean tag search
        let matchingItems = [];
        let allItems = Zotero.Items.getAll();
        
        for (let item of allItems) {{
            if (!item.isRegularItem()) continue;
            
            let itemTags = item.getTags().map(t => t.tag);
            let itemData = {{
                id: item.id,
                key: item.key,
                title: item.getField('title') || 'Untitled',
                itemType: item.itemType,
                date: item.getField('date') || '',
                creators: item.getCreators().map(c => (c.firstName || '') + ' ' + (c.lastName || '')).join(', '),
                tags: itemTags
            }};
            
            // Simple boolean evaluation (this is a simplified version)
            // In practice, you'd want a more robust parser
            let queryParts = '{js_query}'.split(/\\s+(&&|\\|\\||!)\\s+/);
            let operators = '{js_query}'.match(/\\s+(&&|\\|\\||!)\\s+/g) || [];
            
            // For now, implement simple AND/OR logic
            let matches = false;
            if ('{tag_query}'.includes(' OR ')) {{
                let orTags = '{tag_query}'.split(' OR ').map(t => t.trim());
                matches = orTags.some(tag => itemTags.includes(tag));
            }} else if ('{tag_query}'.includes(' AND ')) {{
                let andTags = '{tag_query}'.split(' AND ').map(t => t.trim());
                matches = andTags.every(tag => itemTags.includes(tag));
            }} else {{
                // Single tag
                matches = itemTags.includes('{tag_query}');
            }}
            
            if (matches) {{
                matchingItems.push(itemData);
            }}
        }}
        
        return matchingItems;
        """
        
        result = self.execute_javascript(script)
        
        if result and 'return' in result:
            return result['return'] or []
        
        return []
    
    def get_tag_cooccurrence(self, tag_list: List[str] = None, min_cooccurrence: int = 2) -> Dict[str, Dict[str, int]]:
        """
        Analyze tag co-occurrence patterns
        
        Args:
            tag_list: List of tags to analyze (None for all tags)
            min_cooccurrence: Minimum co-occurrence count to include
            
        Returns:
            Dictionary of tag -> {co-occurring_tag: count}
        """
        script = f"""
        // Tag co-occurrence analysis
        let cooccurrence = {{}};
        let allItems = Zotero.Items.getAll();
        
        for (let item of allItems) {{
            if (!item.isRegularItem()) continue;
            
            let itemTags = item.getTags().map(t => t.tag);
            
            // For each pair of tags in this item
            for (let i = 0; i < itemTags.length; i++) {{
                for (let j = i + 1; j < itemTags.length; j++) {{
                    let tag1 = itemTags[i];
                    let tag2 = itemTags[j];
                    
                    // Initialize if needed
                    if (!cooccurrence[tag1]) cooccurrence[tag1] = {{}};
                    if (!cooccurrence[tag2]) cooccurrence[tag2] = {{}};
                    
                    // Count co-occurrences
                    cooccurrence[tag1][tag2] = (cooccurrence[tag1][tag2] || 0) + 1;
                    cooccurrence[tag2][tag1] = (cooccurrence[tag2][tag1] || 0) + 1;
                }}
            }}
        }}
        
        // Filter by minimum co-occurrence
        let filtered = {{}};
        for (let tag in cooccurrence) {{
            filtered[tag] = {{}};
            for (let coTag in cooccurrence[tag]) {{
                if (cooccurrence[tag][coTag] >= {min_cooccurrence}) {{
                    filtered[tag][coTag] = cooccurrence[tag][coTag];
                }}
            }}
            if (Object.keys(filtered[tag]).length === 0) {{
                delete filtered[tag];
            }}
        }}
        
        return filtered;
        """
        
        result = self.execute_javascript(script)
        
        if result and 'return' in result:
            return result['return'] or {}
        
        return {}
    
    def get_library_metadata_summary(self) -> Dict[str, any]:
        """
        Get comprehensive metadata summary from local library
        
        Returns:
            Dictionary with metadata statistics
        """
        print("DEBUG: Attempting to get metadata summary via JavaScript execution...")
        
        script = """
        // Library metadata summary
        let summary = {
            itemTypes: {},
            years: {},
            creators: {},
            languages: {},
            publishers: {},
            totalItems: 0,
            collectionsCount: 0
        };
        
        let allItems = Zotero.Items.getAll();
        let allCollections = Zotero.Collections.getAll();
        
        summary.collectionsCount = allCollections.length;
        
        for (let item of allItems) {
            if (!item.isRegularItem()) continue;
            
            summary.totalItems++;
            
            // Item type
            let itemType = item.itemType;
            summary.itemTypes[itemType] = (summary.itemTypes[itemType] || 0) + 1;
            
            // Year
            let date = item.getField('date');
            if (date) {
                let yearMatch = date.match(/\\b(19|20)\\d{2}\\b/);
                if (yearMatch) {
                    let year = yearMatch[0];
                    summary.years[year] = (summary.years[year] || 0) + 1;
                }
            }
            
            // Creators
            let creators = item.getCreators();
            for (let creator of creators) {
                if (creator.lastName) {
                    summary.creators[creator.lastName] = (summary.creators[creator.lastName] || 0) + 1;
                }
            }
            
            // Language
            let language = item.getField('language');
            if (language) {
                summary.languages[language] = (summary.languages[language] || 0) + 1;
            }
            
            // Publisher
            let publisher = item.getField('publisher');
            if (publisher) {
                summary.publishers[publisher] = (summary.publishers[publisher] || 0) + 1;
            }
        }
        
        return summary;
        """
        
        result = self.execute_javascript(script)
        
        if result and 'return' in result:
            print(f"DEBUG: JavaScript execution successful, got {len(result['return'])} keys")
            return result['return'] or {}
        
        print("DEBUG: JavaScript execution failed, trying fallback API method...")
        # Fallback: Try to get basic metadata via local API
        return self._get_metadata_fallback()
        
    def _get_metadata_fallback(self) -> Dict[str, any]:
        """
        Fallback method to get basic metadata using local API
        
        Returns:
            Dictionary with basic metadata statistics
        """
        try:
            print("DEBUG: Using fallback API method to get metadata...")
            
            # Get sample of top-level items to extract metadata (exclude annotations and attachments)
            response = self.session.get(f"{self.base_url}/api/users/0/items?itemType=-annotation&itemType=-attachment&limit=100", timeout=30)
            
            if response.status_code == 200:
                items_data = response.json()
                
                summary = {
                    'itemTypes': {},
                    'languages': {},
                    'years': {},
                    'creators': {},
                    'totalItems': len(items_data)
                }
                
                for item in items_data:
                    data = item.get('data', {})
                    
                    # Item type
                    item_type = data.get('itemType')
                    if item_type:
                        summary['itemTypes'][item_type] = summary['itemTypes'].get(item_type, 0) + 1
                    
                    # Language
                    language = data.get('language')
                    if language:
                        summary['languages'][language] = summary['languages'].get(language, 0) + 1
                    
                    # Year from date
                    date = data.get('date')
                    if date:
                        import re
                        year_match = re.search(r'\b(19|20)\d{2}\b', str(date))
                        if year_match:
                            year = year_match.group(0)
                            summary['years'][year] = summary['years'].get(year, 0) + 1
                    
                    # Creators
                    creators = data.get('creators', [])
                    for creator in creators:
                        last_name = creator.get('lastName')
                        if last_name:
                            summary['creators'][last_name] = summary['creators'].get(last_name, 0) + 1
                
                print(f"DEBUG: Fallback method found {len(summary['itemTypes'])} item types, {len(summary['languages'])} languages")
                return summary
            
            else:
                print(f"DEBUG: Fallback API call failed with status {response.status_code}")
                
        except Exception as e:
            print(f"DEBUG: Fallback method error: {e}")
        
        # Return empty summary if all methods fail
        return {
            'itemTypes': {},
            'languages': {},
            'years': {},
            'creators': {},
            'totalItems': 0
        }
    
    def get_items_by_metadata(self, item_types=None, languages=None, start_year=None, end_year=None, limit=1000):
        """
        Get items filtered by metadata criteria
        
        Args:
            item_types: List of item types to include
            languages: List of languages to include  
            start_year: Start year for date filtering
            end_year: End year for date filtering
            limit: Maximum number of items to return
            
        Returns:
            List of item dictionaries matching criteria
        """
        try:
            # Build query parameters - exclude annotations and attachments
            url = f"{self.base_url}/api/users/0/items?limit={limit}&itemType=-annotation&itemType=-attachment"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                items_data = response.json()
                filtered_items = []
                
                for item in items_data:
                    data = item.get('data', {})
                    
                    # Filter by item type
                    if item_types:
                        item_type = data.get('itemType')
                        if item_type not in item_types:
                            continue
                    
                    # Filter by language
                    if languages:
                        language = data.get('language')
                        if language not in languages:
                            continue
                    
                    # Filter by year
                    if start_year or end_year:
                        date = data.get('date')
                        if date:
                            import re
                            year_match = re.search(r'\b(19|20)\d{2}\b', str(date))
                            if year_match:
                                year = int(year_match.group(0))
                                if start_year and year < start_year:
                                    continue
                                if end_year and year > end_year:
                                    continue
                            else:
                                continue  # No valid year found, skip if year filtering requested
                        else:
                            continue  # No date, skip if year filtering requested
                    
                    filtered_items.append(item)
                
                print(f"DEBUG: Filtered {len(filtered_items)} items from {len(items_data)} total")
                return filtered_items
            
            return []
            
        except Exception as e:
            print(f"ERROR: Failed to get filtered items: {e}")
            return []
    
    def export_filtered_data(self, 
                           collection_id: int = None,
                           item_types: List[str] = None,
                           tags: List[str] = None,
                           format: str = 'json') -> str:
        """
        Export filtered data in specified format
        
        Args:
            collection_id: Collection to export from
            item_types: Item types to include
            tags: Tags to filter by
            format: Export format ('json', 'csv', 'bibtex')
            
        Returns:
            Exported data as string
        """
        # Get filtered items
        items = self.get_items_filtered(
            collection_id=collection_id,
            item_types=item_types,
            tags=tags
        )
        
        if format == 'json':
            return json.dumps(items, indent=2)
        elif format == 'csv':
            if not items:
                return ""
            
            # Create CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=items[0].keys())
            writer.writeheader()
            
            for item in items:
                # Convert list fields to strings
                row = {}
                for key, value in item.items():
                    if isinstance(value, list):
                        row[key] = '; '.join(str(v) for v in value)
                    else:
                        row[key] = str(value) if value is not None else ''
                writer.writerow(row)
            
            return output.getvalue()
        
        # Add more export formats as needed
        return json.dumps(items, indent=2)


# Utility functions
def detect_local_zotero() -> bool:
    """
    Quick check if local Zotero is running
    
    Returns:
        True if local instance detected, False otherwise
    """
    client = ZoteroLocalClient()
    return client.test_connection()


def get_local_client_if_available() -> Optional[ZoteroLocalClient]:
    """
    Get local client if Zotero is running, otherwise None
    
    Returns:
        ZoteroLocalClient instance or None
    """
    if detect_local_zotero():
        return ZoteroLocalClient()
    return None