;(function ($) {
	var widget = window.embedWidget;
	
	widget = {
		options: {},
		optgroups: {},
		init: function () {
			var EmbedFields = widget.EmbedFields = $('.embedding'),
				EmbedWidgets = widget.EmbedWidgets,
				EmbedBars = widget.EmbedBars,
				EmbedButtons = widget.EmbedButtons,
				EmbedSelects = widget.EmbedSelects;

			EmbedFields.wrap($('<div class="embed-widget" />'));
			EmbedWidgets = $('.embed-widget');
			EmbedWidgets.prepend($('<div class="embed-toolbar" />'));
			EmbedBars = $('.embed-toolbar');
			EmbedBars.append('<select class="embed-select"></select><button class="embed-button">Embed</button>');
			EmbedButtons = $('.embed-button');
			EmbedSelects = $('.embed-select');
			
			widget.parseContentTypes();
			EmbedSelects.each(widget.populateSelect);
			
			EmbedButtons.click(widget.buttonHandler);
		},
		parseContentTypes: function () {
			var string = widget.EmbedFields.eq(0).attr('data-content-types'),
				data = $.parseJSON(string),
				i=0,
				current_app_label = '',
				optgroups = {};
				
				// this loop relies on data being clustered by app
				for(i=0; i < data.length; i++){
					item = data[i]
					// run this next loop every time we encounter a new app label
					if (item.app_label !== current_app_label) {
						current_app_label = item.app_label;
						optgroups[current_app_label] = {}
					}
					optgroups[current_app_label][item.verbose_name] = [item.app_label,item.object_name].join('.');
					
					widget.optgroups = optgroups;
				}
		},
		populateSelect: function () {
			var $this = $(this),
				optgroups = widget.optgroups,
				optgroup_els = {},
				optgroup_el, group;
				
			// append a title
			$this.append('<option value="">Media Types</option>');
			
			// for each group
			for (name in optgroups){
				if(optgroups.hasOwnProperty(name)){
					// assign the group to variable group, temporarily
					group = optgroups[name];
					// create an element for this group and assign it to optgroup_el, temporarily
					optgroup_el = optgroup_els[name] = $('<optgroup label="'+name+'" />');
					// append this element to the select menu
					$this.append(optgroup_el);
					// for each item in the group
					for (name in group) {
						// append an option to the optgroup
						optgroup_el.append('<option value='+group[name]+'>'+name+'</option>');
					}
				}
			}
		},
		buttonHandler: function (e) {
			var $this = $(this),
				select = $this.prev('select'),
				embed_widget = $this.closest('.embed-widget'),
				textarea = embed_widget.children('.embedding').eq(0),
				val, app_label, object_name,
				href,
				win;
			
			// prevent the button from submitting the form
			e.preventDefault();
			// handle the case that they haven't chosen a type to embed
			if (select.val()==='') {
				alert('Please select a media type to embed.');
				textarea.focus();
				return;
			}
			
			// split the val into app and object
			val = select.val();
			app_label = val.split('.')[0];
			object_name = val.split('.')[1];
			
			// generate the url
			// TODO: abstract this so it can calculate the admin url dynamically
			href=["/admin", app_label, object_name, '?pop=1'].join('/');
			
			// this is a bit hackish. let's walk through it.
			// TODO: best to write our own template for this in the future
			
			// open a new window
			win = window.open(href, id_to_windowname(textarea.attr('id')), 'height=500,width=980,resizable=yes,scrollbars=yes');
			
			// when the window finishes loading
			win.addEventListener('load', function(){
				// collect all the links to objects in that window
				var links = win.django.jQuery('#changelist th:first-child a');
					// for each link
					links.each(function(){
						// capture the pk
						var pk = $(this).attr('href').split('/')[0];
						// bind our own function to onclick instead of the function that's currently there
						this.onclick = function () { widget.appendEmbed(textarea, val, pk); win.close(); return false; };
					});
			}, false)
			
			// return focus to the textarea
			textarea.focus();
		},
		appendEmbed: function (textarea, embed_type, embed_id) {
			var $textarea = $(textarea),
				textarea = $textarea[0], // make sure we're *not* working with a jQuery object
				current_selection = [textarea.selectionStart, textarea.selectionEnd],
				current_text = $textarea.val(),
				embed_string = ['{% embed', embed_type, embed_id, '%}'].join(' '),
				new_text = current_text.substring(0, current_selection[0]) + embed_string + current_text.substring(current_selection[1]);
				
			$textarea.val(new_text);
		}
	}
	
	$(widget.init);
}(django.jQuery));