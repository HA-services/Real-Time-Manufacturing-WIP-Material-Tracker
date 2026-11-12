# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
# Runs only when the optional Subcontracting app is installed (skipped otherwise).
import unittest

from odoo.tests import Form, tagged

try:
    from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon
except ImportError:  # pragma: no cover
    TestMrpSubcontractingCommon = None

if TestMrpSubcontractingCommon:
    @tagged('post_install', '-at_install', 'axsync_wip')
    class TestAxsyncWipSubcontract(TestMrpSubcontractingCommon):

        @classmethod
        def setUpClass(cls):
            from odoo.modules.registry import Registry
            import odoo
            db = odoo.tools.config['db_name']
            if isinstance(db, str):
                db = db.split(',')[0]
            with Registry(db).cursor() as cr:
                cr.execute("SELECT 1 FROM ir_module_module WHERE name='mrp_subcontracting' AND state='installed'")
                if not cr.fetchone():
                    raise unittest.SkipTest('Subcontracting app not installed')
            super().setUpClass()

        def test_subcontract_order_flagged(self):
            if not self.env['axsync.wip.production']._has_subcontracting():
                self.skipTest('Subcontracting app not installed')
            self.env['stock.quant']._update_available_quantity(
                self.comp1, self.env.ref('stock.stock_location_stock'), 10)
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
            self.assertGreaterEqual(tiles['subcontract'], 1)
            comps = self.env['axsync.wip.component'].search([('production_id', 'in', mo.ids)])
            self.assertTrue(comps)
