# ☕ iDrinkCoffee.com Product Creation Guidelines

This documentation provides comprehensive guidelines for creating and managing product listings for iDrinkCoffee.com using the Shopify Admin API.

## Purpose

These guidelines help EspressoBot assist with:
- Creating compelling, accurate product listings that match the iDrinkCoffee.com brand
- Maintaining consistency across all product data
- Optimizing for SEO and customer experience
- Managing product metadata, tags, and technical specifications

## Documentation Structure

1. **[Product Creation Basics](./02-product-creation-basics.md)** - Core workflow and requirements
2. **[Metafields Reference](./03-metafields-reference.md)** - Complete metafield documentation
3. **[Tags System](./04-tags-system.md)** - Tagging conventions and complete tag list
4. **[Coffee Products](./05-coffee-products.md)** - Special guidelines for coffee listings
5. **[API Technical Reference](./06-api-technical-reference.md)** - GraphQL mutations and technical details
6. **[Product Anatomy](./07-product-anatomy.md)** - Complete product data model

## Quick Start

1. Set environment variables (see main README)
2. Use `python tools/search_products.py` to check for existing products
3. Use `python tools/create_product.py` with appropriate parameters
4. Add metafields and tags according to product type
5. Create feature boxes using `create_feature_box()` when applicable

## Key Principles

- **Act human:** Write naturally and engagingly
- **Be accurate:** Double-check all information before including it
- **Follow conventions:** Use established naming patterns and tag systems
- **Canadian English:** Use Canadian spelling and terminology
- **Draft first:** Always create products in DRAFT status

## Important Notes

- Cost of Goods (COGS) must be included for all products
- Inventory tracking should be enabled with "deny" when out of stock
- Each variant is created as a separate product (not using Shopify's variant system)
- All REST endpoints are deprecated; use GraphQL exclusively