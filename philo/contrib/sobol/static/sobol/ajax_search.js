(function($){
	var sobol = window.sobol = {};
	sobol.favoredResults = []
	sobol.favoredResultSearch = null;
	sobol.search = function(){
		var searches = sobol.searches = $('article.search');
		if(sobol.favoredResults.length) sobol.favoredResultSearch = searches.eq(0);
		for (var i=sobol.favoredResults.length ? 1 : 0;i<searches.length;i++) {
			(function(){
				var s = searches[i];
				$.ajax({
					url: s.getAttribute('data-url'),
					dataType: 'json',
					success: function(data){
						sobol.onSuccess($(s), data);
					},
					error: function(data, textStatus, errorThrown){
						sobol.onError($(s), textStatus, errorThrown);
					}
				});
			}());
		};
	}
	sobol.renderResult = function(result){
		// Returns the result rendered as a string. Override this to provide custom rendering.
		var url = result['url'],
			title = result['title'],
			content = result['content'],
			rendered = '';
		
		if(url){
			rendered += "<dt><a href='" + url + "'>" + title + "</a></dt>";
		} else {
			rendered += "<dt>" + title + "</dt>";
		}
		if(content && content != ''){
			rendered += "<dd>" + content + "</dd>"
		}
		return rendered
	}
	sobol.addFavoredResult = function(result) {
		var dl = sobol.favoredResultSearch.find('dl');
		if(!dl.length){
			dl = $('<dl>');
			dl.appendTo(sobol.favoredResultSearch);
			sobol.favoredResultSearch.removeClass('loading');
		}
		dl[0].innerHTML += sobol.renderResult(result)
	}
	sobol.onSuccess = function(ele, data){
		// hook for success!
		ele.removeClass('loading');
		if (data['results'].length) {
			ele[0].innerHTML += "<dl>";
			$.each(data['results'], function(i, v){
				ele[0].innerHTML += sobol.renderResult(v);
			})
			ele[0].innerHTML += "</dl>";
			if(data['hasMoreResults'] && data['moreResultsURL']) ele[0].innerHTML += "<footer><p><a href='" + data['moreResultsURL'] + "'>See more results</a></p></footer>";
		} else {
			ele.addClass('empty');
			ele[0].innerHTML += "<p>No results found.</p>";
			ele.slideUp();
		}
		if (sobol.favoredResultSearch){
			for (var i=0;i<data['results'].length;i++){
				var r = data['results'][i];
				if ($.inArray(r['actual_url'], sobol.favoredResults) != -1){
					sobol.addFavoredResult(r);
				}
			}
		}
	};
	sobol.onError = function(ele, textStatus, errorThrown){
		// Hook for error...
		ele.removeClass('loading');
		text = errorThrown ? errorThrown : textStatus ? textStatus : "Error occurred.";
		ele[0].innerHTML += "<p>" + text + "</p>";
	};
	$(sobol.search);
}(jQuery));