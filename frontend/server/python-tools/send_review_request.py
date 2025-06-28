#!/usr/bin/env python3
"""
Send Yotpo review request emails via CLI

This tool allows you to send review request emails through Yotpo's API
without needing to log into the Yotpo dashboard.

Usage:
    python send_review_request.py --recipient "John Doe <john@example.com>" --product "product-handle" [options]
    python send_review_request.py --csv recipients.csv --product "product-handle" [options]

Environment variables required:
    YOTPO_APP_KEY: Your Yotpo app key (from account settings)
    YOTPO_API_SECRET: Your Yotpo API secret
    YOTPO_ACCOUNT_EMAIL_ID: Your account email ID (default: 140510)
"""

import os
import sys
import json
import argparse
import requests
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import re


class YotpoReviewRequester:
    """Handle Yotpo review request email operations"""
    
    def __init__(self):
        self.app_key = os.environ.get('YOTPO_APP_KEY')
        self.api_secret = os.environ.get('YOTPO_API_SECRET')
        self.account_email_id = os.environ.get('YOTPO_ACCOUNT_EMAIL_ID', '140510')
        self.base_url = "https://api-write.yotpo.com"
        self.utoken = None
        
        if not all([self.app_key, self.api_secret]):
            raise ValueError(
                "Please set YOTPO_APP_KEY and YOTPO_API_SECRET environment variables"
            )
    
    def authenticate(self) -> str:
        """Generate utoken for Yotpo API authentication"""
        auth_url = "https://api.yotpo.com/oauth/token"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.app_key,
            "client_secret": self.api_secret
        }
        
        try:
            response = requests.post(auth_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            self.utoken = data.get('access_token')
            
            if not self.utoken:
                raise ValueError("Failed to obtain utoken")
            
            return self.utoken
            
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            sys.exit(1)
    
    def parse_recipient(self, recipient_string: str) -> Tuple[str, str]:
        """Parse recipient string into name and email"""
        # Check if format is "Name <email@domain.com>"
        match = re.match(r'^(.+?)\s*<(.+?)>$', recipient_string.strip())
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # Otherwise assume it's just an email
        email = recipient_string.strip()
        # Extract name from email (before @ symbol)
        name = email.split('@')[0].replace('.', ' ').title()
        return name, email
    
    def upload_mailing_list(self, recipients: List[Dict[str, str]], product_id: str) -> Optional[str]:
        """
        Upload mailing list for review requests
        
        Args:
            recipients: List of dicts with 'name' and 'email' keys
            product_id: Product ID
            
        Returns:
            File name if successful, None otherwise
        """
        if not self.utoken:
            self.authenticate()
        
        # Create CSV content
        csv_lines = ["Email,Name,Product ID"]
        for recipient in recipients:
            csv_lines.append(f"{recipient['email']},{recipient['name']},{product_id}")
        
        csv_content = "\n".join(csv_lines)
        
        url = f"{self.base_url}/apps/{self.app_key}/account_emails/{self.account_email_id}/upload_mailing_list"
        params = {"utoken": self.utoken}
        
        payload = {
            "file": csv_content
        }
        
        try:
            response = requests.post(url, params=params, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status', {}).get('code') == 200:
                response_data = data.get('response', {}).get('response', {})
                file_path = response_data.get('file_path', '')
                
                # Extract just the filename from the path
                file_name = file_path.split('/')[-1] if file_path else None
                
                print(f"Mailing list uploaded successfully:")
                print(f"  Valid emails: {response_data.get('valid_email_count', 0)}")
                print(f"  Rejected emails: {response_data.get('rejected_email_count', 0)}")
                
                return file_name
            else:
                print(f"Upload failed: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to upload mailing list: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None
    
    def send_burst_email(self, file_name: str, activate_spam_filter: bool = False) -> bool:
        """
        Send the review request emails
        
        Args:
            file_name: The filename returned from upload_mailing_list
            activate_spam_filter: Whether to apply spam limitations
            
        Returns:
            True if successful, False otherwise
        """
        if not self.utoken:
            self.authenticate()
        
        url = f"{self.base_url}/apps/{self.app_key}/account_emails/{self.account_email_id}/send_burst_email"
        params = {"utoken": self.utoken}
        
        payload = {
            "activate_spam_limitations": "1" if activate_spam_filter else "0",
            "file_name": file_name
        }
        
        try:
            response = requests.post(url, params=params, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status', {}).get('code') == 200:
                response_data = data.get('response', {}).get('response', {})
                if response_data.get('sent'):
                    return True
                else:
                    print(f"Send failed: {response_data.get('error')}")
                    return False
            else:
                print(f"Send failed: {data}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to send emails: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return False
    
    def send_review_requests(self, recipients: List[Dict[str, str]], 
                           product_id: str, activate_spam_filter: bool = False) -> Dict:
        """
        Send review requests to multiple recipients
        
        Args:
            recipients: List of dicts with 'name' and 'email' keys
            product_id: Product ID
            activate_spam_filter: Whether to apply spam limitations
            
        Returns:
            Dict with success status and details
        """
        # Step 1: Upload mailing list
        print("Uploading mailing list...")
        file_name = self.upload_mailing_list(recipients, product_id)
        
        if not file_name:
            return {
                "success": False,
                "error": "Failed to upload mailing list"
            }
        
        # Step 2: Send emails
        print(f"\nSending review requests...")
        success = self.send_burst_email(file_name, activate_spam_filter)
        
        if success:
            return {
                "success": True,
                "message": f"Review requests sent successfully to {len(recipients)} recipients"
            }
        else:
            return {
                "success": False,
                "error": "Failed to send review requests"
            }
    
    def get_product_info(self, identifier: str) -> Tuple[str, str]:
        """
        Get product information from Shopify
        This is a placeholder - in practice, you might want to query Shopify API
        """
        # For now, return the identifier as both ID and name
        # You can enhance this to query actual product data
        return identifier, identifier


def main():
    parser = argparse.ArgumentParser(
        description="Send Yotpo review request emails via CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Single recipient
    python send_review_request.py --recipient "John Doe <john@example.com>" --product "5431060993"
    
    # Multiple recipients from CSV
    python send_review_request.py --csv recipients.csv --product "5431060993"
    
    # With spam filter activated
    python send_review_request.py --recipient "jane@example.com" --product "5431060993" --spam-filter
    
CSV Format:
    name,email
    John Doe,john@example.com
    Jane Smith,jane@example.com
    
Note: Product ID should be the Yotpo product ID, not SKU or handle.
        """
    )
    
    parser.add_argument(
        '--recipient', '-r',
        help='Single recipient in format "Name <email>" or just "email"'
    )
    
    parser.add_argument(
        '--csv', '-c',
        help='CSV file with recipients (columns: name, email)'
    )
    
    parser.add_argument(
        '--product', '-p',
        required=True,
        help='Yotpo Product ID (numeric ID)'
    )
    
    parser.add_argument(
        '--spam-filter', '-s',
        action='store_true',
        help='Apply spam limitations (max 5 emails per 30 days, etc.)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be done without actually sending'
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.recipient and not args.csv:
        parser.error("Either --recipient or --csv must be provided")
    
    if args.recipient and args.csv:
        parser.error("Cannot use both --recipient and --csv")
    
    # Initialize Yotpo client
    try:
        client = YotpoReviewRequester()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Get product info
    product_id = args.product
    
    # Prepare recipients list
    recipients = []
    
    if args.recipient:
        name, email = client.parse_recipient(args.recipient)
        recipients.append({"name": name, "email": email})
    
    elif args.csv:
        try:
            with open(args.csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'email' in row:
                        recipients.append({
                            "name": row.get('name', ''),
                            "email": row['email']
                        })
        except FileNotFoundError:
            print(f"Error: CSV file '{args.csv}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading CSV: {e}")
            sys.exit(1)
    
    if not recipients:
        print("Error: No valid recipients found")
        sys.exit(1)
    
    # Summary
    print(f"\nReview Request Summary:")
    print(f"Product ID: {product_id}")
    print(f"Recipients: {len(recipients)}")
    print(f"Spam Filter: {'ON' if args.spam_filter else 'OFF'}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    
    if args.dry_run:
        print("Recipients that would receive review requests:")
        for r in recipients:
            print(f"  - {r['name']} <{r['email']}>")
        return
    
    # Send review requests
    print("Authenticating with Yotpo...")
    client.authenticate()
    
    print("\nProcessing review requests...")
    result = client.send_review_requests(
        recipients=recipients,
        product_id=product_id,
        activate_spam_filter=args.spam_filter
    )
    
    # Summary
    if result.get('success'):
        print(f"\n✓ {result.get('message')}")
        sys.exit(0)
    else:
        print(f"\n✗ Error: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()