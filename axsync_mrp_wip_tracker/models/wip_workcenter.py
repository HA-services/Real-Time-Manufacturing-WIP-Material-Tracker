# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AxsyncWipWorkcenter(models.Model):
    """One row per work order, for work center analysis. Read-only SQL view."""
    _name = 'axsync.wip.workcenter'
    _description = 'AXSync WIP - Work Center Analysis'
    _auto = False
    _order = 'workcenter_id, id desc'
    _rec_name = 'workorder_id'

    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', readonly=True)
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    state = fields.Selection([
        ('pending', 'Waiting for another WO'), ('waiting', 'Waiting for components'),
        ('ready', 'Ready'), ('progress', 'In Progress'), ('done', 'Finished'),
        ('cancel', 'Cancelled')], string='Status', readonly=True)
    mo_state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('progress', 'In Progress'),
        ('to_close', 'To Close'), ('done', 'Done'), ('cancel', 'Cancelled')],
        string='MO State', readonly=True)
    date_start = fields.Datetime('Start', readonly=True)
    date_finished = fields.Datetime('End', readonly=True)
    duration_expected = fields.Float('Expected Duration (min)', readonly=True)
    duration = fields.Float('Real Duration (min)', readonly=True)
    duration_variance = fields.Float('Duration Variance (min)', readonly=True,
                                     help="Real minus expected duration, on finished work orders only.")
    is_open = fields.Boolean('Open', readonly=True)

    def init(self):
        self.env.cr.execute('DROP VIEW IF EXISTS %s CASCADE' % self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT w.id AS id,
                       w.id AS workorder_id,
                       w.production_id,
                       w.workcenter_id,
                       mo.product_id,
                       mo.company_id,
                       w.state,
                       mo.state AS mo_state,
                       w.date_start,
                       w.date_finished,
                       COALESCE(w.duration_expected, 0.0) AS duration_expected,
                       COALESCE(w.duration, 0.0) AS duration,
                       CASE WHEN w.state = 'done'
                            THEN COALESCE(w.duration, 0.0) - COALESCE(w.duration_expected, 0.0)
                            ELSE 0.0 END AS duration_variance,
                       w.state IN ('pending','waiting','ready','progress') AS is_open
                  FROM mrp_workorder w
                  JOIN mrp_production mo ON mo.id = w.production_id
            )
        """ % self._table)
