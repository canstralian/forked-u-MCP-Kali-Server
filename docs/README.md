# Documentation & Visualization

This directory contains documentation and visualization tools for the MCP Kali Server project.

## Wireless Stack Dashboard

**File:** `wireless-stack-dashboard.html`

An interactive cyberpunk-themed dashboard for analyzing the wireless attack stack capabilities of Kali Linux tools.

### Features

- **KPI Dashboard**: High-level metrics showing tool counts, primary focus areas, and critical gaps
- **Capability Radar Chart**: Visual comparison of current capabilities vs. target profile across different attack vectors (WPA, WPS, BLE, SDR, RFID)
- **Stack Composition**: Donut chart showing the ratio of Tier 1 (Core Offensive) vs. Tier 2 (Support) tools
- **Attack Target Analysis**: Bar chart visualizing which attack vectors have the most tool coverage
- **Interactive Tool Matrix**: Filterable grid of all wireless tools with detailed information:
  - Function description
  - Attack targets
  - Tool components
  - Tier classification
- **Operational Workflow**: Visual flow showing the progression from preparation (Tier 2) to execution and resolution (Tier 1)
- **Gap Analysis**: Highlighting missing capabilities in SDR/RF, BLE/Bluetooth, and RFID/NFC domains

### Usage

Simply open the HTML file in any modern web browser:

```bash
# From the docs directory
open wireless-stack-dashboard.html

# Or using a specific browser
firefox wireless-stack-dashboard.html
chromium wireless-stack-dashboard.html
```

No additional dependencies or server setup required - all assets are loaded from CDNs:
- TailwindCSS for styling
- Chart.js for data visualization
- Google Fonts for typography

### Tool Coverage

The dashboard analyzes 10 tools across 2 tiers:

**Tier 1 - Core Offensive Tools (6):**
- aircrack-ng suite
- wifite
- reaver/bully
- airgeddon
- wifiphisher
- wifipumpkin3

**Tier 2 - Support Utilities (4):**
- macchanger
- fern-wifi-cracker
- bettercap
- chirp

### Identified Gaps

The analysis reveals three critical capability gaps:

1. **SDR/Active RF**: Missing gnuradio, hackrf_tools, rfcat, gr-gsm
2. **BLE/Bluetooth**: Missing bleah, crackle, gatttool
3. **RFID/NFC**: Missing mfcuk, mfoc, proxmark3 utilities

### Design

The dashboard uses a cyberpunk neon aesthetic with:
- Dark slate background (#0f172a)
- Cyan accent (#22d3ee) for Tier 1/primary actions
- Purple accent (#c084fc) for Tier 2/secondary elements
- Pink accent (#f472b6) for attack vectors
- Red accent (#ef4444) for gaps and warnings

The interface is fully responsive and works on desktop, tablet, and mobile devices.

---

**Note**: This is an analytical tool for understanding the wireless security testing capabilities. For actual tool usage, refer to the main project documentation and ensure you have proper authorization for any security testing activities.
