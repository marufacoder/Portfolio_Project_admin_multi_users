from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    # Administrator tools
    path("portfolios/", views.portfolio_list, name="portfolio_list"),
    path("portfolios/add/", views.portfolio_create, name="portfolio_create"),
    # One portfolio (owner or administrator)
    path("portfolios/<int:pk>/", views.profile_detail, name="profile_detail"),
    path("portfolios/<int:pk>/edit/", views.profile_edit, name="profile_edit"),
    path("portfolios/<int:pk>/delete/", views.profile_delete, name="profile_delete"),
    path("portfolios/<int:pk>/cv/", views.cv_download, name="cv_download"),
    path("portfolios/<int:pk>/<slug:section>/add/", views.section_create, name="section_create"),
    # Items inside a portfolio
    path("items/<slug:section>/<int:pk>/edit/", views.section_edit, name="section_edit"),
    path("items/<slug:section>/<int:pk>/delete/", views.section_delete, name="section_delete"),
]
