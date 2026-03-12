import os
import json
from flask import Flask, render_template, request, Response, stream_with_context
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an expert startup attorney and venture capital advisor with deep experience
analyzing investment term sheets. Your role is to analyze term sheets and clearly explain their
implications to founders — what each clause means, what is standard, and what to push back on.

Always respond with valid JSON in exactly this structure:
{
  "summary": "Plain English overview of this term sheet: what type of deal it is, who the key parties are, headline economics, and your overall impression (2-3 paragraphs)",
  "key_terms": {
    "instrument": "Type of investment (e.g., Series A Preferred Stock, Post-Money SAFE, Convertible Note)",
    "valuation": "Pre-money and post-money valuation, or cap for SAFEs/notes",
    "investment_amount": "Total investment amount",
    "liquidation_preference": "Liquidation preference multiple and type (participating vs non-participating)",
    "anti_dilution": "Anti-dilution protection type (e.g., broad-based weighted average, full ratchet, none)",
    "board_composition": "Board seat breakdown after the round",
    "pro_rata_rights": "Pro-rata / follow-on investment rights",
    "vesting": "Founder and/or employee vesting schedule"
  },
  "red_flags": [
    {"flag": "Concerning clause title", "detail": "Why this clause is problematic, its real-world impact on founders, and what is market standard instead", "severity": "high|medium|low"}
  ],
  "score": {
    "overall": 72,
    "breakdown": {
      "founder_friendliness": 70,
      "valuation_fairness": 75,
      "control_terms": 65,
      "liquidity_terms": 80,
      "standard_terms": 70
    },
    "verdict": "One-sentence overall verdict on these terms from a founder's perspective"
  },
  "recommendations": [
    {"action": "Specific negotiation ask", "detail": "What to push for, why it matters, and how likely investors are to agree"}
  ]
}

Scores are integers 0-100 where 100 is maximally founder-friendly.
Be specific — reference actual numbers and clauses from the document.
If a field is not addressed in the term sheet, write "Not specified" for that key term.
Red flags should cite real clauses with concrete impact, not generic risks.
Recommendations should be prioritized, actionable negotiation points."""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
@limiter.limit("10 per minute")
def analyze():
    data = request.get_json()
    termsheet = data.get("termsheet", "").strip()

    if not termsheet:
        return {"error": "No term sheet provided"}, 400

    if len(termsheet) > 20000:
        return {"error": "Term sheet is too long. Please keep it under 20,000 characters."}, 400

    def generate():
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze this term sheet:\n\n{termsheet}",
                    }
                ],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            json_str = full_response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                json_str = json_str.strip()

            result = json.loads(json_str)
            yield f"data: {json.dumps({'status': 'done', 'result': result})}\n\n"

        except json.JSONDecodeError:
            yield f"data: {json.dumps({'status': 'error', 'message': 'Failed to parse analysis. Please try again.'})}\n\n"
        except anthropic.APIError as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
