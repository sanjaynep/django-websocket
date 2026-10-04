# BuddyBase

BuddyBase is a Django-based group collaboration hub for friends. It combines authenticated group chat, real-time WebSocket messaging, AI-assisted conversations, group decision-making, shared lists, and a personal AI buddy that can remember simple user preferences.

> **Project status:** This repository is currently configured as a development/demo application. Before deploying it publicly, review the security and production-readiness notes below.

## Features

- User registration, login, and logout
- Create friend groups and add registered users by username
- Real-time group chat over WebSockets
- Mention `@buddy` or `@ai` in group chat to request an AI response
- AI-assisted group decisions:
  - Create a question with one option per line
  - Vote on options
  - Regenerate an AI recommendation using current votes
  - Mark a decision as resolved
- Shared lists for each group:
  - Create lists
  - Add items asynchronously
  - Mark items complete or incomplete
  - Ask the AI list assistant to suggest, categorize, or summarize items
- Personal Buddy chat with session-based conversation history
- Lightweight preference memory based on phrases such as `I like ...`, `I love ...`, `I hate ...`, and `my favorite ...`
- Django admin access to the application models
- Automatic CPU/GPU selection for the Qwen language model

## Technology stack

- Python
- Django
- Django Channels and Daphne for ASGI/WebSocket support
- SQLite for local development
- PyTorch and Hugging Face Transformers
- Qwen/Qwen2.5-1.5B-Instruct for AI responses
- HTML templates, CSS, and vanilla JavaScript

## Repository structure

```text
.
├── ai_engine/
│   └── qwen.py                 # Qwen model loading and text generation helpers
├── buddybase/
│   ├── settings.py             # Django, database, Channels, and static-file settings
│   ├── urls.py                 # Project-level HTTP routes
│   ├── asgi.py                 # HTTP and WebSocket ASGI application
│   └── wsgi.py                 # WSGI entry point
├── hub/
│   ├── models.py               # Groups, messages, decisions, votes, lists, and memories
│   ├── views.py                # HTML views and JSON POST endpoints
│   ├── consumers.py            # Authenticated real-time group chat consumer
│   ├── routing.py              # WebSocket URL patterns
│   ├── forms.py                # Group, decision, list, and member forms
│   ├── admin.py                # Django admin model registration
│   ├── migrations/             # Database schema migrations
│   ├── templates/hub/          # Django HTML templates
│   └── static/hub/             # Shared JavaScript and CSS assets
├── manage.py                   # Django management command entry point
├── requirements.txt            # Python dependencies
└── .gitignore                  # Local, generated, and secret files excluded from Git
```

## How the application works

Django serves the normal HTTP pages through `buddybase.urls`, which includes the routes from `hub.urls`. Most application pages require authentication and use the `Group`, `Decision`, `SharedList`, and related models defined in `hub.models`.

The ASGI application in `buddybase/asgi.py` serves both HTTP and WebSocket traffic. Authenticated WebSocket connections to `/ws/group/<group_id>/chat/` are handled by `hub.consumers.GroupChatConsumer`; the consumer verifies group membership, persists messages, broadcasts them through the Channels layer, and invokes the Qwen model when a message contains `@buddy` or `@ai`.

AI generation is centralized in `ai_engine/qwen.py`. The model is loaded lazily once with an LRU cache, uses CUDA when available, and falls back to CPU otherwise. Generation is serialized with a lock and has a 60-second timeout.

## Requirements

- Python 3.10+ recommended
- `pip` and `venv`
- Enough disk space and memory for the Hugging Face Qwen model
- Optional NVIDIA GPU with a compatible PyTorch installation for faster generation

The dependency file currently includes Django, Channels, Daphne, PyTorch, Transformers, Accelerate, SentencePiece, Requests, and Markdown2. The first AI request downloads `Qwen/Qwen2.5-1.5B-Instruct` from Hugging Face unless it is already cached locally.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sanjaynep/django-websocket.git
cd django-websocket
```

### 2. Create and activate a virtual environment

#### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **GPU note:** The unpinned `torch` dependency may install a CPU or platform-specific build depending on your Python and operating system. For CUDA acceleration, install the PyTorch build appropriate for your CUDA version from the official PyTorch installation instructions, then install the remaining requirements.

### 4. Apply database migrations

```bash
python manage.py migrate
```

The default development database is SQLite at `db.sqlite3`. It is intentionally ignored by Git.

### 5. Create an administrator account (optional)

```bash
python manage.py createsuperuser
```

The admin site is available at `/admin/` after the development server starts.

## Run the application

Because this project uses Django Channels and Daphne, run the ASGI application with Daphne:

```bash
daphne -b 127.0.0.1 -p 8000 buddybase.asgi:application
```

Then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in a browser.

For ordinary Django development work, the standard development server also starts the project, but Daphne is the recommended command when testing WebSocket chat:

```bash
python manage.py runserver
```

### First-use flow

1. Open `/register/` and create a user account.
2. Sign in at `/login/`.
3. Create a group from the home page.
4. Add other registered users by username.
5. Open the group chat and send a message.
6. Include `@buddy` or `@ai` in a message to trigger Buddy.
7. Use the group navigation to create decisions or shared lists.
8. Open `/buddy/` for a personal AI conversation.

## Main routes

### Browser pages

| Route | Purpose |
| --- | --- |
| `/` | Authenticated home page and group list |
| `/register/` | Create a user account |
| `/login/` | Sign in |
| `/logout/` | Django logout route |
| `/signout/` | POST-based sign-out form handler |
| `/create-group/` | Create a group |
| `/group/<group_id>/add-member/` | Add a registered user to a group |
| `/group/<group_id>/chat/` | Group chat page |
| `/group/<group_id>/decisions/` | List active and resolved decisions |
| `/group/<group_id>/decisions/new/` | Create a decision |
| `/group/<group_id>/decisions/<decision_id>/` | View, vote on, and resolve a decision |
| `/group/<group_id>/lists/` | List shared lists |
| `/group/<group_id>/lists/new/` | Create a shared list |
| `/group/<group_id>/lists/<list_id>/` | View and update a shared list |
| `/buddy/` | Personal Buddy chat and saved memories |
| `/admin/` | Django administration |

### WebSocket endpoint

```text
/ws/group/<group_id>/chat/
```

The browser chooses `ws://` for HTTP and `wss://` for HTTPS. A connection is accepted only when the user is authenticated and is a member of the requested group.

