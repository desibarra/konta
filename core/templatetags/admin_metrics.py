from django import template
from django.urls import reverse
from django.utils import timezone
from core.models import BackgroundTask

register = template.Library()

@register.inclusion_tag('admin/_background_task_metrics.html', takes_context=True)
def background_task_metrics(context):
    today = timezone.now().date()
    pending = BackgroundTask.objects.filter(status='PENDING').count()
    failed = BackgroundTask.objects.filter(status='FAILED').count()
    completed_today = BackgroundTask.objects.filter(status='COMPLETED', finished_at__date=today).count()
    failed_url = reverse('admin:core_backgroundtask_changelist') + '?status=FAILED'
    return {
        'pending': pending,
        'failed': failed,
        'completed_today': completed_today,
        'failed_url': failed_url,
        'user': context.get('user')
    }
