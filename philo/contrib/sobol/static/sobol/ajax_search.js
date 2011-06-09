(function($){
	var sobol = window.sobol = {};
	sobol.search = function(){
		var searches = sobol.searches = $('article.search');
		for (var i=0;i<searches.length;i++) {
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
	sobol.onSuccess = function(ele, data){
		// hook for success!
		ele.removeClass('loading')
		if (data['results'].length) {
			ele[0].innerHTML += "<dl>" + data['results'].join("") + "</dl>";
			if(data['hasMoreResults'] && data['moreResultsURL']) ele[0].innerHTML += "<footer><p><a href='" + data['moreResultsURL'] + "'>See more results</a></p></footer>";
		} else {
			ele.addClass('empty');
			ele[0].innerHTML += "<p>No results found.</p>";
			ele.slideUp();
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