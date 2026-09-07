# Django Boilerplate

A ready-to-clone Django backend for department projects. It ships the parts every
project needs and nobody wants to rewrite: user accounts, a sign-in page,
password resets, roles, an admin, a JSON API and tests.

Clone it, rename it, and start building on the dashboard.

## What you get

| | |
|---|---|
| **Accounts** | Custom user model keyed on **email address** (no usernames), with name, job title and role |
| **Sign-in pages** | Login, logout, self-service signup, profile, password change, password reset by email |
| **Roles** | `Administrator` / `Manager` / `Member`, enforced by `role_required`, `RoleRequiredMixin` and a DRF permission |
| **JSON API** | Token + session auth at `/api/auth/` (login, logout, me, password change) |
| **Admin** | Django admin tuned for the user model, with activate/deactivate bulk actions |
| **Hardening** | Per-IP login attempt limiting, secure cookies and HSTS when `DEBUG=False`, throttled API |
| **Ops** | 12-factor settings, `/healthz/` probe, WhiteNoise static files, Dockerfile, Compose with Postgres |
| **Quality** | 45 tests, an end-to-end smoke test, Ruff config, GitHub Actions CI |

## Quick start

```bash
git clone <this-repo> my-project && cd my-project
make install          # virtualenv + dependencies + .env
make migrate
make superuser        # your first administrator account
make run              # http://127.0.0.1:8000/
```

No database to install: it runs on SQLite out of the box. `make help` lists
every command.

Without `make`:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

### On Windows

