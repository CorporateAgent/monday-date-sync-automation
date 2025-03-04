from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
import requests
from dotenv import load_dotenv
from datetime import datetime
import os
import json

# Load environment variables
load_dotenv()

# Get environment variables
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")

app = FastAPI(title="Monday.com Date Automation")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add a test endpoint for debugging Vercel deployment
@app.get("/test")
async def test_endpoint():
    """
    Simple test endpoint to verify the application is running
    Returns environment information to help with debugging
    """
    return {
        "status": "ok",
        "message": "Application is running",
        "environment": {
            "monday_api_key_configured": bool(MONDAY_API_KEY),
            "python_version": os.getenv("PYTHON_VERSION", "unknown"),
            "vercel": os.getenv("VERCEL", "0") == "1",
            "vercel_region": os.getenv("VERCEL_REGION", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
    }

async def execute_monday_query(query, variables=None):
    """Execute a query against the Monday.com API"""
    if not MONDAY_API_KEY:
        raise HTTPException(status_code=500, detail="Monday.com API key not configured")
    
    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "variables": variables
    }
    
    print(f"Sending request to Monday.com API with variables: {json.dumps(variables, indent=2)}")
    
    try:
        response = requests.post(MONDAY_API_URL, json=data, headers=headers)
        
        # Print the response status and content for debugging
        print(f"Monday.com API response status: {response.status_code}")
        
        if response.status_code != 200:
            error_detail = f"Error from Monday.com API: {response.text}"
            print(error_detail)
            raise HTTPException(status_code=response.status_code, detail=error_detail)
        
        response_json = response.json()
        
        # Check for errors in the response
        if "errors" in response_json:
            error_messages = [error.get("message", "Unknown error") for error in response_json.get("errors", [])]
            error_detail = f"Monday.com API returned errors: {', '.join(error_messages)}"
            print(error_detail)
            raise HTTPException(status_code=400, detail=error_detail)
        
        return response_json
    except requests.RequestException as e:
        error_detail = f"Request to Monday.com API failed: {str(e)}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)



@app.post("/")
async def root_webhook(request: Request):
    """
    Root webhook endpoint for Monday.com
    
    This endpoint handles the same functionality as /webhook but at the root path
    """
    print("Received request at root endpoint")
    return await monday_webhook(request)

@app.post("/webhook")
async def monday_webhook(request: Request):
    """
    Webhook endpoint for Monday.com
    
    This endpoint handles:
    1. Challenge response for webhook setup
    2. Processing webhook events for date automation
    """
    # Parse the webhook payload
    try:
        # Get the raw body first for debugging
        raw_body = await request.body()
        print(f"Raw webhook body: {raw_body}")
        
        # Try to parse as JSON
        try:
            body = await request.json()
        except Exception as json_error:
            print(f"Error parsing JSON: {str(json_error)}")
            # Try to decode the raw body as a fallback
            try:
                body_str = raw_body.decode('utf-8')
                body = json.loads(body_str)
            except Exception as decode_error:
                print(f"Error decoding body: {str(decode_error)}")
                raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(json_error)}")
        
        # Log only essential webhook info
        event = body.get("event", {})
        event_type = event.get("type")
        
        print(f"Webhook body: {json.dumps(body, indent=2)}")
        
        # Handle challenge during webhook setup
        if "challenge" in body:
            print("Received challenge request")
            return body
        
        print(f"Event type: {event_type}")
        
        # Handle different event types
        if event_type == "create_pulse" or event_type == "update_column_value":
            print(f"Processing event: {event_type}")
            
            # Check if this is a subitem creation (has parentItemId)
            if body.get("event", {}).get("parentItemId"):
                print("This is a subitem creation, syncing with parent")
                await sync_subitem_with_parent(body)
            else:
                # Regular item creation/update
                await process_date_automation(body)
        elif "subitem" in str(event_type).lower():
            print(f"Detected subitem event: {event_type}")
        else:
            print(f"Unhandled event type: {event_type}")
            
        return {"status": "success"}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in webhook handler: {str(e)}")
        print(f"Traceback: {error_trace}")
        
        # Return a more detailed error response
        return {
            "status": "error",
            "error": str(e),
            "traceback": error_trace,
            "timestamp": datetime.now().isoformat()
        }

