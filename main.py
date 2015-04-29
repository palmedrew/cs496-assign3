import webapp2

config = {'default-group':'base-data'}

application = webapp2.WSGIApplication([
  ('/category', 'category.Category'),
  ('/item', 'item.Item'),
  ('/place', 'place.Place'),
], debug=True, config=config)
application.router.add(webapp2.Route(r'/category/<id:[0-9]+>', 'category.Category'))
application.router.add(webapp2.Route(r'/item/<id:\w+>', 'item.Item'))
application.router.add(webapp2.Route(r'/place/<id:[0-9]+>', 'place.Place'))
