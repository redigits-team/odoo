odoo.define('insurance_management.dashboard_form', function (require) {
"use strict";

const FormController = require('web.FormController');
const FormView = require('web.FormView');
const viewRegistry = require('web.view_registry');
const core = require('web.core');
const _t = core._t;

const DashboardFormController = FormController.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    start: function () {
        const self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$el.on('click', '.card-dashboard-clickable', self._onDashboardCardClicked.bind(self));
        });
    },

    /**
     * @override
     */
    destroy: function () {
        this.$el.off('click', '.card-dashboard-clickable');
        return this._super.apply(this, arguments);
    },

    /**
     * Handler when a dashboard card is clicked
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onDashboardCardClicked: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        const $card = $(ev.currentTarget);
        const actionName = $card.data('action');
        
        if (actionName) {
            // Extract text from h2 and convert to number
            let text = $card.find('h2').text();
            let numericValue = 0;
            
            // Extract numeric part from the string
            const match = text.match(/[\d,\.]+/);
            if (match) {
                numericValue = parseFloat(match[0].replace(/,/g, ''));
            }
            
            console.log("Card clicked:", actionName, "Value:", numericValue);
            
            // Only trigger action if card value is greater than 0
            if (numericValue > 0) {
                this.trigger_up('execute_action', {
                    action_data: {
                        name: actionName,
                        type: 'object',
                        context: this.initialState.context,
                    },
                    env: {
                        model: this.initialState.model,
                        resIDs: this.initialState.res_id ? [this.initialState.res_id] : [],
                        context: this.initialState.context,
                    },
                });
            }
        }
    },
});

const DashboardFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: DashboardFormController,
    }),
});

viewRegistry.add('dashboard_form', DashboardFormView);

return DashboardFormView;
});