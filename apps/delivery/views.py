from django.views.generic import ListView
from web_project.mixins import DeliveryTeamRequiredMixin
from .models import DailyDeliveryTeam

class DeliveryTeamDashboardView(DeliveryTeamRequiredMixin, ListView):
    model = DailyDeliveryTeam
    template_name = 'delivery/dashboard.html'
    context_object_name = 'daily_teams'

    def get_queryset(self):
        # Get assignments for the logged-in delivery team member
        return DailyDeliveryTeam.objects.filter(
            models.Q(driver__user=self.request.user) |
            models.Q(supervisor__user=self.request.user) |
            models.Q(delivery_man__user=self.request.user)
        ).select_related(
            'delivery_team',
            'route',
            'driver__user',
            'supervisor__user',
            'delivery_man__user'
        )
