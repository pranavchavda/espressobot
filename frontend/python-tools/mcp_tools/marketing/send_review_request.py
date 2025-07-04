"""
Native MCP implementation for sending Yotpo review requests
"""

import os
import re
import requests
from typing import Dict, Any, List, Optional, Tuple
from ..base import BaseMCPTool

class SendReviewRequestTool(BaseMCPTool):
    """Send review request emails via Yotpo API"""
    
    name = "send_review_request"
    description = "Send Yotpo review request emails to customers"
    context = """
    Sends review request emails through Yotpo's API for iDrinkCoffee.com.
    
    Features:
    - Single or bulk recipient support
    - Product-specific review requests
    - Spam filter option (max 5 emails per 30 days)
    - Name parsing from email addresses
    
    Process:
    1. Uploads recipient list to Yotpo
    2. Triggers email send via burst email API
    3. Tracks valid/rejected emails
    
    Requirements:
    - YOTPO_APP_KEY environment variable
    - YOTPO_API_SECRET environment variable
    - Yotpo Product ID (numeric, not SKU)
    
    Use cases:
    - Post-purchase review requests
    - Follow-up for high-value customers
    - Manual review campaigns
    - Testing review templates
    
    Note: Review requests should be sent 7-14 days after delivery
    for best response rates.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "recipients": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    },
                    "required": ["email"]
                },
                "description": "List of recipients with name and email"
            },
            "recipient": {
                "type": "string",
                "description": "Single recipient (alternative to recipients array)"
            },
            "product_id": {
                "type": "string",
                "description": "Yotpo Product ID (numeric)"
            },
            "activate_spam_filter": {
                "type": "boolean",
                "description": "Apply spam limitations (default: false)"
            }
        },
        "required": ["product_id"]
    }
    
    def __init__(self):
        super().__init__()
        self.app_key = os.environ.get('YOTPO_APP_KEY')
        self.api_secret = os.environ.get('YOTPO_API_SECRET')
        self.account_email_id = os.environ.get('YOTPO_ACCOUNT_EMAIL_ID', '140510')
        self.base_url = "https://api-write.yotpo.com"
        self.utoken = None
    
    async def execute(self, product_id: str, **kwargs) -> Dict[str, Any]:
        """Send review requests"""
        if not self.app_key or not self.api_secret:
            return {
                "success": False,
                "error": "YOTPO_APP_KEY and YOTPO_API_SECRET environment variables required"
            }
        
        try:
            # Parse recipients
            recipients = []
            
            if 'recipients' in kwargs:
                recipients = kwargs['recipients']
            elif 'recipient' in kwargs:
                name, email = self._parse_recipient(kwargs['recipient'])
                recipients = [{"name": name, "email": email}]
            else:
                return {
                    "success": False,
                    "error": "Either 'recipients' array or 'recipient' string required"
                }
            
            activate_spam_filter = kwargs.get('activate_spam_filter', False)
            
            # Authenticate
            auth_result = await self._authenticate()
            if not auth_result['success']:
                return auth_result
            
            # Upload mailing list
            upload_result = await self._upload_mailing_list(recipients, product_id)
            if not upload_result['success']:
                return upload_result
            
            # Send emails
            send_result = await self._send_burst_email(
                upload_result['file_name'],
                activate_spam_filter
            )
            
            if send_result['success']:
                return {
                    "success": True,
                    "message": f"Review requests sent to {len(recipients)} recipients",
                    "details": {
                        "recipients_count": len(recipients),
                        "product_id": product_id,
                        "spam_filter": activate_spam_filter,
                        "valid_emails": upload_result.get('valid_emails', 0),
                        "rejected_emails": upload_result.get('rejected_emails', 0)
                    }
                }
            else:
                return send_result
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_recipient(self, recipient_string: str) -> Tuple[str, str]:
        """Parse recipient string into name and email"""
        # Check if format is "Name <email@domain.com>"
        match = re.match(r'^(.+?)\s*<(.+?)>$', recipient_string.strip())
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # Otherwise assume it's just an email
        email = recipient_string.strip()
        # Extract name from email
        name = email.split('@')[0].replace('.', ' ').title()
        return name, email
    
    async def _authenticate(self) -> Dict[str, Any]:
        """Authenticate with Yotpo API"""
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
                return {
                    "success": False,
                    "error": "Failed to obtain authentication token"
                }
            
            return {"success": True}
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
    
    async def _upload_mailing_list(self, recipients: List[Dict[str, str]], 
                                  product_id: str) -> Dict[str, Any]:
        """Upload mailing list to Yotpo"""
        # Create CSV content
        csv_lines = ["Email,Name,Product ID"]
        for recipient in recipients:
            name = recipient.get('name', '')
            email = recipient['email']
            csv_lines.append(f"{email},{name},{product_id}")
        
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
                
                # Extract filename
                file_name = file_path.split('/')[-1] if file_path else None
                
                return {
                    "success": True,
                    "file_name": file_name,
                    "valid_emails": response_data.get('valid_email_count', 0),
                    "rejected_emails": response_data.get('rejected_email_count', 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"Upload failed: {data}"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to upload mailing list: {str(e)}"
            }
    
    async def _send_burst_email(self, file_name: str, 
                               activate_spam_filter: bool) -> Dict[str, Any]:
        """Send the review request emails"""
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
                    return {"success": True}
                else:
                    return {
                        "success": False,
                        "error": response_data.get('error', 'Unknown send error')
                    }
            else:
                return {
                    "success": False,
                    "error": f"Send failed: {data}"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to send emails: {str(e)}"
            }
    
    async def test(self) -> Dict[str, Any]:
        """Test Yotpo integration"""
        if not self.app_key or not self.api_secret:
            return {
                "status": "failed",
                "error": "YOTPO_APP_KEY and YOTPO_API_SECRET not configured"
            }
        
        # Test authentication
        auth_result = await self._authenticate()
        if auth_result['success']:
            return {
                "status": "passed",
                "message": "Yotpo authentication successful"
            }
        else:
            return {
                "status": "failed",
                "error": auth_result['error']
            }