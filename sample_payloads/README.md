# Dairy Sales API - Sync Endpoints

This directory contains sample payloads for the individual sync endpoints. These endpoints allow you to sync specific types of data from the mobile app to the server.

## Available Endpoints

1. **Combined Sync API** (Original)
   - URL: `/apiapp/sync/`
   - Method: POST
   - Description: Syncs all types of data in a single request
   - Payload: See `combined_sync.json`

2. **Delivery Order Sync API**
   - URL: `/apiapp/sync/delivery-orders/`
   - Method: POST
   - Description: Syncs only delivery orders
   - Payload: See `delivery_order_sync.json`

3. **Broken Order Sync API**
   - URL: `/apiapp/sync/broken-orders/`
   - Method: POST
   - Description: Syncs only broken orders
   - Payload: See `broken_order_sync.json`

4. **Return Order Sync API**
   - URL: `/apiapp/sync/return-orders/`
   - Method: POST
   - Description: Syncs only return orders
   - Payload: See `return_order_sync.json`

5. **Public Sale Sync API**
   - URL: `/apiapp/sync/public-sales/`
   - Method: POST
   - Description: Syncs only public sales
   - Payload: See `public_sale_sync.json`

6. **Expense Sync API**
   - URL: `/apiapp/sync/expenses/`
   - Method: POST
   - Description: Syncs only delivery expenses
   - Payload: See `expense_sync.json`

7. **Denomination Sync API**
   - URL: `/apiapp/sync/denominations/`
   - Method: POST
   - Description: Syncs only cash denominations
   - Payload: See `denomination_sync.json`

## Authentication

All endpoints require authentication using a JWT token. Include the token in the Authorization header:

```
Authorization: Bearer <your_token>
```

## Request Format

The request body should be a JSON array containing one or more objects of the appropriate type. For example, to sync delivery orders:

```json
[
  {
    "id": null,
    "order_number": "DO-20250421-0001",
    "delivery_date": "2025-04-21",
    "route": 1,
    "seller": 1,
    "items": [
      {
        "product": 3,
        "ordered_quantity": 20.00,
        "delivered_quantity": 20.00
      }
    ]
  }
]
```

Alternatively, you can wrap the array in a `data` object:

```json
{
  "data": [
    {
      "id": null,
      "order_number": "DO-20250421-0001",
      "delivery_date": "2025-04-21",
      "route": 1,
      "seller": 1,
      "items": [
        {
          "product": 3,
          "ordered_quantity": 20.00,
          "delivered_quantity": 20.00
        }
      ]
    }
  ]
}
```

## Response Format

The response will be a JSON object with the following structure:

```json
{
  "status": "success",
  "message": "Processed N items",
  "results": [
    {
      "id": 123,
      "local_id": "mobile-id-123456789",
      "status": "created",
      "message": "Item created successfully"
    }
  ]
}
```

## Error Handling

If there are validation errors, the response will include details about the errors:

```json
{
  "status": "success",
  "message": "Processed N items",
  "results": [
    {
      "local_id": "mobile-id-123456789",
      "status": "error",
      "message": "Validation error",
      "errors": {
        "field_name": ["Error message"]
      }
    }
  ]
}
```

If there is a server error, the response will have a 500 status code and include an error message:

```json
{
  "status": "error",
  "message": "Error message"
}
```

## Testing the APIs

You can test the APIs using curl or any API testing tool. For example:

```bash
curl -X POST \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d @delivery_order_sync.json \
  http://your-server/apiapp/sync/delivery-orders/
```

Or using Python:

```python
import requests
import json

# Load the payload from a file
with open('delivery_order_sync.json', 'r') as f:
    payload = json.load(f)

# Set up the headers
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your_token_here'
}

# Send the request
response = requests.post(
    'http://your-server/apiapp/sync/delivery-orders/',
    json=payload,
    headers=headers
)

# Print the response
print(response.status_code)
print(json.dumps(response.json(), indent=2))
```
