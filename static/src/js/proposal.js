/**@odoo-module **/
import publicWidget from "web.public.widget";
import { useService } from "@web/core/utils/hooks";
var ajax = require('web.ajax');

publicWidget.registry.SaleProposal = publicWidget.Widget.extend({
  setup(){this.dialogService = useService("dialog");},
    selector: '.o_portal_sale_proposal_sidebar',
    events: {
      'change #update_val': '_onUpdateQtyUnit',
    },
  _onUpdateQtyUnit: function (ev) { 
    let self = this,$target = $(ev.currentTarget);
    var $updatedQty = parseFloat($target.val());
    var $line_id = $target.attr('data-order-id');
    var $proposal_id = $target.attr('proposal-id');
    var $fieldname = $target.attr('updatefield');
    var $OldValField = $target.attr('old-value');
    const access_token = new URLSearchParams(window.location.search).get('access_token');
    var dict = {
        'line_id': $line_id,
        'field': $fieldname,
        'value': $updatedQty,
        'oldvalue':$OldValField,
        'access_token': access_token,
        'proposal_id':$proposal_id 
      };
      self._updateElement(dict);
  },
    _updateElement: function (dict) {
      var done=ajax.jsonRpc('/my/proposal/'+dict['proposal_id']+'/update', 'call', {'data': dict, 'access_token':dict['access_token']});
        done.then(setTimeout(function(){ location.reload(); }, 200))
    },
  });

  