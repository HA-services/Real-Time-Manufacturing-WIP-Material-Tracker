# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AxsyncWipProduction(models.Model):
    _inherit = 'axsync.wip.production'

    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor', readonly=True)
    is_subcontract = fields.Boolean('Subcontracted', readonly=True,
                                    help="Manufacturing order created by a subcontracting bill of materials.")

    def _select_extra(self):
        return super()._select_extra() + """,
                       mo.subcontractor_id AS subcontractor_id,
                       (COALESCE(bom.type, '') = 'subcontract' OR mo.subcontractor_id IS NOT NULL) AS is_subcontract
        """

    def _join_extra(self):
        return super()._join_extra() + " LEFT JOIN mrp_bom bom ON bom.id = mo.bom_id "

    @api.model
    def _dashboard_tiles(self, days):
        tiles = super()._dashboard_tiles(days)
        dom = [('is_subcontract', '=', True), ('is_open', '=', True)]
        tiles.insert(4, {
            'key': 'subcontract', 'label': 'Open subcontracting orders', 'model': 'axsync.wip.production',
            'domain': dom, 'value': self.search_count(dom), 'tone': 'primary'})
        return tiles
