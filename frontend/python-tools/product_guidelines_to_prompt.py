#!/usr/bin/env python3
"""
Product Guidelines to System Prompt Converter (Python version)
Converts product documentation into AI agent prompts for Shopify product creation.
"""

import json
import os
from pathlib import Path
import re
from typing import Dict, List, Optional
import argparse

class ProductGuidelinesConverter:
    """Convert product guidelines to system prompts."""
    
    def __init__(self, guidelines_dir: str = "../docs/product-guidelines"):
        self.guidelines_dir = Path(guidelines_dir)
        self.guidelines = {}
        self.key_info = {
            'brand': 'iDrinkCoffee.com',
            'principles': [],
            'requirements': [],
            'workflow': [],
            'metafields': [],
            'tags': [],
            'coffeeSpecific': []
        }
    
    def read_guidelines(self) -> Dict[str, Dict]:
        """Read all markdown files from guidelines directory."""
        for file_path in self.guidelines_dir.glob("*.md"):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                key = file_path.stem.lstrip('0123456789-').replace('-', '_')
                self.guidelines[key] = {
                    'filename': file_path.name,
                    'content': content,
                    'title': self._extract_title(content)
                }
        return self.guidelines
    
    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content."""
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return re.sub(r'[☕️🔧🚀✨]', '', match.group(1)).strip()
        return 'Untitled'
    
    def extract_key_info(self) -> Dict:
        """Extract key information from guidelines."""
        # Extract principles
        if 'overview' in self.guidelines:
            principles_match = re.search(
                r'## Key Principles\n\n([\s\S]+?)(?=\n##|$)',
                self.guidelines['overview']['content']
            )
            if principles_match:
                self.key_info['principles'] = [
                    line[2:] for line in principles_match.group(1).split('\n')
                    if line.startswith('-')
                ]
        
        # Extract requirements and workflow
        if 'product_creation_basics' in self.guidelines:
            content = self.guidelines['product_creation_basics']['content']
            
            req_match = re.search(
                r'## Core Requirements\n\n([\s\S]+?)(?=\n##|$)',
                content
            )
            if req_match:
                self.key_info['requirements'] = [
                    line[2:] for line in req_match.group(1).split('\n')
                    if line.startswith('-')
                ]
            
            workflow_match = re.search(
                r'## Product Creation Workflow\n\n([\s\S]+?)(?=\n##|$)',
                content
            )
            if workflow_match:
                self.key_info['workflow'] = [
                    section for section in workflow_match.group(1).split('\n\n')
                    if '**' in section
                ]
        
        # Extract metafields
        if 'metafields_reference' in self.guidelines:
            content = self.guidelines['metafields_reference']['content']
            metafield_pattern = r'### (.+?)\n- \*\*Namespace:\*\* `(.+?)`\n- \*\*Key:\*\* `(.+?)`'
            
            for match in re.finditer(metafield_pattern, content):
                self.key_info['metafields'].append({
                    'name': match.group(1),
                    'namespace': match.group(2),
                    'key': match.group(3)
                })
        
        # Extract tags
        if 'tags_system' in self.guidelines:
            content = self.guidelines['tags_system']['content']
            tag_pattern = r'### (.+?)\n([\s\S]+?)(?=\n###|$)'
            
            for match in re.finditer(tag_pattern, content):
                category = match.group(1)
                tag_content = match.group(2)
                tags = []
                
                for line in tag_content.split('\n'):
                    if line.startswith('-'):
                        tag_match = re.search(r'`(.+?)`', line)
                        if tag_match:
                            tags.append(tag_match.group(1))
                
                if tags:
                    self.key_info['tags'].append({
                        'category': category,
                        'tags': tags
                    })
        
        # Extract coffee-specific info
        if 'coffee_products' in self.guidelines:
            content = self.guidelines['coffee_products']['content']
            coffee_match = re.search(
                r'### Required Tag Format\n\n([\s\S]+?)(?=\n###|$)',
                content
            )
            if coffee_match:
                self.key_info['coffeeSpecific'] = [
                    line[2:] for line in coffee_match.group(1).split('\n')
                    if line.startswith('-')
                ]
        
        return self.key_info
    
    def create_prompt(self, prompt_type: str = 'productCreation') -> str:
        """Create system prompt based on type."""
        prompt = f"You are a Shopify product creation specialist for {self.key_info['brand']}. "
        prompt += "You help create, update, and manage product listings using the Shopify Admin API.\n\n"
        
        # Add sections based on prompt type
        if prompt_type == 'productCreation':
            prompt += self._add_product_creation_sections()
        elif prompt_type == 'coffeeProducts':
            prompt += self._add_coffee_product_sections()
        elif prompt_type == 'technical':
            prompt += self._add_technical_sections()
        
        return prompt
    
    def _add_product_creation_sections(self) -> str:
        """Add sections for general product creation."""
        sections = []
        
        # Key principles
        if self.key_info['principles']:
            sections.append("# Key Principles\n\n" + 
                          '\n'.join(f"- {p}" for p in self.key_info['principles']))
        
        # Core requirements
        if self.key_info['requirements']:
            sections.append("# Core Product Requirements\n\nEvery product must include:\n" +
                          '\n'.join(f"- {r}" for r in self.key_info['requirements']))
        
        # Metafields
        if self.key_info['metafields']:
            metafield_list = '\n'.join(
                f"- **{m['name']}**: `{m['namespace']}.{m['key']}`"
                for m in self.key_info['metafields'][:10]  # First 10 most important
            )
            sections.append(f"# Metafields Structure\n\nUse these metafields to store product data:\n\n{metafield_list}")
        
        # Workflow
        if self.key_info['workflow']:
            workflow_steps = '\n\n'.join(
                f"{i+1}. {step.strip()}"
                for i, step in enumerate(self.key_info['workflow'])
            )
            sections.append(f"# Product Creation Workflow\n\n{workflow_steps}")
        
        return '\n\n'.join(sections)
    
    def _add_coffee_product_sections(self) -> str:
        """Add sections specific to coffee products."""
        sections = [self._add_product_creation_sections()]
        
        if self.key_info['coffeeSpecific']:
            coffee_tags = '\n'.join(f"- {tag}" for tag in self.key_info['coffeeSpecific'])
            sections.append(f"# Coffee Product Tags\n\nFor coffee products, use these structured tag formats:\n\n{coffee_tags}")
        
        return '\n\n'.join(sections)
    
    def _add_technical_sections(self) -> str:
        """Add technical API sections."""
        sections = []
        
        # Just metafields for technical reference
        if self.key_info['metafields']:
            metafield_list = '\n'.join(
                f"- **{m['name']}**: `{m['namespace']}.{m['key']}`"
                for m in self.key_info['metafields']
            )
            sections.append(f"# Complete Metafields Reference\n\n{metafield_list}")
        
        return '\n\n'.join(sections)
    
    def save_prompts(self, output_dir: str = "../prompts"):
        """Generate and save all prompt variations."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Read guidelines first
        self.read_guidelines()
        self.extract_key_info()
        
        # Generate prompts
        prompts = {
            'productCreation': self.create_prompt('productCreation'),
            'coffeeProducts': self.create_prompt('coffeeProducts'),
            'technical': self.create_prompt('technical')
        }
        
        # Save text prompts
        for name, prompt in prompts.items():
            with open(output_path / f"{name}-system-prompt.txt", 'w') as f:
                f.write(prompt)
            print(f"✅ Created {name} prompt")
        
        # Save structured JSON
        structured_data = {
            'brand': self.key_info['brand'],
            'principles': self.key_info['principles'],
            'requirements': self.key_info['requirements'],
            'metafields': self.key_info['metafields'],
            'tags': self.key_info['tags'],
            'coffeeSpecific': self.key_info['coffeeSpecific'],
            'workflow': self.key_info['workflow']
        }
        
        with open(output_path / 'product-guidelines-structured.json', 'w') as f:
            json.dump(structured_data, f, indent=2)
        print("✅ Created structured JSON data")
        
        return prompts


def main():
    """Main function to run the converter."""
    parser = argparse.ArgumentParser(
        description='Convert product guidelines to system prompts for AI agents.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--guidelines-dir', '-g',
        default='../docs/product-guidelines',
        help='Directory containing the product guideline markdown files. (default: ../docs/product-guidelines)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='../prompts',
        help='Directory to save the generated prompts. (default: ../prompts)'
    )
    
    args = parser.parse_args()
    
    converter = ProductGuidelinesConverter(guidelines_dir=args.guidelines_dir)
    converter.save_prompts(output_dir=args.output_dir)
    print("\n🎉 Product guidelines successfully converted to system prompts!")


if __name__ == '__main__':
    main()
