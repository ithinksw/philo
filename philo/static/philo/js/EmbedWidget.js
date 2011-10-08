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
			
			// overload the dismissRelatedLookupPopup function
			oldDismissRelatedLookupPopup = window.dismissRelatedLookupPopup;
			window.dismissRelatedLookupPopup = function (win, chosenId) {
				var name = windowname_to_id(win.name),
					elem = $('#'+name), val;
				// if the original element was an embed widget, run our script
				if (elem.parent().hasClass('embed-widget')) {
					contenttype = $('select',elem.parent()).val();
					widget.appendEmbed(elem, contenttype, chosenId);
					elem.focus();
					win.close();
					return;
				}
				// otherwise, do what you usually do
				oldDismissRelatedLookupPopup.apply(this, arguments);
			}
			
			// overload the dismissAddAnotherPopup function
			oldDismissAddAnotherPopup = window.dismissAddAnotherPopup;
			window.dismissAddAnotherPopup = function (win, newId, newRepr) {
				var name = windowname_to_id(win.name),
					elem = $('#'+win.name), val;
				if (elem.parent().hasClass('embed-widget')) {
					dismissRelatedLookupPopup(win, newId);
				}
				// otherwise, do what you usually do
				oldDismissAddAnotherPopup.apply(this, arguments);
			}
			
			// Add grappelli to the body class if the admin is grappelli. This will allow us to customize styles accordingly.
			if (window.grappelli) {
				$(document.body).addClass('grappelli');
			}
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
			
			// generate the url for the popup
			// TODO: Find a better way to get the admin URL if possible. This will break if the URL patterns for the admin ever change.
			href=['../../../', app_label,  '/', object_name, '/?pop=1'].join('');
			
			// open a new window
			win = window.open(href, id_to_windowname(textarea.attr('id')), 'height=500,width=980,resizable=yes,scrollbars=yes');
		},
		appendEmbed: function (textarea, embed_type, embed_id) {
			var $textarea = $(textarea),
				textarea = $textarea[0], // make sure we're *not* working with a jQuery object
				current_selection = [textarea.selectionStart, textarea.selectionEnd],
				current_text = $textarea.val(),
				embed_string = ['{% embed', embed_type, embed_id, '%}'].join(' '),
				new_text = current_text.substring(0, current_selection[0]) + embed_string + current_text.substring(current_selection[1]),
				new_cursor_pos = current_selection[0]+embed_string.length;
			$textarea.val(new_text);
			textarea.setSelectionRange(new_cursor_pos, new_cursor_pos);
		}
	}
	
	$(widget.init);
}(django.jQuery));