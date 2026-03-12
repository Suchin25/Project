# Project Rules

- Never create a component longer than 150 lines. If it exceeds this, split it into smaller components automatically.
- Always separate UI from logic.

---

## Project Description and Goals

**BuildFast** is an AI-powered startup idea analyzer. Users submit a startup idea in plain text and receive a structured, expert-level analysis covering market opportunity, competitive landscape, risks, scoring, and actionable next steps.

**Goals:**
- Help founders and builders quickly validate or stress-test startup ideas
- Provide honest, critical analysis (not generic encouragement)
- Deliver results in a structured, readable format via a clean web UI

---

## Current Status / What's Been Done

- Flask backend with a single `/analyze` POST endpoint
- Streaming SSE response from the Claude API (`claude-opus-4-6`)
- Structured JSON analysis returned: summary, market, red flags, score breakdown, next steps
- System prompt engineered to enforce consistent JSON output and critical analysis tone
- Frontend template (`index.html`) scaffolded
- CORS enabled for local dev
- Environment-based API key loading via `python-dotenv`

---

## What's Left To Do

- Build out the `index.html` frontend UI (form input, results rendering, score visualizations)
- Handle streaming progress states in the UI (loading, thinking, done)
- Add input validation and user-friendly error messages on the frontend
- Style the results: score breakdown, red flags list, next steps cards
- Add tests for the `/analyze` endpoint
- Consider rate limiting and abuse prevention before any public deployment

---

## Key Decisions Made and Why

- **Streaming via SSE**: Provides a responsive feel while the model thinks; avoids long hanging requests
- **Adaptive thinking (`"type": "adaptive"`)**: Lets Claude decide when extended reasoning is warranted, balancing quality and speed
- **Strict JSON system prompt**: Enforces consistent output structure so the frontend can reliably parse and render results without fragile string parsing
- **`claude-opus-4-6` model**: Chosen for strongest reasoning quality on complex business analysis tasks
- **Flask over FastAPI**: Simpler setup for a small single-purpose app; no async complexity needed

---

## Tech Stack

| Layer       | Choice              | Reason                                              |
|-------------|---------------------|-----------------------------------------------------|
| Backend     | Python / Flask      | Lightweight, fast to set up, good SSE support       |
| AI          | Anthropic Claude API (`anthropic` SDK) | Best-in-class reasoning for structured analysis |
| Frontend    | HTML/CSS/JS (Jinja2 templates) | No framework overhead for a focused single-page tool |
| Streaming   | Server-Sent Events (SSE) | Simple, native browser support, no WebSocket needed |
| Config      | `python-dotenv`     | Standard env var management for API keys            |
| CORS        | `flask-cors`        | Enables local frontend/backend dev flexibility      |
