pipeline {
agent any

parameters {
string(name: 'CHATBOT_PORT', defaultValue: '9003', description: 'Port for chatbot service')
}

environment {
APP_DIR = "${WORKSPACE}"
CHATBOT_PORT = "${params.CHATBOT_PORT}"
}

stages {
stage('Checkout branch') {
steps {
sh '''
set -eux
git checkout anu || git checkout -b anu
'''
}
}

stage('Install dependencies') {
steps {
sh '''
set -eux
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/activate
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
'''
}
}

stage('Prepare environment') {
steps {
sh '''
set -eux
cd "$APP_DIR"
echo "PORT=${CHATBOT_PORT}" > .env
echo "HOST=0.0.0.0" >> .env
'''
}
}

stage('Validate app import') {
steps {
sh '''
set -eux
cd "$APP_DIR"
.venv/bin/python3 -c "import app; print('IMPORT_OK')"
'''
}
}

stage('Run app') {
steps {
sh '''
set -eux
cd "$APP_DIR"
fuser -k "${CHATBOT_PORT}/tcp" || true
BUILD_ID=dontKillMe nohup .venv/bin/python3 app.py > chatbot.log 2>&1 &
sleep 3
curl -fSs "http://127.0.0.1:${CHATBOT_PORT}/" || curl -fSs "http://127.0.0.1:${CHATBOT_PORT}/health" || true
'''
}
}
}

post {
always {
archiveArtifacts artifacts: 'chatbot.log', allowEmptyArchive: true
}
}
}
