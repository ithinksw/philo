Ext.ns('Gilbert.lib.plugins.auth');


Gilbert.lib.plugins.auth.Plugin = Ext.extend(Gilbert.lib.plugins.Plugin, {
	
	init: function (application) {
		Gilbert.lib.plugins.auth.Plugin.superclass.init.call(this, application);
		
		var outer = this;
		
		Gilbert.api.plugins.auth.whoami(function (whoami) {
			application.mainmenu.add({
				xtype: 'tbfill',
			},{
				xtype: 'tbseparator',
			},{
				xtype: 'button',
				iconCls: 'icon-user-silhouette',
				text: '<span style="font-weight: bolder;">' + whoami + '</span>',
				menu: [{
						text: 'Theme',
						iconCls: 'icon-mask',
						menu: outer.build_theme_menu(),
					},{
						xtype: 'menuseparator',
					},{
					text: 'Change password',
					iconCls: 'icon-key--pencil',
					handler: function(button, event) {
						Gilbert.api.plugins.auth.get_passwd_form(function(formspec) {
							var formspec = formspec;
							for (var item_index in formspec.items) {
								var item = formspec.items[item_index];
								Ext.apply(item, {
									anchor: '100%',
								});
							}
							var change_password_form = new Gilbert.lib.ui.DjangoForm(Ext.applyIf({
								title: 'Change password',
								header: false,
								iconCls: 'icon-key--pencil',
								bodyStyle: 'padding: 10px;',
								baseCls: 'x-plain',
								autoScroll: true,
								api: {
									submit: Gilbert.api.plugins.auth.save_passwd_form,
								},
							}, formspec));
							var change_password_window = application.create_window({
								layout: 'fit',
								title: change_password_form.title,
								iconCls: change_password_form.iconCls,
								bodyStyle: 'padding: 5px; background: solid;',
								width: 360,
								height: 240,
								maximizable: false,
								items: [change_password_form],
								bbar: [
									'->',
									{
										text: 'Change password',
										iconCls: 'icon-key--pencil',
										handler: function(button, event) {
											change_password_form.getForm().submit({
												success: function(form, action) {
													Ext.MessageBox.alert('Password changed', 'Your password has been changed.');
													change_password_window.close();
												},
											});
										},
									}
								],
							});
							change_password_window.doLayout();
							change_password_window.show(button.el);
						});
						
					},
				},{
					text: 'Log out',
					iconCls: 'icon-door-open-out',
					handler: function(button, event) {
						Gilbert.api.plugins.auth.logout(function(success) {
							if (success) {
								window.onbeforeunload = undefined;
								document.location.reload();
							} else {
								Ext.MessageBox.alert('Log out failed', 'You have <strong>not</strong> been logged out. This could mean that your connection with the server has been severed. Please try again.');
							}
						})
					}
				}],
			});
			application.do_layout();
		});
	},
	
	build_theme_menu: function () {
		var application = this.application;
		
		var theme_switcher = function (menuitem) {
			var theme_name = menuitem.theme_name;
			Gilbert.api.plugins.auth.set_preference('gilbert.theme', theme_name, function () {
				application._set_theme(theme_name);
				application.do_layout();
				application.windows.each(function (win) {
					win.doLayout();
				});
			});
		};
		
		var menu = [];
		
		Ext.each(document.getElementsByClassName('gilbert.theme'), function (theme_element) {
			var theme_id = theme_element.id;
			var theme_name = theme_id.match(/gilbert.theme.(.*)/)[1];
			var current_theme = false;
			if (!theme_element.disabled) {
				current_theme = true;
			}
			
			
			menu.push({
				text: theme_name.capfirst(),
				checked: current_theme,
				group: 'theme',
				theme_name: theme_name,
				handler: theme_switcher,
			});
		});
		
		return menu;
	},
	
});


Gilbert.on('ready', function (application) {
	application.register_plugin('auth', new Gilbert.lib.plugins.auth.Plugin());
});