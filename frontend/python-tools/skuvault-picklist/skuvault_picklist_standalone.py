#!/usr/bin/env python3
"""
SkuVault Picklist Generator - Standalone Version
This file contains everything needed to run the application.
Just copy this single file to Windows and run: python skuvault_picklist_standalone.py
"""

# Check and install required packages
import sys
import subprocess
import importlib

def check_and_install_packages():
    """Check and install required packages"""
    required = {
        'requests': 'requests',
        'cryptography': 'cryptography'
    }
    
    missing = []
    for module, package in required.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Installing required packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        print("Packages installed successfully!")

# Install packages if needed
check_and_install_packages()

# Now import everything
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import requests
import time
from datetime import datetime
import configparser
from typing import List, Dict, Any, Optional
import threading
from cryptography.fernet import Fernet
import base64
from dataclasses import dataclass

# ===== SKUVAULT API MODULE =====

@dataclass
class ProductLocation:
    sku: str
    code: str
    description: str
    location: str
    warehouse: str
    quantity_available: int
    quantity_on_hand: int

class SkuVaultAPI:
    def __init__(self, tenant_token: str, user_token: str):
        self.tenant_token = tenant_token
        self.user_token = user_token
        self.base_url = "https://app.skuvault.com/api"
        self.last_request_time = 0
        self.request_count = 0
        
    def _rate_limit(self):
        """Handle rate limiting - 10 requests per minute"""
        current_time = time.time()
        
        if current_time - self.last_request_time > 60:
            self.request_count = 0
            
        if self.request_count >= 10:
            wait_time = 60 - (current_time - self.last_request_time)
            if wait_time > 0:
                time.sleep(wait_time)
            self.request_count = 0
            
        self.request_count += 1
        self.last_request_time = current_time
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with authentication and error handling"""
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload["TenantToken"] = self.tenant_token
        payload["UserToken"] = self.user_token
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e.response, 'text'):
                error_msg += f"\nResponse: {e.response.text}"
            raise Exception(f"API request failed: {error_msg}")
    
    def get_products(self, skus: List[str]) -> List[Dict[str, Any]]:
        """Get product details for given SKUs"""
        payload = {
            "ProductSKUs": skus,
            "IncludeKitLines": True
        }
        
        result = self._make_request("products/getProducts", payload)
        
        if result.get('Status') != 'OK' and 'Products' not in result:
            raise Exception(f"API error: {result.get('Status', 'Unknown error')}")
            
        return result.get('Products', [])
    
    def get_inventory_by_location(self, skus: List[str]) -> List[ProductLocation]:
        """Get inventory locations for given SKUs"""
        products = self.get_products(skus)
        product_map = {p['Sku']: p for p in products}
        
        if not products:
            return []
        
        payload = {
            "ProductSKUs": skus,
            "IncludeKitLines": False
        }
        
        print(f"Fetching inventory locations for: {skus}")
        result = self._make_request("inventory/getInventoryByLocation", payload)
        print(f"Inventory API response keys: {list(result.keys())}")
        
        # If location API fails, use product data
        if 'Items' not in result and 'Products' not in result:
            print(f"Using product data for location info")
            locations = []
            for product in products:
                locations.append(ProductLocation(
                    sku=product.get('Sku', ''),
                    code=product.get('Code', ''),
                    description=product.get('Description', 'Unknown Product'),
                    location='Check SkuVault',
                    warehouse='Main',
                    quantity_available=product.get('QuantityAvailable', 0),
                    quantity_on_hand=product.get('QuantityOnHand', 0)
                ))
            return locations
        
        locations = []
        items = result.get('Items', result.get('Products', []))
        
        for item in items:
            sku = item.get('SKU', item.get('Sku', item.get('ProductSKU', '')))
            product = product_map.get(sku, {})
            
            location_data = item.get('LocationDetails', [])
            
            if not location_data:
                if 'Location' in item or 'WarehouseLocation' in item:
                    location_data = [{
                        'Location': item.get('Location', item.get('WarehouseLocation', 'Unknown')),
                        'Warehouse': item.get('Warehouse', item.get('WarehouseName', 'Main')),
                        'QuantityAvailable': item.get('QuantityAvailable', item.get('Quantity', 0)),
                        'QuantityOnHand': item.get('QuantityOnHand', item.get('Quantity', 0))
                    }]
                else:
                    location_data = [{
                        'Location': 'No Location Data',
                        'Warehouse': 'Main',
                        'QuantityAvailable': product.get('QuantityAvailable', 0),
                        'QuantityOnHand': product.get('QuantityOnHand', 0)
                    }]
            
            for loc in location_data:
                locations.append(ProductLocation(
                    sku=sku,
                    code=product.get('Code', ''),
                    description=product.get('Description', 'Unknown Product'),
                    location=loc.get('Location', 'Unknown'),
                    warehouse=loc.get('Warehouse', 'Main'),
                    quantity_available=loc.get('QuantityAvailable', loc.get('Quantity', 0)),
                    quantity_on_hand=loc.get('QuantityOnHand', loc.get('Quantity', 0))
                ))
        
        return locations

# ===== MAIN APPLICATION =====

class PicklistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("iDrinkCoffee Picklist Generator")
        self.root.geometry("1200x800")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.config_file = "skuvault_picklist_config.ini"
        self.load_config()
        
        self.api = None
        if self.tenant_token and self.user_token:
            try:
                self.api = SkuVaultAPI(self.tenant_token, self.user_token)
            except Exception as e:
                messagebox.showerror("API Error", f"Failed to initialize API: {str(e)}")
        
        self.picklist_items = []
        self.create_widgets()
        
        if not self.api:
            self.show_settings()
    
    def load_config(self):
        """Load configuration from file"""
        self.config = configparser.ConfigParser()
        
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            
            if 'credentials' in self.config:
                try:
                    key = self._get_or_create_key()
                    f = Fernet(key)
                    
                    encrypted_tenant = self.config.get('credentials', 'tenant_token', fallback='')
                    encrypted_user = self.config.get('credentials', 'user_token', fallback='')
                    
                    if encrypted_tenant:
                        self.tenant_token = f.decrypt(encrypted_tenant.encode()).decode()
                    else:
                        self.tenant_token = ''
                        
                    if encrypted_user:
                        self.user_token = f.decrypt(encrypted_user.encode()).decode()
                    else:
                        self.user_token = ''
                except Exception:
                    self.tenant_token = ''
                    self.user_token = ''
            else:
                self.tenant_token = ''
                self.user_token = ''
        else:
            self.tenant_token = ''
            self.user_token = ''
    
    def save_config(self):
        """Save configuration to file"""
        if not 'credentials' in self.config:
            self.config.add_section('credentials')
        
        key = self._get_or_create_key()
        f = Fernet(key)
        
        encrypted_tenant = f.encrypt(self.tenant_token.encode()).decode()
        encrypted_user = f.encrypt(self.user_token.encode()).decode()
        
        self.config.set('credentials', 'tenant_token', encrypted_tenant)
        self.config.set('credentials', 'user_token', encrypted_user)
        
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
    
    def _get_or_create_key(self):
        """Get or create encryption key"""
        key_file = "skuvault_key.key"
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def create_widgets(self):
        """Create all UI elements"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Picklist", command=self.new_picklist)
        file_menu.add_command(label="Save Picklist", command=self.save_picklist)
        file_menu.add_command(label="Load Picklist", command=self.load_picklist)
        file_menu.add_separator()
        file_menu.add_command(label="Print", command=self.print_picklist)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        title_label = ttk.Label(main_frame, text="iDrinkCoffee Picklist Generator", 
                               font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        entry_frame = ttk.LabelFrame(main_frame, text="Add Products", padding="10")
        entry_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(entry_frame, text="SKU or Barcode:").grid(row=0, column=0, padx=(0, 10))
        
        self.sku_entry = ttk.Entry(entry_frame, width=30, font=('Arial', 12))
        self.sku_entry.grid(row=0, column=1, padx=(0, 10))
        self.sku_entry.bind('<Return>', lambda e: self.add_to_picklist())
        self.sku_entry.focus()
        
        self.add_button = ttk.Button(entry_frame, text="Add to Picklist", 
                                    command=self.add_to_picklist)
        self.add_button.grid(row=0, column=2, padx=(0, 10))
        
        ttk.Button(entry_frame, text="Add Multiple", 
                  command=self.show_bulk_add).grid(row=0, column=3)
        
        list_frame = ttk.LabelFrame(main_frame, text="Current Picklist", padding="10")
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        tree_scroll = ttk.Scrollbar(list_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(list_frame, yscrollcommand=tree_scroll.set, height=15)
        tree_scroll.config(command=self.tree.yview)
        
        self.tree['columns'] = ('SKU', 'Description', 'Location', 'Warehouse', 'Available', 'Status')
        
        self.tree.column("#0", width=0, stretch=tk.NO)
        self.tree.column("SKU", width=150)
        self.tree.column("Description", width=300)
        self.tree.column("Location", width=150)
        self.tree.column("Warehouse", width=100)
        self.tree.column("Available", width=80)
        self.tree.column("Status", width=100)
        
        self.tree.heading("#0", text="", anchor=tk.W)
        self.tree.heading("SKU", text="SKU", anchor=tk.W)
        self.tree.heading("Description", text="Description", anchor=tk.W)
        self.tree.heading("Location", text="Location", anchor=tk.W)
        self.tree.heading("Warehouse", text="Warehouse", anchor=tk.W)
        self.tree.heading("Available", text="Qty", anchor=tk.CENTER)
        self.tree.heading("Status", text="Status", anchor=tk.CENTER)
        
        self.tree.tag_configure('picked', background='#90EE90')
        self.tree.tag_configure('lowstock', background='#FFB6C1')
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Mark as Picked", command=self.mark_picked)
        self.context_menu.add_command(label="Remove from List", command=self.remove_item)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(button_frame, text="Generate Picklist", 
                  command=self.generate_picklist).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear All", 
                  command=self.clear_picklist).pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def add_to_picklist(self):
        """Add SKU to picklist"""
        sku = self.sku_entry.get().strip()
        if not sku:
            return
        
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][0] == sku:
                messagebox.showinfo("Duplicate", f"SKU {sku} is already in the picklist")
                self.sku_entry.delete(0, tk.END)
                return
        
        item_id = self.tree.insert('', 'end', values=(sku, 'Loading...', '', '', '', 'Pending'))
        self.sku_entry.delete(0, tk.END)
        
        threading.Thread(target=self.fetch_location_data, args=(sku, item_id)).start()
    
    def fetch_location_data(self, sku: str, item_id: str):
        """Fetch location data for SKU"""
        try:
            if not self.api:
                self.root.after(0, lambda: self.tree.item(item_id, 
                    values=(sku, 'No API Connection', '', '', '', 'Error')))
                return
            
            locations = self.api.get_inventory_by_location([sku])
            
            if locations:
                loc = locations[0]
                status = 'Ready'
                tags = ()
                if loc.quantity_available <= 0:
                    status = 'Out of Stock'
                    tags = ('lowstock',)
                elif loc.quantity_available < 5:
                    status = 'Low Stock'
                    tags = ('lowstock',)
                
                self.root.after(0, lambda: self.tree.item(item_id, 
                    values=(loc.sku, loc.description, loc.location, 
                           loc.warehouse, loc.quantity_available, status),
                    tags=tags))
                
                self.picklist_items.append(loc)
            else:
                self.root.after(0, lambda: self.tree.item(item_id, 
                    values=(sku, 'Product not found', '', '', '0', 'Not Found')))
                
        except Exception as e:
            error_msg = str(e)
            print(f"Error fetching data for {sku}: {error_msg}")
            self.root.after(0, lambda msg=error_msg: self.tree.item(item_id, 
                values=(sku, f'Error: {msg}', '', '', '', 'Error')))
    
    def show_bulk_add(self):
        """Show dialog for adding multiple SKUs"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Multiple SKUs")
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text="Enter SKUs (one per line):").pack(pady=5)
        
        text = tk.Text(dialog, width=40, height=15)
        text.pack(pady=5, padx=10)
        
        def add_bulk():
            skus = text.get(1.0, tk.END).strip().split('\n')
            for sku in skus:
                if sku.strip():
                    self.sku_entry.delete(0, tk.END)
                    self.sku_entry.insert(0, sku.strip())
                    self.add_to_picklist()
            dialog.destroy()
        
        ttk.Button(dialog, text="Add All", command=add_bulk).pack(pady=5)
    
    def generate_picklist(self):
        """Generate organized picklist"""
        if not self.tree.get_children():
            messagebox.showinfo("Empty Picklist", "Please add items to the picklist first")
            return
        
        picklist_window = tk.Toplevel(self.root)
        picklist_window.title("Generated Picklist")
        picklist_window.geometry("800x600")
        
        text = tk.Text(picklist_window, wrap=tk.WORD, font=('Courier', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        picklist_text = self.format_picklist()
        text.insert(1.0, picklist_text)
        text.config(state=tk.DISABLED)
        
        button_frame = ttk.Frame(picklist_window)
        button_frame.pack(pady=5)
        
        ttk.Button(button_frame, text="Close", 
                  command=picklist_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def format_picklist(self) -> str:
        """Format picklist for printing"""
        lines = []
        lines.append("=" * 80)
        lines.append("iDrinkCoffee PICKLIST")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")
        
        locations = {}
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            location = values[2] if values[2] else 'Unknown'
            
            if location not in locations:
                locations[location] = []
            
            locations[location].append({
                'sku': values[0],
                'description': values[1],
                'quantity': values[4],
                'status': values[5]
            })
        
        sorted_locations = sorted(locations.keys())
        
        for location in sorted_locations:
            lines.append(f"\nLOCATION: {location}")
            lines.append("-" * 60)
            
            for item in locations[location]:
                lines.append(f"[ ] SKU: {item['sku']:<20} Qty: {item['quantity']:<5}")
                lines.append(f"    {item['description'][:50]}")
                if item['status'] != 'Ready':
                    lines.append(f"    ** {item['status']} **")
                lines.append("")
        
        lines.append("\n" + "=" * 80)
        lines.append(f"Total Items: {len(self.tree.get_children())}")
        lines.append("=" * 80)
        
        return '\n'.join(lines)
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("500x300")
        
        cred_frame = ttk.LabelFrame(dialog, text="SkuVault API Credentials", padding="10")
        cred_frame.pack(fill=tk.BOTH, padx=10, pady=10)
        
        ttk.Label(cred_frame, text="Tenant Token:").grid(row=0, column=0, sticky=tk.W, pady=5)
        tenant_entry = ttk.Entry(cred_frame, width=50)
        tenant_entry.grid(row=0, column=1, pady=5)
        tenant_entry.insert(0, self.tenant_token)
        
        ttk.Label(cred_frame, text="User Token:").grid(row=1, column=0, sticky=tk.W, pady=5)
        user_entry = ttk.Entry(cred_frame, width=50, show="*")
        user_entry.grid(row=1, column=1, pady=5)
        user_entry.insert(0, self.user_token)
        
        def save_settings():
            self.tenant_token = tenant_entry.get()
            self.user_token = user_entry.get()
            self.save_config()
            
            try:
                self.api = SkuVaultAPI(self.tenant_token, self.user_token)
                messagebox.showinfo("Success", "Settings saved successfully!")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to connect to API: {str(e)}")
        
        def test_connection():
            try:
                test_api = SkuVaultAPI(tenant_entry.get(), user_entry.get())
                test_api.get_products(['TEST'])
                messagebox.showinfo("Success", "Connection successful!")
            except Exception as e:
                messagebox.showerror("Connection Failed", str(e))
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Test Connection", 
                  command=test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", 
                  command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def mark_picked(self):
        """Mark selected item as picked"""
        selected = self.tree.selection()
        if selected:
            for item in selected:
                values = list(self.tree.item(item)['values'])
                values[5] = 'Picked'
                self.tree.item(item, values=values, tags=('picked',))
    
    def remove_item(self):
        """Remove selected item from picklist"""
        selected = self.tree.selection()
        if selected:
            for item in selected:
                self.tree.delete(item)
    
    def clear_picklist(self):
        """Clear all items from picklist"""
        if self.tree.get_children():
            if messagebox.askyesno("Clear Picklist", "Remove all items from the picklist?"):
                for item in self.tree.get_children():
                    self.tree.delete(item)
                self.picklist_items.clear()
    
    def new_picklist(self):
        """Start a new picklist"""
        self.clear_picklist()
    
    def save_picklist(self):
        """Save current picklist to file"""
        if not self.tree.get_children():
            messagebox.showinfo("Empty Picklist", "No items to save")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            data = []
            for child in self.tree.get_children():
                values = self.tree.item(child)['values']
                data.append({
                    'sku': values[0],
                    'description': values[1],
                    'location': values[2],
                    'warehouse': values[3],
                    'quantity': values[4],
                    'status': values[5]
                })
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            messagebox.showinfo("Saved", f"Picklist saved to {filename}")
    
    def load_picklist(self):
        """Load picklist from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                self.clear_picklist()
                
                for item in data:
                    tags = ()
                    if item.get('status') == 'Picked':
                        tags = ('picked',)
                    elif item.get('quantity', 0) < 5:
                        tags = ('lowstock',)
                    
                    self.tree.insert('', 'end', values=(
                        item.get('sku', ''),
                        item.get('description', ''),
                        item.get('location', ''),
                        item.get('warehouse', ''),
                        item.get('quantity', 0),
                        item.get('status', 'Ready')
                    ), tags=tags)
                
                messagebox.showinfo("Loaded", f"Loaded {len(data)} items")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
    
    def print_picklist(self):
        """Print the picklist"""
        self.generate_picklist()

# ===== MAIN ENTRY POINT =====

def main():
    root = tk.Tk()
    app = PicklistApp(root)
    root.mainloop()

if __name__ == "__main__":
    print("Starting SkuVault Picklist Generator...")
    main()