# Simple Chat Bot

This project creates a simple AI chatbot that runs as a FastAPI service and exposes both:

- A browser-based chat interface
- An API endpoint for curl or other HTTP clients

The application is configured to run internally on port 9009 and is intended to sit behind nginx on port 8009 for the hostname http://labs2jobs.com.

## Features

- FastAPI backend
- OpenAI-compatible chat completions integration
- Simple HTML/JavaScript front end
- Health check endpoint
- nginx reverse proxy example
- Environment-based configuration

## Project structure

- `app.py` – FastAPI application and chat endpoint
- `templates/index.html` – browser UI
- `static/style.css` – UI styles
- `static/app.js` – browser client logic
- `nginx/chatbot.conf` – nginx config for port 8009 -> 9009
- `.env.example` – environment variables template
- `requirements.txt` – Python dependencies

## Requirements

- Python 3.11+
- OpenAI-compatible API key
- nginx (optional for production)

## Environment setup

1. Copy `.env.example` to `.env`.
2. Add your API key.
3. Set the OpenAI-compatible base URL if your service is not the public OpenAI endpoint.

Example:

```bash
cp .env.example .env
```

Then update `.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_SERVICE_ACCOUNT_NAME=ChatBotSvcAccount
HOST=0.0.0.0
PORT=9009
```

> The value `ChatBotSvcAccount` is used as the service account name in the deployment notes. The actual OpenAI API key should be kept in the environment and not committed to source control.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Run locally

```bash
python app.py
```

The app will start on:

- http://localhost:9009/
- http://localhost:9009/health
- http://localhost:9009/api/chat

## Browser usage

Open the home page in a browser:

```text
http://localhost:9009/
```

You can type a message and the app will send it to the chat completion endpoint.

## Curl validation

Send a simple request:

```bash
curl -X POST http://localhost:9009/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```

Example response:

```json
{"reply":"Hello! How can I help you today?"}
```

Health check:

```bash
curl http://localhost:9009/health
```

Example response:

```json
{"status":"ok","service":"simple-chat-bot"}
```

## nginx configuration

The included example file is:

```nginx
server {
    listen 8009;
    server_name labs2jobs.com;

    location / {
        proxy_pass http://127.0.0.1:9009;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Place this in your nginx site config and reload nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

This means:

- external public access: http://labs2jobs.com:8009
- backend service: http://127.0.0.1:9009

## Production notes

- Keep the `.env` file outside the repository or use a secrets manager.
- Ensure the OpenAI API key is valid for the planned service account.
- If you are using an OpenAI-compatible API endpoint instead of the official OpenAI service, set `OPENAI_BASE_URL` accordingly.
- If nginx is already serving the site, confirm that the `listen 8009` port is open and the firewall rules allow it.

## Validation checklist

Use this checklist before going live:

1. Install dependencies.
2. Copy `.env.example` to `.env` and fill in your credentials.
3. Run the app with `python app.py`.
4. Confirm `http://localhost:9009/health` returns `status: ok`.
5. Confirm the browser page loads at `http://localhost:9009/`.
6. Send a curl POST to `/api/chat` and verify a valid reply is returned.
7. Confirm nginx proxies requests on `:8009` to the app on `:9009`.
8. Verify the external URL `http://labs2jobs.com` is routing properly through the nginx site.

## Troubleshooting

### 500 error on chat request

Check that:

- `OPENAI_API_KEY` is set in `.env`
- the key is valid
- `OPENAI_BASE_URL` points to the correct API endpoint

### nginx 502 / 504

Check that the backend app is running on port 9009 and that the proxy configuration points to the correct port and host.

### Port already in use

Stop any running process using port 9009 or change `PORT` in `.env` before restarting the app.

## Security note

The service account API key should never be committed to the repository. Use environment variables and keep `.env` out of source control.
