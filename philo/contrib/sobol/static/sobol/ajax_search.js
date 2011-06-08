(function($){
	var sobol = window.sobol = {}
	sobol.setup = function(){
		var searches = sobol.searches = $('article.search');
		for (i=0;i<searches.length;i++) {
			(function(){
				var s = searches[i];
				$.ajax({
					url: s.getAttribute('data-url'),
					dataType: 'json',
					success: function(data){
						$(s).removeClass('loading')
						if (data['results'].length) {
							s.innerHTML += "<dl>" + data['results'].join("") + "</dl>";
							if(data['hasMoreResults'] && data['moreResultsURL']) s.innerHTML += "<footer><p><a href='" + data['moreResultsURL'] + "'>See more results</a></p></footer>";
						} else {
							$(s).addClass('empty')
							s.innerHTML += "<p>No results found.</p>"
						}
					},
					error: function(data, textStatus, errorThrown){
						$(s).removeClass('loading');
						text = errorThrown ? errorThrown : textStatus ? textStatus : "Error occurred."
						if (errorThrown) {
							s.innerHTML += "<p>" + errorThrown + "</p>"
						};
					}
				});
			}());
		};
	};
	$(sobol.setup);
}(jQuery));