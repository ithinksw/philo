# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from philo.migrations import person_model, frozen_person

class Migration(SchemaMigration):

	needed_by = (
		('philo', '0021_auto__del_tag'),
	)

	def forwards(self, orm):
		
		# Removing M2M table for field tags on 'BlogEntry'
		db.delete_table('penfield_blogentry_tags')

		# Removing M2M table for field tags on 'NewsletterArticle'
		db.delete_table('penfield_newsletterarticle_tags')


	def backwards(self, orm):
		
		# Adding M2M table for field tags on 'BlogEntry'
		db.create_table('penfield_blogentry_tags', (
			('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
			('blogentry', models.ForeignKey(orm['penfield.blogentry'], null=False)),
			('tag', models.ForeignKey(orm['philo.tag'], null=False))
		))
		db.create_unique('penfield_blogentry_tags', ['blogentry_id', 'tag_id'])

		# Adding M2M table for field tags on 'NewsletterArticle'
		db.create_table('penfield_newsletterarticle_tags', (
			('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
			('newsletterarticle', models.ForeignKey(orm['penfield.newsletterarticle'], null=False)),
			('tag', models.ForeignKey(orm['philo.tag'], null=False))
		))
		db.create_unique('penfield_newsletterarticle_tags', ['newsletterarticle_id', 'tag_id'])


	models = {
		'auth.group': {
			'Meta': {'object_name': 'Group'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
			'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
		},
		'auth.permission': {
			'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
			'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
			'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
			'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
			'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
			'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
			'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
			'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
			'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
		},
		'contenttypes.contenttype': {
			'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
			'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
		},
		person_model: frozen_person,
		'penfield.blog': {
			'Meta': {'object_name': 'Blog'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
			'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
		},
		'penfield.blogentry': {
			'Meta': {'object_name': 'BlogEntry'},
			'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'blogentries'", 'to': "orm['%s']" % person_model}),
			'blog': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': "orm['penfield.Blog']"}),
			'content': ('django.db.models.fields.TextField', [], {}),
			'date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
			'excerpt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
			'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
		},
		'penfield.blogview': {
			'Meta': {'object_name': 'BlogView'},
			'blog': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'blogviews'", 'to': "orm['penfield.Blog']"}),
			'entries_per_page': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
			'entry_archive_page': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'blog_entry_archive_related'", 'null': 'True', 'to': "orm['philo.Page']"}),
			'entry_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'blog_entry_related'", 'to': "orm['philo.Page']"}),
			'entry_permalink_base': ('django.db.models.fields.CharField', [], {'default': "'entries'", 'max_length': '255'}),
			'entry_permalink_style': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
			'feed_length': ('django.db.models.fields.PositiveIntegerField', [], {'default': '15', 'null': 'True', 'blank': 'True'}),
			'feed_suffix': ('django.db.models.fields.CharField', [], {'default': "'feed'", 'max_length': '255'}),
			'feed_type': ('django.db.models.fields.CharField', [], {'default': "'atom'", 'max_length': '50'}),
			'feeds_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'index_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'blog_index_related'", 'to': "orm['philo.Page']"}),
			'item_description_template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'penfield_blogview_description_related'", 'null': 'True', 'to': "orm['philo.Template']"}),
			'item_title_template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'penfield_blogview_title_related'", 'null': 'True', 'to': "orm['philo.Template']"}),
			'tag_archive_page': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'blog_tag_archive_related'", 'null': 'True', 'to': "orm['philo.Page']"}),
			'tag_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'blog_tag_related'", 'to': "orm['philo.Page']"}),
			'tag_permalink_base': ('django.db.models.fields.CharField', [], {'default': "'tags'", 'max_length': '255'})
		},
		'penfield.newsletter': {
			'Meta': {'object_name': 'Newsletter'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
			'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
		},
		'penfield.newsletterarticle': {
			'Meta': {'ordering': "['-date']", 'unique_together': "(('newsletter', 'slug'),)", 'object_name': 'NewsletterArticle'},
			'authors': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'newsletterarticles'", 'symmetrical': 'False', 'to': "orm['%s']" % person_model}),
			'date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
			'full_text': ('philo.models.fields.TemplateField', [], {'db_index': 'True'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'lede': ('philo.models.fields.TemplateField', [], {'null': 'True', 'blank': 'True'}),
			'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'articles'", 'to': "orm['penfield.Newsletter']"}),
			'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
			'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
		},
		'penfield.newsletterissue': {
			'Meta': {'ordering': "['-numbering']", 'unique_together': "(('newsletter', 'numbering'),)", 'object_name': 'NewsletterIssue'},
			'articles': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'issues'", 'symmetrical': 'False', 'to': "orm['penfield.NewsletterArticle']"}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'issues'", 'to': "orm['penfield.Newsletter']"}),
			'numbering': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
			'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
			'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
		},
		'penfield.newsletterview': {
			'Meta': {'object_name': 'NewsletterView'},
			'article_archive_page': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'newsletter_article_archive_related'", 'null': 'True', 'to': "orm['philo.Page']"}),
			'article_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter_article_related'", 'to': "orm['philo.Page']"}),
			'article_permalink_base': ('django.db.models.fields.CharField', [], {'default': "'articles'", 'max_length': '255'}),
			'article_permalink_style': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
			'feed_length': ('django.db.models.fields.PositiveIntegerField', [], {'default': '15', 'null': 'True', 'blank': 'True'}),
			'feed_suffix': ('django.db.models.fields.CharField', [], {'default': "'feed'", 'max_length': '255'}),
			'feed_type': ('django.db.models.fields.CharField', [], {'default': "'atom'", 'max_length': '50'}),
			'feeds_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'index_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter_index_related'", 'to': "orm['philo.Page']"}),
			'issue_archive_page': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'newsletter_issue_archive_related'", 'null': 'True', 'to': "orm['philo.Page']"}),
			'issue_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter_issue_related'", 'to': "orm['philo.Page']"}),
			'issue_permalink_base': ('django.db.models.fields.CharField', [], {'default': "'issues'", 'max_length': '255'}),
			'item_description_template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'penfield_newsletterview_description_related'", 'null': 'True', 'to': "orm['philo.Template']"}),
			'item_title_template': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'penfield_newsletterview_title_related'", 'null': 'True', 'to': "orm['philo.Template']"}),
			'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletterviews'", 'to': "orm['penfield.Newsletter']"})
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
		},
		'taggit.tag': {
			'Meta': {'object_name': 'Tag'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
			'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
		},
		'taggit.taggeditem': {
			'Meta': {'object_name': 'TaggedItem'},
			'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
			'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
		}
	}

	complete_apps = ['penfield', 'taggit']
