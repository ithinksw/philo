# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Tag'
        db.create_table('philo_tag', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=255, db_index=True)),
        ))
        db.send_create_signal('philo', ['Tag'])

        # Adding model 'Attribute'
        db.create_table('philo_attribute', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entity_content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('entity_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('json_value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('philo', ['Attribute'])

        # Adding unique constraint on 'Attribute', fields ['key', 'entity_content_type', 'entity_object_id']
        db.create_unique('philo_attribute', ['key', 'entity_content_type_id', 'entity_object_id'])

        # Adding model 'Relationship'
        db.create_table('philo_relationship', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('entity_content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='relationship_entity_set', to=orm['contenttypes.ContentType'])),
            ('entity_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('value_content_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='relationship_value_set', null=True, to=orm['contenttypes.ContentType'])),
            ('value_object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('philo', ['Relationship'])

        # Adding unique constraint on 'Relationship', fields ['key', 'entity_content_type', 'entity_object_id']
        db.create_unique('philo_relationship', ['key', 'entity_content_type_id', 'entity_object_id'])

        # Adding model 'Collection'
        db.create_table('philo_collection', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('philo', ['Collection'])

        # Adding model 'CollectionMember'
        db.create_table('philo_collectionmember', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('collection', self.gf('django.db.models.fields.related.ForeignKey')(related_name='members', to=orm['philo.Collection'])),
            ('index', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('member_content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('member_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('philo', ['CollectionMember'])

        # Adding model 'Node'
        db.create_table('philo_node', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['philo.Node'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('view_content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='node_view_set', to=orm['contenttypes.ContentType'])),
            ('view_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('philo', ['Node'])

        # Adding model 'Redirect'
        db.create_table('philo_redirect', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('target', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('status_code', self.gf('django.db.models.fields.IntegerField')(default=302)),
        ))
        db.send_create_signal('philo', ['Redirect'])

        # Adding model 'File'
        db.create_table('philo_file', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mimetype', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        ))
        db.send_create_signal('philo', ['File'])

        # Adding model 'Template'
        db.create_table('philo_template', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['philo.Template'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('documentation', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('mimetype', self.gf('django.db.models.fields.CharField')(default='text/html', max_length=255)),
            ('code', self.gf('philo.models.fields.TemplateField')()),
        ))
        db.send_create_signal('philo', ['Template'])

        # Adding model 'Page'
        db.create_table('philo_page', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('template', self.gf('django.db.models.fields.related.ForeignKey')(related_name='pages', to=orm['philo.Template'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('philo', ['Page'])

        # Adding model 'Contentlet'
        db.create_table('philo_contentlet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contentlets', to=orm['philo.Page'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('content', self.gf('philo.models.fields.TemplateField')()),
        ))
        db.send_create_signal('philo', ['Contentlet'])

        # Adding model 'ContentReference'
        db.create_table('philo_contentreference', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contentreferences', to=orm['philo.Page'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('content_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('philo', ['ContentReference'])


    def backwards(self, orm):
        
        # Deleting model 'Tag'
        db.delete_table('philo_tag')

        # Deleting model 'Attribute'
        db.delete_table('philo_attribute')

        # Removing unique constraint on 'Attribute', fields ['key', 'entity_content_type', 'entity_object_id']
        db.delete_unique('philo_attribute', ['key', 'entity_content_type_id', 'entity_object_id'])

        # Deleting model 'Relationship'
        db.delete_table('philo_relationship')

        # Removing unique constraint on 'Relationship', fields ['key', 'entity_content_type', 'entity_object_id']
        db.delete_unique('philo_relationship', ['key', 'entity_content_type_id', 'entity_object_id'])

        # Deleting model 'Collection'
        db.delete_table('philo_collection')

        # Deleting model 'CollectionMember'
        db.delete_table('philo_collectionmember')

        # Deleting model 'Node'
        db.delete_table('philo_node')

        # Deleting model 'Redirect'
        db.delete_table('philo_redirect')

        # Deleting model 'File'
        db.delete_table('philo_file')

        # Deleting model 'Template'
        db.delete_table('philo_template')

        # Deleting model 'Page'
        db.delete_table('philo_page')

        # Deleting model 'Contentlet'
        db.delete_table('philo_contentlet')

        # Deleting model 'ContentReference'
        db.delete_table('philo_contentreference')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'philo.attribute': {
            'Meta': {'unique_together': "(('key', 'entity_content_type', 'entity_object_id'),)", 'object_name': 'Attribute'},
            'entity_content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'entity_object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'json_value': ('django.db.models.fields.TextField', [], {}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'})
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
