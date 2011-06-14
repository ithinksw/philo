Ext.ns('Gilbert.lib.models');


Gilbert.lib.models.Model = Ext.extend(Object, {
	
	constructor: function (config) {
		Ext.apply(this, config);
		this.drag_drop_group = 'Gilbert.lib.models.Model(' + this.app_label + ',' + this.name + ') ';
	},
	
	create_reader: function (config) {
		return new Ext.data.JsonReader(Ext.applyIf(config||{}, {}));
	},
	
	create_writer: function (config) {
		return new Ext.data.JsonWriter(Ext.applyIf(config||{}, {
			encode: false,
		}));
	},
	
	create_proxy: function (config) {
		return new Ext.data.DirectProxy(Ext.applyIf(config||{},{
			paramsAsHash: true,
			api: {
				read: this.api.data_read,
				create: this.api.data_create,
				update: this.api.data_update,
				destroy: this.api.data_destroy,
			},
		}));
	},
	
	create_store: function (config) {
		return new Ext.data.Store(Ext.applyIf(config||{},{
			proxy: this.create_proxy(),
			reader: this.create_reader(),
			writer: this.create_writer(),
			remoteSort: true,
		}));
	},
	
});


Gilbert.lib.models.ModelInstance = Ext.extend(Object, {
	
	constructor: function (model, pk, __unicode__) {
		this.model = model;
		this.pk = pk;
		this.__unicode__ = __unicode__
	},
	
});


Ext.data.Types.GILBERTMODELFOREIGNKEY = {
	
	convert: function (v, data) {
		if (v) {
			return new Gilbert.lib.models.ModelInstance(Gilbert.get_model(v.app_label, v.name), v.pk, v.__unicode__);
		} else {
			return null;
		}
	},
	
	sortType: Ext.data.SortTypes.none,
	
	type: 'gilbertmodelforeignkey',
	
}


Ext.data.Types.GILBERTMODELFILEFIELD = {
	
	convert: function (v, data) {
		if (v) {
			return v.url;
		} else {
			return null;
		}
	},
	
	sortType: Ext.data.SortTypes.none,
	
	type: 'gilbertmodelfilefield',
	
}