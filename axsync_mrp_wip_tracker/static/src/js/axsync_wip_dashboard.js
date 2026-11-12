/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class AxsyncWipDashboard extends Component {
    static template = "axsync_mrp_wip_tracker.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ days: 30, data: null });
        this.periods = [
            { value: 7, label: "Last 7 days" },
            { value: 30, label: "Last 30 days" },
            { value: 90, label: "Last 90 days" },
            { value: 365, label: "Last 12 months" },
            { value: 0, label: "All time" },
        ];
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call(
            "axsync.wip.production", "get_dashboard_data", [this.state.days]
        );
    }

    async onPeriodChange(ev) {
        this.state.days = parseInt(ev.target.value, 10);
        await this.load();
    }

    formatValue(tile) {
        if (tile.monetary) {
            const cur = this.state.data.currency;
            const num = Number(tile.value || 0).toLocaleString(undefined, {
                minimumFractionDigits: 2, maximumFractionDigits: 2,
            });
            return cur.position === "before" ? `${cur.symbol} ${num}` : `${num} ${cur.symbol}`;
        }
        return String(tile.value);
    }

    openTile(tile) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: tile.label,
            res_model: tile.model,
            views: [[false, "list"], [false, "pivot"], [false, "graph"]],
            domain: tile.domain,
        });
    }

    openProduction(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mrp.production",
            res_id: id,
            views: [[false, "form"]],
        });
    }
}

registry.category("actions").add("axsync_wip_dashboard", AxsyncWipDashboard);
