#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
import subprocess
from typing import Optional

PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions'

def search_perplexity(query: str, model: str = 'sonar') -> Optional[str]:
    """
    Search using Perplexity API with the specified model
    """
    if not PERPLEXITY_API_KEY:
        return "Error: PERPLEXITY_API_KEY environment variable not set"
    
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': 'You are a helpful research assistant to Pranav, or his AI assistant Claude.'
                'About Pranav: Pranav is the e-commerce and tech person at iDrinkCafe.com. He uses EndeavorOS as his primary OS and is querying you from the terminal.'
                'About Claude: Claude is Pranav''s AI assistant. He is a helpful tool-use assistant to Pranav, and must accurately and carefully execute tasks on iDrinkCafe.com.'
                'About iDrinkCafe.com: iDrinkCafe.com is an e-commerce website that sells coffee and tea products. It is a Shopify store and is located in the Milton, Ontario area.'
                'When helping Pranav or Claude, you must thoroughly research the topic and provide accurate, relevant and helpful information.'
                'You can use Markdown to format your responses. Citations won''t be formatted - so instead just note them at the end of your response. instead of using citation markers, just note the source of the information at the end of your response.'
            },
            {
                'role': 'user',
                'content': query
            }
        ]
    }
    
    try:
        response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data['choices'][0]['message']['content']
    
    except requests.exceptions.RequestException as e:
        return f"Error: API request failed - {str(e)}"
    except KeyError:
        return "Error: Unexpected API response format"
    except Exception as e:
        return f"Error: {str(e)}"

def render_markdown(text: str, renderer: str = 'auto', style: str = 'auto') -> str:
    """
    Render markdown using rich (preferred) or glow
    """
    # Force specific renderer if requested
    if renderer == 'rich':
        try:
            from rich.console import Console
            from rich.markdown import Markdown
            
            console = Console()
            md = Markdown(text)
            with console.capture() as capture:
                console.print(md)
            return capture.get().rstrip()
        except ImportError:
            return text + "\n\n(Note: rich not installed, install with: pip install rich)"
    
    elif renderer == 'glow':
        try:
            result = subprocess.run(['which', 'glow'], capture_output=True, text=True)
            if result.returncode == 0:
                cmd = ['glow', '-', '-w', '80']
                if style != 'auto':
                    cmd.extend(['-s', style])
                
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    universal_newlines=True
                )
                stdout, stderr = process.communicate(input=text)
                if process.returncode == 0 and stdout.strip():
                    return stdout.rstrip()
            return text + "\n\n(Note: glow not found)"
        except Exception:
            return text
    
    # Auto mode: try rich first (better inline formatting)
    try:
        from rich.console import Console
        from rich.markdown import Markdown
        
        console = Console()
        md = Markdown(text)
        with console.capture() as capture:
            console.print(md)
        return capture.get().rstrip()
    except ImportError:
        # Fallback to glow
        try:
            result = subprocess.run(['which', 'glow'], capture_output=True, text=True)
            if result.returncode == 0:
                cmd = ['glow', '-', '-w', '80']
                if style != 'auto':
                    cmd.extend(['-s', style])
                
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    universal_newlines=True
                )
                stdout, stderr = process.communicate(input=text)
                if process.returncode == 0 and stdout.strip():
                    return stdout.rstrip()
        except Exception:
            pass
    
    # No markdown renderer available
    return text

def main():
    parser = argparse.ArgumentParser(
        description='Quick Perplexity CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Available models:
  sonar              - Latest Sonar model (default)
  sonar-pro          - Enhanced performance model
  sonar-deep-research - For comprehensive research tasks
  sonar-reasoning    - Optimized for logical reasoning
  sonar-reasoning-pro - Advanced reasoning capabilities

Examples:
  pplx.py "what is quantum computing"
  pplx.py -m sonar-pro "explain transformer architecture"
  pplx.py -m sonar-deep-research "latest AI developments 2024"
  pplx.py -i  # Interactive mode
        '''
    )
    parser.add_argument('query', nargs='*', help='Search query')
    parser.add_argument('-i', '--interactive', action='store_true', 
                       help='Interactive mode')
    parser.add_argument('-m', '--model', default='sonar',
                       choices=['sonar', 'sonar-pro', 'sonar-deep-research', 
                               'sonar-reasoning', 'sonar-reasoning-pro'],
                       help='Model to use (default: sonar)')
    parser.add_argument('--no-markdown', action='store_true',
                       help='Disable markdown rendering')
    parser.add_argument('--renderer', default='auto',
                       choices=['auto', 'rich', 'glow'],
                       help='Markdown renderer to use (default: auto, prefers rich)')
    parser.add_argument('--style', default='auto',
                       choices=['auto', 'dark', 'light', 'dracula', 'github'],
                       help='Glow style for markdown rendering (default: auto)')
    
    args = parser.parse_args()
    
    if args.interactive:
        print("Perplexity CLI - Interactive Mode")
        print(f"Using model: {args.model}")
        print("Type 'exit' or 'quit' to leave")
        print("-" * 40)
        
        while True:
            try:
                query = input("\n🔍 Query: ").strip()
                if query.lower() in ['exit', 'quit']:
                    break
                if not query:
                    continue
                    
                print("\n⏳ Searching...\n")
                result = search_perplexity(query, args.model)
                if args.no_markdown:
                    print(result)
                else:
                    rendered = render_markdown(result, args.renderer, args.style)
                    print(rendered)
                print("\n" + "-" * 40)
                
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
    else:
        if not args.query:
            parser.error("Please provide a search query or use -i for interactive mode")
        
        query = ' '.join(args.query)
        result = search_perplexity(query, args.model)
        if args.no_markdown:
            print(result)
        else:
            rendered = render_markdown(result, args.renderer, args.style)
            print(rendered)

if __name__ == '__main__':
    main()