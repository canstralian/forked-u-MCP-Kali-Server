# MCP Kali Server (Forked)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) 
[![CodeQL](https://github.com/canstralian/forked-u-MCP-Kali-Server/actions/workflows/codeql.yml/badge.svg)](https://github.com/canstralian/forked-u-MCP-Kali-Server/security/code-scanning)
[![Architecture](https://img.shields.io/badge/Architecture-MCP%20Server-blue)](https://github.com/canstralian/forked-u-MCP-Kali-Server)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-enabled-blue)](https://www.docker.com/)

**Fork Notice:**  
This repository is a fork of [Wh0am123/MCP-Kali-Server](https://github.com/Wh0am123/MCP-Kali-Server).  
While it inherits the original structure and features, this fork will evolve in a **new direction**, focusing on expanded AI integrations, multi-agent orchestration, and extended security automation.

**Purpose of the Fork:**  
- Modernize and extend AI-assisted penetration testing capabilities.  
- Introduce more flexible MCP server integrations (HuggingFace, GitHub, Notion).  
- Improve automation for CTF challenges, recon, and exploitation workflows.  
- Maintain schema-compliant MCP client/server interaction while enhancing functionality.

---

## 🔍 Use Case

The original MCP functionality allowed AI-driven offensive security testing by:  

- Interacting with AI endpoints like OpenAI, Claude, DeepSeek, or other models.  
- Exposing an API to execute commands on a Kali Linux machine.  
- Automating recon, exploitation, and solving CTF web challenges.  
- Sending custom requests (e.g., curl, nmap, ffuf) and receiving structured outputs.  

**This fork will expand the direction of the project to include:**  

- Enhanced automation for security workflows beyond standard terminal commands.  
- Extended integrations with additional AI models and services.  
- Improved orchestration for multi-agent scenarios and collaborative testing.  
- Streamlined pipelines for penetration testing, CTF solving, and ethical hacking exercises.

---

## 🚀 Features

The original repository included:

- 🧠 **AI Endpoint Integration:** Connect Kali to any MCP client like Claude Desktop or 5ire.  
- 🖥️ **Command Execution API:** Controlled API to execute terminal commands on Kali Linux.  
- 🕸️ **Web Challenge Support:** AI-assisted interaction with web apps, APIs, and capture of flags.  
- 🔐 **Designed for Offensive Security Professionals:** Ideal for red teamers, bug bounty hunters, or CTF players automating common tasks.  

**Future features in this fork will focus on:**  

- Multi-agent orchestration and intelligent task delegation.  
- Integration with cloud-based AI endpoints and model pipelines.  
- Enhanced logging, analytics, and structured output for automation workflows.  
- Additional security tooling, including forensic and analysis utilities.

---

## 🛠️ Installation

**On the Linux machine (MCP Server):**

```bash
git clone https://github.com/YourUsername/MCP-Kali-Server.git
cd MCP-Kali-Server
python3 kali_server.py

On your MCP Client (Windows or Linux):

python3 /absolute/path/to/mcp_server.py http://LINUX_IP:5000

Claude Desktop Configuration (claude_desktop_config.json):

{
  "mcpServers": {
    "kali_mcp": {
      "command": "python3",
      "args": [
        "/absolute/path/to/mcp_server.py",
        "--server",
        "http://LINUX_IP:5000/"
      ]
    }
  }
}

5ire Desktop Application:
	•	Add an MCP with the command python3 /absolute/path/to/mcp_server.py http://LINUX_IP:5000 and the app will generate the needed configuration automatically.

⸻

🔮 Extended Possibilities

The AI-driven terminal opens up more potential beyond the original features:
	•	Memory Forensics (Volatility): Automate memory analysis tasks like process enumeration, DLL injection checks, and registry extraction from memory dumps.
	•	Disk Forensics (SleuthKit): Automate analysis from disk images, timeline generation, file carving, and hash comparisons.
	•	Custom AI Workflows: The fork will explore automated multi-step AI-driven security workflows, integrating multiple tools in a single pipeline.

⸻

⚠️ Disclaimer

This project is intended solely for educational and ethical testing purposes. Any misuse — including unauthorized access, exploitation, or malicious activity — is strictly prohibited. The author assumes no responsibility for misuse.

