# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'ICalendarFeedView'
        db.delete_table('julian_icalendarfeedview')

        # Adding model 'CalendarView'
        db.create_table('julian_calendarview', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('feed_type', self.gf('django.db.models.fields.CharField')(default='text/calendar', max_length=50)),
            ('feed_suffix', self.gf('django.db.models.fields.CharField')(default='feed', max_length=255)),
            ('feeds_enabled', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('item_title_template', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='julian_calendarview_title_related', null=True, to=orm['philo.Template'])),
            ('item_description_template', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='julian_calendarview_description_related', null=True, to=orm['philo.Template'])),
            ('calendar', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['julian.Calendar'])),
            ('index_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='calendar_index_related', to=orm['philo.Page'])),
            ('timespan_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='calendar_timespan_related', to=orm['philo.Page'])),
            ('event_detail_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='calendar_detail_related', to=orm['philo.Page'])),
            ('tag_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='calendar_tag_related', to=orm['philo.Page'])),
            ('location_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='calendar_location_related', to=orm['philo.Page'])),
            ('owner_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='calendar_owner_related', to=orm['philo.Page'])),
            ('tag_archive_page', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='calendar_tag_archive_related', null=True, to=orm['philo.Page'])),
            ('location_archive_page', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='calendar_location_archive_related', null=True, to=orm['philo.Page'])),
            ('owner_archive_page', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='calendar_owner_archive_related', null=True, to=orm['philo.Page'])),
            ('tag_permalink_base', self.gf('django.db.models.fields.CharField')(default='tags', max_length=30)),
            ('owner_permalink_base', self.gf('django.db.models.fields.CharField')(default='owner', max_length=30)),
            ('location_permalink_base', self.gf('django.db.models.fields.CharField')(default='location', max_length=30)),
        ))
        db.send_create_signal('julian', ['CalendarView'])

        # Adding field 'Location.slug'
        db.add_column('julian_location', 'slug', self.gf('django.db.models.fields.SlugField')(default='slug', unique=True, max_length=255, db_index=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding model 'ICalendarFeedView'
        db.create_table('julian_icalendarfeedview', (
            ('item_title_template', self.gf('django.db.models.fields.related.ForeignKey')(related_name='julian_icalendarfeedview_title_related', null=True, to=orm['philo.Template'], blank=True)),
            ('feed_type', self.gf('django.db.models.fields.CharField')(default='application/atom+xml', max_length=50)),
            ('item_description_template', self.gf('django.db.models.fields.related.ForeignKey')(related_name='julian_icalendarfeedview_description_related', null=True, to=orm['philo.Template'], blank=True)),
            ('feeds_enabled', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('calendar', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['julian.Calendar'])),
            ('feed_suffix', self.gf('django.db.models.fields.CharField')(default='feed', max_length=255)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('julian', ['ICalendarFeedView'])

        # Deleting model 'CalendarView'
        db.delete_table('julian_calendarview')

        # Deleting field 'Location.slug'
        db.delete_column('julian_location', 'slug')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'julian.calendar': {
            'Meta': {'object_name': 'Calendar'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'events': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'calendars'", 'symmetrical': 'False', 'to': "orm['julian.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '100', 'db_index': 'True'}),
            'uuid': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        'julian.calendarview': {
            'Meta': {'object_name': 'CalendarView'},
            'calendar': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['julian.Calendar']"}),
            'event_detail_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'calendar_detail_related'", 'to': "orm['philo.Page']"}),
            'feed_suffix': ('django.db.models.fields.CharField', [], {'default': "'feed'", 'max_length': '255'}),
            'feed_type': ('django.db.models.fields.CharField', [], {'default': "'text/calendar'", 'max_length': '50'}),
            'feeds_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'calendar_index_related'", 'to': "orm['philo.Page']"}),
            'item_description_template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'julian_calendarview_description_related'", 'null': 'True', 'to': "orm['philo.Template']"}),
            'item_title_template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'julian_calendarview_title_related'", 'null': 'True', 'to': "orm['philo.Template']"}),
            'location_archive_page': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'calendar_location_archive_related'", 'null': 'True', 'to': "orm['philo.Page']"}),
            'location_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'calendar_location_related'", 'to': "orm['philo.Page']"}),
            'location_permalink_base': ('django.db.models.fields.CharField', [], {'default': "'location'", 'max_length': '30'}),
            'owner_archive_page': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'calendar_owner_archive_related'", 'null': 'True', 'to': "orm['philo.Page']"}),
            'owner_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'calendar_owner_related'", 'to': "orm['philo.Page']"}),
            'owner_permalink_base': ('django.db.models.fields.CharField', [], {'default': "'owner'", 'max_length': '30'}),
            'tag_archive_page': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'calendar_tag_archive_related'", 'null': 'True', 'to': "orm['philo.Page']"}),
            'tag_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'calendar_tag_related'", 'to': "orm['philo.Page']"}),
            'tag_permalink_base': ('django.db.models.fields.CharField', [], {'default': "'tags'", 'max_length': '30'}),
            'timespan_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'calendar_timespan_related'", 'to': "orm['philo.Page']"})
        },
        'julian.event': {
            'Meta': {'object_name': 'Event'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('philo.models.fields.TemplateField', [], {}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'end_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'location_content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'location_pk': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'parent_event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['julian.Event']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'start_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['philo.Tag']"}),
            'uuid': ('django.db.models.fields.TextField', [], {})
        },
        'julian.location': {
            'Meta': {'object_name': 'Location'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
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
        'philo.node': {
            'Meta': {'object_name': 'Node'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['philo.Node']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'view_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'node_view_set'", 'to': "orm['contenttypes.ContentType']"}),
            'view_object_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'philo.page': {
            'Meta': {'object_name': 'Page'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'pages'", 'to': "orm['philo.Template']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
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

    complete_apps = ['julian']
