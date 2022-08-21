from django.shortcuts import render, redirect
from . forms import LoginForm, UserRegistrationForm, PasswordResetForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import BadHeaderError, send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from ratelimit.decorators import ratelimit
from rest_framework import permissions
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from .models import *


UserModel = get_user_model()


# Create your views here.
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
@ratelimit(key='ip', rate='5/s', block=True)
def register(request):
    try:
        raw_password = request.data['password']
        first_name = request.data['first_name']
        last_name = request.data['last_name']
        email = request.data['email']

        email_exist = User.objects.filter(email=email).first()
        if email_exist:
            return Response({'message': 'Email already exist. Login to continue.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False
        )
        user.set_password(raw_password)
        user.save()

        current_site = get_current_site(request)
        subject = "Verify your email"
        email_template_name = "users/verify_email.txt"
        c = {
            "email": user.email,
            'domain': current_site,
            'site_name': 'Interface',
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "user": user,
            'token': default_token_generator.make_token(user),
            'protocol': 'http',
        }
        email = render_to_string(email_template_name, c)
        try:
            email = send_mail(subject, email, settings.EMAIL_HOST_USER, [
                                user.email], fail_silently=False)
        except BadHeaderError:
            return Response({'message': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Account created successfully. Please check your email to activate your account.',
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response({'message': 'Something went wrong.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = UserModel._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        if user.is_active == True:
            messages.error(request, 'Email already confirmed. Please login to your account.')
            return redirect("https://ecommerceurl.com/")
        user.is_active = True
        user.save()
        messages.success(request, 'Email confirmed. Now you can login your account.')
        return redirect("https://ecommerceurl.com/")
    else:
        messages.error(request, 'Invalid or expired link.')
        return HttpResponse("Invalid or expired link.", content_type="text/plain")


def forgot(request):
    if request.method == 'POST':
        domain = request.headers['Host']
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(Q(email=data))
            # You can use more than one way like this for resetting the password.
            # ...filter(Q(email=data) | Q(username=data))
            # but with this you may need to change the password_reset form as well.
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "users/password_reset_email.txt"
                    c = {
                        "email": user.email,
                        'domain': domain,
                        'site_name': 'Interface',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        send_mail(subject, email, settings.EMAIL_HOST_USER, [
                                  user.email], fail_silently=False)
                    except BadHeaderError:
                        return HttpResponse('Invalid header found.')
                    messages.success(request, "Password reset successfully.")
                    return redirect("/password_reset/done/")
            messages.error(request, "User with that email doesn't exist.")
            return redirect("/forgot/")
        messages.error(
            request, "Error while reseting the password. Try again.")
        return redirect("/forgot/")
    else:
        form = UserRegistrationForm()
    return render(request, 'users/forgot.html', {'r_form': form})


def authenticate_user(login_func):
    def wrapper(request, user=None):
        # if request.user.is_authenticated:
        #     return HttpResponse('You have been Authenticated')
        if request.method == 'POST':
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                cd = login_form.cleaned_data
                user_active = UserModel.objects.filter(
                    username=cd['username'], is_active=False).first()
                if user_active is not None:
                    messages.error(
                        request, 'Please confirm your email to login.')
                    return render(request, 'users/login.html', {'login_form': login_form})
                user = authenticate(
                    username=cd['username'], password=cd['password'])
                if user is not None:
                    # if user.is_staff:
                    #     return redirect("/stats/")
                    # if user.is_active:
                    return login_func(request, user)
                    # else:
                    #     messages.error(request, 'Please confirm your email to login.')
                else:
                    messages.error(request, 'Invalid username of passoword.')
            else:
                messages.error(request, 'Invalid username of passoword')
        else:
            login_form = LoginForm()
        return render(request, 'users/login.html', {'login_form': login_form})
    return wrapper


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
@ratelimit(key='ip', rate='5/s', block=True)
def get_tokens_for_user(request):
    email = request.data['email']
    password = request.data['password']

    # find the user base in params
    if email is None:
        return Response({'message': 'Email address not found'}, status=status.HTTP_403_FORBIDDEN)
    try:
        user = User.objects.get(email=email)
        if not user.check_password(password):
            return Response({'message': 'Email address or password doesnot match.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_active:
            return Response({'message': 'Please activate your account to login.'}, status=status.HTTP_400_BAD_REQUEST)
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Logged in successfully',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'message': 'User not found'}, status=status.HTTP_403_FORBIDDEN)


class LogoutView(APIView):

    @method_decorator(ratelimit(method='POST', key='ip', rate='10/s', block=True))
    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]

            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except:
                pass

            return Response({"message": "User has been logged out successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpdateProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(ratelimit(method='GET', key='ip', rate='10/s', block=True))
    def post(self, request):
        try:
            first_name = request.data["first_name"]
            last_name = request.data["last_name"]
            gender = request.data["gender"]
            about_me = request.data["about_me"]
            raw_password = request.data["password"]

            user = User.objects.get(id=self.request.user.id)
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(raw_password)
            user.save()
            user_profile, created = Profile.objects.get_or_create(user=user)
            user_profile.gender = gender
            user_profile.about_me = about_me
            user_profile.save()

            return Response({"message": "User profile has been changed successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
