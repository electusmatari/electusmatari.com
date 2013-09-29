from django.contrib import messages
from django.http import HttpResponseRedirect, Http404
from django.views.generic.list_detail import object_list
from django.views.generic.simple import direct_to_template

from emtools.emauth.decorators import require_mybbgroup
from emtools.channels.models import Channel, ChangeLog
from emtools.channels.forms import ChannelForm
import emtools.ccpeve.igb as igb

@require_mybbgroup('Electus Matari')
def view_channels(request, category):
    queryset = Channel.objects.filter(category=category)
    if category == 'other' or request.user.is_staff:
        if request.method == 'POST':
            form = ChannelForm(request.POST)
            if form.is_valid():
                channel = form.save(commit=False)
                if request.user.is_staff:
                    channel.category = category
                else:
                    channel.category = 'other'
                ChangeLog.objects.create(user=request.user,
                                         channel=channel.name,
                                         action="create")
                channel.save()
                messages.add_message(request, messages.INFO,
                                     "Channel created.")
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = ChannelForm()
    else:
        form = None
    return object_list(request, queryset,
                       template_name='channels/list.html',
                       extra_context={'tab': category,
                                      'form': form,
                                      'trust': igb.RequestTrust('http://www.electusmatari.com/tools/')},
                       template_object_name='channel')

@require_mybbgroup('Electus Matari')
def view_edit(request, channelid):
    queryset = Channel.objects.all()
    if not request.user.is_staff:
        queryset = queryset.filter(category='other')
    try:
        channel = queryset.get(pk=channelid)
    except Channel.DoesNotExist:
        raise Http404()
    if request.method == 'POST':
        oldname = channel.name
        form = ChannelForm(request.POST, instance=channel)
        if form.is_valid():
            channel = form.save()
            newname = channel.name
            if oldname != newname:
                name = "%s -> %s" % (oldname, newname)
            else:
                name = newname
            ChangeLog.objects.create(user=request.user,
                                     channel=name,
                                     action="edit")
            messages.add_message(request, messages.INFO,
                                 "Channel saved.")
            return HttpResponseRedirect('/tools/channels/%s/' %
                                        channel.category)
    else:
        form = ChannelForm(instance=channel)
    return direct_to_template(request, 'channels/edit.html',
                              extra_context={'tab': channel.category,
                                             'form': form})

@require_mybbgroup('Electus Matari')
def view_changelog(request):
    return object_list(request, ChangeLog.objects.all(),
                       paginate_by=23,
                       template_name='channels/changelog.html',
                       extra_context={'tab': 'changelog'},
                       template_object_name='log')

