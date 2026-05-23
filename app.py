import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Replace with your actual GitHub Pages URL
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "https://ovieofdelta.github.io")
CORS(app, origins=[ALLOWED_ORIGIN])

# ── Environment variables (never hard-code these) ─────────────────────────────
BREVO_API_KEY  = os.environ.get("BREVO_API_KEY")
BREVO_LIST_ID  = int(os.environ.get("BREVO_LIST_ID", "0"))
CONTACT_EMAIL  = os.environ.get("CONTACT_EMAIL")   # where form submissions are sent TO
SENDER_EMAIL   = os.environ.get("SENDER_EMAIL")    # a verified sender email in your Brevo account

BREVO_HEADERS = {
    "Content-Type": "application/json",
    "api-key": BREVO_API_KEY,
}


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Nelson Integrated Oil & Gas API is running"}), 200


# ── Newsletter subscription ───────────────────────────────────────────────────
@app.route("/api/newsletter", methods=["POST"])
def newsletter():
    data  = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    name  = data.get("name", "").strip()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    payload = {
        "email": email,
        "attributes": {"FIRSTNAME": name},
        "listIds": [BREVO_LIST_ID],
        "updateEnabled": True,   # update the contact if they already exist
    }

    res = requests.post(
        "https://api.brevo.com/v3/contacts",
        json=payload,
        headers=BREVO_HEADERS,
        timeout=10,
    )

    # 201 = created, 204 = updated
    if res.status_code in (201, 204):
        return jsonify({"message": "Subscribed successfully"}), 200

    # Brevo returns 400 + code "duplicate_parameter" when already on the list
    try:
        brevo_code = res.json().get("code", "")
    except Exception:
        brevo_code = ""

    if res.status_code == 400 and brevo_code == "duplicate_parameter":
        return jsonify({"message": "already_subscribed"}), 200

    return jsonify({"error": "Failed to subscribe. Please try again."}), 500


# ── Contact / booking form ────────────────────────────────────────────────────
@app.route("/api/contact", methods=["POST"])
def contact():
    data    = request.get_json(silent=True) or {}
    name    = data.get("name", "").strip()
    email   = data.get("email", "").strip()
    company = data.get("company", "N/A").strip()
    phone   = data.get("phone", "").strip()
    service = data.get("service", "General Inquiry").strip()
    location = data.get("location", "N/A").strip()
    details  = data.get("details", "").strip()

    if not email or not name or not phone:
        return jsonify({"error": "Name, email, and phone are required"}), 400

    html_body = f"""
    <h2 style="color:#0A2463;">New Service Request — Nelson Integrated Oil & Gas</h2>
    <table cellpadding="8" style="border-collapse:collapse;width:100%;font-family:sans-serif;">
      <tr><td style="background:#f4f4f4;font-weight:bold;width:180px;">Service</td>
          <td>{service}</td></tr>
      <tr><td style="background:#f4f4f4;font-weight:bold;">Full Name</td>
          <td>{name}</td></tr>
      <tr><td style="background:#f4f4f4;font-weight:bold;">Company</td>
          <td>{company}</td></tr>
      <tr><td style="background:#f4f4f4;font-weight:bold;">Phone</td>
          <td>{phone}</td></tr>
      <tr><td style="background:#f4f4f4;font-weight:bold;">Email</td>
          <td><a href="mailto:{email}">{email}</a></td></tr>
      <tr><td style="background:#f4f4f4;font-weight:bold;">Location</td>
          <td>{location}</td></tr>
      <tr><td style="background:#f4f4f4;font-weight:bold;vertical-align:top;">Details</td>
          <td>{details or "—"}</td></tr>
    </table>
    <p style="color:#888;font-size:12px;margin-top:20px;">
      Sent from the Nelson Integrated Oil & Gas company website contact form.
    </p>
    """

    payload = {
        "sender":  {"name": "Nelson Integrated Oil & Gas Company Website", "email": SENDER_EMAIL},
        "to":      [{"email": CONTACT_EMAIL, "name": "Nelson Integrated Oil & Gas Company"}],
        "replyTo": {"email": email, "name": name},
        "subject": f"[Website Request] {service} — {name}",
        "htmlContent": html_body,
    }

    res = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        json=payload,
        headers=BREVO_HEADERS,
        timeout=10,
    )

    if res.status_code == 201:
        return jsonify({"message": "Message sent successfully"}), 200

    return jsonify({"error": "Failed to send message. Please try again."}), 500


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
