from django.shortcuts import render
from django.core.mail import send_mail
from django.urls import reverse_lazy, reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme

from django.views.generic import (
    View,
    CreateView,
    ListView,
    UpdateView,
    DeleteView
)

from django.views.generic.edit import (
    FormView
)

from .forms import (
    UserRegisterForm, 
    LoginForm,
    UserUpdateForm,
    UpdatePasswordForm,
)
#
from .models import User
# 



def csrf_failure(request, reason=""):
    return HttpResponse(f"""
    <h2>CSRF Failure</h2>

    <b>Reason:</b> {reason}<br><br>

    <b>Session Key:</b><br>
    {request.session.session_key}<br><br>

    <b>Cookie sessionid:</b><br>
    {request.COOKIES.get("sessionid")}<br><br>

    <b>Cookie csrftoken:</b><br>
    {request.COOKIES.get("csrftoken")}<br><br>

    <b>POST csrfmiddlewaretoken:</b><br>
    {request.POST.get("csrfmiddlewaretoken")}<br><br>

    <b>User:</b><br>
    {request.user}
    """, status=403)

class UserRegisterView(FormView):
    template_name = 'users/register.html'
    form_class = UserRegisterForm
    success_url = reverse_lazy('users_app:user-lista')

    def form_valid(self, form):
        #
        User.objects.create_user(
            form.cleaned_data['email'],
            form.cleaned_data['password1'],
            full_name=form.cleaned_data['full_name'],
            ocupation=form.cleaned_data['ocupation'],
            genero=form.cleaned_data['genero'],
            date_birth=form.cleaned_data['date_birth'],
        )
        # enviar el codigo al email del user
        return super(UserRegisterView, self).form_valid(form)



class LoginUser(FormView):
    template_name = 'users/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('inicio_app:home')

    def form_valid(self, form):
        user = authenticate(
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password']
        )
        if user is None:
            print("⚠️ Usuario no autenticado. Email o password incorrecto.")
            form.add_error(None, "Credenciales inválidas")
            return self.form_invalid(form)
        login(self.request, user)

        # Obtener la URL de redirección
        redirect_to = self.request.POST.get('next') or self.request.GET.get('next')
        if redirect_to and url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure()
        ):
            return HttpResponseRedirect(redirect_to)

        return super(LoginUser, self).form_valid(form)


class LogoutView(View):

    def get(self, request, *args, **kargs):
        logout(request)
        return HttpResponseRedirect(
            reverse(
                'inicio_app:home'
            )
        )



class UserUpdateView(UpdateView):
    template_name = "users/update.html"
    model = User
    form_class = UserUpdateForm
    success_url = reverse_lazy('users_app:user-lista')


class UserDeleteView(DeleteView):
    model = User
    success_url = reverse_lazy('users_app:user-lista')


class UpdatePasswordView(LoginRequiredMixin, FormView):
    # template_name = 'users/update.html'
    form_class = UpdatePasswordForm
    success_url = reverse_lazy('users_app:user-login')
    login_url = reverse_lazy('users_app:user-login')

    def form_valid(self, form):
        usuario = self.request.user
        user = authenticate(
            email=usuario.email,
            password=form.cleaned_data['password1']
        )

        if user:
            new_password = form.cleaned_data['password2']
            usuario.set_password(new_password)
            usuario.save()

        logout(self.request)
        return super(UpdatePasswordView, self).form_valid(form)


class UserListView(ListView):
    template_name = "users/lista.html"
    context_object_name = 'usuarios'

    def get_queryset(self):
        return User.objects.usuarios_sistema()