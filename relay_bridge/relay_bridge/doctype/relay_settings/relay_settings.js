frappe.ui.form.on("Relay Settings", {
  refresh(frm) {
    frm.add_custom_button(__("Test Relay configuration"), async () => {
      if (frm.is_dirty()) {
        frappe.msgprint(__("Save settings before testing."));
        return;
      }
      const result = (
        await frappe.call({
          method: "relay_bridge.api.check_configuration",
          freeze: true,
          freeze_message: __("Checking Relay defaults and WhatsApp readiness…"),
        })
      ).message;
      if (result.ready)
        frappe.msgprint(
          __("Relay is ready. Enabled documents: {0}. PDF mode: {1}.", [
            result.doctypes.join(", "),
            result.pdfEnabled ? "PDF + caption" : "Text only",
          ]),
        );
    });
  },
});
