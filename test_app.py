#!/usr/bin/env python3
"""
Test script to verify the advanced filtering system works
"""

def test_imports():
    """Test that all modules can be imported"""
    try:
        print("Testing imports...")
        
        # Test core modules
        from advanced_filters import AdvancedFilter, FilterCriteria, BooleanQueryParser, create_item_type_groups
        from tag_processor import TagProcessor
        from zotero_client import ZoteroClient
        from zotero_local_client import ZoteroLocalClient, detect_local_zotero
        from database import ZoteroDatabase, db
        
        print("✅ All modules imported successfully!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_class_instantiation():
    """Test that classes can be instantiated"""
    try:
        print("Testing class instantiation...")
        
        # Test advanced filters
        filter_engine = AdvancedFilter()
        criteria = FilterCriteria(search_terms=["test"])
        parser = BooleanQueryParser()
        
        # Test tag processor
        processor = TagProcessor()
        
        # Test database
        test_db = ZoteroDatabase(":memory:")  # In-memory database for testing
        
        print("✅ All classes instantiated successfully!")
        return True
    except Exception as e:
        print(f"❌ Instantiation error: {e}")
        return False

def test_boolean_parser():
    """Test Boolean query parser"""
    try:
        print("Testing Boolean query parser...")
        
        from advanced_filters import BooleanQueryParser
        parser = BooleanQueryParser()
        
        # Test queries
        queries = [
            "python AND machine learning",
            "research OR development", 
            "ai NOT beginner",
            "deep AND (learning OR neural)"
        ]
        
        for query in queries:
            result = parser.parse_query(query)
            print(f"  Query: '{query}' → {result.get('terms', [])} ops: {result.get('operators', [])}")
        
        print("✅ Boolean parser working correctly!")
        return True
    except Exception as e:
        print(f"❌ Boolean parser error: {e}")
        return False

def test_tag_processor():
    """Test tag processor with sample data"""
    try:
        print("Testing tag processor...")
        
        processor = TagProcessor()
        
        # Sample tag data
        sample_tags = [
            {"tag": "machine learning", "meta": {"numItems": 5}},
            {"tag": "python", "meta": {"numItems": 8}},
            {"tag": "research", "meta": {"numItems": 3}},
            {"tag": "deep learning", "meta": {"numItems": 2}},
            {"tag": "neural networks", "meta": {"numItems": 4}}
        ]
        
        tag_freq = processor.process_zotero_tags(sample_tags)
        print(f"  Processed {len(tag_freq)} tags: {list(tag_freq.keys())[:3]}...")
        
        # Test Boolean search
        results = processor.get_tags_by_boolean_query("machine OR learning")
        print(f"  Boolean search found {len(results)} matching tags")
        
        # Test stats
        stats = processor.get_tag_statistics()
        print(f"  Stats: {stats.get('total_tags', 0)} total, avg freq: {stats.get('avg_frequency', 0):.1f}")
        
        print("✅ Tag processor working correctly!")
        return True
    except Exception as e:
        print(f"❌ Tag processor error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Advanced Tag Filtering System\n")
    
    tests = [
        test_imports,
        test_class_instantiation, 
        test_boolean_parser,
        test_tag_processor
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}\n")
    
    print(f"🎯 Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Advanced filtering system is ready.")
        print("\n💡 To start the app, run: python app.py")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()