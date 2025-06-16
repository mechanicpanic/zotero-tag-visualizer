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
        all_tags = []
        start = 0
        limit = 100
        
        while True:
            try:
                # Add small delay to respect rate limits
                time.sleep(0.1)
                
                tags_batch = self.zot.tags(start=start, limit=limit)
                
                if not tags_batch:
                    break
                
                all_tags.extend(tags_batch)
                
                if len(tags_batch) < limit:
                    break
                    
                start += limit
                
            except Exception as e:
                print(f"Error fetching tags: {e}")
                break
        
        return all_tags
    
    def get_items_with_tags(self) -> List[Dict]:
        """
        Fetch all items with their tags
        
        Returns:
            List of items with tag information
        """
        try:
            items = self.zot.everything(self.zot.items())
            return items
        except Exception as e:
            print(f"Error fetching items: {e}")
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