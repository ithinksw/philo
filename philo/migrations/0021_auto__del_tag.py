# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'Tag'
        db.delete_table('philo_tag')


    def backwards(self, orm):
        
        # Adding model 'Tag'
        db.create_table('philo_tag', (
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, unique=True, db_index=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('philo', ['Tag'])


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'philo.attribute': {
            'Meta': {'unique_together': "(('key', 'entity_content_type', 'entity_object_id'), ('value_content_type', 'value_object_id'))", 'object_name': 'Attribute'},
            'entity_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_entity_set'", 'to': "orm['contenttypes.ContentType']"}),
            'entity_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'value_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'attribute_value_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'value_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'})
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contentlets'", 'to': "orm['philo.Page']"})
        },
        'philo.contentreference': {
            'Meta': {'object_name': 'ContentReference'},
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contentreferences'", 'to': "orm['philo.Page']"})
        },
        'philo.file': {
            'Meta': {'object_name': 'File'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mimetype': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'philo.foreignkeyvalue': {
            'Meta': {'object_name': 'ForeignKeyValue'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'})
        },
        'philo.jsonvalue': {
            'Meta': {'object_name': 'JSONValue'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('philo.models.fields.JSONField', [], {'default': "'null'", 'db_index': 'True'})
        },
        'philo.manytomanyvalue': {
            'Meta': {'object_name': 'ManyToManyValue'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'values': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['philo.ForeignKeyValue']", 'null': 'True', 'blank': 'True'})
        },
        'philo.node': {
            'Meta': {'unique_together': "(('parent', 'slug'),)", 'object_name': 'Node'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['philo.Node']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'view_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'node_view_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'view_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
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
            'reversing_parameters': ('philo.models.fields.JSONField', [], {'blank': 'True'}),
            'status_code': ('django.db.models.fields.IntegerField', [], {'default': '302'}),
            'target_node': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'philo_redirect_related'", 'null': 'True', 'to': "orm['philo.Node']"}),
            'url_or_subpath': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'philo.template': {
            'Meta': {'unique_together': "(('parent', 'slug'),)", 'object_name': 'Template'},
            'code': ('philo.models.fields.TemplateField', [], {}),
            'documentation': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'mimetype': ('django.db.models.fields.CharField', [], {'default': "'text/html'", 'max_length': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['philo.Template']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['philo']
