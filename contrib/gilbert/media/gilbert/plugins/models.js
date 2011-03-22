Ext.ns('Gilbert.lib.plugins.models.ui');


Ext.override(Gilbert.lib.models.Model, {
	create_new_form: function (callback, config) {
		var model = this;
		var config = config;
		model.api.get_form({}, function (formspec) {
			var formspec = formspec;
			for (var item_index in formspec.items) {
				var item = formspec.items[item_index];
				Ext.apply(item, {
					anchor: '100%',
				});
			}
			var form_panel = new Gilbert.lib.ui.DjangoForm(Ext.applyIf(Ext.applyIf(config||{},{
				title: 'New '+model.verbose_name,
				header: false,
				iconCls: 'icon-plus',
				baseCls: 'x-plain',
				autoScroll: true,
				api: {
					submit: model.api.save_form,
				},
			}), formspec));
			callback(form_panel);
		});
	},
	create_edit_form: function (callback, pk, config) {
		var model = this;
		var config = config;
		model.api.get_form({'pk': pk}, function (formspec) {
			var formspec = formspec;
			for (var item_index in formspec.items) {
				var item = formspec.items[item_index];
				Ext.apply(item, {
					anchor: '100%',
				});
			}
			callback(new Gilbert.lib.ui.DjangoForm(Ext.applyIf(Ext.applyIf(config||{},{
				title: 'Editing '+model.verbose_name+' ('+pk+')',
				header: false,
				iconCls: 'icon-pencil',
				baseCls: 'x-plain',
				autoScroll: true,
				api: {
					submit: model.api.save_form,
				},
				baseParams: {
					pk: pk,
				},
			}), formspec)));
		});
	},
});


