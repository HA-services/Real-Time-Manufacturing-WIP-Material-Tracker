# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import Form, tagged
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


@tagged('post_install', '-at_install', 'axsync_wip')
class TestAxsyncWipSubcontract(TestMrpSubcontractingCommon):

    def test_subcontract_order_flagged(self):
        """A receipt of a subcontracted product creates a subcontract MO that the report flags."""
        self.env['stock.quant']._update_available_quantity(
            self.comp1, self.env.ref('stock.stock_location_stock'), 10)
        # Create the receipt directly (purchase is not a dependency of this module).
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 2
        picking = picking_form.save()
        picking.action_confirm()
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertTrue(mo, "Subcontracting MO should exist")
        self.env.flush_all()
        row = self.env['axsync.wip.production'].search([('production_id', 'in', mo.ids)])
        self.assertTrue(row.is_subcontract)
        data = self.env['axsync.wip.production'].get_dashboard_data(30)
        tiles = {t['key']: t['value'] for t in data['tiles']}
        self.assertIn('subcontract', tiles)
        self.assertGreaterEqual(tiles['subcontract'], 1)
        # The core component report still lists the subcontract MO components.
        comps = self.env['axsync.wip.component'].search([('production_id', 'in', mo.ids)])
        self.assertTrue(comps)
