import json

from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from apps.core.mixins import OrganizerRequiredMixin


class EventOwnedCreateView(OrganizerRequiredMixin, View):
    form_class = None
    template_name = None

    def get_form_kwargs(self):
        kwargs = {"event": self.event}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
            kwargs["files"] = self.request.FILES
        return kwargs

    def get_form(self):
        return self.form_class(**self.get_form_kwargs())

    def get_extra_context(self):
        return {}

    def get_context_data(self, form):
        return {"event": self.event, "form": form, **self.get_extra_context()}

    def prepare_instance(self, instance, form):
        pass

    def post_create(self, instance, form):
        pass

    def get_success_url(self, instance):
        raise NotImplementedError

    def get(self, request, **kwargs):
        return render(request, self.template_name, self.get_context_data(self.get_form()))

    def post(self, request, **kwargs):
        form = self.get_form()
        if form.is_valid():
            instance = form.save(commit=False)
            instance.event = self.event
            self.prepare_instance(instance, form)
            try:
                instance.save()
                form.save_m2m()
            except IntegrityError:
                form.add_error(None, "Un enregistrement identique existe déjà.")
                return render(request, self.template_name, self.get_context_data(form))
            self.post_create(instance, form)
            return redirect(self.get_success_url(instance))
        return render(request, self.template_name, self.get_context_data(form))


class JsonPatchView(OrganizerRequiredMixin, View):
    """Vue de modification inline via fetch() JSON."""

    def patch(self, request, **kwargs):
        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({"error": "Données invalides."}, status=400)
        return self.handle_patch(request, data, **kwargs)

    def handle_patch(self, request, data, **kwargs):
        raise NotImplementedError
