
# from web_project.bootstrap import TemplateBootstrap
from web_project.template_helpers.theme import TemplateHelper
from django.conf import settings


class TemplateLayout:
    @staticmethod
    def init(self, context):
        # Default layout options
        context.update({
            'layout_path': "layout/layout_vertical.html",
            'is_menu': True,  # Enable menu by default
            'is_navbar': True,  # Enable navbar by default
            'navbar_type': 'fixed',  # or your default navbar type
        })
        return context
