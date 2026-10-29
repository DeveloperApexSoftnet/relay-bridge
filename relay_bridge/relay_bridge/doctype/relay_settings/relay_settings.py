from urllib.parse import urlparse
from uuid import UUID
import frappe
from frappe.model.document import Document

class RelaySettings(Document):
    def validate(self):
        if not self.enabled:
            return
        url = urlparse((self.relay_url or "").rstrip("/"))
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            frappe.throw("Relay URL must be HTTPS without credentials, query or fragment.")
        try:
            UUID(self.relay_connection_id or "")
        except ValueError:
            frappe.throw("Enter the ERP connection UUID from the Relay portal.")
        secret = self.get_password("signing_secret", raise_exception=False)
        if not secret or len(secret) < 32:
            frappe.throw("The signing secret must contain at least 32 characters and match Relay.")
