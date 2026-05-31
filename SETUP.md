# WinPatch — Setup Guide

## Windows Server Prerequisites

Before running WinPatch against a Windows server, WinRM must be enabled on each target.

### Enable WinRM (run as Administrator on each Windows server)

```powershell
# Enable WinRM with default settings
winrm quickconfig -q

# Allow unencrypted auth over HTTP (required for NTLM on HTTP port 5985)
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'

# Open firewall port 5985
netsh advfirewall firewall add rule name="WinRM HTTP" dir=in action=allow protocol=TCP localport=5985
```

### Service Account Requirements

The account used (default credential or per-server override) must be a local Administrator
or domain admin on each target server. PSWindowsUpdate requires elevated rights.

### Verify Connectivity from the Linux Host

```bash
curl -s -o /dev/null -w "%{http_code}" http://<SERVER_IP>:5985/wsman
# Expected: 200
```

---

## Running the App

### Generate a SECRET_KEY (required before first run)

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `.env`:
```
SECRET_KEY=<generated-key>
```

### Direct (Python)

```bash
pip install -r requirements.txt
python run.py
# App available at http://localhost:5000
```

### Docker

```bash
docker compose up -d
# App available at http://localhost:5000
```

Pass `SECRET_KEY` via environment or mount a `.env` file.

---

## Security Notes

- **No built-in authentication.** This app is designed for internal/private network use only.
  - Bind to `127.0.0.1` for single-workstation use, or place behind a reverse proxy (nginx, Caddy) with authentication for team access.
  - Do **not** expose port 5000 directly to the internet.
- **IP validation.** The app only connects to RFC1918 (private) IP addresses. Public IPs are blocked.
- **Credentials** are encrypted at rest using Fernet. The `SECRET_KEY` is required to decrypt them — back it up securely.
- **WinRM over HTTP** (port 5985) transmits credentials using NTLM. For production environments, consider enabling HTTPS (port 5986) with certificate validation.
