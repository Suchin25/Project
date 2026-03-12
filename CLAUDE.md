# Project Rules

- Prefer components under 150 lines. If a component exceeds this, evaluate whether it contains distinct concerns (data fetching, sub-UI sections, reusable logic) and split at those natural boundaries. Always extract stateful logic into custom hooks. Don't split purely to meet a line count.
- Always separate UI from logic.

---

## Project Description and Goals

**TermSight** is an AI-powered term sheet analyzer. Users paste an investment term sheet (Series A equity, SAFE, convertible note, etc.) and receive a structured, plain-English analysis covering key terms, red flags, a founder-friendliness score, and prioritized negotiation recommendations.

**Goals:**
- Help founders understand term sheets without needing a lawyer for every clause
- Flag genuinely problematic terms (not generic risk warnings)
- Score founder-friendliness across five dimensions and explain what to push back on
- Deliver results in a clean, tabbed UI with visual score breakdowns

---

## Current Status / What's Been Done

- Flask backend with a single `/analyze` POST endpoint
- Streaming SSE response from the Claude API (`claude-opus-4-6`)
- Structured JSON returned: summary, key_terms, red_flags (with severity), score breakdown, recommendations
- System prompt engineered for VC/legal expertise and consistent JSON output
- Rate limiting: 10 requests/minute per IP via `flask-limiter`
- Input validation: rejects empty or oversized (>20,000 char) submissions
- Full frontend UI with score circle, score bars, tabbed results (Summary, Key Terms, Red Flags, Negotiate)
- Three built-in example term sheets (Series A, SAFE, convertible note)
- 7-test pytest suite covering all major success and error paths

---

## What's Left To Do

- PDF/file upload support (founders often receive term sheets as PDFs)
- Consider additional rate limiting and abuse prevention before any public deployment

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
