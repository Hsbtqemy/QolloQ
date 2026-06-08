from .models import Event, Membership


def user_events(request):
    if not request.user.is_authenticated:
        return {"user_events": []}
    events = (
        Event.objects.filter(memberships__user=request.user)
        .order_by("-start_date")
        .distinct()
    )
    return {"user_events": events}
