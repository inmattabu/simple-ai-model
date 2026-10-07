pipeline {
    agent any

    parameters {
        string(
            name: 'REPOSITORY_URL',
            defaultValue: 'https://github.com/inmattabu/simple-ai-model/',
            description: 'Repository URL to deploy'
        )
        string(
            name: 'BRANCH_NAME',
            defaultValue: 'main',
            description: 'Git branch to deploy'
        )
        string(
            name: 'SITE_PORT',
            defaultValue: '8009',
            description: 'Public site port'
        )
        string(
            name: 'CHATBOT_PORT',
            defaultValue: '9009',
            description: 'FastAPI chatbot port'
        )
    }

    environment {
        APP_DIR = '/home/isaac/app/dist/simple-ai-model'
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
                    python3 -m compileall .
                    python3 - <<'PY'
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

                        pkill -f "python3.*app.py" || true
                        nohup env $(grep -v '^#' .env | xargs) python3 app.py > chatbot.log 2>&1 &
                        sleep 5
                        curl -fsS "http://127.0.0.1:${CHATBOT_PORT}/health"
                    '''
                }
            }
        }
    }
}
