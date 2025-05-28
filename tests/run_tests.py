"""
Test runner script to execute all unit and integration tests.
"""
import os
import sys
import unittest
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from tests.test_memory_service import TestMemoryService
from tests.test_fetch_service import TestFetchService
from tests.test_compatibility import TestCompatibilityLayer

def run_tests():
    """Run all tests and return the results."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestMemoryService))
    test_suite.addTest(unittest.makeSuite(TestFetchService))
    test_suite.addTest(unittest.makeSuite(TestCompatibilityLayer))
    
    # Run tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    return result

if __name__ == '__main__':
    result = run_tests()
    
    # Print summary
    print("\nTest Summary:")
    print(f"Ran {result.testsRun} tests")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    # Exit with appropriate code
    sys.exit(len(result.failures) + len(result.errors))
