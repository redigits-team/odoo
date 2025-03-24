from . import models

# Import the post init hook properly, so it gets correctly registered
from .models.post_init_hook import create_scheduled_actions