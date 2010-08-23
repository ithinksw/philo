Ext.ns('Gilbert.lib');

Gilbert.lib.Desktop = Ext.extend(Ext.Panel, {
	constructor: function(config) {
		Gilbert.lib.Desktop.superclass.constructor.call(this, Ext.applyIf(config||{}, {
			region: 'center',
			border: false,
			padding: '5',
			bodyStyle: 'background: none;',
		}));
	},
});

Gilbert.lib.MainMenu = Ext.extend(Ext.Toolbar, {
	constructor: function(application) {
		var application = this.application = application;
		Gilbert.lib.MainMenu.superclass.constructor.call(this, {
			region: 'north',
			autoHeight: true,
		});
	},
});

Gilbert.lib.Application = Ext.extend(Ext.util.Observable, {
	constructor: function(config) {
		Ext.apply(this, config, {
			renderTo: Ext.getBody(),
			plugins: [],
			
		});
		Gilbert.lib.Application.superclass.constructor.call(this);
		this.addEvents({
			'ready': true,
		});
		this.init();
	},
	init: function() {
		Ext.QuickTips.init();
		
		var desktop = this.desktop = new Gilbert.lib.Desktop();
		var mainmenu = this.mainmenu = new Gilbert.lib.MainMenu(this);
		var viewport = this.viewport = new Ext.Viewport({
			renderTo: this.renderTo,
			layout: 'border',
			items: [
				this.mainmenu,
				this.desktop,
			],
		});
		var windows = this.windows = new Ext.WindowGroup();
		
		if (this.plugins) {
			if (Ext.isArray(this.plugins)) {
				for (var i = 0; i < this.plugins.length; i++) {
					this.plugins[i] = this.initPlugin(this.plugins[i]);
				}
			} else {
				this.plugins = this.initPlugin(this.plugins);
			}
		}
		
		this.doLayout();
		
		this.fireEvent('ready', this);
	},
	initPlugin: function(plugin) {
		plugin.init(this);
		return plugin;
	},
	createWindow: function(config, cls) {
		var win = new(cls||Ext.Window)(Ext.applyIf(config||{},{
			renderTo: this.desktop.el,
			manager: this.windows,
			constrainHeader: true,
		}));
		win.render(this.desktop.el);
		return win;
	},
	doLayout: function() {
		this.mainmenu.doLayout();
		this.viewport.doLayout();
	}
});