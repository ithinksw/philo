# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

	def forwards(self, orm):
		"Write your forwards methods here."
		ContentType = orm['contenttypes.ContentType']
		json_ct = ContentType.objects.get(app_label='philo', model='jsonvalue')
		fk_ct = ContentType.objects.get(app_label='philo', model='foreignkeyvalue')
		
		for attribute in orm.Attribute.objects.all():
			value = orm.JSONValue(value_json=attribute.value_json)
			value.save()
			attribute.value_content_type = json_ct
			attribute.value_object_id = value.id
			attribute.save()
		
		for relationship in orm.Relationship.objects.all():
			attribute = orm.Attribute(entity_content_type=relationship.entity_content_type, entity_object_id=relationship.entity_object_id, key=relationship.key)
			value = orm.ForeignKeyValue(content_type=relationship.value_content_type, object_id=relationship.value_object_id)
			value.save()
			attribute.value_content_type = fk_ct
			attribute.value_object_id = value.id
			attribute.save()
			relationship.delete()


	def backwards(self, orm):
		"Write your backwards methods here."
		if orm.ManyToManyValue.objects.count():
			raise NotImplementedError("ManyToManyValue objects cannot be unmigrated.")
		
		ContentType = orm['contenttypes.ContentType']
		json_ct = ContentType.objects.get(app_label='philo', model='jsonvalue')
		fk_ct = ContentType.objects.get(app_label='philo', model='foreignkeyvalue')
		
		for attribute in orm.Attribute.objects.all():
			if attribute.value_content_type == json_ct:
				value = orm.JSONValue.objects.get(pk=attribute.value_object_id)
				attribute.value_json = value.value_json
				attribute.save()
			elif attribute.value_content_type == fk_ct:
				value = orm.ForeignKeyValue.objects.get(pk=attribute.value_object_id)
				relationship = orm.Relationship(value_content_type=value.content_type, value_object_id=value.object_id, key=attribute.key, entity_content_type=attribute.entity_content_type, entity_object_id=attribute.entity_object_id)
				relationship.save()
				attribute.delete()
			else:
				ct = attribute.value_content_type
				raise NotImplementedError("Class cannot be converted: %s.%s" % (ct.app_label, ct.model))


	models = {
		'contenttypes.contenttype': {
			'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
			'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
		},
		'philo.attribute': {
			'Meta': {'unique_together': "(('key', 'entity_content_type', 'entity_object_id'), ('value_content_type', 'value_object_id'))", 'object_name': 'Attribute'},
			'entity_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_entity_set'", 'to': "orm['contenttypes.ContentType']"}),
			'entity_object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
			'value_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'attribute_value_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
			'value_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('philo.models.fields.JSONField', [], {})
		},
		'philo.collection': {
			'Meta': {'object_name': 'Collection'},
			'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
		},
		'philo.collectionmember': {
			'Meta': {'object_name': 'CollectionMember'},
			'collection': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'members'", 'to': "orm['philo.Collection']"}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'index': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
			'member_content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
			'member_object_id': ('django.db.models.fields.PositiveIntegerField', [], {})
		},
		'philo.contentlet': {
			'Meta': {'object_name': 'Contentlet'},
			'content': ('philo.models.fields.TemplateField', [], {}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
			'page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contentlets'", 'to': "orm['philo.Page']"})
		},
		'philo.contentreference': {
			'Meta': {'object_name': 'ContentReference'},
			'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
			'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
			'page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contentreferences'", 'to': "orm['philo.Page']"})
		},
		'philo.file': {
			'Meta': {'object_name': 'File'},
			'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'mimetype': ('django.db.models.fields.CharField', [], {'max_length': '255'})
		},
		'philo.foreignkeyvalue': {
			'Meta': {'object_name': 'ForeignKeyValue'},
			'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'foreign_key_value_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
		},
		'philo.jsonvalue': {
			'Meta': {'object_name': 'JSONValue'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'value': ('philo.models.fields.JSONField', [], {})
		},
		'philo.manytomanyvalue': {
			'Meta': {'object_name': 'ManyToManyValue'},
			'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'many_to_many_value_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'object_ids': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '300', 'null': 'True', 'blank': 'True'})
		},
		'philo.node': {
			'Meta': {'object_name': 'Node'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['philo.Node']"}),
			'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
			'view_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'node_view_set'", 'to': "orm['contenttypes.ContentType']"}),
			'view_object_id': ('django.db.models.fields.PositiveIntegerField', [], {})
		},
		'philo.page': {
			'Meta': {'object_name': 'Page'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'template': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'pages'", 'to': "orm['philo.Template']"}),
			'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
		},
		'philo.redirect': {
			'Meta': {'object_name': 'Redirect'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'status_code': ('django.db.models.fields.IntegerField', [], {'default': '302'}),
			'target': ('django.db.models.fields.CharField', [], {'max_length': '200'})
		},
        'philo.relationship': {
            'Meta': {'unique_together': "(('key', 'entity_content_type', 'entity_object_id'),)", 'object_name': 'Relationship'},
            'entity_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relationship_entity_set'", 'to': "orm['contenttypes.ContentType']"}),
            'entity_object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'relationship_value_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'value_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
		'philo.tag': {
			'Meta': {'object_name': 'Tag'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
			'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
		},
		'philo.template': {
			'Meta': {'object_name': 'Template'},
			'code': ('philo.models.fields.TemplateField', [], {}),
			'documentation': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'mimetype': ('django.db.models.fields.CharField', [], {'default': "'text/html'", 'max_length': '255'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
			'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['philo.Template']"}),
			'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'})
		}
	}

	complete_apps = ['philo']
