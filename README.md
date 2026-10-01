# AI Coding Models: Lab Starter
Requires Docker with Compose v2. Python 3.10+ and pytest for the mini-eval (pip install pytest).

- Lab A (static):  put your generated site in site/, then
  `docker compose --profile lab-a up` -> http://localhost:8080
- Lab B (dynamic): `docker compose --profile lab-b up --build` -> http://localhost:8081
  API check: `curl localhost:8081/api/health` and `curl localhost:8081/api/entries`
- Mini-eval (Module 8): `cd mini-eval`, follow SPEC.md, then `python run_eval.py`.
  Instructor check: `SAMPLE=reference/duration_reference.py python -m pytest -q tests`
- Prompt templates: prompts/prompts.md



WORKED EXAMPLE:

$  sudo python3 -m venv venv
$  source venv/bin/activate
# Below command does not work
$  pip install -r requirements.txt
# Below command works.
$  sudo pip install -r requirements.txt --break-system-packages

# we are ready with all requirements now...
