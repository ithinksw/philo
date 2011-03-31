Ext.override(String, {
	
	capfirst: function () {
		return this.substr(0, 1).toUpperCase() + this.substr(1);
	},
	
});


Gilbert = new Gilbert.lib.app.Application(Gilbert);