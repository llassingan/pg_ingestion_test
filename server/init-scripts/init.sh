#!/bin/bash
set -e

# Define log file in the mounted volume
LOG_FILE="/var/db/logs/db_init_$(date +%Y%m%d_%H%M%S).log"

# Function to log messages to both console and file
log_message() {
    echo "$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to execute SQL files with error handling
execute_sql_file() {
    local file=$1
    log_message "Executing file: $file"
    if PGPASSWORD=$POSTGRES_PASSWORD_TARGET psql -h "$POSTGRES_HOST_TARGET" -p "$POSTGRES_PORT_TARGET" -U "$POSTGRES_USER_TARGET" -d "$POSTGRES_DB_TARGET" -f "$file" 2>> "$LOG_FILE"; then
        log_message "Successfully executed: $file"
    else
        log_message "ERROR: Failed to execute: $file"
        exit 1
    fi
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

log_message "Starting database initialization script"

# Wait for the database to be ready
until PGPASSWORD=$POSTGRES_PASSWORD_TARGET psql -h "$POSTGRES_HOST_TARGET" -p "$POSTGRES_PORT_TARGET" -U "$POSTGRES_USER_TARGET" -d "$POSTGRES_DB_TARGET" -c '\q' 2>> "$LOG_FILE"; do
    log_message "Postgres is unavailable - sleeping"
    sleep 1
done

log_message "Postgres is up - executing DDL scripts"

# Execute all DDL files in alphabetical order
for f in /docker-entrypoint-initdb.d/ddl/*.sql; do
    if [ -f "$f" ]; then
        execute_sql_file "$f"
    else
        log_message "No DDL files found"
        break
    fi
done

log_message "DDL scripts completed - executing DML scripts"

# Execute all DML files in alphabetical order
for f in /docker-entrypoint-initdb.d/dml/*.sql; do
    if [ -f "$f" ]; then
        execute_sql_file "$f"
    else
        log_message "No DML files found"
        break
    fi
done

log_message "All scripts completed successfully"
