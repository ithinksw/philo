# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from philo.migrations import person_model, frozen_person

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Blog'
        db.create_table('penfield_blog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
        ))
        db.send_create_signal('penfield', ['Blog'])

        # Adding model 'BlogEntry'
        db.create_table('penfield_blogentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('blog', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='entries', null=True, to=orm['penfield.Blog'])),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(related_name='blogentries', to=orm[person_model])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('excerpt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('penfield', ['BlogEntry'])

        # Adding M2M table for field tags on 'BlogEntry'
        db.create_table('penfield_blogentry_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('blogentry', models.ForeignKey(orm['penfield.blogentry'], null=False)),
            ('tag', models.ForeignKey(orm['philo.tag'], null=False))
        ))
        db.create_unique('penfield_blogentry_tags', ['blogentry_id', 'tag_id'])

        # Adding model 'BlogView'
        db.create_table('penfield_blogview', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('blog', self.gf('django.db.models.fields.related.ForeignKey')(related_name='blogviews', to=orm['penfield.Blog'])),
            ('index_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='blog_index_related', to=orm['philo.Page'])),
            ('entry_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='blog_entry_related', to=orm['philo.Page'])),
            ('entry_archive_page', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='blog_entry_archive_related', null=True, to=orm['philo.Page'])),
            ('tag_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='blog_tag_related', to=orm['philo.Page'])),
            ('tag_archive_page', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='blog_tag_archive_related', null=True, to=orm['philo.Page'])),
            ('entries_per_page', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('entry_permalink_style', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('entry_permalink_base', self.gf('django.db.models.fields.CharField')(default='entries', max_length=255)),
            ('tag_permalink_base', self.gf('django.db.models.fields.CharField')(default='tags', max_length=255)),
            ('feed_suffix', self.gf('django.db.models.fields.CharField')(default='feed', max_length=255)),
            ('feeds_enabled', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
        ))
        db.send_create_signal('penfield', ['BlogView'])

        # Adding model 'Newsletter'
        db.create_table('penfield_newsletter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
        ))
        db.send_create_signal('penfield', ['Newsletter'])

        # Adding model 'NewsletterArticle'
        db.create_table('penfield_newsletterarticle', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('newsletter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='articles', to=orm['penfield.Newsletter'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('lede', self.gf('philo.models.fields.TemplateField')(null=True, blank=True)),
            ('full_text', self.gf('philo.models.fields.TemplateField')()),
        ))
        db.send_create_signal('penfield', ['NewsletterArticle'])

        # Adding unique constraint on 'NewsletterArticle', fields ['newsletter', 'slug']
        db.create_unique('penfield_newsletterarticle', ['newsletter_id', 'slug'])

        # Adding M2M table for field authors on 'NewsletterArticle'
        db.create_table('penfield_newsletterarticle_authors', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('newsletterarticle', models.ForeignKey(orm['penfield.newsletterarticle'], null=False)),
            ('person', models.ForeignKey(orm[person_model], null=False))
        ))
        db.create_unique('penfield_newsletterarticle_authors', ['newsletterarticle_id', 'person_id'])

        # Adding M2M table for field tags on 'NewsletterArticle'
        db.create_table('penfield_newsletterarticle_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('newsletterarticle', models.ForeignKey(orm['penfield.newsletterarticle'], null=False)),
            ('tag', models.ForeignKey(orm['philo.tag'], null=False))
        ))
        db.create_unique('penfield_newsletterarticle_tags', ['newsletterarticle_id', 'tag_id'])

        # Adding model 'NewsletterIssue'
        db.create_table('penfield_newsletterissue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, db_index=True)),
            ('newsletter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='issues', to=orm['penfield.Newsletter'])),
            ('numbering', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('penfield', ['NewsletterIssue'])

        # Adding unique constraint on 'NewsletterIssue', fields ['newsletter', 'numbering']
        db.create_unique('penfield_newsletterissue', ['newsletter_id', 'numbering'])

        # Adding M2M table for field articles on 'NewsletterIssue'
        db.create_table('penfield_newsletterissue_articles', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('newsletterissue', models.ForeignKey(orm['penfield.newsletterissue'], null=False)),
            ('newsletterarticle', models.ForeignKey(orm['penfield.newsletterarticle'], null=False))
        ))
        db.create_unique('penfield_newsletterissue_articles', ['newsletterissue_id', 'newsletterarticle_id'])

        # Adding model 'NewsletterView'
        db.create_table('penfield_newsletterview', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('newsletter', self.gf('django.db.models.fields.related.ForeignKey')(related_name='newsletterviews', to=orm['penfield.Newsletter'])),
            ('index_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='newsletter_index_related', to=orm['philo.Page'])),
            ('article_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='newsletter_article_related', to=orm['philo.Page'])),
            ('article_archive_page', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='newsletter_article_archive_related', null=True, to=orm['philo.Page'])),
            ('issue_page', self.gf('django.db.models.fields.related.ForeignKey')(related_name='newsletter_issue_related', to=orm['philo.Page'])),
            ('issue_archive_page', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='newsletter_issue_archive_related', null=True, to=orm['philo.Page'])),
            ('article_permalink_style', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('article_permalink_base', self.gf('django.db.models.fields.CharField')(default='articles', max_length=255)),
            ('issue_permalink_base', self.gf('django.db.models.fields.CharField')(default='issues', max_length=255)),
            ('feed_suffix', self.gf('django.db.models.fields.CharField')(default='feed', max_length=255)),
            ('feeds_enabled', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
        ))
        db.send_create_signal('penfield', ['NewsletterView'])


    def backwards(self, orm):
        
        # Deleting model 'Blog'
        db.delete_table('penfield_blog')

        # Deleting model 'BlogEntry'
        db.delete_table('penfield_blogentry')

        # Removing M2M table for field tags on 'BlogEntry'
        db.delete_table('penfield_blogentry_tags')

        # Deleting model 'BlogView'
        db.delete_table('penfield_blogview')

        # Deleting model 'Newsletter'
        db.delete_table('penfield_newsletter')

        # Deleting model 'NewsletterArticle'
        db.delete_table('penfield_newsletterarticle')

        # Removing unique constraint on 'NewsletterArticle', fields ['newsletter', 'slug']
        db.delete_unique('penfield_newsletterarticle', ['newsletter_id', 'slug'])

        # Removing M2M table for field authors on 'NewsletterArticle'
        db.delete_table('penfield_newsletterarticle_authors')

        # Removing M2M table for field tags on 'NewsletterArticle'
        db.delete_table('penfield_newsletterarticle_tags')

        # Deleting model 'NewsletterIssue'
        db.delete_table('penfield_newsletterissue')

        # Removing unique constraint on 'NewsletterIssue', fields ['newsletter', 'numbering']
        db.delete_unique('penfield_newsletterissue', ['newsletter_id', 'numbering'])

        # Removing M2M table for field articles on 'NewsletterIssue'
        db.delete_table('penfield_newsletterissue_articles')

        # Deleting model 'NewsletterView'
        db.delete_table('penfield_newsletterview')


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
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'blogentries'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['philo.Tag']"}),
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
            'feed_suffix': ('django.db.models.fields.CharField', [], {'default': "'feed'", 'max_length': '255'}),
            'feeds_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'blog_index_related'", 'to': "orm['philo.Page']"}),
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
            'Meta': {'unique_together': "(('newsletter', 'slug'),)", 'object_name': 'NewsletterArticle'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'newsletterarticles'", 'symmetrical': 'False', 'to': "orm['%s']" % person_model}),
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'full_text': ('philo.models.fields.TemplateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lede': ('philo.models.fields.TemplateField', [], {'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'articles'", 'to': "orm['penfield.Newsletter']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'db_index': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'newsletterarticles'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['philo.Tag']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'penfield.newsletterissue': {
            'Meta': {'unique_together': "(('newsletter', 'numbering'),)", 'object_name': 'NewsletterIssue'},
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
            'feed_suffix': ('django.db.models.fields.CharField', [], {'default': "'feed'", 'max_length': '255'}),
            'feeds_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter_index_related'", 'to': "orm['philo.Page']"}),
            'issue_archive_page': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'newsletter_issue_archive_related'", 'null': 'True', 'to': "orm['philo.Page']"}),
            'issue_page': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter_issue_related'", 'to': "orm['philo.Page']"}),
            'issue_permalink_base': ('django.db.models.fields.CharField', [], {'default': "'issues'", 'max_length': '255'}),
            'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletterviews'", 'to': "orm['penfield.Newsletter']"})
        },
        'philo.attribute': {
            'Meta': {'unique_together': "(('key', 'entity_content_type', 'entity_object_id'),)", 'object_name': 'Attribute'},
            'entity_content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'entity_object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'json_value': ('django.db.models.fields.TextField', [], {}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'})
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

    complete_apps = ['penfield']
