from pyzotero import zotero
from typing import List, Dict, Optional
import time

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