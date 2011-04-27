var tagCreation = window.tagCreation;

(function($) {
	location_re = new RegExp("^https?:\/\/" + window.location.host + "/")
	
	$('html').ajaxSend(function(event, xhr, settings) {
		function getCookie(name) {
			var cookieValue = null;
			if (document.cookie && document.cookie != '') {
				var cookies = document.cookie.split(';');
				for (var i = 0; i < cookies.length; i++) {
					var cookie = $.trim(cookies[i]);
					// Does this cookie string begin with the name we want?
					if (cookie.substring(0, name.length + 1) == (name + '=')) {
						cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
						break;
					}
				}
			}
			return cookieValue;
		}
		if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url)) || location_re.test(settings.url)) {
			// Only send the token to relative URLs i.e. locally.
			xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
		}
	});
	tagCreation = {
		'cache': {},
		'addTagFromSlug': function(triggeringLink) {
			var id = triggeringLink.id.replace(/^ajax_add_/, '') + '_input';
			var slug = document.getElementById(id).value;
	
			var name = slug.split(' ');
			for(var i=0;i<name.length;i++) {
				name[i] = name[i].substr(0,1).toUpperCase() + name[i].substr(1);
			}
			name = name.join(' ');
			slug = name.toLowerCase().replace(/ /g, '-').replace(/[^\w-]/g, '');
	
			var href = triggeringLink.href;
			var data = {
				'name': name,
				'slug': slug
			};
			$.post(href, data, function(data){
				newId = html_unescape(data.pk);
				newRepr = html_unescape(data.unicode);
				var toId = id.replace(/_input$/, '_to');
				elem = document.getElementById(toId);
				var o = new Option(newRepr, newId);
				SelectBox.add_to_cache(toId, o);
				SelectBox.redisplay(toId);
			}, "json")
		},
		'init': function(id) {
			tagCreation.cache[id] = {}
			var input = tagCreation.cache[id].input = document.getElementById(id + '_input');
			var select = tagCreation.cache[id].select = document.getElementById(id + '_from');
			var addLinkTemplate = document.getElementById('add_' + input.id.replace(/_input$/, '')).cloneNode(true);
			var addLink = tagCreation.cache[id].addLink = document.createElement('A');
			addLink.id = 'ajax_add_' + id;
			addLink.className = addLinkTemplate.className;
			addLink.href = addLinkTemplate.href;
			addLink.appendChild($(addLinkTemplate).children()[0].cloneNode(false));
			addLink.innerHTML += " <span style='vertical-align:text-top;'>Add this tag</span>"
			addLink.style.marginLeft = "20px";
			addLink.style.display = "block";
			addLink.style.backgroundPosition = "10px 5px";
			addLink.style.width = "120px";
			$(input).after(addLink);
			if (window.grappelli) {
				addLink.parentNode.style.backgroundPosition = "6px 8px";
			} else {
				addLink.style.marginTop = "5px";
			}
			tagCreation.toggleButton(id);
			addEvent(input, 'keyup', function() {
				tagCreation.toggleButton(id);
			})
			addEvent(addLink, 'click', function(e) {
				e.preventDefault();
				tagCreation.addTagFromSlug(addLink);
			})
		},
		'toggleButton': function(id) {
			var addLink = tagCreation.cache[id].addLink;
			var select = $(tagCreation.cache[id].select);
			if (select[0].options.length == 0) {
				if (addLink.style.display == 'none') {
					addLink.style.display = 'block';
					select.height(select.height() - $(addLink).outerHeight(false))
				}
			} else {
				if (addLink.style.display == 'block') {
					select[0].style.height = null;
					addLink.style.display = 'none';
				}
			}
		}
	}
}(django.jQuery))