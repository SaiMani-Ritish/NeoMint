# Ritish's Task List — Outside Cursor

> Everything here is YOUR manual work. Phases 3–5 code will be built for you in Cursor.
> Last updated: March 17, 2026

---

## Current Status at a Glance

| Phase | What | Status |
|-------|------|--------|
| 1 | MCP Server | Done |
| 2 | Fine-tuning + Datasets | Training running on Colab now |
| 3 | Agentic Loop (agent/) | Will be built in Cursor |
| 4 | Overlay UI (overlay-ui/) | Will be built in Cursor |
| 5 | Evaluation + Capstone Paper | Will be built in Cursor |

---

## STEP 1 — Monitor the Colab Training (RIGHT NOW)

You have `train.ipynb` running on a T4 GPU. Here's what to watch for:

### 1a. While cells are executing

- **Cell 16 (Training)** is the long one — it runs 3 epochs and takes ~15–30 minutes.
- Watch the training logs. You should see output every 5 steps like:
  ```
  {'loss': 1.234, 'learning_rate': 0.0002, 'epoch': 0.5}
  ```
- The loss should **decrease over time**. Typical range:
  - Start: ~1.5–2.0
  - End: ~0.3–0.8
- If loss goes to `nan` or spikes wildly, the training failed — restart the runtime and re-run.

### 1b. When training finishes (Cell 16 completes)

Write down these numbers from the output — you need them for the capstone paper:

- [ ] **Training loss** (final value)
- [ ] **Total steps**
- [ ] **Training runtime** (in seconds)
- [ ] **Peak GPU memory** (in GB)

### 1c. Check the test outputs (Cell 18)

Cell 18 runs 5 test prompts. Read each response and verify:

- [ ] "List all files in my Documents folder" → should output a `tool_call` with `list_files`
- [ ] "How much disk space do I have left?" → should output a `tool_call` with `run_command` using `df`
- [ ] "Open Firefox" → should output a `tool_call` with `open_application`
- [ ] "Read my notes.txt and save a summary" → should be a multi-step response
- [ ] "What's on my clipboard?" → should output a `tool_call` with `get_clipboard`

If the model is NOT generating `tool_call` blocks and instead just writing plain text
answers, the fine-tuning didn't work well. Take a screenshot of the outputs either way.

---

## STEP 2 — Download Files from Colab

After all cells complete, Colab will auto-trigger downloads. Make sure you get:

- [ ] **`neomint-3b-unsloth-Q4_K_M.gguf`** (~1.8 GB) — this is the model
- [ ] **`training_summary.json`** — training metrics for the paper

If the auto-download doesn't trigger (common with large files), manually download:
1. Click the folder icon (📁) in the left sidebar of Colab
2. Navigate to find `neomint-3b-unsloth-Q4_K_M.gguf`
3. Right-click → Download

**Alternative for large files:** If the browser download keeps failing:
```python
# Run this in a new Colab cell
from google.colab import drive
drive.mount('/content/drive')
!cp neomint-3b-unsloth-Q4_K_M.gguf /content/drive/MyDrive/
!cp training_summary.json /content/drive/MyDrive/
```
Then download from Google Drive on your local machine.

### Save a copy of the LoRA adapters too (optional but recommended)

```python
# In Colab — zip and download the LoRA adapter directory
!zip -r neomint-3b-lora.zip neomint-3b-lora/
files.download("neomint-3b-lora.zip")
```

---

## STEP 3 — Set Up Your Linux Mint Machine

This is where the model actually runs. You need a Linux Mint machine (physical or VM)
with at least 16 GB RAM.

### 3a. Clone the repo on Linux Mint

```bash
git clone https://github.com/YOUR-USERNAME/neomint-os.git
cd neomint-os
```

Or if you're transferring the repo manually (USB/SCP):
```bash
# From your Windows machine to your Linux Mint machine
scp -r /path/to/NeoMint user@linux-mint-ip:~/neomint-os/
```

### 3b. Copy the GGUF file into the repo root

The GGUF file must be in the same directory as `neomint.modelfile`:

```bash
cp ~/Downloads/neomint-3b-unsloth-Q4_K_M.gguf ~/neomint-os/
```

Verify it's in the right place:
```bash
ls -lh ~/neomint-os/neomint-3b-unsloth-Q4_K_M.gguf
# Should show ~1.8 GB
```

### 3c. Run the installer

```bash
cd ~/neomint-os
chmod +x install.sh
./install.sh
```

