{% load staticmedia %}

Ext.Direct.addProvider({
	'namespace': 'Gilbert.api',
	'url': '{% url gilbert:router %}',
	'type': 'remoting',
	'actions': {{% for gilbert_class in gilbert.core_api.gilbert_plugin_classes.values %}
		'{{ gilbert_class.gilbert_class_name }}': [{% for method in gilbert_class.gilbert_class_methods.values %}{
			'name': '{{ method.gilbert_method_name }}',
			'len': {{ method.gilbert_method_argc }}
		},{% endfor %}],{% endfor %}
	}
});

{% if not logged_in %}

Ext.onReady(function() {
	var login_form = new Ext.FormPanel({
		frame: true,
		bodyStyle: 'padding: 5px 5px 0',
		items: [
			{
				fieldLabel: 'Username',
				name: 'username',
				xtype: 'textfield',
			},
			{
				fieldLabel: 'Password',
				name: 'password',
				xtype: 'textfield',
				inputType: 'password',
			}
		],
		buttons: [
			{
				text: 'Login',
				handler: function(sender) {
					// document.location.reload();
					var the_form = login_form.getForm().el.dom;
					var username = the_form[0].value;
					var password = the_form[1].value;
					Gilbert.api.auth.login(username, password, function(result) {
						if (result) {
							document.location.reload();
						} else {
							Ext.MessageBox.alert('Login failed', 'Unable to authenticate.', function() {
								login_form.getForm().reset();
							});
						}
					});
				}
			}
		],
	});
	var login_window = new Ext.Window({
		title: 'Login',
		closable: false,
		width: 266,
		height: 130,
		layout: 'fit',
		items: login_form,
	});
	login_window.show();
});


{% else %}

Ext.ns('Gilbert', 'Gilbert.ui', 'Gilbert.models', 'Gilbert.plugins');

{% for app_label, models in gilbert.model_registry.items %}Ext.Direct.addProvider({
	'namespace': 'Gilbert.models.{{ app_label }}',
	'url': '{% url gilbert:models app_label %}',
	'type': 'remoting',
	'actions': {{% for model_name, admin in models.items %}
		'{{ model_name }}': [{% for method in admin.gilbert_class_methods.values %}{
				'name': '{{ method.gilbert_method_name }}',
				'len': {{ method.gilbert_method_argc }}
			},{% endfor %}],{% endfor %}
	}
});{% endfor %}
{% for plugin in gilbert.plugin_registry.values %}Ext.Direct.addProvider({
	'namespace': 'Gilbert.plugins.{{ plugin.gilbert_plugin_name }}',
	'url': '{% url gilbert:plugins plugin.gilbert_plugin_name %}',
	'type': 'remoting',
	'actions': {{% for gilbert_class in plugin.gilbert_plugin_classes %}
		'{{ gilbert_class.gilbert_class_name }}': [{% for method in gilbert_class.gilbert_class_methods.values %}{}
			'name': '{{ method.gilbert_method_name }}',
			'len': {{ method.gilbert_method_argc }}
		},{% endfor %}],{% endfor %}
	}
});{% endfor %}

Gilbert.ui.Application = function(cfg) {
	Ext.apply(this, cfg, {
		title: '{{ gilbert.title }}',
	});
	this.addEvents({
		'ready': true,
		'beforeunload': true,
	});
	Ext.onReady(this.initApplication, this);
};