Messages sent to the socket use this JSON shape:

```json
{"message": "Hello everyone"}
```

Incoming message events use this shape:

```json
{
  "type": "message",
  "message": "Hello everyone",
  "username": "alice",
  "is_ai": false,
  "time": "14:30"
}
```

Buddy typing notifications are sent as:

```json
{"type": "typing"}
```

### JSON POST endpoints

All endpoints require an authenticated session and are intended to be called with the CSRF token used by the templates.

| Method | Route | Request body | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/buddy/` | `{"message":"..."}` | Ask personal Buddy and update session history |
| `POST` | `/api/decision/<decision_id>/vote/` | `{"option_id": 1}` | Replace the current user's vote and refresh AI recommendation |
| `POST` | `/api/decision/<decision_id>/resolve/` | none | Mark a decision as resolved |
| `POST` | `/api/list/<list_id>/add/` | `{"text":"..."}` | Add a list item |
| `POST` | `/api/list/<list_id>/toggle/<item_id>/` | none | Toggle an item's completion state |
| `POST` | `/api/list/<list_id>/ai/` | `{"action":"categorize"}` | Ask the AI list assistant about the list |

## AI behavior and configuration

The AI engine is configured in `ai_engine/qwen.py`:

- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Maximum generated tokens: `256`
- Generation timeout: `60` seconds
- CUDA is selected when `torch.cuda.is_available()` returns `True`
- CPU uses `float32`; CUDA uses `float16`
- The model is loaded lazily on the first request and cached for the process lifetime
- A generation lock prevents concurrent model generation in the process

The application defines separate system prompts for group chat, decisions, shared lists, and personal Buddy interactions. To change the model or generation settings, edit the constants in `ai_engine/qwen.py`.

You can test the AI engine directly after installing dependencies:

```bash
python -m ai_engine.qwen
```

The first run may take time because Transformers may download model files from Hugging Face.

## Data model

The `hub` app stores the following entities in SQLite by default:

- `Group`: a friend group and its members
- `ChatMessage`: group messages, including AI messages with `is_ai=True`
- `Decision`: a group question, its AI recommendation, and resolution state
- `DecisionOption`: an option belonging to a decision
- `Vote`: a user's selected option
- `SharedList`: a list belonging to a group
- `ListItem`: an item in a shared list
- `BuddyMemory`: a simple per-user key/value preference memory

The initial schema is defined in `hub/migrations/0001_initial.py`.

## Testing and maintenance commands

The repository currently contains only the default placeholder in `hub/tests.py`; no automated application tests are implemented yet. You can still run Django's test discovery and validation commands:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations
python manage.py migrate
```

Run `makemigrations` only when you intentionally change models and want to create a new migration. Review generated migrations before committing them.

## Configuration and production notes

The current `buddybase/settings.py` is suitable for local development but should not be used unchanged in production. Before deployment:

1. Move `SECRET_KEY` to an environment variable and rotate the committed development key.
2. Set `DEBUG = False`.
3. Replace `ALLOWED_HOSTS = ['*']` with the real hostnames.
4. Configure `CSRF_TRUSTED_ORIGINS` for the deployed HTTPS origin.
5. Use a production database instead of SQLite for concurrent workloads.
6. Replace `InMemoryChannelLayer` with Redis or another shared channel layer when running multiple processes or instances.
7. Configure static-file collection and serving, for example with `collectstatic` and a suitable web server.
8. Install and configure the correct production PyTorch build and confirm the machine can run the selected model.
9. Add rate limiting, authorization checks, structured error handling, and automated tests before exposing the API publicly.
10. Ensure WebSocket traffic is served through a proxy that supports upgrade requests and uses `wss://` in production.

The repository currently includes a hard-coded development secret, wildcard hosts, debug mode, an in-memory channel layer, and an unpinned AI dependency set. These are important deployment considerations, not required changes for a local demo.

## Troubleshooting

### The first AI request is slow

The model is loaded lazily by `_load_llm()` in `ai_engine/qwen.py`. The first request downloads and initializes the model. Later requests reuse the cached model. CPU inference can also be substantially slower than CUDA inference.

### The WebSocket closes immediately

Check all of the following:

- You are signed in.
- Your user is a member of the requested group.
- The server is running through the ASGI application.
- The browser is using the correct `ws://` or `wss://` scheme.
- Daphne, Channels, and Django are installed in the active virtual environment.

### Database tables do not exist

Run:

```bash
python manage.py migrate
```

### Model loading fails

Confirm that `torch`, `transformers`, `accelerate`, and `sentencepiece` installed successfully. Also verify available RAM/VRAM and network access to Hugging Face. If a CUDA installation fails, try a compatible CPU PyTorch build first.

## Contributing

1. Create a feature branch.
2. Make a focused change.
3. Run the Django checks and tests.
4. Verify both HTTP pages and WebSocket chat manually when relevant.
5. Keep secrets, databases, model caches, and generated static files out of commits.
6. Open a pull request with a clear description of the behavior changed.

## License

No license file is currently included in the repository. Add a license before distributing or accepting external contributions under defined terms.
