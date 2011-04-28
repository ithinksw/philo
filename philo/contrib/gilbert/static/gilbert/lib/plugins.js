Ext.ns('Gilbert.lib.plugins');


Gilbert.lib.plugins.Plugin = Ext.extend(Object, {
	
	constructor: function (config) {
		Ext.apply(this, config);
	},
	
	init: function (application) {
		var application = this.application = application;
	}
	
});