# CLAUDE.md - Pulsar Sentinel Project Context

> **Last Updated:** February 13, 2026
> **Version:** 2.1
> **Owner:** Shane Brazelton (SRM Dispatch, Alabama)
> **Repo:** github.com/thebardchat/pulsar_sentinel

---

## Quick Start

```bash
# Start Weaviate (from weaviate-config folder)
cd D:\Angel_Cloud\shanebrain-core\weaviate-config
docker-compose up -d

# Run ShaneBrain Agent
python langchain-chains/shanebrain_agent.py

# Run Angel Cloud CLI (Interactive)
python langchain-chains/angel_cloud_cli.py
```

---

## Current Status (January 11, 2026)

| Component | Status | Notes |
|-----------|--------|-------|
| Ollama LLM | ✅ Installed | v0.13.5, using `llama3.2:1b` (1.3GB - fits 8GB RAM) |
| Weaviate | ✅ Connected | localhost:8080, v1.28.0 |
| LangChain | ✅ Installed | langchain, langchain-ollama, langchain-community |
| Python Deps | ✅ Installed | weaviate-client v4, pymongo, rich, prompt_toolkit |
| Crisis Detection | ✅ Enabled | Integrated into Angel Cloud CLI |
| Docker | ✅ Running | shanebrain-weaviate, shanebrain-qna containers |

**Known Limitation:** 8GB RAM system - using `llama3.2:1b` instead of larger 3B model.

---

## Project Vision

**ShaneBrain** = Central AI orchestrator for the entire ecosystem:
- **Angel Cloud** - Mental wellness platform (named for daughter-in-law Angel)
- **Pulsar AI** - Blockchain security layer (eventually Pulsar Sentinel)
- **Legacy AI** - Personal "TheirNameBrain" for each user's family legacy
- **LogiBot** - Business automation for SRM Dispatch

**Mission:** Serve 800 million Windows users losing security updates with affordable, secure AI infrastructure.

---

## File Structure

```
D:\Angel_Cloud\shanebrain-core\
├── .env                          # Credentials (NEVER commit)
├── requirements.txt              # Python dependencies
├── langchain-chains/
│   ├── shanebrain_agent.py       # Central agent (CHAT, MEMORY, WELLNESS, SECURITY, DISPATCH, CODE modes)
│   ├── angel_cloud_cli.py        # Interactive CLI for mental wellness
│   ├── crisis_detection_chain.py # Mental health crisis detection
│   ├── qa_retrieval_chain.py     # RAG-based question answering
│   └── code_generation_chain.py  # Code generation support
├── weaviate-config/
│   ├── docker-compose.yml        # Weaviate + transformers containers
│   ├── data/                     # Persistent vector database storage
│   └── schemas/
│       ├── shanebrain-memory.json
│       ├── angel-cloud-conversations.json
│       └── pulsar-security-events.json
├── mongodb-schemas/
│   ├── conversations.json
│   ├── user_sessions.json
│   └── crisis_logs.json
├── planning-system/
│   ├── templates/                # Planning templates (tracked in git)
│   └── active-projects/          # Personal project data (gitignored)
├── scripts/
│   ├── start-shanebrain.bat      # Master launcher script
│   ├── health_check.py           # System health verification
│   └── setup_credentials.py      # Credential management
└── angel-cloud/
    ├── docs/
    │   └── crisis-intervention-flow.md
    ├── config/
    │   └── crisis-settings.json
    └── modules/
        └── crisis-handler.py
```

---

## Common Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Start/Stop Services
```bash
# Start Weaviate
cd weaviate-config && docker-compose up -d

# Stop Weaviate
cd weaviate-config && docker-compose down

# View Weaviate logs
docker logs shanebrain-weaviate -f
```

### Ollama (Local LLM)
```bash
# Check Ollama status
ollama list

# Pull the lightweight model (for 8GB RAM systems)
ollama pull llama3.2:1b

# Pull the larger model (needs 16GB+ RAM)
ollama pull llama3.2

# Run Ollama server
ollama serve
```

### Health Check
```bash
python scripts/health_check.py
```

### Verify Credentials
```bash
python scripts/setup_credentials.py --verify
```

---

## Agent Modes

The ShaneBrain agent supports multiple operational modes:

| Mode | Purpose | Trigger |
|------|---------|---------|
| `CHAT` | General conversation | Default |
| `MEMORY` | Shane's knowledge/legacy retrieval | "Tell me about Shane's..." |
| `WELLNESS` | Angel Cloud mental health support | Emotional/mental health queries |
| `SECURITY` | Pulsar AI threat detection | Security/blockchain analysis |
| `DISPATCH` | SRM trucking operations | Logistics/dispatch queries |
| `CODE` | Code generation/debugging | Programming tasks |

---

## Angel Cloud CLI Commands

```
/help    - Show available commands
/status  - System health check
/crisis  - Test crisis detection
/mode    - Switch agent modes
/clear   - Clear screen
/exit    - Exit CLI
```

---

## Architecture

### Core Components

1. **Ollama LLM** (localhost:11434)
   - Local LLM inference via Ollama
   - Default model: `llama3.2:1b` (for 8GB RAM systems)
   - Configured via `OLLAMA_HOST` and `OLLAMA_MODEL` env vars