Gilbert.lib.plugins.models.ui.ModelPanel = Ext.extend(Ext.Panel, {
	constructor: function (model, plugin, config) {
		var model = this.model = model;
		var plugin = this.plugin = plugin;
		var application = this.application = plugin.application;
		var outer = this;
		
		var store = this.store = model.create_store({
			autoLoad: true,
			autoDestroy: true,
			autoSave: false,
			baseParams: {
				start: 0,
				limit: 25,
			},
		});
		
		var grid = this.grid = new Ext.grid.GridPanel({
			ddGroup: model.drag_drop_group,
			enableDragDrop: true,
			loadMask: true,
			store: store,
			columns: model.columns,
			columnLines: true,
			stripeRows: true,
			viewConfig: {
				forceFit: true,
			},
			selModel: new Ext.grid.RowSelectionModel(),
			bbar: new Ext.PagingToolbar({
				pageSize: 25,
				store: store,
				displayInfo: true,
				displayMsg: 'Displaying '+model.verbose_name_plural+' {0} - {1} of {2}',
				emptyMsg: 'No '+model.verbose_name_plural+' to display',
				items: (function () {
					if (model.searchable) {
						return [
							{
								xtype: 'tbseparator',
							},
							new Ext.ux.form.SearchField({
								store: store,
							}),
						];
					} else {
						return [];
					}
				})(),
			}),
		});
		
		var new_action = this.new_action = new Ext.Action({
			text: 'New ' + model.verbose_name,
			iconCls: 'icon-plus',
			handler: function () {
				plugin.create_instance_window(model, undefined, function (win) {
					win.on('saved', function () {
						store.reload();
					});
					win.show();
				});
			},
		});
		
		var edit_action = this.edit_action = new Ext.Action({
			disabled: true,
			text: 'Edit',
			iconCls: 'icon-pencil',
			handler: function () {
				Ext.each(grid.getSelectionModel().getSelections(), function (record, index) {
					plugin.create_instance_window(model, record.id, function (win) {
						win.on('saved', function () {
							store.reload();
						});
						win.show();
					});
				});
			}
		});
		
		var delete_action = this.delete_action = new Ext.Action({
			disabled: true,
			text: 'Delete',
			iconCls: 'icon-minus',
			handler: function () {
				var records = grid.getSelectionModel().getSelections();
				var pks = [];
				Ext.each(records, function (record, index) {
					pks.push(record.id);
				});
				model.api.data_destroy_consequences(pks, function (consequences) {
					var convert_consequences_array = function (consequences) {
						var last_parent = consequences[0];
						Ext.each(consequences, function (consequence, index) {
							if (index != 0) {
								if (!Ext.isArray(consequence)) {
									last_parent = consequence;
								} else {
									last_parent['children'] = convert_consequences_array(consequence);
									delete consequences[index];
								}
							}
						});
						new_consequences = [];
						Ext.each(consequences, function (consequence) {
							if (consequence) {
								var new_consequence = {};
								if (!consequence['children']) {
									new_consequence['leaf'] = true;
								} else {
									new_consequence['leaf'] = false;
									new_consequence['children'] = consequence['children'];
								}
								var app_label = consequence['app_label'];
								var name = consequence['name'];
								var model = Gilbert.get_model(app_label, name);
								if (model) {
									new_consequence['text'] = consequence['__unicode__'];
									new_consequence['iconCls'] = model.iconCls;
								} else {
									new_consequence['text'] = '(' + consequence['name'] + ') ' + consequence['__unicode__'];
									new_consequence['iconCls'] = 'icon-block';
								}
								new_consequence['disabled'] = true;
								new_consequences.push(new_consequence);
							}
						});
						return new_consequences;
					};
					
					var tree = this.tree = new Ext.tree.TreePanel({
						loader: new Ext.tree.TreeLoader(),
						enableDD: false,
						animate: false,
						trackMouseOver: false,
						autoScroll: true,
						root: {
							'disabled': true,
							'text': 'To be deleted',
							'iconCls': 'icon-minus',
							'leaf': false,
							'children': convert_consequences_array(consequences),
						},
						useArrows: true,
						rootVisible: false,
						region: 'center',
					});
					
					var consequences_win = application.create_window({
						layout: 'border',
						width: 300,
						height: 300,
						modal: true,
						title: 'Delete ' + model.verbose_name_plural,
						iconCls: 'icon-minus',
						items: [
							{
								region: 'north',
								xtype: 'panel',
								html: 'Are you sure you want to delete these ' + model.verbose_name_plural + '?',
								bodyStyle: 'padding: 15px;',
							},
							tree,
						],
						bbar: [
							{
								xtype: 'button',
								text: 'Cancel',
								handler: function () {
									consequences_win.close();
								},
							},
							'->',
							{
								xtype: 'button',
								text: 'Yes',
								handler: function () {
									consequences_win.close();
									store.remove(records);
									store.save();
									store.reload();
								},
							},
						],
					});
					
					consequences_win.show();
				});
			}
		});
		
		grid.on('cellcontextmenu', function (grid, rowIndex, cellIndex, e) {
			e.stopEvent();
			selmodel = grid.getSelectionModel();
			if (!selmodel.isSelected(rowIndex)) {
				selmodel.selectRow(rowIndex, false);
			}
			var contextmenu = new Ext.menu.Menu({
				items: [
					edit_action,
					delete_action,
				],
			});
			contextmenu.showAt(e.xy);
		});
		
		grid.getSelectionModel().on('selectionchange', function (selmodel) {
			if (selmodel.hasSelection()) {
				edit_action.setDisabled(false);
				delete_action.setDisabled(false);
			} else {
				edit_action.setDisabled(true);
				delete_action.setDisabled(true);
			}
		});
		
		Gilbert.lib.plugins.models.ui.ModelPanel.superclass.constructor.call(this, Ext.applyIf(config||{}, {
			layout: 'fit',
			tbar: new Ext.Toolbar({
				items: [
					new_action,
					{ xtype: 'tbseparator' },
					edit_action,
					delete_action,
					'->',
					{
						text: 'Advanced',
						iconCls: 'icon-gear',
						disabled: true,
						menu: [],
					},
				],
			}),
			items: [grid],
		}));
	},
});


