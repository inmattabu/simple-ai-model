pipeline {
    agent any

    environment {
        HOST = '0.0.0.0'
        PORT = '9001'
    }

    stages {
        stage('Checkout branch') {
            when {
                branch 'likhitha'
            }
            steps {
                git branch: 'likhitha', url: scm.getUserRemoteConfigs()[0].getUrl()
            }
        }

        stage('Install dependencies') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Prepare environment') {
            steps {
                sh '''
                    if [ ! -f .env ]; then
                        cp .env.example .env
                    fi
                    grep -q '^PORT=' .env || echo 'PORT=9001' >> .env
                    sed -i.bak "s/^PORT=.*/PORT=9001/" .env
                    grep -q '^HOST=' .env || echo 'HOST=0.0.0.0' >> .env
                    sed -i.bak "s/^HOST=.*/HOST=0.0.0.0/" .env
                '''
            }
        }

        stage('Validate app import') {
            steps {
                sh '''
                    . .venv/bin/activate
                    python - <<'PY'
from app import app
print(app.title)
print('FastAPI app import OK')
PY
                '''
            }
        }

        stage('Run app') {
            steps {
                sh '''
                    . .venv/bin/activate
                    nohup env HOST="${HOST}" PORT="${PORT}" python app.py > app.log 2>&1 &
                    for i in $(seq 1 30); do
                        if curl -fsS "http://localhost:${PORT}/health" >/dev/null 2>&1; then
                            echo "Application started successfully on port ${PORT}"
                            exit 0
                        fi
                        sleep 2
                    done
                    echo "Application failed to start on port ${PORT}"
                    exit 1
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'app.log', allowEmptyArchive: true
        }
    }
}
