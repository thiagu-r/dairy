#!/usr/bin/env python3
"""
Test script for the Dairy Sales Sync APIs.
This script tests all the individual sync endpoints as well as the combined sync endpoint.
"""

import argparse
import json
import os
import requests
import sys
from datetime import datetime

# Define the base URL and endpoints
BASE_URL = "http://localhost:8000/apiapp"
ENDPOINTS = {
    "combined": "/sync/",
    "delivery_orders": "/sync/delivery-orders/",
    "broken_orders": "/sync/broken-orders/",
    "return_orders": "/sync/return-orders/",
    "public_sales": "/sync/public-sales/",
    "expenses": "/sync/expenses/",
    "denominations": "/sync/denominations/",
}

# Define the payload files
PAYLOAD_DIR = "sample_payloads"
PAYLOAD_FILES = {
    "combined": "combined_sync.json",
    "delivery_orders": "delivery_order_sync.json",
    "broken_orders": "broken_order_sync.json",
    "return_orders": "return_order_sync.json",
    "public_sales": "public_sale_sync.json",
    "expenses": "expense_sync.json",
    "denominations": "denomination_sync.json",
}


def get_token(username, password):
    """Get a JWT token for authentication."""
    url = f"{BASE_URL}/token/"
    payload = {
        "username": username,
        "password": password
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("access")
    except requests.exceptions.RequestException as e:
        print(f"Error getting token: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        sys.exit(1)


def test_endpoint(endpoint_name, token, base_url=BASE_URL):
    """Test a specific endpoint with its corresponding payload."""
    endpoint = ENDPOINTS.get(endpoint_name)
    payload_file = os.path.join(PAYLOAD_DIR, PAYLOAD_FILES.get(endpoint_name))
    
    if not endpoint or not os.path.exists(payload_file):
        print(f"Invalid endpoint or payload file not found: {endpoint_name}")
        return False
    
    url = f"{base_url}{endpoint}"
    
    # Load the payload
    try:
        with open(payload_file, "r") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"Error loading payload file {payload_file}: {e}")
        return False
    
    # Set up the headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Send the request
    try:
        print(f"\n=== Testing {endpoint_name.upper()} endpoint ===")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status code: {response.status_code}")
        print("Response headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print("\nResponse body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
            
            # Check if the response indicates success
            if response.status_code == 200 and response_json.get("status") == "success":
                print(f"\n✅ {endpoint_name.upper()} endpoint test PASSED")
                return True
            else:
                print(f"\n❌ {endpoint_name.upper()} endpoint test FAILED")
                return False
        except json.JSONDecodeError:
            print(response.text)
            print(f"\n❌ {endpoint_name.upper()} endpoint test FAILED - Invalid JSON response")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error testing {endpoint_name} endpoint: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        print(f"\n❌ {endpoint_name.upper()} endpoint test FAILED")
        return False


def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Test the Dairy Sales Sync APIs")
    parser.add_argument("--username", "-u", required=True, help="Username for authentication")
    parser.add_argument("--password", "-p", required=True, help="Password for authentication")
    parser.add_argument("--base-url", "-b", default=BASE_URL, help=f"Base URL for the API (default: {BASE_URL})")
    parser.add_argument("--endpoint", "-e", choices=list(ENDPOINTS.keys()), help="Specific endpoint to test (default: all)")
    
    args = parser.parse_args()
    
    # Get the token
    print(f"Getting token for user {args.username}...")
    token = get_token(args.username, args.password)
    if not token:
        print("Failed to get token. Exiting.")
        sys.exit(1)
    print(f"Token obtained: {token[:10]}...")
    
    # Test the endpoints
    if args.endpoint:
        # Test a specific endpoint
        success = test_endpoint(args.endpoint, token, args.base_url)
        sys.exit(0 if success else 1)
    else:
        # Test all endpoints
        results = {}
        for endpoint in ENDPOINTS.keys():
            results[endpoint] = test_endpoint(endpoint, token, args.base_url)
        
        # Print summary
        print("\n=== Test Summary ===")
        for endpoint, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{endpoint.upper()}: {status}")
        
        # Exit with appropriate status code
        if all(results.values()):
            print("\nAll tests passed! 🎉")
            sys.exit(0)
        else:
            print("\nSome tests failed. 😢")
            sys.exit(1)


if __name__ == "__main__":
    main()
