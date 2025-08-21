"""
Markdown formatting restoration utility
Reverses LangChain's whitespace/newline stripping for better display
"""
import re
from typing import Union


def restore_markdown_formatting(text: Union[str, object]) -> str:
    """
    Restore markdown formatting that was stripped by LangChain during processing.
    
    LangChain strips whitespace and newlines for token efficiency during processing,
    but this breaks markdown rendering in UIs. This utility adds proper spacing back.
    
    Args:
        text: The text to format (can be string or LLM response object)
        
    Returns:
        Properly formatted markdown text with restored line breaks
    """
    # Extract text from LLM response objects
    if hasattr(text, 'content'):
        content = text.content
    else:
        content = str(text)
    
    if not content or not content.strip():
        return content
    
    # Apply markdown formatting restoration rules
    formatted = content
    
    # 1. Add line breaks before headers (# ## ###)
    formatted = re.sub(r'(?<!\n)(#+\s)', r'\n\1', formatted)
    
    # 2. Add line breaks before list items (- * +) - more aggressive
    # Handle lists that follow text directly without spaces
    formatted = re.sub(r'([a-zA-Z0-9:])([*+-]\s)', r'\1\n\2', formatted)
    formatted = re.sub(r'(?<!\n)([*+-]\s)', r'\n\1', formatted)
    
    # 3. Add line breaks before numbered lists (only at start of line context)
    formatted = re.sub(r'([a-zA-Z])(\d+\.\s)', r'\1\n\2', formatted)
    
    # 4. Add line breaks around code blocks
    formatted = re.sub(r'(?<!\n)(```)', r'\n\1', formatted)
    formatted = re.sub(r'(```)(?!\n)', r'\1\n', formatted)
    
    # 5. Add line breaks before blockquotes
    formatted = re.sub(r'(?<!\n)(>\s)', r'\n\1', formatted)
    
    # 6. Add line breaks before headers after text (but not at start)
    formatted = re.sub(r'([a-zA-Z0-9\.])(#+\s)', r'\1\n\n\2', formatted)
    
    
    # 8. Ensure proper spacing around emphasis (** __)
    formatted = re.sub(r'(\S)(\*\*)', r'\1 \2', formatted)
    formatted = re.sub(r'(\*\*)(\S)', r'\1 \2', formatted)
    
    # 9. Clean up excessive newlines (more than 2 in a row)
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    
    # 10. Clean up leading/trailing whitespace
    formatted = formatted.strip()
    
    return formatted


def restore_list_formatting(text: str) -> str:
    """
    Specifically restore list formatting that often gets broken.
    
    Args:
        text: Text with potentially broken list formatting
        
    Returns:
        Text with properly formatted lists
    """
    # Ensure list items are on separate lines
    text = re.sub(r'([*+-]\s[^\n]+)([*+-]\s)', r'\1\n\2', text)
    text = re.sub(r'(\d+\.\s[^\n]+)(\d+\.\s)', r'\1\n\2', text)
    
    return text


def restore_code_formatting(text: str) -> str:
    """
    Restore code block formatting.
    
    Args:
        text: Text with potentially broken code formatting
        
    Returns:
        Text with properly formatted code blocks
    """
    # Ensure code blocks are on their own lines
    text = re.sub(r'([^`])(`{1,3})([^`])', r'\1\n\2\n\3', text)
    
    return text


def smart_paragraph_breaks(text: str) -> str:
    """
    Add intelligent paragraph breaks based on content structure.
    
    Args:
        text: Text that may need paragraph breaks
        
    Returns:
        Text with smart paragraph breaks added
    """
    # Add breaks before new topics/sections
    patterns = [
        r'(\.)\s*(However|Meanwhile|Additionally|Furthermore|Moreover|In contrast|On the other hand)',
        r'(\.)\s*(First|Second|Third|Finally|Next|Then|After that)',
        r'(\.)\s*(To|For|When|If|Since|Because|Although)',
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, r'\1\n\n\2', text)
    
    return text