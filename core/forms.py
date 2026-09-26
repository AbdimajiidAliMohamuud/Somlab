from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("full_name", "company_name", "email", "phone", "subject", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "username", "password1", "password2")


class AdminLoginForm(AdminAuthenticationForm):
    username = forms.CharField(label="Username or email", max_length=254)
    remember_me = forms.BooleanField(label="Remember me", required=False)

    def clean(self):
        identifier = self.cleaned_data.get("username", "").strip()
        if identifier:
            user = User.objects.filter(username__iexact=identifier).first()
            if user is None:
                email_matches = User.objects.filter(email__iexact=identifier)
                if email_matches.count() == 1:
                    user = email_matches.first()
            if user is not None:
                self.cleaned_data["username"] = user.get_username()
        return super().clean()