2. **Weaviate Vector Database** (localhost:8080)
   - Requires Weaviate 1.27.0+ for Python client v4 compatibility
   - Local embeddings via `text2vec-transformers` (sentence-transformers-all-MiniLM-L6-v2)
   - QnA module via `qna-transformers`
   - Data persisted in `weaviate-config/data/`
   - Docker containers: `shanebrain-weaviate`, `shanebrain-t2v`, `shanebrain-qna`

3. **LangChain Chains** (`langchain-chains/`)
   - `shanebrain_agent.py` - Central agent integrating all components
   - `angel_cloud_cli.py` - Interactive CLI for Angel Cloud
   - `crisis_detection_chain.py` - Mental health crisis detection
   - `qa_retrieval_chain.py` - RAG-based question answering
   - `code_generation_chain.py` - Code generation support

4. **Planning System** (`planning-system/`)
   - Markdown-based persistent planning for multi-session continuity
   - Templates in `templates/` (tracked in git)
   - Active projects in `active-projects/` (gitignored)
   - Checkbox markers: `[ ]` not started, `[x]` completed, `[~]` in progress, `[!]` blocked

5. **MongoDB Schemas** (`mongodb-schemas/`)
   - `conversations.json`, `user_sessions.json`, `crisis_logs.json`

6. **Weaviate Schemas** (`weaviate-config/schemas/`)
   - `shanebrain-memory.json` - Shane's personal knowledge/legacy
   - `angel-cloud-conversations.json` - User mental wellness data
   - `pulsar-security-events.json` - Security threat patterns

---

## Multi-Project Support

This repository supports multiple AI projects under the ShaneBrain umbrella:

| Project | Description | Status |
|---------|-------------|--------|
| ShaneBrain Core | Central orchestration layer | ✅ Active |
| Angel Cloud | Mental wellness platform | 🔨 Building |
| Pulsar AI | Blockchain security | 📋 Planned |
| Pulsar Sentinel | Advanced threat detection | 📋 Planned |
| Legacy AI | Personal family legacy system | 📋 Planned |
| LogiBot | SRM Dispatch automation | 📋 Planned |

---

## Environment Variables

Required in `.env`:
```env
# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=your-api-key-if-using-cloud

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# MongoDB (when enabled)
MONGODB_URI=mongodb+srv://...

# Crisis Intervention (Twilio)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=+1...
```

---

## Security Reminders

- ⚠️ NEVER commit `.env` files
- ⚠️ NEVER paste connection strings in chat
- ⚠️ Keep repo PRIVATE until production ready
- ⚠️ Use Tailscale for remote access, not port forwarding
- ⚠️ Crisis logs store metadata only (privacy protection)

---

## Git Workflow

```bash
# Status check
git status

# Stage and commit
git add .
git commit -m "descriptive message"

# Push to GitHub
git push origin main
```

**Rules:**
- Commit frequently
- Push after every session
- Use descriptive commit messages
- Never let work go unpushed

---

## Troubleshooting

### Docker Not Running
```cmd
# Start Docker Desktop, then:
docker-compose up -d
```

### Weaviate Connection Failed
```bash
# Check container status
docker ps

# View logs
docker logs shanebrain-weaviate
```

### Ollama Not Responding
```bash
# Restart Ollama
ollama serve

# Check if model is pulled
ollama list
```

### Out of Memory (8GB RAM)
- Use `llama3.2:1b` instead of `llama3.2`
- Consider stopping other applications
- t2v-transformer may fail on low RAM - use Ollama for embeddings instead

---

## Ports Reference

| Service | Port | Protocol |
|---------|------|----------|
| Weaviate REST | 8080 | HTTP |
| Weaviate gRPC | 50051 | gRPC |
| Ollama | 11434 | HTTP |
| MongoDB | 27017 | TCP |
| Open WebUI | 3000 | HTTP |

---

## External Resources

- **GitHub Repo:** https://github.com/thebardchat/shanebrain-core
- **Weaviate Docs:** https://weaviate.io/developers/weaviate
- **LangChain Docs:** https://python.langchain.com
- **Ollama Docs:** https://ollama.com/library

---

## Shane's Development Philosophy

1. **"File structure first"** - Always establish directory architecture before coding
2. **"Load my RAG files"** - Simple commands over complex file names
3. **Action over theory** - Build, don't just plan
4. **Family-first** - All projects serve the family's future
5. **ADHD as superpower** - Parallel processing, rapid context switching
6. **No fluff** - Direct solutions, minimal explanation

---

## Next Steps (TODO)

- [ ] Complete Angel Cloud MVP with user authentication
- [ ] Implement full crisis intervention flow with Twilio integration
- [ ] Set up MongoDB Atlas for conversation persistence
- [ ] Build user progression system (New Born → Angel)
- [ ] Integrate Pulsar AI blockchain security layer
- [ ] Create "Legendary Sticks" USB distribution for family
- [ ] Develop mobile access via Tailscale + Open WebUI

---

## Contact

**Owner:** Shane  
**Company:** SRM Dispatch (Alabama)  
**Project:** Angel Cloud Ecosystem  
**Mission:** 800 million users. Digital legacy for generations.
