Ext.ns('Gilbert.lib.app')


Gilbert.lib.app.Desktop = Ext.extend(Ext.Panel, {
	
	constructor: function(application, config) {
		var application = this.application = application;
		Gilbert.lib.app.Desktop.superclass.constructor.call(this, Ext.applyIf(config||{}, {
			region: 'center',
			border: false,
			padding: '5px',
			bodyStyle: 'background: none;',
		}));
	},
	
});


Gilbert.lib.app.MainMenu = Ext.extend(Ext.Toolbar, {
	
	constructor: function(application, config) {
		var application = this.application = application;
		Gilbert.lib.app.MainMenu.superclass.constructor.call(this, Ext.applyIf(config||{}, {
			region: 'north',
			autoHeight: true,
			items: [
				{
					xtype: 'tbtext',
					text: '<span style="font-weight: bolder; text-transform: uppercase;">Gilbert</span>',
				},
				{
					xtype: 'tbseparator',
				},
			],
		}));
	},
	
});


Gilbert.lib.app.TaskBar = Ext.extend(Ext.Toolbar, {
	
	constructor: function(application, config) {
		var application = this.application = application;
		Gilbert.lib.app.TaskBar.superclass.constructor.call(this, Ext.applyIf(config||{}, {
			region: 'south',
			enableOverflow: true,
			autoHeight: true,
			items: [],
			plugins: [
				new Ext.ux.ToolbarReorderer({
					defaultReorderable: true,
				}),
			],
		}));
	},
	
	get_button_for_window: function(win) {
		return this.find('represented_window', win)[0];
	},
	
	default_button_handler: function(button) {
		var win = button.represented_window;
		if (this.active_window === win) {
			win.minimize();
		} else {
			win.show();
		}
	},
	
	register_window: function(win) {
		win.on('show', this.window_shown, this);
		win.on('hide', this.window_hidden, this);
		win.on('minimize', this.window_minimize, this);
		win.on('deactivate', this.window_deactivated, this);
		win.on('activate', this.window_activated, this);
		win.on('titlechange', this.window_titlechanged, this);
		win.on('iconchange', this.window_iconchanged, this);
		
		var button = new Ext.Button({
			text: win.title,
			iconCls: win.iconCls,
			enableToggle: true,
			allowDepress: false,
			width: 200,
			hidden: true,
		});
		button.represented_window = win;
		button.setHandler(this.default_button_handler, this);
		
		this.add(button);
		
		win.on('destroy', this.window_destroyed, this);
	},
	
	window_destroyed: function(win) {
		this.remove(this.get_button_for_window(win));
		this.application.do_layout();
	},
	
	window_shown: function(win) {
		if (this.minimizing_window !== win) {
			this.get_button_for_window(win).show();
			this.application.do_layout();
		}
	},
	
	window_hidden: function(win) {
		if (this.minimizing_window !== win) {
			this.get_button_for_window(win).hide();
			this.application.do_layout();
		}
	},
	
	window_minimize: function(win) {
		var button = this.get_button_for_window(win);
		
		this.minimizing_window = win;
		win.hide(button.el, function () {
			this.minimizing_window = undefined;
			
			win.minimized = true;
			button.setText('<i>'+win.title+'</i>');
			button.setHandler(function (button) {
				var win = button.represented_window;
				
				win.minimized = false;
				button.setText(win.title);
				button.setHandler(this.default_button_handler, this);
				
				this.minimizing_window = win;
				win.show(button.el, function () {
					this.minimizing_window = undefined;
				}, this);
			}, this);
		}, this);
	},
	
	window_deactivated: function(win) {
		var button = this.get_button_for_window(win);
		button.toggle(false);
		button.setText(win.title);
		
		if (this.active_window === win) {
			this.active_window = undefined;
		}
	},
	
	window_activated: function(win) {
		var button = this.get_button_for_window(win);
		button.toggle(true);
		button.setText('<b>'+win.title+'</b>');
		
		this.active_window = win;
	},
	
	window_titlechanged: function(win) {
		var button = this.get_button_for_window(win);
		if (win.minimized) {
			button.setText('<i>'+win.title+'</i>');
		} else {
			button.setText(win.title);
		}
	},
	
	window_iconchanged: function(win) {
		var button = this.get_button_for_window(win);
		button.setIconClass(win.iconCls);
	},
	
});


