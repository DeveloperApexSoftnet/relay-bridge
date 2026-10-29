app_name = "relay_bridge"
app_title = "Relay Bridge"
app_publisher = "Relay"
app_description = "ERPNext WhatsApp messaging through Relay"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["erpnext"]
app_include_js = ["/assets/relay_bridge/js/send-whatsapp.js"]
doc_events = {
    "Quotation": {"on_submit": "relay_bridge.api.auto_event"},
    "Lead": {"after_insert": "relay_bridge.api.auto_event"},
    "Sales Invoice": {"on_submit": "relay_bridge.api.auto_event"},
}