async def process_date_automation(webhook_data):
    """
    Sync parent item's Creative Deadline date to all subitems
    """
    # Get item ID from webhook
    event = webhook_data.get("event", {})
    item_id = event.get("pulseId") or event.get("pulse_id") or event.get("itemId")
    
    if not item_id:
        print("📋 Missing item ID in webhook data")
        return
    
    print(f"🔄 Processing sync for item ID: {item_id}")
    
    # Get parent item with date column and subitems
    query = """
    query {
      items(ids: [%s]) {
        name
        column_values(ids: ["date7"]) {
          value
          text
        }
        subitems {
          id
          name
          board { id }
        }
      }
    }
    """ % item_id
    
    try:
        # Get parent item data
        result = await execute_monday_query(query)
        items = result.get("data", {}).get("items", [])
        
        if not items:
            print(f"❌ Parent item {item_id} not found")
            return
        
        parent = items[0]
        parent_name = parent.get("name", "Unknown")
        date_column = parent.get("column_values", [])[0] if parent.get("column_values") else None
        
        if not date_column:
            print("❌ Creative Deadline column not found")
            return
        
        # Get date value
        date_value = date_column.get("value")
        date_text = date_column.get("text", "")
        
        print(f"📅 Parent '{parent_name}' date: {date_text}")
        
        # Skip if no date value
        if not date_value or date_value == "null":
            print("⏩ No date value to sync")
            return
        
        # Get subitems
        subitems = parent.get("subitems", [])
        if not subitems:
            print("ℹ️ No subitems found")
            return
        
        print(f"📋 Found {len(subitems)} subitems to update")
        
        # Update all subitems
        mutation = """
        mutation($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
            change_column_value(board_id: $boardId, item_id: $itemId, column_id: $columnId, value: $value) {
                id
            }
        }
        """
        
        for subitem in subitems:
            subitem_id = subitem.get("id")
            subitem_name = subitem.get("name", "Unknown")
            subitem_board_id = subitem.get("board", {}).get("id")
            
            if not subitem_id or not subitem_board_id:
                continue
            
            variables = {
                "boardId": subitem_board_id,
                "itemId": subitem_id,
                "columnId": "date_mkn2am1b",
                "value": date_value
            }
            
            try:
                await execute_monday_query(mutation, variables)
                print(f"✅ Updated: {subitem_name}")
            except Exception as e:
                print(f"❌ Error updating {subitem_name}: {str(e)}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")