Gilbert.lib.app.Application = Ext.extend(Ext.util.Observable, {
	
	constructor: function (config) {
		
		this.models = {};
		this.plugins = {};
		
		Ext.apply(this, config, {
			renderTo: Ext.getBody(),
		});
		
		Gilbert.lib.app.Application.superclass.constructor.call(this);
		
		this.addEvents({
			'ready': true,
			'model_registered': true,
			'plugin_registered': true,
			'window_created': true,
		});
		
		Ext.onReady(this.pre_init.createDelegate(this));
	},
	
	pre_init: function () {
		var outer = this;
		
		Gilbert.api.plugins.auth.get_preference('gilbert.background', function (background) {
			if (background) {
				outer.renderTo.setStyle('background', background);
			}
		});
		Gilbert.api.plugins.auth.get_preference('gilbert.theme', function (theme) {
			if (theme) {
				outer._set_theme(theme);
			}
			outer.init();
		});
	},
	
	_set_theme: function(theme) {
		var link_element = document.getElementById('gilbert.theme.' + theme);
		if (link_element) {
			Ext.each(document.getElementsByClassName('gilbert.theme'), function (theme_element) {
				if (theme_element != link_element) {
					theme_element.disabled = true;
				} else {
					theme_element.disabled = false;
				}
			});
		}
	},
	
	init: function () {
		Ext.QuickTips.init();
		
		var desktop = this.desktop = new Gilbert.lib.app.Desktop();
		var mainmenu = this.mainmenu = new Gilbert.lib.app.MainMenu(this);
		var taskbar = this.taskbar = new Gilbert.lib.app.TaskBar(this);
		var viewport = this.viewport = new Ext.Viewport({
			renderTo: this.renderTo,
			layout: 'border',
			items: [
				this.mainmenu,
				this.desktop,
				this.taskbar,
			],
		});
		
		var windows = this.windows = new Ext.WindowGroup();
		
		Ext.Direct.on('exception', function (exception) {
			if (exception.code == Ext.Direct.exceptions.TRANSPORT) {
				if (exception.xhr.status == 403) {
					window.alert('You have been unexpectedly logged out.');
					window.location.reload(true);
				}
			}
			if (exception.html) {
				var win = this.create_window({
					width: 400,
					height: 300,
					maximizable: true,
					minimizable: false,
					modal: true,
					html_source: exception.html,
				}, Gilbert.lib.ui.HTMLWindow);
				win.show();
			}
		}, this);
		
		var initial_plugins = this.plugins;
		this.plugins = {};
		
		Ext.iterate(initial_plugins, function (name, plugin, plugins) {
			this.register_plugin(name, plugin);
		}, this);
		
		this.do_layout();
		
		this.renderTo.on('contextmenu', Ext.emptyFn, null, {preventDefault: true});
		
		window.onbeforeunload = function (event) {
			var notice = 'You will lose all unsaved changes and windows.';
			var event = event || window.event;
			if (event) {
				event.returnValue = notice;
			}
		
			return notice;
		};
		
		this.fireEvent('ready', this);
	},
	
	create_window: function(config, cls) {
		var win = new(cls||Ext.Window)(Ext.applyIf(config||{},{
			renderTo: this.desktop.el,
			manager: this.windows,
			minimizable: true,
			constrainHeader: true,
		}));
		win.render(this.desktop.el);
		if (win.modal) {
			win.on('show', function () {
				this.mainmenu.hide();
				this.taskbar.hide();
				this.do_layout();
			}, this);
			win.on('hide', function () {
				this.taskbar.show();
				this.mainmenu.show();
				this.do_layout();
			}, this);
			win.on('close', function () {
				this.taskbar.show();
				this.mainmenu.show();
				this.do_layout();
			}, this);
		}
		this.taskbar.register_window(win);
		this.fireEvent('window_created', win);
		return win;
	},
	
	do_layout: function() {
		this.mainmenu.doLayout();
		this.taskbar.doLayout();
		this.viewport.doLayout();
	},
	
	register_plugin: function (name, plugin) {
		if (plugin.init(this) != false) {
			this.plugins[name] = plugin;
			this.fireEvent('plugin_registered', name, plugin, this);
		}
	},
	
	get_plugin: function (name) {
		return this.plugins[name];
	},
	
	register_model: function (app_label, name, model) {
		if (!this.models[app_label]) {
			this.models[app_label] = {};
		}
		this.models[app_label][name] = model;
		this.fireEvent('model_registered', name, model, this);
	},
	
	get_model: function (app_label, name) {
		if (!this.models[app_label]) {
			return undefined;
		}
		return this.models[app_label][name];
	},
	
});