from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from catalogues.models import CatalogueVisit
import os

class Command(BaseCommand):
    help = 'Deletes visit photos older than 31 days but keeps the visit record.'

    def handle(self, *args, **options):
        # Calculate the threshold date (31 days ago)
        threshold_date = timezone.localdate() - timedelta(days=31)
        
        # Get visits with photos older than the threshold
        visits = CatalogueVisit.objects.filter(visit_date__lt=threshold_date).exclude(photo='')

        count = 0
        for visit in visits:
            if visit.photo:
                # Delete the file from storage
                if os.path.isfile(visit.photo.path):
                    os.remove(visit.photo.path)
                
                # Clear the photo field in the database
                visit.photo = None
                visit.save(update_fields=['photo'])
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} old photos.'))
