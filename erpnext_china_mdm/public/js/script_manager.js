frappe.ui.form.ScriptManager = class ScriptManager extends frappe.ui.form.ScriptManager {
	async preWorkflowAction(frm,transition) {
		frappe.dom.unfreeze();
		try {
			if (transition.action === 'Reject') {
				const userInput = await promptWithPromise(
					frm.doc.doctype,frm.doc.name,
					[
						{
							fieldname: "reason",
							label: __("Reason"),
							fieldtype: "HTML Editor",
							reqd: 1,
							description:`<span class="text-danger bold">${__("Please provide a reason for the reject action")}</span>`
						},
					],
					__("Type a reply / comment"),
					__("Add")
				);
			}
		} catch (error) {
			throw error;
		}
    }
}

async function promptWithPromise(doctype,docname, fields, title, primary_label) {
	try {
        const values = await new Promise((resolve, reject) => {
            frappe.prompt(fields, (vals) => {
                if (vals) {
                    resolve(vals);
                }
            }, title, primary_label);
        });
		const reason = values.reason;
        await callWithPromise("erpnext_china_mdm.utils.workflow.add_reason", {
            doctype: doctype,
            docname: docname,
            reason: `<div class="text-danger">${reason}</div>`,
            user: frappe.session.user,
            user_name: frappe.session.user_fullname,
        });

        return "Success";
    } catch (error) {
        console.error(__("Something went wrong!"), error);
        throw error;
    }
}


function callWithPromise(method, args) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: method,
            args: args,
            callback: function (r) {
                if (r.exc) {
                    reject(new Error(r.exc));
                } else {
                    resolve(r.message);
                }
            }
        });
    });
}