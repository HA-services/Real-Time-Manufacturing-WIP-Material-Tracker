# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
{
    'name': 'WIP Tracker Subcontract',
    'summary': 'Adds subcontracting visibility to the AXSync Manufacturing WIP Tracker',
    'description': 'Bridge module. Installs automatically when both Manufacturing WIP Tracker '
                   'and Subcontracting are installed.',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'author': 'AXSync',
    'website': 'https://www.axsync.com',
    'license': 'OPL-1',
    'depends': ['axsync_mrp_wip_tracker', 'mrp_subcontracting'],
    'data': [
        'views/wip_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
