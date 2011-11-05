from philo.models import Collection, Node, Redirect, File, Template, Page
from philo.contrib.gilbert import site


site.register_model(Collection, icon_name='box')
site.register_model(Node, icon_name='node')
site.register_model(Redirect, icon_name='arrow-switch')
site.register_model(File, icon_name='document-binary')
site.register_model(Page, icon_name='document-globe')
site.register_model(Template, icon_name='document-template')