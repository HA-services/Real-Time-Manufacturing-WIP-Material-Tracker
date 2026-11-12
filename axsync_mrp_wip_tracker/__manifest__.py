# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
{
    'name': 'Manufacturing WIP Tracker',
    'summary': 'WIP dashboard, material consumption, variance, shortage and scrap reporting for Manufacturing',
    'description': 'AXSync Real-Time Manufacturing WIP & Material Tracker. Read-only reporting on top of standard Odoo Manufacturing.',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'author': 'AXSync',
    'website': 'https://www.axsync.com',
    'license': 'OPL-1',
    'price': 95.00,
    'currency': 'USD',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'security/axsync_wip_security.xml',
        'views/wip_production_views.xml',
        'views/wip_component_views.xml',
        'views/wip_scrap_views.xml',
        'views/wip_workcenter_views.xml',
        'views/wip_dashboard_views.xml',
        'views/wip_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'axsync_mrp_wip_tracker/static/src/scss/axsync_wip_dashboard.scss',
            'axsync_mrp_wip_tracker/static/src/js/axsync_wip_dashboard.js',
            'axsync_mrp_wip_tracker/static/src/xml/axsync_wip_dashboard.xml',
        ],
    },
    'images': [
        'static/description/axsync_banner.png',
        'static/description/axsync_dashboard_screenshot.png',
        'static/description/axsync_screenshot_1.png',
        'static/description/axsync_screenshot_2.png',
        'static/description/axsync_screenshot_3.png',
        'static/description/axsync_screenshot_4.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
