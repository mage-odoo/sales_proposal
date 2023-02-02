/**@odoo-module **/
import publicWidget from "web.public.widget";
import { useService } from "@web/core/utils/hooks";
var ajax = require('web.ajax');

publicWidget.registry.SaleProposal = publicWidget.Widget.extend({
    
  setup(){this.dialogService = useService("dialog");},
    selector: '.o_portal_sale_proposal_sidebar',
    events: {
      'click #reject_button': '_onReject',
      'change #sales_proposal_qty': '_onQty',
      'change #sales_proposal_price_unit': '_onPriceUnit',
    },
    
    _onReject: function (ev) {
      ev.preventDefault();
      let self = this,$target = $(ev.currentTarget);
      var $proposal_id = $target.attr('data-order-id');
      const access_token = new URLSearchParams(window.location.search).get('access_token');
      var dict = {
        'proposal_id': $proposal_id,
        'access_token': access_token
      }
      var done=ajax.jsonRpc('/my/proposal/'+dict['proposal_id']+'/reject', 'call', {'data': dict, 'access_token':dict['access_token']});
        done.then(setTimeout(function(){ location.reload(); }, 200))
  },
    
    _onQty: function (ev) {
      let self = this,$target = $(ev.currentTarget);
      var $updatedQty = parseFloat($target.val());
      var $line_id = $target.attr('data-order-id');
      var $proposal_id = $target.attr('proposal-id');
      const access_token = new URLSearchParams(window.location.search).get('access_token');
      var dict = {
        'line_id': $line_id,
        'field':'product_uom_qty',
        'value': $updatedQty,
        'access_token': access_token,
        'proposal_id':$proposal_id 
      };
      self._updateElement("qty", dict);
    },

    _onPriceUnit: function (ev) {
      let self = this,$target = $(ev.currentTarget);
      var $updatedUnitPrice = parseFloat($target.val());
      var $line_id = $target.attr('data-order-id');
      var $proposal_id = $target.attr('proposal-id');
      const access_token = new URLSearchParams(window.location.search).get('access_token');
      var dict = {
        'line_id': $line_id,
        'field':'price_unit',
        'value': $updatedUnitPrice,
        'access_token': access_token,
        'proposal_id':$proposal_id 
      };
      self._updateElement("UnitPrice", dict);
    },

    _updateElement: function (perameter,dict) {
      var done=ajax.jsonRpc('/my/proposal/'+dict['proposal_id']+'/update', 'call', {'data': dict, 'access_token':dict['access_token']});
        done.then(setTimeout(function(){ location.reload(); }, 200))
    },
  });

  