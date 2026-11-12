# AXSync Real-Time Manufacturing WIP & Material Tracker

Odoo 19.0 | Category: Manufacturing | License: OPL-1 | Publisher: AXSync (www.axsync.com)

Read-only reporting on top of standard Odoo Manufacturing: WIP dashboard, material consumption, variance, shortages, scrap and work center analysis.

## One module

`axsync_mrp_wip_tracker` is a single, self-contained module. It depends only on `mrp`. Subcontracting tracking is built in and switches on by itself when the Subcontracting app is installed.

## Requirements

- Odoo 19.0 (tested on Community). Enterprise not tested.
- Manufacturing (`mrp`). Work center reports need work orders enabled in Manufacturing settings.
- No additional Python libraries.

## Installation

1. Copy the `axsync_mrp_wip_tracker` folder into a directory on your Odoo `addons_path` (or add the Git repository branch `19.0` on Odoo.sh).
2. Restart Odoo and update the Apps list (developer mode, Apps, Update Apps List).
3. Install **Manufacturing WIP Tracker**.

## Access

Members of Manufacturing / User (and Manager) get read-only access. Nobody can create, edit or delete report rows. Reports respect multi-company access: users see only the companies they are allowed to access.

## Using the module

Open Manufacturing > Reporting > WIP Tracker.

- **WIP Dashboard**: tiles for open, in progress, delayed and short orders, WIP material value and scrap value for the chosen period. Click a tile to open its list. Click a row in the lower tables to open the order.
- **Manufacturing Order Analysis**: one row per order. Progress, deadline, material readiness, shortage count, consumed, WIP, variance and scrap values.
- **Material Consumption and Variance**: one row per component line.
- **Material Shortages**: component lines on open orders that are not fully reserved or consumed.
- **Scrap Analysis**: validated scrap linked to manufacturing orders.
- **Work Center Analysis**: one row per work order with expected and real duration in minutes.

Use the standard Odoo export on any list or pivot.

## How the numbers are calculated

All quantities are in the product's own unit of measure. Stock move quantities in another unit are converted.

| Figure | Definition |
|---|---|
| Planned | Demand quantity of the component move. |
| Consumed | Move quantity when the move is picked or done. |
| Reserved | Move quantity when the move is not yet picked or done. |
| Shortage | Planned minus move quantity (not below zero), only on open orders (confirmed, in progress, to close) and moves not yet done. |
| Variance | Consumed minus planned, only on done moves. |
| Progress | Quantity of the finished product in done finished moves, divided by quantity to produce, capped at 100 percent. |
| Delayed | Order is open and its deadline is earlier than now. |
| WIP material value | Consumed quantity times standard cost, only for open orders. |
| Scrap value | Scrapped quantity times standard cost, for validated scrap linked to an order. |

Standard cost is resolved in this order: company specific cost, global cost, then zero. WIP value is an operational estimate, not an accounting valuation. The module creates no journal entries.

## Subcontracting

When the Subcontracting app is installed, an order is subcontracted when its bill of materials is of type Subcontracting or it has a subcontractor. The Manufacturing Order Analysis gains a Subcontractor column (hidden by default), a Subcontracted filter and a Subcontractor group-by. The dashboard gains an Open subcontracting orders tile. Stock held at subcontractor locations is not reported separately.

## Known limitations

- Shortage is based on reservation. It does not consider incoming purchases or planned production.
- Orders without a deadline are never flagged as delayed.
- Scrap not linked to a manufacturing order is not included.
- Reports are database views. Pending changes are visible once saved.
- Tested on Odoo 19.0 Community. Not tested on Enterprise.

## Uninstall

Uninstalling removes the reporting views and menus. No standard Odoo data is changed.
