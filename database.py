import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import diskcache


class ZoteroDatabase:
    def __init__(self, db_path: str = "zotero_cache.db"):
        """
        Initialize the database for caching Zotero data
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize disk cache for preferences and temporary data
        self.disk_cache = diskcache.Cache(str(self.cache_dir))
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS libraries (
                    id TEXT PRIMARY KEY,
                    library_type TEXT NOT NULL,
                    name TEXT,
                    api_key_hash TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    library_id TEXT NOT NULL,
                    tag_name TEXT NOT NULL,
                    frequency INTEGER NOT NULL DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (library_id) REFERENCES libraries (id),
                    UNIQUE(library_id, tag_name)
                );
                
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_tags_library ON tags (library_id);
                CREATE INDEX IF NOT EXISTS idx_tags_frequency ON tags (frequency DESC);
                CREATE INDEX IF NOT EXISTS idx_tags_updated ON tags (last_updated);
            """)
    
    def get_library_id(self, library_id: str, library_type: str) -> str:
        """Generate consistent library identifier"""
        return f"{library_type}_{library_id}"
    
    def save_library_info(self, library_id: str, library_type: str, 
                         name: Optional[str] = None, api_key_hash: Optional[str] = None):
        """Save or update library information"""
        lib_id = self.get_library_id(library_id, library_type)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO libraries 
                (id, library_type, name, api_key_hash, last_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (lib_id, library_type, name, api_key_hash))
    
    def save_tags(self, library_id: str, library_type: str, tag_frequencies: Dict[str, int]):
        """Save tag frequencies for a library"""
        lib_id = self.get_library_id(library_id, library_type)
        
        with sqlite3.connect(self.db_path) as conn:
            # Update library timestamp
            conn.execute("""
                UPDATE libraries SET last_updated = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (lib_id,))
            
            # Clear existing tags for this library
            conn.execute("DELETE FROM tags WHERE library_id = ?", (lib_id,))
            
            # Insert new tags
            tag_data = [
                (lib_id, tag_name, frequency) 
                for tag_name, frequency in tag_frequencies.items()
            ]
            
            conn.executemany("""
                INSERT INTO tags (library_id, tag_name, frequency)
                VALUES (?, ?, ?)
            """, tag_data)
            
            print(f"DEBUG: Cached {len(tag_data)} tags for library {lib_id}")
    
    def get_tags(self, library_id: str, library_type: str, 
                max_age_hours: int = 24) -> Optional[Dict[str, int]]:
        """
        Get cached tag frequencies for a library
        
        Args:
            library_id: Zotero library ID
            library_type: 'user' or 'group'
            max_age_hours: Maximum age of cache in hours
            
        Returns:
            Dictionary of tag frequencies or None if cache is stale/missing
        """
        lib_id = self.get_library_id(library_id, library_type)
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if library exists and is recent enough
            library_row = conn.execute("""
                SELECT last_updated FROM libraries 
                WHERE id = ? AND last_updated > ?
            """, (lib_id, cutoff_time.isoformat())).fetchone()
            
            if not library_row:
                print(f"DEBUG: No recent cache found for library {lib_id}")
                return None
            
            # Get tags
            tag_rows = conn.execute("""
                SELECT tag_name, frequency FROM tags 
                WHERE library_id = ?
                ORDER BY frequency DESC
            """, (lib_id,)).fetchall()
            
            if not tag_rows:
                print(f"DEBUG: No tags found in cache for library {lib_id}")
                return None
            
            tag_frequencies = dict(tag_rows)
            print(f"DEBUG: Loaded {len(tag_frequencies)} tags from cache for library {lib_id}")
            return tag_frequencies
    
    def get_recent_libraries(self, limit: int = 5) -> List[Tuple[str, str, str, str]]:
        """
        Get recently accessed libraries
        
        Returns:
            List of (library_id, library_type, name, last_updated) tuples
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT id, library_type, name, last_updated 
                FROM libraries 
                ORDER BY last_updated DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [(row[0].split('_', 1)[1], row[1], row[2] or 'Unnamed Library', row[3]) 
                    for row in rows]
    
    def clear_library_cache(self, library_id: str, library_type: str):
        """Clear cache for a specific library"""
        lib_id = self.get_library_id(library_id, library_type)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tags WHERE library_id = ?", (lib_id,))
            conn.execute("DELETE FROM libraries WHERE id = ?", (lib_id,))
            
        print(f"DEBUG: Cleared cache for library {lib_id}")
    
    def clear_all_cache(self):
        """Clear all cached data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tags")
            conn.execute("DELETE FROM libraries")
        
        # Clear disk cache
        self.disk_cache.clear()
        print("DEBUG: Cleared all cache data")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Library stats
            lib_count = conn.execute("SELECT COUNT(*) FROM libraries").fetchone()[0]
            
            # Tag stats
            tag_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_tags,
                    COUNT(DISTINCT library_id) as libraries_with_tags,
                    AVG(frequency) as avg_frequency,
                    MAX(frequency) as max_frequency
                FROM tags
            """).fetchone()
            
            # Recent activity
            recent_activity = conn.execute("""
                SELECT COUNT(*) FROM libraries 
                WHERE last_updated > datetime('now', '-24 hours')
            """).fetchone()[0]
            
            return {
                'total_libraries': lib_count,
                'total_tags': tag_stats[0] if tag_stats else 0,
                'libraries_with_tags': tag_stats[1] if tag_stats else 0,
                'avg_frequency': round(tag_stats[2] or 0, 2),
                'max_frequency': tag_stats[3] or 0,
                'recent_activity': recent_activity,
                'disk_cache_size': len(self.disk_cache)
            }
    
    # Preferences management
    def save_preference(self, key: str, value: any):
        """Save a user preference"""
        json_value = json.dumps(value)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO preferences (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, json_value))
    
    def get_preference(self, key: str, default: any = None) -> any:
        """Get a user preference"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT value FROM preferences WHERE key = ?
            """, (key,)).fetchone()
            
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]  # Return as string if not valid JSON
            
            return default
    
    def get_all_preferences(self) -> Dict[str, any]:
        """Get all user preferences"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
            
            preferences = {}
            for key, value in rows:
                try:
                    preferences[key] = json.loads(value)
                except json.JSONDecodeError:
                    preferences[key] = value
            
            return preferences
    
    def close(self):
        """Close database connections"""
        self.disk_cache.close()


# Global database instance
db = ZoteroDatabase()