from django.shortcuts import render, redirect, get_object_or_404
from .models import Exercise, Score
from .forms import ScoreForm
from django.contrib import messages


# Create your views here.
def logbook_view(request):

    user = request.user

    if user.is_authenticated:

        scores = Score.objects.filter(user=user).order_by('-created_on')
        scoreform = ScoreForm()

        if request.method == 'POST':
            scoreform = ScoreForm(request.POST)
            if scoreform.is_valid():
                score = scoreform.save(commit=False)
                score.user = request.user
                score.save()
                messages.success(request, "Score added successfully")
                scoreform = ScoreForm()
                return redirect('open_log')

        return render(request, 'logbook/logbook.html', {
            'exercises': Exercise.objects.all(),
            'scores': scores,
            'scoreform': scoreform
        })

    else:
        return render(request, 'logbook/logbook.html')


# Delete score view
def delete_score(request, score_id):
    score = get_object_or_404(Score, id=score_id, user=request.user)
    if request.method == 'POST':
        score.delete()
        messages.success(request, "Score deleted successfully")
        return redirect('open_log')
    return redirect('open_log')


# Edit score view
def edit_score(request, score_id):
    score = get_object_or_404(Score, id=score_id, user=request.user)
    scoreform = ScoreForm(instance=score)

    if request.method == 'POST':
        scoreform = ScoreForm(request.POST, instance=score)
        if scoreform.is_valid():
            scoreform.save()
            messages.success(request, "Score updated successfully")
            return redirect('open_log')

    return render(request, 'logbook/edit_score.html', {
        'scoreform': scoreform,
        'score': score
    })
