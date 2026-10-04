import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import (
    Group, ChatMessage, Decision, DecisionOption,
    Vote, SharedList, ListItem, BuddyMemory
)
from .forms import (
    GroupForm, ChatMessageForm, DecisionForm,
    SharedListForm, ListItemForm, AddMemberForm
)
from ai_engine.qwen import (
    chat, generate, SYSTEM_GROUP_CHAT, SYSTEM_DECISION,
    SYSTEM_LIST, SYSTEM_BUDDY
)


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'hub/register.html', {'form': form})


def signout(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


@login_required
def home(request):
    groups = request.user.friend_groups.all()
    if not groups.exists():
        return redirect('create_group')
    recent_decisions = Decision.objects.filter(
        group__in=groups, is_resolved=False
    ).order_by('-created_at')[:5]
    return render(request, 'hub/home.html', {
        'groups': groups,
        'recent_decisions': recent_decisions,
    })


@login_required
def create_group(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = Group.objects.create(
                name=form.cleaned_data['name'],
                created_by=request.user
            )
            group.members.add(request.user)
            return redirect('group_chat', group_id=group.id)
    else:
        form = GroupForm()
    return render(request, 'hub/create_group.html', {'form': form})


@login_required
def join_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        return redirect('home')
    error = None
    if request.method == 'POST':
        form = AddMemberForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                friend = User.objects.get(username=username)
                if friend not in group.members.all():
                    group.members.add(friend)
                return redirect('group_chat', group_id=group.id)
            except User.DoesNotExist:
                error = f'User "{username}" not found'
    else:
        form = AddMemberForm()
    return render(request, 'hub/join_group.html', {
        'group': group, 'form': form, 'error': error
    })


@login_required
def group_chat(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        return redirect('home')
    messages_list = group.messages.all()
    return render(request, 'hub/chat.html', {
        'group': group, 'messages': messages_list
    })


@login_required
def decisions(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        return redirect('home')
    active = group.decision_set.filter(is_resolved=False)
    resolved = group.decision_set.filter(is_resolved=True)
    return render(request, 'hub/decisions.html', {
        'group': group, 'active': active, 'resolved': resolved
    })


@login_required
def create_decision(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        return redirect('home')
    if request.method == 'POST':
        form = DecisionForm(request.POST)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.group = group
            decision.created_by = request.user
            decision.save()
            options_text = form.cleaned_data['options_text']
            for line in options_text.strip().split('\n'):
                line = line.strip()
                if line:
                    DecisionOption.objects.create(decision=decision, text=line)
            options = [opt.text for opt in decision.options.all()]
            prompt = (
                f"Question: {decision.question}\n"
                f"Options:\n" + "\n".join(f"- {o}" for o in options) +
                "\n\nWhat do you recommend and why?"
            )
            decision.ai_recommendation = generate(
                prompt=prompt, system=SYSTEM_DECISION
            )
            decision.save()
            return redirect('view_decision', group_id=group.id, decision_id=decision.id)
    else:
        form = DecisionForm()
    return render(request, 'hub/create_decision.html', {'group': group, 'form': form})


@login_required
def view_decision(request, group_id, decision_id):
    group = get_object_or_404(Group, id=group_id)
    decision = get_object_or_404(Decision, id=decision_id, group=group)
    user_vote = Vote.objects.filter(
        option__decision=decision, voter=request.user
    ).first()
    return render(request, 'hub/view_decision.html', {
        'group': group, 'decision': decision, 'user_vote': user_vote
    })


@login_required
def shared_lists(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        return redirect('home')
    lists = group.sharedlist_set.all()
    return render(request, 'hub/lists.html', {'group': group, 'lists': lists})


@login_required
def create_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        return redirect('home')
    if request.method == 'POST':
        form = SharedListForm(request.POST)
        if form.is_valid():
            shared_list = form.save(commit=False)
            shared_list.group = group
            shared_list.created_by = request.user
            shared_list.save()
            return redirect('view_list', group_id=group.id, list_id=shared_list.id)
    else:
        form = SharedListForm()
    return render(request, 'hub/create_list.html', {'group': group, 'form': form})


@login_required
def view_list(request, group_id, list_id):
    group = get_object_or_404(Group, id=group_id)
    shared_list = get_object_or_404(SharedList, id=list_id, group=group)
    items = shared_list.items.all()
    return render(request, 'hub/view_list.html', {
        'group': group, 'shared_list': shared_list, 'items': items
    })


@login_required
def buddy(request):
    history = request.session.get('buddy_history', [])
    memories = BuddyMemory.objects.filter(user=request.user)
    return render(request, 'hub/buddy.html', {
        'history': history, 'memories': memories
    })


# ── API Endpoints ────────────────────────────────────────────

@login_required
@require_POST
def api_buddy(request):
    data = json.loads(request.body)
    message = data.get('message', '').strip()
    if not message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    memories = BuddyMemory.objects.filter(user=request.user)
    memory_text = ""
    if memories.exists():
        memory_text = "Things I know about this person:\n"
        for mem in memories:
            memory_text += f"  - {mem.key}: {mem.value}\n"

    system = SYSTEM_BUDDY + "\n\n" + memory_text
    msgs = [{"role": "system", "content": system}]

    history = request.session.get('buddy_history', [])
    for m in history[-10:]:
        msgs.append(m)
    msgs.append({"role": "user", "content": message})

    ai_response = chat(msgs)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ai_response})
    request.session['buddy_history'] = history

    _try_save_memory(request.user, message)

    return JsonResponse({
        'response': ai_response,
        'role': 'assistant'
    })


@login_required
@require_POST
def api_vote(request, decision_id):
    decision = get_object_or_404(Decision, id=decision_id)
    data = json.loads(request.body)
    option_id = data.get('option_id')
    option = get_object_or_404(DecisionOption, id=option_id, decision=decision)

    Vote.objects.filter(option__decision=decision, voter=request.user).delete()
    Vote.objects.create(option=option, voter=request.user)

    votes = {}
    for vote in Vote.objects.filter(option__decision=decision):
        votes[vote.voter.username] = vote.option.text
    options = [opt.text for opt in decision.options.all()]
    votes_text = "\n".join(f"  {u} voted for: {v}" for u, v in votes.items())
    prompt = (
        f"Question: {decision.question}\n"
        f"Options:\n" + "\n".join(f"- {o}" for o in options) +
        f"\n\nCurrent votes:\n{votes_text}\n\n"
        "Consider the votes and give a final recommendation."
    )
    decision.ai_recommendation = generate(prompt=prompt, system=SYSTEM_DECISION)
    decision.save()

    options_data = []
    for opt in decision.options.all():
        options_data.append({
            'id': opt.id,
            'text': opt.text,
            'votes': opt.vote_count(),
        })

    return JsonResponse({
        'ai_recommendation': decision.ai_recommendation,
        'options': options_data,
        'voted_option_id': option_id,
    })


@login_required
@require_POST
def api_resolve(request, decision_id):
    decision = get_object_or_404(Decision, id=decision_id)
    decision.is_resolved = True
    decision.save()
    return JsonResponse({'resolved': True})


@login_required
@require_POST
def api_list_add(request, list_id):
    shared_list = get_object_or_404(SharedList, id=list_id)
    data = json.loads(request.body)
    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'Empty text'}, status=400)

    item = ListItem.objects.create(
        shared_list=shared_list,
        text=text,
        added_by=request.user
    )
    return JsonResponse({
        'id': item.id,
        'text': item.text,
        'added_by': request.user.username,
        'is_completed': False,
    })


@login_required
@require_POST
def api_list_toggle(request, list_id, item_id):
    item = get_object_or_404(ListItem, id=item_id, shared_list_id=list_id)
    item.is_completed = not item.is_completed
    item.save()
    return JsonResponse({
        'id': item.id,
        'is_completed': item.is_completed,
    })


@login_required
@require_POST
def api_list_ai(request, list_id):
    shared_list = get_object_or_404(SharedList, id=list_id)
    data = json.loads(request.body)
    action = data.get('action', '').strip()
    if not action:
        return JsonResponse({'error': 'Empty action'}, status=400)

    items = [item.text for item in shared_list.items.all()]
    items_text = "\n".join(f"- {i}" for i in items)
    prompt = (
        f"List: \"{shared_list.name}\"\n"
        f"Current items:\n{items_text}\n\n"
        f"Action requested: {action}"
    )
    ai_response = generate(prompt=prompt, system=SYSTEM_LIST)
    return JsonResponse({'response': ai_response})


def _try_save_memory(user, message):
    prefixes = {
        'i love': 'loves', 'i hate': 'hates', 'i like': 'likes',
        "i don't like": 'dislikes', 'my favorite': 'favorite',
        "i'm": 'is', 'i am': 'is',
    }
    msg_lower = message.lower()
    for prefix, key_prefix in prefixes.items():
        if prefix in msg_lower:
            idx = msg_lower.index(prefix)
            value = message[idx + len(prefix):].strip().rstrip('.')
            if value:
                key = f"{key_prefix}_{value[:20].replace(' ', '_')}"
                BuddyMemory.objects.update_or_create(
                    user=user, key=key, defaults={'value': value}
                )