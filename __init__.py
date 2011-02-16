from philo.loaders.database import Loader


_loader = Loader()


def load_template_source(template_name, template_dirs=None):
    # For backwards compatibility
    import warnings
    warnings.warn(
        "'philo.load_template_source' is deprecated; use 'philo.loaders.database.Loader' instead.",
        PendingDeprecationWarning
    )
    return _loader.load_template_source(template_name, template_dirs)
load_template_source.is_usable = True
