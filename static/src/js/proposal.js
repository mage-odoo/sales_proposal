/**@odoo-module **/
import publicWidget from "web.public.widget";
var ajax = require('web.ajax');

  publicWidget.registry.SaleProposal = publicWidget.Widget.extend({
    selector: '.o_portal_sale_proposal_sidebar',
    events: {
      'click #accept_button': '_onAccept',
      'change #sales_proposal_qty': '_onQty',
      'change #sales_proposal_price_unit': '_onPriceUnit',
    },
    
    _onAccept: function (ev) {
      ev.preventDefault();
      console.log(ev)
      console.log(ev.currentTarget.value)
      console.log("called ");
    },

    _onQty: function (ev) {
      let self = this,$target = $(ev.currentTarget);
      var $updatedQty = parseFloat($target.val());
      var $line_id = $target.attr('data-order-id');
      var $proposal_id = $target.attr('proposal-id');
      const access_token = new URLSearchParams(window.location.search).get('access_token');
      // var $parent = $(ev.target).closest('.o_portal_sale_proposal_sidebar');
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
      // var $parent = $(ev.target).closest('.o_portal_sale_proposal_sidebar');
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
