import pandas as pd
from collections import Counter
from typing import List, Dict, Tuple
import re

class TagProcessor:
    def __init__(self):
        self.tags_data = []
        self.processed_tags = {}
    
    def process_zotero_tags(self, tags_data: List[Dict]) -> Dict[str, int]:
        """
        Process raw Zotero tags data into frequency dictionary
        
        Args:
            tags_data: List of tag dictionaries from Zotero API
            
        Returns:
            Dictionary mapping tag names to their frequencies
        """
        self.tags_data = tags_data
        tag_freq = {}
        
        for tag_info in tags_data:
            if isinstance(tag_info, dict):
                tag_name = tag_info.get('tag', '')
                count = tag_info.get('meta', {}).get('numItems', 1)
            else:
                # Handle case where tags are just strings
                tag_name = str(tag_info)
                count = 1
            
            if tag_name:
                tag_freq[tag_name] = count
        
        self.processed_tags = tag_freq
        return tag_freq
    
    def process_items_tags(self, items_data: List[Dict]) -> Dict[str, int]:
        """
        Extract tags from items data and count frequencies
        
        Args:
            items_data: List of Zotero items with tag information
            
        Returns:
            Dictionary mapping tag names to their frequencies
        """
        all_tags = []
        
        for item in items_data:
            if 'data' in item and 'tags' in item['data']:
                for tag_info in item['data']['tags']:
                    if isinstance(tag_info, dict) and 'tag' in tag_info:
                        all_tags.append(tag_info['tag'])
                    elif isinstance(tag_info, str):
                        all_tags.append(tag_info)
        
        tag_freq = Counter(all_tags)
        self.processed_tags = dict(tag_freq)
        return self.processed_tags
    
    def clean_tags(self, min_length: int = 2, max_length: int = 50) -> Dict[str, int]:
        """
        Clean and filter tags based on length and content
        
        Args:
            min_length: Minimum tag length to keep
            max_length: Maximum tag length to keep
            
        Returns:
            Cleaned dictionary of tags and frequencies
        """
        cleaned_tags = {}
        
        for tag, count in self.processed_tags.items():
            # Remove extra whitespace and normalize
            clean_tag = re.sub(r'\s+', ' ', tag.strip())
            
            # Filter by length
            if min_length <= len(clean_tag) <= max_length:
                # Avoid empty tags
                if clean_tag:
                    cleaned_tags[clean_tag] = count
        
        self.processed_tags = cleaned_tags
        return cleaned_tags
    
    def filter_by_frequency(self, min_freq: int = 1, max_freq: int = None) -> Dict[str, int]:
        """
        Filter tags by frequency range
        
        Args:
            min_freq: Minimum frequency to include
            max_freq: Maximum frequency to include (None for no limit)
            
        Returns:
            Filtered dictionary of tags and frequencies
        """
        filtered_tags = {}
        
        for tag, count in self.processed_tags.items():
            if count >= min_freq:
                if max_freq is None or count <= max_freq:
                    filtered_tags[tag] = count
        
        return filtered_tags
    
    def search_tags(self, search_term: str, case_sensitive: bool = False) -> Dict[str, int]:
        """
        Search for tags containing a specific term
        
        Args:
            search_term: Term to search for in tag names
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            Dictionary of matching tags and their frequencies
        """
        matching_tags = {}
        
        if not case_sensitive:
            search_term = search_term.lower()
        
        for tag, count in self.processed_tags.items():
            tag_to_search = tag if case_sensitive else tag.lower()
            
            if search_term in tag_to_search:
                matching_tags[tag] = count
        
        return matching_tags
    
    def get_top_tags(self, n: int = 50) -> Dict[str, int]:
        """
        Get the top N most frequent tags
        
        Args:
            n: Number of top tags to return
            
        Returns:
            Dictionary of top N tags and their frequencies
        """
        sorted_tags = sorted(self.processed_tags.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_tags[:n])
    
    def get_tag_statistics(self) -> Dict[str, any]:
        """
        Get basic statistics about the tags
        
        Returns:
            Dictionary containing tag statistics
        """
        if not self.processed_tags:
            return {}
        
        frequencies = list(self.processed_tags.values())
        
        return {
            'total_tags': len(self.processed_tags),
            'total_occurrences': sum(frequencies),
            'avg_frequency': sum(frequencies) / len(frequencies),
            'max_frequency': max(frequencies),
            'min_frequency': min(frequencies),
            'unique_tags': len([tag for tag, freq in self.processed_tags.items() if freq == 1])
        }