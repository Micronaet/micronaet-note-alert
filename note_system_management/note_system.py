# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import base64
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class NoteDepartment(orm.Model):
    """ Model name: NoteDepartment
    """    
    _name = 'note.department'
    _description = 'Note department'
    
    _columns = {
        'name': fields.char('Department', size=64, required=True),
        'note': fields.text('Note'),
        }

class NoteType(orm.Model):
    """ Model name: NoteType
    """    
    _name = 'note.type'
    _description = 'Note type'
    
    _columns = {
        'name': fields.char(
            'Name', size=64, required=True),
        'note': fields.text('Note'),
        'department_ids': fields.many2many(
            'note.department', 'type_department_note_rel', 
            'type_id', 'department_id', 
            'Department'),
        'linked_image': fields.boolean('Linked image', 
            help='If checked use image from linked module, else store file'),
        'linked_object': fields.selection([
            ('product_id', 'Product'),
            ('partner_id', 'Partner'),
            ], 'Linked object', 
            help='For show image linked to object'),
        'linked_image_field': fields.char('Image field name', size=64, 
            help='Image field name of linked object'),            
        }

    _defaults = {
        'linked_object': lambda *x: 'product_id',
        }

class NoteImage(orm.Model):
    """ Model name: NoteImage
    """    
    # TODO
    _name = 'note.image'
    _description = 'Note image'

    # Parameters:
    _extension = 'png'
    _root_path = 'note_image_default'
    
    # -------------------------------------------------------------------------
    # Functional field:
    # -------------------------------------------------------------------------
    def _set_note_default_image(self, cr, uid, item_id, name, value, fnct_inv_arg=None, 
            context=None):
        ''' Write image as stored file when insert
        '''
        company_pool = self.pool.get('res.company')
        image_folder = os.path.expanduser(company_pool.get_base_local_folder(
            cr, uid, subfolder=self._root_path, context=context))

        filename = os.path.join(
            image_folder, '%s.%s' % (item_id, self._extension))

        image_file = open(filename, 'wb')
        if value:
            image_file.write(base64.decodestring(value))
        image_file.close()        
        return True
    
    def _get_note_default_image(self, cr, uid, ids, field, args, context=None):
        ''' Use base folder for get ID.png filename from filesystem
        '''
        company_pool = self.pool.get('res.company')        
        image_folder = os.path.expanduser(company_pool.get_base_local_folder(
            cr, uid, subfolder=self._root_path, context=context))

        res = {}
        for image in self.browse(cr, uid, ids, context=context):
            filename = os.path.join(
                image_folder, '%s.%s' % (image.id, self._extension))
            try:
                f = open(filename , 'rb')
                res[image.id] = base64.encodestring(f.read())
                f.close()
            except:
                res[image.id] = ''
        return res

    _columns = {
        'name': fields.char('Image', size=64, required=True),
        'note': fields.text('Note'),
        'type_id': fields.many2one('note.type', 'Type'),
        'image': fields.function(_get_note_default_image, 
            fnct_inv=_set_note_default_image, string='Image',
            type='binary', method=True),
        }       

class NoteNote(orm.Model):
    """ Model name: NoteNote
    """    
    _name = 'note.note'
    _description = 'Note'
    _order = 'date'
    
    # Parameters:
    _extension = 'png'
    _root_path = 'note_image'

    # -------------------------------------------------------------------------
    # Functional field:
    # -------------------------------------------------------------------------
    def _set_note_image(self, cr, uid, item_id, name, value, fnct_inv_arg=None, 
            context=None):
        ''' Write image as stored file when insert
        '''
        company_pool = self.pool.get('res.company')
        note_folder = os.path.expanduser(company_pool.get_base_local_folder(
            cr, uid, subfolder=self._root_path, context=context))

        filename = os.path.join(
            note_folder, '%s.%s' % (item_id, self._extension))
        image_file = open(filename, 'wb')
        if value:
            image_file.write(base64.decodestring(value))
        image_file.close()        
        return True
    
    def _get_note_image(self, cr, uid, ids, field, args, context=None):
        ''' Use base folder for get ID.png filename from filesystem
        '''
        company_pool = self.pool.get('res.company')        
        note_folder = os.path.expanduser(company_pool.get_base_local_folder(
            cr, uid, subfolder=self._root_path, context=context))

        res = {}
        for note in self.browse(cr, uid, ids, context=context):
            note_type = note.type_id
            linked_image = note_type.linked_image
            if note.image_id: # Static image
                res[note.id] = note.image_id.image                
            elif linked_image: # Linked category image
                res[note.id] = note.__getattribute__(
                    note_type.linked_object).__getattribute__(
                    note_type.linked_image_field)
            else: # Stored note file
                filename = os.path.join(
                    note_folder, '%s.%s' % (note.id, self._extension))
                try:
                    f = open(filename , 'rb')
                    res[note.id] = base64.encodestring(f.read())
                    f.close()
                except:
                    res[note.id] = ''
        return res

    _columns = {        
        'name': fields.char('Title', size=64, required=True),
        'type_id': fields.many2one('note.type', 'Type', required=True), 
        'create_uid': fields.many2one(
            'res.users', 'Created By', readonly=True),
        'date': fields.datetime('Date', required=True),
        'deadline': fields.date('Deadline date'),
        'description': fields.text('Description'),
        'overridable': fields.boolean('Overridable'),
        
        # Image block:
        'image': fields.function(_get_note_image, fnct_inv=_set_note_image, 
            type='binary', method=True, string='Image'),
        'image_id': fields.many2one('note.image', 'Static image'), 
        
        # Linked object for part.
        'product_id': fields.many2one('product.product', 'Product'), 
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        'order_id': fields.many2one('sale.order', 'Order'),
        'line_id': fields.many2one('sale.order.line', 'Order line'),
        }
         
    _defaults = {
        'date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
        }    

class NoteProductReport(orm.Model):
    """ Model name: NoteProductReport
    """    
    _name = 'note.product.report'
    _description = 'Note product report'

    _columns = {
        'name': fields.char('Report name', size=64, required=True),
        'note': fields.text('Note') ,
        }
    
class NoteProductReportLine(orm.Model):
    """ Model name: NoteProductReportLine
    """    
    _name = 'note.product.report.line'
    _description = 'Note product report'
    _order = 'sequence,id'
    
    _columns = {
        'name': fields.char('Title', size=64, required=True),
        'sequence': fields.integer('Sequence'), 
        'report_id': fields.many2one('note.product.report', 'Report'),
        'type_id': fields.many2one('note.type', 'Type', required=True),        
        }

class NoteProductReport(orm.Model):
    """ Model name: NoteProductReport
    """    
    _inherit = 'note.product.report'
    
    _columns = {
        'line_ids': fields.one2many(
            'note.product.report.line', 'report_id', 'Detail'), 
        }
    
class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """    
    _inherit = 'product.product'
    
    _columns = {
        'note_ids': fields.one2many('note.note', 'product_id', 'Note system'), 
        }

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'note_ids': fields.one2many('note.note', 'partner_id', 'Note system'), 
        }

class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """    
    _inherit = 'sale.order'
    
    _columns = {
        'note_ids': fields.one2many('note.note', 'order_id', 'Note system'), 
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
