from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('proofground.views',
    url(r'^$', 'index'),
    url(r'^start-instance$', 'startInstances'),
    url(r'^update-env-status$', 'updateEnvStatus'),
    url(r'^terminate-instances$', 'terminateInstances'),
    url(r'^refresh$', 'viewRefreshEnv'),
    url(r'^logout$', 'viewLogout'),
)

