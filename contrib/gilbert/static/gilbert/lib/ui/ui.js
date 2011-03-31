Ext.ns('Gilbert.lib.ui');


Gilbert.lib.ui.DjangoForm = Ext.extend(Ext.FormPanel, {
	initComponent: function () {
		/*if (this.djangoFields) {
			this.initDjangoForm();
		}*/
		Gilbert.lib.ui.DjangoForm.superclass.initComponent.call(this);
	},
/*	initDjangoForm: function () {
		this.items = this.items || [];
		Ext.each(this.djangoFields, this.addDjangoField, this);
	},
	addDjangoField: function(field, index, all) {
		this.items.push(Gilbert.lib.ui.DjangoFormHelper.get_field_converter(field.type)(field));
	},*/
});


Gilbert.lib.ui.HTMLWindow = Ext.extend(Ext.Window, {
	html_source: undefined,
	onRender: function() {
		if (this.html_source) {
			this.bodyCfg = {
				tag: 'iframe',
				cls: this.bodyCls,
			};
			Gilbert.lib.ui.HTMLWindow.superclass.onRender.apply(this, arguments);
			var iframe = this.body.dom;
			var doc = iframe.document;
			if (iframe.contentDocument) {
				doc = iframe.contentDocument;
			} else if (iframe.contentWindow) {
				doc = iframe.contentWindow.document;
			}
			doc.open();
			doc.writeln(this.html_source);
			doc.close();
		} else {
			Gilbert.lib.ui.HTMLWindow.superclass.onRender.apply(this, arguments);
		}
	}
});