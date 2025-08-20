#!/usr/bin/env node
/**
 * Product Guidelines to System Prompt Converter
 * 
 * This tool converts product documentation and guidelines into structured
 * system prompts for AI agents, specifically for Shopify product creation.
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Sections that should be included in different prompt types
 */
const PROMPT_SECTIONS = {
  productCreation: {
    required: ['overview', 'basics', 'metafields', 'tags', 'workflow'],
    optional: ['coffee', 'api', 'anatomy']
  },
  coffeeProducts: {
    required: ['coffee', 'tags', 'basics'],
    optional: ['metafields', 'workflow']
  },
  technical: {
    required: ['api', 'metafields', 'anatomy'],
    optional: ['workflow', 'tags']
  }
};

/**
 * Read and parse markdown files from the product guidelines directory
 */
async function readProductGuidelines() {
  const guidelinesDir = path.join(__dirname, '../../../docs/product-guidelines');
  const files = await fs.readdir(guidelinesDir);
  const guidelines = {};
  
  for (const file of files) {
    if (file.endsWith('.md')) {
      const content = await fs.readFile(path.join(guidelinesDir, file), 'utf-8');
      const key = file.replace(/^\d+-/, '').replace('.md', '').replace(/-/g, '_');
      guidelines[key] = {
        filename: file,
        content: content,
        title: extractTitle(content)
      };
    }
  }
  
  return guidelines;
}

/**
 * Extract title from markdown content
 */
