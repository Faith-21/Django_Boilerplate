#!/usr/bin/env bash
#
# End-to-end check that a running copy of this project actually works.
#
#   ./scripts/smoke_test.sh          # starts its own server on port 8765
#   ./scripts/smoke_test.sh 8000     # tests a server you already have running
#
# It signs in as each demo role over real HTTP and asserts what should happen,
# including the things unit tests cannot see: CSRF, cookies, redirects, static
# files and the role gate.

set -uo pipefail

PORT="${1:-8765}"
OWN_SERVER=0
BASE="http://127.0.0.1:${PORT}"
PYTHON="${PYTHON:-.venv/bin/python}"
PASSWORD="demo-passphrase-42"
TMP="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() {
  [ "$OWN_SERVER" = "1" ] && [ -n "${SERVER_PID:-}" ] && kill "$SERVER_PID" 2>/dev/null
  rm -rf "$TMP"
}
trap cleanup EXIT

check() { # check <description> <expected> <actual>
  if [ "$2" = "$3" ]; then
    printf '  \033[32mPASS\033[0m  %-52s %s\n' "$1" "$3"
    PASS=$((PASS + 1))
  else
    printf '  \033[31mFAIL\033[0m  %-52s expected %s, got %s\n' "$1" "$2" "$3"
    FAIL=$((FAIL + 1))
  fi
}

code() { # code <url> [cookie-jar]
  if [ -n "${2:-}" ]; then
    curl -s --noproxy '*' -b "$2" -o /dev/null -w '%{http_code}' "$1"
  else
    curl -s --noproxy '*' -o /dev/null -w '%{http_code}' "$1"
  fi
}

login() { # login <email> <cookie-jar> -> prints the redirect target
  local jar="$2"
  local token
  token=$(curl -s --noproxy '*' -c "$jar" "$BASE/accounts/login/" \
          | grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' | head -1 | cut -d'"' -f4)
  curl -s --noproxy '*' -b "$jar" -c "$jar" -o /dev/null -w '%{redirect_url}' \
       -e "$BASE/accounts/login/" \
       -d "csrfmiddlewaretoken=${token}&username=$1&password=${PASSWORD}" \
       "$BASE/accounts/login/"
}

echo "Preparing the database and demo accounts..."
$PYTHON manage.py migrate --noinput > /dev/null || { echo "migrate failed"; exit 1; }
$PYTHON manage.py seed_demo > /dev/null || { echo "seed_demo failed"; exit 1; }

if ! curl -s --noproxy '*' -o /dev/null "$BASE/healthz/"; then
  echo "Starting a server on port ${PORT}..."
  OWN_SERVER=1
  $PYTHON manage.py runserver "$PORT" --noreload > "$TMP/server.log" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 40); do
    curl -s --noproxy '*' -o /dev/null "$BASE/healthz/" && break
    sleep 0.25
  done
fi

if ! curl -s --noproxy '*' -o /dev/null "$BASE/healthz/"; then
  echo "Could not reach ${BASE}. Server log:"
  cat "$TMP/server.log" 2>/dev/null
  exit 1
fi

echo
echo "Public pages (no account needed)"
check "landing page loads"                200 "$(code "$BASE/")"
check "login page loads"                  200 "$(code "$BASE/accounts/login/")"
check "signup page loads"                 200 "$(code "$BASE/accounts/signup/")"
check "password reset page loads"         200 "$(code "$BASE/accounts/password/reset/")"
check "health probe is ok"                200 "$(code "$BASE/healthz/")"
check "stylesheet is served"              200 "$(code "$BASE/static/css/main.css")"

echo
echo "Pages are protected when signed out"
check "dashboard redirects to login"      302 "$(code "$BASE/dashboard/")"
check "profile redirects to login"        302 "$(code "$BASE/accounts/profile/")"
check "team page redirects to login"      302 "$(code "$BASE/team/")"
check "admin redirects to login"          302 "$(code "$BASE/admin/")"

echo
echo "Signing in"
BAD_TOKEN=$(curl -s --noproxy '*' -c "$TMP/bad.txt" "$BASE/accounts/login/" \
    | grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' | head -1 | cut -d'"' -f4)
check "wrong password re-renders the form" 200 "$(curl -s --noproxy '*' -b "$TMP/bad.txt" -c "$TMP/bad.txt" \
    -o /dev/null -w '%{http_code}' -e "$BASE/accounts/login/" \
    -d "csrfmiddlewaretoken=${BAD_TOKEN}&username=member@example.com&password=wrong" "$BASE/accounts/login/")"
check "and leaves you signed out"          302 "$(code "$BASE/dashboard/" "$TMP/bad.txt")"
check "a POST without a CSRF token fails"  403 "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' \
    -d "username=member@example.com&password=${PASSWORD}" "$BASE/accounts/login/")"
check "member lands on the dashboard"     "$BASE/dashboard/" "$(login member@example.com "$TMP/member.txt")"
check "manager lands on the dashboard"    "$BASE/dashboard/" "$(login manager@example.com "$TMP/manager.txt")"
check "admin lands on the dashboard"      "$BASE/dashboard/" "$(login admin@example.com "$TMP/admin.txt")"
check "login is case-insensitive"         "$BASE/dashboard/" "$(login MEMBER@Example.COM "$TMP/case.txt")"

echo
echo "Roles decide who sees what"
check "member can open the dashboard"     200 "$(code "$BASE/dashboard/" "$TMP/member.txt")"
check "member is refused the team page"   403 "$(code "$BASE/team/" "$TMP/member.txt")"
check "manager can open the team page"    200 "$(code "$BASE/team/" "$TMP/manager.txt")"
check "admin can open the team page"      200 "$(code "$BASE/team/" "$TMP/admin.txt")"
check "member is refused the admin site"  302 "$(code "$BASE/admin/" "$TMP/member.txt")"
check "admin can open the admin site"     200 "$(code "$BASE/admin/" "$TMP/admin.txt")"

echo
echo "JSON API"
TOKEN=$(curl -s --noproxy '*' -H 'Content-Type: application/json' \
        -d "{\"email\":\"member@example.com\",\"password\":\"${PASSWORD}\"}" \
        "$BASE/api/auth/login/" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
check "login returns a token"             "yes" "$([ -n "$TOKEN" ] && echo yes || echo no)"
check "token opens /api/auth/me/"         200 "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' \
    -H "Authorization: Token ${TOKEN}" "$BASE/api/auth/me/")"
check "no token is refused"               401 "$(code "$BASE/api/auth/me/")"
check "bad credentials are refused"       400 "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' \
    -H 'Content-Type: application/json' -d '{"email":"member@example.com","password":"nope"}' \
    "$BASE/api/auth/login/")"
check "logout revokes the token"          204 "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' \
    -X POST -H "Authorization: Token ${TOKEN}" "$BASE/api/auth/logout/")"
check "the revoked token no longer works" 401 "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' \
    -H "Authorization: Token ${TOKEN}" "$BASE/api/auth/me/")"

echo
if [ "$FAIL" -eq 0 ]; then
  printf '\033[32m%s checks passed.\033[0m The project is working.\n' "$PASS"
  exit 0
fi
printf '\033[31m%s of %s checks failed.\033[0m\n' "$FAIL" "$((PASS + FAIL))"
exit 1
