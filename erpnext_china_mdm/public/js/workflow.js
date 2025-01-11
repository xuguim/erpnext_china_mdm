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

	show_actions() {
		var added = false;
		var me = this;

		// if the loaded doc is dirty, don't show workflow buttons
		if (this.frm.doc.__unsaved === 1) {
			return;
		}

		function has_approval_access(transition) {
			let approval_access = false;
			const user = frappe.session.user;
			if (
				user === "Administrator" ||
				transition.allow_self_approval ||
				user !== me.frm.doc.owner
			) {
				approval_access = true;
			}
			return approval_access;
		}

		frappe.workflow.get_transitions(this.frm.doc).then((transitions) => {
			this.frm.page.clear_actions_menu();
			transitions.forEach((d) => {
				if (frappe.user_roles.includes(d.allowed) && has_approval_access(d)) {
					added = true;
					me.frm.page.add_action_item(__(d.action), async function () {
						// set the workflow_action for use in form scripts
						frappe.dom.freeze();
						me.frm.selected_workflow_action = d.action;

						try {
							const result = await me.frm.script_manager.preWorkflowAction(me.frm,d);

							await me.frm.script_manager.trigger("before_workflow_action");

							const doc = await frappe.xcall("frappe.model.workflow.apply_workflow", {
								doc: me.frm.doc,
								action: d.action,
							});

							frappe.model.sync(doc);
							me.frm.refresh();
							me.frm.selected_workflow_action = null;

							await me.frm.script_manager.trigger("after_workflow_action");
						}
						catch (error) {
							console.error(__("Something went wrong!"), error);
						} finally {
							frappe.dom.unfreeze();
						}
					});
				}
			});

			this.setup_btn(added);
		});
	}
};