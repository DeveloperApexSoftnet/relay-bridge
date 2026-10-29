// Requires the Relay Bridge app. No Relay page, browser credentials or auto-save.
(() => {
  if (window.__relayDirectSendInstalled) return;
  window.__relayDirectSendInstalled = true;
  for (const doctype of ["Quotation", "Lead", "Sales Invoice"]) {
    frappe.ui.form.on(doctype, {
      refresh(frm) {
        if (frm.is_new() || frm.doc.docstatus === 2) return;
        const button = frm.add_custom_button(__("Send WhatsApp"), async () => {
          if (frm.__relaySending) return;
          if (frm.is_dirty()) {
            frappe.msgprint(__("Save this document before sending."));
            return;
          }
          frm.__relaySending = true;
          button.prop("disabled", true);
          try {
            const response = await frappe.call({
              method: "relay_bridge.api.send_document",
              args: { doctype: frm.doctype, document_name: frm.doc.name },
              freeze: true,
              freeze_message: __("Queueing WhatsApp message…"),
            });
            const id = response.message.id;
            frappe.show_alert({
              message: __(
                "WhatsApp request queued. Sending uses your administrator's defaults.",
              ),
              indicator: "blue",
            });
            let result = response.message;
            for (let attempt = 0; attempt < 30; attempt++) {
              if (
                ["sent", "delivered", "read", "failed"].includes(result.status)
              ) {
                const text =
                  result.status === "failed"
                    ? __(
                        "WhatsApp request failed. Ask your administrator to review notification {0}. Error: {1}",
                        [id, result.error || "SEND_FAILED"],
                      )
                    : __("WhatsApp: {0}. Notification: {1}", [
                        result.status,
                        id,
                      ]);
                frappe.msgprint({
                  title: __("WhatsApp result"),
                  message: frappe.utils.escape_html(text),
                  indicator: result.status === "failed" ? "red" : "green",
                });
                return;
              }
              await new Promise((resolve) => setTimeout(resolve, 2000));
              result = (
                await frappe.call({
                  method: "relay_bridge.api.notification_status",
                  args: { notification_id: id },
                })
              ).message;
            }
            frappe.msgprint(
              __(
                "WhatsApp is still processing. Notification: {0}. No additional action is needed; your administrator can check Relay history.",
                [id],
              ),
            );
          } catch (error) {
            frappe.show_alert({
              message: __(
                "Could not confirm sending. Ask your administrator to check Relay history before retrying.",
              ),
              indicator: "red",
            });
          } finally {
            frm.__relaySending = false;
            button.prop("disabled", false);
          }
        });
      },
    });
  }
})();
