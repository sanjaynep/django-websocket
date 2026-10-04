from django import forms
from .models import Decision, SharedList, ListItem


class GroupForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Group name'})
    )


class ChatMessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input',
            'placeholder': 'Type a message... use @buddy for AI',
            'autocomplete': 'off'
        })
    )


class DecisionForm(forms.ModelForm):
    options_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'input', 'rows': 4,
            'placeholder': 'One option per line:\nPizza Place\nThai Restaurant\nCook at home'
        })
    )

    class Meta:
        model = Decision
        fields = ['question']
        widgets = {
            'question': forms.TextInput(attrs={
                'class': 'input', 'placeholder': 'Where should we eat tonight?'
            })
        }


class SharedListForm(forms.ModelForm):
    class Meta:
        model = SharedList
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input', 'placeholder': 'Movies to watch together'
            })
        }


class ListItemForm(forms.ModelForm):
    class Meta:
        model = ListItem
        fields = ['text']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Add item...'})
        }


class AddMemberForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Friend username'})
    )