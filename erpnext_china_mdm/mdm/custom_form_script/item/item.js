frappe.ui.form.on("Item", {

    refresh(frm) {
        const uoms = new Set(frm.doc.uoms.map((x) => x.uom));
        if (frm.doc.stock_uom) {
            uoms.add(frm.doc.stock_uom);
        }
        const filters = [["name", "in", Array.from(uoms)]]

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