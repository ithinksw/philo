from django import forms

from philo.contrib.sobol.utils import SEARCH_ARG_GET_KEY


class BaseSearchForm(forms.BaseForm):
	base_fields = {
		SEARCH_ARG_GET_KEY: forms.CharField()
	}


class SearchForm(forms.Form, BaseSearchForm):
	pass