import argparse
from typing import Optional
import csv
import json
import logging
import os
import time
from typing import Dict, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
import fcntl

# Constants
SHOP_DOMAIN = "idrinkcoffee.myshopify.com"
ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
API_VERSION = os.environ.get('SHOPIFY_API_VERSION')
HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN,
}

# Abort at startup if token missing
if not ACCESS_TOKEN or not API_VERSION:
    sys.exit("Missing SHOPIFY_ACCESS_TOKEN or SHOPIFY_API_VERSION")

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Retry strategy for API requests
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    backoff_factor=1,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

def fetch_product_details(product_id: str) -> Optional[Dict]:
    """Fetch original product details using GraphQL."""
    query = f"""
    {{
      product(id: "gid://shopify/Product/{product_id}") {{
        title
        tags
        descriptionHtml
        featuredImage {{
            id
            url
        }}
        variants(first: 1) {{
          edges {{
            node {{
              id
              price
              compareAtPrice
              sku
            }}
          }}
        }}
      }}
    }}
    """
    try:
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": query},
        )
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            logging.error(
                f"GraphQL error fetching product {product_id}: {data['errors']}"
            )
            return None
        return data["data"]["product"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching product {product_id}: {e}")
        return None

def duplicate_product(product_id: str, new_title: str, output_file: str) -> Optional[str]:
    """Duplicate the product with a new title using official productDuplicate mutation."""
    mutation = """
    mutation DuplicateProduct($productId: ID!, $newTitle: String!, $includeImages: Boolean!, $newStatus: ProductStatus!) {
      productDuplicate(productId: $productId, newTitle: $newTitle, includeImages: $includeImages, newStatus: $newStatus) {
        newProduct { id }
        userErrors { field message }
      }
    }
    """
    variables = {
        "productId": f"gid://shopify/Product/{product_id}",
        "newTitle": new_title,
        "includeImages": True,
        "newStatus": "DRAFT",
    }
    try:
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": mutation, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()
        if 'errors' in data:
            logging.error(f"GraphQL error duplicating product {product_id}: {data['errors']}")
            return None
        payload = data.get('data', {}).get('productDuplicate')
        if not payload:
            logging.error(f"Unexpected GraphQL response duplicating product {product_id}: {data}")
            return None
        user_errors = payload.get('userErrors', [])
        if user_errors:
            logging.error(f"Error duplicating product {product_id}: {user_errors}")
            return None
        new_product_gid = payload['newProduct']['id']
        new_product_id = new_product_gid.split("/")[-1]
        save_duplicated_product_ids(product_id, new_product_id, output_file, new_title)
        return new_product_id
    except requests.exceptions.RequestException as e:
        logging.error(f"Error duplicating product {product_id}: {e}")
        return None

def save_duplicated_product_ids(product_id, new_product_id, output_file, new_title):
    """Save the duplicated product ID to a file."""
    with open(output_file, "a") as file:
        file.write(f"{product_id},{new_product_id},{new_title}\n")

def get_default_location_id() -> Optional[str]:
    """Fetch the first available shop location ID."""
    query = """
    {
      locations(first: 1) {
        edges { node { id } }
      }
    }
    """
    try:
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": query},
        )
        response.raise_for_status()
        data = response.json()
        edges = data.get("data", {}).get("locations", {}).get("edges", [])
        if edges:
            return edges[0]["node"]["id"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching default location: {e}")
    return None

def update_product_details(product_id: str, tags: List[str], notes: str) -> bool:
    """
    Update the product's tags and descriptionHtml using productUpdate.
    """
    original_details = fetch_product_details(product_id)
    if not original_details:
        return False
    original_body_html = original_details.get("descriptionHtml", "")
    updated_body_html = f"<strong>{notes}</strong>\n{original_body_html}"
    mutation = """
    mutation UpdateProduct($input: ProductInput!) {
      productUpdate(input: $input) {
        product { id tags descriptionHtml }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": {
            "id": f"gid://shopify/Product/{product_id}",
            "tags": tags,
            "descriptionHtml": updated_body_html
        }
    }
    try:
        logging.debug(f"productUpdate variables: {variables}")
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": mutation, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()
        logging.debug(f"productUpdate Response: {data}")
        if data.get("errors"):
            logging.error(f"GraphQL error updating product {product_id}: {data['errors']}")
            return False
        user_errors = data["data"]["productUpdate"]["userErrors"]
        if user_errors:
            logging.error(f"Error updating product {product_id} (tags/desc): {user_errors}")
            return False
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error updating product {product_id}: {e}")
        return False

def set_inventory_to_one(variant_id: str) -> bool:
    """Set the inventory quantity of a variant's inventory item to 1."""
    query = """
    query VariantInventory($id: ID!) {
      productVariant(id: $id) {
        id
        inventoryItem { id }
        inventoryQuantity
      }
    }
    """
    variables = {"id": variant_id}
    try:
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            logging.error(f"GraphQL error fetching inventory for variant {variant_id}: {data['errors']}")
            return False
        product_variant = data["data"]["productVariant"]
        inventory_item_id = product_variant["inventoryItem"]["id"]
        current_quantity = product_variant.get("inventoryQuantity", 0)
        if not inventory_item_id:
            logging.error(f"No InventoryItem ID for variant {variant_id}.")
            return False
        delta = 1 - current_quantity
        location_id = get_default_location_id()
        if not location_id:
            logging.error("Unable to retrieve default location ID.")
            return False
        mutation = """
        mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
          inventoryAdjustQuantities(input: $input) {
            userErrors { field message }
            inventoryAdjustmentGroup { changes { name delta } }
          }
        }
        """
        variables_input = {
            "input": {
                "reason": "correction",
                "name": "available",
                "referenceDocumentUri": "logistics://some.warehouse/take/2023-01/13",
                "changes": [{
                    "delta": delta,
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_id
                }]
            }
        }
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": mutation, "variables": variables_input},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            logging.error(f"GraphQL error adjusting inventory: {data['errors']}")
            return False
        if data["data"]["inventoryAdjustQuantities"]["userErrors"]:
            logging.error(f"Error adjusting inventory: {data['data']['inventoryAdjustQuantities']['userErrors']}")
            return False
        logging.info(f"Inventory set to 1 for inventory item {inventory_item_id}.")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error setting inventory for variant {variant_id}: {e}")
        return False

def update_variant_details(variant_id: str, price: str, compare_price: str, new_sku: str, new_product_id: str) -> bool:
    """
    Update the product variant's price, compareAtPrice, and sku using bulk mutation.
    """
    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        product { id }
        productVariants { id price sku compareAtPrice inventoryItem { tracked } }
        userErrors { field message }
      }
    }
    """
    variables = {
        "productId": f"gid://shopify/Product/{new_product_id}",
        "variants": [{
            "id": variant_id,
            "price": price,
            "compareAtPrice": compare_price,
            "inventoryPolicy": "DENY",
            "inventoryItem": {"sku": new_sku, "tracked": True}
        }]
    }
    try:
        logging.debug(f"productVariantsBulkUpdate variables: {variables}")
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": mutation, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()
        logging.debug(f"productVariantsBulkUpdate Response: {data}")
        if data.get("errors"):
            logging.error(f"GraphQL error updating variant {variant_id}: {data['errors']}")
            return False
        user_errors = data["data"]["productVariantsBulkUpdate"]["userErrors"]
        if user_errors:
            logging.error(f"Error updating variant {variant_id}: {user_errors}")
            return False
        variant_data = data["data"]["productVariantsBulkUpdate"]["productVariants"][0]
        if variant_data["price"] != price:
            logging.error(f"Price update failed for variant {variant_id}. Expected {price}, got {variant_data['price']}")
            return False
        logging.info(f"Variant update successful: Price {variant_data['price']} | CompareAtPrice {variant_data['compareAtPrice']} | SKU {variant_data['sku']}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error updating variant {variant_id}: {e}")
        return False

def write_kit_csv(
    kit_sku: str,
    sku_code: str,
    line_item_name: str,
    kit_title: str
):
    """
    Append a single row to single_item_kits.csv.
    """
    csv_filename = "single_item_kits.csv"
    file_exists = os.path.isfile(csv_filename)
    with open(csv_filename, mode="a", newline="") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "Kit Sku", "Kit Code", "Sku/Code", "Line Item Name",
                "Quantity", "Combine Option", "Disable Quantity Sync",
                "Kit Title", "Statuses"
            ])
        writer.writerow([
            kit_sku, "", sku_code, line_item_name,
            "1", "1", "Disabled",
            kit_title, ""
        ])
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)

def clear_bundle_product_ids(product_id: str) -> bool:
    logging.info(f"Checking for 'bundle_product_ids' metafield on product {product_id}...")
    query = f"""
    {{
      product(id: "gid://shopify/Product/{product_id}") {{
        metafield(namespace: "custom", key: "bundle_product_ids") {{
          id
        }}
      }}
    }}
    """
    try:
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": query},
        )
        response.raise_for_status()
        data = response.json()
        metafield = data["data"]["product"]["metafield"]
        if metafield:
            metafield_id = metafield["id"]
            logging.info(f"'bundle_product_ids' metafield found: {metafield_id}, removing it...")
            delete_mutation = """
            mutation metafieldDelete($input: MetafieldDeleteInput!) {
              metafieldDelete(input: $input) {
                deletedId
                userErrors {
                  field
                  message
                }
              }
            }
            """
            variables = {
                "input": {
                    "id": metafield_id
                }
            }
            delete_response = http.post(
                f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
                headers=HEADERS,
                json={"query": delete_mutation, "variables": variables},
            )
            delete_response.raise_for_status()
            delete_data = delete_response.json()
            if delete_data["data"]["metafieldDelete"]["userErrors"]:
                logging.error(f"Error removing 'bundle_product_ids': {delete_data['data']['metafieldDelete']['userErrors']}")
                return False
            logging.info(f"Successfully removed 'bundle_product_ids' metafield from product {product_id}.")
        else:
            logging.info("No 'bundle_product_ids' metafield found, so nothing to remove.")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error clearing 'bundle_product_ids' for product {product_id}: {e}")
        return False

def remove_extra_variants(product_id: str, keep_variant_id: str) -> bool:
    """
    Delete all variants for a product except the one with keep_variant_id.
    """
    logging.info(f"remove_extra_variants: product {product_id}, keeping variant {keep_variant_id}")
    # Fetch all variants of the duplicated product
    query = """
    query GetVariants($id: ID!) {
      product(id: $id) {
        variants(first: 100) {
          edges { node { id } }
        }
      }
    }
    """
    variables = {"id": f"gid://shopify/Product/{product_id}"}
    try:
        response = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()
        # Check for GraphQL errors
        if 'errors' in data:
            logging.error(f"GraphQL error fetching variants for product {product_id}: {data['errors']}")
            return False
        product_data = data.get('data', {}).get('product')
        if not product_data or 'variants' not in product_data:
            logging.error(f"Unexpected GraphQL response fetching variants for product {product_id}: {data}")
            return False
        variants = product_data['variants']['edges']
        variant_ids = [edge.get('node', {}).get('id') for edge in variants if edge.get('node', {}).get('id')]
        extra_ids = [vid for vid in variant_ids if vid != keep_variant_id]
        if extra_ids:
            logging.info(f"Bulk deleting variants {extra_ids} for product {product_id}")
            mutation = """
            mutation BulkDeleteVariants($productId: ID!, $variantsIds: [ID!]!) {
              productVariantsBulkDelete(productId: $productId, variantsIds: $variantsIds) {
                userErrors { field message }
              }
            }
            """
            variables_bulk = {"productId": f"gid://shopify/Product/{product_id}", "variantsIds": extra_ids}
            del_resp = http.post(
                f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
                headers=HEADERS,
                json={"query": mutation, "variables": variables_bulk},
            )
            del_resp.raise_for_status()
            del_data = del_resp.json()
            if 'errors' in del_data:
                logging.error(f"GraphQL error bulk deleting variants: {del_data['errors']}")
                return False
            payload = del_data.get('data', {}).get('productVariantsBulkDelete')
            if not payload or payload.get('userErrors'):
                logging.error(f"Bulk delete user errors: {payload.get('userErrors') if payload else del_data}")
                return False
            logging.info(f"Bulk delete completed for product {product_id}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error removing extra variants for product {product_id}: {e}")
        return False

def process_products_from_csv(csv_file: str):
    """Process products listed in a CSV file."""
    with open(csv_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            product_id = row["product_id"]
            new_title = f"{row['title']} |{row['ListingNumber']}| {row['TitleSuffix']}"
            discount = float(row["discount"]) if row["discount"] else 0
            skuPrefix = row["SKUPrefix"]
            tag_to_add_str = (
                row["TagToAdd"]
                + ",open-box,openbox,ob" + time.strftime("%m%d%Y")
                + ",ob" + time.strftime("%y%m")
            )
            notes_to_append = row["NoteToAppend"]
            customPrice = float(row["CustomPrice"]) if row["CustomPrice"] else None
            if customPrice is not None:
                customPrice = "{:.2f}".format(customPrice)

            try:
                original_details = fetch_product_details(product_id)
                if not original_details:
                    continue

                price = original_details["variants"]["edges"][0]["node"]["price"]
                compare_at_price = original_details["variants"]["edges"][0]["node"]["compareAtPrice"]
                imageUrl = original_details.get("featuredImage", {}).get("url")

                price = float(price) if price else 0
                compare_at_price = float(compare_at_price) if compare_at_price else 0
                original_price = max(price, compare_at_price)
                new_price = customPrice if customPrice else f"{original_price * (1 - discount/100):.2f}"
                new_sku = f"{skuPrefix}{original_details['variants']['edges'][0]['node']['sku']}"

                new_product_id = duplicate_product(product_id, new_title, "duplicated_products.csv")
                if not new_product_id:
                    continue

                clear_bundle_product_ids(new_product_id)

                new_product_details = fetch_product_details(new_product_id)
                if not new_product_details:
                    continue
                new_variant_id = new_product_details["variants"]["edges"][0]["node"]["id"]

                # remove extra variants and abort on failure
                if not remove_extra_variants(new_product_id, new_variant_id):
                    logging.error(f"Variant cleanup failed for product {new_product_id}, skipping")
                    continue
                set_inventory_to_one(new_variant_id)

                tags = [t for t in (original_details["tags"] + tag_to_add_str.split(",")) if t]

                product_updated = False
                variant_updated = False
                for attempt in range(7):
                    if not product_updated:
                        if update_product_details(new_product_id, tags, notes_to_append):
                            product_updated = True
                        else:
                            time.sleep(5)
                            continue
                    if not variant_updated:
                        if update_variant_details(new_variant_id, new_price, str(original_price), new_sku, new_product_id):
                            variant_updated = True
                        else:
                            time.sleep(5)
                            continue
                    break
                if product_updated and variant_updated:
                    logging.info(f"Successfully updated product: {new_product_id}")

                    if "-K" in new_sku:
                        logging.info(f"Detected '-K' in {new_sku} => Writing to single_item_kits.csv")
                        write_kit_csv(
                            kit_sku=new_sku,
                            sku_code=new_sku,
                            line_item_name=new_title,
                            kit_title=new_title
                        )
                else:
                    logging.error(f"Failed to update product {new_product_id} after retries.")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error processing product {product_id}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Duplicate products as open box listings using Shopify GraphQL API."
    )
    parser.add_argument(
        "csv_file", help="Path to the CSV file containing product information."
    )
    args = parser.parse_args()
    process_products_from_csv(args.csv_file)
