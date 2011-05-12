var philo_site = {
	three_up: {
		init: function(){
			$('.three-up figure').hover(philo_site.three_up.activate, philo_site.three_up.deactivate);
		},
		activate: function(){
			var $this = $(this);
			$this.addClass('expanded');
			$this.parent().children().not($this).addClass('shrunk');
		},
		deactivate: function(){
			var $this = $(this);
			$this.parent().children().removeClass('expanded').removeClass('shrunk');
		}
	}
}

$(philo_site.three_up.init);