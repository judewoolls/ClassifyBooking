# company/context_processors.py
from .models import Image

def app_logos(request):
    logos = Image.objects.all()
    logos_dict = {logo.name: logo.image.url for logo in logos}
    return {'app_logos': logos_dict}
