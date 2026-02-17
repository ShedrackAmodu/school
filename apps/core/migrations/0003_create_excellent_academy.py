# Generated migration to create the single-tenant institution

from django.db import migrations
import uuid


def create_excellent_academy(apps, schema_editor):
    """Create the Excellent Academy institution as the single tenant."""
    Institution = apps.get_model('core', 'Institution')
    
    # Check if it already exists
    if Institution.objects.filter(code='EXCELLENT_ACADEMY').exists():
        return
    
    # Create the institution
    excellent_academy = Institution.objects.create(
        id=uuid.uuid4(),
        name='Excellent Academy',
        code='EXCELLENT_ACADEMY',
        short_name='Excellent Academy',
        description='Single tenant institution - Excellent Academy',
        institution_type='high_school',
        ownership_type='private',
        status='active',
        is_active=True,
        allows_online_enrollment=True,
        requires_parent_approval=True,
        max_students=1000,
        max_staff=100,
        timezone='UTC',
    )


def reverse_excellent_academy(apps, schema_editor):
    """Reverse: delete the Excellent Academy institution."""
    Institution = apps.get_model('core', 'Institution')
    Institution.objects.filter(code='EXCELLENT_ACADEMY').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(create_excellent_academy, reverse_excellent_academy),
    ]
