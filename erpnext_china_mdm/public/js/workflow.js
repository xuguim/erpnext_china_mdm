frappe.ui.form.States = class FormStates extends frappe.ui.form.States {
	setup_help() {
		var me = this;
		if(frappe.workflow.workflows[me.frm.doctype]) {
			let workflow_name = frappe.workflow.workflows[me.frm.doctype].name;
			frappe.db.get_value('Workflow',workflow_name,'help_html').then(res=>{
				this.frm.page.add_action_item(
					__("Help"),
					function () {
						frappe.workflow.setup(me.frm.doctype);
						var state = me.get_state();
						var d = new frappe.ui.Dialog({
							title: "Workflow: " + frappe.workflow.workflows[me.frm.doctype].name,
						});
		
						frappe.workflow.get_transitions(me.frm.doc).then((transitions) => {
							const next_actions =
								$.map(
									transitions,
									(d) => `${d.action.bold()} ${__("by Role")} ${d.allowed}`
								).join(", ") || __("None: End of Workflow").bold();
		
							const document_editable_by = frappe.workflow
								.get_document_state_roles(me.frm.doctype, state)
								.map((role) => role.bold())
								.join(", ");
		
							$(d.body)
								.html(
									`
										<div>${res.message.help_html || ''}</div>
									`
								)
								.css({ padding: "15px" });
		
							d.show();
						});
					},
					true
				);
			})
		}
		
	}
};
