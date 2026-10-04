from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create-group/', views.create_group, name='create_group'),
    path('group/<int:group_id>/add-member/', views.join_group, name='join_group'),

    path('group/<int:group_id>/chat/', views.group_chat, name='group_chat'),

    path('group/<int:group_id>/decisions/', views.decisions, name='decisions'),
    path('group/<int:group_id>/decisions/new/', views.create_decision, name='create_decision'),
    path('group/<int:group_id>/decisions/<int:decision_id>/', views.view_decision, name='view_decision'),

    path('group/<int:group_id>/lists/', views.shared_lists, name='shared_lists'),
    path('group/<int:group_id>/lists/new/', views.create_list, name='create_list'),
    path('group/<int:group_id>/lists/<int:list_id>/', views.view_list, name='view_list'),

    path('buddy/', views.buddy, name='buddy'),

    path('signout/', views.signout, name='signout'),

    path('api/buddy/', views.api_buddy, name='api_buddy'),
    path('api/decision/<int:decision_id>/vote/', views.api_vote, name='api_vote'),
    path('api/decision/<int:decision_id>/resolve/', views.api_resolve, name='api_resolve'),
    path('api/list/<int:list_id>/add/', views.api_list_add, name='api_list_add'),
    path('api/list/<int:list_id>/toggle/<int:item_id>/', views.api_list_toggle, name='api_list_toggle'),
    path('api/list/<int:list_id>/ai/', views.api_list_ai, name='api_list_ai'),
]