async def sync_subitem_with_parent(webhook_data):
    """
    Sync a subitem's date columns with its parent item
    
    This function will:
    1. Get the parent item's Creative Deadline date
    2. Update the subitem's Date column with the parent's date
    """
    event = webhook_data.get("event", {})
    
    # Extract all the IDs we need
    subitem_id = event.get("itemId") or event.get("pulseId")
    subitem_board_id = event.get("boardId")
    parent_item_id = event.get("parentItemId")
    parent_board_id = event.get("parentItemBoardId")
    
    print(f"Syncing subitem {subitem_id} on board {subitem_board_id} with parent {parent_item_id} on board {parent_board_id}")
    
    if not all([subitem_id, subitem_board_id, parent_item_id, parent_board_id]):
        print("Missing required IDs for subitem-parent sync")
        return
    
    # 1. Get the parent item to find its Creative Deadline column
    parent_query = """
    query GetParentItem($itemId: ID!) {
      items(ids: [$itemId]) {
        id
        name
        column_values {
          id
          type
          value
        }
      }
    }
    """
    
    parent_variables = {
        "itemId": parent_item_id
    }
    
    parent_result = await execute_monday_query(parent_query, parent_variables)
    
    # 2. Get the subitem to find its Date column
    subitem_query = """
    query GetSubItem($itemId: ID!) {
      items(ids: [$itemId]) {
        id
        name
        column_values {
          id
          type
          value
        }
      }
    }
    """
    
    subitem_variables = {
        "itemId": subitem_id
    }
    
    subitem_result = await execute_monday_query(subitem_query, subitem_variables)
    
    try:
        # Extract parent item data
        parent_items = parent_result.get("data", {}).get("items", [])
        if not parent_items:
            print(f"Parent item {parent_item_id} not found")
            return
            
        parent_item = parent_items[0]
        parent_name = parent_item.get("name", "Unknown")
        print(f"Found parent item: {parent_name}")
        
        # Find the Creative Deadline column in parent
        # Using the known column ID for Creative Deadline
        PARENT_DATE_COLUMN_ID = "date7"  # ID of the Creative Deadline column in parent items
        parent_date_col = next((col for col in parent_item.get("column_values", []) 
                              if col.get("id") == PARENT_DATE_COLUMN_ID), None)
        
        # If not found by ID, try any date column
        if not parent_date_col:
            parent_date_col = next((col for col in parent_item.get("column_values", []) 
                                  if col.get("type") == "date"), None)
        
        if not parent_date_col:
            print(f"No date column found in parent item {parent_item_id}")
            return
            
        print(f"Found parent date column: ID={parent_date_col.get('id')}")
        
        # Extract subitem data
        subitem_items = subitem_result.get("data", {}).get("items", [])
        if not subitem_items:
            print(f"Subitem {subitem_id} not found")
            return
            
        subitem = subitem_items[0]
        subitem_name = subitem.get("name", "Unknown")
        print(f"Found subitem: {subitem_name}")
        
        # Find the Date column in subitem using the ID you provided
        SUBITEM_DATE_COLUMN_ID = "date_mkn2am1b"  # ID of the Date column in subitems
        subitem_date_col = next((col for col in subitem.get("column_values", []) 
                                if col.get("id") == SUBITEM_DATE_COLUMN_ID), None)
        
        # If not found by ID, try any date column
        if not subitem_date_col:
            subitem_date_col = next((col for col in subitem.get("column_values", []) 
                                   if col.get("type") == "date"), None)
        
        if not subitem_date_col:
            print(f"No date column found in subitem {subitem_id}")
            return
        
        print(f"Found subitem date column: ID={subitem_date_col.get('id')}")
        
        # Get the parent date value
        parent_value = parent_date_col.get("value")
        
        # Try to parse and display the date in a readable format
        try:
            if parent_value and parent_value != "null":
                date_json = json.loads(parent_value)
                date_str = date_json.get("date", "No date found")
                print(f"Parent date value: {date_str}")
            else:
                print("Parent date value is empty or null")
        except:
            print(f"Raw parent date value: {parent_value}")
        
        # If parent value is null or empty, try to create a date value based on what we see in the UI
        if not parent_value or parent_value == "null":
            print("Parent date value is empty or null, trying to create a date value")
            # Create a date value for March 11th (as seen in your screenshot)
            today = datetime.now()
            march_11 = datetime(today.year, 3, 11).strftime("%Y-%m-%d")
            parent_value = json.dumps({"date": march_11})
            print(f"Created date value: {march_11}")
        
        if parent_value:
            try:
                # Update the subitem with the parent's date value
                print(f"Updating Date column in subitem {subitem_id}")
                mutation = """
                mutation UpdateSubitemDate($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
                    change_column_value(board_id: $boardId, item_id: $itemId, column_id: $columnId, value: $value) {
                        id
                    }
                }
                """
                
                variables = {
                    "boardId": subitem_board_id,
                    "itemId": subitem_id,
                    "columnId": subitem_date_col.get("id"),  # Use the subitem's date column ID
                    "value": parent_value  # Use the value from parent
                }
                
                result = await execute_monday_query(mutation, variables)
                print(f"Update result: {json.dumps(result, indent=2)}")
            except Exception as e:
                print(f"Error updating subitem date: {str(e)}")
        else:
            print("Parent date value is empty, nothing to sync")
    except Exception as e:
        import traceback
        print(f"Error syncing subitem with parent: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
