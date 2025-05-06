from django import forms
from .models import Exercise, Score


class ScoreForm(forms.ModelForm):
    class Meta:
        model = Score
        fields = ['exercise', 'reps', 'weight']
        widgets = {
            'exercise': forms.Select(attrs={'class': 'form-control'}),
            'reps': forms.NumberInput(attrs={'class': 'form-control',
                                             'min': 1}),
            'weight': forms.NumberInput(attrs={'class': 'form-control',
                                               'min': 0})
        }

    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight is not None and weight < 0:
            raise forms.ValidationError("Ensure this value is greater than or equal to 0.")
        return weight
