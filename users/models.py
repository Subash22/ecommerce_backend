from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class ProfileGender(models.TextChoices):
    NONE = "-", "---"
    MALE = "M", "Male"
    FEMALE = "F", "Female"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    about_me = models.TextField(null=True, blank=True)
    image = models.ImageField(_("Profile Picture"), upload_to="image/profile_pic", default="default.png")
    gender = models.CharField(_("Gender"), max_length=1, choices=ProfileGender.choices, default=ProfileGender.NONE)
    slug = models.SlugField(_("Slug Fields"), blank=True, null=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)


    def __str__(self):
        return self.user.username
