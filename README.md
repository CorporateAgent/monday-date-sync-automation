# Monday.com Date Automation Webhook

A FastAPI application that provides a webhook for Monday.com to automate date-related tasks. This application automatically updates date columns in Monday.com items based on webhook events.

## Features

- Webhook endpoint for Monday.com integration
- Automatic date updates (e.g., setting due dates to 7 days from creation)
- Signature verification for secure webhook handling
- Ready for deployment on Vercel

## Setup

### Prerequisites

- Python 3.8+
- Monday.com account with API access
- Vercel account (for deployment)

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
4. Create a `.env` file based on `.env.example` and add your Monday.com API credentials:
   ```
   MONDAY_API_KEY=your_monday_api_key_here
   MONDAY_SIGNING_SECRET=your_monday_signing_secret_here
   ```
5. Run the development server:
   ```
   python main.py
   ```
   or
   ```
   uvicorn main:app --reload
   ```

### Deploying to Vercel

1. Install Vercel CLI:
   ```
   npm install -g vercel
   ```
2. Login to Vercel:
   ```
   vercel login
   ```
3. Deploy the application:
   ```
   vercel
   ```
4. Set environment variables in the Vercel dashboard or using the CLI:
   ```
   vercel env add MONDAY_API_KEY
   vercel env add MONDAY_SIGNING_SECRET
   ```

## Setting up the Monday.com Webhook

1. Go to your Monday.com account
2. Navigate to Developers → Webhooks
3. Create a new webhook with the following settings:
   - URL: Your deployed Vercel URL + `/webhook` (e.g., `https://your-app.vercel.app/webhook`)
   - Event: Choose events like "Create Item" or "Update Column Value"
   - Board: Select the board you want to automate
4. Save the webhook

## Customizing Date Automation

The default behavior is to set the first date column to 7 days from the current date. To customize this:

1. Open `main.py`
2. Modify the `process_date_automation` function to implement your specific date automation logic
3. Deploy the updated code

## API Documentation

When running locally, visit `http://localhost:8000/docs` to see the Swagger UI documentation for the API.

## License

MIT 
