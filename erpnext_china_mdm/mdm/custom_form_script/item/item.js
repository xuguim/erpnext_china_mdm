frappe.ui.form.on("Item", {

    refresh(frm) {
        const filters = [["name", "in", frm.doc.uoms.map((x) => x.uom)]]

        frm.set_query("stock_uom", function (doc) {
            return {
                filters: filters
            };
        });

        frm.set_query("purchase_uom", function (doc) {
            return {
                filters: filters
            };
        });

        frm.set_query("sales_uom", function (doc) {
            return {
                filters: filters
            };
        });
    }
})