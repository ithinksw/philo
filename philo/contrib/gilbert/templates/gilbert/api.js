Ext.Ajax.on('beforerequest', function (connection, options) {
	if (!(/^http:.*/.test(options.url) || /^https:.*/.test(options.url))) {
		options.headers = Ext.apply(options.headers||{}, {
			'X-CSRFToken': '{{ csrf_token }}',
		});
	}
});


Ext.ns('Gilbert.api');
{% for provider in providers %}Ext.Direct.addProvider({{ provider|safe }});{% endfor %}


Gilbert.on('ready', function (application) {{% for app_label, models in model_registry.items %}{% for name, admin in models.items %}
	application.register_model('{{ app_label }}', '{{ name }}', new Gilbert.lib.models.Model({
		app_label: '{{ app_label }}',
		name: '{{ name }}',
		verbose_name: '{{ admin.model_meta.verbose_name }}',
		verbose_name_plural: '{{ admin.model_meta.verbose_name_plural }}',
		searchable: {% if admin.search_fields %}true{% else %}false{% endif %},
		columns: {{ admin.data_columns_spec_json|safe }},
		iconCls: 'icon-{{ admin.icon_name }}',
		api: Gilbert.api.models.{{ app_label }}.{{ name }},
	}));
{% endfor %}{% endfor %}});


Gilbert.on('ready', function (application) {
	application.register_plugin('_about_window', {
		init: function(application) {
			var application = this.application = application;
			
			var plugin = this;
			
			application.mainmenu.remove(application.mainmenu.items.items[0]);
			
			application.mainmenu.insert(0, {
				xtype: 'button',
				text: '<span style="font-weight: bolder; text-transform: uppercase;">{{ gilbert.title|safe }}</span>',
				handler: function(button, event) {
					plugin.showAbout(button);
				},
			});
		},
		showAbout: function(sender) {
			var application = this.application;
			
			if (!this.about_window) {
				var about_window = this.about_window = application.create_window({
					height: 176,
					width: 284,
					header: false,
					html: '<h1>{{ gilbert.title|safe }}</h1><h2>Version {{ gilbert.version|safe }}</h2><div id="credits">{{ gilbert.credits|safe }}</div>',
					bodyStyle: 'background: none; font-size: larger; line-height: 1.4em; text-align: center;',
					modal: true,
					closeAction: 'hide',
					closable: false,
					resizable: false,
					draggable: false,
					minimizable: false,
					fbar: [{
						text: 'OK',
						handler: function(button, event) {
							about_window.hide();
						}
					}],
					defaultButton: 0,
				});
			}
			this.about_window.show();
			this.about_window.focus();
		},
	});
});