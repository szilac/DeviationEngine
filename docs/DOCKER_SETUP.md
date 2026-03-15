# Deviation Engine - Docker Setup Guide

Run Deviation Engine with Docker in just a few steps. No programming experience required!

---

## Prerequisites

### Install Docker Desktop

**Windows or Mac:**
1. Go to [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Download and install Docker Desktop
3. Start Docker Desktop (wait for it to fully start)

**Linux:**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin
```

---

## Quick Start (5 minutes)

### Step 1: Download the Project

Download and extract the project, or clone with Git:

```bash
git clone https://github.com/szilac/DeviationEngine.git
cd DeviationEngine
```

### Step 2: Configure Your API Key

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` file with your favorite text editor (Notepad, TextEdit, nano, etc.)

3. Add your API key:
   ```bash
   # Option 1: Google Gemini (Recommended - Free)
   GEMINI_API_KEY=your_gemini_api_key_here

   # Option 2: OpenRouter
   # OPENROUTER_API_KEY=your_openrouter_key_here
   ```

**Get a Free API Key:**
- **Google Gemini**: https://aistudio.google.com/ (Click "Get API Key")
- **OpenRouter**: https://openrouter.ai/ (Create account, get key)

### Step 3: Start the Application

```bash
docker-compose up -d
```

Wait 1-2 minutes for everything to start.

### Step 4: Open in Browser

Go to: **http://localhost**

That's it! You're ready to create alternate histories.

---

## Common Operations

### Stop the Application

```bash
docker-compose down
```

### Restart the Application

```bash
docker-compose restart
```

### View Logs (Troubleshooting)

```bash
# View all logs
docker-compose logs

# View backend logs only
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f
```

### Update to Latest Version

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Check Status

```bash
docker-compose ps
```

---

## Configuration

### Environment Variables

Edit the `.env` file to customize your setup:

```bash
# Required: At least one API key
GEMINI_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key

# LLM Provider (google or openrouter)
DEFAULT_LLM_PROVIDER=google
DEFAULT_LLM_MODEL=gemini-2.5-flash-lite

# Optional: Translation Service (DeepL)
DEEPL_API_KEY=your_deepl_key:fx
DEEPL_API_TIER=free
DEEPL_ENABLED=true

# Debug mode (true/false)
DEBUG=false
```

### Port Configuration

By default, the app runs on port 80. To change this, edit `docker-compose.yml`:

```yaml
frontend:
  ports:
    - "3000:80"  # Change 3000 to your preferred port
```

Then access at: `http://localhost:3000`

---

## Data Persistence

Your data is automatically saved in a Docker volume:

- **Timelines & Generations**: SQLite database
- **Audio Files**: Generated TTS audio
- **Configuration**: LLM and translation settings

Data survives:
- Container restarts
- Application updates
- System reboots

### Backup Your Data

```bash
# Create backup
docker run --rm -v deviation_data:/data -v $(pwd):/backup alpine tar czf /backup/deviation_backup.tar.gz -C /data .

# Restore backup
docker run --rm -v deviation_data:/data -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/deviation_backup.tar.gz"
```

### Reset Data (Start Fresh)

```bash
docker-compose down -v
docker-compose up -d
```

**Warning**: This deletes all your timelines!

---

## Troubleshooting

### "Cannot connect to Docker daemon"

Docker Desktop is not running. Start Docker Desktop and wait for it to fully initialize.

### "Port 80 already in use"

Another application is using port 80. Change the port in `docker-compose.yml`:

```yaml
frontend:
  ports:
    - "8080:80"  # Use port 8080 instead
```

### "API key not working"

1. Check that your API key is correct in `.env`
2. Ensure there are no extra spaces or quotes
3. Restart the containers:
   ```bash
   docker-compose restart
   ```

### "Build failed"

Try clearing Docker cache:

```bash
docker-compose down
docker system prune -f
docker-compose up -d --build
```

### "Containers won't start"

Check disk space:
```bash
docker system df
```

Clean up if needed:
```bash
docker system prune -a
```

### "Generation times out"

AI generation can take 2-4 minutes. If timeouts persist:

1. Check your internet connection
2. Verify API key is valid
3. Try a different LLM provider

---

## Advanced Usage

### Running on a Server

For hosting on a remote server:

1. Edit `docker-compose.yml`:
   ```yaml
   frontend:
     build:
       args:
         - VITE_API_URL=http://your-server-ip:8000
   ```

2. Open firewall ports:
   ```bash
   sudo ufw allow 80
   ```

3. Rebuild:
   ```bash
   docker-compose up -d --build
   ```

### Resource Limits

Add resource limits in `docker-compose.yml`:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

---

## System Requirements

**Minimum:**
- 4 GB RAM
- 2 CPU cores
- 10 GB disk space
- Docker Desktop installed

**Recommended:**
- 8 GB RAM
- 4 CPU cores
- 20 GB disk space (for audio files)

---

## Getting Help

- **Issues**: https://github.com/szilac/DeviationEngine/issues
- **User Guide**: See `docs/USER_GUIDE.md`
- **API Documentation**: http://localhost:8000/docs (when running)

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start application |
| `docker-compose down` | Stop application |
| `docker-compose restart` | Restart application |
| `docker-compose logs` | View logs |
| `docker-compose ps` | Check status |
| `docker-compose up -d --build` | Rebuild and start |

---

**Enjoy exploring alternate histories!**
