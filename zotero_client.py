from pyzotero import zotero
from typing import List, Dict, Optional, Union
import time
import re

class ZoteroClient:
    def __init__(self, library_id: str, library_type: str, api_key: str):
        """
        Initialize Zotero client
        
        Args:
            library_id: User ID or Group ID
            library_type: 'user' or 'group'
            api_key: Zotero API key
        """
        self.library_id = library_id
        self.library_type = library_type
        self.api_key = api_key
        self.zot = zotero.Zotero(library_id, library_type, api_key)
    
    def fetch_all_tags(self) -> List[Dict]:
        """
        Fetch all tags from the library with pagination
        
        Returns:
            List of tag dictionaries containing tag name and count
        """
        print("DEBUG: Starting fast tag fetch...")
        all_tags = []
        start = 0
        limit = 100
        
        while True:
            try:
                # Get tags (no artificial delay - Zotero API is reasonable)
                tags_batch = self.zot.tags(start=start, limit=limit)
                print(f"DEBUG: Fetched batch of {len(tags_batch) if tags_batch else 0} tags")
                
                if not tags_batch:
                    break
                
                # Debug: check format of tags
                if start == 0 and tags_batch:
                    print(f"DEBUG: First tag type: {type(tags_batch[0])}")
                    print(f"DEBUG: First tag content: {tags_batch[0]}")
                
                all_tags.extend(tags_batch)
                
                if len(tags_batch) < limit:
                    break
                    
                start += limit
                
            except Exception as e:
                print(f"ERROR: Error fetching tags: {e}")
                break
        
        print(f"DEBUG: Total tags fetched: {len(all_tags)}")
        return all_tags
    
    def get_tag_frequencies_fast(self) -> Dict[str, int]:
        """
        Get tag frequencies by first fetching all tags, then getting count per tag
        This is faster than fetching all items
        
        Returns:
            Dictionary mapping tag names to their frequencies
        """
        print("DEBUG: Starting fast tag frequency calculation...")
        
        # First get all tag names
        all_tags = self.fetch_all_tags()
        if not all_tags:
            return {}
        
        # Convert to list of tag names if they're strings
        if isinstance(all_tags[0], str):
            tag_names = all_tags
        else:
            tag_names = [tag.get('tag', str(tag)) for tag in all_tags]
        
        print(f"DEBUG: Got {len(tag_names)} unique tags, now counting frequencies...")
        
        tag_frequencies = {}
        
        # For each tag, get count of items with that tag
        for i, tag_name in enumerate(tag_names):
            try:
                # Get items with this specific tag to count frequency
                # Use limit=100 and count the results - this is efficient
                items = self.zot.items(tag=tag_name, limit=100)
                count = len(items)
                
                # If we got 100 items, there might be more - get total count
                if count == 100:
                    # Get all items for this tag to get accurate count
                    all_items = self.zot.everything(self.zot.items(tag=tag_name))
                    count = len(all_items)
                
                if count > 0:
                    tag_frequencies[tag_name] = count
                
                if i % 25 == 0:  # Progress update every 25 tags
                    print(f"DEBUG: Processed {i}/{len(tag_names)} tags...")
                
            except Exception as e:
                print(f"DEBUG: Error getting count for tag '{tag_name}': {e}")
                continue
        
        print(f"DEBUG: Calculated frequencies for {len(tag_frequencies)} tags")
        return tag_frequencies
    
    def get_items_with_tags(self) -> List[Dict]:
        """
        Fetch all items with their tags
        
        Returns:
            List of items with tag information
        """
        try:
            print(f"DEBUG: Fetching items from library {self.library_id} ({self.library_type})")
            items = self.zot.everything(self.zot.items())
            print(f"DEBUG: Fetched {len(items)} items from Zotero")
            
            # Debug: Show structure of first item
            if items:
                first_item = items[0]
                print(f"DEBUG: First item keys: {list(first_item.keys())}")
                if 'data' in first_item:
                    print(f"DEBUG: First item data keys: {list(first_item['data'].keys())}")
                    if 'tags' in first_item['data']:
                        print(f"DEBUG: First item has {len(first_item['data']['tags'])} tags")
                        if first_item['data']['tags']:
                            print(f"DEBUG: Sample tag: {first_item['data']['tags'][0]}")
            
            return items
        except Exception as e:
            print(f"ERROR: Error fetching items: {e}")
            return []
    
    def test_connection(self) -> bool:
        """
        Test if the connection to Zotero API works
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch just one item to test connection
            self.zot.items(limit=1)
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def get_collections(self) -> List[Dict]:
        """
        Retrieve all collections from the library
        
        Returns:
            List of collection dictionaries with id, name, parentCollection
        """
        try:
            collections = self.zot.collections()
            print(f"DEBUG: Retrieved {len(collections)} collections")
            return collections
        except Exception as e:
            print(f"ERROR: Error fetching collections: {e}")
            return []
    
    def get_top_level_collections(self) -> List[Dict]:
        """
        Retrieve only top-level collections (no parent)
        
        Returns:
            List of top-level collection dictionaries
        """
        try:
            collections = self.zot.collections_top()
            print(f"DEBUG: Retrieved {len(collections)} top-level collections")
            return collections
        except Exception as e:
            print(f"ERROR: Error fetching top-level collections: {e}")
            return []
    
    def get_collection_items(self, collection_key: str) -> List[Dict]:
        """
        Get all items in a specific collection
        
        Args:
            collection_key: Zotero collection key
            
        Returns:
            List of items in the collection
        """
        try:
            items = self.zot.everything(self.zot.collection_items(collection_key))
            print(f"DEBUG: Retrieved {len(items)} items from collection {collection_key}")
            return items
        except Exception as e:
            print(f"ERROR: Error fetching items from collection {collection_key}: {e}")
            return []
    
    def search_items(self, 
                    query: str = None,
                    item_type: str = None,
                    tags: Union[str, List[str]] = None,
                    qmode: str = 'titleCreatorYear',
                    since: int = None,
                    sort: str = 'dateModified',
                    direction: str = 'desc',
                    limit: int = 100) -> List[Dict]:
        """
        Advanced search for items with multiple parameters
        
        Args:
            query: Search query string
            item_type: Item type filter (supports Boolean: 'book || article')
            tags: Tag filter (string or list, supports Boolean)
            qmode: Search mode ('titleCreatorYear' or 'everything')
            since: Library version to filter by modification date
            sort: Sort field (dateAdded, dateModified, title, creator, etc.)
            direction: Sort direction ('asc' or 'desc')
            limit: Maximum results to return
            
        Returns:
            List of matching items
        """
        try:
            search_params = {}
            
            # Add search parameters
            if query:
                search_params['q'] = query
                search_params['qmode'] = qmode
            
            if item_type:
                search_params['itemType'] = item_type
            
            if tags:
                if isinstance(tags, list):
                    # For list of tags, create AND query
                    search_params['tag'] = tags
                else:
                    # For string, support Boolean operators
                    search_params['tag'] = tags
            
            if since:
                search_params['since'] = since
            
            # Sorting and pagination
            search_params['sort'] = sort
            search_params['direction'] = direction
            search_params['limit'] = limit
            
            print(f"DEBUG: Searching items with parameters: {search_params}")
            
            # Use everything() to get all results if needed
            if limit > 100:
                items = self.zot.everything(self.zot.items(**search_params))
            else:
                items = self.zot.items(**search_params)
            
            print(f"DEBUG: Found {len(items)} items matching search criteria")
            return items
            
        except Exception as e:
            print(f"ERROR: Error searching items: {e}")
            return []
    
    def get_items_by_tag_boolean(self, tag_query: str) -> List[Dict]:
        """
        Search items using Boolean tag operations
        
        Args:
            tag_query: Boolean tag query (e.g., 'python || programming', 'research && -draft')
            
        Returns:
            List of matching items
        """
        try:
            items = self.search_items(tags=tag_query)
            return items
        except Exception as e:
            print(f"ERROR: Error in Boolean tag search: {e}")
            return []
    
    def get_items_by_date_range(self, 
                               start_year: int = None, 
                               end_year: int = None,
                               item_types: List[str] = None) -> List[Dict]:
        """
        Get items filtered by publication date range
        
        Args:
            start_year: Earliest publication year
            end_year: Latest publication year  
            item_types: List of item types to include
            
        Returns:
            List of items within date range
        """
        try:
            # Get all items first, then filter by date
            # Note: Zotero API doesn't directly support date range filtering
            search_params = {}
            
            if item_types:
                # Create Boolean OR query for multiple item types
                if len(item_types) == 1:
                    search_params['itemType'] = item_types[0]
                else:
                    search_params['itemType'] = ' || '.join(item_types)
            
            items = self.zot.everything(self.zot.items(**search_params))
            
            # Filter by date range locally
            filtered_items = []
            for item in items:
                if 'data' in item and 'date' in item['data']:
                    date_str = item['data']['date']
                    if date_str:
                        # Extract year from date string (handles various formats)
                        year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
                        if year_match:
                            year = int(year_match.group())
                            
                            # Check if year is within range
                            if start_year and year < start_year:
                                continue
                            if end_year and year > end_year:
                                continue
                            
                            filtered_items.append(item)
            
            print(f"DEBUG: Filtered {len(filtered_items)} items by date range {start_year}-{end_year}")
            return filtered_items
            
        except Exception as e:
            print(f"ERROR: Error filtering by date range: {e}")
            return []
    
    def get_tags_for_collection(self, collection_key: str) -> Dict[str, int]:
        """
        Get tag frequencies for items in a specific collection
        
        Args:
            collection_key: Zotero collection key
            
        Returns:
            Dictionary mapping tag names to frequencies within the collection
        """
        try:
            # Get items in collection
            items = self.get_collection_items(collection_key)
            
            # Count tag frequencies
            tag_freq = {}
            for item in items:
                if 'data' in item and 'tags' in item['data']:
                    for tag_info in item['data']['tags']:
                        tag_name = tag_info.get('tag', '') if isinstance(tag_info, dict) else str(tag_info)
                        if tag_name:
                            tag_freq[tag_name] = tag_freq.get(tag_name, 0) + 1
            
            print(f"DEBUG: Found {len(tag_freq)} unique tags in collection {collection_key}")
            return tag_freq
            
        except Exception as e:
            print(f"ERROR: Error getting tags for collection: {e}")
            return {}
    
    def get_item_metadata_summary(self) -> Dict[str, any]:
        """
        Get a summary of available metadata in the library
        
        Returns:
            Dictionary with metadata statistics (item types, years, creators, etc.)
        """
        try:
            # Get a sample of items to analyze metadata
            items = self.zot.items(limit=100)
            
            item_types = set()
            years = set()
            creators = set()
            languages = set()
            publishers = set()
            
            for item in items:
                if 'data' in item:
                    data = item['data']
                    
                    # Item type
                    if 'itemType' in data:
                        item_types.add(data['itemType'])
                    
                    # Publication year
                    if 'date' in data and data['date']:
                        year_match = re.search(r'\b(19|20)\d{2}\b', data['date'])
                        if year_match:
                            years.add(int(year_match.group()))
                    
                    # Creators
                    if 'creators' in data:
                        for creator in data['creators']:
                            if 'lastName' in creator:
                                creators.add(creator['lastName'])
                    
                    # Language
                    if 'language' in data and data['language']:
                        languages.add(data['language'])
                    
                    # Publisher
                    if 'publisher' in data and data['publisher']:
                        publishers.add(data['publisher'])
            
            summary = {
                'item_types': sorted(list(item_types)),
                'year_range': (min(years), max(years)) if years else (None, None),
                'total_creators': len(creators),
                'languages': sorted(list(languages)),
                'total_publishers': len(publishers),
                'sample_size': len(items)
            }
            
            print(f"DEBUG: Metadata summary: {summary}")
            return summary
            
        except Exception as e:
            print(f"ERROR: Error getting metadata summary: {e}")
            return {}