Ext.extend(Gilbert.ui.Application, Ext.util.Observable, {
	initApplication: function() {
		
		Ext.QuickTips.init();
		
		this.desktop = new Ext.Panel({
			region: 'center',
			border: false,
			padding: '5',
			bodyStyle: 'background: none;',
		});
		var desktop = this.desktop;
		
		this.toolbar = new Ext.Toolbar({
			region: 'north',
			autoHeight: true,
			items: [
			{
				xtype: 'tbtext',
				text: this.title,
				style: 'font-weight: bolder; font-size: larger; text-transform: uppercase;',
			},
			{
				xtype: 'tbseparator',
			}
			]
		});
		var toolbar = this.toolbar;
		
		this.viewport = new Ext.Viewport({
			renderTo: Ext.getBody(),
			layout: 'border',
			items: [
			toolbar,
			desktop,
			],
		});
		var viewport = this.viewport;
		
		var windows = new Ext.WindowGroup();
		
		this.createWindow = function(config, cls) {
			var win = new(cls || Ext.Window)(Ext.applyIf(config || {},
			{
				renderTo: desktop.el,
				manager: windows,
				constrainHeader: true,
				maximizable: true,
			}));
			win.render(desktop.el);
			return win;
		};
		var createWindow = this.createWindow;
		
		if (this.plugins) {
			for (var pluginNum = 0; pluginNum < this.plugins.length; pluginNum++) {
				this.plugins[pluginNum].initWithApp(this);
			};
		};
		
		if (this.user) {
			var user = this.user;
			toolbar.add({ xtype: 'tbfill' });
			toolbar.add({ xtype: 'tbseparator' });
			toolbar.add({
				xtype: 'button',
				text: '<b>' + user + '</b>',
				style: 'font-weight: bolder !important; font-size: smaller !important; text-transform: uppercase !important;',
				menu: [
				{
					text: 'Change password',
					handler: function(button, event) {
						var edit_window = createWindow({
							layout: 'fit',
							title: 'Change password',
							width: 266,
							height: 170,
							layout: 'fit',
							items: _change_password_form = new Ext.FormPanel({
								frame: true,
								bodyStyle: 'padding: 5px 5px 0',
								items: [
									{
										fieldLabel: 'Current password',
										name: 'current_password',
										xtype: 'textfield',
										inputType: 'password',
									},
									{
										fieldLabel: 'New password',
										name: 'new_password',
										xtype: 'textfield',
										inputType: 'password',
									},
									{
										fieldLabel: 'New password (confirm)',
										name: 'new_password_confirm',
										xtype: 'textfield',
										inputType: 'password',
									}
								],
								buttons: [
									{
										text: 'Change password',
										handler: function(sender) {
											// document.location.reload();
											var the_form = _change_password_form.getForm().el.dom;
											var current_password = the_form[0].value;
											var new_password = the_form[1].value;
											var new_password_confirm = the_form[2].value;
											Gilbert.api.auth.passwd(current_password, new_password, new_password_confirm, function(result) {
												if (result) {
													Ext.MessageBox.alert('Password changed', 'Your password has been changed.');
												} else {
													Ext.MessageBox.alert('Password unchanged', 'Unable to change your password.', function() {
														_change_password_form.getForm().reset();
													});
												}
											});
										}
									}
								],
							}),
						});
						edit_window.show(this);
					},
				},
				{
					text: 'Log out',
					handler: function(button, event) {
						Gilbert.api.auth.logout(function(result) {
							if (result) {
								Ext.MessageBox.alert('Logout successful', 'You have been logged out.', function() {
									document.location.reload();
								});
							} else {
								Ext.MessageBox.alert('Logout failed', 'A bit odd, you might say.');
							}
						});
					},
				},
				],
			});
		};
		
		toolbar.doLayout();
		viewport.doLayout();
	},
});

Ext.BLANK_IMAGE_URL = '{% mediaurl "gilbert/extjs/resources/images/default/s.gif" %}';

Ext.onReady(function(){
	Gilbert.Application = new Gilbert.ui.Application({
		user: '{% filter force_escape %}{% firstof user.get_full_name user.username %}{% endfilter %}',
		plugins: [{% for plugin in gilbert.plugin_registry.values %}{% if plugin.gilbert_plugin_javascript %}
			{{ plugin.gilbert_plugin_javascript|safe }},
		{% endif %}{% endfor %}],
	});
});
{% endif %}