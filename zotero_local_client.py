import requests
import json
from typing import List, Dict, Optional
from urllib.parse import urljoin
import time


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
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: JavaScript execution error: {e}")
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
        Get all collections from local Zotero
        
        Returns:
            List of collection dictionaries
        """
        script = """
        // Get all collections
        let collections = [];
        let allCollections = Zotero.Collections.getAll();
        
        for (let collection of allCollections) {
            collections.push({
                id: collection.id,
                key: collection.key,
                name: collection.name,
                parentID: collection.parentID,
                itemCount: collection.getChildItems().length
            });
        }
        
        return collections;
        """
        
        result = self.execute_javascript(script)
        
        if result and 'return' in result:
            return result['return'] or []
        
        return []
    
    def get_tags_for_collection(self, collection_id: int) -> Dict[str, int]:
        """
        Get tags with frequencies for a specific collection
        
        Args:
            collection_id: Zotero collection ID
            
        Returns:
            Dictionary mapping tag names to frequencies
        """
        script = f"""
        // Get tags for specific collection
        let tags = {{}};
        let collection = Zotero.Collections.get({collection_id});
        
        if (collection) {{
            let items = collection.getChildItems();
            
            for (let item of items) {{
                if (item.isRegularItem()) {{
                    let itemTags = item.getTags();
                    for (let tagObj of itemTags) {{
                        let tagName = tagObj.tag;
                        if (tags[tagName]) {{
                            tags[tagName]++;
                        }} else {{
                            tags[tagName] = 1;
                        }}
                    }}
                }}
            }}
        }}
        
        return tags;
        """
        
        result = self.execute_javascript(script)
        
        if result and 'return' in result:
            return result['return'] or {}
        
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