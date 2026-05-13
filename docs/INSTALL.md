# Installation Guide

## Prerequisites

- Hermes Agent v0.12.0+ (supports custom skills and cron)
- DeepSeek API key (for pattern-cluster semantic clustering)
- Python 3.10+

## Install (Choose One)

### Option 1: As a Hermes Custom Skill

```bash
# Clone to skills directory
cd ~/.hermes/skills/custom/
git clone https://github.com/Hwaiming/Hermes-self-cultivation-engine.git

# Create your self continuity file (from template)
cp Hermes-self-cultivation-engine/engine/templates/self-file-template.md \
  ~/.hermes/agent.self.md
# Edit agent.self.md with your core identity

# Load core principles into your SOUL.md
# Either: inject engine/core/three-principles.md content into your system prompt
# Or: add reference bridges like:
#   "Load principles: skill_view('custom/self-cultivation-engine/engine/core/three-principles')"
```

### Option 2: Standalone (No Hermes)

```bash
# Clone anywhere
cd ~/
git clone https://github.com/Hwaiming/Hermes-self-cultivation-engine.git

# Copy template
cp self-cultivation-engine/engine/templates/self-file-template.md ./agent.self.md

# Set environment variables
export SELF_CULTIVATION_HOME=~/self-cultivation-engine/engine
export ENGINES_SELF_FILE=~/agent.self.md

# Run health check
python3 self-cultivation-engine/engine/scripts/self-repair.py
```

### Option 3: Docker (Planned)

```
# Coming soon
```

## Configure Cron Tasks

### Weekly Health Check

```bash
hermes cron create --pattern "0 5 * * 0" \
  --script ~/.hermes/skills/custom/self-cultivation-engine/engine/scripts/self-repair.py \
  --name "self-cultivation-repair"
```

### Daily Pattern Clustering (needs DeepSeek API key)

```bash
hermes cron create --pattern "0 6 * * *" \
  --script ~/.hermes/skills/custom/self-cultivation-engine/engine/scripts/pattern-cluster.py \
  --name "pattern-cluster-daily"
```

## Verify Installation

```bash
python3 path/to/engine/scripts/self-repair.py
# Should see all 8 checks pass
```
