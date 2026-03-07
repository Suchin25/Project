import os
import json
from flask import Flask, render_template, request, Response, stream_with_context
from flask_cors import CORS
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an expert startup analyst with deep experience in venture capital,
entrepreneurship, and business strategy. Analyze startup ideas objectively and thoroughly.

Always respond with valid JSON in exactly this structure:
{
  "summary": "Plain English explanation of what this startup does and why it could matter (2-3 paragraphs)",
  "market": {
    "size": "Estimated market size and growth rate",
    "competitors": ["competitor1", "competitor2", "competitor3"],
    "positioning": "How this startup differentiates from competitors",
    "timing": "Why now? Is market timing good or bad?"
  },
  "red_flags": [
    {"flag": "Risk title", "detail": "Explanation of the risk and its severity"}
  ],
  "score": {
    "overall": 72,
    "breakdown": {
      "market_opportunity": 80,
      "feasibility": 65,
      "differentiation": 70,
      "timing": 75,
      "team_fit": 70
    },
    "verdict": "One-sentence overall verdict"
  },
  "next_steps": [
    {"step": "Action title", "detail": "Specific actionable advice"}
  ]
}

Scores are integers from 0-100. Be honest and critical — not every idea is great.
Red flags should be real concerns, not generic risks. Next steps should be specific and actionable."""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    idea = data.get("idea", "").strip()

    if not idea:
        return {"error": "No idea provided"}, 400

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
                        "content": f"Analyze this startup idea:\n\n{idea}",
                    }
                ],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            # Parse and return the JSON result
            # Extract JSON from response (handle markdown code blocks)
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
    app.run(debug=True, port=5000)