Gilbert.lib.plugins.models.Plugin = Ext.extend(Gilbert.lib.plugins.Plugin, {
	
	init: function (application) {
		Gilbert.lib.plugins.models.Plugin.superclass.init.call(this, application);
		
		var new_menu = this.new_menu = new Ext.menu.Menu();
		var manage_menu = this.manage_menu = new Ext.menu.Menu();
		
		application.mainmenu.insert(2, {
			xtype: 'button',
			iconCls: 'icon-plus',
			text: 'New',
			menu: new_menu,
		});
		
		application.mainmenu.insert(3, {
			xtype: 'button',
			iconCls: 'icon-databases',
			text: 'Manage',
			menu: manage_menu,
		});
		
		application.do_layout();
		
		Ext.iterate(application.models, function (app_label, models) {
			Ext.iterate(models, function (name, model) {
				this.handle_new_model(model);
			}, this);
		}, this);
		
		application.on('model_registered', function (model) {
			this.handle_new_model(model);
		}, this);
	},
	
	handle_new_model: function (model) {
		var outer = this;
		model.api.has_add_permission(function (has_add_permission) {
			if (has_add_permission) {
				outer.add_to_new_menu(model);
			}
		});
		model.api.has_read_permission(function (has_read_permission) {
			if (has_read_permission) {
				outer.add_to_manage_menu(model);
			}
		});
	},
	
	add_to_new_menu: function (model) {
		var outer = this;
		this.new_menu.add({
			text: model.verbose_name.capfirst(),
			iconCls: model.iconCls,
			model: model,
			handler: function (button, event) {
				outer.create_instance_window(this.model, undefined, function (win) {
					win.show();
				});
			},
		});
	},
	
	add_to_manage_menu: function (model) {
		var outer = this;
		this.manage_menu.add({
			text: model.verbose_name_plural.capfirst(),
			iconCls: model.iconCls,
			model: model,
			handler: function (button, event) {
				var win = outer.create_model_management_window(this.model);
				win.show(button.el);
			},
		});
	},
	
	create_model_management_window: function (model, config, cls) {
		var model = model;
		var panel = new Gilbert.lib.plugins.models.ui.ModelPanel(model, this);
		var win = this.application.create_window(Ext.applyIf(config||{},{
			layout: 'fit',
			title: model.verbose_name_plural.capfirst(),
			iconCls: model.iconCls,
			width: 640,
			height: 320,
			maximizable: true,
			items: [panel],
		}), cls);
		return win;
	},
	
	create_instance_window: function (model, pk, callback, config, cls) {
		var pk = pk;
		var callback = callback;
		var application = this.application;
		var outer = this;
		
		var form_callback = function (form) {
			var oldform = form;
			var win = application.create_window({
				layout: 'fit',
				title: form.title,
				iconCls: form.iconCls,
				bodyStyle: 'padding: 5px; background: solid;',
				width: 640,
				height: 320,
				maximizable: true,
				items: [form],
				bbar: [
					'->',
					{
						xtype: 'button',
						text: 'Save and Close',
						iconCls: 'icon-database-import',
						handler: function (button) {
							var loading_mask = new Ext.LoadMask(win.body, {
								msg: 'Saving...',
								removeMask: true,
							});
							loading_mask.show();
							win.items.items[0].getForm().submit({
								success: function (form, action) {
									loading_mask.hide();
									win.fireEvent('saved');
									win.close();
								},
								failure: function (form, action) {
									loading_mask.hide();
								},
							});
						}
					},
					{
						xtype: 'button',
						text: 'Save',
						iconCls: 'icon-database-import',
						handler: function (button) {
							var loading_mask = new Ext.LoadMask(win.body, {
								msg: 'Saving...',
								removeMask: true,
							});
							loading_mask.show();
							win.items.items[0].getForm().submit({
								success: function (form, action) {
									win.fireEvent('saved');
									var pk = action.result.pk;
									model.create_edit_form(function (newform) {
										win.remove(oldform);
										win.add(newform);
										loading_mask.hide();
										win.setTitle(newform.title);
										win.setIconClass(newform.iconCls);
										win.doLayout();
									}, pk);
								},
								failure: function (form, action) {
									loading_mask.hide();
								},
							});
						},
					},
				],
			});
			win.addEvents({
				'saved': true,
			});
			callback(win);
		};

		if (pk) {
			model.create_edit_form(form_callback, pk, {
				bodyStyle: 'padding: 10px;',
			});
		} else {
			model.create_new_form(form_callback, {
				bodyStyle: 'padding: 10px;',
			});
		}
	},
	
});


Gilbert.on('ready', function (application) {
	application.register_plugin('auth', new Gilbert.lib.plugins.models.Plugin());
});
