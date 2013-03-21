from datetime import timedelta, datetime
from django.shortcuts import render_to_response
from django.http import HttpResponse
from proofground.models import Environment, EnvProperty
from django.template import RequestContext
from django.shortcuts import redirect
from proofground.utils import DevOpsProofGround
import boto.ec2
import time
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth import login

@login_required
def index(request, user=None):

    # Collection of proof ground environments depend on user
    if 'mshenh' == request.user.username:
        environment_list = Environment.objects.exclude(state='terminated', expiration_time__lt=datetime.now()-timedelta(minutes=30))
    else:
        environment_list = Environment.objects.filter(owner=request.user.username).exclude(state='terminated', expiration_time__lt=datetime.now()-timedelta(minutes=30))

    if request.method == "POST":
        if not request.POST['name']:
            return render_to_response('proofground/index.html', {
                'environment_list': environment_list,
                'error_message': "Name field is required.",
            }, context_instance=RequestContext(request))

        env_name = request.POST['name']
        env_os = request.POST['os']
        env_owner = request.user.username
        env_lifetime = int(request.POST['lifetime'])
        env_ssh_user = request.POST['ssh_user']
        env_ssh_password = request.POST['ssh_password']
        env_spell = request.POST['spell']

        env = DevOpsProofGround(name=env_name, os=env_os, owner=env_owner, lifetime=env_lifetime, user=env_ssh_user, password=env_ssh_password, spell=env_spell)
        if env._error:
            return render_to_response('proofground/index.html', {
                'environment_list': environment_list,
                'error_message': env._error,
            }, context_instance=RequestContext(request))
        return viewRefreshEnv(request)

    return render_to_response('proofground/index.html', {'username': request.user.username, 'environment_list': environment_list},
                               context_instance=RequestContext(request))


def viewRefreshEnv(request):
    environment_list = Environment.objects.all()
    return redirect('.')


# Redirect to login page
def viewLogout(request):
    logout(request)
    return redirect('/proofground/')


def startInstances(request):
    conn = boto.ec2.connect_to_region("us-east-1")
    glodal_env_list = []

    while Environment.objects.filter(state='new'):

        env_db = Environment.objects.filter(state='new')[0]

        name = env_db.envproperty_set.get(name='Name').value
        owner = env_db.owner

        env = DevOpsProofGround(name=name, owner=owner)
        env.start_instance()

    return render_to_response('proofground/create_instances.html', {'glodal_env_list': glodal_env_list})


def updateEnvStatus(request):
    conn = boto.ec2.connect_to_region("us-east-1")

    env_list = Environment.objects.filter(state='processed')

    global_env_list = []

    for cache_env in env_list:

        # Double check to prevent colision due to run job in parallel
        env = Environment.objects.get(id = cache_env.id)
        if env.state != 'processed':
            continue

        prop_status = EnvProperty.objects.get(env_id=env, name='Status')

        env_instance_id = str(env.get_instanceid())
        try:
            instance = conn.get_all_instances(env_instance_id)[0].instances[0]
        except:
            env.state = 'terminated'
            env.save()
            prop_status.value = 'terminated'
            prop_status.save()
            if env not in global_env_list:
                global_env_list.append(env)
            continue

        if prop_status != instance.state:
            prop_status.value = instance.state
            prop_status.save()
            if env not in global_env_list:
                global_env_list.append(env)

        if instance.state == 'terminated':
            env.state = 'terminated'
            env.save()
            if env not in global_env_list:
                global_env_list.append(env)
            continue

        prop_url = EnvProperty.objects.get(env_id=env, name='PublicUrl')
        if prop_url != instance.public_dns_name:
            prop_url.value = instance.public_dns_name
            prop_url.save()
            if env not in global_env_list:
                global_env_list.append(env)

    return render_to_response('proofground/update_env_status.html', {'global_env_list': global_env_list})

def terminateInstances(request):

    conn = boto.ec2.connect_to_region("us-east-1")
    env_list = Environment.objects.exclude(state='terminated')

    global_env_list = []

    for cache_env in env_list:

        # Double check to prevent colision due to run job in parallel
        env = Environment.objects.get(id = cache_env.id)
        if env.state == 'terminated':
            continue

        # Terminate instance that reached expiraion time
        if env.expiration_time:
            if datetime.now() > env.expiration_time:
                env_instance_id = str(env.get_instanceid())
                try:
                    instance = conn.get_all_instances(env_instance_id)[0].instances[0]
                except:
                    pass
                else:
                    conn.terminate_instances(instance_ids=[env_instance_id,])
                finally:
                    env.state = 'terminated'
                    env.save()
                    prop_status = EnvProperty.objects.get(env_id=env, name='Status')
                    prop_status.value = 'terminated'
                    prop_status.save()
                    global_env_list.append(env)

    return render_to_response('proofground/terminate_instances.html', {'global_env_list': global_env_list})

