# Promotion kit

Ready-to-paste copy for getting scanner-mcp in front of people. Nothing here posts
automatically — pick what you want and I (or you) can submit it.

---

## 1. awesome-mcp-servers list entries

**[punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)**
(icons: 🐍 Python · 🏠 local · 🪟 Windows · 🐧 Linux · 🍎 macOS). Best-fit section:
**🖥️ OS Automation**.

```markdown
- [AminHA1248/scanner-mcp](https://github.com/AminHA1248/scanner-mcp) 🐍 🏠 🪟 🐧 🍎 - Let Claude scan and read paper documents from any USB or network scanner (eSCL/AirScan, WIA, SANE, TWAIN)
```

**[wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers)** (plainer format):

```markdown
- [scanner-mcp](https://github.com/AminHA1248/scanner-mcp) - Scan and read paper documents from any USB or network scanner (eSCL, WIA, SANE, TWAIN)
```

**Directory sites that also accept submissions:** mcp.so, Glama, Smithery, PulseMCP,
mcpservers.org. Most have a "submit" form and take the same one-line description.

---

## 2. Show HN

**Title:**
```
Show HN: Scanner MCP – let Claude scan and read paper documents
```

**Body:**
```
I wanted Claude to be able to read a physical document, so I built an MCP server
that exposes scan tools to any scanner Claude can reach.

It's generic on purpose — instead of vendor SDKs it targets the standard interfaces
each scanner category already exposes:
- eSCL / AirScan / Mopria for network scanners (driverless, cross-platform)
- WIA on Windows and SANE on Linux/macOS for USB
- TWAIN on Windows for older units with no usable WIA driver

Ask Claude "scan my document and read it" — it calls scan_document, and the page
comes back as an inline image Claude reads directly (or OCR'd, or saved as PDF).

Honest status: eSCL + WIA are tested on real hardware (a Canon TS3400); SANE and
TWAIN are written to the standard interfaces but not yet hardware-verified.

Repo (MIT): https://github.com/AminHA1248/scanner-mcp
```

---

## 3. Reddit — r/ClaudeAI and r/mcp

**Title:**
```
I built an MCP server that lets Claude scan and read paper documents
```

**Body:**
```
Sharing a weekend project: an MCP server that gives Claude a scan_document tool.
Put a page on your scanner, ask Claude to "scan and read it," and it reads the page
back (inline image, or OCR to text, or save a PDF).

It's driverless where it can be — eSCL/AirScan for network scanners, WIA for Windows
USB, SANE for Linux/macOS, TWAIN for older Windows scanners. One pip install, one line
in your Claude Desktop config.

Tested end-to-end on a Canon TS3400. MIT licensed, feedback welcome:
https://github.com/AminHA1248/scanner-mcp
```

Reddit etiquette: post as "I built…", reply to comments, don't cross-post the same
text to five subs at once. r/ClaudeAI and r/mcp are the on-topic homes.

---

## 4. Sequencing (do this order)

1. Publish to PyPI so every link can say `pip install scanner-mcp` (see README/workflow).
2. Submit the awesome-mcp PRs (durable, targeted traffic).
3. Post Show HN once, mid-morning US time; then the Reddit posts.
4. Watch GitHub → Insights → Traffic → Referrers and lean into whatever converts.