This will:
1. Install system dependencies (curl, git, xclip, xdotool, etc.)
2. Ensure Python 3.11+ is available
3. Install Ollama and start its service
4. Pull the base Qwen2.5:3B model (as a fallback)
5. Set up the MCP server virtual environment
6. Skip Phase 3–5 components (not built yet — that's fine)
7. Run smoke tests

**Expected time:** ~10–15 minutes (mostly model download)

If `install.sh` fails at any step, note the exact error message and the step it failed on.

---

## STEP 4 — Load NeoMint-3B into Ollama

After `install.sh` succeeds and Ollama is running:

```bash
cd ~/neomint-os

# Create the custom model from your fine-tuned GGUF
ollama create neomint-3b -f neomint.modelfile
```

This should take 1–2 minutes. If it succeeds, you'll see:
```
transferring model data
creating model layer
writing manifest
success
```

### Verify the model is loaded

```bash
ollama list
```

You should see `neomint-3b` in the list with a size around 1.8 GB.

---

## STEP 5 — Test the Model Manually

Run an interactive session:

```bash
ollama run neomint-3b
```

Then type these test prompts one by one and note the responses:

| # | Prompt to type | What you want to see |
|---|----------------|----------------------|
| 1 | `List all files in my home directory` | A `tool_call` block with `list_files` |
| 2 | `What's my disk usage?` | A `tool_call` block with `run_command` using `df -h` |
| 3 | `Open Firefox for me` | A `tool_call` block with `open_application` |
| 4 | `What's the current date and time?` | A `tool_call` block with `run_command` using `date` |
| 5 | `Read the file /etc/hostname` | A `tool_call` block with `read_file` |

### Record your results

For each prompt, note:

- [ ] Did it generate a `tool_call` block? (yes/no)
- [ ] Was the tool name correct? (yes/no)
- [ ] Were the arguments reasonable? (yes/no)
- [ ] Any hallucinated/wrong behavior?

**Take screenshots** — you'll need these for the capstone paper's evaluation section.

### If the model gives bad responses

If it's just generating plain text instead of tool calls, the fine-tuning may need
more data or more epochs. Come back to Cursor and we'll adjust.

---

## STEP 6 — Copy `training_summary.json` into the Repo

Put the training summary where the evaluation suite can find it:

```bash
cp ~/Downloads/training_summary.json ~/neomint-os/fine-tuning/
```

Also, push everything to Git:

```bash
cd ~/neomint-os
git add fine-tuning/training_summary.json
git add neomint-3b-unsloth-Q4_K_M.gguf  # Only if you want it in the repo (1.8 GB!)
git commit -m "Add fine-tuned model and training summary"
```

> **Note on the GGUF file:** 1.8 GB is too large for regular GitHub. Options:
> - Add it to `.gitignore` and distribute separately
> - Use [Git LFS](https://git-lfs.github.com/) (recommended)
> - Host it on Hugging Face Hub and reference it in the install script

---

## STEP 7 — Things to Gather for the Capstone Paper

While I build Phases 3–5 in Cursor, start collecting this material:

### Screenshots needed
- [ ] Colab training loss curve (if visible in output)
- [ ] Colab training completion summary
- [ ] `ollama list` showing neomint-3b
- [ ] 3–5 sample model responses from `ollama run neomint-3b`
- [ ] The overlay UI in action (after Phase 4 is built)

### Numbers to record
- [ ] Training loss (final)
- [ ] Training time (seconds)
- [ ] Peak GPU memory
- [ ] GGUF file size
- [ ] Number of training examples (should be 175)
- [ ] Model response latency on CPU (time from prompt to first token in `ollama run`)

### References to start gathering (need 15+ for the paper)
The paper needs APA citations. Start finding these:

1. Ollama documentation — https://ollama.com
2. Unsloth GitHub — https://github.com/unslothai/unsloth
3. Qwen2.5 paper — https://arxiv.org/abs/2407.10671
4. LoRA paper — Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models" (2021)
5. MCP specification — https://modelcontextprotocol.io
6. Tauri v2 — https://v2.tauri.app
7. NL2Bash — Lin et al. (2018)
8. OSWorld benchmark — Xie et al. (2024)
9. AgentBench — Liu et al. (2023)
10. ShellGPT — https://github.com/TheR1D/shell_gpt
11. QLoRA paper — Dettmers et al. (2023)
12. GGUF format / llama.cpp — https://github.com/ggerganov/llama.cpp
13. Linux Mint — https://linuxmint.com
14. FastAPI — https://fastapi.tiangolo.com
15. Transformer architecture — Vaswani et al., "Attention Is All You Need" (2017)

---

## STEP 8 — After I Finish Building Phases 3–5

Once the remaining code is ready in Cursor, you'll need to:

### For Phase 3 (Agentic Loop)
- [ ] Pull the latest code to your Linux Mint machine
- [ ] Run `install.sh` again (it will detect and set up the agent module)
- [ ] Test the agent CLI: `cd agent && source .venv/bin/activate && python -m neomint_agent`
- [ ] Verify the agent can call MCP tools through the model

### For Phase 4 (Overlay UI)
- [ ] Install Rust toolchain on Linux Mint: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- [ ] Install Node.js 20: `curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs`
- [ ] Run `install.sh` again (it will build the Tauri app)
- [ ] Test Super+Space keybinding
- [ ] Take a screenshot/screen recording for the paper

### For Phase 5 (Evaluation)
- [ ] Run the benchmark suite on your Linux Mint machine (must be run there, not Windows)
- [ ] The benchmark needs the model running locally via Ollama
- [ ] Results will auto-generate into eval/results/
- [ ] The capstone paper will be auto-generated using these results

---

## Quick Reference — Commands You'll Run Most

```bash
# Check if Ollama is running
systemctl status ollama

# Start Ollama if it's not running
sudo systemctl start ollama

# Run NeoMint model interactively
ollama run neomint-3b

# Check model list
ollama list

# Re-create model after updating modelfile
ollama rm neomint-3b
ollama create neomint-3b -f neomint.modelfile

# Run MCP server tests
cd mcp-server && source .venv/bin/activate && pytest

# Run the full installer
cd ~/neomint-os && ./install.sh
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Colab disconnects mid-training | Re-run from Cell 2 (it reinstalls, but fast). Upload dataset again. |
| GGUF download fails in browser | Mount Google Drive in Colab, copy there, download from Drive |
| `ollama create` fails with "file not found" | Make sure the GGUF is in the same directory as `neomint.modelfile` |
| Model generates plain text, no tool_calls | Fine-tuning may need more epochs or data. Come back to Cursor. |
| `install.sh` fails on Python version | Run `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.11` manually |
| Ollama OOM (out of memory) | Close other apps. The 3B Q4 model needs ~3 GB RAM for inference. |
| Tauri build fails (Phase 4) | Make sure Rust and Node.js are installed. Check `cargo --version` and `node --version`. |
