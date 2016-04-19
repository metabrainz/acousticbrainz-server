from flask_admin import expose
from webserver.admin import AdminIndexView


class HomeView(AdminIndexView):

    @expose("/")
    def index(self):
        return self.render("admin/home.html")
