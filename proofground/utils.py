# AWS credentinal is stored in /etc/boto.cfg
# For example:
#[Credentials]
#aws_access_key_id = access_key
#aws_secret_access_key = secret_key
#
#[Boto]
#debug = 0
#num_retries = 10
#
#proxy = host
#proxy_port = port
#proxy_user = user
#proxy_pass = password
 
import boto.ec2
import re
from datetime import timedelta, datetime
from proofground.models import Environment, EnvProperty
from django.core.exceptions import ObjectDoesNotExist
import time

class DevOpsProofGround(object):

    def __init__(self, name, owner, os='AWS Linux', lifetime=1, user='testuser', password='securePassword', instance_id=None, spell='', tag_role='devopszone_proof_ground', public_url=None, state='new', aws_status='pending' ):
        self._lifetime = int(lifetime)*60-5
        self._launch_time = datetime.now()
        self._expiration_time = datetime.now()+timedelta(minutes=self._lifetime)
        self._instance_type = 't1.micro'
        self._security_groups = ['DIE - WebServer', 'DIE - Shell']
        self._name = name
        self._owner = owner
        self._os = os
        if user:
            self._user = user
        else:
            self._user = 'testuser'
        if password:
            self._password = password
        else:
            self._password = 'securePassword'

        self._instance_id = instance_id
        self._spell = spell
        self._tag_role = tag_role
        self._public_url = public_url
        self._state = state
        self._aws_status = aws_status
        self._error = ''

        if self._os == 'AWS Linux':
            # AWS Linux AMI: amazon/amzn-ami-pv-2012.09.1.x86_64-ebs
            # Works for Region US East N. Virginia only
            # See http://aws.amazon.com/amazon-linux-ami/
            self._ami = 'ami-54cf5c3d'
#            self._ami = 'ami-ee1a8987'
        else:
            # Ubuntu 12.04 AMI: 099720109477/ubuntu/images/ebs/ubuntu-precise-12.04-amd64-server-20130222
            # Works for Region US East N. Virginia only
            # See https://help.ubuntu.com/community/EC2StartersGuide
            # And http://cloud-images.ubuntu.com/releases/precise/release/
            self._ami = 'ami-de0d9eb7'
