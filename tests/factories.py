from datetime import date, time, timedelta

import factory
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = "accounts.User"
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = "Marie"
    last_name = "Dupont"

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or "testpass123")
        if create:
            obj.save(update_fields=["password"])


class EventFactory(DjangoModelFactory):
    class Meta:
        model = "events.Event"

    name = factory.Sequence(lambda n: f"Colloque test {n}")
    slug = factory.Sequence(lambda n: f"colloque-test-{n}")
    start_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    end_date = factory.LazyAttribute(lambda o: o.start_date + timedelta(days=1))
    created_by = factory.SubFactory(UserFactory)
    submissions_open = False


class MembershipFactory(DjangoModelFactory):
    class Meta:
        model = "events.Membership"

    user = factory.SubFactory(UserFactory)
    event = factory.SubFactory(EventFactory)
    role = "organizer"


class ProposalFactory(DjangoModelFactory):
    class Meta:
        model = "submissions.Proposal"

    event = factory.SubFactory(EventFactory)
    title = factory.Sequence(lambda n: f"Communication test {n}")
    abstract = "Un résumé de test."
    submitter_email = factory.Sequence(lambda n: f"auteur{n}@example.com")
    status = "submitted"


class AuthorFactory(DjangoModelFactory):
    class Meta:
        model = "submissions.Author"

    proposal = factory.SubFactory(ProposalFactory)
    first_name = "Marie"
    last_name = "Dupont"
    institution = "CNRS"
    order = factory.Sequence(lambda n: n)


class SessionFactory(DjangoModelFactory):
    class Meta:
        model = "programme.Session"

    event = factory.SubFactory(EventFactory)
    date = factory.LazyAttribute(lambda o: o.event.start_date)
    start_time = time(9, 0)
    end_time = time(10, 30)
    title = factory.Sequence(lambda n: f"Session {n}")
    order = factory.Sequence(lambda n: n + 1)


class CommunicationFactory(DjangoModelFactory):
    class Meta:
        model = "programme.Communication"

    session = factory.SubFactory(SessionFactory)
    title = factory.Sequence(lambda n: f"Communication {n}")
    speaker_name = "Jean Martin"
    duration = 20
    order = factory.Sequence(lambda n: n + 1)


class LogisticsFormFactory(DjangoModelFactory):
    class Meta:
        model = "logistics.LogisticsForm"

    event = factory.SubFactory(EventFactory)
    name = "Formulaire logistique test"
    is_open = False


class LogisticsResponseFactory(DjangoModelFactory):
    class Meta:
        model = "logistics.LogisticsResponse"

    form = factory.SubFactory(LogisticsFormFactory)
    respondent_name = "Jean Martin"
    respondent_email = factory.Sequence(lambda n: f"intervenant{n}@example.com")
    is_complete = False


class EmailCampaignFactory(DjangoModelFactory):
    class Meta:
        model = "emails.EmailCampaign"

    event = factory.SubFactory(EventFactory)
    subject = factory.Sequence(lambda n: f"Campagne test {n}")
    body = "Corps du message de test."
    audience = "all_members"
