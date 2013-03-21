from django.conf.urls.defaults import *
#from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^proofground/', include('proofground.urls')),
)

#urlpatterns += staticfiles_urlpatterns()
