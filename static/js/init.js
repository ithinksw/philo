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
	},
	anchor_light: {
		init: function () {
			var self = philo_site.anchor_light;
			links = $('a[href^="#"]');
			links.click(self.hiliteHandler);
		},
		hiliteHandler: function () {
			var self = philo_site.anchor_light,
				$this = $(this),
				id = $this.attr('href'),
				el = $(id);
			el.addClass("lite");
			setTimeout(self.unhiliteHandler, 1000);
		},
		unhiliteHandler: function () {
			$('.lite').removeClass('lite');
		}
	}
}

$(philo_site.three_up.init);
$(philo_site.anchor_light.init);