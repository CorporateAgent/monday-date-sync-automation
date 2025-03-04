# Monday.com Date Sync Automation

A FastAPI application that provides a webhook for Monday.com to automate date synchronization between parent items and subitems. This application uses Monday.com's GraphQL API to automatically sync date columns from parent items to their subitems.

## Features

- Webhook endpoint for Monday.com integration
- Automatic date synchronization from parent items to subitems
- Support for both item creation and column value updates
- Detailed logging for troubleshooting
- Ready for deployment on Vercel or local development with ngrok

## How It Works

This application implements two main automation workflows:

1. **Parent-to-Subitems Date Sync**: When a parent item's "Creative Deadline" date is updated, the application automatically updates the "Date" column in all subitems.

2. **New Subitem Date Sync**: When a new subitem is created, it automatically inherits the "Creative Deadline" date from its parent item.

## Monday.com GraphQL Integration

This application leverages Monday.com's GraphQL API to query and mutate data. Here's how the GraphQL integration works:

### GraphQL Queries

The application uses the following GraphQL queries to fetch data from Monday.com:

1. **Fetching Parent Item with Subitems**:
```graphql
query {
  items(ids: [ITEM_ID]) {
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
```

This query retrieves:
- The parent item's name
- The "Creative Deadline" column value (with ID "date7")
- All subitems associated with the parent, including their IDs, names, and board IDs

2. **Fetching Item Details**:
```graphql
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
```

This query retrieves all column values for a specific item, which is used to find date columns.

### GraphQL Mutations

The application uses the following GraphQL mutation to update date values:

```graphql
mutation($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
  change_column_value(board_id: $boardId, item_id: $itemId, column_id: $columnId, value: $value) {
    id
  }
}
```

This mutation updates a specific column value for an item on a board.

### Date Value Format

Monday.com stores date values in a specific JSON format:

```json
{
  "date": "YYYY-MM-DD"
}
```

For example, to set a date to March 11, 2023:
```json
{
  "date": "2023-03-11"
}
```

## Setup

### Prerequisites

- Python 3.8+
- Monday.com account with API access
- Vercel account (for deployment) or ngrok (for local testing)

### Local Development

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file and add your Monday.com API key:
   ```
   MONDAY_API_KEY=your_monday_api_key_here
   ```
5. Run the development server:
   ```
   python main.py
   ```
   or
   ```
   uvicorn main:app --reload
   ```
6. Use ngrok to expose your local server:
   ```
   ngrok http 8000
   ```

### Deploying to Vercel

1. Fork or clone this repository to your GitHub account
2. Connect your GitHub repository to Vercel
3. Set the environment variable `MONDAY_API_KEY` in the Vercel dashboard
4. Deploy the application

## Setting up the Monday.com Webhook

1. Go to your Monday.com account
2. Navigate to a board → Integrations → API → Webhooks
3. Create a new webhook with the following settings:
   - URL: Your deployed Vercel URL + `/webhook` (e.g., `https://your-app.vercel.app/webhook`)
   - Event: Select "Create Item" and "Update Column Value"
   - Board: Select the board you want to automate
4. Save the webhook

## Testing the Integration

The repository includes a `test.html` file that provides a simple interface for testing your webhook endpoints. This HTML file allows you to:

1. Test the root endpoint (GET /)
2. Test the info endpoint (GET /test)
3. Send test payloads to the webhook endpoint (POST /webhook)

To use the test HTML:
1. Download the `test.html` file to your local machine
2. Open it in a text editor
3. Update the `baseUrl` variable to your actual deployment URL
4. Open the HTML file in a browser and use it to test your endpoints

## Customizing the Integration

### Column IDs

The application uses specific column IDs to identify date columns:

- `date7`: The "Creative Deadline" column in parent items
- `date_mkn2am1b`: The "Date" column in subitems

If your Monday.com board uses different column IDs, you'll need to update these values in the code:

1. For parent items: Update `PARENT_DATE_COLUMN_ID` in the `sync_subitem_with_parent` function
2. For subitems: Update the `columnId` value in the `process_date_automation` function

### Adding Support for Additional Columns

To sync additional columns between parent items and subitems:

1. Modify the GraphQL queries to fetch the additional columns
2. Add logic to the `process_date_automation` or `sync_subitem_with_parent` functions to handle the additional columns
3. Use the same mutation pattern to update the columns in subitems

## Troubleshooting

### Vercel vs. ngrok

If your application works with ngrok but not with Vercel, check:

1. **Environment Variables**: Ensure your `MONDAY_API_KEY` is set in the Vercel dashboard
2. **Vercel Configuration**: Verify your `vercel.json` file has the correct routes and methods
3. **Logs**: Check the Vercel logs for any errors
4. **Timeouts**: Vercel has a 10-second timeout for serverless functions on the free tier

### Testing Endpoints

Use the `/test` endpoint to verify your application is running correctly and environment variables are set.

## API Documentation

When running locally, visit `http://localhost:8000/docs` to see the Swagger UI documentation for the API.

## License

MIT 