function extractTitle(content) {
  const match = content.match(/^#\s+(.+)$/m);
  return match ? match[1].replace(/[☕️🔧🚀✨]/g, '').trim() : 'Untitled';
}

/**
 * Extract key information from guidelines
 */
function extractKeyInfo(guidelines) {
  const info = {
    brand: 'iDrinkCoffee.com',
    principles: [],
    requirements: [],
    workflow: [],
    metafields: [],
    tags: [],
    coffeeSpecific: []
  };
  
  // Extract from overview
  if (guidelines.overview) {
    const principlesMatch = guidelines.overview.content.match(/## Key Principles\n\n([\s\S]+?)(?=\n##|$)/);
    if (principlesMatch) {
      info.principles = principlesMatch[1].split('\n').filter(line => line.startsWith('-')).map(line => line.substring(2));
    }
  }
  
  // Extract from basics
  if (guidelines.product_creation_basics) {
    const reqMatch = guidelines.product_creation_basics.content.match(/## Core Requirements\n\n([\s\S]+?)(?=\n##|$)/);
    if (reqMatch) {
      info.requirements = reqMatch[1].split('\n').filter(line => line.startsWith('-')).map(line => line.substring(2));
    }
    
    const workflowMatch = guidelines.product_creation_basics.content.match(/## Product Creation Workflow\n\n([\s\S]+?)(?=\n##|$)/);
    if (workflowMatch) {
      info.workflow = workflowMatch[1].split('\n\n').filter(section => section.includes('**'));
    }
  }
  
  // Extract metafield types
  if (guidelines.metafields_reference) {
    const metafieldMatches = guidelines.metafields_reference.content.matchAll(/### (.+?)\n- \*\*Namespace:\*\* `(.+?)`\n- \*\*Key:\*\* `(.+?)`/g);
    for (const match of metafieldMatches) {
      info.metafields.push({
        name: match[1],
        namespace: match[2],
        key: match[3]
      });
    }
  }
  
  // Extract tag categories
  if (guidelines.tags_system) {
    const tagMatches = guidelines.tags_system.content.matchAll(/### (.+?)\n([\s\S]+?)(?=\n###|$)/g);
    for (const match of tagMatches) {
      const category = match[1];
      const tags = match[2].split('\n').filter(line => line.startsWith('-')).map(line => line.match(/`(.+?)`/)?.[1]).filter(Boolean);
      if (tags.length > 0) {
        info.tags.push({ category, tags });
      }
    }
  }
  
  // Extract coffee-specific info
  if (guidelines.coffee_products) {
    const coffeeTagMatch = guidelines.coffee_products.content.match(/### Required Tag Format\n\n([\s\S]+?)(?=\n###|$)/);
    if (coffeeTagMatch) {
      info.coffeeSpecific = coffeeTagMatch[1].split('\n').filter(line => line.startsWith('-')).map(line => line.substring(2));
    }
  }
  
  return info;
}

/**
 * Convert guidelines to system prompt
 */
function createSystemPrompt(guidelines, keyInfo, promptType = 'productCreation') {
  const sections = PROMPT_SECTIONS[promptType];
  
  let prompt = `You are a Shopify product creation specialist for ${keyInfo.brand}. You help create, update, and manage product listings using the Shopify Admin API.\n\n`;
  
  // Add key principles
  if (keyInfo.principles.length > 0) {
    prompt += `# Key Principles\n\n`;
    keyInfo.principles.forEach(principle => {
      prompt += `- ${principle}\n`;
    });
    prompt += '\n';
  }
  
  // Add core requirements
  if (sections.required.includes('basics') && keyInfo.requirements.length > 0) {
    prompt += `# Core Product Requirements\n\nEvery product must include:\n`;
    keyInfo.requirements.forEach(req => {
      prompt += `- ${req}\n`;
    });
    prompt += '\n';
  }
  
  // Add metafields information
  if (sections.required.includes('metafields') && keyInfo.metafields.length > 0) {
    prompt += `# Metafields Structure\n\nUse these metafields to store product data:\n\n`;
    keyInfo.metafields.forEach(field => {
      prompt += `- **${field.name}**: \`${field.namespace}.${field.key}\`\n`;
    });
    prompt += '\n';
  }
  
  // Add tags information
  if (sections.required.includes('tags') && keyInfo.tags.length > 0) {
    prompt += `# Tagging System\n\nApply appropriate tags from these categories:\n\n`;
    keyInfo.tags.forEach(tagCategory => {
      prompt += `## ${tagCategory.category}\n`;
      tagCategory.tags.forEach(tag => {
        prompt += `- \`${tag}\`\n`;
      });
      prompt += '\n';
    });
  }
  
  // Add coffee-specific instructions
  if (promptType === 'coffeeProducts' && keyInfo.coffeeSpecific.length > 0) {
    prompt += `# Coffee Product Tags\n\nFor coffee products, use these structured tag formats:\n\n`;
    keyInfo.coffeeSpecific.forEach(tag => {
      prompt += `- ${tag}\n`;
    });
    prompt += '\nNote: For NOTES tags, use # to separate values (e.g., NOTES-Chocolate#Caramel#Citrus)\n\n';
  }
  
  // Add workflow
  if (sections.required.includes('workflow') && keyInfo.workflow.length > 0) {
    prompt += `# Product Creation Workflow\n\n`;
    keyInfo.workflow.forEach((step, index) => {
      prompt += `${index + 1}. ${step.trim()}\n\n`;
    });
  }
  
  // Add specific instructions based on prompt type
  prompt += `# Specific Instructions\n\n`;
  
  switch (promptType) {
    case 'productCreation':
      prompt += `When creating products:
1. Always start with products in DRAFT status
2. Include Cost of Goods (COGS) for all products
3. Enable inventory tracking with "deny" policy when out of stock
4. Create each variant as a separate product (not using Shopify's variant system)
5. Use GraphQL exclusively (REST endpoints are deprecated)
6. For feature boxes, ensure metaobjects are published (status: ACTIVE) to display on storefront

Tools available:
- \`python tools/search_products.py\` - Check for existing products
- \`python tools/create_product.py\` - Create new products
- \`python tools/set_metafield.py\` - Add metafields to products
- Use MCP tools (introspect_admin_schema, search_dev_docs) for API reference\n`;
      break;
      
    case 'coffeeProducts':
      prompt += `When creating coffee products:
1. Vendor must be "Escarpment Coffee Roasters" 
2. Product Type must be "Fresh Coffee"
3. Skip Buy Box, FAQs, Tech Specs, and Features sections
4. Focus on creating detailed and engaging overview in body_html
5. Include origin story, flavor profile, processing details, and brewing methods
6. Use structured tags with proper prefixes (ROAST-, REGION-, PROCESSING-, etc.)
7. Set seasonality metafield (coffee.seasonality) as boolean
8. For NOTES tags, use # to separate values

Example coffee product title format: "{Origin} {Farm/Coop} - {Region}"\n`;
      break;
      
    case 'technical':
      prompt += `When working with the Shopify Admin API:
1. Use GraphQL mutations exclusively
2. Always validate input against the schema using introspect_admin_schema
3. Handle errors gracefully and provide clear feedback
4. Use appropriate GraphQL input types (e.g., ProductInput, MetafieldInput)
5. Remember that metaobjects must be published to appear on storefront
6. Cost is stored in the variant's inventoryItem, not the variant itself\n`;
      break;
  }
  
  return prompt;
}

/**
 * Generate prompts for different use cases
 */
async function generatePrompts() {
  console.log('📚 Reading product guidelines...');
  const guidelines = await readProductGuidelines();
  
  console.log('🔍 Extracting key information...');
  const keyInfo = extractKeyInfo(guidelines);
  
  const prompts = {
    productCreation: createSystemPrompt(guidelines, keyInfo, 'productCreation'),
    coffeeProducts: createSystemPrompt(guidelines, keyInfo, 'coffeeProducts'),
    technical: createSystemPrompt(guidelines, keyInfo, 'technical')
  };
  
  // Save prompts
  const outputDir = path.join(__dirname, '../prompts');
  await fs.mkdir(outputDir, { recursive: true });
  
  for (const [name, prompt] of Object.entries(prompts)) {
    const filename = path.join(outputDir, `${name}-system-prompt.txt`);
    await fs.writeFile(filename, prompt);
    console.log(`✅ Created ${name} prompt: ${filename}`);
  }
  
  // Also create a combined prompt for general use
  const combinedPrompt = `${prompts.productCreation}\n\n---\n\n# Coffee Products Addition\n\n${prompts.coffeeProducts.split('# Specific Instructions')[1]}\n\n---\n\n# Technical Reference\n\n${prompts.technical.split('# Specific Instructions')[1]}`;
  
  await fs.writeFile(path.join(outputDir, 'combined-system-prompt.txt'), combinedPrompt);
  console.log('✅ Created combined prompt');
  
  // Create a JSON version with structured data
  const structuredData = {
    brand: keyInfo.brand,
    principles: keyInfo.principles,
    requirements: keyInfo.requirements,
    metafields: keyInfo.metafields,
    tags: keyInfo.tags,
    coffeeSpecific: keyInfo.coffeeSpecific,
    workflow: keyInfo.workflow,
    prompts: prompts
  };
  
  await fs.writeFile(
    path.join(outputDir, 'product-guidelines-structured.json'),
    JSON.stringify(structuredData, null, 2)
  );
  console.log('✅ Created structured JSON data');
  
  return prompts;
}

/**
 * Create a Python version of the converter
 */
async function createPythonConverter() {
  const pythonCode = `#!/usr/bin/env python3
"""
Product Guidelines to System Prompt Converter (Python version)
Converts product documentation into AI agent prompts for Shopify product creation.
"""

import json
import os
from pathlib import Path
import re
from typing import Dict, List, Optional

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
        match = re.search(r'^#\\s+(.+)$', content, re.MULTILINE)
        if match:
            return re.sub(r'[☕️🔧🚀✨]', '', match.group(1)).strip()
        return 'Untitled'
    
    def extract_key_info(self) -> Dict:
        """Extract key information from guidelines."""
        # Extract principles
        if 'overview' in self.guidelines:
            principles_match = re.search(
                r'## Key Principles\\n\\n([\\s\\S]+?)(?=\\n##|$)',
                self.guidelines['overview']['content']
            )
            if principles_match:
                self.key_info['principles'] = [
                    line[2:] for line in principles_match.group(1).split('\\n')
                    if line.startswith('-')
                ]
        
        # Extract requirements and workflow
        if 'product_creation_basics' in self.guidelines:
            content = self.guidelines['product_creation_basics']['content']
            
            req_match = re.search(
                r'## Core Requirements\\n\\n([\\s\\S]+?)(?=\\n##|$)',
                content
            )
            if req_match:
                self.key_info['requirements'] = [
                    line[2:] for line in req_match.group(1).split('\\n')
                    if line.startswith('-')
                ]
            
            workflow_match = re.search(
                r'## Product Creation Workflow\\n\\n([\\s\\S]+?)(?=\\n##|$)',
                content
            )
            if workflow_match:
                self.key_info['workflow'] = [
                    section for section in workflow_match.group(1).split('\\n\\n')
                    if '**' in section
                ]
        
        # Extract metafields
        if 'metafields_reference' in self.guidelines:
            content = self.guidelines['metafields_reference']['content']
            metafield_pattern = r'### (.+?)\\n- \\*\\*Namespace:\\*\\* \`(.+?)\`\\n- \\*\\*Key:\\*\\* \`(.+?)\`'
            
            for match in re.finditer(metafield_pattern, content):
                self.key_info['metafields'].append({
                    'name': match.group(1),
                    'namespace': match.group(2),
                    'key': match.group(3)
                })
        
        # Extract tags
        if 'tags_system' in self.guidelines:
            content = self.guidelines['tags_system']['content']
            tag_pattern = r'### (.+?)\\n([\\s\\S]+?)(?=\\n###|$)'
            
            for match in re.finditer(tag_pattern, content):
                category = match.group(1)
                tag_content = match.group(2)
                tags = []
                
                for line in tag_content.split('\\n'):
                    if line.startswith('-'):
                        tag_match = re.search(r'\`(.+?)\`', line)
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
                r'### Required Tag Format\\n\\n([\\s\\S]+?)(?=\\n###|$)',
                content
            )
            if coffee_match:
                self.key_info['coffeeSpecific'] = [
                    line[2:] for line in coffee_match.group(1).split('\\n')
                    if line.startswith('-')
                ]
        
        return self.key_info
    
    def create_prompt(self, prompt_type: str = 'productCreation') -> str:
        """Create system prompt based on type."""
        prompt = f"You are a Shopify product creation specialist for {self.key_info['brand']}. "
        prompt += "You help create, update, and manage product listings using the Shopify Admin API.\\n\\n"
        
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
            sections.append("# Key Principles\\n\\n" + 
                          '\\n'.join(f"- {p}" for p in self.key_info['principles']))
        
        # Core requirements
        if self.key_info['requirements']:
            sections.append("# Core Product Requirements\\n\\nEvery product must include:\\n" +
                          '\\n'.join(f"- {r}" for r in self.key_info['requirements']))
        
        # Metafields
        if self.key_info['metafields']:
            metafield_list = '\\n'.join(
                f"- **{m['name']}**: \`{m['namespace']}.{m['key']}\`"
                for m in self.key_info['metafields'][:10]  # First 10 most important
            )
            sections.append(f"# Metafields Structure\\n\\nUse these metafields to store product data:\\n\\n{metafield_list}")
        
        # Workflow
        if self.key_info['workflow']:
            workflow_steps = '\\n\\n'.join(
                f"{i+1}. {step.strip()}"
                for i, step in enumerate(self.key_info['workflow'])
            )
            sections.append(f"# Product Creation Workflow\\n\\n{workflow_steps}")
        
        return '\\n\\n'.join(sections)
    
    def _add_coffee_product_sections(self) -> str:
        """Add sections specific to coffee products."""
        sections = [self._add_product_creation_sections()]
        
        if self.key_info['coffeeSpecific']:
            coffee_tags = '\\n'.join(f"- {tag}" for tag in self.key_info['coffeeSpecific'])
            sections.append(f"# Coffee Product Tags\\n\\nFor coffee products, use these structured tag formats:\\n\\n{coffee_tags}")
        
        return '\\n\\n'.join(sections)
    
    def _add_technical_sections(self) -> str:
        """Add technical API sections."""
        sections = []
        
        # Just metafields for technical reference
        if self.key_info['metafields']:
            metafield_list = '\\n'.join(
                f"- **{m['name']}**: \`{m['namespace']}.{m['key']}\`"
                for m in self.key_info['metafields']
            )
            sections.append(f"# Complete Metafields Reference\\n\\n{metafield_list}")
        
        return '\\n\\n'.join(sections)
    
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
    converter = ProductGuidelinesConverter()
    converter.save_prompts()
    print("\\n🎉 Product guidelines successfully converted to system prompts!")


if __name__ == '__main__':
    main()
`;

  const pythonPath = path.join(__dirname, '../../python-tools/product_guidelines_to_prompt.py');
  await fs.writeFile(pythonPath, pythonCode);
  await fs.chmod(pythonPath, 0o755);
  console.log(`✅ Created Python converter: ${pythonPath}`);
}

// Main execution
if (import.meta.url === `file://${process.argv[1]}`) {
  console.log('🚀 Product Guidelines to System Prompt Converter\n');
  
  generatePrompts()
    .then(async () => {
      await createPythonConverter();
      console.log('\n🎉 Successfully converted product guidelines to system prompts!');
      console.log('\nGenerated files:');
      console.log('  - server/prompts/productCreation-system-prompt.txt');
      console.log('  - server/prompts/coffeeProducts-system-prompt.txt');
      console.log('  - server/prompts/technical-system-prompt.txt');
      console.log('  - server/prompts/combined-system-prompt.txt');
      console.log('  - server/prompts/product-guidelines-structured.json');
      console.log('  - python-tools/product_guidelines_to_prompt.py');
    })
    .catch(error => {
      console.error('❌ Error:', error);
      process.exit(1);
    });
}

export { readProductGuidelines, extractKeyInfo, createSystemPrompt, generatePrompts };