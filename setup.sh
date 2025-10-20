#!/bin/bash
set -e

# File Definitions
SECRET_DIR="secrets"
ENV_FILE=".env"
ENV_EXAMPLE_FILE=".env.example"

DB_PASS_FILE="$SECRET_DIR/db_password"
SECRET_KEY_FILE="$SECRET_DIR/secret_key"
PEPPER_FILE="$SECRET_DIR/refresh_token_pepper"
ADMIN_PASS_FILE="$SECRET_DIR/admin_password" #

# Create .env if not exists
if [ ! -s "$ENV_FILE" ]; then
  if [ ! -f "$ENV_EXAMPLE_FILE" ]; then
    echo "ERROR: Couldn't find $ENV_EXAMPLE_FILE."
    exit 1
  fi
  echo "Copying $ENV_EXAMPLE_FILE into $ENV_FILE..."
  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
else
  echo "$ENV_FILE already exists. Skipping."
fi

# Secrets Configuration ---
mkdir -p "$SECRET_DIR"
echo "Checking secrets and generating missing ones..."

# Helper function for secrets user DOESN'T need to know
generate_secret_if_missing() {
  local file_path=$1
  local length=$2
  local description=$3

  if [ ! -s "$file_path" ]; then
    echo "Generating: $description..."
    < /dev/urandom tr -dc 'A-Za-z0-9' | head -c "$length" > "$file_path"
    chmod 600 "$file_path"
  else
    echo "$description found. Skipping."
  fi
}

# Generate secrets user doesn't care about
generate_secret_if_missing "$DB_PASS_FILE" 32 "Database password"
generate_secret_if_missing "$SECRET_KEY_FILE" 64 "Secret key file"
generate_secret_if_missing "$PEPPER_FILE" 64 "Refresh token pepper"


ADMIN_PASS_VALUE=""
if [ ! -s "$ADMIN_PASS_FILE" ]; then
  echo "Generating: Admin password..."
  ADMIN_PASS_VALUE=$(< /dev/urandom tr -dc 'A-Za-z0-9' | head -c 16)
  echo "$ADMIN_PASS_VALUE" > "$ADMIN_PASS_FILE"
  chmod 600 "$ADMIN_PASS_FILE"
else
  echo "Admin password found. Reading..."
  ADMIN_PASS_VALUE=$(cat "$ADMIN_PASS_FILE")
fi

ADMIN_EMAIL_VALUE=$(grep "^ADMIN_EMAIL=" "$ENV_FILE" | cut -d '=' -f 2-)

if [ -z "$ADMIN_EMAIL_VALUE" ]; then
    echo "WARNING: Could not read ADMIN_EMAIL from $ENV_FILE."
    ADMIN_EMAIL_VALUE="<email-not-found-in-.env>"
fi

echo ""
echo "--------------------------------------------------"
echo "Setup complete! Demo login credentials:"
echo "--------------------------------------------------"
echo ""
echo "   Login:    $ADMIN_EMAIL_VALUE"
echo "   Password: $ADMIN_PASS_VALUE"
echo ""
echo "--------------------------------------------------"