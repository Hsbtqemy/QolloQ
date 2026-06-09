import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logistics", "0006_add_budget_categories"),
    ]

    operations = [
        migrations.CreateModel(
            name="BudgetCharge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("person_name", models.CharField(max_length=255, verbose_name="Nom")),
                ("person_email", models.EmailField(blank=True, max_length=254, verbose_name="Email")),
                ("description", models.CharField(max_length=500, verbose_name="Description")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="Montant (€)")),
                ("status", models.CharField(
                    choices=[("pending", "En attente"), ("sent", "Envoyé"), ("received", "Reçu")],
                    default="pending",
                    max_length=20,
                    verbose_name="Statut",
                )),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("budget_line", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="charges",
                    to="logistics.budgetline",
                    verbose_name="Poste budgétaire",
                )),
                ("form_response", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="charges",
                    to="logistics.logisticsresponse",
                    verbose_name="Réponse liée",
                )),
            ],
            options={
                "verbose_name": "Prise en charge",
                "verbose_name_plural": "Prises en charge",
                "ordering": ["person_name"],
            },
        ),
        migrations.DeleteModel(
            name="Reimbursement",
        ),
    ]
