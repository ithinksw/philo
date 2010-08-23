GILBERT_PLUGINS.push(new (function() {
	return {
		init: function(application) {
			if (GILBERT_LOGGED_IN) {
				application.on('ready', this.addUserMenu, this, {
					single: true,
				});
			} else {
				application.on('ready', this.showLoginWindow, this, {
					single: true,
				});
			}
		},
		addUserMenu: function(application) {
			Gilbert.api.auth.whoami(function(result) {
				application.mainmenu.add({
					xtype: 'tbfill',
				},{
					xtype: 'tbseparator',
				},{
					xtype: 'button',
					iconCls: 'user-silhouette',
					text: '<span style="font-weight: bolder;">' + result + '</span>',
					menu: [{
						text: 'Change password',
						iconCls: 'key--pencil',
						handler: function(button, event) {
							var change_password_window = application.createWindow({
								layout: 'fit',
								resizable: false,
								title: 'Change password',
								iconCls: 'key--pencil',
								width: 266,
								height: 170,
								items: change_password_form = new Ext.FormPanel({
									frame: true,
									bodyStyle: 'padding: 5px 5px 0',
									items: [{
										fieldLabel: 'Current password',
										name: 'current_password',
										xtype: 'textfield',
										inputType: 'password',
									},{
										fieldLabel: 'New password',
										name: 'new_password',
										xtype: 'textfield',
										inputType: 'password',
									},{
										fieldLabel: 'New password (confirm)',
										name: 'new_password_confirm',
										xtype: 'textfield',
										inputType: 'password',
									}],
									buttons: [{
										text: 'Change password',
										iconCls: 'key--pencil',
										handler: function(button, event) {
											var the_form = change_password_form.getForm().el.dom;
											var current_password = the_form[0].value;
											var new_password = the_form[1].value;
											var new_password_confirm = the_form[2].value;
											Gilbert.api.auth.passwd(current_password, new_password, new_password_confirm, function(result) {
												if (result) {
													Ext.MessageBox.alert('Password changed', 'Your password has been changed.');
												} else {
													Ext.MessageBox.alert('Password unchanged', 'Unable to change your password.', function() {
														change_password_form.getForm().reset();
													});
												}
											});
										},
									}],
								})
							});
							change_password_window.show();
						},
					},{
						text: 'Log out',
						iconCls: 'door-open-out',
						handler: function(button, event) {
							Gilbert.api.auth.logout(function(result) {
								if (result) {
									document.location.reload();
								} else {
									Ext.MessageBox.alert('Log out failed', 'You have <strong>not</strong> been logged out. This could mean that your connection with the server has been severed. Please try again.');
								}
							})
						}
					}],
				});
				application.doLayout();
			});
		},
		showLoginWindow: function(application) {
			application.mainmenu.hide();
			application.doLayout();
			var login_window = application.createWindow({
				header: false,
				closable: false,
				resizable: false,
				draggable: false,
				width: 266,
				height: 130,
				layout: 'fit',
				items: login_form = new Ext.FormPanel({
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
							text: 'Log in',
							iconCls: 'door-open-in',
							handler: function(button, event) {
								var the_form = login_form.getForm().el.dom;
								var username = the_form[0].value;
								var password = the_form[1].value;
								Gilbert.api.auth.login(username, password, function(result) {
									if (result) {
										document.location.reload();
									} else {
										Ext.MessageBox.alert('Log in failed', 'Unable to authenticate using the credentials provided. Please try again.', function() {
											login_form.getForm().reset();
										});
									}
								});
							}
						}
					],
				}),
			});
			login_window.show();
		},
	}
})());