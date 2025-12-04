# Full Website Captures

![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)

A powerful web application that captures full-page screenshots of entire websites. Simply enter a URL and let the app automatically discover and screenshot all pages—perfect for archiving, design reviews, competitive analysis, or documentation.

## ✨ Features

- 🌐 **Modern Web Interface** — Clean, minimalist dark UI with real-time progress updates
- 📸 **Full-Page Screenshots** — Captures complete page content including lazy-loaded images
- 🗺️ **Sitemap Mode** — Fast page discovery using sitemap.xml
- 🕷️ **Crawl Mode** — Discover pages by following links (works without sitemap)
- 🖥️📱 **Multi-Viewport** — Capture in desktop (1920×1080), mobile (390×844), or **both at once**
- 📦 **Batch Download** — Download all screenshots as a ZIP file
- 🔄 **Real-time Progress** — Live progress bar updates via WebSocket
- 🖼️ **Gallery View** — Browse captured screenshots in a beautiful grid layout
- 🐳 **Docker Ready** — Production-ready Docker and Docker Compose configuration

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Mihai-Bogdan-Robert/Full-Website-Captures.git
cd Full-Website-Captures

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
python -m playwright install chromium

# Start the web server
python app.py
```

Open **http://localhost:5001** in your browser.

---

## 🐳 Docker Deployment

```bash
# Using Docker Compose (recommended)
docker-compose up --build

# Or using Docker directly
docker build -t full-website-captures .
docker run -p 5001:5001 -v $(pwd)/screenshots:/app/screenshots full-website-captures
```

---

## ▶️ How It Works

1. **Enter URL** — Input any website URL
2. **Choose Mode** — Sitemap (fast) or Crawl (discovers all links)
3. **Select Viewport** — Desktop, Mobile, or Both
4. **Set Limit** — Configure maximum pages to capture
5. **Start Capture** — Watch real-time progress as pages are captured
6. **Download** — Get all screenshots as a ZIP file

---

## 📁 Project Structure

```
├── app.py              # Flask web application with WebSocket support
├── main.py             # Core screenshot & crawling functionality
├── gui.py              # Legacy desktop GUI (tkinter)
├── templates/
│   └── index.html      # Modern dark-theme web interface
├── screenshots/        # Output directory for captures
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Docker Compose setup
└── requirements.txt    # Python dependencies
```

---

## 🧩 Tech Stack

- **Flask** + **Flask-SocketIO** — Web framework with real-time updates
- **Playwright** — Headless browser automation
- **TailwindCSS** — Modern utility-first CSS
- **BeautifulSoup** — HTML parsing for crawl mode

---

## ⚙️ Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| Mode | Sitemap / Crawl | Page discovery method |
| Viewport | Desktop / Mobile / Both | Screenshot dimensions |
| Max Pages | 1-500 | Limit number of captures |

---

## 📄 License

This project is licensed under **CC BY-NC-ND 4.0** (Creative Commons Attribution-NonCommercial-NoDerivatives).

**You may:**
- ✅ Use this software for personal, non-commercial purposes
- ✅ Share the software with proper attribution

**You may NOT:**
- ❌ Sell this software or use it commercially
- ❌ Use it in any commercial product or service
- ❌ Distribute modified versions

See [LICENSE](LICENSE) for full details.

---

## 👤 Author

**Mihai-Bogdan-Robert**

For commercial licensing inquiries, please contact the author.
