"""
Advanced filtering utilities for Zotero tag visualizer
Provides sophisticated filtering and query capabilities
"""

from typing import List, Dict, Set, Optional, Union, Tuple
from dataclasses import dataclass
import re
from enum import Enum


class FilterOperator(Enum):
    """Boolean operators for filtering"""
    AND = "AND"
    OR = "OR" 
    NOT = "NOT"


@dataclass
class FilterCriteria:
    """Container for filter criteria"""
    search_terms: List[str] = None
    item_types: List[str] = None
    start_year: int = None
    end_year: int = None
    creators: List[str] = None
    languages: List[str] = None
    collections: List[str] = None
    min_frequency: int = None
    max_frequency: int = None
    regex_pattern: str = None
    exclude_patterns: List[str] = None


class BooleanQueryParser:
    """
    Parser for Boolean query expressions
    Supports AND, OR, NOT operators with parentheses
    """
    
    def __init__(self):
        self.operators = {'AND', 'OR', 'NOT'}
    
    def parse_query(self, query: str) -> Dict[str, any]:
        """
        Parse a Boolean query string into a structured format
        
        Args:
            query: Boolean query string (e.g., "python AND (machine OR learning) NOT beginner")
            
        Returns:
            Dictionary with parsed query structure
        """
        # Clean and normalize the query
        normalized = self._normalize_query(query)
        
        # Tokenize the query
        tokens = self._tokenize(normalized)
        
        # Parse into expression tree (simplified for this implementation)
        return self._parse_expression(tokens)
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query by handling case and spacing"""
        # Convert to uppercase for operators
        normalized = query.upper()
        
        # Ensure proper spacing around operators
        for op in self.operators:
            normalized = re.sub(rf'\b{op}\b', f' {op} ', normalized)
        
        # Clean up extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _tokenize(self, query: str) -> List[str]:
        """Split query into tokens"""
        # Simple tokenization - could be enhanced for complex queries
        tokens = []
        current_token = ""
        in_quotes = False
        
        for char in query:
            if char == '"':
                in_quotes = not in_quotes
                current_token += char
            elif char == ' ' and not in_quotes:
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            else:
                current_token += char
        
        if current_token:
            tokens.append(current_token)
        
        return tokens
    
    def _parse_expression(self, tokens: List[str]) -> Dict[str, any]:
        """Parse tokens into expression structure"""
        # Simplified parser - in production, would use proper parsing techniques
        expression = {
            'type': 'expression',
            'terms': [],
            'operators': [],
            'negated_terms': []
        }
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token == 'NOT' and i + 1 < len(tokens):
                expression['negated_terms'].append(tokens[i + 1].strip('"'))
                i += 2
            elif token in ['AND', 'OR']:
                expression['operators'].append(token)
                i += 1
            elif token not in self.operators:
                expression['terms'].append(token.strip('"'))
                i += 1
            else:
                i += 1
        
        return expression
    
    def evaluate_query(self, query_expr: Dict[str, any], item_tags: List[str]) -> bool:
        """
        Evaluate a parsed query against a list of tags
        
        Args:
            query_expr: Parsed query expression
            item_tags: List of tags to evaluate against
            
        Returns:
            True if the item matches the query
        """
        # Convert tags to lowercase for case-insensitive matching
        item_tags_lower = [tag.lower() for tag in item_tags]
        
        # Check negated terms first
        for negated_term in query_expr.get('negated_terms', []):
            if negated_term.lower() in item_tags_lower:
                return False
        
        terms = query_expr.get('terms', [])
        operators = query_expr.get('operators', [])
        
        if not terms:
            return True  # No positive terms to match
        
        # Simplified evaluation logic
        if not operators:
            # Single term
            return any(term.lower() in tag.lower() for tag in item_tags for term in terms)
        
        # Multiple terms with operators
        if 'OR' in operators:
            # If any OR is present, use OR logic
            return any(any(term.lower() in tag.lower() for tag in item_tags) for term in terms)
        else:
            # All AND logic
            return all(any(term.lower() in tag.lower() for tag in item_tags) for term in terms)


class AdvancedFilter:
    """
    Advanced filtering engine that combines multiple filter criteria
    """
    
    def __init__(self):
        self.query_parser = BooleanQueryParser()
    
    def apply_filters(self, 
                     items: List[Dict], 
                     criteria: FilterCriteria) -> List[Dict]:
        """
        Apply advanced filtering criteria to a list of items
        
        Args:
            items: List of Zotero items
            criteria: FilterCriteria object with filter parameters
            
        Returns:
            Filtered list of items
        """
        filtered_items = []
        
        for item in items:
            if self._item_matches_criteria(item, criteria):
                filtered_items.append(item)
        
        return filtered_items
    
    def _item_matches_criteria(self, item: Dict, criteria: FilterCriteria) -> bool:
        """Check if an item matches the filter criteria"""
        if 'data' not in item:
            return False
        
        data = item['data']
        
        # Item type filter
        if criteria.item_types:
            if data.get('itemType') not in criteria.item_types:
                return False
        
        # Year range filter
        if criteria.start_year or criteria.end_year:
            if not self._matches_year_range(data, criteria.start_year, criteria.end_year):
                return False
        
        # Creator filter
        if criteria.creators:
            if not self._matches_creators(data, criteria.creators):
                return False
        
        # Language filter
        if criteria.languages:
            if data.get('language') not in criteria.languages:
                return False
        
        # Tag-based filters
        if criteria.search_terms or criteria.regex_pattern or criteria.exclude_patterns:
            item_tags = self._extract_tags(item)
            
            # Search terms
            if criteria.search_terms:
                if not self._matches_search_terms(item_tags, criteria.search_terms):
                    return False
            
            # Regex pattern
            if criteria.regex_pattern:
                if not any(re.search(criteria.regex_pattern, tag, re.IGNORECASE) for tag in item_tags):
                    return False
            
            # Exclude patterns
            if criteria.exclude_patterns:
                for exclude_pattern in criteria.exclude_patterns:
                    if any(re.search(exclude_pattern, tag, re.IGNORECASE) for tag in item_tags):
                        return False
        
        return True
    
    def _matches_year_range(self, data: Dict, start_year: int, end_year: int) -> bool:
        """Check if item matches year range"""
        if 'date' not in data or not data['date']:
            return False
        
        year_match = re.search(r'\b(19|20)\d{2}\b', data['date'])
        if not year_match:
            return False
        
        year = int(year_match.group())
        
        if start_year and year < start_year:
            return False
        if end_year and year > end_year:
            return False
        
        return True
    
    def _matches_creators(self, data: Dict, creators: List[str]) -> bool:
        """Check if item matches creator criteria"""
        if 'creators' not in data:
            return False
        
        item_creators = data['creators']
        
        for creator_filter in creators:
            creator_match = False
            for creator in item_creators:
                creator_name = f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()
                if creator_filter.lower() in creator_name.lower():
                    creator_match = True
                    break
            if creator_match:
                return True
        
        return False
    
    def _extract_tags(self, item: Dict) -> List[str]:
        """Extract tags from an item"""
        if 'data' not in item or 'tags' not in item['data']:
            return []
        
        tags = []
        for tag_info in item['data']['tags']:
            tag_name = tag_info.get('tag', '') if isinstance(tag_info, dict) else str(tag_info)
            if tag_name:
                tags.append(tag_name)
        
        return tags
    
    def _matches_search_terms(self, item_tags: List[str], search_terms: List[str]) -> bool:
        """Check if item tags match search terms"""
        for search_term in search_terms:
            if any(search_term.lower() in tag.lower() for tag in item_tags):
                return True
        return False
    
    def filter_tags_by_cooccurrence(self, 
                                  tags: Dict[str, int], 
                                  cooccurrence_data: Dict[str, Dict[str, int]],
                                  target_tag: str,
                                  min_cooccurrence: int = 2) -> Dict[str, int]:
        """
        Filter tags based on co-occurrence with a target tag
        
        Args:
            tags: Dictionary of all tags and frequencies
            cooccurrence_data: Co-occurrence matrix
            target_tag: Tag to find co-occurrences for
            min_cooccurrence: Minimum co-occurrence count
            
        Returns:
            Filtered tags that co-occur with target tag
        """
        if target_tag not in cooccurrence_data:
            return {}
        
        cooccurring_tags = {}
        target_cooccurrences = cooccurrence_data[target_tag]
        
        for tag, cooccur_count in target_cooccurrences.items():
            if cooccur_count >= min_cooccurrence and tag in tags:
                cooccurring_tags[tag] = tags[tag]
        
        return cooccurring_tags
    
    def create_filter_preset(self, name: str, criteria: FilterCriteria) -> Dict[str, any]:
        """
        Create a filter preset that can be saved and reused
        
        Args:
            name: Name for the preset
            criteria: FilterCriteria object
            
        Returns:
            Dictionary representation of the preset
        """
        return {
            'name': name,
            'criteria': {
                'search_terms': criteria.search_terms,
                'item_types': criteria.item_types,
                'start_year': criteria.start_year,
                'end_year': criteria.end_year,
                'creators': criteria.creators,
                'languages': criteria.languages,
                'collections': criteria.collections,
                'min_frequency': criteria.min_frequency,
                'max_frequency': criteria.max_frequency,
                'regex_pattern': criteria.regex_pattern,
                'exclude_patterns': criteria.exclude_patterns
            },
            'created_at': pd.Timestamp.now().isoformat()
        }
    
    def load_filter_preset(self, preset_data: Dict[str, any]) -> FilterCriteria:
        """
        Load a filter preset into a FilterCriteria object
        
        Args:
            preset_data: Dictionary representation of preset
            
        Returns:
            FilterCriteria object
        """
        criteria_data = preset_data.get('criteria', {})
        
        return FilterCriteria(
            search_terms=criteria_data.get('search_terms'),
            item_types=criteria_data.get('item_types'),
            start_year=criteria_data.get('start_year'),
            end_year=criteria_data.get('end_year'),
            creators=criteria_data.get('creators'),
            languages=criteria_data.get('languages'),
            collections=criteria_data.get('collections'),
            min_frequency=criteria_data.get('min_frequency'),
            max_frequency=criteria_data.get('max_frequency'),
            regex_pattern=criteria_data.get('regex_pattern'),
            exclude_patterns=criteria_data.get('exclude_patterns')
        )


# Utility functions
def create_item_type_groups() -> Dict[str, List[str]]:
    """
    Create predefined groups of related item types for easier filtering
    
    Returns:
        Dictionary mapping group names to lists of item types
    """
    return {
        'Academic Articles': ['journalArticle', 'conferencePaper', 'preprint'],
        'Books': ['book', 'bookSection'],
        'Reports & Documents': ['report', 'document', 'manuscript'],
        'Theses': ['thesis', 'dissertation'],
        'Media': ['podcast', 'videoRecording', 'film'],
        'Web Resources': ['webpage', 'blogPost', 'forumPost'],
        'Legal': ['case', 'statute', 'patent']
    }


def suggest_filter_combinations(tags: Dict[str, int], 
                              cooccurrence_data: Dict[str, Dict[str, int]]) -> List[Dict[str, any]]:
    """
    Suggest useful filter combinations based on tag patterns
    
    Args:
        tags: Dictionary of tags and frequencies
        cooccurrence_data: Tag co-occurrence matrix
        
    Returns:
        List of suggested filter combinations
    """
    suggestions = []
    
    # Find highly connected tags (tags with many co-occurrences)
    highly_connected = {}
    for tag, cooccur_dict in cooccurrence_data.items():
        if len(cooccur_dict) >= 5:  # Tags that co-occur with 5+ other tags
            highly_connected[tag] = len(cooccur_dict)
    
    # Suggest filters based on highly connected tags
    for tag, connection_count in sorted(highly_connected.items(), 
                                       key=lambda x: x[1], reverse=True)[:5]:
        suggestions.append({
            'name': f'Related to "{tag}"',
            'description': f'Items tagged with "{tag}" and related concepts',
            'criteria': FilterCriteria(search_terms=[tag]),
            'estimated_items': tags.get(tag, 0)
        })
    
    # Suggest common academic filters
    academic_types = ['journalArticle', 'book', 'conferencePaper']
    suggestions.append({
        'name': 'Academic Publications',
        'description': 'Journal articles, books, and conference papers',
        'criteria': FilterCriteria(item_types=academic_types),
        'estimated_items': sum(tags.get(t, 0) for t in academic_types)
    })
    
    return suggestions


# Import pandas for timestamp functionality
import pandas as pd