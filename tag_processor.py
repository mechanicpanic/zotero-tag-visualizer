import pandas as pd
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional, Set, Union
import re
import json

class TagProcessor:
    def __init__(self):
        self.tags_data = []
        self.processed_tags = {}
        self.items_data = []  # Store full items data for metadata filtering
        self.metadata_cache = {}  # Cache for metadata analysis
    
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
        print(f"DEBUG: Processing {len(items_data)} items for tags")
        all_tags = []
        items_with_tags = 0
        
        for i, item in enumerate(items_data):
            if 'data' in item and 'tags' in item['data']:
                item_tags = item['data']['tags']
                if item_tags:  # Only count items that actually have tags
                    items_with_tags += 1
                    if i < 3:  # Debug first few items
                        print(f"DEBUG: Item {i} has {len(item_tags)} tags: {[t.get('tag', t) if isinstance(t, dict) else str(t) for t in item_tags[:3]]}")
                
                for tag_info in item_tags:
                    if isinstance(tag_info, dict) and 'tag' in tag_info:
                        all_tags.append(tag_info['tag'])
                    elif isinstance(tag_info, str):
                        all_tags.append(tag_info)
        
        print(f"DEBUG: Found {items_with_tags} items with tags out of {len(items_data)} total items")
        print(f"DEBUG: Collected {len(all_tags)} total tag instances")
        
        tag_freq = Counter(all_tags)
        print(f"DEBUG: Found {len(tag_freq)} unique tags")
        
        # Show top 5 most frequent tags
        if tag_freq:
            top_tags = tag_freq.most_common(5)
            print(f"DEBUG: Top 5 tags: {top_tags}")
        
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
    
    def process_items_with_metadata(self, items_data: List[Dict]) -> Dict[str, int]:
        """
        Process items data with full metadata for advanced filtering
        
        Args:
            items_data: List of Zotero items with complete metadata
            
        Returns:
            Dictionary mapping tag names to their frequencies
        """
        self.items_data = items_data
        print(f"DEBUG: Processing {len(items_data)} items with metadata")
        
        # Extract tags and build metadata relationships
        tag_item_map = defaultdict(list)  # tag -> list of item indices
        all_tags = []
        
        for i, item in enumerate(items_data):
            if 'data' in item and 'tags' in item['data']:
                item_tags = item['data']['tags']
                for tag_info in item_tags:
                    tag_name = tag_info.get('tag', '') if isinstance(tag_info, dict) else str(tag_info)
                    if tag_name:
                        all_tags.append(tag_name)
                        tag_item_map[tag_name].append(i)
        
        # Calculate frequencies
        tag_freq = Counter(all_tags)
        self.processed_tags = dict(tag_freq)
        
        # Cache metadata relationships
        self.metadata_cache['tag_item_map'] = dict(tag_item_map)
        
        print(f"DEBUG: Found {len(tag_freq)} unique tags with metadata")
        return self.processed_tags
    
    def filter_tags_by_metadata(self, 
                                item_types: List[str] = None,
                                start_year: int = None,
                                end_year: int = None,
                                creators: List[str] = None,
                                collections: List[str] = None,
                                languages: List[str] = None) -> Dict[str, int]:
        """
        Filter tags based on item metadata criteria
        
        Args:
            item_types: List of item types to include
            start_year: Earliest publication year
            end_year: Latest publication year
            creators: List of creator names (partial match)
            collections: List of collection names
            languages: List of languages
            
        Returns:
            Filtered dictionary of tags and frequencies
        """
        if not self.items_data:
            print("WARNING: No items data available for metadata filtering")
            return self.processed_tags
        
        # Get items that match metadata criteria
        matching_item_indices = set()
        
        for i, item in enumerate(self.items_data):
            if 'data' not in item:
                continue
                
            data = item['data']
            matches_criteria = True
            
            # Item type filter
            if item_types and data.get('itemType') not in item_types:
                matches_criteria = False
            
            # Year range filter
            if (start_year or end_year) and 'date' in data and data['date']:
                year_match = re.search(r'\b(19|20)\d{2}\b', data['date'])
                if year_match:
                    year = int(year_match.group())
                    if start_year and year < start_year:
                        matches_criteria = False
                    if end_year and year > end_year:
                        matches_criteria = False
                else:
                    matches_criteria = False
            
            # Creator filter
            if creators and 'creators' in data:
                creator_match = False
                item_creators = data['creators']
                for creator_filter in creators:
                    for creator in item_creators:
                        creator_name = f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()
                        if creator_filter.lower() in creator_name.lower():
                            creator_match = True
                            break
                    if creator_match:
                        break
                if not creator_match:
                    matches_criteria = False
            
            # Language filter
            if languages and data.get('language') not in languages:
                matches_criteria = False
            
            if matches_criteria:
                matching_item_indices.add(i)
        
        # Count tags only from matching items
        filtered_tags = defaultdict(int)
        tag_item_map = self.metadata_cache.get('tag_item_map', {})
        
        for tag, item_indices in tag_item_map.items():
            count = len([idx for idx in item_indices if idx in matching_item_indices])
            if count > 0:
                filtered_tags[tag] = count
        
        print(f"DEBUG: Metadata filtering reduced tags from {len(self.processed_tags)} to {len(filtered_tags)}")
        return dict(filtered_tags)
    
    def get_tag_cooccurrence_matrix(self, min_cooccurrence: int = 2) -> Dict[str, Dict[str, int]]:
        """
        Calculate tag co-occurrence matrix
        
        Args:
            min_cooccurrence: Minimum co-occurrence count to include
            
        Returns:
            Dictionary of tag -> {co-occurring_tag: count}
        """
        if not self.items_data:
            return {}
        
        cooccurrence = defaultdict(lambda: defaultdict(int))
        
        for item in self.items_data:
            if 'data' not in item or 'tags' not in item['data']:
                continue
            
            # Get tags for this item
            item_tags = []
            for tag_info in item['data']['tags']:
                tag_name = tag_info.get('tag', '') if isinstance(tag_info, dict) else str(tag_info)
                if tag_name:
                    item_tags.append(tag_name)
            
            # Calculate co-occurrences for all tag pairs in this item
            for i in range(len(item_tags)):
                for j in range(i + 1, len(item_tags)):
                    tag1, tag2 = item_tags[i], item_tags[j]
                    cooccurrence[tag1][tag2] += 1
                    cooccurrence[tag2][tag1] += 1
        
        # Filter by minimum co-occurrence
        filtered_cooccurrence = {}
        for tag1, cooccur_dict in cooccurrence.items():
            filtered_dict = {tag2: count for tag2, count in cooccur_dict.items() 
                           if count >= min_cooccurrence}
            if filtered_dict:
                filtered_cooccurrence[tag1] = filtered_dict
        
        print(f"DEBUG: Found co-occurrence patterns for {len(filtered_cooccurrence)} tags")
        return filtered_cooccurrence
    
    def parse_hierarchical_tags(self, separator: str = '-') -> Dict[str, List[str]]:
        """
        Parse pseudo-hierarchical tags (e.g., 'Research-Methods-Quantitative')
        
        Args:
            separator: Character(s) that separate hierarchy levels
            
        Returns:
            Dictionary mapping parent tags to lists of child tags
        """
        hierarchical_tags = defaultdict(list)
        
        for tag in self.processed_tags.keys():
            if separator in tag:
                parts = tag.split(separator)
                if len(parts) > 1:
                    # Build hierarchy
                    for i in range(len(parts) - 1):
                        parent = separator.join(parts[:i+1]).strip()
                        child = separator.join(parts[:i+2]).strip()
                        if parent and child and child not in hierarchical_tags[parent]:
                            hierarchical_tags[parent].append(child)
        
        print(f"DEBUG: Found {len(hierarchical_tags)} hierarchical tag relationships")
        return dict(hierarchical_tags)
    
    def search_tags_advanced(self, 
                           query: str = None,
                           regex_pattern: str = None,
                           tag_length_range: Tuple[int, int] = None,
                           exclude_patterns: List[str] = None) -> Dict[str, int]:
        """
        Advanced tag search with regex and exclusion patterns
        
        Args:
            query: Simple text search
            regex_pattern: Regular expression pattern
            tag_length_range: (min_length, max_length) tuple
            exclude_patterns: List of patterns to exclude
            
        Returns:
            Dictionary of matching tags and frequencies
        """
        matching_tags = {}
        
        for tag, count in self.processed_tags.items():
            include_tag = True
            
            # Text search
            if query and query.lower() not in tag.lower():
                include_tag = False
            
            # Regex pattern
            if regex_pattern and not re.search(regex_pattern, tag, re.IGNORECASE):
                include_tag = False
            
            # Length filter
            if tag_length_range:
                min_len, max_len = tag_length_range
                if not (min_len <= len(tag) <= max_len):
                    include_tag = False
            
            # Exclusion patterns
            if exclude_patterns:
                for exclude_pattern in exclude_patterns:
                    if re.search(exclude_pattern, tag, re.IGNORECASE):
                        include_tag = False
                        break
            
            if include_tag:
                matching_tags[tag] = count
        
        return matching_tags
    
    def get_tags_by_boolean_query(self, query: str) -> Dict[str, int]:
        """
        Search tags using Boolean operators
        
        Args:
            query: Boolean query (e.g., 'python AND (machine OR learning) NOT beginner')
            
        Returns:
            Dictionary of matching tags and frequencies
        """
        from advanced_filters import BooleanQueryParser
        
        matching_tags = {}
        parser = BooleanQueryParser()
        
        try:
            # Parse the Boolean query
            query_expr = parser.parse_query(query)
            
            # Evaluate each tag against the parsed query
            for tag, count in self.processed_tags.items():
                # For tag-level matching, treat each tag as a single-item list
                if parser.evaluate_query(query_expr, [tag]):
                    matching_tags[tag] = count
            
            print(f"DEBUG: Boolean query '{query}' matched {len(matching_tags)} tags")
            return matching_tags
            
        except Exception as e:
            print(f"DEBUG: Boolean query parsing failed, falling back to simple search: {e}")
            
            # Fallback to simple search
            query_lower = query.lower()
            for tag, count in self.processed_tags.items():
                tag_lower = tag.lower()
                
                # Simple pattern matching
                if 'and' in query_lower:
                    # All terms must be present
                    terms = [term.strip() for term in query_lower.split('and')]
                    if all(term in tag_lower for term in terms):
                        matching_tags[tag] = count
                elif 'or' in query_lower:
                    # Any term must be present
                    terms = [term.strip() for term in query_lower.split('or')]
                    if any(term in tag_lower for term in terms):
                        matching_tags[tag] = count
                else:
                    # Simple contains search
                    if query_lower in tag_lower:
                        matching_tags[tag] = count
            
            return matching_tags
    
    def get_metadata_summary(self) -> Dict[str, any]:
        """
        Get comprehensive metadata summary from processed items
        
        Returns:
            Dictionary with metadata statistics
        """
        if not self.items_data:
            return {}
        
        summary = {
            'total_items': len(self.items_data),
            'item_types': defaultdict(int),
            'years': defaultdict(int),
            'creators': defaultdict(int),
            'languages': defaultdict(int),
            'publishers': defaultdict(int),
            'year_range': [None, None]
        }
        
        years = []
        
        for item in self.items_data:
            if 'data' not in item:
                continue
            
            data = item['data']
            
            # Item type
            if 'itemType' in data:
                summary['item_types'][data['itemType']] += 1
            
            # Year
            if 'date' in data and data['date']:
                year_match = re.search(r'\b(19|20)\d{2}\b', data['date'])
                if year_match:
                    year = int(year_match.group())
                    years.append(year)
                    summary['years'][year] += 1
            
            # Creators
            if 'creators' in data:
                for creator in data['creators']:
                    if 'lastName' in creator:
                        summary['creators'][creator['lastName']] += 1
            
            # Language
            if 'language' in data and data['language']:
                summary['languages'][data['language']] += 1
            
            # Publisher
            if 'publisher' in data and data['publisher']:
                summary['publishers'][data['publisher']] += 1
        
        # Set year range
        if years:
            summary['year_range'] = [min(years), max(years)]
        
        # Convert defaultdicts to regular dicts and sort
        summary['item_types'] = dict(sorted(summary['item_types'].items(), key=lambda x: x[1], reverse=True))
        summary['years'] = dict(sorted(summary['years'].items()))
        summary['creators'] = dict(sorted(summary['creators'].items(), key=lambda x: x[1], reverse=True))
        summary['languages'] = dict(sorted(summary['languages'].items(), key=lambda x: x[1], reverse=True))
        summary['publishers'] = dict(sorted(summary['publishers'].items(), key=lambda x: x[1], reverse=True))
        
        return summary
    
    def export_filtered_tags(self, 
                           filtered_tags: Dict[str, int] = None,
                           format: str = 'json',
                           include_metadata: bool = True) -> str:
        """
        Export filtered tags in various formats
        
        Args:
            filtered_tags: Dictionary of tags to export (None for all processed tags)
            format: Export format ('json', 'csv')
            include_metadata: Whether to include metadata summary
            
        Returns:
            Exported data as string
        """
        if filtered_tags is None:
            filtered_tags = self.processed_tags
        
        export_data = {
            'tags': filtered_tags,
            'statistics': {
                'total_tags': len(filtered_tags),
                'total_occurrences': sum(filtered_tags.values()),
                'timestamp': pd.Timestamp.now().isoformat()
            }
        }
        
        if include_metadata and self.items_data:
            export_data['metadata_summary'] = self.get_metadata_summary()
        
        if format == 'json':
            return json.dumps(export_data, indent=2)
        elif format == 'csv':
            # Create CSV of tags
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Tag', 'Frequency'])
            
            for tag, freq in sorted(filtered_tags.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([tag, freq])
            
            return output.getvalue()
        
        return json.dumps(export_data, indent=2)