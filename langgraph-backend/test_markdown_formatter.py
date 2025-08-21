#!/usr/bin/env python3
"""
Quick test for markdown formatter utility
"""
from app.utils.markdown_formatter import restore_markdown_formatting

def test_markdown_formatter():
    # Test text that simulates LangChain's stripped formatting
    stripped_text = "Here are the results:# Product Search Results- Product A: Coffee Machine- Product B: Grinder```python\ncode_example = 'hello'\n```This is another paragraph.## Pricing Details1. Regular price: $1992. Sale price: $149"
    
    print("BEFORE formatting:")
    print(repr(stripped_text))
    print("\nBEFORE (display):")
    print(stripped_text)
    
    formatted_text = restore_markdown_formatting(stripped_text)
    
    print("\n" + "="*50)
    print("AFTER formatting:")
    print(repr(formatted_text))
    print("\nAFTER (display):")
    print(formatted_text)

if __name__ == "__main__":
    test_markdown_formatter()