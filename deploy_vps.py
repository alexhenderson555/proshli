import os
import tarfile
import paramiko
import secrets

# Server details
HOST = "151.243.177.88"
USER = "root"
PASSWORD = "n--rV-SE33"

# Source path (local)
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_PATH = os.path.join(LOCAL_DIR, "proshli.tar.gz")

def exclude_files(tarinfo):
    name = tarinfo.name
    # Exclude files/directories
    exclude_list = [
        "node_modules",
        ".git",
        ".next",
        "dist",
        ".venv",
        ".turbo",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "proshli.tar.gz",
        "deploy_vps.py"
    ]
    for ex in exclude_list:
        if ex in name.split(os.sep):
            return None
    return tarinfo

def create_archive():
    print("Compressing project files to proshli.tar.gz...")
    with tarfile.open(ARCHIVE_PATH, "w:gz") as tar:
        tar.add(LOCAL_DIR, arcname="", filter=exclude_files)
    print("Archive created successfully.")

def run_ssh_command(ssh, cmd):
    print(f"Executing: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    # Wait for the command to finish
    exit_status = stdout.channel.recv_exit_status()
    
    out = stdout.read().decode(errors='replace').strip()
    err = stderr.read().decode(errors='replace').strip()
    
    if out:
        try:
            print(f"STDOUT:\n{out}")
        except UnicodeEncodeError:
            print(f"STDOUT:\n{out.encode('ascii', errors='replace').decode('ascii')}")
    if err:
        try:
            print(f"STDERR:\n{err}")
        except UnicodeEncodeError:
            print(f"STDERR:\n{err.encode('ascii', errors='replace').decode('ascii')}")
        
    if exit_status != 0:
        raise Exception(f"Command failed with exit status {exit_status}")
    return out

def deploy():
    # 1. Create archive
    create_archive()
    
    # 2. Connect to VPS
    print(f"Connecting to VPS {HOST} via SSH...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("Connected.")
    
    try:
        # 3. Install Docker and Docker Compose if not available
        print("Checking/Installing Docker on the VPS...")
        print("Waiting for any background apt-get or dpkg processes to release their locks...")
        try:
            run_ssh_command(ssh, "systemctl stop unattended-upgrades || true")
        except Exception as e:
            print(f"Failed to stop unattended-upgrades (non-fatal): {e}")
        
        # A loop to wait for locks to be released
        lock_wait_cmd = (
            "while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || "
            "fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || "
            "fuser /var/lib/dpkg/lock >/dev/null 2>&1; "
            "do echo 'Waiting for apt lock...'; sleep 5; done"
        )
        run_ssh_command(ssh, lock_wait_cmd)
        
        run_ssh_command(ssh, "apt-get update")
        run_ssh_command(ssh, "apt-get install -y curl tar")
        try:
            run_ssh_command(ssh, "apt-get remove -y docker docker-engine docker.io containerd runc || true")
        except Exception as e:
            print(f"Remove failed (non-fatal): {e}")
        run_ssh_command(ssh, "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh")
        # docker-compose-plugin is already installed by get-docker.sh, no need to install docker-compose-v2
        print("Docker installed successfully. Compose plugin is ready.")
        
        # 4. Upload archive
        print("Uploading archive to VPS...")
        sftp = ssh.open_sftp()
        sftp.put(ARCHIVE_PATH, "/tmp/proshli.tar.gz")
        sftp.close()
        print("Upload complete.")
        
        # 5. Extract files
        print("Extracting files on the VPS...")
        run_ssh_command(ssh, "mkdir -p /var/www/proshli")
        run_ssh_command(ssh, "tar -xzf /tmp/proshli.tar.gz -C /var/www/proshli")
        
        # 6. Generate secure tokens for production (or reuse existing ones from env)
        pg_password = None
        jwt_secret = None
        try:
            print("Checking for existing deploy/.env.prod on VPS to preserve secrets...")
            existing_env = run_ssh_command(ssh, "cat /var/www/proshli/deploy/.env.prod || echo ''")
            for line in existing_env.splitlines():
                if line.startswith("POSTGRES_PASSWORD="):
                    pg_password = line.split("=", 1)[1].strip()
                elif line.startswith("JWT_SECRET="):
                    jwt_secret = line.split("=", 1)[1].strip()
            if pg_password:
                print("Found existing POSTGRES_PASSWORD. Reusing it.")
            if jwt_secret:
                print("Found existing JWT_SECRET. Reusing it.")
        except Exception as e:
            print(f"Could not read existing env (non-fatal): {e}")

        if not pg_password:
            pg_password = secrets.token_urlsafe(16)
        if not jwt_secret:
            jwt_secret = secrets.token_urlsafe(32)
        
        # Values from local environment
        telegram_token = "8538018548:AAGq0hB1iRDFPWIkIWX5ino4M1ahFk0u2NE"
        admin_chat_id = "788578446"
        pub_channel_id = "-1003993675697"
        pub_group_id = "-1003962937534"
        bot_service_key = "nXUXaElZedz9QQIjd4Wi_H7V0c7zoinF7V6U8VNJTGU"
        anthropic_key = "sk-fp-adb2fecf-d9dc-40be-a7ec-85385434bba7"
        anthropic_url = "https://api.tokenator.cloud/anthropic"
        
        env_content = f"""# Production environment
PROSHLI_DOMAIN=proshli.ru
POSTGRES_USER=proshli
POSTGRES_PASSWORD={pg_password}
POSTGRES_DB=proshli

JWT_SECRET={jwt_secret}
BOT_SERVICE_KEY={bot_service_key}

TELEGRAM_BOT_TOKEN={telegram_token}
TELEGRAM_ADMIN_CHAT_ID={admin_chat_id}
TELEGRAM_PUBLICATION_CHANNEL_ID={pub_channel_id}
TELEGRAM_PUBLICATION_GROUP_ID={pub_group_id}
CHANNEL_APPROVAL_TOP_N=8

PROSHLI_BOT_TOKEN={telegram_token}
PROSHLI_BOT_SERVICE_KEY={bot_service_key}

ANTHROPIC_API_KEY={anthropic_key}
ANTHROPIC_BASE_URL={anthropic_url}
ANTHROPIC_MODEL=claude-opus-4-7
ANTHROPIC_MAX_TOKENS=1024

CORS_ALLOWED_ORIGINS=https://proshli.ru,https://www.proshli.ru,https://app.proshli.ru
TRUSTED_PROXIES=172.16.0.0/12

# YOOKASSA configuration bypass
YOOKASSA_SECRET_KEY=mock-staging-secret-key-please-replace
"""
        # Write .env.prod directly to the server
        print("Writing deploy/.env.prod on VPS...")
        sftp = ssh.open_sftp()
        with sftp.file("/var/www/proshli/deploy/.env.prod", "w") as f:
            f.write(env_content)
        sftp.close()
        
        # 7. Start docker-compose stack
        print("Building and running docker-compose stack...")
        run_ssh_command(ssh, "cd /var/www/proshli && docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d --build")
        
        # 8. Run migrations
        print("Running database migrations...")
        run_ssh_command(ssh, "cd /var/www/proshli && docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod exec -T api uv run alembic upgrade head")
        
        # 9. Verify
        print("Verifying running containers...")
        run_ssh_command(ssh, "cd /var/www/proshli && docker compose -f deploy/docker-compose.prod.yml ps")
        
        print("DEPLOYMENT SUCCESSFUL!")
        
    finally:
        ssh.close()
        # Clean up local archive
        if os.path.exists(ARCHIVE_PATH):
            os.remove(ARCHIVE_PATH)

if __name__ == "__main__":
    deploy()
