#!/usr/bin/env python
"""
End-to-end check that a running copy of this project actually works.

    python scripts/smoke_test.py           # starts its own server on port 8765
    python scripts/smoke_test.py 8000      # test a server you already have running

Signs in as each demo role over real HTTP and asserts what should happen,
including what unit tests cannot see: CSRF, cookies, redirects, static files
and the role gate. Standard library only, so it runs anywhere Django does.

It creates the demo accounts, so run it against development or staging only.
"""

import http.cookiejar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PASSWORD = "demo-passphrase-42"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Windows terminals only understand ANSI colour on newer builds; skip it when
# the output is redirected or the terminal has not enabled it.
COLOUR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
GREEN, RED, RESET = ("\033[32m", "\033[31m", "\033[0m") if COLOUR else ("", "", "")

passed = 0
failed = 0


def check(description, expected, actual):
    global passed, failed
    if expected == actual:
        passed += 1
        print(f"  {GREEN}PASS{RESET}  {description:<42} {actual}")
    else:
        failed += 1
        print(f"  {RED}FAIL{RESET}  {description:<42} expected {expected}, got {actual}")


class Session:
    """A browser-like session: keeps cookies, never follows redirects blindly."""

    def __init__(self, base):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        # ProxyHandler({}) bypasses any system proxy -- localhost must stay local.
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.ProxyHandler({}),
            NoRedirect(),
        )

    def request(self, path, data=None, headers=None, method=None):
        url = path if path.startswith("http") else self.base + path
        body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
        req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
        if path.startswith("/accounts/") and body:
            req.add_header("Referer", url)
        try:
            with self.opener.open(req, timeout=15) as response:
                return response.status, response.read().decode("utf-8", "replace"), response.headers
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace"), exc.headers

    def status(self, path):
        return self.request(path)[0]

    def csrf_token(self, path):
        _, body, _ = self.request(path)
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', body)
        return match.group(1) if match else ""

    def login(self, email, password=PASSWORD):
        """
        Sign in through the real form.

        Returns where the browser is sent next -- Django sends a relative
        Location header -- or '' when the sign-in did not redirect at all.
        """
        token = self.csrf_token("/accounts/login/")
        status, _, headers = self.request(
            "/accounts/login/",
            {"csrfmiddlewaretoken": token, "username": email, "password": password},
        )
        return headers.get("Location", "") if status in (301, 302) else ""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Report redirects instead of following them -- that is what we assert on."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(base, path, payload=None, token=None, method=None):
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    if token:
        headers["Authorization"] = f"Token {token}"
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=15) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def server_is_up(base):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        opener.open(base + "/healthz/", timeout=2)
        return True
    except Exception:
        return False


def manage(*args):
    result = subprocess.run(
        [sys.executable, "manage.py", *args], cwd=BASE_DIR, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"'manage.py {' '.join(args)}' failed:\n{result.stdout}{result.stderr}")
        sys.exit(1)


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "8765"
    base = f"http://127.0.0.1:{port}"

    print("Preparing the database and demo accounts...")
    manage("migrate", "--noinput")
    manage("seed_demo")

    server = None
    if not server_is_up(base):
        print(f"Starting a server on port {port}...")
        server = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", port, "--noreload"],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for _ in range(40):
            if server_is_up(base):
                break
            time.sleep(0.25)

    if not server_is_up(base):
        print(f"Could not reach {base}.")
        if server:
            server.terminate()
            print(server.communicate()[0].decode("utf-8", "replace")[-2000:])
        sys.exit(1)

    try:
        run_checks(base)
    finally:
        if server:
            server.terminate()
            server.wait(timeout=10)

    print()
    if failed == 0:
        print(f"{GREEN}{passed} checks passed.{RESET} The project is working.")
        sys.exit(0)
    print(f"{RED}{failed} of {passed + failed} checks failed.{RESET}")
    sys.exit(1)


def run_checks(base):
    anon = Session(base)

    print("\nPublic pages (no account needed)")
    check("landing page loads", 200, anon.status("/"))
    check("login page loads", 200, anon.status("/accounts/login/"))
    check("signup page loads", 200, anon.status("/accounts/signup/"))
    check("password reset page loads", 200, anon.status("/accounts/password/reset/"))
    check("health probe is ok", 200, anon.status("/healthz/"))
    check("stylesheet is served", 200, anon.status("/static/css/main.css"))

    print("\nPages are protected when signed out")
    check("dashboard redirects to login", 302, anon.status("/dashboard/"))
    check("profile redirects to login", 302, anon.status("/accounts/profile/"))
    check("team page redirects to login", 302, anon.status("/team/"))
    check("admin redirects to login", 302, anon.status("/admin/"))

    print("\nSigning in")
    bad = Session(base)
    token = bad.csrf_token("/accounts/login/")
    status, _, _ = bad.request(
        "/accounts/login/",
        {"csrfmiddlewaretoken": token, "username": "member@example.com", "password": "wrong"},
    )
    check("wrong password re-renders the form", 200, status)
    check("and leaves you signed out", 302, bad.status("/dashboard/"))

    no_csrf = Session(base)
    status, _, _ = no_csrf.request(
        "/accounts/login/", {"username": "member@example.com", "password": PASSWORD}
    )
    check("a POST without a CSRF token fails", 403, status)

    member, manager, admin = Session(base), Session(base), Session(base)
    check("member lands on the dashboard", "/dashboard/", member.login("member@example.com"))
    check("manager lands on the dashboard", "/dashboard/", manager.login("manager@example.com"))
    check("admin lands on the dashboard", "/dashboard/", admin.login("admin@example.com"))
    check("login is case-insensitive", "/dashboard/", Session(base).login("MEMBER@Example.COM"))

    print("\nRoles decide who sees what")
    check("member can open the dashboard", 200, member.status("/dashboard/"))
    check("member is refused the team page", 403, member.status("/team/"))
    check("manager can open the team page", 200, manager.status("/team/"))
    check("admin can open the team page", 200, admin.status("/team/"))
    check("member is refused the admin site", 302, member.status("/admin/"))
    check("admin can open the admin site", 200, admin.status("/admin/"))

    print("\nJSON API")
    status, body = api(base, "/api/auth/login/", {"email": "member@example.com", "password": PASSWORD})
    api_token = json.loads(body).get("token", "") if status == 200 else ""
    check("login returns a token", "yes", "yes" if api_token else "no")
    check("token opens /api/auth/me/", 200, api(base, "/api/auth/me/", token=api_token)[0])
    check("no token is refused", 401, api(base, "/api/auth/me/")[0])
    check(
        "bad credentials are refused",
        400,
        api(base, "/api/auth/login/", {"email": "member@example.com", "password": "nope"})[0],
    )
    check(
        "logout revokes the token",
        204,
        api(base, "/api/auth/logout/", payload={}, token=api_token, method="POST")[0],
    )
    check("the revoked token no longer works", 401, api(base, "/api/auth/me/", token=api_token)[0])


if __name__ == "__main__":
    main()
