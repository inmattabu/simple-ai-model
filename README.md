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

## Manual deployment on the Jenkins server

Use these steps when deploying directly from the Jenkins server at `https://labs2jobs.com:8443`.

### 1) Clone the code onto the server

```bash
sudo mkdir -p /home/isaac/app/dist
cd /home/isaac/app/dist
sudo git clone https://github.com/inmattabu/simple-ai-model.git
cd simple-ai-model
```

### 2) Create the environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Configure runtime environment

Create a `.env` file in the project root and set the required values:

```bash
cat > .env <<'EOF'
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
HOST=0.0.0.0
PORT=9009
EOF
```

> Keep `.env` outside of source control. Jenkins can inject secrets securely via credentials instead of storing them in the repository.

### 4) Start the app on the same server

```bash
nohup python app.py > chatbot.log 2>&1 &
```

The app will be available on:

- http://localhost:9009/
- http://localhost:9009/health
- http://localhost:9009/api/chat

### 5) Confirm the service is healthy

```bash
curl http://localhost:9009/health
```

Example response:

```json
{"status":"ok","service":"simple-chat-bot"}
```

## Automated deployment with Jenkins

The Jenkins pipeline is designed to run from the Jenkins server itself, fetch the repository, validate the code, and deploy it on the same machine.

### Jenkins pipeline behavior

The pipeline accepts these parameters:

- `REPOSITORY_URL` — Git repository URL to check out
- `BRANCH_NAME` — Git branch to build from
- `SITE_PORT` — public site port exposed by nginx or the front end
- `CHATBOT_PORT` — backend FastAPI port

The pipeline runs in three stages:

1. Fetch source from the repository to the Jenkins server
2. Stage and test the project on the server
3. Deploy the application and restart it on the same host

### Jenkinsfile example

Create a `Jenkinsfile` at the project root. The file should be checked into source control and used by Jenkins to deploy the app automatically.

```groovy
pipeline {
    agent any

    parameters {
        string(name: 'REPOSITORY_URL', defaultValue: 'https://github.com/inmattabu/simple-ai-model/', description: 'Repository URL to deploy')
        string(name: 'BRANCH_NAME', defaultValue: 'main', description: 'Git branch to deploy')
        string(name: 'SITE_PORT', defaultValue: '8009', description: 'Public site port')
        string(name: 'CHATBOT_PORT', defaultValue: '9009', description: 'FastAPI chatbot port')
    }

    environment {
        APP_DIR = '/home/isaac/app/dist/simple-ai-model'
        PYTHON_BIN = '/usr/bin/python3'
    }

    stages {
        stage('Fetch Source') {
            steps {
                sh '''
                    set -eux
                    mkdir -p /home/isaac/app/dist
                    if [ -d "$APP_DIR/.git" ]; then
                        cd "$APP_DIR"
                        git fetch --all --tags
                        git checkout "$BRANCH_NAME"
                        git pull --ff-only origin "$BRANCH_NAME"
                    else
                        git clone --branch "$BRANCH_NAME" "$REPOSITORY_URL" "$APP_DIR"
                    fi
                '''
            }
        }

        stage('Stage and Test') {
            steps {
                sh '''
                    set -eux
                    cd "$APP_DIR"
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    python -m compileall .
                    python - <<'PY'
import os
try:
    import app  # noqa: F401
    print('IMPORT_OK')
except Exception as exc:
    print(f'IMPORT_FAILED: {exc}')
    raise
PY
                '''
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([string(credentialsId: 'openai_api_key', variable: 'OPENAI_API_KEY')]) {
                    sh '''
                        set -eux
                        cd "$APP_DIR"
                        cat > .env <<EOF
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
HOST=0.0.0.0
PORT=${CHATBOT_PORT}
EOF

                        pkill -f "python.*app.py" || true
                        nohup env $(cat .env | xargs) python app.py > chatbot.log 2>&1 &
                        sleep 5
                        curl -fsS "http://127.0.0.1:${CHATBOT_PORT}/health"
                    '''
                }
            }
        }
    }
}
```

### Jenkins configuration notes

- Add the repository URL and branch as `Build with Parameters` values in Jenkins.
- Configure a Jenkins credential named `openai_api_key` for the OpenAI API key.
- Ensure the Jenkins service account has permission to write to `/home/isaac/app/dist/simple-ai-model`.
- If nginx is in front of the app, update the site configuration to point to the selected `SITE_PORT` and `CHATBOT_PORT`.

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

Example Prompt2:
```
isaac@labs2jobs$ curl -X POST http://localhost:9009/api/chat   -H "Content-Type: application/json"   -d '{"message":"explain briefly about MAI-Code-1.1-Flash"}'
```

Example Prompt2 Response:
```
{"reply":"MAI-Code-1.1-Flash is a software framework developed for managing and executing code in embedded systems, particularly those that require efficient memory usage and fast execution. It is part of the MAI (Microcontroller Application Interface) project, which aims to streamline the development process for microcontroller applications.\n\nThe \"Flash\" component typically refers to the use of flash memory for storing code and data, allowing for quicker access and updates compared to traditional storage methods. MAI-Code-1.1-Flash is designed to facilitate the development of applications by providing a structured approach to coding, debugging, and deploying firmware on microcontrollers.\n\nThis framework may include features such as modular design, support for various microcontroller architectures, and tools for testing and optimization, making it a valuable resource for developers working on embedded systems."}
isaac@labs2jobs$
````

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
