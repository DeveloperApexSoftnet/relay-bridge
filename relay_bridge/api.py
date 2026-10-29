"""Server-to-server Relay bridge. Never return credentials to browser code."""
import hashlib
import hmac
import json
import re
import time
from urllib.parse import urlparse
import frappe
import requests

EVENTS = {"Quotation": "quotation_submit", "Lead": "lead_create", "Sales Invoice": "invoice_submit"}

def _configuration():
    settings = frappe.get_single("Relay Settings")
    if settings.enabled:
        base = (settings.relay_url or "").rstrip("/")
        connection = settings.relay_connection_id
        secret = settings.get_password("signing_secret", raise_exception=False)
    else:
        if settings.relay_url or settings.relay_connection_id:
            frappe.throw("Relay is disabled in Relay Settings.")
        base = (frappe.conf.get("relay_url") or "").rstrip("/")
        connection = frappe.conf.get("relay_connection_id")
        secret = frappe.conf.get("relay_signing_secret")
    url = urlparse(base)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or not connection or not re.fullmatch(r"[a-fA-F0-9-]{36}", connection)
            or not secret or len(secret) < 32):
        frappe.throw("An administrator must configure Relay Settings and this site's Relay defaults first.")
    return base, connection, secret

def _request(payload, suffix=""):
    base, connection, secret = _configuration()
    body = {**payload, "site": frappe.utils.get_url().rstrip("/"), "timestamp": int(time.time())}
    raw = json.dumps(body, separators=(",", ":")).encode()
    signature = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    try:
        response = requests.post(f"{base}/integration/{connection}{suffix}", data=raw,
            headers={"Content-Type": "application/json", "X-Integration-Signature": signature},
            timeout=20, allow_redirects=False)
    except requests.RequestException:
        frappe.throw("Relay could not confirm the request. Check notification history before retrying; the same event is deduplicated.")
    try:
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError()
    except ValueError:
        frappe.throw("Relay returned an invalid response. Check notification history before retrying.")
    if response.status_code not in (200, 202):
        candidate = result.get("error", "")
        code = candidate if isinstance(candidate, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", candidate) else "RELAY_REQUEST_REJECTED"
        frappe.throw(f"Relay: {code} (HTTP {response.status_code}). Ask your administrator to check the connection/defaults.")
    return result

@frappe.whitelist(methods=["POST"])
def send_document(doctype, document_name):
    if doctype not in EVENTS:
        frappe.throw("Unsupported document type", frappe.PermissionError)
    doc = frappe.get_doc(doctype, document_name)
    doc.check_permission("read")
    if not frappe.has_permission(doctype, "write", doc=doc):
        frappe.throw("Document write permission is required to send notifications", frappe.PermissionError)
    if doc.docstatus == 2:
        frappe.throw("Cancelled documents cannot be sent.")
    result = _request({"doctype": doctype, "documentId": doc.name, "trigger": "manual"})
    frappe.cache.set_value(f"relay:{frappe.session.user}:{result['id']}",
        {"doctype": doctype, "name": doc.name}, expires_in_sec=3600)
    return {"id": result["id"], "status": _display_status(result["status"])}

@frappe.whitelist(methods=["POST"])
def send_quotation(document_name):
    return send_document("Quotation", document_name)

def _display_status(status):
    return {"uncertain": "failed", "operator_confirmed": "sent", "accepted": "sent"}.get(status, status)

@frappe.whitelist(methods=["POST"])
def notification_status(notification_id):
    record = frappe.cache.get_value(f"relay:{frappe.session.user}:{notification_id}")
    if not record:
        frappe.throw("Notification access expired or denied", frappe.PermissionError)
    if isinstance(record, str):
        record = {"doctype": "Quotation", "name": record}
    if record.get("doctype") not in EVENTS:
        frappe.throw("Notification access denied", frappe.PermissionError)
    frappe.get_doc(record["doctype"], record["name"]).check_permission("read")
    result = _request({"notificationId": notification_id}, "/status")
    return {"id": result["id"], "status": _display_status(result["status"]), "error": result.get("error")}

@frappe.whitelist(methods=["POST"])
def check_configuration():
    frappe.only_for("System Manager")
    return _request({}, "/check")

def auto_event(doc, method=None):
    trigger = EVENTS.get(doc.doctype)
    if not trigger or trigger not in frappe.conf.get("relay_triggers", []):
        return
    if trigger.endswith("_submit") and doc.docstatus != 1:
        return
    frappe.enqueue("relay_bridge.api.deliver_event", queue="short", enqueue_after_commit=True,
        doctype=doc.doctype, document_name=doc.name, trigger=trigger)

def deliver_event(doctype, document_name, trigger):
    if doctype not in EVENTS or EVENTS[doctype] != trigger:
        frappe.throw("Unsupported Relay event")
    try:
        return _request({"doctype": doctype, "documentId": document_name, "trigger": trigger})
    except Exception:
        frappe.log_error(title="Relay automatic notification failed", message="Check Relay history and administrator configuration. No credentials or customer payload logged.")
        raise
