import datetime

from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.simple import direct_to_template
from django.views.generic.list_detail import object_list

from gradient.decorators import require_gradient
from gradient.rc.models import Change

from models import Ticket, TicketForm, State, TicketType, Comment

@require_gradient
def list(request):
    type_list = TicketType.objects.all()
    state_list = State.objects.all()
    qs = Ticket.objects.all()

    state_filter = request.GET.getlist('state')
    if len(state_filter) == 0:
        state_filter = ['open', 'in-progress']
    state_q = Q(state__name=state_filter[0])
    for stname in state_filter[1:]:
        state_q |= Q(state__name=stname)
    qs = qs.filter(state_q)

    type_filter = request.GET.getlist('type')
    if len(type_filter) == 0:
        type_filter = [tt.name for tt in request.user.tickettype_set.all()]
        if len(type_filter) == 0:
            type_filter = [tt.name for tt in TicketType.objects.all()
                           if tt.name != 'Waiting']
    elif 'all' in type_filter:
        type_filter = [tt.name for tt in TicketType.objects.all()]
    type_q = Q(type__name=type_filter[0])
    for tname in type_filter[1:]:
        type_q |= Q(type__name=tname)
    qs = qs.filter(type_q)

    owner_filter = request.GET.get('owner')
    if owner_filter is None:
        owner_filter = request.user.profile.name
    qs = qs.filter(Q(assignedto=None) |
                   Q(assignedto__profile__name__icontains=owner_filter))

    createdby_filter = request.GET.get('createdby')
    if createdby_filter is not None:
        qs = qs.filter(createdby__profile__name__icontains=createdby_filter)

    return object_list(request,
                       queryset=qs,
                       paginate_by=10,
                       template_object_name='ticket',
                       template_name='gts/list.html',
                       extra_context={
            'request': request,
            'owner_filter': owner_filter or '',
            'createdby_filter': createdby_filter or '',
            'type_filter': type_filter,
            'state_filter': state_filter or '',
            'type_list': type_list,
            'state_list': state_list})

@require_gradient
def details(request, ticketid):
    ticket = get_object_or_404(Ticket, pk=ticketid)
    return direct_to_template(request, 'gts/detail.html',
                              extra_context={'ticket': ticket})

@require_gradient
def add_comment(request, ticketid):
    ticket = get_object_or_404(Ticket, pk=ticketid)
    Comment.objects.create(author=request.user,
                           ticket=ticket,
                           text=request.POST.get('text', ''))
    Change.objects.create(app="gts",
                          category="comment",
                          text=("%s commented on ticket #%s" %
                                (request.user.profile.name,
                                 ticket.id)))
    return HttpResponseRedirect('/gts/%s/' % ticket.id)

@require_gradient
def create(request, ticketid=None):
    if ticketid is not None:
        instance = get_object_or_404(Ticket, pk=ticketid)
    else:
        instance = None
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=instance)
        if form.is_valid():
            ticket = form.save(commit=False)
            if instance is None:
                # Create
                ticket.createdby = request.user
                ticket.state = State.objects.get(name='open')
            else:
                # Edit
                ticket.editedby = request.user
                ticket.edited = datetime.datetime.now()
            ticket.save()
            Change.objects.create(app="gts",
                                  category="ticket",
                                  text=("%s %s ticket #%s" %
                                        (request.user.profile.name,
                                         "edited" if instance else "created",
                                         ticket.id)))
            return HttpResponseRedirect('/gts/%s/' % ticket.id)
    else:
        if instance is None:
            try:
                defaulttickettype = TicketType.objects.get(
                    name__iexact=request.GET.get('type', '')).id
            except TicketType.DoesNotExist:
                defaulttickettype = None
            form = TicketForm(initial={'type': defaulttickettype,
                                       'text': request.GET.get('text')})
        else:
            form = TicketForm(instance=instance)
    return direct_to_template(request, 'gts/create.html',
                              extra_context={'form': form,
                                             'instance': instance})

@require_gradient
def accept(request, ticketid):
    if request.method == 'POST':
        ticket = get_object_or_404(Ticket, pk=ticketid)
        ticket.assigned = datetime.datetime.utcnow()
        ticket.assignedto = request.user
        ticket.state = State.objects.get(name='in-progress')
        ticket.save()
        Change.objects.create(app="gts",
                              category="ticket",
                              text=("%s accepted ticket #%s" %
                                    (request.user.profile.name,
                                     ticket.id)))
        return HttpResponseRedirect('/gts/%s/' % ticket.id)
    return HttpResponseRedirect('/gts/')

@require_gradient
def close(request, ticketid):
    if request.method != 'POST':
        return HttpResponseRedirect('/gts/%s/' % ticketid)
    ticket = get_object_or_404(Ticket, pk=ticketid)
    ticket.closed = datetime.datetime.utcnow()
    if ticket.assignedto != request.user:
        ticket.assignedto = request.user
        ticket.assigned = datetime.datetime.utcnow()
    ticket.state = State.objects.get(name='closed')
    ticket.save()
    Change.objects.create(app="gts",
                          category="ticket",
                          text=("%s closed ticket #%s" %
                                (request.user.profile.name,
                                 ticket.id)))
    return HttpResponseRedirect('/gts/%s/' % ticket.id)

@require_gradient
def reopen(request, ticketid):
    if request.method == 'POST':
        ticket = get_object_or_404(Ticket, pk=ticketid)
        ticket.assigned = None
        ticket.assignedto = None
        ticket.state = State.objects.get(name='open')
        ticket.save()
        Change.objects.create(app="gts",
                              category="ticket",
                              text=("%s reopened ticket #%s" %
                                    (request.user.profile.name,
                                     ticket.id)))
    return HttpResponseRedirect('/gts/%s/' % ticket.id)

@require_gradient
def help(request):
    return direct_to_template(request, 'gts/help.html')

@require_gradient
def config(request):
    if request.method == 'POST':
        type_list = request.POST.getlist('type')
        request.user.tickettype_set.clear()
        for type_id in type_list:
            try:
                t = TicketType.objects.get(pk=type_id)
            except TicketType.DoesNotExist:
                pass
            else:
                request.user.tickettype_set.add(t)
        return HttpResponseRedirect('/gts/configuration/')
    selected_types = [tt.id for tt in request.user.tickettype_set.all()]
    if len(selected_types) == 0:
        selected_types = [tt.id for tt in TicketType.objects.all()
                          if tt.name != 'Waiting']
    type_list = [(tt, tt.id in selected_types)
                 for tt in TicketType.objects.all()]
    return direct_to_template(
        request, 'gts/config.html',
        extra_context={'type_list': type_list})


def add_ticket_status(request, status):
    if (request.user.is_anonymous() or
        request.user.profile is None or
        request.user.profile.corp != 'Gradient'):
        return
    numassigned = Ticket.objects.filter(assignedto=request.user,
                                        state__name='in-progress').count()
    numopen = Ticket.objects.filter(
        state__name='open'
        )
    wantedtypes = request.user.tickettype_set.all()
    if wantedtypes.count() > 0:
        numopen = numopen.filter(type__in=wantedtypes)
    else:
        numopen = numopen.exclude(type__name='Waiting')
    numopen = numopen.count()
    status.append({'text': "%i open ticket%s" % (numopen, 
                                                 "s" if numopen != 1 else ""),
                   'url': 'http://gradient.electusmatari.com/gts/?state=open'})
    status.append({'text': "%i assigned to you" % numassigned,
                   'url': 'http://gradient.electusmatari.com/gts/?state=in-progress&type=all'})
