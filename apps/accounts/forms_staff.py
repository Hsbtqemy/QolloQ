from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class StaffUserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Mot de passe temporaire",
        widget=forms.PasswordInput,
        help_text="L'utilisateur devra le changer à sa première connexion.",
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "is_staff"]

    def clean_password(self):
        password = self.cleaned_data.get("password")
        validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.must_change_password = True
        if commit:
            user.save()
        return user


class StaffUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "is_staff", "is_active"]