#            self._ami = 'ami-e01a8989'

        if self.exists():
            self._error = 'Environment with such name and owner already exists.'
            env = Environment.objects.filter(owner=self._owner, envproperty__name='Name', envproperty__value=self._name).exclude(state='terminated')[0]
            self._id = env.id
            self._launch_time = env.launch_time
            self._expiration_time = env.expiration_time
            self._state = env.state
            try:
              self._instance_id = env.envproperty_set.get(name='InstanID').value
            except ObjectDoesNotExist:
              pass

            try:
              self._public_url = env.envproperty_set.get(name='PublicUrl').value
            except ObjectDoesNotExist:
              pass

            try:
              self._aws_status = env.envproperty_set.get(name='Status').value
            except ObjectDoesNotExist:
              pass

            try:
              self._user = env.envproperty_set.get(name='SshUser').value
            except ObjectDoesNotExist:
              pass

            try:
              self._password = env.envproperty_set.get(name='SshPassword').value
            except ObjectDoesNotExist:
              pass

            try:
              self._os = env.envproperty_set.get(name='OS').value
            except ObjectDoesNotExist:
              pass

            try:
              self._spell = env.envproperty_set.get(name='Spell').value
            except ObjectDoesNotExist:
              pass

            try:
              self._ami = env.envproperty_set.get(name='AMI').value
            except ObjectDoesNotExist:
              pass
        else:
            try:
                new_environment = Environment(owner=self._owner,
                                  state=self._state,
                                  launch_time=self._launch_time,
                                  expiration_time=self._expiration_time)
                new_environment.save()
            except:
                self._error = 'Can not save environment to database.'

            self._id = new_environment.id

            try:
                new_environment.envproperty_set.create(name='Name', value=self._name)
                new_environment.envproperty_set.create(name='OS', value=self._os)
                new_environment.envproperty_set.create(name='Status', value=self._aws_status)
                new_environment.envproperty_set.create(name='SshUser', value=self._user)
                new_environment.envproperty_set.create(name='SshPassword', value=self._password)
                new_environment.envproperty_set.create(name='Spell', value=self._spell)
                new_environment.envproperty_set.create(name='AMI', value=self._ami)
            except:
                self._error = 'Can not save environemnt property to database.'


    # Verify if environment already exists
    # Returns:
    #    True if exists
    #    False if not exists
    def exists(self):
        existing_env = Environment.objects.filter(owner=self._owner, envproperty__name='Name', envproperty__value=self._name).exclude(state='terminated')
        if existing_env:  
            # environemnt with such owner and name already exists
            return True
        else:
            # environemnt with such owner and name doesn't exist
            return False


    # Start ec2 instance
    def start_instance(self):
        conn = boto.ec2.connect_to_region("us-east-1")

        # Change environment status
        environment = Environment.objects.get(id=self._id)
        environment.state = 'pending'
        environment.save()

        if self._spell:
            user_data = """#!/bin/bash
curl -s -L https://s3.amazonaws.com/ops_proof_ground/8350e5a3e24c153df2275c9f80692773/install-proof-ground.sh > ./install-proof-ground.sh
chmod a+x ./install-proof-ground.sh
./install-proof-ground.sh -u {0} -p {1} --spell "{2}"
""".format(self._user, self._password, self._spell)
        else:
            user_data = """#!/bin/bash
curl -s -L https://s3.amazonaws.com/ops_proof_ground/8350e5a3e24c153df2275c9f80692773/install-proof-ground.sh > ./install-proof-ground.sh
chmod a+x ./install-proof-ground.sh
./install-proof-ground.sh -u {0} -p {1}
""".format(self._user, self._password)

        # Start a new instance
        reservation = conn.run_instances(
            self._ami,
            instance_type   = self._instance_type,
            user_data       = user_data,
            security_groups = self._security_groups)

        instance = reservation.instances[0]
        self._instance_id = instance.id

        try:
            prop, created = EnvProperty.objects.get_or_create(env_id=environment, name='InstanceID')
            prop.value = self._instance_id
            prop.save()
        except:
            pass

        # Check up on its status
        status = instance.update()
        while status == 'pending':
            time.sleep(10)
            status = instance.update()

        if status == 'running':
            instance.add_tag("Name", self._name)
            instance.add_tag("Owner", self._owner)
            instance.add_tag("Role", self._tag_role)
        else:
            return False

        try:
            prop, created = EnvProperty.objects.get_or_create(env_id=environment, name='PublicUrl')
            prop.value = instance.public_dns_name
            prop.save()

            prop, created = EnvProperty.objects.get_or_create(env_id=environment, name='Status')
            prop.value = instance.state
            prop.save()
        except:
            pass

        environment.state = 'processed'
        environment.save()
        self._state = environment.state

        return True

    # Get information about instance from AWS and sync it to DB
    def update(self):
        if not self._instance_id:
            self._error = 'Can not update environment because aws instance id is absent.'
            return False

        conn = boto.ec2.connect_to_region("us-east-1")
        try:
            instance = conn.get_all_instances(self._instance_id)[0].instances[0]
        except:
            skip_instance_id_update = True
            self._state = 'terminated'

        if not skip_instance_id_update:
            prop, created = EnvProperty.objects.get_or_create(env_id=self._id, name='InstanceID')
            prop.value = instance.id
            prop.save()

            prop, created = EnvProperty.objects.get_or_create(env_id=self._id, name='PublicUrl')
            prop.value = instance.public_dns_name
            prop.save()

            self._state = instance.state

        prop, created = EnvProperty.objects.get_or_update(env_id=self._id, name='Status')
        prop.value = self._state
        prop.save()

        if self._state == 'terminated':
            environment.state = 'terminated'
        else:
            environment.state = 'processed'
            self._state = environment.state

        environment.save()

        return True


