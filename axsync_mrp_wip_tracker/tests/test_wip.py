# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import Form, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged('post_install', '-at_install', 'axsync_wip')
class TestAxsyncWip(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.comp_a = env['product.product'].create({'name': 'AX Comp A', 'type': 'consu', 'is_storable': True, 'standard_price': 10.0})
        cls.comp_b = env['product.product'].create({'name': 'AX Comp B', 'type': 'consu', 'is_storable': True, 'standard_price': 4.0})
        cls.fg = env['product.product'].create({'name': 'AX Finished', 'type': 'consu', 'is_storable': True})
        cls.bom = env['mrp.bom'].create({
            'product_tmpl_id': cls.fg.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [Command.create({'product_id': cls.comp_a.id, 'product_qty': 2.0}),
                             Command.create({'product_id': cls.comp_b.id, 'product_qty': 5.0})],
        })

    def _mo(self, qty, **kw):
        mo = self.env['mrp.production'].create(dict({
            'product_id': self.fg.id, 'bom_id': self.bom.id, 'product_qty': qty,
            'product_uom_id': self.fg.uom_id.id}, **kw))
        # Stock the component source location of this order (it depends on the default warehouse).
        location = mo.location_src_id
        stocked = getattr(self, '_stocked', self.env['stock.location'])
        if location not in stocked:
            self._stocked = stocked | location
            self.env['stock.quant']._update_available_quantity(self.comp_a, location, 100.0)
            self.env['stock.quant']._update_available_quantity(self.comp_b, location, 20.0)
        mo.action_confirm()
        return mo

    def _row(self, mo):
        self.env.flush_all()  # SQL views read the database: write pending ORM changes first
        self.env.invalidate_all()  # and drop cached view rows from earlier reads
        return self.env['axsync.wip.production'].search([('production_id', '=', mo.id)])

    def _comps(self, mo):
        self.env.flush_all()
        self.env.invalidate_all()
        return self.env['axsync.wip.component'].search([('production_id', '=', mo.id)])

    def test_planned_and_reserved(self):
        mo = self._mo(2)
        mo.action_assign()
        comps = self._comps(mo)
        self.assertEqual(len(comps), 2)
        a = comps.filtered(lambda c: c.product_id == self.comp_a)
        self.assertEqual(a.planned_qty, 4.0)
        self.assertEqual(a.reserved_qty, 4.0)
        self.assertEqual(a.consumed_qty, 0.0)
        self.assertEqual(a.shortage_qty, 0.0)
        row = self._row(mo)
        self.assertEqual(row.planned_value, 4 * 10 + 10 * 4)
        self.assertEqual(row.consumed_value, 0.0)
        self.assertFalse(row.has_shortage)
        self.assertTrue(row.is_open)

    def test_shortage_detected(self):
        mo = self._mo(10)   # needs 50 of B, only 20 in stock
        mo.action_assign()
        b = self._comps(mo).filtered(lambda c: c.product_id == self.comp_b)
        self.assertEqual(b.planned_qty, 50.0)
        self.assertEqual(b.reserved_qty, 20.0)
        self.assertEqual(b.shortage_qty, 30.0)
        self.assertEqual(b.shortage_value, 30.0 * 4.0)
        row = self._row(mo)
        self.assertTrue(row.has_shortage)
        self.assertEqual(row.shortage_count, 1)
        self.env.flush_all()
        data = self.env['axsync.wip.production'].get_dashboard_data(30)
        tiles = {t['key']: t['value'] for t in data['tiles']}
        self.assertGreaterEqual(tiles['shortage'], 1)
        self.assertTrue(any(s['id'] == mo.id for s in data['shortages']))

    def test_consumption_variance_and_wip(self):
        mo = self._mo(1)
        mo.action_assign()
        mo.qty_producing = 1
        # consume one extra unit of A (over-consumption) before closing
        raw_a = mo.move_raw_ids.filtered(lambda m: m.product_id == self.comp_a)
        raw_a.quantity = 3.0
        raw_a.picked = True
        mo.move_raw_ids.filtered(lambda m: m.product_id == self.comp_b).picked = True
        a = self._comps(mo).filtered(lambda c: c.product_id == self.comp_a)
        self.assertEqual(a.consumed_qty, 3.0)
        self.assertEqual(self._row(mo).wip_value, 3 * 10 + 5 * 4)
        mo.with_context(skip_consumption=True, skip_backorder=True).button_mark_done()
        self.assertEqual(mo.state, 'done')
        a = self._comps(mo).filtered(lambda c: c.product_id == self.comp_a)
        self.assertEqual(a.variance_qty, 1.0)
        self.assertTrue(a.is_over_consumed)
        row = self._row(mo)
        self.assertEqual(row.variance_value, 10.0)
        self.assertEqual(row.wip_value, 0.0, "Done orders carry no WIP")
        self.assertFalse(row.is_open)
        self.assertEqual(row.produced_qty, 1.0)
        self.assertEqual(row.progress, 100.0)

    def test_delayed_flag(self):
        late = self._mo(1, date_deadline=fields.Datetime.now() - timedelta(days=3))
        ontime = self._mo(1, date_deadline=fields.Datetime.now() + timedelta(days=3))
        self.assertTrue(self._row(late).is_delayed)
        self.assertFalse(self._row(ontime).is_delayed)
        self.env.flush_all()
        data = self.env['axsync.wip.production'].get_dashboard_data(30)
        self.assertTrue(any(d['id'] == late.id for d in data['delayed']))
        self.assertFalse(any(d['id'] == ontime.id for d in data['delayed']))

    def test_scrap(self):
        mo = self._mo(1)
        mo.action_assign()
        scrap = self.env['stock.scrap'].create({
            'product_id': self.comp_a.id, 'product_uom_id': self.comp_a.uom_id.id,
            'scrap_qty': 1.0, 'production_id': mo.id})
        scrap.action_validate()
        self.env.flush_all()
        rows = self.env['axsync.wip.scrap'].search([('production_id', '=', mo.id)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.scrap_qty, 1.0)
        self.assertEqual(rows.scrap_value, 10.0)
        self.assertEqual(self._row(mo).scrap_value, 10.0)
        self.assertEqual(self._row(mo).scrap_count, 1)

    def test_cancelled_moves_are_excluded(self):
        mo = self._mo(1)
        mo.action_cancel()
        self.assertFalse(self._comps(mo))
        self.assertFalse(self._row(mo).is_open)

    def test_workcenter_rows(self):
        wc = self.env['mrp.workcenter'].create({'name': 'AX WC'})
        self.bom.write({'operation_ids': [Command.create({
            'name': 'Assemble', 'workcenter_id': wc.id, 'time_cycle_manual': 30})]})
        mo = self._mo(1)
        self.env.flush_all()
        rows = self.env['axsync.wip.workcenter'].search([('production_id', '=', mo.id)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.workcenter_id, wc)
        self.assertEqual(rows.duration_expected, 30.0)
        self.assertEqual(self._row(mo).workorder_count, 1)

    def test_read_only_and_access(self):
        mo = self._mo(1)
        row = self._row(mo)
        user = self.env['res.users'].create({
            'name': 'AX Mrp User', 'login': 'ax_mrp_user',
            'group_ids': [Command.set([self.env.ref('base.group_user').id,
                                       self.env.ref('mrp.group_mrp_user').id])]})
        self.assertTrue(row.with_user(user).read(['production_id']))
        with self.assertRaises(AccessError):
            row.with_user(user).write({'progress': 5})
        plain = self.env['res.users'].create({
            'name': 'AX Plain', 'login': 'ax_plain',
            'group_ids': [Command.set([self.env.ref('base.group_user').id])]})
        with self.assertRaises(AccessError):
            row.with_user(plain).read(['production_id'])

    def test_multi_company_rule(self):
        company2 = self.env['res.company'].create({'name': 'AX Company 2'})
        user = self.env['res.users'].create({
            'name': 'AX Mrp User C2', 'login': 'ax_mrp_c2',
            'company_id': company2.id, 'company_ids': [Command.set([company2.id])],
            'group_ids': [Command.set([self.env.ref('base.group_user').id,
                                       self.env.ref('mrp.group_mrp_user').id])]})
        mo = self._mo(1)
        self.env.flush_all()
        visible = self.env['axsync.wip.production'].with_user(user).search([('production_id', '=', mo.id)])
        self.assertFalse(visible, "A user of company 2 must not see company 1 orders")

    def test_dashboard_all_periods(self):
        for days in (0, 7, 30, 365):
            data = self.env['axsync.wip.production'].get_dashboard_data(days)
            keys = {t['key'] for t in data['tiles']}
            self.assertTrue({'open', 'progress', 'delayed', 'shortage', 'wip', 'scrap'} <= keys)

    def test_subcontracting_columns_without_subcontracting_app(self):
        """The module is self-contained: the subcontracting columns exist even if the app is absent."""
        mo = self._mo(1)
        row = self._row(mo)
        self.assertFalse(row.subcontractor_id)
        self.assertEqual(row.is_subcontract, self.env['axsync.wip.production']._has_subcontracting() and row.is_subcontract)
        self.assertFalse(row.is_subcontract)

    def test_register_hook_rebuilds_missing_view(self):
        model = self.env['axsync.wip.production']
        self.env.cr.execute('DROP VIEW axsync_wip_production CASCADE')
        model._register_hook()
        self.assertTrue(model._view_flag())
        self.assertEqual(model.search_count([]), model.search_count([]))
