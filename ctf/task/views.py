from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum
from django.contrib.auth import logout, login, authenticate
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .forms import UserRegisterForm
from .models import *
from .metrics import registration_counter, login_counter, attempt_counter


def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            registration_counter.inc()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'task/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                login_counter.inc()
                return redirect('task_list')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    form = AuthenticationForm()
    return render(request, 'task/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def leaderboard_view(request):
    leaderboard = (Attempt.objects.filter(correct=True)
                   .values('user__username')
                   .annotate(score=Sum('task__points'))
                   .order_by('-score'))
    return render(request, 'task/leaderboard.html', {'leaderboard': leaderboard})


def task_list_view(request):
    tasks = Task.objects.all()
    return render(request, 'task/task_list.html', {'tasks': tasks})


@login_required
def task_detail_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        correct = user_answer == task.answer
        attempt_counter.inc()
        Attempt.objects.create(user=request.user, task=task, correct=correct)
        if correct:
            messages.success(request, 'И это правильный ответ! Крутите барабан!')
        else:
            messages.error(request, 'Ты тупее обезьяны!!!')
        return redirect('task_detail', task_id=task.id)
    return render(request, 'task/task_detail.html', {'task': task})


def rules_view(request):
    return render(request, 'task/rules.html')

@login_required
def profile_view(request):
    completed_attempts = Attempt.objects.filter(user=request.user, correct=True).select_related('task')
    total_points = completed_attempts.aggregate(Sum('task__points'))['task__points__sum'] or 0
    completed_tasks = [attempt.task for attempt in completed_attempts]

    return render(request, 'task/profile.html', {
        'completed_tasks': completed_tasks,
        'total_points': total_points,
    })