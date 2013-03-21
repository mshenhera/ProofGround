from django.db import models

class Environment(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)
    owner = models.CharField(db_column='Owner', max_length=200, null=True)
    state = models.CharField(db_column='State', max_length=200, null=True)
    launch_time = models.DateTimeField(db_column='CreateTimestamp', editable=0, auto_now_add=True, null=True)
    expiration_time = models.DateTimeField(db_column='ExpirationTimestamp', null=True)

    def get_instanceid(self):
      if self.envproperty_set.filter(name='InstanceID'):
        return self.envproperty_set.get(name='InstanceID').value
      else:
        return ''

    def get_public_url(self):
      if self.envproperty_set.filter(name='PublicUrl'):
        return self.envproperty_set.get(name='PublicUrl').value
      else:
        return ''

    def get_name(self):
      if self.envproperty_set.filter(name='Name'):
        return self.envproperty_set.get(name='Name').value
      else:
        return ''

    def get_owner(self):
      if self.owner:
        return self.owner
      else:
        return ''

    def get_user(self):
      if self.envproperty_set.filter(name='SshUser'):
        return self.envproperty_set.get(name='SshUser').value
      else:
        return ''

    def get_password(self):
      if self.envproperty_set.filter(name='SshPassword'):
        return self.envproperty_set.get(name='SshPassword').value
      else:
        return ''

    def get_os(self):
      if self.envproperty_set.filter(name='OS'):
        return self.envproperty_set.get(name='OS').value
      else:
        return ''

    def get_status(self):
      if self.envproperty_set.filter(name='Status'):
        return self.envproperty_set.get(name='Status').value
      else:
        return ''

    def get_spell(self):
      if self.envproperty_set.filter(name='Spell'):
        return self.envproperty_set.get(name='Spell').value
      else:
        return ''

class EnvProperty(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)
    env_id = models.ForeignKey(Environment, db_column='EnvID')
    name = models.CharField(db_column='Name', max_length=200)
    value = models.CharField(db_column='Value', max_length=200, null=True)

    class Meta:
        unique_together = ('env_id', 'name')

