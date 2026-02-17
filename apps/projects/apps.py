import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ProjectsConfig(AppConfig):
    name = 'apps.projects'
    label = "projects"

    def ready(self):
        logger.info("Projects application ready | Context: Program & Project Management")