`make` is not available, so run the same steps directly (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
Copy-Item .env.example .env
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver
```

The equivalent of `make verify`:

```powershell
.venv\Scripts\ruff check .
.venv\Scripts\python manage.py test --settings=config.test_settings
.venv\Scripts\python scripts\smoke_test.py
```

### Pages

| URL | Who can see it |
|---|---|
| `/` | Everyone — public landing page |
| `/accounts/login/` | Everyone — the sign-in page |
| `/accounts/signup/` | Everyone, unless `SIGNUP_OPEN=False` |
| `/dashboard/` | Any signed-in user |
| `/team/` | Managers and administrators only (an example of a role-gated page) |
| `/accounts/profile/` | Any signed-in user, for their own details |
| `/admin/` | Staff accounts |
| `/healthz/` | Everyone — JSON health probe for load balancers |

## Making it your project

1. **Set the name.** `SITE_NAME` in `.env` retitles the site, the nav and the admin.
2. **Build on the dashboard.** `core/views.py` and `templates/core/dashboard.html`
   are a placeholder — replace them with your project's home page.
3. **Add your apps.** `python manage.py startapp <name>`, add it to `INSTALLED_APPS`,
   and include its URLs in `config/urls.py`.
4. **Decide how people get accounts** (see below).
5. **Drop what you don't need.** No API? Delete `accounts/api.py`,
   `accounts/api_urls.py`, `accounts/serializers.py`, `accounts/tests/test_api.py`,
   the `/api/auth/` line in `config/urls.py`, and the `rest_framework` entries in
   `INSTALLED_APPS` and `requirements.txt`.

### Controlling who gets in

Three settings in `.env` cover the usual department policies:

```ini
# Anyone with the link can register (the default)
SIGNUP_OPEN=True

# Anyone can register, but only with a department address
SIGNUP_ALLOWED_EMAIL_DOMAINS=dept.example.edu,example.edu

# Nobody self-registers; an administrator creates accounts in /admin/
SIGNUP_OPEN=False
```

To revoke someone's access, **deactivate** their account in the admin rather than
deleting it — their history stays intact and they can no longer sign in.

### Using roles

Every user has a `role`. Administrators pass every role check, so you only ever
name the lowest role that should be allowed.

```python
from accounts.models import User
from accounts.permissions import HasRole, RoleRequiredMixin, role_required


# Function-based view
@role_required(User.Role.MANAGER)
def budget_report(request): ...


# Class-based view
class BudgetReport(RoleRequiredMixin, TemplateView):
    required_roles = [User.Role.MANAGER]


# DRF viewset
class BudgetViewSet(ModelViewSet):
    permission_classes = [HasRole.of(User.Role.MANAGER)]
```

In templates: `{% if user.is_manager %}` / `{% if user.is_admin %}`.

Need finer-grained rules than three roles? Use Django's built-in groups and
permissions on top — they work unchanged.

## The API

Session-authenticated JavaScript on the same site can call these directly.
Scripts and mobile clients log in once and send the token afterwards.

```bash
# Log in
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
     -H 'Content-Type: application/json' \
     -d '{"email":"you@example.com","password":"..."}'
# -> {"token": "a933...", "user": {...}}

# Use it
curl http://127.0.0.1:8000/api/auth/me/ -H 'Authorization: Token a933...'
```

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/login/` | Email + password → token |
| `POST` | `/api/auth/logout/` | Revoke the token, end the session |
| `GET` / `PATCH` | `/api/auth/me/` | Read or update the caller's profile |
| `POST` | `/api/auth/password/` | Change password, rotating the token |

New API views are authenticated by default (`IsAuthenticated` is the project-wide
default permission); opt out explicitly with `permission_classes = [AllowAny]`.

## Verifying it works

Three layers, from fastest to most convincing.

### 1. One command

```bash
make verify
```

Runs the linter, the test suite, then starts a server and exercises the whole
application over real HTTP — 29 checks covering public pages, protected pages,
sign-in for each role, the role gate, CSRF, and the JSON API. Every line prints
PASS or FAIL, and the command exits non-zero if anything fails.

Use `make test` alone (about a second) while you are writing code, and
`make verify` before you hand a project to someone else.

### 2. The end-to-end smoke test on its own

```bash
make smoke                              # starts its own server on port 8765
python scripts/smoke_test.py 8000       # or point it at a server you already have running
```

The script is plain Python with no dependencies, so it runs the same on Windows,
macOS and Linux — on Windows use `.venv\Scripts\python scripts\smoke_test.py`.

This is the check to run after deploying, or when something feels wrong. It
catches what unit tests cannot see: cookies, CSRF, redirects, static files and
the real login round-trip. It creates the demo accounts described below, so run
it against development or staging, never production.

### 3. Click through it yourself

Some things only a person can judge — that the pages read well, that error
messages make sense, that the reset email arrives. Create one account per role:

```bash
make demo    # admin@example.com, manager@example.com, member@example.com
             # password for all three: demo-passphrase-42
make run
```

(`make demo` refuses to run when `DEBUG=False`, so these known passwords cannot
reach a real deployment.)

Then walk through this list at http://127.0.0.1:8000/ — it is the behaviour the
project is supposed to guarantee:

| Step | What should happen |
|---|---|
| Visit `/dashboard/` signed out | Bounced to the login page |
| Sign in as `member@example.com` | Lands on the dashboard, greeted by name |
| Look at the nav as the member | No **Team** or **Admin** links |
| Type `/team/` in the address bar | **403 Forbidden** — the role gate holds even without a link |
| Sign out, sign in as `manager@example.com` | **Team** appears in the nav and the page opens |
| Sign in as `admin@example.com` | **Team** and **Admin** both work |
| Sign in with `MEMBER@EXAMPLE.COM` | Works — email is case-insensitive |
| Sign in with a wrong password | Stays on the login page with an error, and does not say whether the address exists |
| Get the password wrong 8 times | "Too many failed attempts" — the limiter kicks in |
| Use **Forgotten your password?** | The reset email is printed in the terminal running the server; the link opens a working form |
| Edit your name on `/accounts/profile/` | Saves, and there is no field to change your own role |
| In `/admin/`, deactivate a user, then try to sign in as them | Refused, with a message to contact an administrator |

### Does it do what *we* want?

The tests prove it does what it says. Whether that matches your department is a
separate question — the settings most likely to need a decision are:

- **Who may create an account?** `SIGNUP_OPEN` and
  `SIGNUP_ALLOWED_EMAIL_DOMAINS` (see *Controlling who gets in* above). Try
  registering from a personal address to confirm your choice is enforced.
- **Are three roles enough?** Add one in `accounts/models.py` (`User.Role`),
  make a migration, and it works everywhere immediately.
- **Do reset emails actually arrive?** Development prints them to the console.
  Point `EMAIL_*` at your real SMTP server and repeat the reset test before you
  rely on it.
- **Session length.** `SESSION_COOKIE_AGE` defaults to 12 hours.

### Before a deployment

```bash
make check     # Django's own deployment checklist
```

Run it with your production environment loaded (`DEBUG=False`, a real
`DJANGO_SECRET_KEY`, your real `ALLOWED_HOSTS`). It should report no issues. The
app deliberately refuses to start with `DEBUG=False` and no secret key.

CI runs the linter, the tests, a check for missing migrations, a fresh-checkout
start-up using `.env.example`, the smoke test and the deployment checklist on
every push.

## Development

```bash
make test        # run the suite (fast: in-memory database, cheap hashing)
make smoke       # end-to-end check over real HTTP
make verify      # lint + test + smoke
make coverage    # tests plus a coverage report
make lint        # ruff check + format check
make format      # auto-fix
make check       # Django's deployment checklist
```

Password-reset emails are printed to the console in development — copy the link
from the terminal.

## Postgres and Docker

SQLite is the default. To use Postgres, set `DATABASE_URL` in `.env`:

```ini
DATABASE_URL=postgres://django:django@localhost:5432/django
```

Compose brings up Postgres and the app together:

```bash
docker compose up --build     # http://127.0.0.1:8000/
docker compose exec web python manage.py createsuperuser
```

## Deploying

Set these in the environment (never commit them):

```ini
DEBUG=False
DJANGO_SECRET_KEY=<50+ random characters>
ALLOWED_HOSTS=portal.dept.example.edu
CSRF_TRUSTED_ORIGINS=https://portal.dept.example.edu
DATABASE_URL=postgres://...
SECURE_SSL_REDIRECT=True
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.edu
DEFAULT_FROM_EMAIL=no-reply@dept.example.edu
```

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

With `DEBUG=False` the project turns on secure cookies, HSTS and hashed static
files automatically, and refuses to start without a secret key. The Docker image
runs migrations, collects static files and serves the app with Gunicorn. Run
`make check` before a release.

Running more than one worker process? Point `CACHE_URL` at Redis or Memcached so
the login attempt limiter is shared across them.

## Layout

```
config/            settings, URLs, WSGI/ASGI
  settings.py        all configuration, read from the environment
  test_settings.py   fast settings for the test suite
accounts/          user model, auth pages, roles, JSON API
  models.py          the custom User (email login, role)
  backends.py        case-insensitive email authentication
  views.py           login, signup, profile, password views
  permissions.py     role_required / RoleRequiredMixin / HasRole
  throttling.py      per-IP login attempt limiting
  api.py             DRF auth endpoints
core/              landing page, dashboard, role-gated example, health check
scripts/           smoke_test.py -- end-to-end verification over real HTTP
templates/         base layout, auth pages, dashboard
static/css/        one small stylesheet, no build step
```

## Conventions worth keeping

- Configuration comes from the environment; `.env` is git-ignored and
  `.env.example` documents every setting.
- The user model is `accounts.User` — always reference it with
  `settings.AUTH_USER_MODEL` or `get_user_model()`, never by importing it into
  another model's `ForeignKey` directly.
- Users may edit their own name and job title, never their own role or staff flag.
- New pages require a login unless there is a reason they shouldn't.
