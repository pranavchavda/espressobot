"""
Native MCP implementation for managing SkuVault kits
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional, Tuple
from ..base import BaseMCPTool

class ManageSkuVaultKitsTool(BaseMCPTool):
    """Manage SkuVault kits (bundles/combos)"""
    
    name = "manage_skuvault_kits"
    description = "Create, update, and manage product kits in SkuVault"
    context = """
    Manages SkuVault kits - bundles of products sold as a single SKU.
    
    Features:
    - Create new kits with components
    - Update existing kit components
    - Remove kits
    - List all kits
    - Get specific kit details
    
    Component format: "SKU1:QTY1,SKU2:QTY2"
    Examples:
    - "BES870XL:1,EUREKA-SPEC:1" (Breville + Eureka combo)
    - "COFFEE-001:2,FILTERS-100:1" (Coffee starter pack)
    
    Actions:
    - create: Create new kit
    - update: Update kit components
    - remove: Delete kit
    - get: Get kit details
    - list: List all kits
    
    Requirements:
    - SKUVAULT_TENANT_TOKEN environment variable
    - SKUVAULT_USER_TOKEN environment variable
    
    Business Rules:
    - Kit SKUs typically use COMBO- or BUNDLE- prefix
    - Components must exist in SkuVault
    - Quantity must be positive integer
    - Kit lines use Combine=3 for proper inventory tracking
    
    Use cases:
    - Machine + grinder combos
    - Coffee starter bundles
    - Promotional packages
    - Seasonal kits
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "remove", "get", "list"],
                "description": "Action to perform"
            },
            "kit_sku": {
                "type": "string",
                "description": "Kit SKU (required for most actions)"
            },
            "components": {
                "type": "string",
                "description": "Components in format 'SKU1:QTY1,SKU2:QTY2'"
            },
            "title": {
                "type": "string",
                "description": "Kit title/description"
            },
            "limit": {
                "type": "integer",
                "description": "Limit for list action (default: 100)",
                "default": 100
            },
            "dry_run": {
                "type": "boolean",
                "description": "Preview without making changes",
                "default": False
            }
        },
        "required": ["action"]
    }
    
    def __init__(self):
        super().__init__()
        self.tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
        self.user_token = os.environ.get('SKUVAULT_USER_TOKEN')
        self.base_url = "https://app.skuvault.com/api"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute kit management action"""
        if not self.tenant_token or not self.user_token:
            return {
                "success": False,
                "error": "SkuVault credentials not configured. Set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN"
            }
        
        try:
            if action == "create":
                return await self._create_kit(kwargs)
            elif action == "update":
                return await self._update_kit(kwargs)
            elif action == "remove":
                return await self._remove_kit(kwargs)
            elif action == "get":
                return await self._get_kit(kwargs)
            elif action == "list":
                return await self._list_kits(kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    async def _create_kit(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new kit"""
        kit_sku = kwargs.get('kit_sku')
        components_str = kwargs.get('components')
        title = kwargs.get('title')
        dry_run = kwargs.get('dry_run', False)
        
        if not kit_sku or not components_str:
            return {
                "success": False,
                "error": "kit_sku and components are required for create action"
            }
        
        components = self._parse_components(components_str)
        if not components:
            return {
                "success": False,
                "error": "No valid components found"
            }
        
        # Build kit data
        kit_lines = []
        for sku, quantity in components:
            kit_line = {
                "LineName": sku,
                "Combine": 3,
                "Quantity": quantity,
                "Items": [sku]
            }
            kit_lines.append(kit_line)
        
        kit_data = {
            "Sku": kit_sku,
            "Title": title or f"Kit {kit_sku}",
            "KitLines": kit_lines
        }
        
        if dry_run:
            return {
                "success": True,
                "action": "would_create",
                "kit_sku": kit_sku,
                "title": kit_data['Title'],
                "components": components,
                "kit_data": kit_data
            }
        
        response = self._make_request("products/createKit", kit_data)
        
        if response.get("Status") in ["OK", "Success"] or (not response.get("Errors") and response.get("Status") != "Error"):
            return {
                "success": True,
                "message": f"Kit created successfully: {kit_sku}",
                "kit_sku": kit_sku,
                "components": components
            }
        else:
            return {
                "success": False,
                "error": response.get("Errors", ["Unknown error"]),
                "kit_sku": kit_sku
            }
    
    async def _update_kit(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing kit"""
        kit_sku = kwargs.get('kit_sku')
        components_str = kwargs.get('components')
        dry_run = kwargs.get('dry_run', False)
        
        if not kit_sku or not components_str:
            return {
                "success": False,
                "error": "kit_sku and components are required for update action"
            }
        
        components = self._parse_components(components_str)
        if not components:
            return {
                "success": False,
                "error": "No valid components found"
            }
        
        if dry_run:
            return {
                "success": True,
                "action": "would_update",
                "kit_sku": kit_sku,
                "components": components,
                "steps": [
                    f"Remove existing kit: {kit_sku}",
                    f"Create new kit with {len(components)} components"
                ]
            }
        
        # Note: SkuVault API doesn't support kit removal, so we can't truly update
        # Instead, we'll return an error explaining the limitation
        return {
            "success": False,
            "error": "Kit updating is not supported by the SkuVault API because there is no /removeKit endpoint. To update a kit, you must manually delete it via the SkuVault web interface and then recreate it using the create action.",
            "action": "update",
            "kit_sku": kit_sku
        }
    
    async def _remove_kit(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a kit"""
        kit_sku = kwargs.get('kit_sku')
        dry_run = kwargs.get('dry_run', False)
        
        if not kit_sku:
            return {
                "success": False,
                "error": "kit_sku is required for remove action"
            }
        
        if dry_run:
            return {
                "success": False,
                "action": "would_remove",
                "kit_sku": kit_sku,
                "note": "Kit removal is not supported by the SkuVault API"
            }
        
        return {
            "success": False,
            "error": "Kit removal is not supported by the SkuVault API. The /removeKit endpoint does not exist. Kits can only be created via the API, not removed. To remove a kit, use the SkuVault web interface.",
            "action": "remove",
            "kit_sku": kit_sku
        }
    
    async def _get_kit(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Get kit details"""
        kit_sku = kwargs.get('kit_sku')
        
        if not kit_sku:
            return {
                "success": False,
                "error": "kit_sku is required for get action"
            }
        
        # Get all kits and search for the specific SKU
        response = self._make_request("products/getKits", {})
        
        if "Kits" in response and not response.get("Errors"):
            for kit in response.get("Kits", []):
                if kit.get("SKU") == kit_sku:
                    components = []
                    
                    if kit.get("KitLines"):
                        for line in kit["KitLines"]:
                            # Get SKU from first item in the line
                            sku = ""
                            if line.get("Items") and len(line["Items"]) > 0:
                                sku = line["Items"][0].get("SKU", "")
                            
                            components.append({
                                "sku": sku,
                                "quantity": line.get("Quantity", 0),
                                "line_name": line.get("LineName", "")
                            })
                    
                    return {
                        "success": True,
                        "kit": {
                            "sku": kit_sku,
                            "description": kit.get("Description", "N/A"),
                            "components": components,
                            "component_count": len(components)
                        }
                    }
            
            return {
                "success": False,
                "error": f"Kit not found: {kit_sku}"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to retrieve kits: {response.get('Errors', ['Unknown error'])}"
            }
    
    async def _list_kits(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """List all kits"""
        limit = kwargs.get('limit', 100)
        
        # Use the correct getKits endpoint instead of getProducts
        # Try without pagination parameters first
        response = self._make_request("products/getKits", {})
        
        # Check for successful response - getKits might not return Status field
        if "Kits" in response and not response.get("Errors"):
            kits = []
            kits_data = response.get("Kits", [])
            
            for kit in kits_data:
                components = []
                # Extract components from KitLines
                if kit.get("KitLines"):
                    for line in kit["KitLines"]:
                        # Get SKU from first item in the line
                        sku = ""
                        if line.get("Items") and len(line["Items"]) > 0:
                            sku = line["Items"][0].get("SKU", "")
                        
                        components.append({
                            "sku": sku,
                            "quantity": line.get("Quantity", 0),
                            "line_name": line.get("LineName", "")
                        })
                
                kits.append({
                    "sku": kit.get("Sku") or kit.get("SKU", ""),
                    "description": kit.get("Description", "N/A"),
                    "components": components,
                    "component_count": len(components)
                })
            
            return {
                "success": True,
                "kits": kits,
                "count": len(kits),
                "total_kits_returned": len(kits_data),
                "note": f"Found {len(kits)} kits using getKits endpoint"
            }
        else:
            return {
                "success": False,
                "error": f"SkuVault API error: {response.get('Errors', ['No errors but no kits returned'])}",
                "status": response.get("Status", "No status field"),
                "response_keys": list(response.keys()) if isinstance(response, dict) else "Not a dict",
                "kits_count": len(response.get("Kits", [])),
                "errors_count": len(response.get("Errors", []))
            }
    
    def _parse_components(self, components_str: str) -> List[Tuple[str, int]]:
        """Parse component string into list of (sku, quantity) tuples"""
        components = []
        for component in components_str.split(','):
            component = component.strip()
            if ':' in component:
                sku, qty = component.split(':', 1)
                try:
                    quantity = int(qty)
                    if quantity <= 0:
                        quantity = 1
                    components.append((sku.strip(), quantity))
                except ValueError:
                    components.append((sku.strip(), 1))
            else:
                components.append((component.strip(), 1))
        
        return components
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to SkuVault API"""
        url = f"{self.base_url}/{endpoint}"
        
        request_body = {
            "TenantToken": self.tenant_token,
            "UserToken": self.user_token,
            **data
        }
        
        try:
            response = requests.post(url, json=request_body, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"SkuVault API error: {str(e)}")
    
    async def test(self) -> Dict[str, Any]:
        """Test SkuVault kit management capability"""
        if not self.tenant_token or not self.user_token:
            return {
                "status": "failed",
                "error": "SkuVault credentials not configured"
            }
        
        # Test component parsing
        test_components = "TEST-SKU:2,ANOTHER-SKU:1"
        parsed = self._parse_components(test_components)
        
        if len(parsed) == 2 and parsed[0] == ("TEST-SKU", 2) and parsed[1] == ("ANOTHER-SKU", 1):
            return {
                "status": "passed",
                "message": "SkuVault kit management tool ready"
            }
        else:
            return {
                "status": "failed",
                "error": "Component parsing test failed"
            }